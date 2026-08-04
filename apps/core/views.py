from django.views.generic import TemplateView

from apps.listings.models import Listing


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        published = Listing.objects.filter(status=Listing.Status.PUBLISHED)
        context["latest_listings"] = (
            published.select_related("category", "owner")
            .prefetch_related("images")[:8]
        )
        context["listing_count"] = published.count()
        return context
