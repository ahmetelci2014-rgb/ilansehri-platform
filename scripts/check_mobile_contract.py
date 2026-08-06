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
    if version != "v1.16.0":
        fail(f"VERSION v1.16.0 olmalı, bulundu: {version}")

    base = (ROOT / "templates/base.html").read_text(encoding="utf-8")
    views = (ROOT / "apps/core/views.py").read_text(encoding="utf-8")
    css = (ROOT / "static/css/v132-mobile-system.css").read_text(encoding="utf-8")
    js = (ROOT / "static/js/v132-mobile-system.js").read_text(encoding="utf-8")
    audit = (ROOT / "scripts/mobile_audit.py").read_text(encoding="utf-8")
    listing_form = (ROOT / "templates/listings/form.html").read_text(encoding="utf-8")
    listing_detail = (ROOT / "templates/listings/detail.html").read_text(encoding="utf-8")
    pricing = (ROOT / "apps/listings/pricing.py").read_text(encoding="utf-8")
    nearby = (ROOT / "apps/listings/nearby.py").read_text(encoding="utf-8")
    nearby_css = (ROOT / "static/css/v116-nearby.css").read_text(encoding="utf-8")
    nearby_js = (ROOT / "static/js/v116-nearby.js").read_text(encoding="utf-8")
    listing_list = (ROOT / "templates/listings/list.html").read_text(encoding="utf-8")
    listing_views = (ROOT / "apps/listings/views.py").read_text(encoding="utf-8")
    listing_urls = (ROOT / "apps/listings/urls.py").read_text(encoding="utf-8")

    require(base, "css/v132-mobile-system.css", "templates/base.html")
    require(base, "js/v132-mobile-system.js", "templates/base.html")
    require(base, "v1.16.0", "templates/base.html")
    require(views, 'const CACHE = "ilansehri-v1160";', "apps/core/views.py")
    require(views, "/static/css/v132-mobile-system.css", "apps/core/views.py")
    require(base, "css/v14-matching.css", "templates/base.html")
    require(base, "css/v141-price-guide.css", "templates/base.html")
    require(base, "js/v141-price-guide.js", "templates/base.html")
    require(base, "css/v15-message-safety.css", "templates/base.html")
    require(base, "js/v15-message-safety.js", "templates/base.html")
    require(base, "css/v116-nearby.css", "templates/base.html")
    require(base, "js/v116-nearby.js", "templates/base.html")
    require(views, "/static/css/v14-matching.css", "apps/core/views.py")
    require(views, "/static/css/v141-price-guide.css", "apps/core/views.py")
    require(views, "/static/js/v141-price-guide.js", "apps/core/views.py")
    require(views, "/static/css/v15-message-safety.css", "apps/core/views.py")
    require(views, "/static/js/v15-message-safety.js", "apps/core/views.py")
    require(views, "/static/css/v116-nearby.css", "apps/core/views.py")
    require(views, "/static/js/v116-nearby.js", "apps/core/views.py")
    require(views, "/static/js/v132-mobile-system.js", "apps/core/views.py")
    require(views, '"version": "1.16.0"', "apps/core/views.py")
    require(listing_form, "data-price-guide-assistant", "templates/listings/form.html")
    require(listing_detail, "listings/_price_guide.html", "templates/listings/detail.html")
    require(pricing, "def build_price_guide", "apps/listings/pricing.py")
    require(pricing, "_remove_outliers", "apps/listings/pricing.py")
    require(nearby, "def haversine_km", "apps/listings/nearby.py")
    require(nearby, "def bounding_box", "apps/listings/nearby.py")
    require(nearby, "def sort_nearby_listings", "apps/listings/nearby.py")
    require(nearby_css, ".v116-nearby-panel", "static/css/v116-nearby.css")
    require(nearby_js, "navigator.geolocation", "static/js/v116-nearby.js")
    require(listing_form, "data-listing-location-capture", "templates/listings/form.html")
    require(listing_list, "data-nearby-discovery", "templates/listings/list.html")
    require(listing_list, "data-nearby-session-form", "templates/listings/list.html")
    require(listing_views, "def set_nearby_location", "apps/listings/views.py")
    require(listing_views, 'request.session["nearby_origin"]', "apps/listings/views.py")
    require(listing_urls, 'path("yakindaki/konum/", set_nearby_location', "apps/listings/urls.py")

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
    require(js, "data-mobile-overflow", "static/js/v132-mobile-system.js")
    require(audit, "VIEWPORTS", "scripts/mobile_audit.py")
    require(audit, "ROLE_ROUTES", "scripts/mobile_audit.py")

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

    print("Mobil sözleşme kontrolü başarılı: v1.16.0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"MOBİL SÖZLEŞME HATASI: {exc}", file=sys.stderr)
        raise SystemExit(1)
