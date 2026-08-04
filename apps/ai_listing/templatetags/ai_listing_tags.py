from django import template
from django.db.utils import OperationalError, ProgrammingError

from apps.ai_listing.models import AISettings

register = template.Library()


@register.simple_tag(takes_context=True)
def ai_listing_config(context):
    try:
        config = AISettings.objects.filter(singleton_key=1).first()
        if config is None:
            return {
                "available": True,
                "enabled": False,
                "can_analyze": False,
                "max_images": 8,
                "max_image_size_mb": 8,
                "min_confidence_score": 60,
                "status_message": "Yapay zekâ ayarları henüz oluşturulmadı. Başlatma komutunu yeniden çalıştırın.",
            }
    except (OperationalError, ProgrammingError):
        return {
            "available": True,
            "enabled": False,
            "can_analyze": False,
            "max_images": 8,
            "max_image_size_mb": 8,
            "min_confidence_score": 60,
            "status_message": "Yapay zekâ veritabanı kurulumu henüz tamamlanmadı. Migration işlemini yeniden çalıştırın.",
        }

    request = context.get("request")
    user = request.user if request else None
    mock_allowed = config.provider != AISettings.Provider.MOCK or bool(user and user.is_staff)
    can_analyze = bool(config.is_enabled and mock_allowed)

    if not config.is_enabled:
        status_message = "Yapay zekâ özelliği yönetim panelinden henüz açılmadı."
    elif config.provider == AISettings.Provider.MOCK and not mock_allowed:
        status_message = (
            "Test sağlayıcısı yalnız personel hesabında kullanılabilir. "
            "Test için demo_admin hesabıyla giriş yapın."
        )
    else:
        status_message = "Önce 1–8 fotoğraf seçin; ardından yapay zekâ ilan taslağını hazırlasın."

    return {
        "available": True,
        "enabled": config.is_enabled,
        "can_analyze": can_analyze,
        "provider": config.provider,
        "max_images": config.max_images,
        "max_image_size_mb": config.max_image_size_mb,
        "min_confidence_score": config.min_confidence_score,
        "status_message": status_message,
    }
