from django.contrib import admin
from .models import ManagedRequest


@admin.register(ManagedRequest)
class ManagedRequestAdmin(admin.ModelAdmin):
    list_display = ("listing", "customer", "package", "status", "created_at")
    list_filter = ("package", "status")
