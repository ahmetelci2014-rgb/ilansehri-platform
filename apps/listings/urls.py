from django.urls import path

from .views import ListingCreateView, ListingDetailView, ListingListView, ListingUpdateView

app_name = "listings"

urlpatterns = [
    path("", ListingListView.as_view(), name="list"),
    path("yeni/", ListingCreateView.as_view(), name="create"),
    path("<slug:slug>/duzenle/", ListingUpdateView.as_view(), name="update"),
    path("<slug:slug>/", ListingDetailView.as_view(), name="detail"),
]
