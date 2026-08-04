from django.urls import path

from .views import (
    DashboardView,
    ProfileEditView,
    PublicProfileView,
    SignUpView,
    VerificationCenterView,
    confirm_verification,
    start_verification,
    toggle_block,
)

app_name = "accounts"

urlpatterns = [
    path("kayit/", SignUpView.as_view(), name="signup"),
    path("hesabim/", DashboardView.as_view(), name="dashboard"),
    path("profilim/", ProfileEditView.as_view(), name="profile_edit"),
    path("dogrulama/", VerificationCenterView.as_view(), name="verification"),
    path("dogrulama/baslat/", start_verification, name="verification_start"),
    path("dogrulama/onayla/", confirm_verification, name="verification_confirm"),
    path("kullanici/<str:username>/", PublicProfileView.as_view(), name="public_profile"),
    path("kullanici/<int:pk>/engelle/", toggle_block, name="toggle_block"),
]
