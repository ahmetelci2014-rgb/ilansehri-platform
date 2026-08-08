#!/usr/bin/env python3
"""İlan Şehri tablet + masaüstü responsive görsel denetimi."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, sync_playwright

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from mobile_audit import (  # noqa: E402
    CREDENTIALS,
    PUBLIC_ROUTES as MOBILE_PUBLIC_ROUTES,
    RELEASE_VERSION,
    ROLE_ROUTES as MOBILE_ROLE_ROUTES,
    PageResult,
    inspect_page,
    login,
)


VIEWPORTS = (
    {
        "name": "tablet-900",
        "width": 900,
        "height": 1200,
        "has_touch": True,
    },
    {
        "name": "tablet-1024",
        "width": 1024,
        "height": 1366,
        "has_touch": True,
    },
    {
        "name": "laptop-1280",
        "width": 1280,
        "height": 800,
        "has_touch": False,
    },
    {
        "name": "desktop-1440",
        "width": 1440,
        "height": 900,
        "has_touch": False,
    },
)


PUBLIC_NAMES = {
    "home",
    "listings",
    "location-filter",
    "category-filter",
    "product-category",
    "vehicle-category",
    "real-estate-category",
    "listing-detail",
    "compare",
    "login",
    "signup",
    "help",
}

ROLE_NAMES = {
    "buyer": {
        "account",
        "profile",
        "settings",
        "verification",
        "favorites",
        "saved-searches",
        "messages",
        "conversation-detail",
        "notifications",
        "offers",
        "secure-transaction",
        "matches",
    },
    "seller": {
        "account",
        "my-listings",
        "my-listings-attention",
        "new-listing",
        "drafts",
        "messages",
        "conversation-detail",
        "offers",
        "managed",
        "edit-listing",
    },
    "partner": {
        "partner-dashboard",
        "tasks",
    },
    "admin": {
        "staff-dashboard",
        "moderation",
        "support-staff",
        "managed-staff",
    },
}


def select_routes(
    routes: tuple[tuple[str, str], ...],
    wanted: set[str],
    source: str,
) -> tuple[tuple[str, str], ...]:
    available = {name for name, _path in routes}
    missing = wanted - available
    if missing:
        raise RuntimeError(
            f"{source}: responsive denetimde istenen rota bulunamadı: "
            + ", ".join(sorted(missing))
        )
    return tuple((name, path) for name, path in routes if name in wanted)


PUBLIC_ROUTES = select_routes(
    MOBILE_PUBLIC_ROUTES,
    PUBLIC_NAMES,
    "PUBLIC_ROUTES",
)

ROLE_ROUTES = {
    role: select_routes(
        MOBILE_ROLE_ROUTES[role],
        names,
        f"ROLE_ROUTES[{role}]",
    )
    for role, names in ROLE_NAMES.items()
}


def inspect_responsive_page(
    page: Page,
    base_url: str,
    output_dir: Path,
    role: str,
    viewport_name: str,
    name: str,
    path: str,
) -> PageResult:
    result = inspect_page(
        page,
        base_url,
        output_dir,
        role,
        viewport_name,
        name,
        path,
    )

    if result.error or result.status is None or result.status >= 400:
        return result

    try:
        layout: dict[str, Any] = page.evaluate(
            """
            () => {
              const inspect = (selector) => {
                const element = document.querySelector(selector);
                if (!element) return null;

                const style = getComputedStyle(element);
                const rect = element.getBoundingClientRect();

                if (
                  style.display === "none" ||
                  style.visibility === "hidden" ||
                  rect.width <= 0 ||
                  rect.height <= 0
                ) {
                  return null;
                }

                const overflow = Math.max(
                  0,
                  Math.ceil(element.scrollWidth - element.clientWidth)
                );

                return {
                  selector,
                  overflow,
                  width: Math.round(rect.width),
                  scrollWidth: element.scrollWidth
                };
              };

              return {
                header: inspect(".market-header-row"),
                main: inspect("main#main-content")
              };
            }
            """
        )

        for key in ("header", "main"):
            item = layout.get(key)
            if not item:
                continue

            overflow = int(item.get("overflow", 0))
            if overflow > 2:
                result.horizontal_overflow = max(
                    result.horizontal_overflow,
                    overflow,
                )
                result.overflow_elements.append(item)

    except Exception as exc:  # noqa: BLE001
        result.page_errors.append(
            f"Responsive layout kontrolü: {type(exc).__name__}: {exc}"[:500]
        )

    return result


def new_context(browser: Browser, viewport: dict[str, Any]):
    return browser.new_context(
        viewport={
            "width": viewport["width"],
            "height": viewport["height"],
        },
        device_scale_factor=1,
        locale="tr-TR",
        timezone_id="Europe/Istanbul",
        is_mobile=False,
        has_touch=viewport["has_touch"],
    )


def run_audit(
    base_url: str,
    output_dir: Path,
) -> list[PageResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[PageResult] = []

    with sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(headless=True)

        for viewport in VIEWPORTS:
            public_context = new_context(browser, viewport)
            public_page = public_context.new_page()

            for name, path in PUBLIC_ROUTES:
                results.append(
                    inspect_responsive_page(
                        public_page,
                        base_url,
                        output_dir,
                        "public",
                        viewport["name"],
                        name,
                        path,
                    )
                )

            public_context.close()

            for role, routes in ROLE_ROUTES.items():
                context = new_context(browser, viewport)
                page = context.new_page()

                username, password = CREDENTIALS[role]

                try:
                    login(
                        page,
                        base_url,
                        username,
                        password,
                    )

                    for name, path in routes:
                        results.append(
                            inspect_responsive_page(
                                page,
                                base_url,
                                output_dir,
                                role,
                                viewport["name"],
                                name,
                                path,
                            )
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
    per_viewport = len(PUBLIC_ROUTES) + sum(
        len(routes)
        for routes in ROLE_ROUTES.values()
    )
    return len(VIEWPORTS) * per_viewport


def write_report(
    output_dir: Path,
    results: list[PageResult],
) -> None:
    expected_pages = expected_result_count()

    payload = {
        "version": RELEASE_VERSION,
        "audit": "tablet-desktop-responsive",
        "viewports": VIEWPORTS,
        "summary": {
            "pages": len(results),
            "expected_pages": expected_pages,
            "coverage_complete": len(results) == expected_pages,
            "critical": sum(result.critical for result in results),
            "overflow_pages": sum(
                result.horizontal_overflow > 2
                for result in results
            ),
            "console_error_pages": sum(
                bool(result.console_errors or result.page_errors)
                for result in results
            ),
        },
        "results": [
            asdict(result) | {"critical": result.critical}
            for result in results
        ],
    }

    (output_dir / "responsive-audit.json").write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    rows = [
        "# İlan Şehri Tablet + Masaüstü Görsel Denetim",
        "",
        f"- Sürüm: {RELEASE_VERSION}",
        (
            "- Sayfa/ekran kombinasyonu: "
            f"{payload['summary']['pages']} / "
            f"{payload['summary']['expected_pages']}"
        ),
        (
            "- Kapsam tamamlandı: "
            + (
                "Evet"
                if payload["summary"]["coverage_complete"]
                else "Hayır"
            )
        ),
        f"- Kritik sonuç: {payload['summary']['critical']}",
        f"- Taşma görülen: {payload['summary']['overflow_pages']}",
        (
            "- Tarayıcı hatası görülen: "
            f"{payload['summary']['console_error_pages']}"
        ),
        "",
        "| Rol | Ekran | Sayfa | HTTP | Taşma | Küçük hedef | Sonuç |",
        "|---|---|---|---:|---:|---:|---|",
    ]

    for result in results:
        status = (
            result.status
            if result.status is not None
            else "—"
        )
        outcome = "❌" if result.critical else "✅"

        rows.append(
            f"| {result.role} | "
            f"{result.viewport} | "
            f"{result.name} | "
            f"{status} | "
            f"{result.horizontal_overflow}px | "
            f"{result.small_targets} | "
            f"{outcome} |"
        )

    (output_dir / "responsive-audit.md").write_text(
        "\n".join(rows) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--output",
        default="responsive-audit-artifacts",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
    )
    args = parser.parse_args()

    output_dir = Path(args.output).resolve()

    results = run_audit(
        args.base_url.rstrip("/") + "/",
        output_dir,
    )

    write_report(
        output_dir,
        results,
    )

    critical = [
        result
        for result in results
        if result.critical
    ]

    expected_pages = expected_result_count()
    coverage_complete = len(results) == expected_pages

    print(
        "Tablet + masaüstü denetimi tamamlandı: "
        f"{len(results)}/{expected_pages} ekran, "
        f"{len(critical)} kritik sonuç."
    )

    if not coverage_complete:
        print(
            "Responsive denetim kapsamı eksik; "
            "rol girişleri veya rota taraması tamamlanamadı."
        )

    print(
        f"Rapor: {output_dir / 'responsive-audit.md'}"
    )

    return (
        1
        if args.strict and (
            critical or not coverage_complete
        )
        else 0
    )


if __name__ == "__main__":
    sys.exit(main())
