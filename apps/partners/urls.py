from django.urls import path

from .views import (
    OpenTaskListView,
    PartnerApplyView,
    PartnerDashboardView,
    PartnerProfileUpdateView,
    PartnerStaffBoardView,
    TaskCreateView,
    TaskDetailView,
    apply_task,
    partner_profile_action,
    task_action,
)

app_name = "partners"
urlpatterns = [
    path("basvuru/", PartnerApplyView.as_view(), name="apply"),
    path("profil/", PartnerProfileUpdateView.as_view(), name="profile_edit"),
    path("panelim/", PartnerDashboardView.as_view(), name="dashboard"),
    path("gorevler/", OpenTaskListView.as_view(), name="task_list"),
    path("gorev-yeni/<int:managed_request_id>/", TaskCreateView.as_view(), name="task_create"),
    path("gorevler/<int:pk>/", TaskDetailView.as_view(), name="task_detail"),
    path("gorevler/<int:pk>/basvur/", apply_task, name="apply_task"),
    path("gorevler/<int:pk>/<str:action>/", task_action, name="task_action"),
    path("ekip/", PartnerStaffBoardView.as_view(), name="staff_board"),
    path("ekip/profil/<int:pk>/<str:action>/", partner_profile_action, name="profile_action"),
]
