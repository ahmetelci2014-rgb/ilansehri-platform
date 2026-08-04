from django.urls import path

from . import views

app_name = "ai_listing"

urlpatterns = [
    path("durum/", views.availability, name="availability"),
    path("analiz/", views.analyze, name="analyze"),
    path("analiz/<uuid:public_id>/", views.analysis_detail, name="analysis_detail"),
]
