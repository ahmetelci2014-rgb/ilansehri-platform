from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from django.contrib.auth.mixins import UserPassesTestMixin
from django.conf import settings
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.models import AccountClosureRequest, AccountRiskEvent, User, UserFollow, UserReport
from apps.ai_listing.models import AIAnalysis, AISettings
from apps.listings.catalog import category_market_kind
from apps.listings.models import Category, Favorite, Listing, ListingPriceHistory, ListingReport, Offer, Review, Transaction
from apps.managed_services.models import ManagedRequest
from apps.partners.models import PartnerProfile, Task
from apps.support_center.models import StaffActionLog, SupportTicket


RELEASE_VERSION = (Path(settings.BASE_DIR) / "VERSION").read_text(encoding="utf-8").strip().removeprefix("v")
RELEASE_CACHE = "".join(character for character in RELEASE_VERSION if character.isdigit())


def _active_listing_q():
    return Q(status=Listing.Status.PUBLISHED) & (
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    )


def _listing_queryset():
    return (
        Listing.objects.filter(_active_listing_q())
        .select_related("category", "owner")
        .prefetch_related("images", "price_history")
    )


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        published = _listing_queryset()
        preferred_city = (self.request.GET.get("city") or "").strip()
        preferred_district = (self.request.GET.get("district") or "").strip()
        if self.request.user.is_authenticated:
            if not preferred_city:
                preferred_city = self.request.user.city.strip()
            if not preferred_district:
                preferred_district = self.request.user.district.strip()

        nearby = published.filter(city__iexact=preferred_city) if preferred_city else published
        if preferred_district:
            district_nearby = nearby.filter(district__iexact=preferred_district)
            if district_nearby.exists():
                nearby = district_nearby
        if preferred_city and not nearby.exists():
            nearby = published

        latest = list(nearby.order_by("-is_featured", "-published_at", "-created_at")[:12])
        popular = list(published.order_by("-view_count", "-favorite_count", "-created_at")[:10])
        vehicles = list(published.filter(kind=Listing.Kind.VEHICLE).order_by("-is_featured", "-created_at")[:10])
        estates = list(published.filter(kind=Listing.Kind.REAL_ESTATE).order_by("-is_featured", "-created_at")[:10])
        services = list(published.filter(kind=Listing.Kind.SERVICE).order_by("-is_featured", "-created_at")[:10])

        latest_price_history = ListingPriceHistory.objects.filter(
            listing_id=OuterRef("pk")
        ).order_by("-created_at")
        price_drops = list(
            published.annotate(
                latest_price_old=Subquery(latest_price_history.values("old_price")[:1]),
                latest_price_new=Subquery(latest_price_history.values("new_price")[:1]),
                latest_price_changed_at=Subquery(latest_price_history.values("created_at")[:1]),
            )
            .filter(latest_price_old__gt=F("latest_price_new"))
            .order_by("-latest_price_changed_at", "-created_at")[:10]
        )

        following_listings = []
        if self.request.user.is_authenticated:
            followed_sellers = UserFollow.objects.filter(follower=self.request.user).values_list("seller_id", flat=True)
            following_listings = list(
                published.filter(owner_id__in=followed_sellers).order_by("-published_at", "-created_at")[:10]
            )

        recent_ids = self.request.session.get("recently_viewed", [])[:8]
        recent_map = {
            item.pk: item
            for item in published.filter(pk__in=recent_ids)
        }
        recently_viewed = [recent_map[item_id] for item_id in recent_ids if item_id in recent_map]

        favorite_ids = set()
        if self.request.user.is_authenticated:
            favorite_ids = set(
                Favorite.objects.filter(user=self.request.user).values_list("listing_id", flat=True)
            )

        kind_counts = {
            row["kind"]: row["total"]
            for row in published.order_by().values("kind").annotate(total=Count("id"))
        }
        category_counts = {
            row["category_id"]: row["total"]
            for row in published.order_by().values("category_id").annotate(total=Count("id"))
        }
        category_shortcuts: dict[str, list[dict]] = {kind: [] for kind, _label in Listing.Kind.choices}
        category_rows = (
            Category.objects.filter(is_active=True)
            .select_related("parent", "parent__parent")
            .annotate(active_child_count=Count("children", filter=Q(children__is_active=True)))
        )
        for category in category_rows:
            kind = category_market_kind(category)
            if not kind or category.active_child_count:
                continue
            category_shortcuts.setdefault(kind, []).append(
                {
                    "id": category.pk,
                    "label": category.name,
                    "count": category_counts.get(category.pk, 0),
                    "sort_order": category.sort_order,
                }
            )
        for kind, rows in category_shortcuts.items():
            rows.sort(key=lambda row: (-row["count"], row["sort_order"], row["label"].casefold()))
            category_shortcuts[kind] = rows[:3]

        category_tiles = [
            {"kind": Listing.Kind.PRODUCT, "label": "Ürün & Eşya", "icon": "📱"},
            {"kind": Listing.Kind.VEHICLE, "label": "Araç", "icon": "🚗"},
            {"kind": Listing.Kind.REAL_ESTATE, "label": "Emlak", "icon": "🏠"},
            {"kind": Listing.Kind.SERVICE, "label": "Hizmet", "icon": "🛠️"},
            {"kind": Listing.Kind.JOB, "label": "İş", "icon": "💼"},
            {"kind": Listing.Kind.NEED, "label": "Arıyorum", "icon": "📣"},
        ]
        for tile in category_tiles:
            tile["count"] = kind_counts.get(tile["kind"], 0)
            tile["shortcuts"] = category_shortcuts.get(tile["kind"], [])

        context.update(
            {
                "preferred_city": preferred_city,
                "preferred_district": preferred_district,
                "latest_listings": latest,
                "popular_listings": popular,
                "vehicle_listings": vehicles,
                "estate_listings": estates,
                "service_listings": services,
                "price_drop_listings": price_drops,
                "following_listings": following_listings,
                "recently_viewed": recently_viewed,
                "favorite_ids": favorite_ids,
                "compare_ids": set(self.request.session.get("compare_listing_ids", [])),
                "category_tiles": category_tiles,
                "listing_count": published.count(),
                "member_count": User.objects.filter(is_active=True).count(),
                "active_city_count": published.order_by().exclude(city="").values("city").distinct().count(),
                "review_count": Review.objects.filter(is_visible=True).count(),
            }
        )
        return context


