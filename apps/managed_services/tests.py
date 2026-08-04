from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.listings.models import Category, Listing

from .models import ManagedActivity, ManagedRequest


class ManagedServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="customer", password="StrongPass_2026")
        self.staff = User.objects.create_user(username="staffmanaged", password="StrongPass_2026", is_staff=True)
        category = Category.objects.create(name="Eşya", slug="esya-managed")
        listing = Listing.objects.create(
            owner=self.user, category=category, kind=Listing.Kind.PRODUCT,
            action=Listing.Action.SELL, title="Yönetilen ilan", description="Açıklama",
            condition="İyi", city="Şanlıurfa", district="Karaköprü",
        )
        self.managed = ManagedRequest.objects.create(listing=listing, customer=self.user)

    def test_customer_can_view_and_add_activity(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("managed_services:detail", kwargs={"pk": self.managed.pk}))
        self.assertEqual(response.status_code, 200)
        self.client.post(
            reverse("managed_services:add_activity", kwargs={"pk": self.managed.pk}),
            {"activity_type": ManagedActivity.ActivityType.NOTE, "note": "Müsait olduğum saat 15:00", "visible_to_customer": "on"},
        )
        self.assertTrue(ManagedActivity.objects.filter(managed_request=self.managed, actor=self.user).exists())

    def test_staff_can_update_operation(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("managed_services:staff_update", kwargs={"pk": self.managed.pk}),
            {
                "assigned_staff": self.staff.pk,
                "status": ManagedRequest.Status.ACTIVE,
                "package": ManagedRequest.Package.FULL,
                "progress": 35,
                "next_action": "Fotoğraf çekimi",
            },
        )
        self.assertRedirects(response, reverse("managed_services:detail", kwargs={"pk": self.managed.pk}))
        self.managed.refresh_from_db()
        self.assertEqual(self.managed.progress, 35)
