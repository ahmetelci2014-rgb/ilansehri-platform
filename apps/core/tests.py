from django.conf import settings
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
        self.assertContains(robots, "Disallow: /ilanlar/ilanlarim/")
        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        self.assertContains(sitemap, self.listing.get_absolute_url())

    def test_listing_detail_has_structured_metadata(self):
        response = self.client.get(self.listing.get_absolute_url())
        self.assertContains(response, 'application/ld+json')
        self.assertContains(response, 'property="og:type" content="product"')
        self.assertContains(response, "İLAN BİLGİ KALİTESİ")


class MobileMarketplaceExperienceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="mobile-owner", password="StrongPass_2026")
        self.category = Category.objects.create(name="Mobil Telefon", slug="mobil-telefon-v113")
        self.listing = Listing.objects.create(
            owner=self.owner,
            category=self.category,
            kind=Listing.Kind.PRODUCT,
            action=Listing.Action.SELL,
            title="Mobil görünüm test ilanı",
            description="Mobil ilan kartı ve detay fiyat özeti için örnek açıklama.",
            price=12500,
            city="Şanlıurfa",
            district="Karaköprü",
            status=Listing.Status.PUBLISHED,
        )

    def test_home_loads_mobile_market_assets_and_search(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "css/v113-mobile-market.css")
        self.assertContains(response, "js/v113-mobile-market.js")
        self.assertContains(response, "css/v132-mobile-system.css")
        self.assertContains(response, "js/v132-mobile-system.js")
        self.assertContains(response, "css/v121-discovery.css")
        self.assertContains(response, "js/v121-discovery.js")
        self.assertContains(response, "css/v122-market-polish.css")
        self.assertContains(response, "js/v122-market-polish.js")
        self.assertContains(response, "css/v123-detail-experience.css")
        self.assertContains(response, "js/v123-detail-experience.js")
        self.assertContains(response, "data-v122-category-hub")
        self.assertContains(response, "aktif şehir")
        self.assertContains(response, "css/v14-matching.css")
        self.assertContains(response, "css/v141-price-guide.css")
        self.assertContains(response, "js/v141-price-guide.js")
        self.assertContains(response, "css/v15-message-safety.css")
        self.assertContains(response, "js/v15-message-safety.js")
        self.assertContains(response, "data-mobile-market-search")
        self.assertContains(response, "page-home")

    def test_listing_detail_contains_mobile_price_summary(self):
        response = self.client.get(self.listing.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "v113-mobile-price-summary")
        self.assertContains(response, "v131-mobile-facts")
        self.assertContains(response, "v131-mobile-seller-strip")
        self.assertContains(response, "data-v123-gallery")
        self.assertContains(response, "data-v123-summary-card")
        self.assertContains(response, "data-v123-mobile-contact-bar")
        self.assertContains(response, "12.500 TL")

    def test_listing_list_contains_mobile_quick_filters_and_result_summary(self):
        response = self.client.get(reverse("listings:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "v131-mobile-quick-filters")
        self.assertContains(response, "v131-mobile-result-summary")
        self.assertContains(response, "data-kind-filter")
        self.assertContains(response, "data-v121-category-filter")
        self.assertContains(response, "data-v121-neighborhood")

    def test_service_worker_uses_mobile_release_cache(self):
        response = self.client.get(reverse("core:service_worker"))
        self.assertEqual(response.status_code, 200)
        release_version = (settings.BASE_DIR / "VERSION").read_text(encoding="utf-8").strip().removeprefix("v")
        cache_version = "".join(character for character in release_version if character.isdigit())
        self.assertContains(response, f'const CACHE = "ilansehri-v{cache_version}";')
        self.assertContains(response, "/static/css/v113-mobile-market.css")
        self.assertContains(response, "/static/js/v113-mobile-market.js")
        self.assertContains(response, "/static/css/v132-mobile-system.css")
        self.assertContains(response, "/static/js/v132-mobile-system.js")
        self.assertContains(response, "/static/css/v14-matching.css")
        self.assertContains(response, "/static/css/v141-price-guide.css")
        self.assertContains(response, "/static/js/v141-price-guide.js")
        self.assertContains(response, "/static/css/v15-message-safety.css")
        self.assertContains(response, "/static/js/v15-message-safety.js")
        self.assertContains(response, "/static/css/v120-appointments.css")
        self.assertContains(response, "/static/css/v121-discovery.css")
        self.assertContains(response, "/static/js/v121-discovery.js")
        self.assertContains(response, "/static/css/v122-market-polish.css")
        self.assertContains(response, "/static/js/v122-market-polish.js")
        self.assertContains(response, "/static/css/v123-detail-experience.css")
        self.assertContains(response, "/static/js/v123-detail-experience.js")
        self.assertContains(response, "/static/css/v124-seller-center.css")
        self.assertContains(response, "/static/js/v124-seller-center.js")
        self.assertContains(response, '"/ilanlar/ilanlarim/"')


class MobileSystemContractTests(TestCase):
    def test_health_and_shell_report_mobile_system_release(self):
        health = self.client.get(reverse("core:health"))
        self.assertEqual(health.status_code, 200)
        expected_version = (settings.BASE_DIR / "VERSION").read_text(encoding="utf-8").strip().removeprefix("v")
        self.assertEqual(health.json()["version"], expected_version)

        shell = self.client.get(reverse("support_center:help_center"))
        self.assertEqual(shell.status_code, 200)
        self.assertContains(shell, "css/v132-mobile-system.css")
        self.assertContains(shell, "js/v132-mobile-system.js")
        self.assertContains(shell, "app-support_center")
        self.assertContains(shell, "page-help_center")

    def test_authenticated_account_page_uses_shared_mobile_shell(self):
        user = User.objects.create_user(username="mobile-shell-user", password="StrongPass_2026")
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "css/v132-mobile-system.css")
        self.assertContains(response, "page-dashboard")
