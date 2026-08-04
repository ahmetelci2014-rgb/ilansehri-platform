from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, F, Q
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from django.views.generic.edit import FormMixin

from apps.managed_services.models import ManagedRequest

from .forms import ListingForm, ListingReportForm, MessageForm, OfferForm
from .locations import CITY_CHOICES, get_districts, get_neighborhoods
from .models import (
    Conversation,
    Favorite,
    Listing,
    ListingImage,
    ListingReport,
    Message,
    Notification,
)
from .services import create_notification


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_decimal(value):
    try:
        return Decimal(value)
    except (TypeError, ValueError, InvalidOperation):
        return None


class ListingListView(ListView):
    model = Listing
    template_name = "listings/list.html"
    context_object_name = "listings"
    paginate_by = 24

    def get_queryset(self):
        qs = (
            Listing.objects.filter(status=Listing.Status.PUBLISHED)
            .select_related("owner", "category")
            .prefetch_related("images")
        )
        params = self.request.GET
        q = params.get("q", "").strip()
        city = params.get("city", "").strip()
        district = params.get("district", "").strip()
        kind = params.get("kind", "").strip()
        action = params.get("action", "").strip()
        brand = params.get("brand", "").strip()
        model_name = params.get("model", "").strip()
        room_count = params.get("room_count", "").strip()

        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(category__name__icontains=q)
                | Q(brand__icontains=q)
                | Q(model_name__icontains=q)
            )
        if city:
            qs = qs.filter(city__iexact=city)
        if district:
            qs = qs.filter(district__icontains=district)
        if kind:
            qs = qs.filter(kind=kind)
        if action:
            qs = qs.filter(action=action)
        if brand:
            qs = qs.filter(brand__icontains=brand)
        if model_name:
            qs = qs.filter(model_name__icontains=model_name)
        if room_count:
            qs = qs.filter(room_count__iexact=room_count)

        filters = {
            "price__gte": _safe_decimal(params.get("min_price")),
            "price__lte": _safe_decimal(params.get("max_price")),
            "model_year__gte": _safe_int(params.get("min_year")),
            "model_year__lte": _safe_int(params.get("max_year")),
            "mileage__lte": _safe_int(params.get("max_mileage")),
            "area_m2__gte": _safe_int(params.get("min_area")),
            "area_m2__lte": _safe_int(params.get("max_area")),
        }
        qs = qs.filter(**{key: value for key, value in filters.items() if value is not None})
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["city_choices"] = CITY_CHOICES
        context["kind_choices"] = Listing.Kind.choices
        context["action_choices"] = Listing.Action.choices
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        context["query_string"] = query_params.urlencode()
        return context


class ListingDetailView(FormMixin, DetailView):
    template_name = "listings/detail.html"
    context_object_name = "listing"
    form_class = OfferForm

    def get_queryset(self):
        qs = Listing.objects.select_related("owner", "category", "moderated_by").prefetch_related(
            "images"
        )
        user = self.request.user
        if user.is_authenticated:
            if user.is_staff:
                return qs
            return qs.filter(Q(status=Listing.Status.PUBLISHED) | Q(owner=user))
        return qs.filter(status=Listing.Status.PUBLISHED)

    def get_success_url(self):
        return reverse("listings:detail", kwargs={"slug": self.object.slug})

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if self.request.method == "GET" and obj.status == Listing.Status.PUBLISHED:
            Listing.objects.filter(pk=obj.pk).update(view_count=F("view_count") + 1)
            obj.view_count += 1
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["can_offer"] = (
            user.is_authenticated
            and user != self.object.owner
            and self.object.status == Listing.Status.PUBLISHED
        )
        context["message_form"] = MessageForm()
        context["report_form"] = ListingReportForm()
        context["can_report"] = context["can_offer"]
        context["is_favorite"] = (
            user.is_authenticated
            and Favorite.objects.filter(user=user, listing=self.object).exists()
        )
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Teklif vermek için giriş yapmalısın.")
            return redirect(f"/hesap/login/?next={request.path}")
        self.object = self.get_object()
        if self.object.status != Listing.Status.PUBLISHED:
            messages.warning(request, "Bu ilan şu anda teklif almıyor.")
            return redirect(self.get_success_url())
        if self.object.owner == request.user:
            messages.warning(request, "Kendi ilanına teklif veremezsin.")
            return redirect(self.get_success_url())
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        offer = form.save(commit=False)
        offer.listing = self.object
        offer.sender = self.request.user
        offer.save()
        create_notification(
            user=self.object.owner,
            actor=self.request.user,
            listing=self.object,
            notification_type=Notification.Type.OFFER,
            title="İlanına yeni teklif geldi",
            body=f"{self.request.user} · {self.object.title}",
            link=self.object.get_absolute_url(),
        )
        messages.success(self.request, "Teklifin ilan sahibine gönderildi.")
        return redirect(self.get_success_url())


