from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

from apps.listings.models import (
    Conversation,
    Favorite,
    Listing,
    Notification,
    Offer,
    Review,
    SavedSearch,
    Transaction,
)
from apps.listings.services import assess_listing_quality, create_notification

from .delivery import send_phone_verification_code
from .forms import ProfileForm, SignUpForm, VerificationConfirmForm, VerificationStartForm
from .models import User, UserBlock, UserFollow, VerificationCode


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
        context["recent_notifications"] = Notification.objects.filter(user=user)[:8]
        context["unread_notification_count"] = Notification.objects.filter(user=user, is_read=False).count()
        return context


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
        if self.request.user.is_authenticated and self.request.user != self.object:
            context["is_blocked"] = UserBlock.objects.filter(blocker=self.request.user, blocked=self.object).exists()
            context["is_following"] = UserFollow.objects.filter(
                follower=self.request.user, seller=self.object
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
