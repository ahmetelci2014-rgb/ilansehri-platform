from datetime import timedelta
from django.contrib import admin
from django.utils import timezone

from .models import (
    Category,
    Conversation,
    Favorite,
    Listing,
    ListingDraft,
    ListingImage,
    ListingMatch,
    ListingPriceHistory,
    ListingReport,
    Message,
    Notification,
    Offer,
    OfferEvent,
    Review,
    SavedSearch,
    SavedSearchMatch,
    Transaction,
    TransactionEvent,
)
from .matching import sync_listing_matches
from .services import (
    create_notification,
    notify_listing_publication,
    notify_price_drop_favorites,
)


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0
    readonly_fields = ("fingerprint",)


class OfferInline(admin.TabularInline):
    model = Offer
    extra = 0
    readonly_fields = ("created_at", "updated_at", "responded_at")


@admin.register(ListingDraft)
class ListingDraftAdmin(admin.ModelAdmin):
    list_display = ("display_title", "user", "source_listing", "updated_at")
    search_fields = ("title", "user__username", "source_listing__title")
    readonly_fields = ("created_at", "updated_at")


@admin.action(description="Seçili ilanları onayla ve yayınla")
def approve_listings(modeladmin, request, queryset):
    for listing in queryset.select_related("owner"):
        listing.status = Listing.Status.PUBLISHED
        listing.published_at = timezone.now()
        listing.expires_at = timezone.now() + timedelta(days=60)
        listing.moderated_at = timezone.now()
        listing.moderated_by = request.user
        listing.review_note = ""
        listing.save()
        notify_listing_publication(listing)
        latest_price_change = listing.price_history.filter(
            notifications_sent_at__isnull=True
        ).first()
        if latest_price_change:
            notify_price_drop_favorites(latest_price_change)
        create_notification(
            user=listing.owner,
            actor=request.user,
            listing=listing,
            notification_type=Notification.Type.LISTING_STATUS,
            title="İlanın onaylandı",
            body="İlanın güvenlik incelemesinden geçti ve yayına alındı.",
            link=listing.get_absolute_url(),
        )


@admin.action(description="Seçili ilanları reddet")
def reject_listings(modeladmin, request, queryset):
    for listing in queryset.select_related("owner"):
        listing.status = Listing.Status.REJECTED
        listing.moderated_at = timezone.now()
        listing.moderated_by = request.user
        listing.save()
        sync_listing_matches(listing, notify=False)
        create_notification(
            user=listing.owner,
            actor=request.user,
            listing=listing,
            notification_type=Notification.Type.LISTING_STATUS,
            title="İlanın için düzenleme gerekiyor",
            body=listing.review_note or "İlanın güvenlik incelemesinde onaylanmadı.",
            link=listing.get_absolute_url(),
        )


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "kind", "action", "city", "status", "management_mode", "view_count", "created_at")
    list_filter = ("kind", "action", "management_mode", "status", "city", "is_featured")
    search_fields = ("title", "description", "owner__username", "brand", "model_name", "city", "district")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "published_at", "moderated_at", "view_count", "favorite_count")
    actions = (approve_listings, reject_listings)
    inlines = (ListingImageInline, OfferInline)


class TransactionEventInline(admin.TabularInline):
    model = TransactionEvent
    extra = 0
    can_delete = False
    readonly_fields = ("event_type", "actor", "note", "metadata", "created_at")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("public_id", "listing", "buyer", "seller", "amount", "status", "delivery_type", "created_at")
    list_filter = ("status", "delivery_type", "buyer_confirmed", "seller_confirmed")
    search_fields = ("public_id", "listing__title", "buyer__username", "seller__username")
    readonly_fields = (
        "public_id", "created_at", "updated_at", "delivery_started_at", "handover_verified_at",
        "buyer_confirmed_at", "seller_confirmed_at", "completed_at", "cancelled_at",
    )
    inlines = (TransactionEventInline,)


@admin.register(TransactionEvent)
class TransactionEventAdmin(admin.ModelAdmin):
    list_display = ("transaction", "event_type", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("transaction__public_id", "transaction__listing__title", "actor__username", "note")
    readonly_fields = ("transaction", "event_type", "actor", "note", "metadata", "created_at")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("reviewed_user", "reviewer", "rating", "is_visible", "published_at", "created_at")
    list_filter = ("rating", "is_visible")
    search_fields = ("reviewed_user__username", "reviewer__username", "comment")


@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    list_display = ("listing", "reporter", "reason", "status", "created_at")
    list_filter = ("reason", "status")
    search_fields = ("listing__title", "reporter__username", "details")


@admin.register(ListingMatch)
class ListingMatchAdmin(admin.ModelAdmin):
    list_display = ("wanted_listing", "offered_listing", "score", "wanted_status", "offered_status", "created_at")
    list_filter = ("wanted_status", "offered_status", "score")
    search_fields = ("wanted_listing__title", "offered_listing__title")
    readonly_fields = ("created_at", "updated_at", "notified_wanted_at", "notified_offered_at")


admin.site.register(Category)
@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ("listing", "is_cover", "duplicate_owner_count", "created_at")
    search_fields = ("listing__title", "listing__owner__username", "fingerprint")
    readonly_fields = ("fingerprint", "duplicate_owner_count", "created_at")

admin.site.register(Offer)
admin.site.register(Favorite)


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "alert_frequency", "alert_enabled", "last_checked_at", "last_notified_at", "created_at")
    list_filter = ("alert_frequency", "alert_enabled")
    search_fields = ("name", "user__username", "user__email")
    readonly_fields = ("alert_enabled", "created_at", "updated_at", "last_checked_at", "last_notified_at")


@admin.register(SavedSearchMatch)
class SavedSearchMatchAdmin(admin.ModelAdmin):
    list_display = ("saved_search", "listing", "notified_at", "created_at")
    list_filter = ("notified_at",)
    search_fields = ("saved_search__name", "saved_search__user__username", "listing__title")
    readonly_fields = ("created_at", "notified_at")


admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(Notification)

admin.site.register(ListingPriceHistory)
admin.site.register(OfferEvent)
