from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, F, Q
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.views.generic.edit import FormMixin

from apps.managed_services.models import ManagedRequest

from .forms import ListingForm, MessageForm, OfferForm
from .models import Conversation, Favorite, Listing, ListingImage, Message


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
        q = self.request.GET.get("q", "").strip()
        city = self.request.GET.get("city", "").strip()
        district = self.request.GET.get("district", "").strip()
        kind = self.request.GET.get("kind", "").strip()
        action = self.request.GET.get("action", "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(category__name__icontains=q)
            )
        if city:
            qs = qs.filter(city__iexact=city)
        if district:
            qs = qs.filter(district__iexact=district)
        if kind:
            qs = qs.filter(kind=kind)
        if action:
            qs = qs.filter(action=action)
        return qs


class ListingDetailView(FormMixin, DetailView):
    queryset = (
        Listing.objects.filter(status=Listing.Status.PUBLISHED)
        .select_related("owner", "category")
        .prefetch_related("images")
    )
    template_name = "listings/detail.html"
    context_object_name = "listing"
    form_class = OfferForm

    def get_success_url(self):
        return reverse("listings:detail", kwargs={"slug": self.object.slug})

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if self.request.method == "GET":
            Listing.objects.filter(pk=obj.pk).update(view_count=F("view_count") + 1)
            obj.view_count += 1
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["can_offer"] = user.is_authenticated and user != self.object.owner
        context["message_form"] = MessageForm()
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
        else:
            messages.success(self.request, "İlanın başarıyla oluşturuldu.")
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
    transitions = {
        "pause": (Listing.Status.PAUSED, "İlan duraklatıldı."),
        "publish": (Listing.Status.PUBLISHED, "İlan yeniden yayına alındı."),
        "complete": (Listing.Status.COMPLETED, "İlan sonuçlandı olarak işaretlendi."),
    }
    if action not in transitions:
        messages.error(request, "Geçersiz ilan işlemi.")
        return redirect("accounts:dashboard")

    status, message = transitions[action]
    listing.status = status
    update_fields = ["status", "updated_at"]
    if status == Listing.Status.PUBLISHED:
        listing.published_at = timezone.now()
        update_fields.append("published_at")
    listing.save(update_fields=update_fields)
    messages.success(request, message)
    return redirect("accounts:dashboard")


@login_required
@require_POST
def toggle_favorite(request, slug):
    listing = get_object_or_404(Listing, slug=slug, status=Listing.Status.PUBLISHED)
    if listing.owner == request.user:
        messages.info(request, "Kendi ilanını favorilere eklemene gerek yok.")
    else:
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            listing=listing,
        )
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
        return Favorite.objects.filter(user=self.request.user, listing__status=Listing.Status.PUBLISHED).select_related(
            "listing",
            "listing__owner",
            "listing__category",
        ).prefetch_related("listing__images")


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
        return redirect(self.get_success_url())
