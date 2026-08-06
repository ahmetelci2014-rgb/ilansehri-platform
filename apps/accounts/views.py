from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

from apps.listings.models import (
    Conversation,
    Favorite,
    Listing,
    ListingMatch,
    Notification,
    Offer,
    Review,
    SavedSearch,
    Transaction,
)
from apps.listings.services import assess_listing_quality, consume_rate_limit, create_notification
from apps.support_center.models import SupportTicket

from .delivery import send_phone_verification_code
from .trust import build_trust_profile, record_risk_event
from .forms import (
    AccountClosureForm,
    NotificationPreferenceForm,
    ProfileForm,
    SignUpForm,
    VerificationConfirmForm,
    VerificationStartForm,
    UserReportForm,
)
from .models import (
    AccountClosureRequest,
    AccountRiskEvent,
    NotificationPreference,
    User,
    UserBlock,
    UserFollow,
    UserReport,
    VerificationCode,
)


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("accounts:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "İlan Şehri hesabın oluşturuldu. Hoş geldin!")
        return response


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        my_listings = list(
            user.listings.select_related("category", "owner")
            .prefetch_related("images", "price_history")
            .order_by("-updated_at")[:20]
        )
        for listing in my_listings:
            listing.quality_profile = assess_listing_quality(listing)
        context["my_listings"] = my_listings
        context["received_offers"] = Offer.objects.filter(listing__owner=user).select_related("listing", "sender").order_by("-created_at")[:15]
        context["sent_offers"] = user.offers.select_related("listing", "listing__owner")[:15]
        context["managed_requests"] = user.managed_requests.select_related("listing").order_by("-updated_at")[:10]
        context["favorite_items"] = Favorite.objects.filter(user=user, listing__status="published").filter(Q(listing__expires_at__isnull=True) | Q(listing__expires_at__gt=timezone.now())).select_related(
            "listing", "listing__category", "listing__owner"
        ).prefetch_related("listing__images")[:6]
        context["conversations"] = (
            Conversation.objects.filter(Q(buyer=user) | Q(seller=user))
            .select_related("listing", "buyer", "seller")
            .prefetch_related("messages")
            .annotate(
                unread_count=Coalesce(
                    Count("messages", filter=Q(messages__is_read=False) & ~Q(messages__sender=user)),
                    0,
                )
            )
            .order_by("-updated_at")[:8]
        )
        context["transactions"] = Transaction.objects.filter(Q(buyer=user) | Q(seller=user)).select_related(
            "listing", "buyer", "seller"
        )[:12]
        context["saved_searches"] = SavedSearch.objects.filter(user=user)[:10]
        context["favorite_count"] = Favorite.objects.filter(user=user, listing__status="published").filter(Q(listing__expires_at__isnull=True) | Q(listing__expires_at__gt=timezone.now())).count()
        context["unread_message_count"] = sum(item.unread_count for item in context["conversations"])
        active_match_pairs = (
            Q(wanted_listing__status=Listing.Status.PUBLISHED)
            & Q(offered_listing__status=Listing.Status.PUBLISHED)
            & (Q(wanted_listing__expires_at__isnull=True) | Q(wanted_listing__expires_at__gt=timezone.now()))
            & (Q(offered_listing__expires_at__isnull=True) | Q(offered_listing__expires_at__gt=timezone.now()))
        )
        blocked_ids = set(
            UserBlock.objects.filter(blocker=user).values_list("blocked_id", flat=True)
        )
        blocked_ids.update(
            UserBlock.objects.filter(blocked=user).values_list("blocker_id", flat=True)
        )
        wanted_visible = (
            ListingMatch.objects.filter(active_match_pairs, wanted_listing__owner=user)
            .exclude(wanted_status=ListingMatch.Status.DISMISSED)
            .exclude(offered_listing__owner_id__in=blocked_ids)
        )
        offered_visible = (
            ListingMatch.objects.filter(active_match_pairs, offered_listing__owner=user)
            .exclude(offered_status=ListingMatch.Status.DISMISSED)
            .exclude(wanted_listing__owner_id__in=blocked_ids)
        )
        recent_wanted = list(
            wanted_visible.select_related("wanted_listing", "offered_listing").order_by("-created_at")[:6]
        )
        recent_offered = list(
            offered_visible.select_related("wanted_listing", "offered_listing").order_by("-created_at")[:6]
        )
        context["recent_matches"] = sorted(
            recent_wanted + recent_offered,
            key=lambda item: item.created_at,
            reverse=True,
        )[:6]
        context["match_count"] = wanted_visible.count() + offered_visible.count()
        context["new_match_count"] = (
            wanted_visible.filter(wanted_status=ListingMatch.Status.NEW).count()
            + offered_visible.filter(offered_status=ListingMatch.Status.NEW).count()
        )
        context["recent_notifications"] = Notification.objects.filter(user=user)[:8]
        context["unread_notification_count"] = Notification.objects.filter(user=user, is_read=False).count()
        context["listing_drafts"] = user.listing_drafts.select_related("source_listing")[:5]
        context["draft_count"] = user.listing_drafts.count()
        context["open_support_ticket_count"] = user.support_tickets.exclude(
            status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]
        ).count()
        context["recent_support_tickets"] = user.support_tickets.all()[:4]
        profile_steps = [
            {
                "label": "Ad ve soyadını ekle",
                "complete": bool(user.first_name.strip() and user.last_name.strip()),
                "url": reverse("accounts:profile_edit"),
            },
            {
                "label": "Profil fotoğrafı yükle",
                "complete": bool(user.avatar),
                "url": reverse("accounts:profile_edit"),
            },
            {
                "label": "E-posta adresini ekle",
                "complete": bool(user.email.strip()),
                "url": reverse("accounts:profile_edit"),
            },
            {
                "label": "Telefon numaranı ekle",
                "complete": bool(user.phone.strip()),
                "url": reverse("accounts:profile_edit"),
            },
            {
                "label": "Şehir ve ilçeni tamamla",
                "complete": bool(user.city.strip() and user.district.strip()),
                "url": reverse("accounts:profile_edit"),
            },
            {
                "label": "Kısa profil açıklaması yaz",
                "complete": bool(user.bio.strip()),
                "url": reverse("accounts:profile_edit"),
            },
            {
                "label": "Telefonunu doğrula",
                "complete": user.is_phone_verified,
                "url": reverse("accounts:verification"),
            },
            {
                "label": "E-postanı doğrula",
                "complete": user.is_email_verified,
                "url": reverse("accounts:verification"),
            },
        ]
        completed_profile_steps = sum(1 for step in profile_steps if step["complete"])
        context["profile_steps"] = profile_steps
        context["profile_completion"] = round(completed_profile_steps / len(profile_steps) * 100)
        context["profile_next_step"] = next(
            (step for step in profile_steps if not step["complete"]),
            None,
        )
        return context


