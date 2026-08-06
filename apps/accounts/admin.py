from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    AccountClosureRequest,
    AccountRiskEvent,
    NotificationPreference,
    User,
    UserBlock,
    UserFollow,
    UserReport,
    VerificationCode,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "İlan Şehri profili",
            {
                "fields": (
                    "user_type",
                    "phone",
                    "city",
                    "district",
                    "neighborhood",
                    "avatar",
                    "bio",
                    "is_phone_verified",
                    "is_email_verified",
                    "verification_level",
                    "average_rating",
                    "rating_count",
                    "completed_transactions",
                    "accepts_marketing",
                )
            },
        ),
    )
    list_display = ("username", "email", "phone", "user_type", "verification_level", "is_staff")
    list_filter = ("user_type", "verification_level", "is_phone_verified", "is_email_verified")


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "channel", "destination", "created_at", "expires_at", "consumed_at")
    readonly_fields = ("code_hash", "created_at", "consumed_at")


admin.site.register(UserBlock)

admin.site.register(UserFollow)


@admin.register(AccountClosureRequest)
class AccountClosureRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "requested_at", "updated_at", "resolved_by")
    list_filter = ("status", "requested_at")
    search_fields = ("user__username", "user__email", "reason")
    readonly_fields = ("requested_at", "updated_at")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "digest_frequency", "updated_at")
    list_filter = ("digest_frequency", "email_messages", "email_offers", "email_system")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at", "last_digest_at")


@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):
    list_display = ("reported_user", "reporter", "reason", "status", "created_at")
    list_filter = ("reason", "status")
    search_fields = ("reported_user__username", "reporter__username", "details")
    readonly_fields = ("created_at", "reviewed_at")


@admin.register(AccountRiskEvent)
class AccountRiskEventAdmin(admin.ModelAdmin):
    list_display = ("subject_user", "event_type", "severity", "status", "created_at")
    list_filter = ("event_type", "severity", "status")
    search_fields = ("subject_user__username", "summary", "fingerprint")
    readonly_fields = ("fingerprint", "created_at", "updated_at", "reviewed_at")
