import json
import logging
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


def send_phone_verification_code(*, destination: str, code: str) -> bool:
    """Send an SMS through a generic JSON webhook.

    Expected request body: {"to": "...", "message": "..."}.
    Optional bearer token is read from SMS_WEBHOOK_TOKEN.
    """
    if settings.VERIFICATION_DEBUG_CODE:
        return True
    if not settings.SMS_WEBHOOK_URL:
        return False

    payload = json.dumps(
        {
            "to": destination,
            "message": f"İlan Şehri doğrulama kodunuz: {code}. Kod 10 dakika geçerlidir.",
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if settings.SMS_WEBHOOK_TOKEN:
        headers["Authorization"] = f"Bearer {settings.SMS_WEBHOOK_TOKEN}"
    request = Request(settings.SMS_WEBHOOK_URL, data=payload, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300
    except (URLError, TimeoutError, OSError):
        logger.exception("SMS doğrulama webhook isteği başarısız oldu")
        return False
