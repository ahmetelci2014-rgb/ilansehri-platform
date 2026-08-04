from django.contrib.sitemaps import Sitemap
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.listings.models import Listing


class StaticViewSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return [
            "core:home",
            "listings:list",
            "core:about",
            "core:how_it_works",
            "core:trust",
        ]

    def location(self, item):
        return reverse(item)


class KindLandingSitemap(Sitemap):
    priority = 0.8
    changefreq = "daily"

    def items(self):
        return [choice for choice, _label in Listing.Kind.choices]

    def location(self, item):
        return reverse("listings:kind_landing", kwargs={"kind": item})


class ListingSitemap(Sitemap):
    priority = 0.9
    changefreq = "daily"

    def items(self):
        return Listing.objects.filter(status=Listing.Status.PUBLISHED).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).order_by("-updated_at")

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {
    "static": StaticViewSitemap,
    "categories": KindLandingSitemap,
    "listings": ListingSitemap,
}
