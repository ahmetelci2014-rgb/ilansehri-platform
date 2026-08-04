from django.contrib import admin

from .models import ManagedActivity, ManagedRequest


class ManagedActivityInline(admin.TabularInline):
    model = ManagedActivity
    extra = 0


@admin.register(ManagedRequest)
class ManagedRequestAdmin(admin.ModelAdmin):
    list_display = ("listing", "customer", "package", "status", "progress", "assigned_staff", "updated_at")
    list_filter = ("package", "status", "preferred_contact")
    search_fields = ("listing__title", "customer__username", "customer__phone")
    inlines = (ManagedActivityInline,)


admin.site.register(ManagedActivity)
