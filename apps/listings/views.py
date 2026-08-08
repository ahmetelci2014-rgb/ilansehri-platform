from __future__ import annotations

from datetime import timedelta

import json

from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction as db_transaction
from django.db.models import Count, F, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView
from django.views.generic.edit import FormMixin

from apps.accounts.models import AccountRiskEvent, User, UserBlock, UserFollow, UserReport
from apps.accounts.trust import build_trust_profile
from apps.managed_services.models import ManagedRequest
from apps.support_center.models import StaffActionLog
from apps.support_center.services import log_staff_action

from .catalog import category_options, category_path
from .forms import (
    AppointmentForm,
    CounterOfferForm,
    HandoverCodeForm,
    ListingForm,
    ListingReportForm,
    MessageForm,
    OfferForm,
    ReviewForm,
    SavedSearchForm,
    TransactionDisputeForm,
)
from .geocoding import (
    ReverseGeocodingBusy,
    ReverseGeocodingError,
    reverse_geocode,
)
from .locations import CITY_CHOICES, get_districts, get_neighborhoods
from .location_preference import effective_listing_params
from .models import (
    Appointment,
    Category,
    Conversation,
    Favorite,
    Listing,
    ListingDraft,
    ListingImage,
    ListingMatch,
    ListingPriceHistory,
    ListingReport,
    Message,
    Notification,
    Offer,
    OfferEvent,
    Review,
    SavedSearch,
    SavedSearchMatch,
    Transaction,
    TransactionEvent,
)
from .services import (
    accept_offer,
    assess_listing_quality,
    consume_rate_limit,
    confirm_transaction,
    counter_offer,
    create_appointment,
    create_offer_event,
    create_notification,
    notify_listing_publication,
    notify_price_drop_favorites,
    optimize_listing_image,
    record_price_change,
    finalize_transaction,
    issue_handover_code,
    record_transaction_event,
    refresh_user_rating,
    reject_offer,
    review_window_is_open,
    respond_appointment,
    start_transaction_delivery,
    verify_handover_code,
)
from .matching import blocked_owner_ids, refresh_user_matches, sync_listing_matches
from .message_safety import safe_notification_preview
from .pricing import build_price_guide
from .safety import (
    assess_listing_safety,
    record_listing_report_risk,
    record_listing_risks,
    record_message_risk,
)
from .search_alerts import (
    apply_listing_filters,
    attach_nearby_distances,
    nearby_sort_key,
    normalize_saved_search_params,
    parse_nearby_params,
    parse_listing_number_query,
    saved_search_result_params,
)


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_decimal(value):
    try:
        candidate = Decimal(value)
        return candidate if candidate.is_finite() else None
    except (TypeError, ValueError, InvalidOperation):
        return None



@login_required
@require_GET
def reverse_location(request):
    """Cihaz koordinatını yalnız il / ilçe / mahalle seviyesine çevir."""

    latitude = _safe_decimal(request.GET.get("lat", ""))
    longitude = _safe_decimal(request.GET.get("lng", ""))

    if (
        latitude is None
        or longitude is None
        or not (-90 <= latitude <= 90)
        or not (-180 <= longitude <= 180)
    ):
        return JsonResponse(
            {"error": "Geçerli konum koordinatı gönderilmedi."},
            status=400,
        )

    if not consume_rate_limit(
        request,
        "reverse_location",
        limit=8,
        period=60,
    ):
        return JsonResponse(
            {
                "error": (
                    "Konum servisi kısa sürede çok kez kullanıldı. "
                    "Biraz sonra tekrar dene."
                )
            },
            status=429,
        )

    try:
        result = reverse_geocode(
            float(latitude),
            float(longitude),
        )
    except ReverseGeocodingBusy as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=429,
        )
    except ReverseGeocodingError as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=503,
        )

    return JsonResponse(
        {
            "city": result.get("city", ""),
            "district": result.get("district", ""),
            "neighborhood": result.get("neighborhood", ""),
            "attribution": result.get(
                "attribution",
                "© OpenStreetMap contributors",
            ),
        }
    )


def _safe_next_url(request, fallback):
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}):
        return candidate
    return fallback


def _save_images(listing, images):
    current_count = listing.images.count()
    has_cover = listing.images.filter(is_cover=True).exists()
    for index, image in enumerate(images, start=current_count):
        optimized_image = optimize_listing_image(image)
        ListingImage.objects.create(
            listing=listing,
            image=optimized_image,
            alt_text=listing.title,
            sort_order=index,
            is_cover=not has_cover and index == current_count,
        )


_DRAFT_BOOLEAN_FIELDS = {"price_on_request", "is_negotiable"}
_DRAFT_FIELD_LIMITS = {
    "title": 180,
    "description": 5000,
    "district": 80,
    "neighborhood": 120,
    "brand": 100,
    "model_name": 100,
    "condition": 50,
    "color": 60,
    "search_tags_text": 900,
    "technical_features_text": 5000,
    "service_area": 160,
    "experience_level": 80,
}


def _listing_draft_payload(post_data):
    payload = {}
    for field_name in [*ListingForm.Meta.fields, "search_tags_text", "technical_features_text"]:
        if field_name in _DRAFT_BOOLEAN_FIELDS:
            payload[field_name] = field_name in post_data
            continue
        value = post_data.get(field_name, "")
        if value not in (None, ""):
            payload[field_name] = str(value)[: _DRAFT_FIELD_LIMITS.get(field_name, 240)]
    return payload


def _save_listing_draft(request, *, source_listing=None):
    draft_id = request.POST.get("draft_id")
    draft = None
    if draft_id:
        draft = ListingDraft.objects.filter(pk=draft_id, user=request.user).first()
    if draft is None:
        oldest_ids = list(
            ListingDraft.objects.filter(user=request.user)
            .order_by("-updated_at")
            .values_list("pk", flat=True)[19:]
        )
        if oldest_ids:
            ListingDraft.objects.filter(pk__in=oldest_ids).delete()
        draft = ListingDraft(user=request.user)
    payload = _listing_draft_payload(request.POST)
    draft.title = str(payload.get("title", "")).strip()[:180]
    draft.data = payload
    draft.source_listing = source_listing
    draft.save()
    return draft


def _blocked_between(user_a, user_b) -> bool:
    if not user_a.is_authenticated:
        return False
    return UserBlock.objects.filter(
        Q(blocker=user_a, blocked=user_b) | Q(blocker=user_b, blocked=user_a)
    ).exists()


def _active_listing_q():
    return Q(status=Listing.Status.PUBLISHED) & (
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    )


def _compare_ids(request):
    raw_ids = request.session.get("compare_listing_ids", [])
    valid_ids = []
    for value in raw_ids:
        try:
            item_id = int(value)
        except (TypeError, ValueError):
            continue
        if item_id not in valid_ids:
            valid_ids.append(item_id)
    if valid_ids != raw_ids:
        request.session["compare_listing_ids"] = valid_ids
    return valid_ids[:4]




_KIND_META = {
    Listing.Kind.PRODUCT: {"icon": "📱", "headline": "İkinci el ve sıfır ürünleri keşfet", "description": "Elektronikten ev eşyasına, yakındaki ürün ilanlarını karşılaştır."},
    Listing.Kind.VEHICLE: {"icon": "🚗", "headline": "Aradığın aracı güvenle bul", "description": "Otomobil, motosiklet ve ticari araç ilanlarını ayrıntılı filtrele."},
    Listing.Kind.REAL_ESTATE: {"icon": "🏠", "headline": "Satılık ve kiralık emlak ilanları", "description": "Şehrindeki konut, işyeri ve arsa seçeneklerini tek ekranda incele."},
    Listing.Kind.SERVICE: {"icon": "🛠️", "headline": "Yakınındaki hizmet verenlere ulaş", "description": "Usta, bakım, taşıma, eğitim ve yerel hizmetleri keşfet."},
    Listing.Kind.NEED: {"icon": "📣", "headline": "İhtiyacını yaz, teklifler gelsin", "description": "Aradığın ürünü veya hizmeti ilan et; uygun kişiler sana ulaşsın."},
    Listing.Kind.JOB: {"icon": "💼", "headline": "İş ve kazanç fırsatlarını keşfet", "description": "Yerel iş ilanlarına ulaş, çalışan veya görev ortağı bul."},
}


class KindLandingView(TemplateView):
    template_name = "listings/category_landing.html"

    def dispatch(self, request, *args, **kwargs):
        self.kind = kwargs.get("kind", "")
        if self.kind not in dict(Listing.Kind.choices):
            raise Http404("Kategori bulunamadı.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        latest_price_history = ListingPriceHistory.objects.filter(
            listing_id=OuterRef("pk")
        ).order_by("-created_at")
        base = (
            Listing.objects.filter(_active_listing_q(), kind=self.kind)
            .annotate(
                latest_price_old=Subquery(latest_price_history.values("old_price")[:1]),
                latest_price_new=Subquery(latest_price_history.values("new_price")[:1]),
                latest_price_changed_at=Subquery(latest_price_history.values("created_at")[:1]),
            )
            .select_related("owner", "category")
            .prefetch_related("images", "price_history")
        )
        favorite_ids = set()
        if self.request.user.is_authenticated:
            favorite_ids = set(
                Favorite.objects.filter(user=self.request.user).values_list("listing_id", flat=True)
            )
        count_base = Listing.objects.filter(_active_listing_q(), kind=self.kind)
        category_rows = list(
            count_base.values("category_id", "category__name")
            .annotate(total=Count("id"))
            .order_by("-total", "category__name")[:12]
        )
        city_rows = list(
            count_base.values("city").annotate(total=Count("id")).order_by("-total", "city")[:10]
        )
        context.update(
            {
                "kind": self.kind,
                "kind_label": dict(Listing.Kind.choices)[self.kind],
                "kind_meta": _KIND_META[self.kind],
                "latest_listings": base.order_by("-is_featured", "-published_at", "-created_at")[:12],
                "popular_listings": base.order_by("-view_count", "-favorite_count", "-created_at")[:10],
                "price_drop_listings": base.filter(latest_price_old__gt=F("latest_price_new")).order_by(
                    "-latest_price_changed_at", "-created_at"
                )[:10],
                "category_rows": category_rows,
                "city_rows": city_rows,
                "listing_count": base.count(),
                "favorite_ids": favorite_ids,
                "compare_ids": set(_compare_ids(self.request)),
            }
        )
        return context


class SavedSearchListView(LoginRequiredMixin, TemplateView):
    template_name = "listings/saved_searches.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        searches = list(
            SavedSearch.objects.filter(user=self.request.user).annotate(
                pending_match_count=Count("matches", filter=Q(matches__notified_at__isnull=True))
            )
        )
        label_map = {
            "q": "Arama", "city": "Şehir", "district": "İlçe", "neighborhood": "Mahalle",
            "kind": "İlan türü", "action": "İşlem", "category": "Kategori", "brand": "Marka",
            "model": "Model", "condition": "Durum", "color": "Renk",
            "delivery_type": "Teslimat", "fuel_type": "Yakıt", "transmission": "Vites",
            "fee_type": "Ücret", "job_type": "İş türü", "room_count": "Oda",
            "heating_type": "Isıtma", "floor_location": "Kat", "service_area": "Hizmet bölgesi",
            "experience_level": "Deneyim", "min_price": "En az", "max_price": "En çok",
            "min_year": "Min. yıl", "max_year": "Maks. yıl", "max_mileage": "Azami km",
            "min_area": "Min. m²", "max_area": "Maks. m²", "max_building_age": "Azami bina yaşı",
            "price_drop": "Fiyat düşüşü", "verified": "Doğrulanmış", "managed": "Güvenceli",
            "following": "Takip edilen", "radius": "Yakınlık",
        }
        for saved in searches:
            saved.query_string = urlencode(saved_search_result_params(saved.query_params or {}), doseq=True)
            saved.filter_summary = [
                {"label": label_map.get(key, key.replace("_", " ").title()), "value": value}
                for key, value in (saved.query_params or {}).items()
                if value and key not in {"lat", "lng"}
            ]
        context["saved_searches"] = searches
        return context


@require_GET
def search_suggestions(request):
    query = request.GET.get("q", "").strip()[:80]
    listing_number = parse_listing_number_query(query)
    if len(query) < 2 and listing_number is None:
        return JsonResponse({"results": []})

    results = []
    seen = set()

    if listing_number is not None:
        exact_listing = (
            Listing.objects.filter(_active_listing_q(), pk=listing_number)
            .select_related("category")
            .first()
        )
        if exact_listing:
            seen.add(("listing", exact_listing.pk))
            results.append(
                {
                    "label": exact_listing.title,
                    "meta": (
                        f"İlan No: {exact_listing.pk} · "
                        f"{exact_listing.get_kind_display()} · {exact_listing.city}"
                    ),
                    "type": "listing_number",
                    "url": exact_listing.get_absolute_url(),
                }
            )

    listings = (
        Listing.objects.filter(_active_listing_q())
        .filter(
            Q(title__icontains=query)
            | Q(brand__icontains=query)
            | Q(model_name__icontains=query)
            | Q(category__name__icontains=query)
        )
        .select_related("category")
        .order_by("-is_featured", "-view_count", "-created_at")[:6]
    )
    for listing in listings:
        key = ("listing", listing.pk)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "label": listing.title,
                "meta": f"{listing.get_kind_display()} · {listing.city}",
                "type": "listing",
                "url": listing.get_absolute_url(),
            }
        )

    categories = Category.objects.filter(is_active=True, name__icontains=query).order_by("sort_order", "name")[:4]
    for category in categories:
        key = ("category", category.name.lower())
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "label": category.name,
                "meta": "Kategori",
                "type": "category",
                "url": f"{reverse('listings:list')}?{urlencode({'category': category.pk})}",
            }
        )

    brands = (
        Listing.objects.filter(_active_listing_q(), brand__icontains=query)
        .exclude(brand="")
        .order_by("brand")
        .values_list("brand", flat=True)
        .distinct()[:4]
    )
    for brand in brands:
        key = ("brand", brand.lower())
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "label": brand,
                "meta": "Marka",
                "type": "brand",
                "url": f"{reverse('listings:list')}?{urlencode({'brand': brand})}",
            }
        )

    return JsonResponse({"results": results[:10]})


