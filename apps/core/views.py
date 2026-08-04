from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.models import User
from apps.listings.models import Listing, Review
from apps.partners.models import PartnerProfile


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        published = Listing.objects.filter(status=Listing.Status.PUBLISHED).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        context["latest_listings"] = published.select_related("category", "owner").prefetch_related("images")[:8]
        context["listing_count"] = published.count()
        context["member_count"] = User.objects.filter(is_active=True).count()
        context["partner_count"] = PartnerProfile.objects.filter(status=PartnerProfile.Status.ACTIVE).count()
        context["review_count"] = Review.objects.filter(is_visible=True).count()
        return context


class StaticPageView(TemplateView):
    pass


def health_check(request):
    return JsonResponse({"status": "ok", "service": "ilansehri", "version": "1.0"})


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
            ],
        }
    )


def service_worker(request):
    script = r'''
const CACHE = "ilansehri-v1";
const CORE = ["/ilanlar/", "/offline/", "/static/css/app.css", "/static/js/app.js", "/static/img/icon-192.svg", "/static/img/icon-512.svg"];
const PRIVATE_PREFIXES = ["/hesap/", "/ilanlar/mesajlar/", "/ilanlar/bildirimler/", "/ilanlar/islem/", "/tam-yonetim/", "/kazanc-agi/panelim/", "/admin/"];
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
