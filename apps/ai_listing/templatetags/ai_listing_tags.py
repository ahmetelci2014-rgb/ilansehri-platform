from django import template
from django.db.utils import OperationalError, ProgrammingError

from apps.ai_listing.models import AISettings

register = template.Library()


@register.simple_tag(takes_context=True)
def ai_listing_config(context):
    try:
        config = AISettings.objects.filter(singleton_key=1).first()
        if config is None:
            return {"enabled": False}
    except (OperationalError, ProgrammingError):
        return {"enabled": False}
    user = context.get("request").user if context.get("request") else None
    mock_allowed = config.provider != AISettings.Provider.MOCK or bool(user and user.is_staff)
    return {
        "enabled": config.is_enabled and mock_allowed,
        "provider": config.provider,
        "max_images": config.max_images,
        "max_image_size_mb": config.max_image_size_mb,
        "min_confidence_score": config.min_confidence_score,
    }
