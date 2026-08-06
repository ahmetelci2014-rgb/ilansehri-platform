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
        ("account", "/hesap/hesabim/"),
        ("profile", "/hesap/profilim/"),
        ("settings", "/hesap/ayarlar/"),
        ("verification", "/hesap/dogrulama/"),
        ("following", "/hesap/takip-ettiklerim/"),
        ("favorites", "/ilanlar/favorilerim/"),
        ("saved-searches", "/ilanlar/aramalarim/"),
        ("messages", "/ilanlar/mesajlar/"),
        ("appointments", "/ilanlar/randevularim/"),
        ("notifications", "/ilanlar/bildirimler/"),
        ("offers", "/ilanlar/tekliflerim/"),
        ("secure-transaction", "/ilanlar/islem/11111111-1111-4111-8111-111111111119/"),
        ("matches", "/ilanlar/eslesmelerim/"),
        ("support-tickets", "/yardim/taleplerim/"),
        ("support-create", "/yardim/talep/yeni/"),
    ),
    "seller": (
        ("account", "/hesap/hesabim/"),
        ("new-listing", "/ilanlar/yeni/"),
        ("drafts", "/ilanlar/taslaklarim/"),
        ("messages", "/ilanlar/mesajlar/"),
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


def inspect_page(
    page: Page,
    base_url: str,
    output_dir: Path,
    role: str,
    viewport_name: str,
    name: str,
    path: str,
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
