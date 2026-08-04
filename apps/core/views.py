from django.views.generic import TemplateView

from apps.listings.models import Listing


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_listings"] = Listing.objects.filter(status=Listing.Status.PUBLISHED).select_related("category", "owner")[:8]
        context["listing_count"] = Listing.objects.filter(status=Listing.Status.PUBLISHED).count()
        return context