class StaffDashboardView(UserPassesTestMixin, TemplateView):
    template_name = "core/staff_dashboard.html"
    raise_exception = True

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        day_rows = []
        max_activity = 1
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            listing_total = Listing.objects.filter(created_at__date=day).count()
            user_total = User.objects.filter(date_joined__date=day).count()
            max_activity = max(max_activity, listing_total + user_total)
            day_rows.append(
                {
                    "date": day,
                    "label": day.strftime("%d.%m"),
                    "listing_total": listing_total,
                    "user_total": user_total,
                    "activity": listing_total + user_total,
                }
            )
        for row in day_rows:
            row["percent"] = max(8, round((row["activity"] / max_activity) * 100)) if row["activity"] else 4

        active_listings = Listing.objects.filter(_active_listing_q())
        seven_days_ago = timezone.now() - timedelta(days=7)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        total_transactions = Transaction.objects.count()
        completed_transactions = Transaction.objects.filter(status=Transaction.Status.COMPLETED).count()
        context["launch_metrics"] = {
            "new_listings_7d": Listing.objects.filter(created_at__gte=seven_days_ago).count(),
            "new_users_7d": User.objects.filter(date_joined__gte=seven_days_ago).count(),
            "offers_7d": Offer.objects.filter(created_at__gte=seven_days_ago).count(),
            "completed_7d": Transaction.objects.filter(
                status=Transaction.Status.COMPLETED, completed_at__gte=seven_days_ago
            ).count(),
            "conversion_rate": round((completed_transactions / total_transactions) * 100) if total_transactions else 0,
            "stale_listings": active_listings.filter(updated_at__lt=thirty_days_ago).count(),
        }
        context["top_categories"] = list(
            active_listings.values("category__name")
            .annotate(total=Count("id"))
            .order_by("-total", "category__name")[:6]
        )
        context["top_cities"] = list(
            active_listings.values("city")
            .annotate(total=Count("id"))
            .order_by("-total", "city")[:6]
        )

        ai_config = AISettings.objects.filter(singleton_key=1).first()
        ai_today = AIAnalysis.objects.filter(created_at__date=today)
        context["ai_operations"] = {
            "enabled": bool(ai_config and ai_config.is_enabled),
            "provider": ai_config.get_provider_display() if ai_config else "Kurulmadı",
            "today": ai_today.count(),
            "failed_today": ai_today.filter(status=AIAnalysis.Status.FAILED).count(),
            "blocked_today": ai_today.filter(status=AIAnalysis.Status.BLOCKED).count(),
            "success_rate": ai_config.success_rate if ai_config else 0,
            "average_duration_ms": ai_config.average_duration_ms if ai_config else 0,
        }

        context.update(
            {
                "stats": {
                    "active_listings": Listing.objects.filter(_active_listing_q()).count(),
                    "pending_listings": Listing.objects.filter(status=Listing.Status.REVIEW).count(),
                    "users": User.objects.filter(is_active=True).count(),
                    "open_reports": ListingReport.objects.filter(
                        status__in=[ListingReport.Status.OPEN, ListingReport.Status.REVIEWING]
                    ).count(),
                    "open_user_reports": UserReport.objects.filter(
                        status__in=[UserReport.Status.OPEN, UserReport.Status.REVIEWING]
                    ).count(),
                    "open_risk_events": AccountRiskEvent.objects.filter(
                        status__in=[AccountRiskEvent.Status.OPEN, AccountRiskEvent.Status.REVIEWING]
                    ).count(),
                    "active_transactions": Transaction.objects.exclude(
                        status__in=[Transaction.Status.COMPLETED, Transaction.Status.CANCELLED]
                    ).count(),
                    "managed_requests": ManagedRequest.objects.exclude(
                        status__in=[ManagedRequest.Status.COMPLETED, ManagedRequest.Status.CANCELLED]
                    ).count(),
                    "open_tasks": Task.objects.exclude(
                        status__in=[Task.Status.COMPLETED, Task.Status.CANCELLED]
                    ).count(),
                    "closure_requests": AccountClosureRequest.objects.filter(
                        status=AccountClosureRequest.Status.PENDING
                    ).count(),
                    "open_support_tickets": SupportTicket.objects.exclude(
                        status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]
                    ).count(),
                },
                "day_rows": day_rows,
                "pending_listing_rows": Listing.objects.filter(status=Listing.Status.REVIEW)
                .select_related("owner", "category")
                .order_by("created_at")[:8],
                "report_rows": ListingReport.objects.filter(
                    status__in=[ListingReport.Status.OPEN, ListingReport.Status.REVIEWING]
                )
                .select_related("listing", "reporter")[:8],
                "transaction_rows": Transaction.objects.exclude(
                    status__in=[Transaction.Status.COMPLETED, Transaction.Status.CANCELLED]
                )
                .select_related("listing", "buyer", "seller")[:6],
                "managed_rows": ManagedRequest.objects.exclude(
                    status__in=[ManagedRequest.Status.COMPLETED, ManagedRequest.Status.CANCELLED]
                )
                .select_related("listing", "customer", "assigned_staff")[:6],
                "task_rows": Task.objects.exclude(
                    status__in=[Task.Status.COMPLETED, Task.Status.CANCELLED]
                )
                .select_related("managed_request__listing", "assigned_partner__user")[:6],
                "recent_users": User.objects.order_by("-date_joined")[:8],
                "closure_rows": AccountClosureRequest.objects.filter(
                    status=AccountClosureRequest.Status.PENDING
                ).select_related("user")[:8],
                "support_ticket_rows": SupportTicket.objects.exclude(
                    status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]
                ).select_related("user", "assigned_to").order_by("-priority", "updated_at")[:8],
                "staff_action_rows": StaffActionLog.objects.select_related("actor")[:10],
            }
        )
        return context


