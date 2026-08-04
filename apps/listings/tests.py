from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.managed_services.models import ManagedRequest

from .models import (
    Category,
    Conversation,
    Favorite,
    Listing,
    ListingReport,
    Message,
    Notification,
    Offer,
)


class ListingFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            password="GucluTestSifresi_2026",
            city="Şanlıurfa",
            district="Karaköprü",
        )
        self.buyer = User.objects.create_user(
            username="buyer",
            password="GucluTestSifresi_2026",
        )
        self.stranger = User.objects.create_user(
            username="stranger",
            password="GucluTestSifresi_2026",
        )
        self.staff = User.objects.create_user(
            username="moderator",
            password="GucluTestSifresi_2026",
            is_staff=True,
        )
        self.category = Category.objects.create(name="Elektronik", slug="elektronik")
        self.vehicle_category = Category.objects.create(name="Otomobil", slug="otomobil")

    def create_listing(self, **overrides):
        data = {
            "owner": self.owner,
            "category": self.category,
            "kind": Listing.Kind.PRODUCT,
            "action": Listing.Action.SELL,
            "management_mode": Listing.ManagementMode.SELF,
            "title": "Satılık dizüstü bilgisayar",
            "description": "Bakımlı ve sorunsuz.",
            "price": Decimal("25000.00"),
            "condition": "İyi durumda",
            "city": "Şanlıurfa",
            "district": "Haliliye",
            "status": Listing.Status.PUBLISHED,
        }
        data.update(overrides)
        return Listing.objects.create(**data)

    @override_settings(AUTO_PUBLISH_LISTINGS=True)
    def test_full_management_listing_creates_managed_request(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("listings:create"),
            {
                "kind": Listing.Kind.PRODUCT,
                "action": Listing.Action.SELL,
                "management_mode": Listing.ManagementMode.FULL,
                "category": self.category.pk,
                "title": "Temiz ikinci el telefon",
                "description": "Çalışır durumda, kutusu ve faturası vardır.",
                "price": "15000.00",
                "condition": "İkinci el",
                "brand": "Apple",
                "model_name": "iPhone 15",
                "city": "Şanlıurfa",
                "district": "Karaköprü",
                "neighborhood": "Atakent",
            },
        )

        listing = Listing.objects.get(title="Temiz ikinci el telefon")
        self.assertRedirects(response, listing.get_absolute_url())
        self.assertEqual(listing.status, Listing.Status.PUBLISHED)
        self.assertTrue(
            ManagedRequest.objects.filter(listing=listing, customer=self.owner).exists()
        )

    @override_settings(AUTO_PUBLISH_LISTINGS=True)
    def test_vehicle_specific_fields_are_saved(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("listings:create"),
            {
                "kind": Listing.Kind.VEHICLE,
                "action": Listing.Action.SELL,
                "management_mode": Listing.ManagementMode.SELF,
                "category": self.vehicle_category.pk,
                "title": "2022 model otomobil",
                "description": "Bakımları düzenli yapıldı.",
                "price": "875000.00",
                "condition": "Hasarsız",
                "brand": "Toyota",
                "model_name": "Corolla",
                "model_year": "2022",
                "mileage": "42000",
                "fuel_type": Listing.FuelType.GASOLINE,
                "transmission": Listing.Transmission.AUTOMATIC,
                "city": "Şanlıurfa",
                "district": "Karaköprü",
                "neighborhood": "Akpıyar",
            },
        )
        listing = Listing.objects.get(title="2022 model otomobil")
        self.assertRedirects(response, listing.get_absolute_url())
        self.assertEqual(listing.brand, "Toyota")
        self.assertEqual(listing.model_year, 2022)
        self.assertEqual(listing.mileage, 42000)

    def test_another_user_can_send_offer_and_owner_is_notified(self):
        listing = self.create_listing()
        self.client.force_login(self.buyer)
        response = self.client.post(
            listing.get_absolute_url(),
            {"amount": "23500.00", "message": "Bugün teslim alabilirim."},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Offer.objects.filter(
                listing=listing,
                sender=self.buyer,
                amount=Decimal("23500.00"),
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.owner,
                listing=listing,
                notification_type=Notification.Type.OFFER,
            ).exists()
        )
        self.assertContains(response, "Teklifin ilan sahibine gönderildi")

    def test_non_owner_cannot_edit_listing(self):
        listing = self.create_listing(title="Satılık masa")
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("listings:update", kwargs={"slug": listing.slug}))
        self.assertEqual(response.status_code, 403)

    def test_user_can_favorite_and_unfavorite_listing(self):
        listing = self.create_listing(title="Favori telefon")
        self.client.force_login(self.buyer)
        url = reverse("listings:toggle_favorite", kwargs={"slug": listing.slug})
        self.client.post(url, {"next": listing.get_absolute_url()})
        self.assertTrue(Favorite.objects.filter(user=self.buyer, listing=listing).exists())
        self.client.post(url, {"next": listing.get_absolute_url()})
        self.assertFalse(Favorite.objects.filter(user=self.buyer, listing=listing).exists())

    def test_owner_can_pause_and_republish_listing(self):
        listing = self.create_listing(title="Durum değişecek ilan")
        self.client.force_login(self.owner)
        self.client.post(
            reverse("listings:change_status", kwargs={"slug": listing.slug, "action": "pause"})
        )
        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.PAUSED)
        self.client.post(
            reverse("listings:change_status", kwargs={"slug": listing.slug, "action": "publish"})
        )
        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.PUBLISHED)

    def test_review_listing_cannot_bypass_moderation(self):
        listing = self.create_listing(title="İncelemedeki ilan", status=Listing.Status.REVIEW)
        self.client.force_login(self.owner)
        self.client.post(
            reverse("listings:change_status", kwargs={"slug": listing.slug, "action": "publish"})
        )
        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.REVIEW)

    def test_non_owner_cannot_change_listing_status(self):
        listing = self.create_listing(title="Korunan ilan")
        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse("listings:change_status", kwargs={"slug": listing.slug, "action": "pause"})
        )
        self.assertEqual(response.status_code, 404)
        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.PUBLISHED)

    def test_user_can_start_private_conversation_and_owner_is_notified(self):
        listing = self.create_listing(title="Mesajlı ilan")
        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse("listings:start_conversation", kwargs={"slug": listing.slug}),
            {"body": "Ürün hâlâ satılık mı?"},
        )
        conversation = Conversation.objects.get(listing=listing, buyer=self.buyer)
        self.assertRedirects(
            response,
            reverse("listings:conversation_detail", kwargs={"pk": conversation.pk}),
        )
        self.assertTrue(
            Message.objects.filter(
                conversation=conversation,
                sender=self.buyer,
                body="Ürün hâlâ satılık mı?",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.owner,
                notification_type=Notification.Type.MESSAGE,
            ).exists()
        )

    def test_only_conversation_participants_can_view_messages(self):
        listing = self.create_listing(title="Özel konuşma ilanı")
        conversation = Conversation.objects.create(
            listing=listing,
            buyer=self.buyer,
            seller=self.owner,
        )
        Message.objects.create(conversation=conversation, sender=self.buyer, body="Merhaba")
        self.client.force_login(self.stranger)
        response = self.client.get(
            reverse("listings:conversation_detail", kwargs={"pk": conversation.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_owner_can_delete_listing(self):
        listing = self.create_listing(title="Silinecek ilan")
        self.client.force_login(self.owner)
        response = self.client.post(reverse("listings:delete", kwargs={"slug": listing.slug}))
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.assertFalse(Listing.objects.filter(pk=listing.pk).exists())

    def test_user_can_report_listing_once(self):
        listing = self.create_listing(title="Şikâyet edilecek ilan")
        self.client.force_login(self.buyer)
        url = reverse("listings:report", kwargs={"slug": listing.slug})
        self.client.post(
            url,
            {"reason": ListingReport.Reason.WRONG_INFO, "details": "Fiyat bilgisi yanıltıcı."},
        )
        self.client.post(
            url,
            {"reason": ListingReport.Reason.OTHER, "details": "İkinci kayıt."},
        )
        self.assertEqual(
            ListingReport.objects.filter(listing=listing, reporter=self.buyer).count(),
            1,
        )

    def test_staff_can_approve_listing_and_owner_gets_notification(self):
        listing = self.create_listing(title="Onay bekleyen ilan", status=Listing.Status.REVIEW)
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("listings:moderate_listing", kwargs={"pk": listing.pk, "action": "approve"})
        )
        self.assertRedirects(response, reverse("listings:moderation"))
        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.PUBLISHED)
        self.assertEqual(listing.moderated_by, self.staff)
        self.assertTrue(
            Notification.objects.filter(
                user=self.owner,
                listing=listing,
                notification_type=Notification.Type.LISTING_STATUS,
            ).exists()
        )

    def test_non_staff_cannot_open_moderation_dashboard(self):
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("listings:moderation"))
        self.assertEqual(response.status_code, 403)

    def test_user_can_mark_notification_as_read(self):
        notification = Notification.objects.create(
            user=self.buyer,
            notification_type=Notification.Type.SYSTEM,
            title="Test bildirimi",
            link=reverse("accounts:dashboard"),
        )
        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse("listings:mark_notification_read", kwargs={"pk": notification.pk})
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_location_suggestions_return_districts(self):
        response = self.client.get(
            reverse("listings:location_suggestions"),
            {"city": "Şanlıurfa", "district": "Karaköprü"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Karaköprü", response.json()["districts"])
        self.assertIn("Atakent", response.json()["neighborhoods"])
