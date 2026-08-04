from django.apps import AppConfig


class AIListingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_listing"
    verbose_name = "Yapay Zekâ İlan Asistanı"

    def ready(self):
        from . import signals  # noqa: F401
