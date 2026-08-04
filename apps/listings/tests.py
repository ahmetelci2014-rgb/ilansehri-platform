from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User

from .models import (
    Category,
    Conversation,
    Favorite,
    Listing,
    ListingImage,
    Message,
    Notification,
    Offer,
    Review,
    Transaction,
)


TINY_GIF = (
    b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


@override_settings(AUTO_PUBLISH_LISTINGS=True)
class ListingFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="StrongPass_2026", phone="05550000001")
        self.buyer = User.objects.create_user(username="buyer", password="StrongPass_2026", phone="05550000002")
        self.stranger = User.objects.create_user(username="stranger", password="StrongPass_2026")
        self.staff = User.objects.create_user(username="staff", password="StrongPass_2026", is_staff=True)
        self.product_category = Category.objects.create(name="Telefon", slug="telefon")
        self.vehicle_category = Category.objects.create(name="Otomobil", slug="otomobil")

    def create_listing(self, **overrides):
        data = {
            "owner": self.owner,
            "category": self.product_category,
            "kind": Listing.Kind.PRODUCT,
            "action": Listing.Action.SELL,
            "management_mode": Listing.ManagementMode.SELF,
            "title": "Test telefonu",
            "description": "Çok temiz durumda test telefonu.",
            "price": Decimal("25000.00"),
            "condition": "Az kullanılmış",
            "city": "Şanlıurfa",
            "district": "Karaköprü",
            "status": Listing.Status.PUBLISHED,
        }
        data.update(overrides)
        return Listing.objects.create(**data)

    def test_user_can_create_category_specific_vehicle_listing(self):
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
                "delivery_type": Listing.DeliveryType.HANDOVER,
                "city": "Şanlıurfa",
                "district": "Karaköprü",
                "neighborhood": "Akpıyar",
            },
        )
        listing = Listing.objects.get(title="2022 model otomobil")
        self.assertRedirects(response, listing.get_absolute_url())
        self.assertEqual(listing.brand, "Toyota")
        self.assertEqual(listing.model_year, 2022)

    def test_offer_acceptance_creates_transaction_and_rejects_others(self):
        listing = self.create_listing()
        first = Offer.objects.create(listing=listing, sender=self.buyer, amount="23000", message="Bugün alabilirim")
        second = Offer.objects.create(listing=listing, sender=self.stranger, amount="22000", message="Yarın alabilirim")
        self.client.force_login(self.owner)
        response = self.client.post(reverse("listings:offer_action", kwargs={"pk": first.pk, "action": "accept"}))
        transaction = Transaction.objects.get(offer=first)
        self.assertRedirects(response, transaction.get_absolute_url())
        first.refresh_from_db(); second.refresh_from_db(); listing.refresh_from_db()
        self.assertEqual(first.status, Offer.Status.ACCEPTED)
        self.assertEqual(second.status, Offer.Status.REJECTED)
        self.assertEqual(listing.status, Listing.Status.PAUSED)

    def test_two_sided_confirmation_completes_transaction(self):
        listing = self.create_listing()
        offer = Offer.objects.create(listing=listing, sender=self.buyer, amount="23000", message="Teklif")
        offer.status = Offer.Status.ACCEPTED
        offer.save()
        transaction = Transaction.objects.create(listing=listing, offer=offer, buyer=self.buyer, seller=self.owner, amount="23000")
        self.client.force_login(self.buyer)
        self.client.post(reverse("listings:transaction_action", kwargs={"public_id": transaction.public_id, "action": "confirm"}))
        self.client.force_login(self.owner)
        self.client.post(reverse("listings:transaction_action", kwargs={"public_id": transaction.public_id, "action": "confirm"}))
        transaction.refresh_from_db(); listing.refresh_from_db()
        self.assertEqual(transaction.status, Transaction.Status.COMPLETED)
        self.assertEqual(listing.status, Listing.Status.COMPLETED)

    def test_completed_transaction_can_be_reviewed_once(self):
        listing = self.create_listing(status=Listing.Status.COMPLETED)
        offer = Offer.objects.create(listing=listing, sender=self.buyer, amount="23000", message="Teklif", status=Offer.Status.ACCEPTED)
        transaction = Transaction.objects.create(
            listing=listing,
            offer=offer,
            buyer=self.buyer,
            seller=self.owner,
            amount="23000",
            status=Transaction.Status.COMPLETED,
        )
        self.client.force_login(self.buyer)
        url = reverse("listings:create_review", kwargs={"public_id": transaction.public_id})
        self.client.post(url, {"rating": "5", "comment": "Güvenilir satıcı."})
        self.client.post(url, {"rating": "1", "comment": "İkinci yorum."})
        self.assertEqual(Review.objects.filter(transaction=transaction, reviewer=self.buyer).count(), 1)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.rating_count, 1)

    def test_owner_can_manage_listing_images(self):
        listing = self.create_listing()
        image1 = ListingImage.objects.create(
            listing=listing,
            image=SimpleUploadedFile("one.gif", TINY_GIF, content_type="image/gif"),
            is_cover=True,
        )
        image2 = ListingImage.objects.create(
            listing=listing,
            image=SimpleUploadedFile("two.gif", TINY_GIF, content_type="image/gif"),
            sort_order=1,
        )
        self.client.force_login(self.owner)
        self.client.post(reverse("listings:set_cover_image", kwargs={"slug": listing.slug, "image_id": image2.pk}))
        image1.refresh_from_db(); image2.refresh_from_db()
        self.assertFalse(image1.is_cover)
        self.assertTrue(image2.is_cover)
        self.client.post(reverse("listings:delete_image", kwargs={"slug": listing.slug, "image_id": image2.pk}))
        image1.refresh_from_db()
        self.assertTrue(image1.is_cover)

    def test_user_can_favorite_and_private_message(self):
        listing = self.create_listing()
        self.client.force_login(self.buyer)
        self.client.post(reverse("listings:toggle_favorite", kwargs={"slug": listing.slug}))
        self.assertTrue(Favorite.objects.filter(user=self.buyer, listing=listing).exists())
        self.client.post(
            reverse("listings:start_conversation", kwargs={"slug": listing.slug}),
            {"body": "Ürün hâlâ satılık mı?"},
        )
        conversation = Conversation.objects.get(listing=listing, buyer=self.buyer)
        self.assertTrue(Message.objects.filter(conversation=conversation, sender=self.buyer).exists())
        self.assertTrue(Notification.objects.filter(user=self.owner, notification_type=Notification.Type.MESSAGE).exists())

    def test_non_participant_cannot_view_transaction(self):
        listing = self.create_listing()
        offer = Offer.objects.create(listing=listing, sender=self.buyer, message="Teklif", status=Offer.Status.ACCEPTED)
        transaction = Transaction.objects.create(listing=listing, offer=offer, buyer=self.buyer, seller=self.owner)
        self.client.force_login(self.stranger)
        response = self.client.get(transaction.get_absolute_url())
        self.assertEqual(response.status_code, 404)


    def test_staff_can_view_review_listing(self):
        listing = self.create_listing(status=Listing.Status.REVIEW)
        self.client.force_login(self.staff)
        response = self.client.get(listing.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_staff_can_resolve_disputed_transaction(self):
        listing = self.create_listing(status=Listing.Status.PAUSED)
        offer = Offer.objects.create(listing=listing, sender=self.buyer, message="Teklif", status=Offer.Status.ACCEPTED)
        transaction = Transaction.objects.create(
            listing=listing,
            offer=offer,
            buyer=self.buyer,
            seller=self.owner,
            status=Transaction.Status.DISPUTED,
            dispute_reason="Teslim durumu anlaşmazlığı",
        )
        self.client.force_login(self.staff)
        detail = self.client.get(transaction.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.client.post(
            reverse("listings:moderate_transaction", kwargs={"public_id": transaction.public_id, "action": "complete"})
        )
        transaction.refresh_from_db(); listing.refresh_from_db()
        self.assertEqual(transaction.status, Transaction.Status.COMPLETED)
        self.assertEqual(listing.status, Listing.Status.COMPLETED)

    def test_duplicate_pending_offer_is_not_created(self):
        listing = self.create_listing()
        self.client.force_login(self.buyer)
        url = listing.get_absolute_url()
        self.client.post(url, {"amount": "23000", "message": "İlk teklifim"})
        self.client.post(url, {"amount": "24000", "message": "İkinci teklifim"})
        self.assertEqual(Offer.objects.filter(listing=listing, sender=self.buyer, status=Offer.Status.PENDING).count(), 1)

    def test_same_kind_listings_can_be_compared(self):
        first = self.create_listing(title="Birinci telefon")
        second = self.create_listing(title="İkinci telefon")
        vehicle = self.create_listing(
            title="Test aracı",
            category=self.vehicle_category,
            kind=Listing.Kind.VEHICLE,
            brand="Toyota",
        )
        self.client.post(reverse("listings:toggle_compare", kwargs={"slug": first.slug}))
        self.client.post(reverse("listings:toggle_compare", kwargs={"slug": second.slug}))
        self.assertEqual(self.client.session["compare_listing_ids"], [first.pk, second.pk])
        self.client.post(reverse("listings:toggle_compare", kwargs={"slug": vehicle.slug}))
        self.assertEqual(self.client.session["compare_listing_ids"], [first.pk, second.pk])
        response = self.client.get(reverse("listings:compare"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Birinci telefon")
        self.assertContains(response, "İkinci telefon")

    def test_listing_detail_is_added_to_recently_viewed(self):
        listing = self.create_listing()
        response = self.client.get(listing.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session["recently_viewed"][0], listing.pk)

    def test_favorites_page_uses_marketplace_cards(self):
        listing = self.create_listing()
        Favorite.objects.create(user=self.buyer, listing=listing)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("listings:favorites"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, listing.title)
        self.assertContains(response, "market-card")
