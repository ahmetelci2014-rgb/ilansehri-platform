from django.contrib import admin
from django.utils import timezone

from .models import (
    Category,
    Conversation,
    Favorite,
    Listing,
    ListingImage,
    ListingReport,
    Message,
    Notification,
    Offer,
)
from .services import create_notification


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0


@admin.action(description="Seçili ilanları onayla ve yayınla")
def approve_listings(modeladmin, request, queryset):
    for listing in queryset.select_related("owner"):
        listing.status = Listing.Status.PUBLISHED
        listing.published_at = timezone.now()
        listing.moderated_at = timezone.now()
        listing.moderated_by = request.user
        listing.review_note = ""
        listing.save(
            update_fields=[
                "status",
                "published_at",
                "moderated_at",
                "moderated_by",
                "review_note",
                "updated_at",
            ]
        )
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
        listing.save(
            update_fields=["status", "moderated_at", "moderated_by", "updated_at"]
        )
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
    list_display = (
        "title",
        "kind",
        "action",
        "management_mode",
        "city",
        "status",
        "created_at",
    )
    list_filter = ("kind", "action", "management_mode", "status", "city")
    search_fields = (
        "title",
        "description",
        "owner__username",
        "brand",
        "model_name",
    )
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "published_at", "moderated_at")
    actions = (approve_listings, reject_listings)
    inlines = [ListingImageInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("listing", "buyer", "seller", "updated_at")
    search_fields = ("listing__title", "buyer__username", "seller__username")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("body", "sender__username", "conversation__listing__title")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "title", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("user__username", "title", "body")


@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    list_display = ("listing", "reporter", "reason", "status", "created_at")
    list_filter = ("reason", "status", "created_at")
    search_fields = ("listing__title", "reporter__username", "details")
    readonly_fields = ("created_at",)


admin.site.register(Offer)
admin.site.register(Favorite)