class AccountSettingsView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_item = AccountClosureRequest.objects.filter(user=self.request.user).first()
        context["closure_request"] = request_item
        context["closure_form"] = AccountClosureForm(user=self.request.user)
        return context


class NotificationPreferenceView(LoginRequiredMixin, UpdateView):
    model = NotificationPreference
    form_class = NotificationPreferenceForm
    template_name = "accounts/notification_preferences.html"
    success_url = reverse_lazy("accounts:notification_preferences")

    def get_object(self, queryset=None):
        preference, _ = NotificationPreference.objects.get_or_create(user=self.request.user)
        return preference

    def form_valid(self, form):
        messages.success(self.request, "Bildirim tercihlerin kaydedildi.")
        return super().form_valid(form)


@login_required
def export_account_data(request):
    user = request.user
    notification_preferences, _ = NotificationPreference.objects.get_or_create(user=user)
    conversations = []
    for conversation in (
        Conversation.objects.filter(Q(buyer=user) | Q(seller=user))
        .select_related("listing", "buyer", "seller")
        .prefetch_related("messages__sender")
    ):
        conversations.append(
            {
                "listing": conversation.listing.title,
                "buyer": conversation.buyer.username,
                "seller": conversation.seller.username,
                "created_at": conversation.created_at,
                "messages": [
                    {
                        "sender": item.sender.username,
                        "body": item.body,
                        "created_at": item.created_at,
                    }
                    for item in conversation.messages.all()
                ],
            }
        )

    data = {
        "generated_at": timezone.now(),
        "notification_preferences": {
            "in_app_messages": notification_preferences.in_app_messages,
            "in_app_offers": notification_preferences.in_app_offers,
            "in_app_price_drops": notification_preferences.in_app_price_drops,
            "in_app_follows": notification_preferences.in_app_follows,
            "in_app_matches": notification_preferences.in_app_matches,
            "in_app_reviews": notification_preferences.in_app_reviews,
            "email_messages": notification_preferences.email_messages,
            "email_offers": notification_preferences.email_offers,
            "email_transactions": notification_preferences.email_transactions,
            "email_listing_updates": notification_preferences.email_listing_updates,
            "email_price_drops": notification_preferences.email_price_drops,
            "email_follows": notification_preferences.email_follows,
            "email_matches": notification_preferences.email_matches,
            "email_reviews": notification_preferences.email_reviews,
            "email_system": notification_preferences.email_system,
            "digest_frequency": notification_preferences.digest_frequency,
        },
        "profile": {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "user_type": user.user_type,
            "city": user.city,
            "district": user.district,
            "neighborhood": user.neighborhood,
            "bio": user.bio,
            "is_phone_verified": user.is_phone_verified,
            "is_email_verified": user.is_email_verified,
            "date_joined": user.date_joined,
            "last_login": user.last_login,
        },
        "listings": list(
            user.listings.values(
                "id", "title", "slug", "status", "kind", "action", "price", "city",
                "district", "created_at", "updated_at"
            )
        ),
        "drafts": list(user.listing_drafts.values("id", "title", "data", "created_at", "updated_at")),
        "sent_offers": list(
            user.offers.values("id", "listing__title", "amount", "message", "status", "created_at")
        ),
        "received_offers": list(
            Offer.objects.filter(listing__owner=user).values(
                "id", "listing__title", "sender__username", "amount", "message", "status", "created_at"
            )
        ),
        "transactions": list(
            Transaction.objects.filter(Q(buyer=user) | Q(seller=user)).values(
                "public_id", "listing__title", "buyer__username", "seller__username",
                "amount", "status", "delivery_type", "delivery_started_at",
                "handover_verified_at", "buyer_confirmed_at", "seller_confirmed_at",
                "created_at", "completed_at"
            )
        ),
        "reviews_written": list(
            user.written_reviews.values(
                "transaction__listing__title", "reviewed_user__username", "rating", "comment",
                "is_visible", "published_at", "created_at"
            )
        ),
        "favorites": list(
            Favorite.objects.filter(user=user).values("listing__title", "listing__slug", "created_at")
        ),
        "saved_searches": list(
            SavedSearch.objects.filter(user=user).values("name", "query_params", "alert_enabled", "created_at")
        ),
        "submitted_user_reports": list(
            UserReport.objects.filter(reporter=user).values(
                "reported_user__username",
                "related_listing__title",
                "reason",
                "details",
                "status",
                "created_at",
                "reviewed_at",
            )
        ),
        "submitted_listing_reports": list(
            user.listing_reports.values(
                "listing__title",
                "reason",
                "details",
                "status",
                "created_at",
                "reviewed_at",
            )
        ),
        "listing_matches": list(
            ListingMatch.objects.filter(Q(wanted_listing__owner=user) | Q(offered_listing__owner=user)).values(
                "wanted_listing__title",
                "offered_listing__title",
                "score",
                "reasons",
                "wanted_status",
                "offered_status",
                "created_at",
            )
        ),
        "conversations": conversations,
    }
    response = JsonResponse(
        data,
        encoder=DjangoJSONEncoder,
        json_dumps_params={"ensure_ascii": False, "indent": 2},
    )
    response["Content-Disposition"] = 'attachment; filename="ilan-sehri-hesap-verilerim.json"'
    response["Cache-Control"] = "no-store, private"
    return response


