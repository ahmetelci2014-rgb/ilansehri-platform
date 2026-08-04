from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("hesap/", include("django.contrib.auth.urls")),
    path("hesap/", include("apps.accounts.urls")),
    path("", include("apps.core.urls")),
    path("ilanlar/", include("apps.listings.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