class StaticPageView(TemplateView):
    pass


def health_check(request):
    return JsonResponse({"status": "ok", "service": "ilansehri", "version": RELEASE_VERSION})


def robots_txt(request):
    base_url = settings.PUBLIC_BASE_URL or f"{request.scheme}://{request.get_host()}"
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /yonetim/",
        "Disallow: /hesap/",
        "Disallow: /yardim/talep/",
        "Disallow: /yardim/taleplerim/",
        "Disallow: /yardim/ekip/",
        "Disallow: /ilanlar/taslaklarim/",
        "Disallow: /ilanlar/ilanlarim/",
        "Disallow: /ilanlar/yapay-zeka/",
        "Disallow: /ilanlar/fiyat-rehberi/",
        "Disallow: /ilanlar/favorilerim/",
        "Disallow: /ilanlar/aramalarim/",
        "Disallow: /ilanlar/mesajlar/",
        "Disallow: /ilanlar/randevularim/",
        "Disallow: /ilanlar/randevu/",
        "Disallow: /ilanlar/eslesmelerim/",
        "Disallow: /ilanlar/bildirimler/",
        "Disallow: /ilanlar/tekliflerim/",
        "Disallow: /ilanlar/islem/",
        f"Sitemap: {base_url}{reverse('django.contrib.sitemaps.views.sitemap')}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


