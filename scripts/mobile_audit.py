#!/usr/bin/env python3
"""İlan Şehri mobil ekran görüntüsü ve taşma denetimi.

Bu araç Playwright ile gerçek Django sayfalarını 360, 390 ve 430 px genişlikte
gezer. Varsayılan mod rapor üretir; --strict kullanılırsa kritik sayfa veya
yatay taşma hatalarında başarısız döner.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from playwright.sync_api import Browser, Page, sync_playwright


VIEWPORTS = (
    {"name": "android-360", "width": 360, "height": 800},
    {"name": "iphone-390", "width": 390, "height": 844},
    {"name": "large-430", "width": 430, "height": 932},
)

PUBLIC_ROUTES = (
    ("home", "/"),
    ("listings", "/ilanlar/"),
    ("location-filter", "/ilanlar/?city=%C5%9Eanl%C4%B1urfa&district=Karak%C3%B6pr%C3%BC&neighborhood=Akp%C4%B1yar"),
    ("category-filter", "/ilanlar/?kind=product&category=2&sort=newest"),
    ("product-category", "/ilanlar/kategori/product/"),
    ("vehicle-category", "/ilanlar/kategori/vehicle/"),
    ("real-estate-category", "/ilanlar/kategori/real_estate/"),
    ("service-category", "/ilanlar/kategori/service/"),
    ("listing-detail", "/ilanlar/demo-telefon/"),
    ("compare", "/ilanlar/karsilastir/"),
    ("login", "/hesap/login/"),
    ("signup", "/hesap/kayit/"),
    ("help", "/yardim/"),
    ("trust", "/guven-merkezi/"),
)

ROLE_ROUTES = {
    "buyer": (
        ("listing-detail", "/ilanlar/demo-telefon/"),
        ("account", "/hesap/hesabim/"),
        ("profile", "/hesap/profilim/"),
        ("settings", "/hesap/ayarlar/"),
        ("verification", "/hesap/dogrulama/"),
        ("following", "/hesap/takip-ettiklerim/"),
        ("favorites", "/ilanlar/favorilerim/"),
        ("saved-searches", "/ilanlar/aramalarim/"),
        ("messages", "/ilanlar/mesajlar/"),
        ("messages-action", "/ilanlar/mesajlar/?mode=action"),
        ("conversation-detail", "/ilanlar/mesajlar/1/"),
        ("appointments", "/ilanlar/randevularim/"),
        ("notifications", "/ilanlar/bildirimler/"),
        ("offers", "/ilanlar/tekliflerim/"),
        ("secure-transaction", "/ilanlar/islem/11111111-1111-4111-8111-111111111119/"),
        ("matches", "/ilanlar/eslesmelerim/"),
        ("support-tickets", "/yardim/taleplerim/"),
        ("support-create", "/yardim/talep/yeni/"),
    ),
    "seller": (
        ("listing-detail", "/ilanlar/demo-telefon/"),
        ("account", "/hesap/hesabim/"),
        ("my-listings", "/ilanlar/ilanlarim/"),
        ("my-listings-attention", "/ilanlar/ilanlarim/?status=attention"),
        ("new-listing", "/ilanlar/yeni/"),
        ("drafts", "/ilanlar/taslaklarim/"),
        ("messages", "/ilanlar/mesajlar/"),
        ("messages-action", "/ilanlar/mesajlar/?mode=action"),
        ("conversation-detail", "/ilanlar/mesajlar/1/"),
        ("appointments", "/ilanlar/randevularim/"),
        ("offers", "/ilanlar/tekliflerim/"),
        ("secure-transaction", "/ilanlar/islem/11111111-1111-4111-8111-111111111119/"),
        ("matches", "/ilanlar/eslesmelerim/?tab=offered"),
        ("managed", "/tam-yonetim/"),
        ("edit-listing", "/ilanlar/demo-telefon/duzenle/"),
    ),
    "partner": (
        ("partner-dashboard", "/kazanc-agi/panelim/"),
        ("partner-profile", "/kazanc-agi/profil/"),
        ("tasks", "/kazanc-agi/gorevler/"),
    ),
    "admin": (
        ("staff-dashboard", "/yonetim/"),
        ("moderation", "/ilanlar/moderasyon/"),
        ("secure-transaction", "/ilanlar/islem/11111111-1111-4111-8111-111111111119/"),
        ("support-staff", "/yardim/ekip/"),
        ("managed-staff", "/tam-yonetim/operasyon/"),
        ("partner-staff", "/kazanc-agi/ekip/"),
    ),
}

CREDENTIALS = {
    "buyer": ("demo_alici", "Demo1234!"),
    "seller": ("demo_satici", "Demo1234!"),
    "partner": ("demo_partner", "Demo1234!"),
    "admin": ("demo_admin", "DemoAdmin1234!"),
}

ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


@dataclass
class PageResult:
    role: str
    viewport: str
    name: str
    requested_path: str
    final_url: str = ""
    status: int | None = None
    title: str = ""
    horizontal_overflow: int = 0
    overflow_elements: list[dict[str, Any]] = field(default_factory=list)
    small_targets: int = 0
    console_errors: list[str] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    interaction_errors: list[str] = field(default_factory=list)
    screenshot: str = ""
    error: str = ""

    @property
    def critical(self) -> bool:
        return bool(
            self.error
            or self.status is None
            or self.status >= 400
            or self.horizontal_overflow > 2
            or self.console_errors
            or self.page_errors
            or self.interaction_errors
        )


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")


def login(page: Page, base_url: str, username: str, password: str) -> None:
    response = page.goto(
        urljoin(base_url, "/hesap/login/"),
        wait_until="domcontentloaded",
        timeout=30_000,
    )
    if response is None or response.status >= 400:
        status = response.status if response else "yanıt yok"
        raise RuntimeError(f"Giriş sayfası açılamadı: HTTP {status}")

    # Ortak mobil kabukta gizli bir arama formu da submit düğmesi içerir.
    # Giriş öğelerini yalnız görünür auth formu içinde arayarak yanlış düğmeye
    # tıklanmasını ve sahte mobil denetim hatalarını önlüyoruz.
    login_form = page.locator("form[data-mobile-audit-login]").first
    login_form.wait_for(state="visible", timeout=10_000)
    login_form.locator('input[name="username"]').fill(username)
    login_form.locator('input[name="password"]').fill(password)
    submit = login_form.locator('button[type="submit"], input[type="submit"]').first
    submit.wait_for(state="visible", timeout=10_000)
    with page.expect_navigation(wait_until="domcontentloaded", timeout=30_000):
        submit.click()

    if "/hesap/login/" in page.url:
        raise RuntimeError(f"Demo giriş başarısız: {username}")



def run_interaction_checks(page: Page, role: str, name: str) -> list[str]:
    """Kritik mobil kontrolleri gerçekten tıklayarak doğrula."""
    errors: list[str] = []

    def check(label, callback):
        try:
            callback()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{label}: {type(exc).__name__}: {exc}")

    if role == "public" and name == "home":
        def menu_check():
            toggle = page.locator("[data-menu-toggle]").first
            menu = page.locator("[data-mobile-menu]").first

            if toggle.count() == 0 or menu.count() == 0:
                raise AssertionError("Mobil menü öğeleri bulunamadı")

            toggle.click()
            page.wait_for_function(
                "() => document.querySelector('[data-mobile-menu]')?.classList.contains('is-open')",
                timeout=3000,
            )

            if toggle.get_attribute("aria-expanded") != "true":
                raise AssertionError("Menü açıldı ama aria-expanded=true olmadı")

            toggle.click()
            page.wait_for_function(
                "() => !document.querySelector('[data-mobile-menu]')?.classList.contains('is-open')",
                timeout=3000,
            )

        check("hamburger", menu_check)

    if role == "public" and name == "listings":
        def filter_check():
            open_button = page.locator("[data-filter-open]").first
            panel = page.locator("[data-filter-panel]").first
            close_button = page.locator("[data-filter-close]").first

            if (
                open_button.count() == 0
                or panel.count() == 0
                or close_button.count() == 0
            ):
                raise AssertionError("Filtre kontrol öğeleri bulunamadı")

            open_button.click()
            page.wait_for_function(
                "() => document.querySelector('[data-filter-panel]')?.classList.contains('is-open')",
                timeout=3000,
            )

            close_button.click()
            page.wait_for_function(
                "() => !document.querySelector('[data-filter-panel]')?.classList.contains('is-open')",
                timeout=3000,
            )

        check("filtre", filter_check)

    if role == "public" and name == "listing-detail":
        def gallery_check():
            stage = page.locator("[data-v123-gallery-stage]").first
            lightbox = page.locator("[data-v123-lightbox]").first
            main_image = page.locator("[data-v123-main-image]").first

            if stage.count() == 0 or lightbox.count() == 0:
                raise AssertionError("Galeri veya lightbox bulunamadı")

            # Fotoğrafsız demo ilanda açılacak görsel olmadığı için
            # yapısal kontrol yeterlidir.
            if main_image.count() == 0:
                return

            stage.click(position={"x": 60, "y": 60})

            page.wait_for_function(
                "() => document.querySelector('[data-v123-lightbox]')?.hidden === false",
                timeout=3000,
            )

            close_button = page.locator(
                "[data-v123-lightbox] [data-gallery-close]"
            ).first

            if close_button.count() == 0:
                raise AssertionError("Galeri kapatma düğmesi bulunamadı")

            close_button.click()

            page.wait_for_function(
                "() => document.querySelector('[data-v123-lightbox]')?.hidden === true",
                timeout=3000,
            )

        check("galeri", gallery_check)

    if role == "buyer" and name == "listing-detail":
        def detail_actions_check():
            share = page.locator("[data-share-listing]").first
            copy = page.locator("[data-copy-listing]").first

            if share.count() == 0 or copy.count() == 0:
                raise AssertionError("Paylaş/kopyala aksiyonları bulunamadı")

            page.evaluate(
                """
                () => {
                  window.__AUDIT_SHARED__ = null;
                  window.__AUDIT_COPIED__ = null;

                  Object.defineProperty(navigator, "share", {
                    configurable: true,
                    value: async (data) => {
                      window.__AUDIT_SHARED__ = data;
                    }
                  });

                  Object.defineProperty(navigator, "clipboard", {
                    configurable: true,
                    value: {
                      writeText: async (value) => {
                        window.__AUDIT_COPIED__ = value;
                      }
                    }
                  });
                }
                """
            )

            share.click()
            page.wait_for_function(
                "() => window.__AUDIT_SHARED__?.url",
                timeout=3000,
            )

            # Mobil tasarımda ayrı "Bağlantıyı kopyala" düğmesi
            # bazı genişliklerde bilinçli olarak gizlidir.
            # DOM sözleşmesini doğrula; yalnız görünürse gerçek tıklama yap.
            if not copy.get_attribute("data-copy-url"):
                raise AssertionError("Kopyalama bağlantısı eksik")

            if copy.is_visible():
                copy.click()
                page.wait_for_function(
                    """() =>
                      window.__AUDIT_COPIED__
                      && document.querySelector("[data-copy-toast]")?.hidden === false
                    """,
                    timeout=3000,
                )

            message_box = page.locator("[data-v123-message-box]").first
            if message_box.count() == 0:
                raise AssertionError("Mesaj kutusu bulunamadı")

            message_trigger = page.locator("[data-open-message]:visible").first
            if message_trigger.count():
                message_trigger.click()
            else:
                message_box.locator("summary").first.click()

            page.wait_for_function(
                "() => document.querySelector('[data-v123-message-box]')?.open === true",
                timeout=3000,
            )

            page.evaluate(
                "() => document.querySelector('[data-v123-message-box]').open = false"
            )

            offer_box = page.locator("[data-v123-offer-box]").first
            if offer_box.count():
                offer_trigger = page.locator("[data-open-offer]:visible").first

                if offer_trigger.count():
                    offer_trigger.click()
                else:
                    offer_box.locator("summary").first.click()

                page.wait_for_function(
                    "() => document.querySelector('[data-v123-offer-box]')?.open === true",
                    timeout=3000,
                )
            else:
                pending = page.locator(".pending-offer-card")
                negotiation = page.get_by_text("Pazarlığı aç", exact=True)

                if pending.count() == 0 and negotiation.count() == 0:
                    raise AssertionError("Teklif/pazarlık aksiyonu bulunamadı")

            favorite = page.locator(
                'button[aria-label="Favori durumunu değiştir"]'
            ).first

            if favorite.count() == 0:
                raise AssertionError("Favori düğmesi bulunamadı")

            favorite_action = favorite.evaluate(
                "(button) => button.closest('form')?.action || ''"
            )

            if not favorite_action:
                raise AssertionError("Favori form bağlantısı bulunamadı")

            page.evaluate(
                """
                () => {
                  const button = document.querySelector(
                    'button[aria-label="Favori durumunu değiştir"]'
                  );
                  const form = button?.closest("form");

                  window.__AUDIT_FAVORITE_SUBMIT__ = false;

                  form?.addEventListener(
                    "submit",
                    (event) => {
                      event.preventDefault();
                      window.__AUDIT_FAVORITE_SUBMIT__ = true;
                    },
                    {once: true}
                  );
                }
                """
            )

            favorite.click()

            page.wait_for_function(
                "() => window.__AUDIT_FAVORITE_SUBMIT__ === true",
                timeout=3000,
            )

        check("detay-aksiyonlari", detail_actions_check)

    if role == "seller" and name == "new-listing":
        def wizard_gps_check():
            manual = page.locator("[data-ai-manual-start]").first
            if manual.count() and manual.is_visible():
                manual.click()
                page.wait_for_timeout(150)

            def choose_first(selector, preferred=None):
                field = page.locator(selector).first
                if field.count() == 0:
                    return
                value = field.evaluate(
                    """(el, preferred) => {
                        const options = Array.from(el.options || []);
                        const preferredOption = options.find(
                            o => o.value === preferred && !o.disabled && !o.hidden
                        );
                        const first = preferredOption || options.find(
                            o => o.value && !o.disabled && !o.hidden
                        );
                        return first?.value || "";
                    }""",
                    preferred,
                )
                if value:
                    field.select_option(value)

            choose_first('[name="kind"]', "product")
            page.wait_for_timeout(150)
            choose_first('[name="action"]', "sell")
            choose_first('[name="category"]')
            choose_first('[name="management_mode"]')

            next_button = page.locator("[data-v16-next]").first
            if next_button.count() == 0:
                raise AssertionError("Sihirbaz Devam et düğmesi bulunamadı")

            next_button.click()

            page.wait_for_function(
                "() => document.querySelector('[data-v16-section=\"2\"]')?.classList.contains('active')",
                timeout=3000,
            )

            required = page.locator(
                '[data-v16-section="2"].active input[required], '
                '[data-v16-section="2"].active textarea[required], '
                '[data-v16-section="2"].active select[required]'
            )

            for index in range(required.count()):
                field = required.nth(index)
                if not field.is_visible() or not field.is_enabled():
                    continue

                tag = field.evaluate("(el) => el.tagName")
                field_type = (field.get_attribute("type") or "").lower()
                name_attr = field.get_attribute("name") or ""

                if tag == "SELECT":
                    if not field.input_value():
                        value = field.evaluate(
                            """el => Array.from(el.options)
                                .find(o => o.value && !o.disabled && !o.hidden)?.value || """""
                        )
                        if value:
                            field.select_option(value)
                elif field_type == "checkbox":
                    field.check()
                elif not field.input_value():
                    if field_type == "number" or name_attr == "price":
                        field.fill("1000")
                    elif tag == "TEXTAREA" or name_attr == "description":
                        field.fill(
                            "Mobil audit için yeterli uzunlukta güvenli test açıklaması."
                        )
                    elif name_attr == "title":
                        field.fill("Mobil audit test ilanı")
                    else:
                        field.fill("Mobil audit")

            step_four = page.locator('[data-v16-step="4"]').first
            if step_four.count() == 0:
                raise AssertionError("Konum adımı bulunamadı")

            step_four.click()

            page.wait_for_function(
                "() => document.querySelector('[data-v16-section=\"4\"]')?.classList.contains('active')",
                timeout=3000,
            )

            page.evaluate(
                """
                () => {
                  const capture = document.querySelector(
                    '[data-listing-location-capture]'
                  );
                  const reverseUrl = capture?.dataset.reverseUrl || '';

                  if (!window.__ILANSEHRI_AUDIT_ORIGINAL_FETCH__) {
                    window.__ILANSEHRI_AUDIT_ORIGINAL_FETCH__ =
                      window.fetch.bind(window);
                  }

                  const originalFetch =
                    window.__ILANSEHRI_AUDIT_ORIGINAL_FETCH__;

                  window.fetch = async (input, init) => {
                    const url =
                      typeof input === 'string'
                        ? input
                        : (input?.url || String(input));

                    if (reverseUrl && url.includes(reverseUrl)) {
                      return new Response(
                        JSON.stringify({
                          city: 'Şanlıurfa',
                          district: 'Karaköprü',
                          neighborhood: 'Akpıyar',
                          attribution: 'Mobil audit'
                        }),
                        {
                          status: 200,
                          headers: {'Content-Type': 'application/json'}
                        }
                      );
                    }

                    return originalFetch(input, init);
                  };

                  Object.defineProperty(
                    navigator,
                    'geolocation',
                    {
                      configurable: true,
                      value: {
                        getCurrentPosition(success) {
                          success({
                            coords: {
                              latitude: 37.1674,
                              longitude: 38.7955
                            }
                          });
                        }
                      }
                    }
                  );
                }
                """
            )

            capture = page.locator("[data-listing-location-capture]").first
            if capture.count() == 0:
                raise AssertionError("Konumumu bul düğmesi bulunamadı")

            capture.click()

            page.wait_for_function(
                """() => {
                  const city =
                    document.querySelector('[data-location-city]')?.value;
                  const district =
                    document.querySelector('[data-location-district]')?.value;
                  const neighborhood =
                    document.querySelector('[data-location-neighborhood]')?.value;
                  const button =
                    document.querySelector('[data-listing-location-capture]');

                  return city === 'Şanlıurfa'
                    && district === 'Karaköprü'
                    && neighborhood === 'Akpıyar'
                    && button?.classList.contains('is-captured');
                }""",
                timeout=5000,
            )

            coordinates = page.evaluate(
                """() => ({
                  lat: document.querySelector(
                    '[data-listing-latitude]'
                  )?.value,
                  lng: document.querySelector(
                    '[data-listing-longitude]'
                  )?.value
                })"""
            )

            if coordinates["lat"] != "37.167":
                raise AssertionError(
                    f"GPS enlem doldurulmadı: {coordinates['lat']}"
                )
            if coordinates["lng"] != "38.795":
                raise AssertionError(
                    f"GPS boylam doldurulmadı: {coordinates['lng']}"
                )

        check("ilan-sihirbazi-gps", wizard_gps_check)

    return errors


def inspect_page(
    page: Page,
    base_url: str,
    output_dir: Path,
    role: str,
    viewport_name: str,
    name: str,
    path: str,
    *,
    run_interactions: bool = True,
) -> PageResult:
    result = PageResult(role=role, viewport=viewport_name, name=name, requested_path=path)
    console_errors: list[str] = []
    page_errors: list[str] = []

    def on_console(message):
        if message.type == "error":
            console_errors.append(message.text[:500])

    def on_page_error(error):
        page_errors.append(str(error)[:500])

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    try:
        response = page.goto(urljoin(base_url, path), wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(250)
        result.final_url = page.url
        result.status = response.status if response else None
        result.title = page.title()
        metrics = page.evaluate(
            """
            () => {
              const root = document.documentElement;
              const allTargets = [...document.querySelectorAll('a,button,input,select,textarea,summary')]
                .filter((el) => {
                  const s = getComputedStyle(el);
                  const r = el.getBoundingClientRect();
                  return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
                });
              const smallTargets = allTargets.filter((el) => {
                const r = el.getBoundingClientRect();
                return (r.width < 38 || r.height < 38) && !el.closest('.market-card-meta');
              }).length;
              const runtime = window.__ILANSEHRI_MOBILE_AUDIT__ || {overflows: []};
              return {
                overflow: Math.max(0, root.scrollWidth - root.clientWidth),
                overflowElements: runtime.overflows || [],
                smallTargets,
              };
            }
            """
        )
        result.horizontal_overflow = int(metrics["overflow"])
        result.overflow_elements = list(metrics["overflowElements"])[:20]
        result.small_targets = int(metrics["smallTargets"])
        if run_interactions:
            result.interaction_errors = run_interaction_checks(page, role, name)

        filename = f"{slugify(role)}__{slugify(viewport_name)}__{slugify(name)}.png"
        screenshot_path = output_dir / "screenshots" / filename
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_path), full_page=True)
        result.screenshot = str(screenshot_path.relative_to(output_dir))
    except Exception as exc:  # noqa: BLE001 - raporda görmek için tüm tarayıcı hataları yakalanır
        result.error = f"{type(exc).__name__}: {exc}"
    finally:
        result.console_errors = console_errors[:20]
        result.page_errors = page_errors[:20]
        page.remove_listener("console", on_console)
        page.remove_listener("pageerror", on_page_error)
    return result


def run_audit(base_url: str, output_dir: Path) -> list[PageResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[PageResult] = []

    with sync_playwright() as playwright:
        launch_options: dict[str, Any] = {"headless": True}
        chromium_executable = os.getenv("ILANSEHRI_CHROMIUM_EXECUTABLE", "").strip()
        if chromium_executable:
            launch_options["executable_path"] = chromium_executable
        browser: Browser = playwright.chromium.launch(**launch_options)
        for viewport in VIEWPORTS:
            public_context = browser.new_context(
                viewport={"width": viewport["width"], "height": viewport["height"]},
                device_scale_factor=1,
                locale="tr-TR",
                timezone_id="Europe/Istanbul",
                is_mobile=True,
                has_touch=True,
            )
            public_page = public_context.new_page()
            for name, path in PUBLIC_ROUTES:
                results.append(
                    inspect_page(public_page, base_url, output_dir, "public", viewport["name"], name, path)
                )
            public_context.close()

            for role, routes in ROLE_ROUTES.items():
                context = browser.new_context(
                    viewport={"width": viewport["width"], "height": viewport["height"]},
                    device_scale_factor=1,
                    locale="tr-TR",
                    timezone_id="Europe/Istanbul",
                    is_mobile=True,
                    has_touch=True,
                )
                page = context.new_page()
                username, password = CREDENTIALS[role]
                try:
                    login(page, base_url, username, password)
                    for name, path in routes:
                        results.append(
                            inspect_page(page, base_url, output_dir, role, viewport["name"], name, path)
                        )
                except Exception as exc:  # noqa: BLE001
                    results.append(
                        PageResult(
                            role=role,
                            viewport=viewport["name"],
                            name="login",
                            requested_path="/hesap/login/",
                            error=f"{type(exc).__name__}: {exc}",
                        )
                    )
                finally:
                    context.close()
        browser.close()
    return results


def expected_result_count() -> int:
    per_viewport = len(PUBLIC_ROUTES) + sum(len(routes) for routes in ROLE_ROUTES.values())
    return len(VIEWPORTS) * per_viewport


def write_report(output_dir: Path, results: list[PageResult]) -> None:
    expected_pages = expected_result_count()
    payload = {
        "version": RELEASE_VERSION,
        "summary": {
            "pages": len(results),
            "expected_pages": expected_pages,
            "coverage_complete": len(results) == expected_pages,
            "critical": sum(result.critical for result in results),
            "overflow_pages": sum(result.horizontal_overflow > 2 for result in results),
            "console_error_pages": sum(bool(result.console_errors or result.page_errors) for result in results),
            "interaction_error_pages": sum(bool(result.interaction_errors) for result in results),
        },
        "results": [asdict(result) | {"critical": result.critical} for result in results],
    }
    (output_dir / "mobile-audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    rows = [
        "# İlan Şehri Mobil Denetim",
        "",
        f"- Sayfa/ekran kombinasyonu: {payload['summary']['pages']} / {payload['summary']['expected_pages']}",
        f"- Kapsam tamamlandı: {'Evet' if payload['summary']['coverage_complete'] else 'Hayır'}",
        f"- Kritik sonuç: {payload['summary']['critical']}",
        f"- Yatay taşma görülen: {payload['summary']['overflow_pages']}",
        f"- Tarayıcı hatası görülen: {payload['summary']['console_error_pages']}",
        f"- Etkileşim hatası görülen: {payload['summary']['interaction_error_pages']}",
        "",
        "| Rol | Ekran | Sayfa | HTTP | Taşma | Küçük hedef | Sonuç |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for result in results:
        status = result.status if result.status is not None else "—"
        outcome = "❌" if result.critical else "✅"
        rows.append(
            f"| {result.role} | {result.viewport} | {result.name} | {status} | "
            f"{result.horizontal_overflow}px | {result.small_targets} | {outcome} |"
        )
    (output_dir / "mobile-audit.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", default="mobile-audit-artifacts")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output).resolve()
    results = run_audit(args.base_url.rstrip("/") + "/", output_dir)
    write_report(output_dir, results)
    critical = [result for result in results if result.critical]
    expected_pages = expected_result_count()
    coverage_complete = len(results) == expected_pages
    print(
        f"Mobil denetim tamamlandı: {len(results)}/{expected_pages} ekran, "
        f"{len(critical)} kritik sonuç."
    )
    if not coverage_complete:
        print("Mobil denetim kapsamı eksik; rol girişleri veya rota taraması tamamlanamadı.")
    print(f"Rapor: {output_dir / 'mobile-audit.md'}")
    return 1 if args.strict and (critical or not coverage_complete) else 0


if __name__ == "__main__":
    sys.exit(main())
