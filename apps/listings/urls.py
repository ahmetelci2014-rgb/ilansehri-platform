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
    ModerationDashboardView,
    NotificationListView,
    change_listing_status,
    location_suggestions,
    mark_all_notifications_read,
    mark_notification_read,
    moderate_listing,
    moderate_report,
    report_listing,
    start_conversation,
    toggle_favorite,
)

app_name = "listings"

urlpatterns = [
    path("", ListingListView.as_view(), name="list"),
    path("yeni/", ListingCreateView.as_view(), name="create"),
    path("favorilerim/", FavoriteListView.as_view(), name="favorites"),
    path("mesajlar/", ConversationListView.as_view(), name="conversation_list"),
    path("mesajlar/<int:pk>/", ConversationDetailView.as_view(), name="conversation_detail"),
    path("bildirimler/", NotificationListView.as_view(), name="notifications"),
    path("bildirimler/tumunu-oku/", mark_all_notifications_read, name="mark_all_notifications_read"),
    path("bildirimler/<int:pk>/oku/", mark_notification_read, name="mark_notification_read"),
    path("moderasyon/", ModerationDashboardView.as_view(), name="moderation"),
    path("moderasyon/ilan/<int:pk>/<str:action>/", moderate_listing, name="moderate_listing"),
    path("moderasyon/sikayet/<int:pk>/<str:action>/", moderate_report, name="moderate_report"),
    path("konum-onerileri/", location_suggestions, name="location_suggestions"),
    path("<slug:slug>/duzenle/", ListingUpdateView.as_view(), name="update"),
    path("<slug:slug>/sil/", ListingDeleteView.as_view(), name="delete"),
    path("<slug:slug>/durum/<str:action>/", change_listing_status, name="change_status"),
    path("<slug:slug>/favori/", toggle_favorite, name="toggle_favorite"),
    path("<slug:slug>/mesaj-gonder/", start_conversation, name="start_conversation"),
    path("<slug:slug>/sikayet/", report_listing, name="report"),
    path("<slug:slug>/", ListingDetailView.as_view(), name="detail"),
]
