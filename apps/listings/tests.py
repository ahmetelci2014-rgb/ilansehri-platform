from decimal import Decimal

from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import AccountRiskEvent, NotificationPreference, User, UserBlock
from apps.support_center.models import StaffActionLog

from .models import (
    Category,
    Conversation,
    Favorite,
    Listing,
    ListingDraft,
    ListingImage,
    ListingMatch,
    ListingPriceHistory,
    Message,
    Notification,
    Offer,
    OfferEvent,
    Review,
    SavedSearch,
    SavedSearchMatch,
    Transaction,
)
from .matching import score_listing_pair, sync_listing_matches
from .message_safety import analyze_message, safe_notification_preview
from .pricing import build_price_guide
from .safety import assess_listing_safety
from .services import (
    assess_listing_quality,
    create_notification,
    notify_listing_publication,
    record_price_change,
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

    def test_saved_search_frequency_is_sanitized_and_duplicate_is_updated(self):
        self.client.force_login(self.buyer)
        url = reverse("listings:save_search")
        self.client.post(
            url,
            {
                "name": "Şanlıurfa telefon",
                "q": "telefon",
                "city": "Şanlıurfa",
                "alert_frequency": SavedSearch.AlertFrequency.DAILY,
                "unsupported": "saklanmamali",
            },
        )
        saved = SavedSearch.objects.get(user=self.buyer)
        self.assertEqual(saved.alert_frequency, SavedSearch.AlertFrequency.DAILY)
        self.assertTrue(saved.alert_enabled)
        self.assertNotIn("unsupported", saved.query_params)

        self.client.post(
            url,
            {
                "name": "Telefon fırsatları",
                "q": "telefon",
                "city": "Şanlıurfa",
                "alert_frequency": SavedSearch.AlertFrequency.OFF,
            },
        )
        self.assertEqual(SavedSearch.objects.filter(user=self.buyer).count(), 1)
        saved.refresh_from_db()
        self.assertEqual(saved.name, "Telefon fırsatları")
        self.assertFalse(saved.alert_enabled)

    def test_instant_saved_search_notification_is_created_only_once(self):
        saved = SavedSearch.objects.create(
            user=self.buyer,
            name="Telefon alarmı",
            query_params={"q": "telefon", "city": "Şanlıurfa"},
            alert_frequency=SavedSearch.AlertFrequency.INSTANT,
        )
        listing = self.create_listing(title="Yeni test telefonu")
        notify_listing_publication(listing)
        notify_listing_publication(listing)
        self.assertEqual(SavedSearchMatch.objects.filter(saved_search=saved, listing=listing).count(), 1)
        self.assertEqual(
            Notification.objects.filter(user=self.buyer, listing=listing, title__contains="Telefon alarmı").count(),
            1,
        )

    def test_daily_saved_search_is_grouped_by_maintenance(self):
        saved = SavedSearch.objects.create(
            user=self.buyer,
            name="Günlük araç özeti",
            query_params={"kind": Listing.Kind.VEHICLE, "city": "Şanlıurfa"},
            alert_frequency=SavedSearch.AlertFrequency.DAILY,
        )
        listing = self.create_listing(
            category=self.vehicle_category,
            kind=Listing.Kind.VEHICLE,
            title="Günlük özete uygun otomobil",
        )
        call_command("marketplace_maintenance")
        saved.refresh_from_db()
        self.assertIsNotNone(saved.last_checked_at)
        self.assertTrue(SavedSearchMatch.objects.filter(saved_search=saved, listing=listing).exists())
        self.assertTrue(Notification.objects.filter(user=self.buyer, title__contains="günlük arama özeti").exists())

    def test_nearby_search_filters_and_exposes_distance(self):
        near = self.create_listing(
            title="Yakındaki telefon",
            latitude=Decimal("37.167400"),
            longitude=Decimal("38.795500"),
        )
        far = self.create_listing(
            title="Uzaktaki telefon",
            latitude=Decimal("41.008200"),
            longitude=Decimal("28.978400"),
        )
        response = self.client.get(
            reverse("listings:list"),
            {"lat": "37.167000", "lng": "38.795000", "radius": "25", "sort": "nearby"},
        )
        self.assertContains(response, near.title)
        self.assertNotContains(response, far.title)
        self.assertContains(response, "km")

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

    def test_optional_notification_can_be_muted_but_critical_notification_remains(self):
        preference = NotificationPreference.objects.get(user=self.buyer)
        preference.in_app_messages = False
        preference.save(update_fields=["in_app_messages", "updated_at"])
        create_notification(
            user=self.buyer,
            notification_type=Notification.Type.MESSAGE,
            title="Sessize alınan mesaj",
        )
        create_notification(
            user=self.buyer,
            notification_type=Notification.Type.SYSTEM,
            title="Önemli sistem bildirimi",
        )
        self.assertFalse(Notification.objects.filter(user=self.buyer, title="Sessize alınan mesaj").exists())
        self.assertTrue(Notification.objects.filter(user=self.buyer, title="Önemli sistem bildirimi").exists())

    def test_staff_can_bulk_approve_review_listings_and_actions_are_logged(self):
        first = self.create_listing(title="Toplu onay bir", status=Listing.Status.REVIEW)
        second = self.create_listing(title="Toplu onay iki", status=Listing.Status.REVIEW)
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("listings:bulk_moderate_listings"),
            {
                "listing_ids": [str(first.pk), str(second.pk)],
                "bulk_action": "approve",
                "bulk_note": "",
            },
        )
        self.assertRedirects(response, reverse("listings:moderation"))
        first.refresh_from_db(); second.refresh_from_db()
        self.assertEqual(first.status, Listing.Status.PUBLISHED)
        self.assertEqual(second.status, Listing.Status.PUBLISHED)
        self.assertEqual(
            StaffActionLog.objects.filter(
                action=StaffActionLog.Action.LISTING_MODERATION, actor=self.staff
            ).count(),
            2,
        )

    def test_bulk_reject_requires_common_note(self):
        listing = self.create_listing(title="Not bekleyen ilan", status=Listing.Status.REVIEW)
        self.client.force_login(self.staff)
        self.client.post(
            reverse("listings:bulk_moderate_listings"),
            {"listing_ids": [str(listing.pk)], "bulk_action": "reject", "bulk_note": ""},
        )
        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.REVIEW)


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


