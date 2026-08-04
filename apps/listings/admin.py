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
    ListingPriceHistory,
    ListingReport,
    Message,
    Notification,
    Offer,
    OfferEvent,
    Review,
    SavedSearch,
    Transaction,
)
from .services import (
    create_notification,
    notify_followers_new_listing,
    notify_price_drop_favorites,
)


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0


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
        notify_followers_new_listing(listing)
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


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("public_id", "listing", "buyer", "seller", "amount", "status", "created_at")
    list_filter = ("status", "buyer_confirmed", "seller_confirmed")
    search_fields = ("public_id", "listing__title", "buyer__username", "seller__username")
    readonly_fields = ("public_id", "created_at", "updated_at", "completed_at", "cancelled_at")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("reviewed_user", "reviewer", "rating", "is_visible", "created_at")
    list_filter = ("rating", "is_visible")
    search_fields = ("reviewed_user__username", "reviewer__username", "comment")


@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    list_display = ("listing", "reporter", "reason", "status", "created_at")
    list_filter = ("reason", "status")
    search_fields = ("listing__title", "reporter__username", "details")


admin.site.register(Category)
admin.site.register(ListingImage)
admin.site.register(Offer)
admin.site.register(Favorite)
admin.site.register(SavedSearch)
admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(Notification)

admin.site.register(ListingPriceHistory)
admin.site.register(OfferEvent)
