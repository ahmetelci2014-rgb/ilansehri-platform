#!/usr/bin/env python3
"""Hafif ve bağımlılıksız mobil sözleşme kontrolü.

GitHub ana test akışında Playwright kurmadan çalışır. Mobil varlıkların yüklenmesini,
cache sürümünü, kritik sayfa gruplarının CSS kapsamını ve denetim aracının temel
sözdizimini doğrular.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise AssertionError(message)


def require(text: str, needle: str, source: str) -> None:
    if needle not in text:
        fail(f"{source}: gerekli içerik bulunamadı: {needle}")


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:\.\d+)?", version):
        fail(f"VERSION biçimi geçersiz: {version}")
    release_number = version.removeprefix("v")
    cache_version = "".join(character for character in release_number if character.isdigit())

    base = (ROOT / "templates/base.html").read_text(encoding="utf-8")
    views = (ROOT / "apps/core/views.py").read_text(encoding="utf-8")
    css = (ROOT / "static/css/v132-mobile-system.css").read_text(encoding="utf-8")
    js = (ROOT / "static/js/v132-mobile-system.js").read_text(encoding="utf-8")
    audit = (ROOT / "scripts/mobile_audit.py").read_text(encoding="utf-8")
    listing_form = (ROOT / "templates/listings/form.html").read_text(encoding="utf-8")
    listing_detail = (ROOT / "templates/listings/detail.html").read_text(encoding="utf-8")
    pricing = (ROOT / "apps/listings/pricing.py").read_text(encoding="utf-8")
    search_alerts = (ROOT / "apps/listings/search_alerts.py").read_text(encoding="utf-8")
    saved_searches = (ROOT / "templates/listings/saved_searches.html").read_text(encoding="utf-8")
    location_js = (ROOT / "static/js/v116-location-discovery.js").read_text(encoding="utf-8")
    maintenance_script = (ROOT / "scripts/run_daily_maintenance.sh").read_text(encoding="utf-8")
    transaction_template = (ROOT / "templates/listings/transaction_detail.html").read_text(encoding="utf-8")
    login_template = (ROOT / "templates/registration/login.html").read_text(encoding="utf-8")
    transaction_services = (ROOT / "apps/listings/services.py").read_text(encoding="utf-8")
    transaction_css = (ROOT / "static/css/v119-transactions.css").read_text(encoding="utf-8")
    appointment_template = (ROOT / "templates/listings/appointment_list.html").read_text(encoding="utf-8")
    appointment_css = (ROOT / "static/css/v120-appointments.css").read_text(encoding="utf-8")
    discovery_css = (ROOT / "static/css/v121-discovery.css").read_text(encoding="utf-8")
    discovery_js = (ROOT / "static/js/v121-discovery.js").read_text(encoding="utf-8")
    polish_css = (ROOT / "static/css/v122-market-polish.css").read_text(encoding="utf-8")
    polish_js = (ROOT / "static/js/v122-market-polish.js").read_text(encoding="utf-8")
    detail_css = (ROOT / "static/css/v123-detail-experience.css").read_text(encoding="utf-8")
    detail_js = (ROOT / "static/js/v123-detail-experience.js").read_text(encoding="utf-8")
    home_template = (ROOT / "templates/core/home.html").read_text(encoding="utf-8")
    listing_card = (ROOT / "templates/listings/_card.html").read_text(encoding="utf-8")
    listing_catalog = (ROOT / "apps/listings/catalog.py").read_text(encoding="utf-8")
    listing_list = (ROOT / "templates/listings/list.html").read_text(encoding="utf-8")
    mobile_workflow = (ROOT / ".github/workflows/mobile-audit.yml").read_text(encoding="utf-8")

    require(base, "css/v132-mobile-system.css", "templates/base.html")
    require(base, "js/v132-mobile-system.js", "templates/base.html")
    require(base, version, "templates/base.html")
    require(base, "v118-trust-safety.css", "templates/base.html")
    require(base, "v119-transactions.css", "templates/base.html")
    require(base, "v120-appointments.css", "templates/base.html")
    require(base, "v121-discovery.css", "templates/base.html")
    require(base, "v121-discovery.js", "templates/base.html")
    require(base, "v122-market-polish.css", "templates/base.html")
    require(base, "v122-market-polish.js", "templates/base.html")
    require(base, "v123-detail-experience.css", "templates/base.html")
    require(base, "v123-detail-experience.js", "templates/base.html")
    require(views, "RELEASE_CACHE", "apps/core/views.py")
    require(views, 'const CACHE = "ilansehri-v__CACHE__";', "apps/core/views.py")
    require(views, '.replace("__CACHE__", RELEASE_CACHE)', "apps/core/views.py")
    require(views, "/static/css/v132-mobile-system.css", "apps/core/views.py")
    require(base, "css/v14-matching.css", "templates/base.html")
    require(base, "css/v141-price-guide.css", "templates/base.html")
    require(base, "js/v141-price-guide.js", "templates/base.html")
    require(base, "css/v15-message-safety.css", "templates/base.html")
    require(base, "js/v15-message-safety.js", "templates/base.html")
    require(base, "css/v117-search-alerts.css", "templates/base.html")
    require(base, "js/v116-location-discovery.js", "templates/base.html")
    require(views, "/static/css/v14-matching.css", "apps/core/views.py")
    require(views, "/static/css/v141-price-guide.css", "apps/core/views.py")
    require(views, "/static/js/v141-price-guide.js", "apps/core/views.py")
    require(views, "/static/css/v15-message-safety.css", "apps/core/views.py")
    require(views, "/static/js/v15-message-safety.js", "apps/core/views.py")
    require(views, "/static/css/v117-search-alerts.css", "apps/core/views.py")
    require(views, "/static/css/v118-trust-safety.css", "apps/core/views.py")
    require(views, "/static/css/v119-transactions.css", "apps/core/views.py")
    require(views, "/static/css/v120-appointments.css", "apps/core/views.py")
    require(views, "/static/css/v121-discovery.css", "apps/core/views.py")
    require(views, "/static/js/v121-discovery.js", "apps/core/views.py")
    require(views, "/static/css/v122-market-polish.css", "apps/core/views.py")
    require(views, "/static/js/v122-market-polish.js", "apps/core/views.py")
    require(views, "/static/css/v123-detail-experience.css", "apps/core/views.py")
    require(views, "/static/js/v123-detail-experience.js", "apps/core/views.py")
    require(views, "/static/js/v116-location-discovery.js", "apps/core/views.py")
    require(views, "/static/js/v132-mobile-system.js", "apps/core/views.py")
    require(views, '"version": RELEASE_VERSION', "apps/core/views.py")
    require(listing_form, "data-price-guide-assistant", "templates/listings/form.html")
    require(listing_form, "data-listing-location-capture", "templates/listings/form.html")
    require(location_js, "data-listing-latitude", "static/js/v116-location-discovery.js")
    require(saved_searches, 'name="alert_frequency"', "templates/listings/saved_searches.html")
    require(search_alerts, "def apply_listing_filters", "apps/listings/search_alerts.py")
    require(search_alerts, "def saved_search_result_params", "apps/listings/search_alerts.py")
    require(maintenance_script, "marketplace_maintenance", "scripts/run_daily_maintenance.sh")
    require(transaction_template, "generate_code", "templates/listings/transaction_detail.html")
    require(transaction_template, "verify_code", "templates/listings/transaction_detail.html")
    require(transaction_template, "KÖR DEĞERLENDİRME", "templates/listings/transaction_detail.html")
    require(transaction_services, "def issue_handover_code", "apps/listings/services.py")
    require(transaction_services, "def publish_due_reviews", "apps/listings/services.py")
    require(transaction_css, ".v119-transaction-page", "static/css/v119-transactions.css")
    require(appointment_template, "GÜVENLİ GÖRÜŞME PLANI", "templates/listings/appointment_list.html")
    require(appointment_css, ".v120-appointment-page", "static/css/v120-appointments.css")
    require(discovery_css, ".v121-filter-sheet", "static/css/v121-discovery.css")
    require(discovery_js, "data-v121-location-form", "static/js/v121-discovery.js")
    require(listing_catalog, "def descendant_category_ids", "apps/listings/catalog.py")
    require(listing_list, "data-v121-category-filter", "templates/listings/list.html")
    require(listing_list, "data-v121-neighborhood", "templates/listings/list.html")
    require(home_template, "data-v122-category-hub", "templates/core/home.html")
    require(home_template, "preferred_district", "templates/core/home.html")
    require(listing_card, "data-market-card", "templates/listings/_card.html")
    require(listing_card, "v122-card-category", "templates/listings/_card.html")
    require(listing_form, "data-v122-wizard-progress", "templates/listings/form.html")
    require(listing_form, "data-v122-review-checklist", "templates/listings/form.html")
    require(polish_css, ".v122-category-hub", "static/css/v122-market-polish.css")
    require(polish_css, ".v122-review-checklist", "static/css/v122-market-polish.css")
    require(polish_js, "data-v122-review-checklist", "static/js/v122-market-polish.js")
    require(listing_detail, "data-v123-gallery", "templates/listings/detail.html")
    require(listing_detail, "data-v123-summary-card", "templates/listings/detail.html")
    require(listing_detail, "data-v123-mobile-contact-bar", "templates/listings/detail.html")
    require(detail_css, ".v123-gallery-lightbox", "static/css/v123-detail-experience.css")
    require(detail_css, ".v123-mobile-contact-bar", "static/css/v123-detail-experience.css")
    require(detail_js, "data-v123-gallery-thumb", "static/js/v123-detail-experience.js")
    require(detail_js, "ArrowRight", "static/js/v123-detail-experience.js")
    require(detail_js, "touchstart", "static/js/v123-detail-experience.js")
    if "continue-on-error: true" in mobile_workflow:
        fail("Mobil Görsel Denetim gerçek hataları gizlememeli")
    require(mobile_workflow, "mobile_audit.py --strict", ".github/workflows/mobile-audit.yml")
    require(mobile_workflow, "manage.py makemigrations", ".github/workflows/mobile-audit.yml")
    require(audit, "or self.console_errors", "scripts/mobile_audit.py")
    require(audit, "or self.page_errors", "scripts/mobile_audit.py")
    require(listing_detail, "listings/_price_guide.html", "templates/listings/detail.html")
    require(pricing, "def build_price_guide", "apps/listings/pricing.py")
    require(pricing, "_remove_outliers", "apps/listings/pricing.py")
    accounts_models = (ROOT / "apps/accounts/models.py").read_text(encoding="utf-8")
    listing_models = (ROOT / "apps/listings/models.py").read_text(encoding="utf-8")
    accounts_urls = (ROOT / "apps/accounts/urls.py").read_text(encoding="utf-8")
    listing_urls = (ROOT / "apps/listings/urls.py").read_text(encoding="utf-8")
    trust_module = (ROOT / "apps/accounts/trust.py").read_text(encoding="utf-8")
    safety_module = (ROOT / "apps/listings/safety.py").read_text(encoding="utf-8")
    require(accounts_models, "class UserReport", "apps/accounts/models.py")
    require(accounts_models, "class AccountRiskEvent", "apps/accounts/models.py")
    require(listing_models, "fingerprint = models.CharField", "apps/listings/models.py")
    require(listing_models, "class Appointment", "apps/listings/models.py")
    require(accounts_urls, 'name="report_user"', "apps/accounts/urls.py")
    require(listing_urls, 'name="moderate_risk_event"', "apps/listings/urls.py")
    require(listing_urls, 'name="appointment_list"', "apps/listings/urls.py")
    require(trust_module, "def build_trust_profile", "apps/accounts/trust.py")
    require(safety_module, "def assess_listing_safety", "apps/listings/safety.py")

    required_css_groups = (
        "body.page-dashboard .v16-account-layout",
        "body.page-conversation_detail .chat-layout",
        "body.page-conversation_list .conversation-list",
        "body.page-create .v16-listing-wizard",
        "body.page-notifications .notification-hero",
        "body.page-offer_center .offer-summary-grid",
        "body.page-ticket_list .support-ticket-row",
        "body.page-staff_board .support-staff-row",
        "body.page-staff_dashboard .staff-grid-main",
        "body.app-managed_services .operation-summary",
        "body.page-task_list .task-grid",
        "body.marketplace-body .legal-page",
        "body.marketplace-body .auth-section",
        "body.page-compare .compare-scroll",
    )
    for selector in required_css_groups:
        require(css, selector, "static/css/v132-mobile-system.css")

    require(js, "window.__ILANSEHRI_MOBILE_AUDIT__", "static/js/v132-mobile-system.js")
    require(js, f'version: "{version}"', "static/js/v132-mobile-system.js sürümü")
    require(js, "data-mobile-overflow", "static/js/v132-mobile-system.js")
    require(audit, "VIEWPORTS", "scripts/mobile_audit.py")
    require(audit, "ROLE_ROUTES", "scripts/mobile_audit.py")
    require(login_template, "data-mobile-audit-login", "templates/registration/login.html")
    require(audit, 'page.locator("form[data-mobile-audit-login]")', "scripts/mobile_audit.py")
    require(audit, "expected_result_count", "scripts/mobile_audit.py")
    if "page.locator('button[type=\"submit\"], input[type=\"submit\"]').first.click()" in audit:
        fail("Mobil denetim giriş formu dışındaki gizli submit düğmesine tıklamamalı")

    # Kullanıcıya gösterilen HTML sayfalarının çoğu ortak mobil kabuğu kullanmalı.
    excluded = {
        Path("templates/base.html"),
        Path("templates/registration/password_reset_email.html"),
        Path("templates/registration/password_reset_subject.txt"),
        Path("templates/admin/ai_listing/aisettings/change_form.html"),
        Path("templates/listings/_card.html"),
        Path("templates/listings/_price_guide.html"),
        Path("templates/listings/_message_form_fields.html"),
    }
    missing_extends: list[str] = []
    for template in sorted((ROOT / "templates").rglob("*.html")):
        relative = template.relative_to(ROOT)
        if relative in excluded:
            continue
        text = template.read_text(encoding="utf-8")
        if "{% extends 'base.html' %}" not in text and '{% extends "base.html" %}' not in text:
            missing_extends.append(str(relative))
    if missing_extends:
        fail("Ortak mobil kabuğu kullanmayan şablonlar: " + ", ".join(missing_extends))

    # Sabit piksel genişlikli inline stiller mobil taşmaya yol açmamalı.
    inline_width = re.compile(r'style="[^"]*\bwidth\s*:\s*([4-9]\d{2,}|\d{4,})px', re.I)
    offenders: list[str] = []
    for template in sorted((ROOT / "templates").rglob("*.html")):
        text = template.read_text(encoding="utf-8")
        if inline_width.search(text):
            offenders.append(str(template.relative_to(ROOT)))
    if offenders:
        fail("Mobil taşma riski taşıyan inline genişlikler: " + ", ".join(offenders))

    print(f"Mobil sözleşme kontrolü başarılı: {version}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"MOBİL SÖZLEŞME HATASI: {exc}", file=sys.stderr)
        raise SystemExit(1)
