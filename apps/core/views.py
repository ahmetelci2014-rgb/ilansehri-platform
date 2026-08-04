from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.models import User
from apps.listings.models import Favorite, Listing, ListingReport, Review, Transaction
from apps.managed_services.models import ManagedRequest
from apps.partners.models import PartnerProfile, Task


def _active_listing_q():
    return Q(status=Listing.Status.PUBLISHED) & (
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    )


def _listing_queryset():
    return (
        Listing.objects.filter(_active_listing_q())
        .select_related("category", "owner")
        .prefetch_related("images")
    )


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        published = _listing_queryset()
        preferred_city = (self.request.GET.get("city") or "").strip()
        if not preferred_city and self.request.user.is_authenticated:
            preferred_city = self.request.user.city.strip()

        nearby = published.filter(city__iexact=preferred_city) if preferred_city else published
        if preferred_city and not nearby.exists():
            nearby = published

        latest = list(nearby.order_by("-is_featured", "-published_at", "-created_at")[:12])
        popular = list(published.order_by("-view_count", "-favorite_count", "-created_at")[:10])
        vehicles = list(published.filter(kind=Listing.Kind.VEHICLE).order_by("-is_featured", "-created_at")[:10])
        estates = list(published.filter(kind=Listing.Kind.REAL_ESTATE).order_by("-is_featured", "-created_at")[:10])
        services = list(published.filter(kind=Listing.Kind.SERVICE).order_by("-is_featured", "-created_at")[:10])

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
        context.update(
            {
                "preferred_city": preferred_city,
                "latest_listings": latest,
                "popular_listings": popular,
                "vehicle_listings": vehicles,
                "estate_listings": estates,
                "service_listings": services,
                "recently_viewed": recently_viewed,
                "favorite_ids": favorite_ids,
                "compare_ids": set(self.request.session.get("compare_listing_ids", [])),
                "category_tiles": [
                    {"kind": Listing.Kind.PRODUCT, "label": "Ürün & Eşya", "icon": "📱", "count": kind_counts.get(Listing.Kind.PRODUCT, 0)},
                    {"kind": Listing.Kind.VEHICLE, "label": "Araç", "icon": "🚗", "count": kind_counts.get(Listing.Kind.VEHICLE, 0)},
                    {"kind": Listing.Kind.REAL_ESTATE, "label": "Emlak", "icon": "🏠", "count": kind_counts.get(Listing.Kind.REAL_ESTATE, 0)},
                    {"kind": Listing.Kind.SERVICE, "label": "Hizmet", "icon": "🛠️", "count": kind_counts.get(Listing.Kind.SERVICE, 0)},
                    {"kind": Listing.Kind.JOB, "label": "İş", "icon": "💼", "count": kind_counts.get(Listing.Kind.JOB, 0)},
                    {"kind": Listing.Kind.NEED, "label": "Arıyorum", "icon": "📣", "count": kind_counts.get(Listing.Kind.NEED, 0)},
                ],
                "listing_count": published.count(),
                "member_count": User.objects.filter(is_active=True).count(),
                "partner_count": PartnerProfile.objects.filter(status=PartnerProfile.Status.ACTIVE).count(),
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

        context.update(
            {
                "stats": {
                    "active_listings": Listing.objects.filter(_active_listing_q()).count(),
                    "pending_listings": Listing.objects.filter(status=Listing.Status.REVIEW).count(),
                    "users": User.objects.filter(is_active=True).count(),
                    "open_reports": ListingReport.objects.filter(
                        status__in=[ListingReport.Status.OPEN, ListingReport.Status.REVIEWING]
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
            }
        )
        return context


class StaticPageView(TemplateView):
    pass


def health_check(request):
    return JsonResponse({"status": "ok", "service": "ilansehri", "version": "1.2"})


def manifest(request):
    return JsonResponse(
        {
            "name": "İlan Şehri",
            "short_name": "İlan Şehri",
            "description": "Şehrindeki ürün, hizmet, iş ve ihtiyaçları buluşturan güven odaklı yerel pazar.",
            "start_url": "/?source=pwa",
            "scope": "/",
            "display": "standalone",
            "background_color": "#f7faf9",
            "theme_color": "#0f766e",
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
            ],
        }
    )


def service_worker(request):
    script = r'''
const CACHE = "ilansehri-v12";
const CORE = ["/ilanlar/", "/offline/", "/static/css/app.css", "/static/js/app.js", "/static/img/icon-192.svg", "/static/img/icon-512.svg"];
const PRIVATE_PREFIXES = ["/hesap/", "/ilanlar/mesajlar/", "/ilanlar/bildirimler/", "/ilanlar/islem/", "/tam-yonetim/", "/kazanc-agi/panelim/", "/admin/", "/yonetim/"];
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
'''
    response = HttpResponse(script, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response
