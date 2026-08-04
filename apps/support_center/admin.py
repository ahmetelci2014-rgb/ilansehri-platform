from django.contrib import admin

from .models import StaffActionLog, SupportReply, SupportTicket


class SupportReplyInline(admin.TabularInline):
    model = SupportReply
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("short_id", "subject", "user", "category", "priority", "status", "assigned_to", "updated_at")
    list_filter = ("status", "priority", "category")
    search_fields = ("subject", "description", "user__username", "user__email")
    readonly_fields = ("public_id", "created_at", "updated_at", "last_reply_at", "resolved_at")
    inlines = (SupportReplyInline,)

    @admin.display(description="Talep")
    def short_id(self, obj):
        return f"#{str(obj.public_id)[:8]}"


@admin.register(StaffActionLog)
class StaffActionLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "summary", "target_type", "target_id")
    list_filter = ("action", "created_at")
    search_fields = ("summary", "actor__username", "target_id")
    readonly_fields = ("actor", "action", "target_type", "target_id", "summary", "metadata", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(SupportReply)
