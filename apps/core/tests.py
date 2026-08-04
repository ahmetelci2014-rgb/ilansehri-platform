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


class PublicDiscoveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="seo-owner", password="StrongPass_2026")
        category = Category.objects.create(name="SEO Telefon", slug="seo-telefon")
        self.listing = Listing.objects.create(
            owner=self.user, category=category, kind=Listing.Kind.PRODUCT, action=Listing.Action.SELL,
            title="SEO uyumlu örnek telefon ilanı", description="Ayrıntılı ve güvenilir örnek ilan açıklaması.",
            city="Şanlıurfa", district="Karaköprü", status=Listing.Status.PUBLISHED,
        )

    def test_robots_and_sitemap_are_public(self):
        robots = self.client.get(reverse("core:robots"))
        self.assertEqual(robots.status_code, 200)
        self.assertContains(robots, "Sitemap:")
        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        self.assertContains(sitemap, self.listing.get_absolute_url())

    def test_listing_detail_has_structured_metadata(self):
        response = self.client.get(self.listing.get_absolute_url())
        self.assertContains(response, 'application/ld+json')
        self.assertContains(response, 'property="og:type" content="product"')
        self.assertContains(response, "İLAN BİLGİ KALİTESİ")
