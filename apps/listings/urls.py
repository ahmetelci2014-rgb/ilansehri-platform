from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListView,
    FavoriteListView,
    ListingCreateView,
    ListingDeleteView,
    ListingDetailView,
    ListingListView,
    ListingUpdateView,
    change_listing_status,
    start_conversation,
    toggle_favorite,
)

app_name = "listings"

urlpatterns = [
    path("", ListingListView.as_view(), name="list"),
    path("yeni/", ListingCreateView.as_view(), name="create"),
    path("favorilerim/", FavoriteListView.as_view(), name="favorites"),
    path("mesajlar/", ConversationListView.as_view(), name="conversation_list"),
    path(
        "mesajlar/<int:pk>/",
        ConversationDetailView.as_view(),
        name="conversation_detail",
    ),
    path("<slug:slug>/duzenle/", ListingUpdateView.as_view(), name="update"),
    path("<slug:slug>/sil/", ListingDeleteView.as_view(), name="delete"),
    path(
        "<slug:slug>/durum/<str:action>/",
        change_listing_status,
        name="change_status",
    ),
    path("<slug:slug>/favori/", toggle_favorite, name="toggle_favorite"),
    path("<slug:slug>/mesaj-gonder/", start_conversation, name="start_conversation"),
    path("<slug:slug>/", ListingDetailView.as_view(), name="detail"),
]