class ListingCreateView(LoginRequiredMixin, CreateView):
    model = Listing
    form_class = ListingForm
    template_name = "listings/form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.status = (
            Listing.Status.PUBLISHED
            if getattr(settings, "AUTO_PUBLISH_LISTINGS", False)
            else Listing.Status.REVIEW
        )
        response = super().form_valid(form)
        self._save_images(form)
        if self.object.management_mode == Listing.ManagementMode.FULL:
            ManagedRequest.objects.get_or_create(
                listing=self.object,
                defaults={
                    "customer": self.request.user,
                    "package": ManagedRequest.Package.FULL,
                    "requested_services": [
                        "ilan_hazirlama",
                        "mesaj_yonetimi",
                        "teklif_toplama",
                        "randevu_koordinasyonu",
                    ],
                },
            )
            messages.success(
                self.request,
                "İlanın oluşturuldu ve Tam Yönetim ekibine iletildi.",
            )
        elif self.object.status == Listing.Status.REVIEW:
            messages.success(
                self.request,
                "İlanın oluşturuldu ve güvenlik incelemesine gönderildi.",
            )
        else:
            messages.success(self.request, "İlanın başarıyla yayınlandı.")
        return response

    def _save_images(self, form):
        for index, image in enumerate(form.cleaned_data.get("images", [])):
            ListingImage.objects.create(
                listing=self.object,
                image=image,
                is_cover=index == 0,
                sort_order=index,
                alt_text=self.object.title,
            )


class ListingUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Listing
    form_class = ListingForm
    template_name = "listings/form.html"

    def test_func(self):
        return self.get_object().owner == self.request.user

    def form_valid(self, form):
        if (
            self.object.status == Listing.Status.PUBLISHED
            and not getattr(settings, "AUTO_PUBLISH_LISTINGS", False)
            and not self.request.user.is_staff
        ):
            form.instance.status = Listing.Status.REVIEW
            form.instance.review_note = ""
        response = super().form_valid(form)
        start_index = self.object.images.count()
        for index, image in enumerate(
            form.cleaned_data.get("images", []),
            start=start_index,
        ):
            ListingImage.objects.create(
                listing=self.object,
                image=image,
                is_cover=not self.object.images.exists(),
                sort_order=index,
                alt_text=self.object.title,
            )
        if self.object.status == Listing.Status.REVIEW:
            messages.success(self.request, "Değişiklikler kaydedildi ve yeniden incelemeye gönderildi.")
        else:
            messages.success(self.request, "İlan bilgileri güncellendi.")
        return response


class ListingDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Listing
    template_name = "listings/confirm_delete.html"
    success_url = reverse_lazy("accounts:dashboard")

    def test_func(self):
        return self.get_object().owner == self.request.user

    def form_valid(self, form):
        messages.success(self.request, "İlan kalıcı olarak silindi.")
        return super().form_valid(form)


