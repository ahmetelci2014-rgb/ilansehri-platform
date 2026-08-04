from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.managed_services.models import ManagedRequest

from .models import Category, Listing, Offer


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
        self.category = Category.objects.create(name="Elektronik", slug="elektronik")

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
        listing = Listing.objects.create(
            owner=self.owner,
            category=self.category,
            kind=Listing.Kind.PRODUCT,
            action=Listing.Action.SELL,
            management_mode=Listing.ManagementMode.SELF,
            title="Satılık dizüstü bilgisayar",
            description="Bakımlı ve sorunsuz.",
            price=Decimal("25000.00"),
            city="Şanlıurfa",
            district="Haliliye",
            status=Listing.Status.PUBLISHED,
        )
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
        listing = Listing.objects.create(
            owner=self.owner,
            category=self.category,
            kind=Listing.Kind.PRODUCT,
            action=Listing.Action.SELL,
            title="Satılık masa",
            description="Ahşap çalışma masası.",
            price=Decimal("3500.00"),
            city="Şanlıurfa",
            district="Eyyübiye",
            status=Listing.Status.PUBLISHED,
        )
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("listings:update", kwargs={"slug": listing.slug}))

        self.assertEqual(response.status_code, 403)
