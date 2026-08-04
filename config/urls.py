from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from .sitemaps import sitemaps

admin.site.site_header = "İlan Şehri Yönetim"
admin.site.site_title = "İlan Şehri"
admin.site.index_title = "Operasyon ve Güven Merkezi"

urlpatterns = [
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("admin/", admin.site.urls),
    path("hesap/", include("django.contrib.auth.urls")),
    path("hesap/", include("apps.accounts.urls")),
    path("ilanlar/", include("apps.listings.urls")),
    path("tam-yonetim/", include("apps.managed_services.urls")),
    path("kazanc-agi/", include("apps.partners.urls")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