@require_POST
def request_account_closure(request):
    if not request.user.is_authenticated:
        return redirect("login")
    form = AccountClosureForm(request.POST, user=request.user)
    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        return redirect("accounts:settings")
    closure, _ = AccountClosureRequest.objects.get_or_create(user=request.user)
    closure.reason = form.cleaned_data["reason"]
    closure.status = AccountClosureRequest.Status.PENDING
    closure.resolved_at = None
    closure.resolved_by = None
    closure.save()
    messages.success(request, "Hesap kapatma talebin alındı. İnceleme tamamlanana kadar hesabın açık kalır.")
    return redirect("accounts:settings")


@require_POST
def cancel_account_closure(request):
    if not request.user.is_authenticated:
        return redirect("login")
    closure = get_object_or_404(AccountClosureRequest, user=request.user)
    if closure.status == AccountClosureRequest.Status.PENDING:
        closure.status = AccountClosureRequest.Status.CANCELLED
        closure.save(update_fields=["status", "updated_at"])
        messages.success(request, "Hesap kapatma talebin iptal edildi.")
    return redirect("accounts:settings")


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = "accounts/profile_edit.html"
    success_url = reverse_lazy("accounts:dashboard")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        previous_phone = User.objects.get(pk=self.request.user.pk).phone
        previous_email = User.objects.get(pk=self.request.user.pk).email
        response = super().form_valid(form)
        update_fields = []
        if previous_phone != self.object.phone and self.object.is_phone_verified:
            self.object.is_phone_verified = False
            self.object.verification_level = User.VerificationLevel.BASIC
            update_fields.extend(["is_phone_verified", "verification_level"])
        if previous_email.lower() != self.object.email.lower() and self.object.is_email_verified:
            self.object.is_email_verified = False
            update_fields.append("is_email_verified")
        if update_fields:
            self.object.save(update_fields=update_fields)
        messages.success(self.request, "Profil bilgilerin güncellendi.")
        return response


