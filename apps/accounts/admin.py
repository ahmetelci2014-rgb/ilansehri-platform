from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("İlan Şehri Profili", {"fields": ("user_type", "phone", "city", "district", "is_phone_verified")}),
    )
    list_display = ("username", "email", "user_type", "city", "is_phone_verified", "is_staff")
    list_filter = ("user_type", "is_phone_verified", "is_staff")