@login_required
@require_GET
def price_guide(request):
    if not consume_rate_limit(request, "price_guide", limit=30, period=300):
        return JsonResponse(
            {"guide": {"available": False, "message": "Çok sık fiyat sorgusu yapıldı. Birkaç dakika sonra tekrar dene."}},
            status=429,
        )

    kind = request.GET.get("kind", "").strip()
    action = request.GET.get("action", "").strip()
    category_id = _safe_int(request.GET.get("category"))
    if kind not in dict(Listing.Kind.choices) or action not in dict(Listing.Action.choices) or not category_id:
        return JsonResponse(
            {"guide": {"available": False, "message": "İlan türü, işlem ve kategori bilgilerini tamamla."}}
        )

    category = Category.objects.filter(pk=category_id, is_active=True).select_related("parent").first()
    if not category:
        return JsonResponse({"guide": {"available": False, "message": "Geçerli bir kategori seç."}})

    current_id = _safe_int(request.GET.get("current_id"))
    if current_id and not Listing.objects.filter(pk=current_id, owner=request.user).exists():
        current_id = None

    subject = Listing(
        owner=request.user,
        category=category,
        kind=kind,
        action=action,
        title=request.GET.get("title", "").strip()[:180],
        description="",
        price=_safe_decimal(request.GET.get("price")),
        brand=request.GET.get("brand", "").strip()[:100],
        model_name=request.GET.get("model_name", "").strip()[:100],
        model_year=_safe_int(request.GET.get("model_year")),
        mileage=_safe_int(request.GET.get("mileage")),
        room_count=request.GET.get("room_count", "").strip()[:30],
        area_m2=_safe_int(request.GET.get("area_m2")),
        city=request.GET.get("city", "").strip()[:80],
        district=request.GET.get("district", "").strip()[:80],
        neighborhood=request.GET.get("neighborhood", "").strip()[:120],
    )
    guide = build_price_guide(subject, exclude_pk=current_id)
    return JsonResponse({"guide": guide.to_dict()})


class ListingListView(ListView):
    model = Listing
    template_name = "listings/list.html"
    context_object_name = "listings"
    paginate_by = 24

    def get_queryset(self):
        latest_price_history = ListingPriceHistory.objects.filter(
            listing_id=OuterRef("pk")
        ).order_by("-created_at")
        qs = (
            Listing.objects.filter(_active_listing_q())
            .annotate(
                latest_price_old=Subquery(latest_price_history.values("old_price")[:1]),
                latest_price_new=Subquery(latest_price_history.values("new_price")[:1]),
                latest_price_changed_at=Subquery(latest_price_history.values("created_at")[:1]),
            )
            .select_related("owner", "category")
            .prefetch_related("images", "price_history")
        )
        params = effective_listing_params(self.request)
        qs = apply_listing_filters(qs, params, user=self.request.user)
        sort = params.get("sort", "newest")
        ordering = {
            "newest": ("-is_featured", "-published_at", "-created_at"),
            "price_asc": ("price", "-is_featured"),
            "price_desc": ("-price", "-is_featured"),
            "popular": ("-view_count", "-favorite_count", "-created_at"),
            "oldest": ("created_at",),
            "price_drop": ("-latest_price_changed_at", "-created_at"),
            "nearby": ("-is_featured", "-published_at", "-created_at"),
        }.get(sort, ("-is_featured", "-published_at", "-created_at"))
        qs = qs.order_by(*ordering)

        if parse_nearby_params(params):
            items = attach_nearby_distances(qs, params)
            if sort == "nearby":
                items.sort(key=nearby_sort_key)
            return items
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        source_params = effective_listing_params(self.request)
        pagination_params = source_params.copy()
        pagination_params.pop("page", None)
        context["pagination_query"] = pagination_params.urlencode()

        favorite_ids = set()
        if self.request.user.is_authenticated:
            favorite_ids = set(
                Favorite.objects.filter(user=self.request.user).values_list("listing_id", flat=True)
            )

        params = normalize_saved_search_params(source_params)
        display_filters = dict(params)
        display_filters["sort"] = source_params.get("sort", "newest")[:20] or "newest"
        all_categories = list(
            Category.objects.filter(is_active=True)
            .select_related("parent", "parent__parent")
            .prefetch_related("children")
            .order_by("parent__sort_order", "parent__name", "sort_order", "name")
        )
        categories_by_id = {item.pk: item for item in all_categories}
        selected_category = categories_by_id.get(_safe_int(params.get("category")))

        choice_maps = {
            "kind": dict(Listing.Kind.choices),
            "action": dict(Listing.Action.choices),
            "delivery_type": dict(Listing.DeliveryType.choices),
            "fuel_type": dict(Listing.FuelType.choices),
            "transmission": dict(Listing.Transmission.choices),
            "fee_type": dict(Listing.FeeType.choices),
            "job_type": dict(Listing.JobType.choices),
        }
        label_map = {
            "q": "Arama", "city": "Şehir", "district": "İlçe", "neighborhood": "Mahalle",
            "kind": "İlan türü", "action": "İşlem", "category": "Kategori",
            "brand": "Marka", "model": "Model", "condition": "Durum", "color": "Renk",
            "delivery_type": "Teslimat", "room_count": "Oda", "heating_type": "Isıtma",
            "floor_location": "Kat", "service_area": "Hizmet bölgesi",
            "experience_level": "Deneyim", "fuel_type": "Yakıt", "transmission": "Vites",
            "fee_type": "Ücret tipi", "job_type": "Çalışma şekli",
            "min_price": "En az fiyat", "max_price": "En çok fiyat",
            "min_year": "En düşük yıl", "max_year": "En yüksek yıl",
            "max_mileage": "Azami km", "min_area": "En az m²", "max_area": "En çok m²",
            "max_building_age": "Azami bina yaşı",
            "verified": "Doğrulanmış satıcı", "managed": "İlan Şehri güvenceli",
            "price_drop": "Fiyatı düşen", "following": "Takip edilen satıcı",
        }
        ordered_filter_keys = (
            "q", "kind", "category", "action", "city", "district", "neighborhood",
            "brand", "model", "condition", "color", "delivery_type", "room_count",
            "min_price", "max_price", "min_year", "max_year", "max_mileage",
            "fuel_type", "transmission", "min_area", "max_area", "max_building_age",
            "heating_type", "floor_location", "service_area", "fee_type", "job_type",
            "experience_level", "verified", "managed", "price_drop", "following",
        )
        active_labels = []
        for key in ordered_filter_keys:
            value = params.get(key, "")
            if not value:
                continue
            display_value = value
            if key in choice_maps:
                display_value = choice_maps[key].get(value, value)
            elif key == "category" and selected_category:
                display_value = category_path(selected_category)
            elif key in {"verified", "managed", "price_drop", "following"}:
                display_value = "Evet"
            remove_params = source_params.copy()
            remove_params.pop("page", None)
            remove_params.pop(key, None)
            if key == "city":
                remove_params.pop("district", None)
                remove_params.pop("neighborhood", None)
                remove_params["location_reset"] = "1"
            active_labels.append(
                {
                    "key": key,
                    "label": label_map.get(key, key.replace("_", " ").title()),
                    "value": display_value,
                    "remove_url": f"{reverse('listings:list')}?{remove_params.urlencode()}" if remove_params else reverse("listings:list"),
                }
            )

        nearby = parse_nearby_params(params)
        if nearby:
            remove_params = source_params.copy()
            for key in ("lat", "lng", "radius"):
                remove_params.pop(key, None)
            remove_params["location_reset"] = "1"
            if remove_params.get("sort") == "nearby":
                remove_params["sort"] = "newest"
            active_labels.append(
                {
                    "key": "radius",
                    "label": "Yakınlık",
                    "value": f"{nearby[2]} km",
                    "remove_url": f"{reverse('listings:list')}?{remove_params.urlencode()}" if remove_params else reverse("listings:list"),
                }
            )

        kind = params.get("kind", "")
        category_counts = (
            Listing.objects.filter(_active_listing_q())
            .values("category_id")
            .annotate(total=Count("id"))
        )
        if kind:
            category_counts = category_counts.filter(kind=kind)
        if params.get("city"):
            category_counts = category_counts.filter(city__iexact=params["city"])
        totals = {row["category_id"]: row["total"] for row in category_counts}
        shortcuts = []
        for option in category_options(all_categories):
            if option["depth"] == 0 or not option["is_leaf"]:
                continue
            if kind and option["kind"] != kind:
                continue
            total = totals.get(option["id"], 0)
            if total:
                query = {"category": option["id"]}
                if kind:
                    query["kind"] = kind
                if params.get("city"):
                    query["city"] = params["city"]
                shortcuts.append(option | {"total": total, "url": f"{reverse('listings:list')}?{urlencode(query)}"})
        shortcuts.sort(key=lambda item: (-item["total"], item["path"].casefold()))

        if params.get("q"):
            result_title = f"“{params['q']}” sonuçları"
        elif selected_category:
            result_title = category_path(selected_category)
        elif kind:
            result_title = f"{dict(Listing.Kind.choices).get(kind, 'İlan')} ilanları"
        elif params.get("city"):
            result_title = f"{params['city']} ilanları"
        else:
            result_title = "Tüm ilanlar"
        location_summary = " / ".join(
            value for value in (params.get("city"), params.get("district"), params.get("neighborhood")) if value
        )

        context.update(
            {
                "kind_choices": Listing.Kind.choices,
                "action_choices": Listing.Action.choices,
                "city_choices": CITY_CHOICES,
                "category_options": category_options(all_categories),
                "fuel_choices": Listing.FuelType.choices,
                "transmission_choices": Listing.Transmission.choices,
                "delivery_choices": Listing.DeliveryType.choices,
                "fee_choices": Listing.FeeType.choices,
                "job_choices": Listing.JobType.choices,
                "active_filters": display_filters,
                "active_filter_labels": active_labels,
                "active_filter_count": len(active_labels),
                "selected_category": selected_category,
                "category_shortcuts": shortcuts[:10],
                "result_title": result_title,
                "location_summary": location_summary,
                "district_suggestions": get_districts(params.get("city", "")),
                "neighborhood_suggestions": get_neighborhoods(params.get("city", ""), params.get("district", "")),
                "favorite_ids": favorite_ids,
                "compare_ids": set(_compare_ids(self.request)),
                "saved_search_form": SavedSearchForm(),
            }
        )
        return context


