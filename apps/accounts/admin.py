from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, UserBlock, VerificationCode


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
