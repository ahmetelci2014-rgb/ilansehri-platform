from io import BytesIO
import json
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.listings.models import Category

from .models import AIAnalysis, AISettings
from .templatetags.ai_listing_tags import ai_listing_config
from .services.image_processor import prepare_images
from .services.providers import GeminiVisionProvider, OpenAIVisionProvider
from .services.exceptions import SafetyBlockedError
from .services.schemas import validate_analysis_payload


class _FakeHTTPResponse:
    def __init__(self, payload, *, headers=None, status=200):
        self.payload = payload
        self.headers = headers or {}
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, _limit=-1):
        return json.dumps(self.payload).encode("utf-8")


def _provider_payload():
    technical_keys = [
        "model_year", "mileage", "fuel_type", "transmission", "room_count",
        "area_m2", "building_age", "floor_location", "heating_type",
        "service_area", "fee_type", "job_type", "experience_level",
    ]
    confidence_keys = [
        "title", "description", "category", "condition", "brand", "model", "color",
        *technical_keys,
    ]
    return {
        "schema_version": "1.0",
        "title": "Mavi akıllı telefon",
        "description": "Fotoğraflarda görülen kullanılmış akıllı telefon.",
        "category_slug": "elektronik",
        "subcategory_slug": "",
        "condition": "Kullanılmış",
        "brand": "",
        "model": "",
        "color": "Mavi",
        "tags": ["telefon", "mavi"],
        "detected_features": ["Dokunmatik ekran"],
        "technical_attributes": {key: "" for key in technical_keys},
        "possible_defects": [],
        "missing_questions": [
            {
                "field": "brand",
                "question": "Telefonun markası nedir?",
                "type": "text",
                "options": [],
                "required": True,
            }
        ],
        "field_confidence": {key: (88 if key in {"title", "description", "category", "color"} else 0) for key in confidence_keys},
        "confidence_score": 78,
        "safety_status": "safe",
        "safety_warnings": [],
        "pii_warnings": [],
    }


class AIListingCoreTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ai_user", password="StrongPass123!", is_staff=True)
        self.category = Category.objects.create(name="Elektronik", slug="elektronik")
        self.config = AISettings.load()

    def image_file(self, name="urun.png"):
        buffer = BytesIO()
        Image.new("RGB", (640, 480), "white").save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


    def test_ai_card_state_is_explained_for_normal_user_on_mock_provider(self):
        normal = get_user_model().objects.create_user(username="normal_card", password="StrongPass123!")
        self.config.is_enabled = True
        self.config.provider = AISettings.Provider.MOCK
        self.config.save()
        request = RequestFactory().get("/ilanlar/yeni/")
        request.user = normal
        payload = ai_listing_config({"request": request})
        self.assertTrue(payload["available"])
        self.assertTrue(payload["enabled"])
        self.assertFalse(payload["can_analyze"])
        self.assertIn("demo_admin", payload["status_message"])

    def test_ai_card_is_available_for_staff_when_enabled(self):
        self.config.is_enabled = True
        self.config.provider = AISettings.Provider.MOCK
        self.config.save()
        request = RequestFactory().get("/ilanlar/yeni/")
        request.user = self.user
        payload = ai_listing_config({"request": request})
        self.assertTrue(payload["available"])
        self.assertTrue(payload["can_analyze"])

    def test_ai_card_explains_when_feature_is_disabled(self):
        request = RequestFactory().get("/ilanlar/yeni/")
        request.user = self.user
        payload = ai_listing_config({"request": request})
        self.assertTrue(payload["available"])
        self.assertFalse(payload["can_analyze"])
        self.assertIn("yönetim panelinden", payload["status_message"])

    def test_settings_is_singleton(self):
        self.assertEqual(AISettings.load().pk, self.config.pk)
        self.config.singleton_key = 2
        self.config.save()
        self.assertEqual(self.config.singleton_key, 1)

    def test_image_processor_converts_to_safe_jpeg(self):
        prepared = prepare_images([self.image_file()], max_images=8, max_image_size_mb=8)
        self.assertEqual(len(prepared), 1)
        self.assertEqual(prepared[0].mime_type, "image/jpeg")
        self.assertTrue(prepared[0].fingerprint)

    def test_schema_rejects_unknown_fields(self):
        with self.assertRaises(Exception):
            validate_analysis_payload({"title": "Test", "price": 100}, allowed_category_slugs={"elektronik"})

    def test_schema_clears_unknown_category(self):
        result = validate_analysis_payload(
            {"title": "Test", "category_slug": "olmayan", "confidence_score": 50, "safety_status": "safe"},
            allowed_category_slugs={"elektronik"},
        )
        self.assertEqual(result["category_slug"], "")

    def test_disabled_endpoint_fails_without_breaking_form(self):
        self.client.login(username="ai_user", password="StrongPass123!")
        response = self.client.post(
            reverse("ai_listing:analyze"),
            {"request_id": "request-key-123456", "images": [self.image_file()]},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "feature_disabled")

    def test_mock_analysis_is_idempotent(self):
        self.config.is_enabled = True
        self.config.provider = AISettings.Provider.MOCK
        self.config.save()
        self.client.login(username="ai_user", password="StrongPass123!")
        data = {"request_id": "same-request-123456", "images": [self.image_file()]}
        first = self.client.post(reverse("ai_listing:analyze"), data)
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            reverse("ai_listing:analyze"),
            {"request_id": "same-request-123456", "images": [self.image_file()]},
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(AIAnalysis.objects.count(), 1)
        self.assertEqual(first.json()["analysis_id"], second.json()["analysis_id"])

    def test_non_staff_cannot_use_mock_provider(self):
        normal = get_user_model().objects.create_user(username="normal_ai", password="StrongPass123!")
        self.config.is_enabled = True
        self.config.provider = AISettings.Provider.MOCK
        self.config.save()
        self.client.force_login(normal)
        response = self.client.post(
            reverse("ai_listing:analyze"),
            {"request_id": "normal-request-123456", "images": [self.image_file()]},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "feature_disabled")

    def test_user_cannot_read_another_users_analysis(self):
        other = get_user_model().objects.create_user(username="other_ai", password="StrongPass123!")
        analysis = AIAnalysis.objects.create(
            user=other,
            status=AIAnalysis.Status.SUCCEEDED,
            provider="mock",
            model_name="test",
            idempotency_key="other-key-123456",
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("ai_listing:analysis_detail", args=[analysis.public_id]))
        self.assertEqual(response.status_code, 404)

    def test_daily_limit_is_enforced(self):
        self.config.is_enabled = True
        self.config.provider = AISettings.Provider.MOCK
        self.config.user_daily_limit = 1
        self.config.save()
        AIAnalysis.objects.create(
            user=self.user,
            status=AIAnalysis.Status.FAILED,
            provider="mock",
            model_name="test",
            idempotency_key="used-key-123456",
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("ai_listing:analyze"),
            {"request_id": "limit-key-123456", "images": [self.image_file()]},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "usage_limit")

    def test_photo_first_create_page_is_visible(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("listings:create"))
        self.assertContains(response, "Fotoğrafı yükle, ilan taslağın hazırlansın")
        self.assertContains(response, "data-ai-drop-zone")
        self.assertContains(response, "Yapay Zekâ ile İlan Hazırla")

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "AI_LISTING_MODEL": "gpt-5-mini"}, clear=False)
    def test_openai_provider_uses_moderation_images_and_strict_schema(self):
        prepared = prepare_images([self.image_file()], max_images=8, max_image_size_mb=8)
        output = _provider_payload()
        requests = []

        def fake_urlopen(req, timeout=0):
            body = json.loads(req.data.decode("utf-8"))
            requests.append((req.full_url, body, timeout))
            if req.full_url.endswith("/moderations"):
                return _FakeHTTPResponse({"results": [{"flagged": False}]})
            return _FakeHTTPResponse(
                {
                    "id": "resp_test_123",
                    "output": [{"content": [{"type": "output_text", "text": json.dumps(output)}]}],
                },
                headers={"X-Request-ID": "request-test-123"},
            )

        provider = OpenAIVisionProvider(model_name="gpt-5-mini")
        with patch("apps.ai_listing.services.providers.request.urlopen", side_effect=fake_urlopen):
            response = provider.analyze(
                images=prepared,
                context={"instructions": "Güvenli analiz", "allowed_categories": [{"id": 1, "slug": "elektronik", "name": "Elektronik", "parent_id": None}]},
                timeout_seconds=45,
            )
        self.assertEqual(response.payload["title"], "Mavi akıllı telefon")
        self.assertEqual(len(requests), 2)
        self.assertTrue(requests[0][0].endswith("/moderations"))
        response_body = requests[1][1]
        self.assertFalse(response_body["store"])
        self.assertTrue(response_body["text"]["format"]["strict"])
        image_part = response_body["input"][0]["content"][1]
        self.assertTrue(image_part["image_url"].startswith("data:image/jpeg;base64,"))

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False)
    def test_openai_provider_blocks_flagged_images_before_analysis(self):
        prepared = prepare_images([self.image_file()], max_images=8, max_image_size_mb=8)
        provider = OpenAIVisionProvider(model_name="gpt-5-mini")
        with patch(
            "apps.ai_listing.services.providers.request.urlopen",
            return_value=_FakeHTTPResponse({"results": [{"flagged": True}]}),
        ):
            with self.assertRaises(SafetyBlockedError):
                provider.analyze(
                    images=prepared,
                    context={"instructions": "", "allowed_categories": []},
                    timeout_seconds=45,
                )

    @patch.dict(
        "os.environ",
        {
            "GEMINI_API_KEY": "test-gemini-key",
            "GEMINI_MODEL": "gemini-3.6-flash",
            "GEMINI_API_BASE": "https://generativelanguage.googleapis.com/v1beta",
            "GEMINI_API_REVISION": "2026-05-20",
        },
        clear=False,
    )
    def test_gemini_provider_uses_inline_images_and_json_schema(self):
        prepared = prepare_images([self.image_file()], max_images=8, max_image_size_mb=8)
        output = _provider_payload()
        requests = []

        def fake_urlopen(req, timeout=0):
            body = json.loads(req.data.decode("utf-8"))
            requests.append((req.full_url, body, timeout, dict(req.headers)))
            return _FakeHTTPResponse(
                {
                    "id": "interaction_test_123",
                    "status": "completed",
                    "steps": [
                        {
                            "type": "model_output",
                            "content": [{"type": "text", "text": json.dumps(output)}],
                        }
                    ],
                },
                headers={"X-Request-ID": "gemini-request-123"},
            )

        provider = GeminiVisionProvider(model_name="gemini-3.6-flash")
        with patch("apps.ai_listing.services.providers.request.urlopen", side_effect=fake_urlopen):
            response = provider.analyze(
                images=prepared,
                context={
                    "instructions": "Güvenli analiz",
                    "allowed_categories": [
                        {"id": 1, "slug": "elektronik", "name": "Elektronik", "parent_id": None}
                    ],
                },
                timeout_seconds=45,
            )

        self.assertEqual(response.payload["title"], "Mavi akıllı telefon")
        self.assertEqual(len(requests), 1)
        url, body, timeout, headers = requests[0]
        self.assertTrue(url.endswith("/interactions"))
        self.assertEqual(body["model"], "gemini-3.6-flash")
        self.assertFalse(body["store"])
        self.assertEqual(body["response_format"]["mime_type"], "application/json")
        self.assertEqual(body["response_format"]["schema"]["type"], "object")
        self.assertEqual(body["input"][1]["type"], "image")
        self.assertEqual(body["input"][1]["mime_type"], "image/jpeg")
        self.assertTrue(body["input"][1]["data"])
        self.assertEqual(timeout, 45)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-gemini-key"}, clear=False)
    def test_gemini_provider_blocks_safety_failure(self):
        prepared = prepare_images([self.image_file()], max_images=8, max_image_size_mb=8)
        provider = GeminiVisionProvider(model_name="gemini-3.6-flash")
        with patch(
            "apps.ai_listing.services.providers.request.urlopen",
            return_value=_FakeHTTPResponse(
                {
                    "id": "interaction_blocked",
                    "status": "failed",
                    "error": {"code": "safety", "message": "Blocked by safety policy"},
                    "steps": [],
                }
            ),
        ):
            with self.assertRaises(SafetyBlockedError):
                provider.analyze(
                    images=prepared,
                    context={"instructions": "", "allowed_categories": []},
                    timeout_seconds=45,
                )