class ListingDetailView(FormMixin, DetailView):
    model = Listing
    template_name = "listings/detail.html"
    context_object_name = "listing"
    form_class = OfferForm

    def get_queryset(self):
        qs = Listing.objects.select_related("owner", "category").prefetch_related("images", "price_history")
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return qs
        if user.is_authenticated:
            return qs.filter(_active_listing_q() | Q(owner=user))
        return qs.filter(_active_listing_q())

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        is_active_public = obj.status == Listing.Status.PUBLISHED and (
            obj.expires_at is None or obj.expires_at > timezone.now()
        )
        if not is_active_public:
            if obj.status == Listing.Status.PUBLISHED and obj.expires_at and obj.expires_at <= timezone.now():
                Listing.objects.filter(pk=obj.pk).update(status=Listing.Status.EXPIRED, updated_at=timezone.now())
                obj.status = Listing.Status.EXPIRED
                sync_listing_matches(obj, notify=False)
            if not self.request.user.is_authenticated or not (self.request.user == obj.owner or self.request.user.is_staff):
                raise Http404
        session_key = f"viewed_listing_{obj.pk}"
        if not self.request.session.get(session_key):
            Listing.objects.filter(pk=obj.pk).update(view_count=F("view_count") + 1)
            self.request.session[session_key] = True
            obj.view_count += 1
        recent = [item_id for item_id in self.request.session.get("recently_viewed", []) if item_id != obj.pk]
        recent.insert(0, obj.pk)
        self.request.session["recently_viewed"] = recent[:12]
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["is_favorite"] = user.is_authenticated and Favorite.objects.filter(user=user, listing=self.object).exists()
        pending_key = f"pending_message_{self.object.pk}"
        pending_message = self.request.session.pop(pending_key, None)
        context["message_form"] = MessageForm(
            initial={"body": pending_message.get("body", "")}
        ) if pending_message else MessageForm()
        context["message_safety_pending"] = bool(pending_message)
        context["report_form"] = ListingReportForm()
        context["owner_reviews"] = self.object.owner.received_reviews.filter(is_visible=True).select_related("reviewer")[:6]
        context["blocked_between"] = user.is_authenticated and _blocked_between(user, self.object.owner)
        context["owner_pending_offers"] = (
            self.object.offers.filter(status=Offer.Status.PENDING).select_related("sender")
            if user.is_authenticated and user == self.object.owner
            else Offer.objects.none()
        )
        context["compare_ids"] = set(_compare_ids(self.request))
        context["is_compared"] = self.object.pk in context["compare_ids"]
        context["price_history"] = self.object.price_history.all()[:8]
        context["is_following"] = (
            user.is_authenticated
            and user != self.object.owner
            and UserFollow.objects.filter(follower=user, seller=self.object.owner).exists()
        )
        context["my_pending_offer"] = (
            self.object.offers.filter(sender=user, status=Offer.Status.PENDING)
            .select_related("last_actor", "listing__owner")
            .prefetch_related("events__actor")
            .first()
            if user.is_authenticated and user != self.object.owner
            else None
        )
        similar_base = (
            Listing.objects.filter(_active_listing_q(), kind=self.object.kind)
            .exclude(pk=self.object.pk)
            .select_related("owner", "category")
            .prefetch_related("images", "price_history")
            .order_by("-is_featured", "-published_at", "-created_at")
        )
        # Önce aynı kategori ve konum, sonra aynı kategori ve aynı şehir gelir.
        # Böylece “benzer ilan” alanı yalnız tür eşleşmesine dayanmaz.
        similar_rows = []
        similar_ids = set()
        similar_buckets = (
            similar_base.filter(category_id=self.object.category_id, city__iexact=self.object.city),
            similar_base.filter(category_id=self.object.category_id),
            similar_base.filter(city__iexact=self.object.city),
            similar_base,
        )
        for bucket in similar_buckets:
            for item in bucket[:12]:
                if item.pk in similar_ids:
                    continue
                similar_rows.append(item)
                similar_ids.add(item.pk)
                if len(similar_rows) >= 8:
                    break
            if len(similar_rows) >= 8:
                break
        context["similar_listings"] = similar_rows
        context["seller_other_listings"] = (
            Listing.objects.filter(_active_listing_q(), owner=self.object.owner)
            .exclude(pk=self.object.pk)
            .select_related("owner", "category")
            .prefetch_related("images", "price_history")[:6]
        )
        context["seller_active_listing_count"] = Listing.objects.filter(
            _active_listing_q(), owner=self.object.owner
        ).count()
        context["gallery_images"] = list(self.object.images.all())
        context["gallery_count"] = len(context["gallery_images"])
        detail_cover = self.object.cover_image
        context["cover_image_id"] = detail_cover.pk if detail_cover else None
        if self.object.kind == Listing.Kind.SERVICE:
            context["contact_target_label"] = "Hizmet verene"
        elif self.object.kind == Listing.Kind.JOB:
            context["contact_target_label"] = "İlan sahibine"
        elif self.object.kind == Listing.Kind.NEED:
            context["contact_target_label"] = "Talep sahibine"
        else:
            context["contact_target_label"] = "Satıcıya"
        if user.is_authenticated:
            context["favorite_ids"] = set(
                Favorite.objects.filter(user=user).values_list("listing_id", flat=True)
            )
        else:
            context["favorite_ids"] = set()
        context["owner_match_count"] = 0
        if user.is_authenticated and user == self.object.owner:
            excluded_owner_ids = blocked_owner_ids(user.pk)
            if self.object.action in {Listing.Action.WANTED, Listing.Action.SERVICE_REQUEST, Listing.Action.JOB_REQUEST} or self.object.kind == Listing.Kind.NEED:
                context["owner_match_count"] = (
                    self.object.wanted_matches.filter(offered_listing__status=Listing.Status.PUBLISHED)
                    .filter(Q(offered_listing__expires_at__isnull=True) | Q(offered_listing__expires_at__gt=timezone.now()))
                    .exclude(wanted_status=ListingMatch.Status.DISMISSED)
                    .exclude(offered_listing__owner_id__in=excluded_owner_ids)
                    .count()
                )
                context["owner_match_tab"] = "wanted"
            else:
                context["owner_match_count"] = (
                    self.object.offered_matches.filter(wanted_listing__status=Listing.Status.PUBLISHED)
                    .filter(Q(wanted_listing__expires_at__isnull=True) | Q(wanted_listing__expires_at__gt=timezone.now()))
                    .exclude(offered_status=ListingMatch.Status.DISMISSED)
                    .exclude(wanted_listing__owner_id__in=excluded_owner_ids)
                    .count()
                )
                context["owner_match_tab"] = "offered"
        context["price_guide"] = build_price_guide(self.object, exclude_pk=self.object.pk)
        context["quality_profile"] = assess_listing_quality(self.object)
        context["listing_safety_profile"] = assess_listing_safety(
            self.object, price_guide=context["price_guide"]
        )
        context["seller_trust_profile"] = build_trust_profile(
            self.object.owner, include_private=bool(user.is_authenticated and user.is_staff)
        )
        context["canonical_url"] = self.request.build_absolute_uri(self.object.get_absolute_url())
        cover = self.object.cover_image
        context["share_image_url"] = self.request.build_absolute_uri(cover.image.url) if cover else ""
        schema = {
            "@context": "https://schema.org",
            "@type": "Product" if self.object.kind in {Listing.Kind.PRODUCT, Listing.Kind.VEHICLE} else "Offer",
            "name": self.object.title,
            "description": self.object.description[:500],
            "url": context["canonical_url"],
            "image": [self.request.build_absolute_uri(item.image.url) for item in self.object.images.all()[:10]],
            "offers": {
                "@type": "Offer",
                "priceCurrency": "TRY",
                "price": str(self.object.price) if self.object.price is not None else "",
                "availability": "https://schema.org/InStock",
                "url": context["canonical_url"],
            },
            "seller": {
                "@type": "Person",
                "name": self.object.owner.display_name,
            },
        }
        context["listing_schema_json"] = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={self.object.get_absolute_url()}")
        if not consume_rate_limit(request, "offer", limit=8, period=600):
            messages.error(request, "Kısa sürede çok fazla teklif işlemi yaptın. Birkaç dakika sonra tekrar dene.")
            return redirect(self.object.get_absolute_url())
        if self.object.status != Listing.Status.PUBLISHED:
            messages.warning(request, "Yalnız yayındaki ilanlara teklif verilebilir.")
            return redirect(self.object.get_absolute_url())
        if request.user == self.object.owner:
            messages.warning(request, "Kendi ilanına teklif veremezsin.")
            return redirect(self.object.get_absolute_url())
        if self.object.offers.filter(sender=request.user, status=Offer.Status.PENDING).exists():
            messages.info(request, "Bu ilan için bekleyen bir teklifin zaten var.")
            return redirect(self.object.get_absolute_url())
        if _blocked_between(request.user, self.object.owner):
            messages.error(request, "Bu kullanıcıyla iletişim veya teklif işlemi yapılamıyor.")
            return redirect(self.object.get_absolute_url())
        form = self.get_form()
        if form.is_valid():
            offer = form.save(commit=False)
            offer.listing = self.object
            offer.sender = request.user
            offer.last_actor = request.user
            offer.save()
            create_offer_event(
                offer=offer,
                actor=request.user,
                event_type=OfferEvent.Type.SUBMITTED,
                amount=offer.amount,
                message=offer.message,
            )
            create_notification(
                user=self.object.owner,
                actor=request.user,
                listing=self.object,
                notification_type=Notification.Type.OFFER,
                title="İlanına yeni teklif geldi",
                body=f"{request.user.display_name} bir teklif gönderdi.",
                link=f"{reverse('listings:offer_center')}?focus={offer.pk}",
            )
            messages.success(request, "Teklifin ilan sahibine gönderildi.")
            return redirect(self.object.get_absolute_url())
        return self.render_to_response(self.get_context_data(form=form))


class OwnerListingMixin(LoginRequiredMixin, UserPassesTestMixin):
    def get_queryset(self):
        return Listing.objects.filter(owner=self.request.user)

    def test_func(self):
        return self.get_object().owner_id == self.request.user.pk


class ListingDraftListView(LoginRequiredMixin, ListView):
    model = ListingDraft
    template_name = "listings/drafts.html"
    context_object_name = "drafts"
    paginate_by = 20

    def get_queryset(self):
        return ListingDraft.objects.filter(user=self.request.user).select_related("source_listing")


