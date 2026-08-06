/* İlan Şehri v1.13.2 — site geneli mobil davranış ve denetim */
(() => {
  "use strict";

  const mobileQuery = window.matchMedia("(max-width: 780px)");
  const auditEnabled = new URLSearchParams(window.location.search).get("mobile_audit") === "1";

  const setViewportHeight = () => {
    document.documentElement.style.setProperty("--v132-vh", `${window.innerHeight * 0.01}px`);
  };

  const makeScrollableRegionAccessible = () => {
    const selectors = [
      ".compare-scroll",
      ".notification-status-tabs",
      ".notification-type-tabs",
      ".offer-tabs",
      ".support-filter-tabs",
      ".v16-account-sidebar",
      ".v18-profile-steps",
      ".v131-mobile-facts",
      ".v131-mobile-quick-filters",
    ];
    document.querySelectorAll(selectors.join(",")).forEach((element) => {
      if (!element.hasAttribute("tabindex")) element.setAttribute("tabindex", "0");
      if (!element.hasAttribute("role")) element.setAttribute("role", "region");
      if (!element.hasAttribute("aria-label")) element.setAttribute("aria-label", "Yatay kaydırılabilir içerik");
    });
  };

  const improveMobileDetails = () => {
    const accordions = document.querySelectorAll(".support-faq-group");
    accordions.forEach((group) => {
      group.querySelectorAll(":scope > details").forEach((details) => {
        details.addEventListener("toggle", () => {
          if (!mobileQuery.matches || !details.open) return;
          group.querySelectorAll(":scope > details[open]").forEach((other) => {
            if (other !== details) other.removeAttribute("open");
          });
        });
      });
    });
  };

  const improveMobileMenu = () => {
    const menu = document.querySelector("[data-mobile-menu]");
    const toggle = document.querySelector("[data-menu-toggle]");
    if (!menu || !toggle) return;

    menu.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        if (mobileQuery.matches && menu.classList.contains("is-open")) toggle.click();
      });
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && menu.classList.contains("is-open")) {
        toggle.click();
        toggle.focus();
      }
    });
  };

  const protectForms = () => {
    document.querySelectorAll("form").forEach((form) => {
      form.addEventListener("submit", () => {
        const submitter = form.querySelector('button[type="submit"], input[type="submit"], button:not([type])');
        if (!submitter || submitter.dataset.allowRepeat === "1") return;
        submitter.setAttribute("aria-busy", "true");
        window.setTimeout(() => {
          submitter.disabled = true;
          submitter.classList.add("is-submitting");
        }, 0);
      });
    });
  };

  const markCurrentSection = () => {
    const namespace = document.body.className.match(/\bapp-([^\s]+)/)?.[1] || "";
    document.querySelectorAll(".mobile-menu a").forEach((link) => {
      const path = new URL(link.href, window.location.origin).pathname;
      const matches =
        (namespace === "accounts" && path.startsWith("/hesap/")) ||
        (namespace === "listings" && path.startsWith("/ilanlar/")) ||
        (namespace === "support_center" && path.startsWith("/yardim/")) ||
        (namespace === "managed_services" && path.startsWith("/tam-yonetim/")) ||
        (namespace === "partners" && path.startsWith("/kazanc-agi/"));
      if (matches) link.setAttribute("aria-current", "page");
    });
  };

  const runOverflowAudit = () => {
    if (!mobileQuery.matches) return [];
    document.querySelectorAll('[data-mobile-overflow="true"]').forEach((item) => item.removeAttribute("data-mobile-overflow"));

    const viewportWidth = document.documentElement.clientWidth;
    const ignored = new Set(["SCRIPT", "STYLE", "SVG", "PATH"]);
    const findings = [];

    document.querySelectorAll("body *").forEach((element) => {
      if (ignored.has(element.tagName)) return;
      const style = window.getComputedStyle(element);
      if (style.display === "none" || style.visibility === "hidden" || style.position === "fixed") return;
      if (["auto", "scroll"].includes(style.overflowX)) return;
      const rect = element.getBoundingClientRect();
      if (rect.width < 1 || rect.height < 1) return;
      if (rect.right > viewportWidth + 2 || rect.left < -2) {
        const identifier = [
          element.tagName.toLowerCase(),
          element.id ? `#${element.id}` : "",
          ...Array.from(element.classList).slice(0, 3).map((name) => `.${name}`),
        ].join("");
        findings.push({
          element: identifier,
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          width: Math.round(rect.width),
          viewport: viewportWidth,
        });
        if (auditEnabled) element.setAttribute("data-mobile-overflow", "true");
      }
    });

    window.__ILANSEHRI_MOBILE_AUDIT__ = {
      version: "v1.18.0",
      viewport: { width: viewportWidth, height: window.innerHeight },
      path: window.location.pathname,
      overflows: findings.slice(0, 50),
    };
    if (auditEnabled) console.info("İlan Şehri mobil denetim", window.__ILANSEHRI_MOBILE_AUDIT__);
    return findings;
  };

  const initialize = () => {
    setViewportHeight();
    makeScrollableRegionAccessible();
    improveMobileDetails();
    improveMobileMenu();
    protectForms();
    markCurrentSection();
    document.documentElement.dataset.mobileSystem = "v132";
    window.requestAnimationFrame(() => window.setTimeout(runOverflowAudit, 160));
  };

  document.addEventListener("DOMContentLoaded", initialize);
  window.addEventListener("resize", () => {
    setViewportHeight();
    window.clearTimeout(window.__v132ResizeTimer);
    window.__v132ResizeTimer = window.setTimeout(runOverflowAudit, 180);
  }, { passive: true });
})();
