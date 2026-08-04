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
    ListingDraft,
    ListingImage,
    ListingPriceHistory,
    Message,
    Notification,
    Offer,
    OfferEvent,
    Review,
    SavedSearch,
    Transaction,
)
from .services import assess_listing_quality, record_price_change


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

    def test_user_can_save_resume_and_delete_server_listing_draft(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("listings:create"),
            {
                "submit_action": "save_draft",
                "kind": Listing.Kind.PRODUCT,
                "action": Listing.Action.SELL,
                "category": self.product_category.pk,
                "title": "Yarım kalan telefon ilanı",
                "description": "Bu açıklama henüz tamamlanmadı.",
                "city": "Şanlıurfa",
                "district": "Karaköprü",
                "is_negotiable": "on",
            },
        )
        draft = ListingDraft.objects.get(user=self.owner)
        self.assertRedirects(response, reverse("listings:drafts"))
        self.assertEqual(draft.title, "Yarım kalan telefon ilanı")
        self.assertTrue(draft.data["is_negotiable"])
        resume = self.client.get(f"{reverse('listings:create')}?draft={draft.pk}")
        self.assertContains(resume, "Yarım kalan telefon ilanı")
        self.assertContains(resume, "Hesabındaki taslak açıldı")
        delete = self.client.post(reverse("listings:delete_draft", kwargs={"pk": draft.pk}))
        self.assertRedirects(delete, reverse("listings:drafts"))
        self.assertFalse(ListingDraft.objects.filter(pk=draft.pk).exists())

    def test_user_cannot_open_another_users_listing_draft(self):
        draft = ListingDraft.objects.create(
            user=self.owner,
            title="Özel taslak",
            data={"title": "Özel taslak"},
        )
        self.client.force_login(self.buyer)
        response = self.client.get(f"{reverse('listings:create')}?draft={draft.pk}")
        self.assertNotContains(response, "Özel taslak")

    def test_publishing_a_resumed_draft_removes_the_draft(self):
        draft = ListingDraft.objects.create(
            user=self.owner,
            title="Yayınlanacak taslak",
            data={"title": "Yayınlanacak taslak"},
        )
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("listings:create"),
            {
                "draft_id": draft.pk,
                "kind": Listing.Kind.PRODUCT,
                "action": Listing.Action.SELL,
                "management_mode": Listing.ManagementMode.SELF,
                "category": self.product_category.pk,
                "title": "Yayınlanacak taslak",
                "description": "Taslak tamamlandı ve yayınlanmaya hazırlandı.",
                "price": "12000.00",
                "condition": "Az kullanılmış",
                "city": "Şanlıurfa",
                "district": "Karaköprü",
            },
        )
        listing = Listing.objects.get(title="Yayınlanacak taslak")
        self.assertRedirects(response, listing.get_absolute_url())
        self.assertFalse(ListingDraft.objects.filter(pk=draft.pk).exists())

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


    def test_seller_can_counter_and_buyer_can_accept(self):
        listing = self.create_listing()
        offer = Offer.objects.create(
            listing=listing,
            sender=self.buyer,
            last_actor=self.buyer,
            amount="23000",
            message="İlk teklif",
        )
        OfferEvent.objects.create(
            offer=offer,
            actor=self.buyer,
            event_type=OfferEvent.Type.SUBMITTED,
            amount=offer.amount,
            message=offer.message,
        )
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("listings:counter_offer", kwargs={"pk": offer.pk}),
            {"amount": "24000", "message": "Bu tutarla bugün teslim edebilirim."},
        )
        self.assertRedirects(response, reverse("listings:offer_center"))
        offer.refresh_from_db()
        self.assertEqual(offer.amount, Decimal("24000"))
        self.assertEqual(offer.last_actor, self.owner)
        self.assertEqual(offer.counter_count, 1)
        self.assertTrue(offer.events.filter(event_type=OfferEvent.Type.COUNTERED).exists())

        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse("listings:offer_action", kwargs={"pk": offer.pk, "action": "accept"})
        )
        transaction = Transaction.objects.get(offer=offer)
        self.assertRedirects(response, transaction.get_absolute_url())
        self.assertEqual(transaction.amount, Decimal("24000"))

    def test_price_drop_notifies_users_who_favorited_listing(self):
        listing = self.create_listing()
        Favorite.objects.create(user=self.buyer, listing=listing)
        old_price = listing.price
        listing.price = Decimal("22000")
        listing.save(update_fields=["price", "updated_at"])
        record_price_change(
            listing=listing,
            old_price=old_price,
            new_price=listing.price,
            actor=self.owner,
        )
        history = ListingPriceHistory.objects.get(listing=listing)
        self.assertTrue(history.is_drop)
        self.assertTrue(
            Notification.objects.filter(
                user=self.buyer,
                listing=listing,
                notification_type=Notification.Type.PRICE_DROP,
            ).exists()
        )

    def test_offer_post_creates_offer_history(self):
        listing = self.create_listing()
        self.client.force_login(self.buyer)
        self.client.post(
            listing.get_absolute_url(),
            {"amount": "23000", "message": "Bugün teslim alabilirim."},
        )
        offer = Offer.objects.get(listing=listing, sender=self.buyer)
        self.assertEqual(offer.last_actor, self.buyer)
        self.assertTrue(offer.events.filter(event_type=OfferEvent.Type.SUBMITTED).exists())
    def test_price_drop_waits_for_moderation_before_notification(self):
        listing = self.create_listing(status=Listing.Status.REVIEW)
        Favorite.objects.create(user=self.buyer, listing=listing)
        history = record_price_change(
            listing=listing,
            old_price=Decimal("25000"),
            new_price=Decimal("22000"),
            actor=self.owner,
        )
        self.assertIsNone(history.notifications_sent_at)
        self.assertFalse(
            Notification.objects.filter(
                user=self.buyer,
                listing=listing,
                notification_type=Notification.Type.PRICE_DROP,
            ).exists()
        )
        self.client.force_login(self.staff)
        self.client.post(
            reverse("listings:moderate_listing", kwargs={"pk": listing.pk, "action": "approve"})
        )
        history.refresh_from_db()
        self.assertIsNotNone(history.notifications_sent_at)
        self.assertEqual(
            Notification.objects.filter(
                user=self.buyer,
                listing=listing,
                notification_type=Notification.Type.PRICE_DROP,
            ).count(),
            1,
        )

    def test_stranger_cannot_counter_an_offer(self):
        listing = self.create_listing()
        offer = Offer.objects.create(
            listing=listing,
            sender=self.buyer,
            last_actor=self.buyer,
            amount=Decimal("23000"),
            message="Teklif",
        )
        self.client.force_login(self.stranger)
        response = self.client.post(
            reverse("listings:counter_offer", kwargs={"pk": offer.pk}),
            {"amount": "24000", "message": "Yetkisiz karşı teklif"},
        )
        self.assertEqual(response.status_code, 404)
        offer.refresh_from_db()
        self.assertEqual(offer.amount, Decimal("23000"))


    def test_kind_landing_page_lists_matching_items(self):
        listing = self.create_listing(title="Kategori vitrini telefonu")
        response = self.client.get(reverse("listings:kind_landing", kwargs={"kind": Listing.Kind.PRODUCT}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, listing.title)
        self.assertContains(response, "İkinci el ve sıfır ürünleri keşfet")

    def test_search_suggestions_returns_active_listing(self):
        listing = self.create_listing(title="Özel arama telefonu")
        response = self.client.get(reverse("listings:search_suggestions"), {"q": "Özel arama"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(any(item["url"] == listing.get_absolute_url() for item in payload["results"]))

    def test_saved_search_page_and_alert_toggle_are_private(self):
        saved = SavedSearch.objects.create(
            user=self.buyer,
            name="Telefon aramam",
            query_params={"q": "telefon", "city": "Şanlıurfa"},
            alert_enabled=True,
        )
        anonymous = self.client.get(reverse("listings:saved_searches"))
        self.assertEqual(anonymous.status_code, 302)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("listings:saved_searches"))
        self.assertContains(response, "Telefon aramam")
        self.client.post(reverse("listings:toggle_saved_search_alert", kwargs={"pk": saved.pk}))
        saved.refresh_from_db()
        self.assertFalse(saved.alert_enabled)

    def test_notifications_can_be_filtered(self):
        Notification.objects.create(
            user=self.buyer,
            notification_type=Notification.Type.MESSAGE,
            title="Yeni mesaj",
        )
        Notification.objects.create(
            user=self.buyer,
            notification_type=Notification.Type.OFFER,
            title="Yeni teklif",
            is_read=True,
        )
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("listings:notifications"), {"type": "message", "status": "unread"})
        self.assertContains(response, "Yeni mesaj")
        self.assertNotContains(response, "Yeni teklif")


class ListingQualityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="quality-owner", password="StrongPass_2026", is_phone_verified=True
        )
        self.category = Category.objects.create(name="Kalite Ürün", slug="kalite-urun")

    def test_quality_profile_rewards_complete_listing(self):
        listing = Listing.objects.create(
            owner=self.owner, category=self.category, kind=Listing.Kind.PRODUCT, action=Listing.Action.SELL,
            title="Kutulu ve garantili profesyonel telefon ilanı",
            description="Ürün temiz kullanılmıştır. Kutusu, faturası ve teslim koşulları mevcuttur. Tüm kusurlar açıklamada belirtilmiştir ve elden teslim mümkündür.",
            price=Decimal("25000"), condition="Az kullanılmış", brand="Örnek Marka",
            delivery_type=Listing.DeliveryType.HANDOVER, city="Şanlıurfa", district="Karaköprü",
            status=Listing.Status.PUBLISHED,
        )
        profile = assess_listing_quality(listing)
        self.assertGreaterEqual(profile["score"], 70)
        self.assertNotIn("Açıklamada telefon numarası", profile["risk_flags"])
        self.assertNotIn("Çok kısa açıklama", profile["risk_flags"])

    def test_quality_profile_flags_phone_number_and_short_text(self):
        listing = Listing.objects.create(
            owner=self.owner, category=self.category, kind=Listing.Kind.PRODUCT, action=Listing.Action.SELL,
            title="ACİL!!!", description="Ara 0555 111 22 33", city="Şanlıurfa", district="Haliliye",
            status=Listing.Status.REVIEW,
        )
        profile = assess_listing_quality(listing)
        self.assertIn("Açıklamada telefon numarası", profile["risk_flags"])
        self.assertIn("Çok kısa açıklama", profile["risk_flags"])
