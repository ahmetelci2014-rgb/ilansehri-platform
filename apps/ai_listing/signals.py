from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import AISettings


@receiver(post_migrate)
def ensure_ai_settings(sender, **kwargs):
    if sender.name == "apps.ai_listing":
        AISettings.objects.get_or_create(singleton_key=1)
