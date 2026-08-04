from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.listings.models import Category

from .models import AIAnalysis, AISettings
from .templatetags.ai_listing_tags import ai_listing_config
from .services.image_processor import prepare_images
from .services.schemas import validate_analysis_payload


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