@override_settings(AUTO_PUBLISH_LISTINGS=True)
class ListingMatchingTests(TestCase):
    def setUp(self):
        self.seeker = User.objects.create_user(
            username="match-seeker", password="StrongPass_2026", phone="05550000101"
        )
        self.seller = User.objects.create_user(
            username="match-seller", password="StrongPass_2026", phone="05550000102"
        )
        self.other = User.objects.create_user(
            username="match-other", password="StrongPass_2026", phone="05550000103"
        )
        self.root = Category.objects.create(name="Ürün & Eşya", slug="match-urun-root")
        self.phone = Category.objects.create(name="Telefon", slug="match-telefon", parent=self.root)
        self.vehicle_root = Category.objects.create(name="Araç", slug="match-arac-root")
        self.vehicle = Category.objects.create(name="Otomobil", slug="match-otomobil", parent=self.vehicle_root)

    def create_wanted(self, **overrides):
        data = {
            "owner": self.seeker,
            "category": self.phone,
            "kind": Listing.Kind.PRODUCT,
            "action": Listing.Action.WANTED,
            "title": "Apple iPhone 15 128 GB arıyorum",
            "description": "Kutulu veya temiz durumda iPhone 15 arıyorum. Siyah renk tercih edilir.",
            "price": Decimal("40000"),
            "brand": "Apple",
            "model_name": "iPhone 15",
            "city": "Şanlıurfa",
            "district": "Karaköprü",
            "status": Listing.Status.PUBLISHED,
        }
        data.update(overrides)
        return Listing.objects.create(**data)

    def create_offer(self, **overrides):
        data = {
            "owner": self.seller,
            "category": self.phone,
            "kind": Listing.Kind.PRODUCT,
            "action": Listing.Action.SELL,
            "title": "Kutulu Apple iPhone 15 128 GB siyah",
            "description": "Temiz kullanılmış, kutulu iPhone 15. Elden teslim edilebilir.",
            "price": Decimal("38500"),
            "brand": "Apple",
            "model_name": "iPhone 15",
            "condition": "Az kullanılmış",
            "city": "Şanlıurfa",
            "district": "Karaköprü",
            "status": Listing.Status.PUBLISHED,
        }
        data.update(overrides)
        return Listing.objects.create(**data)

    def test_matching_scores_category_brand_model_location_and_budget(self):
        wanted = self.create_wanted()
        offered = self.create_offer()
        result = score_listing_pair(wanted, offered)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.score, 80)
        self.assertIn("Aynı kategori", result.reasons)
        self.assertIn("Marka eşleşiyor", result.reasons)
        self.assertIn("Model eşleşiyor", result.reasons)
        self.assertIn("Aynı şehir", result.reasons)
        self.assertIn("Bütçeye uygun", result.reasons)

    def test_sync_creates_one_match_and_notifies_both_sides_once(self):
        wanted = self.create_wanted()
        offered = self.create_offer()
        first = sync_listing_matches(offered, notify=True)
        second = sync_listing_matches(offered, notify=True)
        self.assertEqual(first["created"], 1)
        self.assertEqual(second["created"], 0)
        match = ListingMatch.objects.get(wanted_listing=wanted, offered_listing=offered)
        self.assertGreaterEqual(match.score, 80)
        self.assertEqual(
            Notification.objects.filter(user=self.seeker, notification_type=Notification.Type.MATCH).count(),
            1,
        )
        self.assertEqual(
            Notification.objects.filter(user=self.seller, notification_type=Notification.Type.MATCH).count(),
            1,
        )

    def test_muted_match_preference_keeps_match_but_suppresses_notification(self):
        wanted = self.create_wanted()
        offered = self.create_offer()
        preference = NotificationPreference.objects.get(user=self.seeker)
        preference.in_app_matches = False
        preference.save(update_fields=["in_app_matches", "updated_at"])
        sync_listing_matches(offered, notify=True)
        self.assertTrue(ListingMatch.objects.filter(wanted_listing=wanted, offered_listing=offered).exists())
        self.assertFalse(
            Notification.objects.filter(user=self.seeker, notification_type=Notification.Type.MATCH).exists()
        )

    def test_match_center_is_private_and_dismissal_is_side_specific(self):
        wanted = self.create_wanted()
        offered = self.create_offer()
        sync_listing_matches(offered, notify=False)
        match = ListingMatch.objects.get(wanted_listing=wanted, offered_listing=offered)
        anonymous = self.client.get(reverse("listings:matches"))
        self.assertEqual(anonymous.status_code, 302)
        self.client.force_login(self.seeker)
        page = self.client.get(reverse("listings:matches"))
        self.assertContains(page, offered.title)
        response = self.client.post(reverse("listings:dismiss_match", kwargs={"pk": match.pk}))
        self.assertRedirects(response, f"{reverse('listings:matches')}?tab=wanted")
        match.refresh_from_db()
        self.assertEqual(match.wanted_status, ListingMatch.Status.DISMISSED)
        self.assertNotEqual(match.offered_status, ListingMatch.Status.DISMISSED)

    def test_different_listing_kind_does_not_match(self):
        wanted = self.create_wanted()
        vehicle_offer = self.create_offer(
            category=self.vehicle,
            kind=Listing.Kind.VEHICLE,
            title="2022 model Toyota Corolla",
            brand="Toyota",
            model_name="Corolla",
        )
        self.assertIsNone(score_listing_pair(wanted, vehicle_offer))

    def test_publishing_offer_through_form_creates_match(self):
        wanted = self.create_wanted()
        self.client.force_login(self.seller)
        response = self.client.post(
            reverse("listings:create"),
            {
                "kind": Listing.Kind.PRODUCT,
                "action": Listing.Action.SELL,
                "management_mode": Listing.ManagementMode.SELF,
                "category": self.phone.pk,
                "title": "Apple iPhone 15 128 GB temiz telefon",
                "description": "Kutulu ve temiz iPhone 15, Karaköprü elden teslim.",
                "price": "39000",
                "brand": "Apple",
                "model_name": "iPhone 15",
                "condition": "Az kullanılmış",
                "delivery_type": Listing.DeliveryType.HANDOVER,
                "city": "Şanlıurfa",
                "district": "Karaköprü",
            },
        )
        offered = Listing.objects.get(title="Apple iPhone 15 128 GB temiz telefon")
        self.assertRedirects(response, offered.get_absolute_url())
        self.assertTrue(ListingMatch.objects.filter(wanted_listing=wanted, offered_listing=offered).exists())

    def test_same_category_without_semantic_overlap_does_not_match(self):
        wanted = self.create_wanted(
            brand="Apple",
            model_name="iPhone 15",
            title="Apple iPhone 15 arıyorum",
            description="iPhone 15 telefon arıyorum.",
        )
        unrelated = self.create_offer(
            brand="Samsung",
            model_name="Galaxy S24",
            title="Samsung Galaxy S24 Ultra",
            description="Samsung Android telefon satılıktır.",
        )
        self.assertIsNone(score_listing_pair(wanted, unrelated))

    def test_sync_removes_stale_match_after_listing_changes(self):
        wanted = self.create_wanted()
        offered = self.create_offer()
        sync_listing_matches(offered, notify=False)
        self.assertTrue(ListingMatch.objects.filter(wanted_listing=wanted, offered_listing=offered).exists())

        offered.title = "Samsung Galaxy S24 Ultra"
        offered.description = "Samsung Android telefon satılıktır."
        offered.brand = "Samsung"
        offered.model_name = "Galaxy S24"
        offered.save()
        result = sync_listing_matches(offered, notify=False)

        self.assertGreaterEqual(result["deleted"], 1)
        self.assertFalse(ListingMatch.objects.filter(wanted_listing=wanted, offered_listing=offered).exists())

    def test_blocked_users_do_not_see_existing_match(self):
        wanted = self.create_wanted()
        offered = self.create_offer()
        sync_listing_matches(offered, notify=False)
        UserBlock.objects.create(blocker=self.seeker, blocked=self.seller)

        self.client.force_login(self.seeker)
        response = self.client.get(reverse("listings:matches"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, offered.title)
        self.assertEqual(response.context["wanted_match_count"], 0)



@override_settings(AUTO_PUBLISH_LISTINGS=True)
class ListingPriceGuideTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="price-owner", password="StrongPass_2026")
        self.root = Category.objects.create(name="Elektronik", slug="price-elektronik")
        self.category = Category.objects.create(name="Akıllı Telefon", slug="price-telefon", parent=self.root)
        self.comparison_prices = [
            Decimal("20000"), Decimal("22000"), Decimal("24000"), Decimal("25000"),
            Decimal("26000"), Decimal("28000"), Decimal("30000"), Decimal("250000"),
        ]
        for index, price in enumerate(self.comparison_prices):
            seller = User.objects.create_user(username=f"price-seller-{index}", password="StrongPass_2026")
            Listing.objects.create(
                owner=seller,
                category=self.category,
                kind=Listing.Kind.PRODUCT,
                action=Listing.Action.SELL,
                title=f"Apple iPhone 15 ilanı {index}",
                description="Temiz kullanılmış, kutulu telefon.",
                price=price,
                brand="Apple",
                model_name="iPhone 15",
                city="Şanlıurfa",
                district="Karaköprü",
                status=Listing.Status.PUBLISHED,
            )

    def subject(self, **overrides):
        data = {
            "owner": self.owner,
            "category": self.category,
            "kind": Listing.Kind.PRODUCT,
            "action": Listing.Action.SELL,
            "title": "Apple iPhone 15",
            "description": "Temiz telefon",
            "price": Decimal("55000"),
            "brand": "Apple",
            "model_name": "iPhone 15",
            "city": "Şanlıurfa",
            "district": "Karaköprü",
        }
        data.update(overrides)
        return Listing(**data)

    def test_price_guide_removes_outlier_and_classifies_high_price(self):
        guide = build_price_guide(self.subject())
        self.assertTrue(guide.available)
        self.assertEqual(guide.status, "high")
        self.assertGreaterEqual(guide.sample_count, 7)
        self.assertGreaterEqual(guide.removed_outliers, 1)
        self.assertLess(guide.upper_price, Decimal("100000"))
        self.assertGreater(guide.median_price, Decimal("20000"))

    def test_price_guide_returns_unavailable_when_similar_data_is_insufficient(self):
        Listing.objects.exclude(owner=self.owner).delete()
        seller = User.objects.create_user(username="single-price-seller", password="StrongPass_2026")
        Listing.objects.create(
            owner=seller, category=self.category, kind=Listing.Kind.PRODUCT,
            action=Listing.Action.SELL, title="Tek karşılaştırma", description="Tek ilan",
            price=Decimal("25000"), brand="Apple", model_name="iPhone 15",
            city="Şanlıurfa", district="Karaköprü", status=Listing.Status.PUBLISHED,
        )
        guide = build_price_guide(self.subject())
        self.assertFalse(guide.available)
        self.assertIn("yeterli", guide.message.lower())

    def test_vehicle_guide_uses_brand_model_year_and_mileage(self):
        vehicle_root = Category.objects.create(name="Araç", slug="price-vehicle-root")
        vehicle_category = Category.objects.create(name="Otomobil", slug="price-vehicle", parent=vehicle_root)
        prices = [Decimal("900000"), Decimal("940000"), Decimal("975000"), Decimal("1010000"), Decimal("1050000")]
        sellers = list(User.objects.filter(username__startswith="price-seller-").order_by("username")[:5])
        for index, (seller, price) in enumerate(zip(sellers, prices)):
            Listing.objects.create(
                owner=seller, category=vehicle_category, kind=Listing.Kind.VEHICLE,
                action=Listing.Action.SELL, title=f"Toyota Corolla 2022 {index}",
                description="Bakımlı otomobil", price=price, brand="Toyota", model_name="Corolla",
                model_year=2021 + (index % 3), mileage=35000 + (index * 5000),
                city="Şanlıurfa", district="Haliliye", status=Listing.Status.PUBLISHED,
            )
        guide = build_price_guide(self.subject(
            category=vehicle_category, kind=Listing.Kind.VEHICLE, price=Decimal("1200000"),
            brand="Toyota", model_name="Corolla", model_year=2022, mileage=45000,
        ))
        self.assertTrue(guide.available)
        self.assertTrue(any("marka" in item.lower() and "model" in item.lower() for item in guide.criteria))
        self.assertEqual(guide.status, "high")

    def test_real_estate_guide_prioritizes_location_room_and_area(self):
        estate_root = Category.objects.create(name="Emlak", slug="price-estate-root")
        estate_category = Category.objects.create(name="Konut", slug="price-estate", parent=estate_root)
        prices = [Decimal("20000"), Decimal("21000"), Decimal("22000"), Decimal("23000"), Decimal("24000"), Decimal("25000")]
        sellers = list(User.objects.filter(username__startswith="price-seller-").order_by("username")[:6])
        for index, (seller, price) in enumerate(zip(sellers, prices)):
            Listing.objects.create(
                owner=seller, category=estate_category, kind=Listing.Kind.REAL_ESTATE,
                action=Listing.Action.RENT, title=f"Karaköprü 3+1 daire {index}",
                description="Bakımlı kiralık daire", price=price, room_count="3+1",
                area_m2=150 + (index * 5), city="Şanlıurfa", district="Karaköprü",
                neighborhood="Akpıyar", status=Listing.Status.PUBLISHED,
            )
        guide = build_price_guide(self.subject(
            category=estate_category, kind=Listing.Kind.REAL_ESTATE, action=Listing.Action.RENT,
            price=Decimal("32000"), brand="", model_name="", room_count="3+1", area_m2=165,
            city="Şanlıurfa", district="Karaköprü", neighborhood="Akpıyar",
        ))
        self.assertTrue(guide.available)
        self.assertTrue(any("mahalle" in item.lower() or "ilçe" in item.lower() for item in guide.criteria))
        self.assertEqual(guide.status, "high")

    def test_real_estate_root_fallback_accepts_child_category_filter(self):
        estate_root = Category.objects.create(name="Emlak kökü", slug="price-estate-fallback-root")
        subject_category = Category.objects.create(
            name="Kiralık daire", slug="price-estate-fallback-subject", parent=estate_root
        )
        sibling_category = Category.objects.create(
            name="Kiralık konut", slug="price-estate-fallback-sibling", parent=estate_root
        )
        prices = [
            Decimal("18000"), Decimal("19000"), Decimal("20000"),
            Decimal("21000"), Decimal("22000"), Decimal("23000"),
        ]
        sellers = list(User.objects.filter(username__startswith="price-seller-").order_by("username")[:6])
        for index, (seller, price) in enumerate(zip(sellers, prices)):
            Listing.objects.create(
                owner=seller, category=sibling_category, kind=Listing.Kind.REAL_ESTATE,
                action=Listing.Action.RENT, title=f"Karaköprü kiralık konut {index}",
                description="Benzer bölgede kiralık konut", price=price, room_count="3+1",
                area_m2=150 + index, city="Şanlıurfa", district="Karaköprü",
                status=Listing.Status.PUBLISHED,
            )

        guide = build_price_guide(self.subject(
            category=subject_category, kind=Listing.Kind.REAL_ESTATE,
            action=Listing.Action.RENT, price=Decimal("25000"), brand="", model_name="",
            room_count="3+1", area_m2=152, city="Şanlıurfa", district="Karaköprü",
        ))

        self.assertTrue(guide.available)
        self.assertGreaterEqual(guide.sample_count, 6)
        self.assertTrue(any("yakın emlak kategorisi" in item.lower() for item in guide.criteria))

        listing = Listing.objects.create(
            owner=self.owner, category=subject_category, kind=Listing.Kind.REAL_ESTATE,
            action=Listing.Action.RENT, title="Demo emlak kök filtre testi",
            description="İlan detayında fiyat rehberi hatası üretmemeli.",
            price=Decimal("25000"), room_count="3+1", area_m2=152,
            city="Şanlıurfa", district="Karaköprü", status=Listing.Status.PUBLISHED,
        )
        detail = self.client.get(listing.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "AKILLI FİYAT REHBERİ")

    def test_authenticated_price_guide_endpoint_returns_market_range(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("listings:price_guide"),
            {
                "kind": Listing.Kind.PRODUCT,
                "action": Listing.Action.SELL,
                "category": self.category.pk,
                "price": "55000",
                "brand": "Apple",
                "model_name": "iPhone 15",
                "city": "Şanlıurfa",
                "district": "Karaköprü",
            },
        )
        self.assertEqual(response.status_code, 200)
        guide = response.json()["guide"]
        self.assertTrue(guide["available"])
        self.assertEqual(guide["status"], "high")
        self.assertGreaterEqual(guide["sample_count"], 7)

    def test_listing_form_and_detail_show_price_guide_components(self):
        self.client.force_login(self.owner)
        form_page = self.client.get(reverse("listings:create"))
        self.assertContains(form_page, "data-price-guide-assistant")
        self.assertContains(form_page, reverse("listings:price_guide"))

        listing = Listing.objects.create(
            owner=self.owner, category=self.category, kind=Listing.Kind.PRODUCT,
            action=Listing.Action.SELL, title="Pahalı iPhone 15", description="Temiz telefon",
            price=Decimal("55000"), brand="Apple", model_name="iPhone 15",
            city="Şanlıurfa", district="Karaköprü", status=Listing.Status.PUBLISHED,
        )
        detail = self.client.get(listing.get_absolute_url())
        self.assertContains(detail, "AKILLI FİYAT REHBERİ")
        self.assertContains(detail, "Piyasanın üzerinde")


