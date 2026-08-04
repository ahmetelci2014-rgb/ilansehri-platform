from django.urls import path

from .views import DashboardView, SignUpView

app_name = "accounts"

urlpatterns = [
    path("kayit/", SignUpView.as_view(), name="signup"),
    path("hesabim/", DashboardView.as_view(), name="dashboard"),
]
