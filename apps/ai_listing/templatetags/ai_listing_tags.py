import os

from django import template
from django.db.utils import OperationalError, ProgrammingError

from apps.ai_listing.models import AISettings
from apps.ai_listing.services.providers import provider_is_configured

register = template.Library()


@register.simple_tag(takes_context=True)
def ai_listing_config(context):
    fallback = {
        "available": True,
        "enabled": False,
        "can_analyze": False,
        "provider_ready": False,
        "provider": "",
        "max_images": 8,
        "max_image_size_mb": 8,
        "min_confidence_score": 60,
        "status_message": "Yapay zekâ kurulumu henüz tamamlanmadı. Normal ilan formunu kullanabilirsin.",
    }
    try:
        config = AISettings.objects.filter(singleton_key=1).first()
        if config is None:
            fallback["status_message"] = "Yapay zekâ ayarları henüz oluşturulmadı. Başlatma komutunu yeniden çalıştırın."
            return fallback
    except (OperationalError, ProgrammingError):
        fallback["status_message"] = "Yapay zekâ veritabanı kurulumu tamamlanmadı. Migration işlemini yeniden çalıştırın."
        return fallback

    request = context.get("request")
    user = request.user if request else None
    provider_ready = provider_is_configured(config.provider)
    mock_allowed = config.provider != AISettings.Provider.MOCK or bool(user and user.is_staff)
    can_analyze = bool(config.is_enabled and provider_ready and mock_allowed)

    if not config.is_enabled:
        status_message = "Yapay zekâ özelliği yönetim panelinden henüz açılmadı. Fotoğrafları yine yükleyip formu elle doldurabilirsin."
    elif config.provider == AISettings.Provider.MOCK and not mock_allowed:
        status_message = "Test sağlayıcısı yalnız demo_admin gibi personel hesabında çalışır. Gerçek kullanım için Google Gemini sağlayıcısını seçin."
    elif not provider_ready and config.provider == AISettings.Provider.GEMINI:
        status_message = "Gemini API anahtarı .env dosyasında tanımlı değil. GEMINI_API_KEY eklenince görsel analiz aktif olur."
    elif not provider_ready and config.provider == AISettings.Provider.OPENAI:
        status_message = "OpenAI API anahtarı .env dosyasında tanımlı değil. Bu sağlayıcı yalnız yedek seçenek olarak korunuyor."
    elif not provider_ready:
        status_message = "Seçilen yapay zekâ sağlayıcısının bağlantı bilgileri eksik."
    else:
        status_message = "1–8 fotoğraf seç. Yapay zekâ ürünü tanıyıp ilan taslağını hazırlasın."

    return {
        "available": True,
        "enabled": config.is_enabled,
        "can_analyze": can_analyze,
        "provider_ready": provider_ready,
        "provider": config.provider,
        "provider_label": config.get_provider_display(),
        "model_name": (
            os.getenv("GEMINI_MODEL", "").strip() if config.provider == AISettings.Provider.GEMINI
            else os.getenv("AI_LISTING_MODEL", "").strip()
        ) or config.model_name,
        "max_images": config.max_images,
        "max_image_size_mb": config.max_image_size_mb,
        "min_confidence_score": config.min_confidence_score,
        "status_message": status_message,
    }