@login_required
@require_POST
def change_listing_status(request, slug, action):
    listing = get_object_or_404(Listing, slug=slug, owner=request.user)
    allowed = {
        "pause": ({Listing.Status.PUBLISHED}, Listing.Status.PAUSED, "İlan duraklatıldı."),
        "publish": ({Listing.Status.PAUSED}, Listing.Status.PUBLISHED, "İlan yeniden yayına alındı."),
        "complete": (
            {Listing.Status.PUBLISHED, Listing.Status.PAUSED},
            Listing.Status.COMPLETED,
            "İlan sonuçlandı olarak işaretlendi.",
        ),
    }
    transition = allowed.get(action)
    if not transition or listing.status not in transition[0]:
        messages.error(request, "Bu ilan için geçersiz durum işlemi.")
        return redirect("accounts:dashboard")

    listing.status = transition[1]
    update_fields = ["status", "updated_at"]
    if listing.status == Listing.Status.PUBLISHED:
        listing.published_at = timezone.now()
        update_fields.append("published_at")
    listing.save(update_fields=update_fields)
    messages.success(request, transition[2])
    return redirect("accounts:dashboard")


@login_required
@require_POST
def toggle_favorite(request, slug):
    listing = get_object_or_404(Listing, slug=slug, status=Listing.Status.PUBLISHED)
    if listing.owner == request.user:
        messages.info(request, "Kendi ilanını favorilere eklemene gerek yok.")
    else:
        favorite, created = Favorite.objects.get_or_create(user=request.user, listing=listing)
        if created:
            messages.success(request, "İlan favorilerine eklendi.")
        else:
            favorite.delete()
            messages.info(request, "İlan favorilerinden çıkarıldı.")

    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = listing.get_absolute_url()
    return redirect(next_url)


class FavoriteListView(LoginRequiredMixin, ListView):
    template_name = "listings/favorites.html"
    context_object_name = "favorites"
    paginate_by = 24

    def get_queryset(self):
        return (
            Favorite.objects.filter(
                user=self.request.user,
                listing__status=Listing.Status.PUBLISHED,
            )
            .select_related("listing", "listing__owner", "listing__category")
            .prefetch_related("listing__images")
        )


@login_required
@require_POST
def start_conversation(request, slug):
    listing = get_object_or_404(Listing, slug=slug, status=Listing.Status.PUBLISHED)
    if listing.owner == request.user:
        messages.warning(request, "Kendi ilanına mesaj gönderemezsin.")
        return redirect(listing.get_absolute_url())

    form = MessageForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Mesajını kontrol edip yeniden gönder.")
        return redirect(listing.get_absolute_url())

    conversation, _ = Conversation.objects.get_or_create(
        listing=listing,
        buyer=request.user,
        defaults={"seller": listing.owner},
    )
    Message.objects.create(
        conversation=conversation,
        sender=request.user,
        body=form.cleaned_data["body"],
    )
    create_notification(
        user=listing.owner,
        actor=request.user,
        listing=listing,
        notification_type=Notification.Type.MESSAGE,
        title="İlanın hakkında yeni mesaj",
        body=f"{request.user}: {form.cleaned_data['body'][:100]}",
        link=reverse("listings:conversation_detail", kwargs={"pk": conversation.pk}),
    )
    messages.success(request, "Mesajın ilan sahibine gönderildi.")
    return redirect("listings:conversation_detail", pk=conversation.pk)


class ConversationListView(LoginRequiredMixin, ListView):
    template_name = "listings/conversation_list.html"
    context_object_name = "conversations"
    paginate_by = 30

    def get_queryset(self):
        user = self.request.user
        return (
            Conversation.objects.filter(Q(buyer=user) | Q(seller=user))
            .select_related("listing", "buyer", "seller")
            .prefetch_related("messages")
            .annotate(
                unread_count=Coalesce(
                    Count(
                        "messages",
                        filter=Q(messages__is_read=False) & ~Q(messages__sender=user),
                    ),
                    0,
                )
            )
            .order_by("-updated_at")
        )


