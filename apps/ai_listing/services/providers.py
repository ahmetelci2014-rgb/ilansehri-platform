from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from urllib import error, parse, request

from .exceptions import ProviderError, SafetyBlockedError
from .schemas import provider_json_schema


@dataclass(frozen=True)
class ProviderResponse:
    payload: dict
    request_id: str = ""


class BaseVisionProvider:
    key = "base"

    def __init__(self, *, model_name: str = ""):
        self.model_name = (model_name or "").strip()

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
                "Bu çıktı yalnızca İlan Şehri yapay zekâ akışını test etmek için üretildi. "
                "Test sağlayıcısı gerçek görsel tanıma yapmaz; ürün bilgilerini kullanıcı tamamlamalıdır."
            ),
            "category_slug": "",
            "subcategory_slug": "",
            "condition": "",
            "brand": "",
            "model": "",
            "color": "",
            "tags": ["fotoğraflı ilan"],
            "detected_features": [f"{len(images)} fotoğraf güvenli biçimde hazırlandı"],
            "technical_attributes": {},
            "possible_defects": [],
            "missing_questions": [
                {"field": "category", "question": "Ürün hangi kategoriye ait?", "type": "text", "options": [], "required": True},
                {"field": "condition", "question": "Ürünün çalışma ve kullanım durumu nedir?", "type": "text", "options": [], "required": True},
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



class GeminiVisionProvider(BaseVisionProvider):
    """Google Gemini Interactions API ile güvenli, şemalı görsel ilan analizi."""

    key = "gemini"
    MAX_INLINE_REQUEST_BYTES = 18 * 1024 * 1024

    def __init__(self, *, model_name: str = ""):
        super().__init__(model_name=model_name)
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.base_url = os.getenv(
            "GEMINI_API_BASE",
            "https://generativelanguage.googleapis.com/v1beta",
        ).strip().rstrip("/")
        self.api_revision = os.getenv("GEMINI_API_REVISION", "2026-05-20").strip()
        self.model = os.getenv("GEMINI_MODEL", "").strip() or self.model_name or "gemini-3.6-flash"

    def _require_configuration(self):
        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY .env dosyasında tanımlanmalıdır.")
        if not self.model:
            raise ProviderError("Gemini model adı tanımlanmalıdır.")

    def _headers(self) -> dict[str, str]:
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_revision:
            headers["Api-Revision"] = self.api_revision
        return headers

    @staticmethod
    def _extract_output_text(payload: dict) -> str:
        direct = payload.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        pieces: list[str] = []
        for step in payload.get("steps", []) or []:
            if not isinstance(step, dict) or step.get("type") != "model_output":
                continue
            for content in step.get("content", []) or []:
                if isinstance(content, dict) and content.get("type") == "text":
                    text = content.get("text")
                    if isinstance(text, str) and text.strip():
                        pieces.append(text.strip())
        return "\n".join(pieces).strip()

    @staticmethod
    def _safe_http_error(exc: error.HTTPError) -> tuple[str, bool]:
        message = ""
        code = ""
        try:
            raw = exc.read(256 * 1024)
            payload = json.loads(raw.decode("utf-8"))
            if isinstance(payload, dict):
                error_payload = payload.get("error", {})
                if isinstance(error_payload, dict):
                    message = str(error_payload.get("message", ""))[:500]
                    code = str(error_payload.get("code", ""))
        except Exception:
            pass
        combined = f"{code} {message}".casefold()
        blocked = any(token in combined for token in ("safety", "prohibited_content", "blocked by", "policy violation"))
        if not message:
            message = f"Gemini servisi HTTP {exc.code} hatası döndürdü."
        return message, blocked

    @staticmethod
    def _payload_is_safety_blocked(payload: dict) -> bool:
        error_payload = payload.get("error", {}) if isinstance(payload, dict) else {}
        if not isinstance(error_payload, dict):
            error_payload = {}
        combined = " ".join(
            [
                str(error_payload.get("code", "")),
                str(error_payload.get("message", "")),
                str(payload.get("status", "")) if isinstance(payload, dict) else "",
            ]
        ).casefold()
        return any(token in combined for token in ("safety", "prohibited_content", "blocked by", "policy violation"))

    @staticmethod
    def _category_catalog(context) -> list[dict]:
        categories = context.get("allowed_categories", [])
        category_by_id = {row.get("id"): row for row in categories}
        return [
            {
                "id": row.get("id"),
                "slug": row.get("slug", ""),
                "name": row.get("name", ""),
                "parent_slug": category_by_id.get(row.get("parent_id"), {}).get("slug", ""),
            }
            for row in categories
        ]

    def analyze(self, *, images, context, timeout_seconds: int) -> ProviderResponse:
        self._require_configuration()
        encoded_size = sum(4 * ((len(image.data) + 2) // 3) for image in images)
        if encoded_size > self.MAX_INLINE_REQUEST_BYTES:
            raise ProviderError(
                "Fotoğrafların analiz boyutu Gemini satır içi istek sınırını aşıyor. "
                "Daha az veya daha küçük fotoğraf seçin."
            )

        category_catalog = self._category_catalog(context)
        prompt = (
            "İlan Şehri için fotoğraflardan düzenlenebilir bir ilan taslağı hazırla. "
            "Yalnız görsel kanıta dayan; emin olmadığın marka, model, durum veya teknik bilgiyi boş bırak "
            "ve missing_questions içine kısa bir soru ekle. Görülen çizik, kırık, leke, deformasyon, "
            "eksik parça ve diğer kusurları gizleme. Fiyat üretme. Kişisel bilgi, plaka, kimlik, telefon "
            "veya açık adres görünüyorsa pii_warnings yaz. Yasaklı, tehlikeli, sahte veya mevzuata aykırı "
            "ürün ihtimali varsa safety_status=blocked yap ve ilan metni üretme. Kategori ve alt kategori "
            "için yalnız verilen katalogdaki slug değerlerini kullan. Teknik seçim alanlarında yalnız şu iç "
            "değerleri kullan: fuel_type=gasoline|diesel|lpg|hybrid|electric|other; "
            "transmission=automatic|manual|semi_automatic; "
            "fee_type=fixed|hourly|daily|monthly|negotiable; "
            "job_type=full_time|part_time|daily|remote|internship. "
            "Diğer teknik değerler kısa ve doğrudan metin olsun. Açıklama doğal Türkçe, dürüst ve ilan diline "
            "uygun olsun; görünmeyen özellikleri uydurma. Birden çok fotoğraf aynı ürüne ait kabul edilir, "
            "ancak çelişki varsa bunu missing_questions içinde sor.\n\n"
            f"Kategori kataloğu: {json.dumps(category_catalog, ensure_ascii=False, separators=(',', ':'))}"
        )
        interaction_input = [{"type": "text", "text": prompt}]
        interaction_input.extend(
            {
                "type": "image",
                "mime_type": image.mime_type,
                "data": base64.b64encode(image.data).decode("ascii"),
            }
            for image in images
        )
        body = {
            "model": self.model,
            "system_instruction": context.get("instructions", ""),
            "input": interaction_input,
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": provider_json_schema(),
            },
            "generation_config": {
                "max_output_tokens": 3200,
                "thinking_level": "low",
            },
            "store": False,
        }
        req = request.Request(
            f"{self.base_url}/interactions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                raw = response.read(4 * 1024 * 1024)
                api_payload = json.loads(raw.decode("utf-8"))
                request_id = response.headers.get("X-Request-ID", "") or api_payload.get("id", "")
        except error.HTTPError as exc:
            message, blocked = self._safe_http_error(exc)
            if blocked:
                raise SafetyBlockedError(
                    "Fotoğraflar Gemini güvenlik denetiminde riskli bulunduğu için ilan taslağı oluşturulmadı."
                ) from exc
            raise ProviderError(message) from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            raise ProviderError("Gemini görsel analiz servisine ulaşılamadı veya geçersiz yanıt alındı.") from exc

        if self._payload_is_safety_blocked(api_payload):
            raise SafetyBlockedError(
                "Fotoğraflar Gemini güvenlik denetiminde riskli bulunduğu için ilan taslağı oluşturulmadı."
            )
        if api_payload.get("status") not in {None, "completed"}:
            error_payload = api_payload.get("error", {})
            message = error_payload.get("message", "") if isinstance(error_payload, dict) else ""
            raise ProviderError(str(message or "Gemini analizi tamamlanamadı.")[:500])

        output_text = self._extract_output_text(api_payload)
        if not output_text:
            raise ProviderError("Gemini yanıtında doğrulanabilir ilan verisi bulunamadı.")
        try:
            payload = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ProviderError("Gemini yanıtı geçerli JSON biçiminde değil.") from exc
        if not isinstance(payload, dict):
            raise ProviderError("Gemini yanıtı JSON nesnesi olmalıdır.")
        return ProviderResponse(payload=payload, request_id=str(request_id))

    def test_connection(self, *, timeout_seconds: int) -> tuple[bool, str]:
        try:
            self._require_configuration()
            model_id = parse.quote(self.model, safe="")
            req = request.Request(
                f"{self.base_url}/models/{model_id}",
                headers=self._headers(),
                method="GET",
            )
            with request.urlopen(req, timeout=timeout_seconds) as response:
                payload = json.loads(response.read(512 * 1024).decode("utf-8"))
                display = payload.get("displayName") or payload.get("name") or self.model
                return True, f"Gemini bağlantısı hazır. Model: {display}."
        except error.HTTPError as exc:
            message, _blocked = self._safe_http_error(exc)
            return False, message
        except (error.URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError):
            return False, "Gemini servisine ulaşılamadı. API anahtarını, modeli ve internet erişimini kontrol edin."


class OpenAIVisionProvider(BaseVisionProvider):
    key = "openai"

    def __init__(self, *, model_name: str = ""):
        super().__init__(model_name=model_name)
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").strip().rstrip("/")
        self.project = os.getenv("OPENAI_PROJECT_ID", "").strip()
        self.model = os.getenv("AI_LISTING_MODEL", "").strip() or self.model_name or "gpt-5-mini"

    def _require_configuration(self):
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY .env dosyasında tanımlanmalıdır.")
        if not self.model:
            raise ProviderError("Yapay zekâ model adı tanımlanmalıdır.")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.project:
            headers["OpenAI-Project"] = self.project
        return headers

    @staticmethod
    def _extract_output_text(payload: dict) -> str:
        direct = payload.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        pieces: list[str] = []
        for item in payload.get("output", []) or []:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []) or []:
                if not isinstance(content, dict):
                    continue
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    pieces.append(content["text"])
                elif content.get("type") == "refusal" and content.get("refusal"):
                    raise ProviderError("Yapay zekâ bu görselleri güvenlik nedeniyle analiz etmedi.")
        return "\n".join(pieces).strip()

    @staticmethod
    def _safe_http_error(exc: error.HTTPError) -> str:
        try:
            raw = exc.read(128 * 1024)
            payload = json.loads(raw.decode("utf-8"))
            message = payload.get("error", {}).get("message", "") if isinstance(payload, dict) else ""
            if message:
                return str(message)[:500]
        except Exception:
            pass
        return f"OpenAI servisi HTTP {exc.code} hatası döndürdü."

    def _moderate_images(self, *, images, timeout_seconds: int) -> None:
        """OpenAI görsel güvenlik sınıflandırmasını ana analizden önce çalıştırır."""
        moderation_input = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image.mime_type};base64,{base64.b64encode(image.data).decode('ascii')}"
                },
            }
            for image in images
        ]
        req = request.Request(
            f"{self.base_url}/moderations",
            data=json.dumps({"model": "omni-moderation-latest", "input": moderation_input}).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=min(timeout_seconds, 30)) as response:
                payload = json.loads(response.read(1024 * 1024).decode("utf-8"))
        except error.HTTPError as exc:
            raise ProviderError(self._safe_http_error(exc)) from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            raise ProviderError("Fotoğraf güvenlik kontrolü tamamlanamadı.") from exc
        results = payload.get("results", []) if isinstance(payload, dict) else []
        if any(bool(item.get("flagged")) for item in results if isinstance(item, dict)):
            raise SafetyBlockedError(
                "Fotoğraflar güvenlik denetiminde riskli bulunduğu için ilan taslağı oluşturulmadı."
            )

    def analyze(self, *, images, context, timeout_seconds: int) -> ProviderResponse:
        self._require_configuration()
        self._moderate_images(images=images, timeout_seconds=timeout_seconds)
        categories = context.get("allowed_categories", [])
        category_by_id = {row.get("id"): row for row in categories}
        category_catalog = [
            {
                "id": row.get("id"),
                "slug": row.get("slug", ""),
                "name": row.get("name", ""),
                "parent_slug": category_by_id.get(row.get("parent_id"), {}).get("slug", ""),
            }
            for row in categories
        ]
        prompt = (
            "İlan Şehri için fotoğraflardan düzenlenebilir bir ilan taslağı hazırla. "
            "Yalnız görsel kanıta dayan; emin olmadığın marka, model, durum veya teknik bilgiyi boş bırak "
            "ve missing_questions içine kısa bir soru ekle. Görülen kusurları kesinlikle gizleme. "
            "Fiyat üretme. Kişisel bilgi, plaka, kimlik, telefon veya açık adres görünüyorsa pii_warnings yaz. "
            "Yasaklı, tehlikeli, sahte veya mevzuata aykırı ürün ihtimali varsa safety_status=blocked yap. "
            "Kategori ve alt kategori için yalnız verilen katalogdaki slug değerlerini kullan. "
            "Teknik seçim alanlarında yalnız şu iç değerleri kullan: "
            "fuel_type=gasoline|diesel|lpg|hybrid|electric|other; "
            "transmission=automatic|manual|semi_automatic; "
            "fee_type=fixed|hourly|daily|monthly|negotiable; "
            "job_type=full_time|part_time|daily|remote|internship. "
            "Diğer teknik değerler kısa ve doğrudan metin olsun. "
            "Açıklama doğal Türkçe, dürüst ve satış ilanına uygun olsun; görünmeyen özellikleri uydurma.\n\n"
            f"Kategori kataloğu: {json.dumps(category_catalog, ensure_ascii=False, separators=(',', ':'))}"
        )
        content = [{"type": "input_text", "text": prompt}]
        content.extend(
            {
                "type": "input_image",
                "image_url": f"data:{image.mime_type};base64,{base64.b64encode(image.data).decode('ascii')}",
                "detail": "high",
            }
            for image in images
        )
        body = {
            "model": self.model,
            "instructions": context.get("instructions", ""),
            "input": [{"role": "user", "content": content}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "ilan_sehri_listing_analysis",
                    "strict": True,
                    "schema": provider_json_schema(),
                }
            },
            "max_output_tokens": 3200,
            "store": False,
        }
        req = request.Request(
            f"{self.base_url}/responses",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                raw = response.read(4 * 1024 * 1024)
                api_payload = json.loads(raw.decode("utf-8"))
                request_id = response.headers.get("X-Request-ID", "") or api_payload.get("id", "")
        except error.HTTPError as exc:
            raise ProviderError(self._safe_http_error(exc)) from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            raise ProviderError("OpenAI görsel analiz servisine ulaşılamadı veya geçersiz yanıt alındı.") from exc

        output_text = self._extract_output_text(api_payload)
        if not output_text:
            raise ProviderError("OpenAI yanıtında doğrulanabilir ilan verisi bulunamadı.")
        try:
            payload = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ProviderError("OpenAI yanıtı geçerli JSON biçiminde değil.") from exc
        if not isinstance(payload, dict):
            raise ProviderError("OpenAI yanıtı JSON nesnesi olmalıdır.")
        return ProviderResponse(payload=payload, request_id=str(request_id))

    def test_connection(self, *, timeout_seconds: int) -> tuple[bool, str]:
        try:
            self._require_configuration()
            model_id = parse.quote(self.model, safe="")
            req = request.Request(
                f"{self.base_url}/models/{model_id}",
                headers=self._headers(),
                method="GET",
            )
            with request.urlopen(req, timeout=timeout_seconds) as response:
                payload = json.loads(response.read(256 * 1024).decode("utf-8"))
                resolved = payload.get("id", self.model) if isinstance(payload, dict) else self.model
                return True, f"OpenAI bağlantısı hazır. Model: {resolved}."
        except error.HTTPError as exc:
            return False, self._safe_http_error(exc)
        except (error.URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError):
            return False, "OpenAI servisine ulaşılamadı. API anahtarını, modeli ve internet erişimini kontrol edin."


class HTTPJSONVisionProvider(BaseVisionProvider):
    key = "http_json"

    def __init__(self, *, model_name: str = ""):
        super().__init__(model_name=model_name)
        self.endpoint = os.getenv("AI_LISTING_API_URL", "").strip()
        self.api_key = os.getenv("AI_LISTING_API_KEY", "").strip()
        self.model = os.getenv("AI_LISTING_MODEL", "").strip() or self.model_name

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
            "json_schema": provider_json_schema(),
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
        except error.HTTPError as exc:
            raise ProviderError(f"Harici yapay zekâ servisi HTTP {exc.code} hatası döndürdü.") from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
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
        except (error.URLError, TimeoutError, OSError):
            return False, "Harici yapay zekâ servisine ulaşılamadı."


def provider_is_configured(provider_key: str) -> bool:
    if provider_key == "mock":
        return True
    if provider_key == "gemini":
        return bool(os.getenv("GEMINI_API_KEY", "").strip())
    if provider_key == "openai":
        return bool(os.getenv("OPENAI_API_KEY", "").strip())
    if provider_key == "http_json":
        return bool(os.getenv("AI_LISTING_API_URL", "").strip() and os.getenv("AI_LISTING_API_KEY", "").strip())
    return False


def get_provider(provider_key: str, *, model_name: str = "") -> BaseVisionProvider:
    providers = {
        "gemini": GeminiVisionProvider,
        "mock": MockVisionProvider,
        "openai": OpenAIVisionProvider,
        "http_json": HTTPJSONVisionProvider,
    }
    provider_class = providers.get(provider_key)
    if provider_class is None:
        raise ProviderError("Tanımsız yapay zekâ sağlayıcısı.")
    return provider_class(model_name=model_name)
