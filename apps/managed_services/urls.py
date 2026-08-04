from django.urls import path

from .views import (
    ManagedRequestDetailView,
    ManagedRequestListView,
    ManagedRequestUpdateView,
    ManagedStaffBoardView,
    ManagedStaffUpdateView,
    add_activity,
)

app_name = "managed_services"

urlpatterns = [
    path("", ManagedRequestListView.as_view(), name="list"),
    path("operasyon/", ManagedStaffBoardView.as_view(), name="staff_board"),
    path("<int:pk>/", ManagedRequestDetailView.as_view(), name="detail"),
    path("<int:pk>/tercihler/", ManagedRequestUpdateView.as_view(), name="update"),
    path("<int:pk>/operasyon-guncelle/", ManagedStaffUpdateView.as_view(), name="staff_update"),
    path("<int:pk>/aktivite/", add_activity, name="add_activity"),
]
