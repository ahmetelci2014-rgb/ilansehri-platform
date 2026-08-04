from django.contrib import admin

from .models import PartnerEarning, PartnerProfile, Task, TaskApplication


@admin.register(PartnerProfile)
class PartnerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "level", "status", "available", "rating", "completed_tasks", "total_earnings")
    list_filter = ("level", "status", "available", "identity_verified")
    search_fields = ("user__username", "user__phone", "about")


class TaskApplicationInline(admin.TabularInline):
    model = TaskApplication
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "task_type", "city", "reward", "status", "assigned_partner", "due_at")
    list_filter = ("task_type", "status", "city", "min_level")
    search_fields = ("title", "description", "managed_request__listing__title")
    inlines = (TaskApplicationInline,)


admin.site.register(TaskApplication)
admin.site.register(PartnerEarning)
