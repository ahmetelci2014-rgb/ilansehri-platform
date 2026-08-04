from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from .forms import ListingForm
from .models import Listing


class ListingListView(ListView):
    model = Listing
    template_name = "listings/list.html"
    context_object_name = "listings"
    paginate_by = 24

    def get_queryset(self):
        qs = Listing.objects.filter(status=Listing.Status.PUBLISHED).select_related("owner", "category")
        q = self.request.GET.get("q", "").strip()
        city = self.request.GET.get("city", "").strip()
        kind = self.request.GET.get("kind", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if city:
            qs = qs.filter(city__iexact=city)
        if kind:
            qs = qs.filter(kind=kind)
        return qs


class ListingDetailView(DetailView):
    queryset = Listing.objects.filter(status=Listing.Status.PUBLISHED).select_related("owner", "category")
    template_name = "listings/detail.html"
    context_object_name = "listing"


class ListingCreateView(LoginRequiredMixin, CreateView):
    model = Listing
    form_class = ListingForm
    template_name = "listings/form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.status = Listing.Status.REVIEW
        return super().form_valid(form)