class PublicProfileView(DetailView):
    model = User
    template_name = "accounts/public_profile.html"
    context_object_name = "profile_user"
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_queryset(self):
        return User.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["published_listings"] = self.object.listings.filter(status="published").filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).select_related("category", "owner").prefetch_related("images", "price_history")[:12]
        context["reviews"] = Review.objects.filter(reviewed_user=self.object, is_visible=True).select_related("reviewer", "transaction__listing")[:20]
        context["compare_ids"] = set(self.request.session.get("compare_listing_ids", []))
        context["favorite_ids"] = (
            set(Favorite.objects.filter(user=self.request.user).values_list("listing_id", flat=True))
            if self.request.user.is_authenticated
            else set()
        )
        context["follower_count"] = UserFollow.objects.filter(seller=self.object).count()
        context["following_count"] = UserFollow.objects.filter(follower=self.object).count()
        context["is_following"] = False
        context["trust_profile"] = build_trust_profile(
            self.object, include_private=bool(self.request.user.is_authenticated and self.request.user.is_staff)
        )
        context["user_report_form"] = UserReportForm()
        context["can_report_user"] = False
        if self.request.user.is_authenticated and self.request.user != self.object:
            context["is_blocked"] = UserBlock.objects.filter(blocker=self.request.user, blocked=self.object).exists()
            context["is_following"] = UserFollow.objects.filter(
                follower=self.request.user, seller=self.object
            ).exists()
            context["can_report_user"] = not UserReport.objects.filter(
                reporter=self.request.user,
                reported_user=self.object,
                status__in=[UserReport.Status.OPEN, UserReport.Status.REVIEWING],
            ).exists()
        return context