@override_settings(AUTO_PUBLISH_LISTINGS=True)
class MessageSafetyTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="safety-owner", password="StrongPass_2026", phone="05551110001"
        )
        self.buyer = User.objects.create_user(
            username="safety-buyer", password="StrongPass_2026", phone="05551110002"
        )
        self.category = Category.objects.create(name="Güvenlik telefonu", slug="safety-phone")
        self.listing = Listing.objects.create(
            owner=self.owner, category=self.category, kind=Listing.Kind.PRODUCT,
            action=Listing.Action.SELL, title="Güvenli mesaj test telefonu",
            description="Mesaj güvenliği için yayınlanan ilan.", price=Decimal("25000"),
            city="Şanlıurfa", district="Karaköprü", status=Listing.Status.PUBLISHED,
        )

    def test_analyzer_distinguishes_safe_and_critical_messages(self):
        safe = analyze_message("Ürün hâlâ satılık mı, yarın görebilir miyim?")
        critical = analyze_message("AnyDesk kur, SMS doğrulama kodunu hemen gönder.")
        self.assertEqual(safe.level, "safe")
        self.assertEqual(critical.level, "critical")
        self.assertTrue(critical.requires_confirmation)
        self.assertIn("credential", critical.flags)
        self.assertIn("remote_access", critical.flags)

    def test_safe_message_is_sent_without_confirmation(self):
        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse("listings:start_conversation", kwargs={"slug": self.listing.slug}),
            {"body": "Ürün hâlâ satılık mı?"},
        )
        conversation = Conversation.objects.get(listing=self.listing, buyer=self.buyer)
        self.assertRedirects(response, reverse("listings:conversation_detail", kwargs={"pk": conversation.pk}))
        self.assertEqual(conversation.messages.count(), 1)

    def test_high_risk_message_requires_confirmation_and_keeps_text(self):
        self.client.force_login(self.buyer)
        url = reverse("listings:start_conversation", kwargs={"slug": self.listing.slug})
        risky_body = "Kapora için ödeme linkini aç ve SMS doğrulama kodunu gönder."
        response = self.client.post(url, {"body": risky_body})
        self.assertRedirects(response, f"{self.listing.get_absolute_url()}#message-box", fetch_redirect_response=False)
        self.assertFalse(Conversation.objects.filter(listing=self.listing, buyer=self.buyer).exists())

        detail = self.client.get(self.listing.get_absolute_url())
        self.assertContains(detail, risky_body)
        self.assertContains(detail, "data-message-safety-confirm")
        self.assertContains(detail, "open")

        sent = self.client.post(url, {"body": risky_body, "safety_confirmed": "on"})
        conversation = Conversation.objects.get(listing=self.listing, buyer=self.buyer)
        self.assertRedirects(sent, reverse("listings:conversation_detail", kwargs={"pk": conversation.pk}))
        self.assertEqual(conversation.messages.count(), 1)
        notification = Notification.objects.get(user=self.owner, notification_type=Notification.Type.MESSAGE)
        self.assertIn("Güvenlik uyarısı", notification.body)
        self.assertNotIn("doğrulama kodunu", notification.body.lower())

    def test_conversation_reply_shows_server_warning_and_receiver_banner(self):
        conversation = Conversation.objects.create(
            listing=self.listing, buyer=self.buyer, seller=self.owner
        )
        Message.objects.create(
            conversation=conversation, sender=self.owner, body="Merhaba, ilan güncel."
        )
        self.client.force_login(self.buyer)
        url = reverse("listings:conversation_detail", kwargs={"pk": conversation.pk})
        risky_body = "AnyDesk kurup ekranını paylaş, sonra kaporayı havale yap."
        blocked = self.client.post(url, {"body": risky_body})
        self.assertEqual(blocked.status_code, 200)
        self.assertContains(blocked, "yüksek riskli ifade")
        self.assertEqual(conversation.messages.count(), 1)

        sent = self.client.post(url, {"body": risky_body, "safety_confirmed": "on"})
        self.assertRedirects(sent, url)
        self.assertEqual(conversation.messages.count(), 2)
        detail = self.client.get(url)
        self.assertContains(detail, "Kritik güvenlik uyarısı")
        self.assertContains(detail, "Cihaza uzaktan erişim")

    def test_high_risk_notification_preview_does_not_repeat_message(self):
        preview = safe_notification_preview(
            "Ahmet", "SMS doğrulama kodunu ve kart şifreni gönder."
        )
        self.assertIn("Güvenlik uyarısı", preview)
        self.assertNotIn("kart şifreni", preview)


