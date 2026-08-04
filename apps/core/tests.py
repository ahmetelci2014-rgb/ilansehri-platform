from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.listings.models import Category, Listing


class StaffDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="normal", password="StrongPass_2026")
        self.staff = User.objects.create_user(username="staffcore", password="StrongPass_2026", is_staff=True)
        category = Category.objects.create(name="Telefon", slug="telefon-core")
        Listing.objects.create(
            owner=self.user,
            category=category,
            kind=Listing.Kind.PRODUCT,
            action=Listing.Action.SELL,
            title="İnceleme bekleyen telefon",
            description="Test ilanı",
            city="Şanlıurfa",
            district="Karaköprü",
            status=Listing.Status.REVIEW,
        )

    def test_normal_user_cannot_open_staff_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:staff_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_open_professional_dashboard(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("core:staff_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profesyonel Yönetim Merkezi")
        self.assertContains(response, "İnceleme bekleyen telefon")