class FollowingListView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/following.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        follows = UserFollow.objects.filter(follower=self.request.user).select_related("seller")
        seller_ids = list(follows.values_list("seller_id", flat=True))
        context["follows"] = follows
        context["followed_listings"] = (
            Listing.objects.filter(owner_id__in=seller_ids, status=Listing.Status.PUBLISHED)
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
            .select_related("owner", "category")
            .prefetch_related("images", "price_history")
            .order_by("-published_at", "-created_at")[:24]
        )
        context["favorite_ids"] = set(
            Favorite.objects.filter(user=self.request.user).values_list("listing_id", flat=True)
        )
        context["compare_ids"] = set(self.request.session.get("compare_listing_ids", []))
        return context


@require_POST
def toggle_follow(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    seller = get_object_or_404(User, pk=pk, is_active=True)
    if seller == request.user:
        messages.warning(request, "Kendi hesabını takip edemezsin.")
        return redirect("accounts:public_profile", username=seller.username)
    follow, created = UserFollow.objects.get_or_create(follower=request.user, seller=seller)
    if created:
        messages.success(request, f"{seller.display_name} takip ediliyor.")
        create_notification(
            user=seller,
            actor=request.user,
            notification_type=Notification.Type.FOLLOW,
            title="Yeni takipçin var",
            body=f"{request.user.display_name} mağazanı takip etmeye başladı.",
            link=reverse("accounts:public_profile", kwargs={"username": request.user.username}),
        )
    else:
        follow.delete()
        messages.info(request, f"{seller.display_name} takibi bırakıldı.")
    return redirect("accounts:public_profile", username=seller.username)


class VerificationCenterView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/verification.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["start_form"] = VerificationStartForm(user=self.request.user)
        context["confirm_form"] = VerificationConfirmForm()
        context["latest_codes"] = self.request.user.verification_codes.all()[:5]
        return context


@require_POST
def start_verification(request):
    if not request.user.is_authenticated:
        return redirect("login")
    form = VerificationStartForm(request.POST, user=request.user)
    if not form.is_valid():
        messages.error(request, form.errors.as_text())
        return redirect("accounts:verification")
    channel = form.cleaned_data["channel"]
    destination = request.user.phone if channel == VerificationCode.Channel.PHONE else request.user.email
    latest = request.user.verification_codes.filter(channel=channel).first()
    if latest and latest.created_at > timezone.now() - timedelta(seconds=60):
        messages.warning(request, "Yeni kod istemeden önce 60 saniye beklemelisin.")
        return redirect("accounts:verification")
    raw_code = f"{secrets.randbelow(1_000_000):06d}"
    verification = VerificationCode.issue(user=request.user, channel=channel, destination=destination, raw_code=raw_code)

    delivered = True
    if channel == VerificationCode.Channel.EMAIL and destination:
        delivered = bool(
            send_mail(
                "İlan Şehri doğrulama kodu",
                f"Doğrulama kodun: {raw_code}. Kod 10 dakika geçerlidir.",
                settings.DEFAULT_FROM_EMAIL,
                [destination],
                fail_silently=True,
            )
        ) or settings.VERIFICATION_DEBUG_CODE
    elif channel == VerificationCode.Channel.PHONE:
        delivered = send_phone_verification_code(destination=destination, code=raw_code)
    if not delivered:
        verification.delete()
        messages.error(request, "Doğrulama servisine ulaşılamadı. Bir süre sonra yeniden dene.")
        return redirect("accounts:verification")
    if settings.VERIFICATION_DEBUG_CODE:
        messages.info(request, f"Geliştirme doğrulama kodu: {raw_code}")
    else:
        messages.success(request, "Doğrulama kodu gönderildi. Kod 10 dakika geçerlidir.")
    request.session["verification_channel"] = channel
    return redirect("accounts:verification")


@require_POST
def confirm_verification(request):
    if not request.user.is_authenticated:
        return redirect("login")
    data = request.POST.copy()
    data["channel"] = data.get("channel") or request.session.get("verification_channel", "")
    form = VerificationConfirmForm(data)
    if not form.is_valid():
        messages.error(request, "Doğrulama kodunu kontrol et.")
        return redirect("accounts:verification")
    code = request.user.verification_codes.filter(
        channel=form.cleaned_data["channel"],
        consumed_at__isnull=True,
    ).first()
    if not code or not code.verify(form.cleaned_data["code"]):
        messages.error(request, "Kod geçersiz, süresi dolmuş veya deneme sınırı aşılmış.")
        return redirect("accounts:verification")
    if code.channel == VerificationCode.Channel.PHONE:
        request.user.is_phone_verified = True
        request.user.verification_level = User.VerificationLevel.PHONE
        fields = ["is_phone_verified", "verification_level"]
    else:
        request.user.is_email_verified = True
        fields = ["is_email_verified"]
    request.user.save(update_fields=fields)
    messages.success(request, f"{code.get_channel_display()} doğrulaması tamamlandı.")
    return redirect("accounts:verification")


@require_POST
def report_user(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    target = get_object_or_404(User, pk=pk, is_active=True)
    target_url = reverse("accounts:public_profile", kwargs={"username": target.username})
    if target == request.user:
        messages.warning(request, "Kendi hesabını şikâyet edemezsin.")
        return redirect(target_url)
    if not consume_rate_limit(request, "user_report", limit=5, period=3600):
        messages.error(request, "Şikâyet gönderme sınırına ulaştın. Daha sonra tekrar dene.")
        return redirect(target_url)
    if UserReport.objects.filter(
        reporter=request.user,
        reported_user=target,
        status__in=[UserReport.Status.OPEN, UserReport.Status.REVIEWING],
    ).exists():
        messages.info(request, "Bu kullanıcı için açık bir şikâyet kaydın zaten var.")
        return redirect(target_url)
    form = UserReportForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Şikâyet bilgilerini kontrol et.")
        return redirect(target_url)
    report = form.save(commit=False)
    report.reporter = request.user
    report.reported_user = target
    related_listing_id = request.POST.get("related_listing", "").strip()
    if related_listing_id:
        report.related_listing = Listing.objects.filter(pk=related_listing_id, owner=target).first()
    report.save()
    severity = (
        AccountRiskEvent.Severity.HIGH
        if report.reason in {UserReport.Reason.FRAUD, UserReport.Reason.HARASSMENT, UserReport.Reason.PROHIBITED}
        else AccountRiskEvent.Severity.MEDIUM
    )
    record_risk_event(
        subject_user=target,
        event_type=AccountRiskEvent.EventType.USER_REPORT,
        severity=severity,
        fingerprint=f"user-report:{report.pk}",
        summary=f"Kullanıcı şikâyeti: {report.get_reason_display()}",
        listing=report.related_listing,
        user_report=report,
        details={"reason": report.reason, "details": report.details[:500]},
    )
    messages.success(request, "Şikâyetin güvenlik ekibine gönderildi.")
    return redirect(target_url)


@require_POST
def toggle_block(request, pk):
    if not request.user.is_authenticated:
        return redirect("login")
    target = get_object_or_404(User, pk=pk, is_active=True)
    if target == request.user:
        messages.warning(request, "Kendini engelleyemezsin.")
        return redirect("accounts:dashboard")
    block, created = UserBlock.objects.get_or_create(blocker=request.user, blocked=target)
    if created:
        messages.success(request, f"{target.display_name} engellendi.")
    else:
        block.delete()
        messages.success(request, f"{target.display_name} engeli kaldırıldı.")
    return redirect(reverse("accounts:public_profile", kwargs={"username": target.username}))