def manifest(request):
    return JsonResponse(
        {
            "name": "İlan Şehri",
            "short_name": "İlan Şehri",
            "description": "Şehrindeki ürün, hizmet, iş ve ihtiyaçları buluşturan güven odaklı yerel pazar.",
            "start_url": "/?source=pwa",
            "scope": "/",
            "display": "standalone",
            "background_color": "#f8fafc",
            "theme_color": "#2563eb",
            "lang": "tr",
            "icons": [
                {"src": "/static/img/icon-192.svg", "sizes": "192x192", "type": "image/svg+xml", "purpose": "any maskable"},
                {"src": "/static/img/icon-512.svg", "sizes": "512x512", "type": "image/svg+xml", "purpose": "any maskable"},
            ],
            "shortcuts": [
                {"name": "İlan ver", "url": "/ilanlar/yeni/"},
                {"name": "İlanları keşfet", "url": "/ilanlar/"},
                {"name": "Mesajlar", "url": "/ilanlar/mesajlar/"},
                {"name": "Karşılaştır", "url": "/ilanlar/karsilastir/"},
                {"name": "Yardım Merkezi", "url": "/yardim/"},
            ],
        }
    )


def service_worker(request):
    script = r'''
const CACHE = "ilansehri-v__CACHE__";
const CORE = ["/ilanlar/", "/offline/", "/static/css/app.css", "/static/css/v14-polish.css", "/static/css/v15-experience.css", "/static/css/v16-premium.css", "/static/css/v17-launch.css", "/static/css/v18-vibrant.css", "/static/css/v19-flow.css", "/static/css/v110-support.css", "/static/css/v111-operations.css", "/static/css/v112-ai.css", "/static/css/v113-mobile-market.css", "/static/css/v132-mobile-system.css", "/static/css/v14-matching.css", "/static/css/v141-price-guide.css", "/static/css/v15-message-safety.css", "/static/css/v117-search-alerts.css", "/static/css/v118-trust-safety.css", "/static/css/v119-transactions.css", "/static/css/v120-appointments.css", "/static/css/v121-discovery.css", "/static/css/v122-market-polish.css", "/static/css/v123-detail-experience.css", "/static/css/v124-seller-center.css", "/static/js/app.js", "/static/js/v16-premium.js", "/static/js/v17-launch.js", "/static/js/v18-ux.js", "/static/js/v111-operations.js", "/static/js/v112-ai.js", "/static/js/v113-mobile-market.js", "/static/js/v132-mobile-system.js", "/static/js/v141-price-guide.js", "/static/js/v15-message-safety.js", "/static/js/v116-location-discovery.js", "/static/js/v121-discovery.js", "/static/js/v122-market-polish.js", "/static/js/v123-detail-experience.js", "/static/js/v124-seller-center.js", "/static/img/icon-192.svg", "/static/img/icon-512.svg"];
const PRIVATE_PREFIXES = ["/hesap/", "/yardim/talep/", "/yardim/taleplerim/", "/yardim/ekip/", "/ilanlar/favorilerim/", "/ilanlar/aramalarim/", "/ilanlar/taslaklarim/", "/ilanlar/ilanlarim/", "/ilanlar/yapay-zeka/", "/ilanlar/fiyat-rehberi/", "/ilanlar/mesajlar/", "/ilanlar/randevularim/", "/ilanlar/randevu/", "/ilanlar/bildirimler/", "/ilanlar/eslesmelerim/", "/ilanlar/tekliflerim/", "/ilanlar/islem/", "/tam-yonetim/", "/kazanc-agi/panelim/", "/admin/", "/yonetim/"];
self.addEventListener("install", event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(CORE))));
self.addEventListener("activate", event => event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))));
self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || PRIVATE_PREFIXES.some(prefix => url.pathname.startsWith(prefix))) {
    event.respondWith(fetch(event.request));
    return;
  }
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(caches.match(event.request).then(hit => hit || fetch(event.request).then(response => {
      const copy = response.clone(); caches.open(CACHE).then(cache => cache.put(event.request, copy)); return response;
    })));
    return;
  }
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request).then(hit => hit || caches.match("/offline/"))));
});
'''.replace("__CACHE__", RELEASE_CACHE)
    response = HttpResponse(script, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response