@require_POST
def delete_listing_draft(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    draft = get_object_or_404(ListingDraft, pk=pk, user=request.user)
    draft.delete()
    messages.success(request, "Taslak silindi.")
    return redirect("listings:drafts")


class MyListingListView(LoginRequiredMixin, ListView):
    template_name = "listings/my_listings.html"
    context_object_name = "listings"
    paginate_by = 12

    STATUS_FILTERS = (
        ("published", "Yayında"),
        ("review", "İncelemede"),
        ("paused", "Duraklatıldı"),
        ("draft", "Taslak"),
        ("expired", "Süresi doldu"),
        ("completed", "Sonuçlandı"),
        ("rejected", "Reddedildi"),
    )
    SORT_OPTIONS = {
        "updated": "-updated_at",
        "views": "-view_count",
        "favorites": "-favorite_count",
        "offers": "-offer_total",
        "messages": "-conversation_count",
        "expiring": "expires_at",
        "oldest": "created_at",
    }

    def get_queryset(self):
        queryset = (
            Listing.objects.filter(owner=self.request.user)
            .select_related("category", "owner")
            .prefetch_related("images", "price_history")
            .annotate(
                offer_total=Count("offers", distinct=True),
                pending_offer_count=Count(
                    "offers",
                    filter=Q(offers__status=Offer.Status.PENDING),
                    distinct=True,
                ),
                conversation_count=Count("conversations", distinct=True),
                unread_message_count=Count(
                    "conversations__messages",
                    filter=Q(conversations__messages__is_read=False)
                    & ~Q(conversations__messages__sender=self.request.user),
                    distinct=True,
                ),
            )
        )
        self.query = self.request.GET.get("q", "").strip()[:120]
        self.status_filter = self.request.GET.get("status", "").strip()
        self.sort_filter = self.request.GET.get("sort", "updated").strip()

        valid_statuses = {value for value, _label in self.STATUS_FILTERS}
        if self.status_filter in valid_statuses:
            queryset = queryset.filter(status=self.status_filter)
        elif self.status_filter == "attention":
            warning_date = timezone.now() + timedelta(days=7)
            queryset = queryset.filter(
                Q(status__in=[Listing.Status.REVIEW, Listing.Status.REJECTED, Listing.Status.EXPIRED])
                | Q(status=Listing.Status.PUBLISHED, expires_at__lte=warning_date)
            )
        elif self.status_filter:
            self.status_filter = ""

        if self.sort_filter not in self.SORT_OPTIONS:
            self.sort_filter = "updated"

        if self.query:
            queryset = queryset.filter(
                Q(title__icontains=self.query)
                | Q(category__name__icontains=self.query)
                | Q(city__icontains=self.query)
                | Q(district__icontains=self.query)
                | Q(brand__icontains=self.query)
                | Q(model_name__icontains=self.query)
            )

        ordering = self.SORT_OPTIONS.get(self.sort_filter, self.SORT_OPTIONS["updated"])
        if ordering == "expires_at":
            queryset = queryset.order_by(F("expires_at").asc(nulls_last=True), "-updated_at")
        else:
            queryset = queryset.order_by(ordering, "-updated_at")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.now()
        warning_date = now + timedelta(days=7)
        all_listings = Listing.objects.filter(owner=user)
        status_counts = {row["status"]: row["total"] for row in all_listings.values("status").annotate(total=Count("id"))}
        totals = all_listings.aggregate(
            total_views=Coalesce(Sum("view_count"), 0),
            total_favorites=Coalesce(Sum("favorite_count"), 0),
        )
        attention_count = all_listings.filter(
            Q(status__in=[Listing.Status.REVIEW, Listing.Status.REJECTED, Listing.Status.EXPIRED])
            | Q(status=Listing.Status.PUBLISHED, expires_at__lte=warning_date)
        ).count()

        for listing in context["listings"]:
            listing.quality_profile = assess_listing_quality(listing)
            listing.quality_suggestion = next(iter(listing.quality_profile["suggestions"]), "")
            listing.expiry_days = None
            if listing.expires_at:
                seconds = (listing.expires_at - now).total_seconds()
                listing.expiry_days = max(0, int((seconds + 86399) // 86400))
            listing.show_renew_action = (
                listing.status == Listing.Status.PUBLISHED
                and listing.expiry_days is not None
                and listing.expiry_days <= 14
            )
            if listing.status == Listing.Status.REJECTED:
                listing.attention_note = listing.review_note or "İlan reddedildi; bilgileri düzenleyip yeniden incelemeye gönder."
            elif listing.status == Listing.Status.REVIEW:
                listing.attention_note = "İlan yayın öncesi inceleme sırasında."
            elif listing.status == Listing.Status.EXPIRED:
                listing.attention_note = "İlanın süresi doldu; bilgileri kontrol edip yeniden yayınla."
            elif listing.status == Listing.Status.PUBLISHED and listing.expiry_days is not None and listing.expiry_days <= 7:
                listing.attention_note = f"İlanın süresi {listing.expiry_days} gün içinde doluyor."
            else:
                listing.attention_note = ""

        context.update(
            {
                "status_filters": [
                    {"value": value, "label": label, "count": status_counts.get(value, 0)}
                    for value, label in self.STATUS_FILTERS
                ],
                "status_counts": status_counts,
                "status_filter": self.status_filter,
                "query": self.query,
                "sort_filter": self.sort_filter,
                "total_listing_count": all_listings.count(),
                "published_count": status_counts.get(Listing.Status.PUBLISHED, 0),
                "attention_count": attention_count,
                "total_views": totals["total_views"],
                "total_favorites": totals["total_favorites"],
                "total_offers": Offer.objects.filter(listing__owner=user).count(),
                "total_conversations": Conversation.objects.filter(listing__owner=user).count(),
                "bulk_max_count": 50,
            }
        )
        return context


def _apply_listing_status_action(listing, action, *, actor):
    previous_status = listing.status
    if action in {"publish", "renew"}:
        if previous_status in {Listing.Status.REVIEW, Listing.Status.REJECTED} and not actor.is_staff:
            return False, "İncelemede veya reddedilmiş ilan doğrudan yayınlanamaz."
        publishable = {
            Listing.Status.DRAFT,
            Listing.Status.PAUSED,
            Listing.Status.COMPLETED,
            Listing.Status.EXPIRED,
        }
        renewable = {Listing.Status.PUBLISHED, Listing.Status.PAUSED, Listing.Status.EXPIRED}
        if action == "publish" and previous_status not in publishable:
            return False, "Bu ilan mevcut durumunda yeniden yayınlanamaz."
        if action == "renew" and previous_status not in renewable:
            return False, "Bu ilan şu anda yenilenemez."
        listing.status = Listing.Status.PUBLISHED
        listing.published_at = timezone.now()
        listing.expires_at = timezone.now() + timedelta(days=60)
        listing.renewal_count += 1
        listing.save(update_fields=["status", "published_at", "expires_at", "renewal_count", "updated_at"])
        if action == "publish" and previous_status != Listing.Status.PUBLISHED:
            notify_listing_publication(listing)
        sync_listing_matches(listing, notify=False)
        return True, "İlan yeniden yayınlandı." if action == "publish" else "İlan 60 gün süreyle yenilendi."

    allowed = {
        "pause": ({Listing.Status.PUBLISHED}, Listing.Status.PAUSED, "İlan duraklatıldı."),
        "complete": (
            {Listing.Status.PUBLISHED, Listing.Status.PAUSED},
            Listing.Status.COMPLETED,
            "İlan sonuçlandı olarak işaretlendi.",
        ),
        "draft": (
            {
                Listing.Status.REVIEW,
                Listing.Status.PUBLISHED,
                Listing.Status.PAUSED,
                Listing.Status.COMPLETED,
                Listing.Status.REJECTED,
                Listing.Status.EXPIRED,
            },
            Listing.Status.DRAFT,
            "İlan taslağa alındı.",
        ),
    }
    if action not in allowed:
        return False, "Geçersiz işlem."
    valid_sources, target_status, message = allowed[action]
    if previous_status == target_status:
        return False, "İlan zaten bu durumda."
    if previous_status not in valid_sources:
        return False, "Bu işlem ilanın mevcut durumunda kullanılamaz."
    listing.status = target_status
    listing.save(update_fields=["status", "updated_at"])
    sync_listing_matches(listing, notify=False)
    return True, message


@login_required
@require_POST
def bulk_manage_listings(request):
    raw_ids = request.POST.getlist("listing_ids")[:50]
    try:
        listing_ids = {int(value) for value in raw_ids if value}
    except (TypeError, ValueError):
        listing_ids = set()
    action = request.POST.get("bulk_action", "").strip()
    fallback = reverse("listings:my_listings")
    redirect_to = _safe_next_url(request, fallback)
    if not listing_ids:
        messages.warning(request, "İşlem yapılacak en az bir ilan seçmelisin.")
        return redirect(redirect_to)
    if action not in {"pause", "publish", "renew", "complete", "draft"}:
        messages.error(request, "Toplu işlem seçimi geçersiz.")
        return redirect(redirect_to)

    listings = list(Listing.objects.filter(owner=request.user, pk__in=listing_ids).order_by("pk"))
    changed = 0
    skipped = 0
    with db_transaction.atomic():
        for listing in listings:
            applied, _message = _apply_listing_status_action(listing, action, actor=request.user)
            changed += int(applied)
            skipped += int(not applied)
    if changed:
        messages.success(request, f"{changed} ilan için toplu işlem tamamlandı.")
    if skipped:
        messages.warning(request, f"{skipped} ilan mevcut durumu nedeniyle değiştirilmedi.")
    return redirect(redirect_to)


class ListingCreateView(LoginRequiredMixin, CreateView):
    model = Listing
    form_class = ListingForm
    template_name = "listings/form.html"

    def get_draft(self):
        if not hasattr(self, "_draft"):
            draft_id = self.request.GET.get("draft") or self.request.POST.get("draft_id")
            self._draft = (
                ListingDraft.objects.filter(pk=draft_id, user=self.request.user).first()
                if draft_id
                else None
            )
        return self._draft

    def get_initial(self):
        initial = super().get_initial()
        draft = self.get_draft()
        if draft:
            initial.update(draft.data)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["server_draft"] = self.get_draft()
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get("submit_action") == "save_draft":
            draft = _save_listing_draft(request)
            messages.success(request, f"{draft.display_title} taslak olarak hesabına kaydedildi.")
            return redirect("listings:drafts")
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.status = (
            Listing.Status.PUBLISHED
            if settings.AUTO_PUBLISH_LISTINGS or self.request.user.is_staff
            else Listing.Status.REVIEW
        )
        response = super().form_valid(form)
        _save_images(self.object, form.cleaned_data.get("images", []))
        safety_profile = assess_listing_safety(
            self.object, price_guide=build_price_guide(self.object, exclude_pk=self.object.pk)
        )
        if safety_profile["requires_review"] and self.object.status == Listing.Status.PUBLISHED and not self.request.user.is_staff:
            self.object.status = Listing.Status.REVIEW
            self.object.published_at = None
            self.object.expires_at = None
            self.object.save(update_fields=["status", "published_at", "expires_at", "updated_at"])
        record_listing_risks(self.object, safety_profile=safety_profile)
        analysis_id = self.request.POST.get("ai_analysis_id", "").strip()
        if analysis_id:
            try:
                from apps.ai_listing.services.analysis import record_analysis_application
                record_analysis_application(analysis_id=analysis_id, user=self.request.user, listing=self.object)
            except Exception:
                import logging
                logging.getLogger(__name__).exception("AI analiz uygulama kaydı oluşturulamadı.")
        if self.object.management_mode == Listing.ManagementMode.FULL:
            ManagedRequest.objects.get_or_create(
                listing=self.object,
                defaults={"customer": self.request.user},
            )
        if self.object.status == Listing.Status.REVIEW:
            messages.success(self.request, "İlanın kaydedildi ve güvenlik incelemesine gönderildi.")
        else:
            notify_listing_publication(self.object)
            messages.success(self.request, "İlanın yayınlandı.")
        draft = self.get_draft()
        if draft:
            draft.delete()
        return response


class ListingUpdateView(OwnerListingMixin, UpdateView):
    model = Listing
    form_class = ListingForm
    template_name = "listings/form.html"

    def get_draft(self):
        if not hasattr(self, "_draft"):
            draft_id = self.request.GET.get("draft") or self.request.POST.get("draft_id")
            self._draft = (
                ListingDraft.objects.filter(
                    pk=draft_id,
                    user=self.request.user,
                    source_listing=self.get_object(),
                ).first()
                if draft_id
                else None
            )
        return self._draft

    def get_initial(self):
        initial = super().get_initial()
        draft = self.get_draft()
        if draft:
            initial.update(draft.data)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["server_draft"] = self.get_draft()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.POST.get("submit_action") == "save_draft":
            draft = _save_listing_draft(request, source_listing=self.object)
            messages.success(request, f"{draft.display_title} düzenleme taslağı olarak kaydedildi.")
            return redirect("listings:drafts")
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        previous_price = Listing.objects.only("price").get(pk=self.object.pk).price
        if not self.request.user.is_staff:
            form.instance.status = Listing.Status.REVIEW
            form.instance.review_note = ""
        response = super().form_valid(form)
        if self.object.status != Listing.Status.PUBLISHED:
            sync_listing_matches(self.object, notify=False)
        record_price_change(
            listing=self.object,
            old_price=previous_price,
            new_price=self.object.price,
            actor=self.request.user,
        )
        _save_images(self.object, form.cleaned_data.get("images", []))
        safety_profile = assess_listing_safety(
            self.object, price_guide=build_price_guide(self.object, exclude_pk=self.object.pk)
        )
        record_listing_risks(self.object, safety_profile=safety_profile)
        if self.object.management_mode == Listing.ManagementMode.FULL:
            ManagedRequest.objects.get_or_create(listing=self.object, defaults={"customer": self.request.user})
        messages.success(self.request, "İlan değişiklikleri kaydedildi.")
        draft = self.get_draft()
        if draft:
            draft.delete()
        return response


class ListingDeleteView(OwnerListingMixin, DeleteView):
    model = Listing
    template_name = "listings/confirm_delete.html"
    success_url = reverse_lazy("accounts:dashboard")

    def form_valid(self, form):
        messages.success(self.request, "İlan silindi.")
        return super().form_valid(form)


@login_required
@require_POST
def change_listing_status(request, slug, action):
    listing = get_object_or_404(Listing, slug=slug, owner=request.user)
    applied, message = _apply_listing_status_action(listing, action, actor=request.user)
    if applied:
        messages.success(request, message)
    else:
        messages.warning(request, message)
    return redirect(_safe_next_url(request, reverse("accounts:dashboard")))


@login_required
@require_POST
def toggle_favorite(request, slug):
    listing = get_object_or_404(Listing, _active_listing_q(), slug=slug)
    favorite, created = Favorite.objects.get_or_create(user=request.user, listing=listing)
    if created:
        Listing.objects.filter(pk=listing.pk).update(favorite_count=F("favorite_count") + 1)
        messages.success(request, "İlan favorilerine eklendi.")
    else:
        favorite.delete()
        Listing.objects.filter(pk=listing.pk, favorite_count__gt=0).update(favorite_count=F("favorite_count") - 1)
        messages.info(request, "İlan favorilerinden çıkarıldı.")
    return redirect(_safe_next_url(request, listing.get_absolute_url()))


class CompareListView(TemplateView):
    template_name = "listings/compare.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        compare_ids = _compare_ids(self.request)
        queryset = (
            Listing.objects.filter(_active_listing_q(), pk__in=compare_ids)
            .select_related("owner", "category")
            .prefetch_related("images", "price_history")
        )
        item_map = {item.pk: item for item in queryset}
        listings = [item_map[item_id] for item_id in compare_ids if item_id in item_map]
        context["listings"] = listings
        context["compare_ids"] = set(compare_ids)
        context["favorite_ids"] = (
            set(Favorite.objects.filter(user=self.request.user).values_list("listing_id", flat=True))
            if self.request.user.is_authenticated
            else set()
        )
        labels = []
        detail_maps = []
        for listing in listings:
            item_map = dict(listing.detail_items)
            detail_maps.append(item_map)
            for label in item_map:
                if label not in labels:
                    labels.append(label)
        context["comparison_rows"] = [
            {"label": label, "values": [item_map.get(label, "—") for item_map in detail_maps]}
            for label in labels
        ]
        return context


@require_POST
def toggle_compare(request, slug):
    listing = get_object_or_404(Listing, _active_listing_q(), slug=slug)
    compare_ids = _compare_ids(request)
    if listing.pk in compare_ids:
        compare_ids.remove(listing.pk)
        messages.info(request, "İlan karşılaştırmadan çıkarıldı.")
    else:
        existing = Listing.objects.filter(pk__in=compare_ids).first() if compare_ids else None
        if existing and existing.kind != listing.kind:
            messages.warning(request, "Yalnız aynı ilan türündeki seçenekler karşılaştırılabilir.")
            return redirect(_safe_next_url(request, listing.get_absolute_url()))
        if len(compare_ids) >= 4:
            messages.warning(request, "Aynı anda en fazla 4 ilan karşılaştırılabilir.")
            return redirect(_safe_next_url(request, reverse("listings:compare")))
        compare_ids.append(listing.pk)
        messages.success(request, "İlan karşılaştırmaya eklendi.")
    request.session["compare_listing_ids"] = compare_ids
    request.session.modified = True
    return redirect(_safe_next_url(request, listing.get_absolute_url()))


class FavoriteListView(LoginRequiredMixin, ListView):
    template_name = "listings/favorites.html"
    context_object_name = "favorite_items"
    paginate_by = 24

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user, listing__status=Listing.Status.PUBLISHED).filter(Q(listing__expires_at__isnull=True) | Q(listing__expires_at__gt=timezone.now())).select_related(
            "listing", "listing__category", "listing__owner"
        ).prefetch_related("listing__images")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["favorite_ids"] = set(item.listing_id for item in context["favorite_items"])
        context["compare_ids"] = set(_compare_ids(self.request))
        return context


@login_required
@require_POST
def set_cover_image(request, slug, image_id):
    listing = get_object_or_404(Listing, slug=slug, owner=request.user)
    image = get_object_or_404(ListingImage, pk=image_id, listing=listing)
    with db_transaction.atomic():
        listing.images.update(is_cover=False)
        image.is_cover = True
        image.sort_order = 0
        image.save(update_fields=["is_cover", "sort_order"])
    messages.success(request, "Kapak fotoğrafı güncellendi.")
    return redirect("listings:update", slug=listing.slug)


@login_required
@require_POST
def delete_listing_image(request, slug, image_id):
    listing = get_object_or_404(Listing, slug=slug, owner=request.user)
    image = get_object_or_404(ListingImage, pk=image_id, listing=listing)
    was_cover = image.is_cover
    image.delete()
    if was_cover:
        next_image = listing.images.first()
        if next_image:
            next_image.is_cover = True
            next_image.save(update_fields=["is_cover"])
    messages.success(request, "Fotoğraf silindi.")
    return redirect("listings:update", slug=listing.slug)


@login_required
@require_POST
def reorder_listing_images(request, slug):
    listing = get_object_or_404(Listing, slug=slug, owner=request.user)
    raw_ids = request.POST.get("image_order", "")
    try:
        ids = [int(value) for value in raw_ids.split(",") if value.strip()]
    except ValueError:
        messages.error(request, "Fotoğraf sırası geçersiz.")
        return redirect("listings:update", slug=listing.slug)
    valid_ids = set(listing.images.values_list("id", flat=True))
    if set(ids) != valid_ids:
        messages.error(request, "Fotoğraf sırası eksik veya geçersiz.")
        return redirect("listings:update", slug=listing.slug)
    for index, image_id in enumerate(ids):
        ListingImage.objects.filter(pk=image_id, listing=listing).update(sort_order=index)
    messages.success(request, "Fotoğraf sırası kaydedildi.")
    return redirect("listings:update", slug=listing.slug)


class OfferCenterView(LoginRequiredMixin, TemplateView):
    template_name = "listings/offer_center.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        all_offers = Offer.objects.filter(Q(sender=user) | Q(listing__owner=user))
        base = (
            all_offers.select_related("listing", "listing__owner", "sender", "last_actor")
            .prefetch_related("events__actor", "listing__images")
            .order_by("-updated_at")
        )
        status_filter = self.request.GET.get("status", "").strip()
        if status_filter in {value for value, _ in Offer.Status.choices}:
            base = base.filter(status=status_filter)
        else:
            status_filter = ""

        direction = self.request.GET.get("direction", "all").strip()
        if direction == "incoming":
            base = base.filter(listing__owner=user)
        elif direction == "outgoing":
            base = base.filter(sender=user)
        elif direction == "action":
            base = base.filter(status=Offer.Status.PENDING).filter(
                Q(listing__owner=user, last_actor=F("sender"))
                | Q(listing__owner=user, last_actor__isnull=True)
                | Q(sender=user, last_actor=F("listing__owner"))
            )
        else:
            direction = "all"

        query = self.request.GET.get("q", "").strip()
        if query:
            base = base.filter(
                Q(listing__title__icontains=query)
                | Q(sender__username__icontains=query)
                | Q(sender__first_name__icontains=query)
                | Q(sender__last_name__icontains=query)
                | Q(listing__owner__username__icontains=query)
                | Q(listing__owner__first_name__icontains=query)
                | Q(listing__owner__last_name__icontains=query)
            )

        offer_rows = list(base[:60])
        if offer_rows:
            listing_ids = {offer.listing_id for offer in offer_rows}
            buyer_ids = {offer.sender_id for offer in offer_rows}
            conversation_map = {
                (conversation.listing_id, conversation.buyer_id): conversation.pk
                for conversation in Conversation.objects.filter(
                    listing_id__in=listing_ids,
                    buyer_id__in=buyer_ids,
                ).only("pk", "listing_id", "buyer_id")
            }
            for offer in offer_rows:
                offer.conversation_pk = conversation_map.get((offer.listing_id, offer.sender_id))

        action_filter = Q(status=Offer.Status.PENDING) & (
            Q(listing__owner=user, last_actor=F("sender"))
            | Q(listing__owner=user, last_actor__isnull=True)
            | Q(sender=user, last_actor=F("listing__owner"))
        )
        context["offers"] = offer_rows
        context["status_filter"] = status_filter
        context["direction"] = direction
        context["query"] = query
        context["focus_offer_id"] = _safe_int(self.request.GET.get("focus"))
        context["counter_form"] = CounterOfferForm()
        context["offer_summary"] = {
            "all": all_offers.count(),
            "incoming": all_offers.filter(listing__owner=user).count(),
            "outgoing": all_offers.filter(sender=user).count(),
            "action": all_offers.filter(action_filter).count(),
            "pending": all_offers.filter(status=Offer.Status.PENDING).count(),
        }
        transaction_qs = (
            Transaction.objects.filter(Q(buyer=user) | Q(seller=user))
            .select_related("listing", "buyer", "seller")
            .prefetch_related("listing__images")
            .order_by("-updated_at")
        )
        context["active_transaction_count"] = transaction_qs.filter(
            status__in=[Transaction.Status.AGREED, Transaction.Status.DELIVERY, Transaction.Status.DISPUTED]
        ).count()
        context["transactions"] = transaction_qs[:20]
        return context


@login_required
@require_POST
def counter_offer_action(request, pk):
    offer = get_object_or_404(
        Offer.objects.select_related("listing", "listing__owner", "sender", "last_actor"),
        pk=pk,
    )
    form = CounterOfferForm(request.POST)
    fallback = f"{reverse('listings:offer_center')}?focus={offer.pk}"
    if not form.is_valid():
        messages.error(request, "Karşı teklif bilgilerini kontrol et.")
        return redirect(_safe_next_url(request, fallback))
    try:
        counter_offer(
            offer=offer,
            actor=request.user,
            amount=form.cleaned_data["amount"],
            message=form.cleaned_data["message"],
        )
        messages.success(request, "Karşı teklif gönderildi.")
    except PermissionError:
        raise Http404
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect(_safe_next_url(request, fallback))


@login_required
@require_POST
def offer_action(request, pk, action):
    offer = get_object_or_404(Offer.objects.select_related("listing", "sender", "listing__owner", "last_actor"), pk=pk)
    fallback = f"{reverse('listings:offer_center')}?focus={offer.pk}"
    try:
        if action == "accept":
            transaction = accept_offer(offer=offer, actor=request.user)
            messages.success(request, "Teklif kabul edildi ve güvenli işlem kaydı açıldı.")
            return redirect(transaction.get_absolute_url())
        if action == "reject":
            reject_offer(offer=offer, actor=request.user)
            messages.success(request, "Teklif reddedildi.")
        elif action == "withdraw":
            if offer.sender_id != request.user.pk or offer.status != Offer.Status.PENDING:
                raise PermissionError
            offer.status = Offer.Status.WITHDRAWN
            offer.responded_at = timezone.now()
            offer.save(update_fields=["status", "responded_at", "updated_at"])
            create_offer_event(
                offer=offer,
                actor=request.user,
                event_type=OfferEvent.Type.WITHDRAWN,
                amount=offer.amount,
                message="Teklif geri çekildi.",
            )
            messages.success(request, "Teklifin geri çekildi.")
        else:
            messages.error(request, "Geçersiz teklif işlemi.")
    except PermissionError:
        raise Http404
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect(_safe_next_url(request, fallback))


class TransactionDetailView(LoginRequiredMixin, DetailView):
    model = Transaction
    template_name = "listings/transaction_detail.html"
    context_object_name = "transaction"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        user = self.request.user
        qs = (
            Transaction.objects.select_related("listing", "offer", "buyer", "seller")
            .prefetch_related("reviews", "events__actor")
        )
        if user.is_staff:
            return qs
        return qs.filter(Q(buyer=user) | Q(seller=user))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        is_participant = self.object.is_participant(user)
        my_review = self.object.reviews.filter(reviewer=user).first() if is_participant else None
        context["is_participant"] = is_participant
        context["is_buyer"] = bool(is_participant and user.pk == self.object.buyer_id)
        context["is_seller"] = bool(is_participant and user.pk == self.object.seller_id)
        context["review_window_open"] = bool(is_participant and review_window_is_open(self.object))
        context["review_form"] = ReviewForm() if is_participant and not my_review else None
        context["handover_form"] = HandoverCodeForm()
        context["dispute_form"] = TransactionDisputeForm(instance=self.object) if is_participant else None
        context["my_review"] = my_review
        context["other_user"] = (
            self.object.seller if user.pk == self.object.buyer_id else self.object.buyer
        ) if is_participant else None
        return context


@login_required
@require_POST
def transaction_action(request, public_id, action):
    transaction = get_object_or_404(
        Transaction.objects.select_related("buyer", "seller", "listing"),
        public_id=public_id,
    )
    if not transaction.is_participant(request.user):
        raise Http404
    if transaction.status in {Transaction.Status.COMPLETED, Transaction.Status.CANCELLED}:
        messages.warning(request, "Bu işlem kapanmış durumda.")
        return redirect(transaction.get_absolute_url())

    try:
        if action == "delivery":
            start_transaction_delivery(transaction=transaction, actor=request.user)
            messages.success(request, "İşlem teslim / hizmet aşamasına geçirildi.")
        elif action == "generate_code":
            _, raw_code = issue_handover_code(transaction=transaction, actor=request.user)
            messages.success(
                request,
                f"Teslim kodun: {raw_code}. Bu kod 15 dakika geçerlidir; yalnız teslim anında satıcıya söyle.",
            )
        elif action == "verify_code":
            form = HandoverCodeForm(request.POST)
            if not form.is_valid():
                messages.error(request, "6 haneli teslim kodunu kontrol et.")
            else:
                verify_handover_code(
                    transaction=transaction, actor=request.user, raw_code=form.cleaned_data["code"]
                )
                messages.success(request, "Teslim kodu doğrulandı. Satıcı onayı kaydedildi.")
        elif action == "confirm":
            confirm_transaction(transaction=transaction, actor=request.user)
            messages.success(request, "Tamamlama onayın kaydedildi.")
        elif action == "cancel":
            if transaction.status != Transaction.Status.AGREED:
                messages.error(request, "Teslim aşamasındaki işlem tek taraflı iptal edilemez; uyuşmazlık bildir.")
            else:
                transaction.status = Transaction.Status.CANCELLED
                transaction.cancelled_at = timezone.now()
                transaction.save(update_fields=["status", "cancelled_at", "updated_at"])
                record_transaction_event(
                    transaction=transaction, actor=request.user,
                    event_type=TransactionEvent.Type.CANCELLED, note="İşlem teslim başlamadan iptal edildi.",
                )
                Listing.objects.filter(pk=transaction.listing_id).update(
                    status=Listing.Status.PAUSED, updated_at=timezone.now(),
                )
                sync_listing_matches(transaction.listing, notify=False)
                messages.success(request, "İşlem iptal edildi.")
        elif action == "dispute":
            form = TransactionDisputeForm(request.POST, instance=transaction)
            if form.is_valid():
                transaction = form.save(commit=False)
                transaction.status = Transaction.Status.DISPUTED
                transaction.save(update_fields=["status", "dispute_reason", "updated_at"])
                record_transaction_event(
                    transaction=transaction, actor=request.user,
                    event_type=TransactionEvent.Type.DISPUTED, note="Taraflardan biri destek incelemesi istedi.",
                )
                for staff_user in transaction.seller.__class__.objects.filter(is_staff=True, is_active=True)[:20]:
                    create_notification(
                        user=staff_user, actor=request.user, listing=transaction.listing,
                        notification_type=Notification.Type.SYSTEM, title="Yeni işlem uyuşmazlığı",
                        body=f"{transaction.listing.title} işlemi için inceleme istendi.",
                        link=transaction.get_absolute_url(),
                    )
                messages.warning(request, "Uyuşmazlık kaydı açıldı. Destek ekibi inceleyecek.")
            else:
                messages.error(request, "Uyuşmazlık açıklamasını kontrol et.")
        else:
            messages.error(request, "Geçersiz işlem.")
    except PermissionError:
        raise Http404
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect(transaction.get_absolute_url())


@login_required
@require_POST
def moderate_transaction(request, public_id, action):
    if not request.user.is_staff:
        raise Http404
    transaction = get_object_or_404(
        Transaction.objects.select_related("buyer", "seller", "listing"),
        public_id=public_id, status=Transaction.Status.DISPUTED,
    )
    now = timezone.now()
    if action == "complete":
        transaction.buyer_confirmed = True
        transaction.seller_confirmed = True
        transaction.buyer_confirmed_at = transaction.buyer_confirmed_at or now
        transaction.seller_confirmed_at = transaction.seller_confirmed_at or now
        transaction.status = Transaction.Status.DELIVERY
        transaction.save(
            update_fields=[
                "buyer_confirmed", "seller_confirmed", "buyer_confirmed_at",
                "seller_confirmed_at", "status", "updated_at",
            ]
        )
        record_transaction_event(
            transaction=transaction, actor=request.user, event_type=TransactionEvent.Type.MODERATED,
            note="Destek ekibi uyuşmazlığı tamamlandı olarak sonuçlandırdı.",
        )
        finalize_transaction(transaction)
        title = "Uyuşmazlık tamamlandı olarak çözüldü"
        body = "Destek ekibi işlem kaydını tamamlandı olarak kapattı."
        messages.success(request, "Uyuşmazlık tamamlandı olarak kapatıldı.")
    elif action == "cancel":
        transaction.status = Transaction.Status.CANCELLED
        transaction.cancelled_at = now
        transaction.save(update_fields=["status", "cancelled_at", "updated_at"])
        record_transaction_event(
            transaction=transaction, actor=request.user, event_type=TransactionEvent.Type.MODERATED,
            note="Destek ekibi uyuşmazlığı iptal ile sonuçlandırdı.",
        )
        Listing.objects.filter(pk=transaction.listing_id).update(
            status=Listing.Status.PAUSED, updated_at=now,
        )
        title = "Uyuşmazlık iptal ile sonuçlandı"
        body = "Destek ekibi işlem kaydını iptal ederek ilanı duraklattı."
        messages.success(request, "Uyuşmazlık iptal ile kapatıldı.")
    else:
        messages.error(request, "Geçersiz moderasyon işlemi.")
        return redirect(transaction.get_absolute_url())
    for recipient in (transaction.buyer, transaction.seller):
        create_notification(
            user=recipient, actor=request.user, listing=transaction.listing,
            notification_type=Notification.Type.SYSTEM, title=title, body=body,
            link=transaction.get_absolute_url(),
        )
    return redirect(transaction.get_absolute_url())


@login_required
@require_POST
@db_transaction.atomic
def create_review(request, public_id):
    transaction = get_object_or_404(
        Transaction.objects.select_for_update().select_related("buyer", "seller", "listing"),
        public_id=public_id,
    )
    if not transaction.is_participant(request.user) or not review_window_is_open(transaction):
        raise Http404
    if Review.objects.filter(transaction=transaction, reviewer=request.user).exists():
        messages.warning(request, "Bu işlem için daha önce değerlendirme yaptın.")
        return redirect(transaction.get_absolute_url())
    form = ReviewForm(request.POST)
    if form.is_valid():
        now = timezone.now()
        other_review = transaction.reviews.exclude(reviewer=request.user).first()
        review = form.save(commit=False)
        review.transaction = transaction
        review.reviewer = request.user
        review.reviewed_user = transaction.seller if request.user.pk == transaction.buyer_id else transaction.buyer
        review.is_visible = bool(other_review)
        review.published_at = now if other_review else None
        review.save()
        if other_review:
            if not other_review.is_visible:
                Review.objects.filter(pk=other_review.pk).update(is_visible=True, published_at=now)
                published_reviews = (review, other_review)
                success_message = "İki taraf da değerlendirdi; yorumlar aynı anda yayınlandı."
            else:
                published_reviews = (review,)
                success_message = "Değerlendirmen yayınlandı."
            for reviewed_user in {item.reviewed_user_id: item.reviewed_user for item in published_reviews}.values():
                refresh_user_rating(reviewed_user)
            for item in published_reviews:
                create_notification(
                    user=item.reviewed_user, actor=item.reviewer, listing=transaction.listing,
                    notification_type=Notification.Type.REVIEW, title="İşlem değerlendirmesi yayınlandı",
                    body=f"Tamamlanan işlem için {item.rating}/5 puanlık değerlendirme yayınlandı.",
                    link=reverse("accounts:public_profile", kwargs={"username": item.reviewed_user.username}),
                )
            messages.success(request, success_message)
        else:
            create_notification(
                user=review.reviewed_user, actor=request.user, listing=transaction.listing,
                notification_type=Notification.Type.REVIEW, title="Değerlendirme süreci başladı",
                body="Diğer taraf değerlendirmesini gönderdi. Sen de yazdığında iki yorum aynı anda yayınlanacak.",
                link=transaction.get_absolute_url(),
            )
            messages.success(
                request,
                "Değerlendirmen kaydedildi. Diğer taraf da yazdığında veya 7 gün dolduğunda yayınlanacak.",
            )
    else:
        messages.error(request, "Puan ve yorum alanlarını kontrol et.")
    return redirect(transaction.get_absolute_url())


@login_required
@require_POST
def start_conversation(request, slug):
    listing = get_object_or_404(Listing, _active_listing_q(), slug=slug)
    if not consume_rate_limit(request, "message", limit=12, period=600):
        messages.error(request, "Kısa sürede çok fazla mesaj gönderdin. Birkaç dakika sonra tekrar dene.")
        return redirect(listing.get_absolute_url())
    if listing.owner == request.user:
        messages.warning(request, "Kendi ilanına mesaj gönderemezsin.")
        return redirect(listing.get_absolute_url())
    if _blocked_between(request.user, listing.owner):
        messages.error(request, "Bu kullanıcıyla mesajlaşma kullanılamıyor.")
        return redirect(listing.get_absolute_url())
    form = MessageForm(request.POST, request.FILES)
    if not form.is_valid():
        request.session[f"pending_message_{listing.pk}"] = {
            "body": (request.POST.get("body") or "")[:1600],
        }
        safety_result = getattr(form, "safety_result", None)
        if safety_result and safety_result.requires_confirmation:
            messages.warning(
                request,
                "Mesajın güvenlik uyarısı içeriyor. Metni kontrol edip onay kutusunu işaretleyerek yeniden gönder.",
            )
        else:
            messages.error(request, "Mesajını kontrol edip yeniden gönder.")
        return redirect(f"{listing.get_absolute_url()}#message-box")
    conversation, _ = Conversation.objects.get_or_create(
        listing=listing,
        buyer=request.user,
        defaults={"seller": listing.owner},
    )
    if conversation.buyer_archived or conversation.seller_archived:
        conversation.buyer_archived = False
        conversation.seller_archived = False
        conversation.save(update_fields=["buyer_archived", "seller_archived", "updated_at"])
    message = form.save(commit=False)
    message.conversation = conversation
    message.sender = request.user
    message.save()
    record_message_risk(message)
    create_notification(
        user=listing.owner,
        actor=request.user,
        listing=listing,
        notification_type=Notification.Type.MESSAGE,
        title="İlanın hakkında yeni mesaj",
        body=safe_notification_preview(request.user.display_name, message.body),
        link=reverse("listings:conversation_detail", kwargs={"pk": conversation.pk}),
    )
    messages.success(request, "Mesajın ilan sahibine gönderildi.")
    return redirect("listings:conversation_detail", pk=conversation.pk)


class AppointmentListView(LoginRequiredMixin, ListView):
    template_name = "listings/appointment_list.html"
    context_object_name = "appointments"
    paginate_by = 30

    def get_queryset(self):
        user = self.request.user
        queryset = (
            Appointment.objects.filter(Q(proposer=user) | Q(invitee=user))
            .select_related("listing", "proposer", "invitee", "conversation")
            .order_by("starts_at", "-created_at")
        )
        mode = self.request.GET.get("mode", "upcoming")
        if mode == "pending":
            queryset = queryset.filter(
                status=Appointment.Status.PENDING,
                starts_at__gte=timezone.now(),
            )
        elif mode == "past":
            queryset = queryset.filter(starts_at__lt=timezone.now()).order_by("-starts_at", "-created_at")
        elif mode == "all":
            pass
        else:
            mode = "upcoming"
            queryset = queryset.filter(
                status__in=[Appointment.Status.PENDING, Appointment.Status.ACCEPTED],
                starts_at__gte=timezone.now(),
            )
        self.mode = mode
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mode"] = getattr(self, "mode", "upcoming")
        context["highlight"] = self.request.GET.get("highlight", "")
        context["pending_invites"] = Appointment.objects.filter(
            invitee=self.request.user,
            status=Appointment.Status.PENDING,
            starts_at__gte=timezone.now(),
        ).count()
        return context


@login_required
@require_POST
def create_conversation_appointment(request, pk):
    conversation = get_object_or_404(
        Conversation.objects.select_related("listing", "buyer", "seller").filter(
            Q(buyer=request.user) | Q(seller=request.user)
        ),
        pk=pk,
    )
    other_user = conversation.other_participant(request.user)
    if _blocked_between(request.user, other_user):
        messages.error(request, "Engellenen kullanıcıyla randevu oluşturulamaz.")
        return redirect("listings:conversation_detail", pk=conversation.pk)
    if not consume_rate_limit(request, "appointment-create", limit=8, period=3600):
        messages.error(request, "Kısa sürede çok fazla randevu önerisi oluşturdun. Bir süre sonra tekrar dene.")
        return redirect("listings:conversation_detail", pk=conversation.pk)
    form = AppointmentForm(request.POST)
    if not form.is_valid():
        first_error = next(
            (str(error) for errors in form.errors.values() for error in errors),
            "Randevu bilgilerini kontrol et.",
        )
        messages.error(request, first_error)
        return redirect("listings:conversation_detail", pk=conversation.pk)
    try:
        appointment = create_appointment(
            conversation=conversation,
            proposer=request.user,
            cleaned_data=form.cleaned_data,
        )
        messages.success(request, "Randevu önerisi gönderildi. Diğer tarafın onayı bekleniyor.")
        return redirect(appointment.get_absolute_url())
    except PermissionError:
        raise Http404
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("listings:conversation_detail", pk=conversation.pk)


@login_required
@require_POST
def appointment_action(request, public_id, action):
    appointment = get_object_or_404(
        Appointment.objects.select_related("listing", "proposer", "invitee", "conversation"),
        public_id=public_id,
    )
    if not appointment.is_participant(request.user):
        raise Http404
    try:
        respond_appointment(appointment=appointment, actor=request.user, action=action)
        message_map = {
            "accept": "Randevu onaylandı.",
            "decline": "Randevu reddedildi.",
            "cancel": "Randevu iptal edildi.",
        }
        messages.success(request, message_map.get(action, "Randevu güncellendi."))
    except PermissionError:
        raise Http404
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect(_safe_next_url(request, appointment.get_absolute_url()))


def _conversation_action_offer_ids(user):
    queryset = Offer.objects.filter(status=Offer.Status.PENDING).filter(
        Q(listing__owner=user, last_actor=F("sender"))
        | Q(listing__owner=user, last_actor__isnull=True)
        | Q(sender=user, last_actor=F("listing__owner"))
    )
    return list(queryset.values_list("listing_id", "sender_id"))


class ConversationListView(LoginRequiredMixin, ListView):
    template_name = "listings/conversation_list.html"
    context_object_name = "conversations"
    paginate_by = 30

    def get_queryset(self):
        user = self.request.user
        mode = self.request.GET.get("mode", "all").strip()
        allowed_modes = {"all", "action", "unread", "buying", "selling", "archived"}
        if mode not in allowed_modes:
            mode = "all"
        self.mode = mode

        participant_q = Q(buyer=user) | Q(seller=user)
        if mode == "archived":
            visibility_q = Q(buyer=user, buyer_archived=True) | Q(seller=user, seller_archived=True)
        else:
            visibility_q = Q(buyer=user, buyer_archived=False) | Q(seller=user, seller_archived=False)

        queryset = (
            Conversation.objects.filter(participant_q, visibility_q)
            .select_related("listing", "buyer", "seller")
            .prefetch_related("messages", "listing__images")
            .annotate(
                unread_count=Coalesce(
                    Count("messages", filter=Q(messages__is_read=False) & ~Q(messages__sender=user)),
                    0,
                )
            )
            .order_by("-updated_at")
        )
        if mode == "buying":
            queryset = queryset.filter(buyer=user)
        elif mode == "selling":
            queryset = queryset.filter(seller=user)
        elif mode == "unread":
            queryset = queryset.filter(unread_count__gt=0)
        elif mode == "action":
            action_pairs = _conversation_action_offer_ids(user)
            action_q = Q(unread_count__gt=0)
            for listing_id, buyer_id in action_pairs:
                action_q |= Q(listing_id=listing_id, buyer_id=buyer_id)
            queryset = queryset.filter(action_q)

        query = self.request.GET.get("q", "").strip()
        self.query = query
        if query:
            queryset = queryset.filter(
                Q(listing__title__icontains=query)
                | Q(buyer__username__icontains=query)
                | Q(buyer__first_name__icontains=query)
                | Q(buyer__last_name__icontains=query)
                | Q(seller__username__icontains=query)
                | Q(seller__first_name__icontains=query)
                | Q(seller__last_name__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        active = Conversation.objects.filter(
            Q(buyer=user, buyer_archived=False) | Q(seller=user, seller_archived=False)
        )
        action_pairs = _conversation_action_offer_ids(user)
        action_conversation_ids = set()
        if action_pairs:
            pair_q = Q(pk__in=[])
            for listing_id, buyer_id in action_pairs:
                pair_q |= Q(listing_id=listing_id, buyer_id=buyer_id)
            action_conversation_ids = set(active.filter(pair_q).values_list("pk", flat=True))
        unread_ids = set(
            active.filter(messages__is_read=False)
            .exclude(messages__sender=user)
            .values_list("pk", flat=True)
        )
        context["mode"] = getattr(self, "mode", "all")
        context["query"] = getattr(self, "query", "")
        context["conversation_summary"] = {
            "all": active.count(),
            "action": len(action_conversation_ids | unread_ids),
            "unread": len(unread_ids),
            "buying": active.filter(buyer=user).count(),
            "selling": active.filter(seller=user).count(),
            "archived": Conversation.objects.filter(
                Q(buyer=user, buyer_archived=True) | Q(seller=user, seller_archived=True)
            ).count(),
        }
        page_rows = list(context.get("conversations") or [])
        if page_rows:
            pair_map = {(row.listing_id, row.buyer_id): row for row in page_rows}
            pending_offers = Offer.objects.filter(
                status=Offer.Status.PENDING,
                listing_id__in={row.listing_id for row in page_rows},
                sender_id__in={row.buyer_id for row in page_rows},
            ).select_related("last_actor", "listing__owner", "sender")
            for offer in pending_offers:
                row = pair_map.get((offer.listing_id, offer.sender_id))
                if row is not None:
                    row.pending_offer = offer
                    row.offer_needs_my_action = offer.can_respond(user)
        return context


class ConversationDetailView(LoginRequiredMixin, FormMixin, DetailView):
    model = Conversation
    template_name = "listings/conversation_detail.html"
    context_object_name = "conversation"
    form_class = MessageForm

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(Q(buyer=user) | Q(seller=user)).select_related(
            "listing", "buyer", "seller", "listing__owner", "listing__category"
        )

    def get_success_url(self):
        return reverse("listings:conversation_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        other_user = self.object.other_participant(user)
        blocked_between = _blocked_between(user, other_user)
        context["other_user"] = other_user
        context["blocked_between"] = blocked_between
        context["other_user_trust_profile"] = build_trust_profile(other_user)

        show_full_history = self.request.GET.get("history") == "all"
        message_limit = 500 if show_full_history else 120
        recent_messages = list(
            self.object.messages.select_related("sender").order_by("-created_at")[:message_limit]
        )
        recent_messages.reverse()
        context["thread_messages"] = recent_messages
        context["message_total_count"] = self.object.messages.count()
        context["show_full_history"] = show_full_history
        context["history_truncated"] = context["message_total_count"] > len(recent_messages)

        active_offer = (
            Offer.objects.filter(listing=self.object.listing, sender=self.object.buyer)
            .select_related("last_actor", "listing__owner", "sender")
            .prefetch_related("events__actor")
            .order_by("-updated_at")
            .first()
        )
        context["active_offer"] = active_offer
        context["offer_form"] = OfferForm()
        context["can_make_offer"] = bool(
            user.pk == self.object.buyer_id
            and self.object.listing.status == Listing.Status.PUBLISHED
            and not blocked_between
            and not (active_offer and active_offer.status == Offer.Status.PENDING)
        )
        context["offer_needs_my_action"] = bool(
            active_offer and active_offer.status == Offer.Status.PENDING and active_offer.can_respond(user)
        )
        context["conversation_role_label"] = "Alıcı" if user.pk == self.object.buyer_id else "Satıcı"
        context["is_archived_for_user"] = (
            self.object.buyer_archived if user.pk == self.object.buyer_id else self.object.seller_archived
        )

        initial = {
            "appointment_type": Appointment.Type.IN_PERSON,
            "duration_minutes": 30,
            "city": self.object.listing.city,
            "district": self.object.listing.district,
        }
        context["appointment_form"] = AppointmentForm(initial=initial)
        context["conversation_appointments"] = self.object.appointments.select_related(
            "proposer", "invitee"
        ).filter(
            status__in=[Appointment.Status.PENDING, Appointment.Status.ACCEPTED],
            starts_at__gte=timezone.now(),
        ).order_by("starts_at")[:3]
        return context

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        self.object.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        return response

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        other_user = self.object.other_participant(request.user)
        if _blocked_between(request.user, other_user):
            messages.error(request, "Engellenen kullanıcıyla mesaj gönderilemez.")
            return redirect(self.get_success_url())
        if not consume_rate_limit(request, "message", limit=20, period=600):
            messages.error(request, "Kısa sürede çok fazla mesaj gönderdin. Birkaç dakika sonra tekrar dene.")
            return redirect(self.get_success_url())
        form = self.get_form()
        if form.is_valid():
            if self.object.buyer_archived or self.object.seller_archived:
                self.object.buyer_archived = False
                self.object.seller_archived = False
                self.object.save(update_fields=["buyer_archived", "seller_archived", "updated_at"])
            message = form.save(commit=False)
            message.conversation = self.object
            message.sender = request.user
            message.save()
            record_message_risk(message)
            create_notification(
                user=other_user,
                actor=request.user,
                listing=self.object.listing,
                notification_type=Notification.Type.MESSAGE,
                title="Yeni mesajın var",
                body=safe_notification_preview(request.user.display_name, message.body),
                link=self.get_success_url(),
            )
            return redirect(self.get_success_url() + "#message-composer")
        return self.form_invalid(form)


@login_required
@require_POST
def create_conversation_offer(request, pk):
    conversation = get_object_or_404(
        Conversation.objects.select_related("listing", "buyer", "seller", "listing__owner"),
        Q(buyer=request.user) | Q(seller=request.user),
        pk=pk,
    )
    if request.user.pk != conversation.buyer_id:
        raise Http404
    listing = conversation.listing
    if listing.status != Listing.Status.PUBLISHED:
        messages.warning(request, "Yalnız yayındaki ilanlara teklif verilebilir.")
        return redirect("listings:conversation_detail", pk=conversation.pk)
    if _blocked_between(request.user, conversation.seller):
        messages.error(request, "Bu kullanıcıyla teklif işlemi yapılamıyor.")
        return redirect("listings:conversation_detail", pk=conversation.pk)
    if not consume_rate_limit(request, "offer", limit=8, period=600):
        messages.error(request, "Kısa sürede çok fazla teklif işlemi yaptın. Birkaç dakika sonra tekrar dene.")
        return redirect("listings:conversation_detail", pk=conversation.pk)
    if Offer.objects.filter(listing=listing, sender=request.user, status=Offer.Status.PENDING).exists():
        messages.info(request, "Bu ilan için bekleyen teklifin zaten var.")
        return redirect("listings:conversation_detail", pk=conversation.pk)
    form = OfferForm(request.POST)
    if not form.is_valid():
        first_error = next(
            (str(error) for errors in form.errors.values() for error in errors),
            "Teklif bilgilerini kontrol et.",
        )
        messages.error(request, first_error)
        return redirect("listings:conversation_detail", pk=conversation.pk)

    offer = form.save(commit=False)
    offer.listing = listing
    offer.sender = request.user
    offer.last_actor = request.user
    offer.save()
    create_offer_event(
        offer=offer,
        actor=request.user,
        event_type=OfferEvent.Type.SUBMITTED,
        amount=offer.amount,
        message=offer.message,
    )
    create_notification(
        user=conversation.seller,
        actor=request.user,
        listing=listing,
        notification_type=Notification.Type.OFFER,
        title="Görüşmene yeni teklif geldi",
        body=f"{request.user.display_name} bir teklif gönderdi.",
        link=f"{reverse('listings:conversation_detail', kwargs={'pk': conversation.pk})}#offer-panel",
    )
    messages.success(request, "Teklifin görüşmeye eklendi.")
    return redirect(f"{reverse('listings:conversation_detail', kwargs={'pk': conversation.pk})}#offer-panel")


@login_required
@require_POST
def archive_conversation(request, pk):
    conversation = get_object_or_404(Conversation, Q(buyer=request.user) | Q(seller=request.user), pk=pk)
    if request.user.pk == conversation.buyer_id:
        conversation.buyer_archived = True
        conversation.save(update_fields=["buyer_archived", "updated_at"])
    else:
        conversation.seller_archived = True
        conversation.save(update_fields=["seller_archived", "updated_at"])
    messages.success(request, "Konuşma arşivlendi.")
    return redirect("listings:conversation_list")


@login_required
@require_POST
def restore_conversation(request, pk):
    conversation = get_object_or_404(Conversation, Q(buyer=request.user) | Q(seller=request.user), pk=pk)
    if request.user.pk == conversation.buyer_id:
        conversation.buyer_archived = False
        conversation.save(update_fields=["buyer_archived", "updated_at"])
    else:
        conversation.seller_archived = False
        conversation.save(update_fields=["seller_archived", "updated_at"])
    messages.success(request, "Konuşma yeniden mesaj kutusuna taşındı.")
    return redirect("listings:conversation_list")


class ListingMatchCenterView(LoginRequiredMixin, TemplateView):
    template_name = "listings/matches.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        active_tab = self.request.GET.get("tab", "wanted")
        if active_tab not in {"wanted", "offered"}:
            active_tab = "wanted"

        now = timezone.now()
        excluded_owner_ids = blocked_owner_ids(user.pk)
        active_pairs = (
            Q(wanted_listing__status=Listing.Status.PUBLISHED)
            & Q(offered_listing__status=Listing.Status.PUBLISHED)
            & (Q(wanted_listing__expires_at__isnull=True) | Q(wanted_listing__expires_at__gt=now))
            & (Q(offered_listing__expires_at__isnull=True) | Q(offered_listing__expires_at__gt=now))
        )
        wanted_matches = (
            ListingMatch.objects.filter(active_pairs, wanted_listing__owner=user)
            .exclude(wanted_status=ListingMatch.Status.DISMISSED)
            .exclude(offered_listing__owner_id__in=excluded_owner_ids)
            .select_related(
                "wanted_listing",
                "offered_listing",
                "offered_listing__owner",
                "offered_listing__category",
            )
            .prefetch_related("offered_listing__images", "offered_listing__price_history")
        )
        offered_matches = (
            ListingMatch.objects.filter(active_pairs, offered_listing__owner=user)
            .exclude(offered_status=ListingMatch.Status.DISMISSED)
            .exclude(wanted_listing__owner_id__in=excluded_owner_ids)
            .select_related(
                "wanted_listing",
                "wanted_listing__owner",
                "wanted_listing__category",
                "offered_listing",
            )
            .prefetch_related("wanted_listing__images")
        )
        wanted_new_count = wanted_matches.filter(wanted_status=ListingMatch.Status.NEW).count()
        offered_new_count = offered_matches.filter(offered_status=ListingMatch.Status.NEW).count()
        if active_tab == "wanted":
            wanted_matches.filter(wanted_status=ListingMatch.Status.NEW).update(
                wanted_status=ListingMatch.Status.VIEWED,
                updated_at=timezone.now(),
            )
        else:
            offered_matches.filter(offered_status=ListingMatch.Status.NEW).update(
                offered_status=ListingMatch.Status.VIEWED,
                updated_at=timezone.now(),
            )
        context.update(
            {
                "active_tab": active_tab,
                "wanted_matches": wanted_matches[:80],
                "offered_matches": offered_matches[:80],
                "wanted_match_count": wanted_matches.count(),
                "offered_match_count": offered_matches.count(),
                "wanted_new_count": wanted_new_count,
                "offered_new_count": offered_new_count,
                "highlight_match_id": self.request.GET.get("highlight", ""),
            }
        )
        return context


@login_required
@require_POST
def refresh_listing_matches(request):
    if not consume_rate_limit(request, "listing-match-refresh", limit=5, period=3600):
        messages.warning(request, "Eşleşmeleri kısa sürede çok kez yeniledin. Biraz sonra tekrar dene.")
        return redirect("listings:matches")
    result = refresh_user_matches(request.user, notify=False)
    messages.success(
        request,
        f"{result['scanned']} ilan tarandı; {result['created']} yeni eşleşme bulundu, "
        f"{result.get('deleted', 0)} geçersiz eşleşme temizlendi.",
    )
    return redirect("listings:matches")


@login_required
@require_POST
def dismiss_listing_match(request, pk):
    excluded_owner_ids = blocked_owner_ids(request.user.pk)
    match = get_object_or_404(
        ListingMatch.objects.select_related(
            "wanted_listing", "wanted_listing__owner", "offered_listing", "offered_listing__owner"
        ).exclude(
            Q(wanted_listing__owner=request.user, offered_listing__owner_id__in=excluded_owner_ids)
            | Q(offered_listing__owner=request.user, wanted_listing__owner_id__in=excluded_owner_ids)
        ),
        Q(wanted_listing__owner=request.user) | Q(offered_listing__owner=request.user),
        pk=pk,
    )
    tab = "wanted"
    update_fields = ["updated_at"]
    if match.wanted_listing.owner_id == request.user.pk:
        match.wanted_status = ListingMatch.Status.DISMISSED
        update_fields.append("wanted_status")
    elif match.offered_listing.owner_id == request.user.pk:
        match.offered_status = ListingMatch.Status.DISMISSED
        tab = "offered"
        update_fields.append("offered_status")
    match.save(update_fields=update_fields)
    messages.info(request, "Eşleşme listenden gizlendi.")
    return redirect(f"{reverse('listings:matches')}?tab={tab}")


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "listings/notifications.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user).select_related("actor", "listing")
        notification_type = self.request.GET.get("type", "").strip()
        status = self.request.GET.get("status", "").strip()
        valid_types = {value for value, _ in Notification.Type.choices}
        if notification_type in valid_types:
            qs = qs.filter(notification_type=notification_type)
        if status == "unread":
            qs = qs.filter(is_read=False)
        elif status == "read":
            qs = qs.filter(is_read=True)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pagination_params = self.request.GET.copy()
        pagination_params.pop("page", None)
        context.update(
            {
                "notification_type_choices": Notification.Type.choices,
                "active_type": self.request.GET.get("type", ""),
                "active_status": self.request.GET.get("status", ""),
                "pagination_query": pagination_params.urlencode(),
                "all_notification_count": Notification.objects.filter(user=self.request.user).count(),
                "unread_page_count": Notification.objects.filter(user=self.request.user, is_read=False).count(),
            }
        )
        return context


@login_required
@require_POST
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    target = notification.link or reverse("listings:notifications")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = reverse("listings:notifications")
    return redirect(target)


@login_required
@require_POST
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "Tüm bildirimler okundu olarak işaretlendi.")
    return redirect("listings:notifications")


@login_required
@require_POST
def save_search(request):
    if not consume_rate_limit(request, "save_search", limit=12, period=3600):
        messages.error(request, "Çok fazla arama kaydedildi. Bir süre sonra tekrar dene.")
        return redirect(_safe_next_url(request, reverse("listings:list")))

    post_data = request.POST.copy()
    if not post_data.get("alert_frequency"):
        post_data["alert_frequency"] = (
            SavedSearch.AlertFrequency.INSTANT
            if post_data.get("alert_enabled")
            else SavedSearch.AlertFrequency.OFF
        )
    form = SavedSearchForm(post_data)
    query_params = normalize_saved_search_params(request.POST)
    if not query_params:
        messages.error(request, "Kaydetmek için en az bir arama veya filtre seçmelisin.")
        return redirect(_safe_next_url(request, reverse("listings:list")))

    if form.is_valid():
        existing = next(
            (
                item
                for item in SavedSearch.objects.filter(user=request.user)
                if (item.query_params or {}) == query_params
            ),
            None,
        )
        if existing:
            previous_frequency = existing.effective_alert_frequency
            existing.name = form.cleaned_data["name"]
            existing.alert_frequency = form.cleaned_data["alert_frequency"]
            if previous_frequency != existing.alert_frequency and existing.alert_frequency == SavedSearch.AlertFrequency.DAILY:
                existing.last_checked_at = timezone.now()
            existing.save()
            messages.success(request, "Bu arama daha önce kayıtlıydı; adı ve bildirim ayarı güncellendi.")
        elif SavedSearch.objects.filter(user=request.user).count() >= 30:
            messages.error(request, "En fazla 30 arama kaydedebilirsin. Önce kullanmadığın bir aramayı sil.")
        else:
            saved = form.save(commit=False)
            saved.user = request.user
            saved.query_params = query_params
            saved.save()
            messages.success(request, "Araman kaydedildi.")
    else:
        messages.error(request, "Arama kaydedilemedi. Arama adını ve bildirim sıklığını kontrol et.")
    return redirect(_safe_next_url(request, reverse("listings:list")))


@login_required
@require_POST
def update_saved_search(request, pk):
    saved = get_object_or_404(SavedSearch, pk=pk, user=request.user)
    previous_frequency = saved.effective_alert_frequency
    form = SavedSearchForm(request.POST, instance=saved)
    if form.is_valid():
        updated = form.save(commit=False)
        if previous_frequency != updated.alert_frequency and updated.alert_frequency == SavedSearch.AlertFrequency.DAILY:
            updated.last_checked_at = timezone.now()
        updated.save()
        messages.success(request, "Kayıtlı arama güncellendi.")
    else:
        messages.error(request, "Arama güncellenemedi. Alanları kontrol et.")
    return redirect(_safe_next_url(request, reverse("listings:saved_searches")))


@login_required
@require_POST
def delete_saved_search(request, pk):
    get_object_or_404(SavedSearch, pk=pk, user=request.user).delete()
    messages.success(request, "Kayıtlı arama silindi.")
    return redirect(_safe_next_url(request, reverse("listings:saved_searches")))


@login_required
@require_POST
def toggle_saved_search_alert(request, pk):
    saved = get_object_or_404(SavedSearch, pk=pk, user=request.user)
    saved.alert_frequency = (
        SavedSearch.AlertFrequency.OFF
        if saved.alert_enabled
        else SavedSearch.AlertFrequency.INSTANT
    )
    saved.save()
    messages.success(
        request,
        "Arama bildirimi açıldı." if saved.alert_enabled else "Arama bildirimi kapatıldı.",
    )
    return redirect(_safe_next_url(request, reverse("listings:saved_searches")))


@login_required
@require_POST
def report_listing(request, slug):
    listing = get_object_or_404(Listing, _active_listing_q(), slug=slug)
    if not consume_rate_limit(request, "report", limit=5, period=3600):
        messages.error(request, "Şikâyet gönderme sınırına ulaştın. Daha sonra tekrar dene.")
        return redirect(listing.get_absolute_url())
    if listing.owner == request.user:
        messages.warning(request, "Kendi ilanını şikâyet edemezsin.")
        return redirect(listing.get_absolute_url())
    if ListingReport.objects.filter(listing=listing, reporter=request.user).exists():
        messages.info(request, "Bu ilan için daha önce şikâyet kaydı oluşturdun.")
        return redirect(listing.get_absolute_url())
    form = ListingReportForm(request.POST)
    if form.is_valid():
        report = form.save(commit=False)
        report.listing = listing
        report.reporter = request.user
        report.save()
        record_listing_report_risk(report)
        messages.success(request, "Şikâyetin inceleme ekibine gönderildi.")
    else:
        messages.error(request, "Şikâyet bilgilerini kontrol et.")
    return redirect(listing.get_absolute_url())


class ModerationDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "listings/moderation_dashboard.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = Listing.objects.filter(status=Listing.Status.REVIEW).select_related(
            "owner", "category"
        ).prefetch_related("images", "price_history")
        context["pending_total"] = base_qs.count()
        q = self.request.GET.get("q", "").strip()
        kind = self.request.GET.get("kind", "").strip()
        city = self.request.GET.get("city", "").strip()
        quality = self.request.GET.get("quality", "").strip()
        order = self.request.GET.get("order", "oldest").strip()
        if q:
            base_qs = base_qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(owner__username__icontains=q)
                | Q(owner__first_name__icontains=q)
                | Q(owner__last_name__icontains=q)
            )
        valid_kinds = {value for value, _ in Listing.Kind.choices}
        if kind in valid_kinds:
            base_qs = base_qs.filter(kind=kind)
        if city:
            base_qs = base_qs.filter(city__iexact=city)
        if order == "newest":
            base_qs = base_qs.order_by("-created_at")
        else:
            base_qs = base_qs.order_by("created_at")
        pending_listings = list(base_qs[:200])
        for listing in pending_listings:
            listing.quality_profile = assess_listing_quality(listing)
            listing.safety_profile = assess_listing_safety(
                listing, price_guide=build_price_guide(listing, exclude_pk=listing.pk)
            )
        if quality == "low":
            pending_listings = [item for item in pending_listings if item.quality_profile["score"] < 60]
        elif quality == "strong":
            pending_listings = [item for item in pending_listings if item.quality_profile["score"] >= 80]
        context.update(
            {
                "pending_listings": pending_listings,
                "moderation_q": q,
                "moderation_kind": kind,
                "moderation_city": city,
                "moderation_quality": quality,
                "moderation_order": order,
                "kind_choices": Listing.Kind.choices,
                "city_choices": CITY_CHOICES,
            }
        )
        context["open_reports"] = list(ListingReport.objects.filter(
            status__in=[ListingReport.Status.OPEN, ListingReport.Status.REVIEWING]
        ).select_related("listing", "listing__owner", "reporter")[:100])
        context["disputes"] = list(Transaction.objects.filter(status=Transaction.Status.DISPUTED).select_related(
            "listing", "buyer", "seller"
        )[:100])
        context["open_user_reports"] = list(UserReport.objects.filter(
            status__in=[UserReport.Status.OPEN, UserReport.Status.REVIEWING]
        ).select_related("reported_user", "reporter", "related_listing")[:100])
        context["open_risk_events"] = list(AccountRiskEvent.objects.filter(
            status__in=[AccountRiskEvent.Status.OPEN, AccountRiskEvent.Status.REVIEWING]
        ).select_related("subject_user", "source_listing", "source_message")[:100])
        risky_ids = {item.reported_user_id for item in context["open_user_reports"]}
        risky_ids.update(item.subject_user_id for item in context["open_risk_events"])
        risky_ids.update(item.listing.owner_id for item in context["open_reports"])
        risky_accounts = list(User.objects.filter(pk__in=risky_ids).order_by("date_joined")[:30])
        for account in risky_accounts:
            account.risk_profile = build_trust_profile(account, include_private=True, include_response=False)
        context["risky_accounts"] = risky_accounts
        return context


def _apply_listing_moderation(*, listing, actor, action, note=""):
    note = (note or "").strip()[:2000]
    if action == "approve":
        listing.status = Listing.Status.PUBLISHED
        listing.published_at = timezone.now()
        listing.expires_at = timezone.now() + timedelta(days=60)
        title = "İlanın onaylandı"
        body = "İlanın güvenlik incelemesinden geçti ve yayına alındı."
    elif action == "reject":
        listing.status = Listing.Status.REJECTED
        title = "İlanın için düzenleme gerekiyor"
        body = note or "İlanın güvenlik incelemesinde onaylanmadı. Ayrıntıları kontrol et."
    else:
        raise ValueError("Geçersiz moderasyon işlemi")
    listing.review_note = note
    listing.moderated_by = actor
    listing.moderated_at = timezone.now()
    listing.save()
    if action != "approve":
        sync_listing_matches(listing, notify=False)
    if action == "approve":
        notify_listing_publication(listing)
        latest_price_change = listing.price_history.filter(
            notifications_sent_at__isnull=True
        ).first()
        if latest_price_change:
            notify_price_drop_favorites(latest_price_change)
    create_notification(
        user=listing.owner,
        actor=actor,
        listing=listing,
        notification_type=Notification.Type.LISTING_STATUS,
        title=title,
        body=body,
        link=listing.get_absolute_url(),
    )
    log_staff_action(
        actor=actor,
        action=StaffActionLog.Action.LISTING_MODERATION,
        target=listing,
        summary=f"{listing.title} · {'onaylandı' if action == 'approve' else 'düzeltme istendi'}",
        metadata={"action": action, "review_note": note},
    )


@user_passes_test(lambda user: user.is_authenticated and user.is_staff)
@require_POST
def moderate_listing(request, pk, action):
    listing = get_object_or_404(Listing, pk=pk)
    note = request.POST.get("review_note", "").strip()[:2000]
    if action == "reject" and not note:
        messages.error(request, "Düzeltme istenirken kullanıcıya açıklayıcı bir not yazmalısın.")
        return redirect("listings:moderation")
    try:
        _apply_listing_moderation(listing=listing, actor=request.user, action=action, note=note)
    except ValueError:
        messages.error(request, "Geçersiz moderasyon işlemi.")
        return redirect("listings:moderation")
    messages.success(request, f"{listing.title} için işlem tamamlandı.")
    return redirect("listings:moderation")


@user_passes_test(lambda user: user.is_authenticated and user.is_staff)
@require_POST
def bulk_moderate_listings(request):
    raw_ids = request.POST.getlist("listing_ids")
    action = request.POST.get("bulk_action", "").strip()
    note = request.POST.get("bulk_note", "").strip()[:2000]
    try:
        selected_ids = list(dict.fromkeys(int(value) for value in raw_ids))[:100]
    except (TypeError, ValueError):
        selected_ids = []
    if not selected_ids:
        messages.warning(request, "Toplu işlem için en az bir ilan seç.")
        return redirect("listings:moderation")
    if action not in {"approve", "reject"}:
        messages.error(request, "Toplu işlem türünü seç.")
        return redirect("listings:moderation")
    if action == "reject" and not note:
        messages.error(request, "Toplu düzeltme isteğinde ortak bir açıklama yazmalısın.")
        return redirect("listings:moderation")
    listings = list(
        Listing.objects.filter(pk__in=selected_ids, status=Listing.Status.REVIEW)
        .select_related("owner")
        .prefetch_related("price_history")
    )
    if not listings:
        messages.info(request, "Seçilen ilanlar artık inceleme kuyruğunda değil.")
        return redirect("listings:moderation")
    with db_transaction.atomic():
        for listing in listings:
            _apply_listing_moderation(
                listing=listing, actor=request.user, action=action, note=note
            )
    messages.success(
        request,
        f"{len(listings)} ilan için toplu moderasyon işlemi tamamlandı.",
    )
    return redirect("listings:moderation")


@user_passes_test(lambda user: user.is_authenticated and user.is_staff)
@require_POST
def moderate_report(request, pk, action):
    report = get_object_or_404(ListingReport, pk=pk)
    statuses = {
        "review": ListingReport.Status.REVIEWING,
        "resolve": ListingReport.Status.RESOLVED,
        "dismiss": ListingReport.Status.DISMISSED,
    }
    if action not in statuses:
        messages.error(request, "Geçersiz şikâyet işlemi.")
        return redirect("listings:moderation")
    report.status = statuses[action]
    report.reviewed_by = request.user
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    related_status = {
        "review": AccountRiskEvent.Status.REVIEWING,
        "resolve": AccountRiskEvent.Status.RESOLVED,
        "dismiss": AccountRiskEvent.Status.DISMISSED,
    }[action]
    AccountRiskEvent.objects.filter(
        fingerprint=f"listing-report:{report.pk}",
        status__in=[AccountRiskEvent.Status.OPEN, AccountRiskEvent.Status.REVIEWING],
    ).update(
        status=related_status,
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
        updated_at=timezone.now(),
    )
    log_staff_action(
        actor=request.user,
        action=StaffActionLog.Action.ACCOUNT_ACTION,
        target=report.listing.owner,
        summary=f"İlan şikâyeti güncellendi: {report.get_status_display()}",
        metadata={"listing_report_id": report.pk, "listing_id": report.listing_id, "action": action},
    )
    messages.success(request, "Şikâyet durumu güncellendi.")
    return redirect("listings:moderation")


@user_passes_test(lambda user: user.is_authenticated and user.is_staff)
@require_POST
def moderate_user_report(request, pk, action):
    report = get_object_or_404(UserReport, pk=pk)
    statuses = {
        "review": UserReport.Status.REVIEWING,
        "resolve": UserReport.Status.RESOLVED,
        "dismiss": UserReport.Status.DISMISSED,
    }
    if action not in statuses:
        messages.error(request, "Geçersiz kullanıcı şikâyeti işlemi.")
        return redirect("listings:moderation")
    report.status = statuses[action]
    report.reviewed_by = request.user
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    if action in {"resolve", "dismiss"}:
        report.risk_events.filter(status__in=[AccountRiskEvent.Status.OPEN, AccountRiskEvent.Status.REVIEWING]).update(
            status=(AccountRiskEvent.Status.RESOLVED if action == "resolve" else AccountRiskEvent.Status.DISMISSED),
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
            updated_at=timezone.now(),
        )
    log_staff_action(
        actor=request.user, action=StaffActionLog.Action.ACCOUNT_ACTION, target=report.reported_user,
        summary=f"Kullanıcı şikâyeti güncellendi: {report.get_status_display()}",
        metadata={"report_id": report.pk, "action": action},
    )
    messages.success(request, "Kullanıcı şikâyeti güncellendi.")
    return redirect("listings:moderation")


@user_passes_test(lambda user: user.is_authenticated and user.is_staff)
@require_POST
def moderate_risk_event(request, pk, action):
    event = get_object_or_404(AccountRiskEvent, pk=pk)
    statuses = {
        "review": AccountRiskEvent.Status.REVIEWING,
        "resolve": AccountRiskEvent.Status.RESOLVED,
        "dismiss": AccountRiskEvent.Status.DISMISSED,
    }
    if action not in statuses:
        messages.error(request, "Geçersiz risk kaydı işlemi.")
        return redirect("listings:moderation")
    event.status = statuses[action]
    event.reviewed_by = request.user
    event.reviewed_at = timezone.now()
    event.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
    log_staff_action(
        actor=request.user, action=StaffActionLog.Action.ACCOUNT_ACTION, target=event.subject_user,
        summary=f"Risk kaydı güncellendi: {event.get_status_display()}",
        metadata={"risk_event_id": event.pk, "action": action},
    )
    messages.success(request, "Risk kaydı güncellendi.")
    return redirect("listings:moderation")


def _merge_location_suggestions(catalog_values, observed_values, *, limit=140):
    merged = []
    seen = set()
    for raw in (*catalog_values, *observed_values):
        value = " ".join(str(raw or "").split())
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        merged.append(value)
        if len(merged) >= limit:
            break
    return merged


@require_GET
def location_suggestions(request):
    city = " ".join(request.GET.get("city", "").strip().split())[:80]
    district = " ".join(request.GET.get("district", "").strip().split())[:80]
    observed_districts = []
    observed_neighborhoods = []
    if city:
        observed_districts = list(
            Listing.objects.filter(_active_listing_q(), city__iexact=city)
            .exclude(district="")
            .order_by("district")
            .values_list("district", flat=True)
            .distinct()[:140]
        )
    if city and district:
        observed_neighborhoods = list(
            Listing.objects.filter(
                _active_listing_q(), city__iexact=city, district__iexact=district
            )
            .exclude(neighborhood="")
            .order_by("neighborhood")
            .values_list("neighborhood", flat=True)
            .distinct()[:140]
        )
    return JsonResponse(
        {
            "districts": _merge_location_suggestions(get_districts(city), observed_districts),
            "neighborhoods": _merge_location_suggestions(
                get_neighborhoods(city, district), observed_neighborhoods
            ),
            "catalog_complete": bool(get_districts(city)),
        }
    )
