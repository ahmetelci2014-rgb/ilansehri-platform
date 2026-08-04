from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from urllib import error, request

from .exceptions import ProviderError


@dataclass(frozen=True)
class ProviderResponse:
    payload: dict
    request_id: str = ""


class BaseVisionProvider:
    key = "base"

    def analyze(self, *, images, context, timeout_seconds: int) -> ProviderResponse:
        raise NotImplementedError

    def test_connection(self, *, timeout_seconds: int) -> tuple[bool, str]:
        raise NotImplementedError


class MockVisionProvider(BaseVisionProvider):
    key = "mock"

    def analyze(self, *, images, context, timeout_seconds: int) -> ProviderResponse:
        payload = {
            "schema_version": "1.0",
            "title": "Fotoğraflı ürün ilanı",
            "description": (
                "Bu çıktı yalnızca İlan Şehri yapay zekâ çekirdeğini test etmek için üretildi. "
                "Gerçek görsel analiz sağlayıcısı henüz bağlanmadı; kullanıcı ürün bilgilerini kontrol etmelidir."
            ),
            "category_slug": "",
            "subcategory_slug": "",
            "condition": "",
            "brand": "",
            "model": "",
            "color": "",
            "tags": ["fotoğraflı ilan"],
            "detected_features": [f"{len(images)} fotoğraf güvenli biçimde hazırlandı"],
            "possible_defects": [],
            "missing_questions": [
                {"field": "category", "question": "Ürün hangi kategoriye ait?", "type": "text", "required": True},
                {"field": "condition", "question": "Ürünün çalışma ve kullanım durumu nedir?", "type": "text", "required": True},
            ],
            "field_confidence": {"title": 20, "description": 10},
            "confidence_score": 15,
            "safety_status": "review_required",
            "safety_warnings": ["Test sağlayıcısı gerçek görsel tanıma yapmaz."],
            "pii_warnings": [],
        }
        return ProviderResponse(payload=payload, request_id="mock-local")

    def test_connection(self, *, timeout_seconds: int) -> tuple[bool, str]:
        return True, "Test sağlayıcısı hazır. Gerçek görsel analizi yapmaz."


class HTTPJSONVisionProvider(BaseVisionProvider):
    key = "http_json"

    def __init__(self):
        self.endpoint = os.getenv("AI_LISTING_API_URL", "").strip()
        self.api_key = os.getenv("AI_LISTING_API_KEY", "").strip()
        self.model = os.getenv("AI_LISTING_MODEL", "").strip()

    def _require_configuration(self):
        if not self.endpoint or not self.api_key:
            raise ProviderError("AI_LISTING_API_URL ve AI_LISTING_API_KEY tanımlanmalıdır.")

    def analyze(self, *, images, context, timeout_seconds: int) -> ProviderResponse:
        self._require_configuration()
        body = {
            "schema_version": "1.0",
            "model": self.model or context.get("model_name", ""),
            "instructions": context.get("instructions", ""),
            "allowed_categories": context.get("allowed_categories", []),
            "images": [
                {
                    "mime_type": image.mime_type,
                    "data_base64": base64.b64encode(image.data).decode("ascii"),
                }
                for image in images
            ],
        }
        req = request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                raw = response.read(2 * 1024 * 1024)
                payload = json.loads(raw.decode("utf-8"))
                request_id = response.headers.get("X-Request-ID", "")
        except (error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProviderError("Yapay zekâ servisine ulaşılamadı veya geçersiz yanıt alındı.") from exc
        if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
            payload = payload["result"]
        if not isinstance(payload, dict):
            raise ProviderError("Yapay zekâ servisi JSON nesnesi döndürmelidir.")
        return ProviderResponse(payload=payload, request_id=request_id)

    def test_connection(self, *, timeout_seconds: int) -> tuple[bool, str]:
        try:
            self._require_configuration()
            req = request.Request(
                self.endpoint,
                data=json.dumps({"action": "connection_test", "model": self.model}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with request.urlopen(req, timeout=timeout_seconds) as response:
                response.read(64 * 1024)
                return True, f"Harici yapay zekâ servisine erişildi (HTTP {response.status})."
        except error.HTTPError as exc:
            return False, f"Servis bağlantı testi başarısız oldu (HTTP {exc.code})."
        except (error.URLError, TimeoutError, OSError) as exc:
            return False, "Harici yapay zekâ servisine ulaşılamadı."


def get_provider(provider_key: str) -> BaseVisionProvider:
    providers = {
        "mock": MockVisionProvider,
        "http_json": HTTPJSONVisionProvider,
    }
    provider_class = providers.get(provider_key)
    if provider_class is None:
        raise ProviderError("Tanımsız yapay zekâ sağlayıcısı.")
    return provider_class()
