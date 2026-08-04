from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.edit import FormMixin

from apps.managed_services.models import ManagedRequest

from .forms import ListingForm, OfferForm
from .models import Listing, ListingImage


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
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(category__name__icontains=q))
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_offer"] = self.request.user.is_authenticated and self.request.user != self.object.owner
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
            messages.success(self.request, "İlanın oluşturuldu ve Tam Yönetim ekibine iletildi.")
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
        for index, image in enumerate(form.cleaned_data.get("images", []), start=start_index):
            ListingImage.objects.create(
                listing=self.object,
                image=image,
                is_cover=not self.object.images.exists(),
                sort_order=index,
                alt_text=self.object.title,
            )
        messages.success(self.request, "İlan bilgileri güncellendi.")
        return response