class ConversationDetailView(LoginRequiredMixin, FormMixin, DetailView):
    model = Conversation
    template_name = "listings/conversation_detail.html"
    context_object_name = "conversation"
    form_class = MessageForm

    def get_queryset(self):
        user = self.request.user
        return (
            Conversation.objects.filter(Q(buyer=user) | Q(seller=user))
            .select_related("listing", "buyer", "seller")
            .prefetch_related("messages__sender")
        )

    def get_success_url(self):
        return reverse("listings:conversation_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["other_user"] = self.object.other_participant(self.request.user)
        return context

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        self.object.messages.filter(is_read=False).exclude(sender=request.user).update(
            is_read=True
        )
        return response

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        message = form.save(commit=False)
        message.conversation = self.object
        message.sender = self.request.user
        message.save()
        recipient = self.object.other_participant(self.request.user)
        create_notification(
            user=recipient,
            actor=self.request.user,
            listing=self.object.listing,
            notification_type=Notification.Type.MESSAGE,
            title="Yeni mesajın var",
            body=f"{self.request.user}: {message.body[:100]}",
            link=self.get_success_url(),
        )
        return redirect(self.get_success_url())


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "listings/notifications.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related(
            "actor", "listing"
        )


@login_required
@require_POST
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    next_url = notification.link or reverse("listings:notifications")
    return redirect(next_url)


@login_required
@require_POST
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "Tüm bildirimler okundu olarak işaretlendi.")
    return redirect("listings:notifications")


@login_required
@require_POST
def report_listing(request, slug):
    listing = get_object_or_404(Listing, slug=slug, status=Listing.Status.PUBLISHED)
    if listing.owner == request.user:
        messages.warning(request, "Kendi ilanını şikâyet edemezsin.")
        return redirect(listing.get_absolute_url())
    if ListingReport.objects.filter(listing=listing, reporter=request.user).exists():
        messages.info(request, "Bu ilan için daha önce bildirim oluşturdun.")
        return redirect(listing.get_absolute_url())

    form = ListingReportForm(request.POST)
    if form.is_valid():
        report = form.save(commit=False)
        report.listing = listing
        report.reporter = request.user
        report.save()
        messages.success(request, "Bildirimin güvenlik ekibine iletildi.")
    else:
        messages.error(request, "Şikâyet bilgilerini kontrol et.")
    return redirect(listing.get_absolute_url())


class ModerationDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "listings/moderation_dashboard.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pending_listings"] = (
            Listing.objects.filter(status=Listing.Status.REVIEW)
            .select_related("owner", "category")
            .prefetch_related("images")[:50]
        )
        context["open_reports"] = (
            ListingReport.objects.filter(
                status__in=[ListingReport.Status.OPEN, ListingReport.Status.REVIEWING]
            )
            .select_related("listing", "reporter")[:50]
        )
        return context


@user_passes_test(lambda user: user.is_authenticated and user.is_staff)
@require_POST
def moderate_listing(request, pk, action):
    listing = get_object_or_404(Listing, pk=pk)
    note = request.POST.get("review_note", "").strip()[:2000]
    if action == "approve":
        listing.status = Listing.Status.PUBLISHED
        listing.published_at = timezone.now()
        title = "İlanın onaylandı"
        body = "İlanın güvenlik incelemesinden geçti ve yayına alındı."
    elif action == "reject":
        listing.status = Listing.Status.REJECTED
        title = "İlanın için düzenleme gerekiyor"
        body = note or "İlanın güvenlik incelemesinde onaylanmadı. Ayrıntıları kontrol et."
    else:
        messages.error(request, "Geçersiz moderasyon işlemi.")
        return redirect("listings:moderation")

    listing.review_note = note
    listing.moderated_by = request.user
    listing.moderated_at = timezone.now()
    listing.save(
        update_fields=[
            "status",
            "published_at",
            "review_note",
            "moderated_by",
            "moderated_at",
            "updated_at",
        ]
    )
    create_notification(
        user=listing.owner,
        actor=request.user,
        listing=listing,
        notification_type=Notification.Type.LISTING_STATUS,
        title=title,
        body=body,
        link=listing.get_absolute_url(),
    )
    messages.success(request, f"{listing.title} için işlem tamamlandı.")
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
    messages.success(request, "Şikâyet durumu güncellendi.")
    return redirect("listings:moderation")


@require_GET
def location_suggestions(request):
    city = request.GET.get("city", "").strip()
    district = request.GET.get("district", "").strip()
    return JsonResponse(
        {
            "districts": list(get_districts(city)),
            "neighborhoods": list(get_neighborhoods(city, district)),
        }
    )
