from django.contrib import admin, messages
from django.db.models import Avg, Count
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .forms import AISettingsAdminForm
from .models import AIAnalysis, AIFieldChange, AISettings
from .services.providers import get_provider


@admin.register(AISettings)
class AISettingsAdmin(admin.ModelAdmin):
    form = AISettingsAdminForm
    change_form_template = "admin/ai_listing/aisettings/change_form.html"
    fieldsets = (
        ("Özellik", {"fields": ("is_enabled", "provider", "model_name")}),
        ("Limit ve güvenlik", {"fields": ("user_daily_limit", "site_daily_limit", "timeout_seconds", "max_images", "max_image_size_mb", "min_confidence_score")}),
        ("İstatistikler", {"fields": ("statistics_summary", "last_connection_checked_at", "last_connection_ok", "last_connection_message")}),
        ("Kayıt", {"fields": ("updated_by", "updated_at")}),
    )
    readonly_fields = (
        "statistics_summary",
        "last_connection_checked_at",
        "last_connection_ok",
        "last_connection_message",
        "updated_by",
        "updated_at",
    )

    def has_add_permission(self, request):
        return not AISettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Kullanım özeti")
    def statistics_summary(self, obj):
        return format_html(
            "<b>{}</b> başarılı · <b>{}</b> başarısız · <b>{}</b> engelli · Başarı oranı <b>%{}</b> · Ortalama <b>{} ms</b>",
            obj.successful_analyses,
            obj.failed_analyses,
            obj.blocked_analyses,
            obj.success_rate,
            obj.average_duration_ms,
        )

    def get_urls(self):
        return [
            path(
                "connection-test/",
                self.admin_site.admin_view(self.connection_test),
                name="ai_listing_aisettings_connection_test",
            )
        ] + super().get_urls()

    def connection_test(self, request):
        config = AISettings.load()
        try:
            ok, message = get_provider(config.provider, model_name=config.model_name).test_connection(timeout_seconds=config.timeout_seconds)
        except Exception as exc:
            ok, message = False, str(exc)
        config.last_connection_checked_at = timezone.now()
        config.last_connection_ok = ok
        config.last_connection_message = message[:500]
        config.updated_by = request.user
        config.save()
        if ok:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return HttpResponseRedirect(reverse("admin:ai_listing_aisettings_change", args=[config.pk]))


class AIFieldChangeInline(admin.TabularInline):
    model = AIFieldChange
    extra = 0
    can_delete = False
    readonly_fields = ("field_name", "suggested_value", "final_value", "change_type", "created_at")


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ("short_id", "user", "status", "safety_status", "provider", "image_count", "confidence_score", "duration_ms", "created_at")
    list_filter = ("status", "safety_status", "provider", "created_at")
    search_fields = ("public_id", "user__username", "user__email", "error_code", "error_message")
    readonly_fields = tuple(field.name for field in AIAnalysis._meta.fields)
    inlines = (AIFieldChangeInline,)

    @admin.display(description="Analiz")
    def short_id(self, obj):
        return f"#{str(obj.public_id)[:8]}"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(AIFieldChange)
class AIFieldChangeAdmin(admin.ModelAdmin):
    list_display = ("analysis", "field_name", "change_type", "listing", "created_at")
    list_filter = ("change_type", "created_at")
    search_fields = ("analysis__public_id", "field_name", "listing__title")
    readonly_fields = tuple(field.name for field in AIFieldChange._meta.fields)

    def has_add_permission(self, request):
        return False
