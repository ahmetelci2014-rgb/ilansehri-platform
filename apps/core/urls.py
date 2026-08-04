from django.urls import path

from .views import HomeView, StaffDashboardView, StaticPageView, health_check, manifest, service_worker

app_name = "core"
urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("yonetim/", StaffDashboardView.as_view(), name="staff_dashboard"),
    path("hakkimizda/", StaticPageView.as_view(template_name="core/about.html"), name="about"),
    path("nasil-calisir/", StaticPageView.as_view(template_name="core/how_it_works.html"), name="how_it_works"),
    path("guven-merkezi/", StaticPageView.as_view(template_name="core/trust.html"), name="trust"),
    path("kullanim-kosullari/", StaticPageView.as_view(template_name="core/terms.html"), name="terms"),
    path("gizlilik/", StaticPageView.as_view(template_name="core/privacy.html"), name="privacy"),
    path("kvkk/", StaticPageView.as_view(template_name="core/kvkk.html"), name="kvkk"),
    path("cerezler/", StaticPageView.as_view(template_name="core/cookies.html"), name="cookies"),
    path("offline/", StaticPageView.as_view(template_name="core/offline.html"), name="offline"),
    path("manifest.webmanifest", manifest, name="manifest"),
    path("service-worker.js", service_worker, name="service_worker"),
    path("health/", health_check, name="health"),
]
