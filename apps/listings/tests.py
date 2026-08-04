from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.managed_services.models import ManagedRequest

from .models import Category, Conversation, Favorite, Listing, Message, Offer


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
        self.category = Category.objects.create(name="Elektronik", slug="elektronik")

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

    def test_another_user_can_send_offer(self):
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
        self.assertContains(response, "Teklifin ilan sahibine gönderildi")

    def test_non_owner_cannot_edit_listing(self):
        listing = self.create_listing(title="Satılık masa")
        self.client.force_login(self.buyer)

        response = self.client.get(
            reverse("listings:update", kwargs={"slug": listing.slug})
        )

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
            reverse(
                "listings:change_status",
                kwargs={"slug": listing.slug, "action": "pause"},
            )
        )
        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.PAUSED)

        self.client.post(
            reverse(
                "listings:change_status",
                kwargs={"slug": listing.slug, "action": "publish"},
            )
        )
        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.PUBLISHED)

    def test_non_owner_cannot_change_listing_status(self):
        listing = self.create_listing(title="Korunan ilan")
        self.client.force_login(self.buyer)

        response = self.client.post(
            reverse(
                "listings:change_status",
                kwargs={"slug": listing.slug, "action": "pause"},
            )
        )

        self.assertEqual(response.status_code, 404)
        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.PUBLISHED)

    def test_user_can_start_private_conversation(self):
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
        self.assertEqual(conversation.seller, self.owner)

    def test_only_conversation_participants_can_view_messages(self):
        listing = self.create_listing(title="Özel konuşma ilanı")
        conversation = Conversation.objects.create(
            listing=listing,
            buyer=self.buyer,
            seller=self.owner,
        )
        Message.objects.create(
            conversation=conversation,
            sender=self.buyer,
            body="Merhaba",
        )
        self.client.force_login(self.stranger)

        response = self.client.get(
            reverse("listings:conversation_detail", kwargs={"pk": conversation.pk})
        )

        self.assertEqual(response.status_code, 404)

    def test_owner_can_delete_listing(self):
        listing = self.create_listing(title="Silinecek ilan")
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("listings:delete", kwargs={"slug": listing.slug})
        )

        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.assertFalse(Listing.objects.filter(pk=listing.pk).exists())
