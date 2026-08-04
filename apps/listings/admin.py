from django.contrib import admin
from .models import Category, Listing, ListingImage, Offer


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "action", "management_mode", "city", "status", "created_at")
    list_filter = ("kind", "action", "management_mode", "status", "city")
    search_fields = ("title", "description", "owner__username")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ListingImageInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    prepopulated_fields = {"slug": ("name",)}

admin.site.register(Offer)
