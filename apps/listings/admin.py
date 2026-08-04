from django.contrib import admin

from .models import (
    Category,
    Conversation,
    Favorite,
    Listing,
    ListingImage,
    Message,
    Offer,
)


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0


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
    search_fields = ("title", "description", "owner__username")
    prepopulated_fields = {"slug": ("title",)}
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


admin.site.register(Offer)
admin.site.register(Favorite)