class TrustSafetyInfrastructureTests(TestCase):
    def setUp(self):
        self.first_owner = User.objects.create_user(username="photo-owner-a", password="StrongPass_2026")
        self.second_owner = User.objects.create_user(username="photo-owner-b", password="StrongPass_2026")
        self.category = Category.objects.create(name="Risk test", slug="risk-test")
        self.first_listing = Listing.objects.create(
            owner=self.first_owner,
            category=self.category,
            kind=Listing.Kind.PRODUCT,
            action=Listing.Action.SELL,
            title="Birinci fotoğraf ilanı",
            description="Aynı fotoğraf parmak izi kontrolü için yeterli açıklama.",
            price=Decimal("1000"),
            city="Şanlıurfa",
            district="Haliliye",
            status=Listing.Status.REVIEW,
        )
        self.second_listing = Listing.objects.create(
            owner=self.second_owner,
            category=self.category,
            kind=Listing.Kind.PRODUCT,
            action=Listing.Action.SELL,
            title="İkinci fotoğraf ilanı",
            description="Aynı fotoğrafın farklı hesaplarda kullanımını test eder.",
            price=Decimal("900"),
            city="Şanlıurfa",
            district="Haliliye",
            status=Listing.Status.REVIEW,
        )

    def test_same_image_bytes_create_duplicate_signal(self):
        first = ListingImage.objects.create(
            listing=self.first_listing,
            image=SimpleUploadedFile("first.gif", TINY_GIF, content_type="image/gif"),
        )
        second = ListingImage.objects.create(
            listing=self.second_listing,
            image=SimpleUploadedFile("second.gif", TINY_GIF, content_type="image/gif"),
        )
        self.assertTrue(first.fingerprint)
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(second.duplicate_owner_count, 1)
        profile = assess_listing_safety(self.second_listing)
        self.assertGreaterEqual(profile["score"], 20)
        self.assertIn("Fotoğraf başka hesaplarda da kullanılmış", profile["flags"])

    def test_confirmed_high_risk_message_creates_staff_risk_event(self):
        listing = Listing.objects.create(
            owner=self.first_owner,
            category=self.category,
            kind=Listing.Kind.PRODUCT,
            action=Listing.Action.SELL,
            title="Mesaj risk ilanı",
            description="Güvenli mesaj risk kaydı oluşturmak için yayınlanan test ilanı.",
            price=Decimal("1000"),
            city="Şanlıurfa",
            district="Haliliye",
            status=Listing.Status.PUBLISHED,
        )
        self.client.force_login(self.second_owner)
        response = self.client.post(
            reverse("listings:start_conversation", kwargs={"slug": listing.slug}),
            {
                "body": "AnyDesk kur ve SMS doğrulama kodunu hemen gönder.",
                "safety_confirmed": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            AccountRiskEvent.objects.filter(
                subject_user=self.second_owner,
                event_type=AccountRiskEvent.EventType.MESSAGE,
            ).exists()
        )
