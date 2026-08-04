/* İlan Şehri v1.8 — eksik tamamlama ve kullanıcı deneyimi */
document.addEventListener("DOMContentLoaded", () => {
  // Dismissible flash messages.
  const dismissFlash = (message) => {
    if (!message || message.classList.contains("is-hiding")) return;
    message.classList.add("is-hiding");
    window.setTimeout(() => message.remove(), 260);
  };
  document.querySelectorAll("[data-flash-message]").forEach((message) => {
    message.querySelector("[data-flash-close]")?.addEventListener("click", () => dismissFlash(message));
    if (message.classList.contains("success") || message.classList.contains("info")) {
      window.setTimeout(() => dismissFlash(message), 6500);
    }
  });

  // Highlight only the most specific current navigation entry.
  const pathname = window.location.pathname.replace(/\/$/, "") || "/";
  const navigationLinks = Array.from(document.querySelectorAll(".market-nav a,.market-mobile-nav a"));
  const matches = navigationLinks.map((link) => {
    try {
      const target = new URL(link.href, window.location.origin).pathname.replace(/\/$/, "") || "/";
      const matchesPath = target === "/" ? pathname === "/" : pathname.startsWith(target);
      return matchesPath ? { link, target } : null;
    } catch (_error) { return null; }
  }).filter(Boolean);
  const longestLength = matches.reduce((length, item) => Math.max(length, item.target.length), 0);
  matches.filter((item) => item.target.length === longestLength).forEach((item) => {
    item.link.classList.add("is-current");
    item.link.setAttribute("aria-current", "page");
  });


  // Clear the create-listing draft only after a confirmed successful server redirect.
  const successfulListingMessage = Array.from(document.querySelectorAll("[data-flash-message].success span"))
    .some((node) => /İlanın (kaydedildi|yayınlandı)/i.test(node.textContent || ""));
  if (successfulListingMessage) {
    try { window.localStorage.removeItem("ilansehri:listing-create-v18"); } catch (_error) {}
  }

  // Back-to-top button.
  const scrollTopButton = document.querySelector("[data-scroll-top]");
  if (scrollTopButton) {
    const syncScrollButton = () => scrollTopButton.classList.toggle("is-visible", window.scrollY > 720);
    syncScrollButton();
    window.addEventListener("scroll", syncScrollButton, { passive: true });
    scrollTopButton.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  }

  // Character counters for long text fields.
  document.querySelectorAll("textarea[maxlength], input[type=text][maxlength]").forEach((field) => {
    if (field.dataset.v18CounterReady === "1") return;
    field.dataset.v18CounterReady = "1";
    const max = Number(field.maxLength);
    if (!Number.isFinite(max) || max <= 0) return;
    const counter = document.createElement("small");
    counter.className = "v18-char-counter";
    field.insertAdjacentElement("afterend", counter);
    const update = () => {
      const length = String(field.value || "").length;
      counter.textContent = `${length} / ${max}`;
      counter.classList.toggle("near-limit", length >= max * 0.85);
    };
    update();
    field.addEventListener("input", update);
  });

  // Prevent accidental duplicate submits and show immediate feedback.
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (event.defaultPrevented) return;
      const submitter = event.submitter;
      if (!submitter || submitter.hasAttribute("formnovalidate")) return;
      if (submitter.dataset.v18Submitting === "1") {
        event.preventDefault();
        return;
      }
      submitter.dataset.v18Submitting = "1";
      submitter.classList.add("is-loading");
      submitter.setAttribute("aria-busy", "true");
    });
  });

  // Browser-local draft protection for the new listing wizard.
  const draftForm = document.querySelector("form[data-v18-draft-key]");
  if (draftForm) {
    const key = `ilansehri:${draftForm.dataset.v18DraftKey}`;
    const box = document.querySelector("[data-v18-draft-box]");
    const status = box?.querySelector("[data-v18-draft-status]");
    const restoreButton = box?.querySelector("[data-v18-restore-draft]");
    const clearButton = box?.querySelector("[data-v18-clear-draft]");
    let restored = false;
    let saveTimer;

    const eligibleFields = () => Array.from(draftForm.elements).filter((field) => {
      if (!field.name || field.disabled) return false;
      if (["csrfmiddlewaretoken", "images", "image_order"].includes(field.name)) return false;
      return !["file", "password", "submit", "button", "hidden"].includes(field.type);
    });

    const serialize = () => {
      const values = {};
      eligibleFields().forEach((field) => {
        if (field.type === "checkbox" || field.type === "radio") values[field.name] = field.checked;
        else values[field.name] = field.value;
      });
      return { savedAt: Date.now(), values };
    };

    const readDraft = () => {
      try {
        const raw = window.localStorage.getItem(key);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        if (!parsed?.values || Date.now() - Number(parsed.savedAt || 0) > 14 * 24 * 60 * 60 * 1000) {
          window.localStorage.removeItem(key);
          return null;
        }
        return parsed;
      } catch (_error) { return null; }
    };

    const syncDraftNotice = () => {
      const draft = readDraft();
      if (restoreButton) restoreButton.hidden = !draft || restored;
      if (status && draft && !restored) {
        const date = new Date(draft.savedAt);
        status.textContent = `${date.toLocaleString("tr-TR")} tarihinde kaydedilmiş bir taslak bulundu.`;
      }
    };

    const saveDraft = () => {
      try {
        window.localStorage.setItem(key, JSON.stringify(serialize()));
        box?.classList.add("saved");
        if (status) status.textContent = "Son değişiklikler tarayıcıya kaydedildi.";
        window.setTimeout(() => box?.classList.remove("saved"), 900);
      } catch (_error) {
        if (status) status.textContent = "Tarayıcı taslağı kaydedemedi; formu kapatmadan önce kontrol et.";
      }
    };

    const scheduleSave = () => {
      window.clearTimeout(saveTimer);
      saveTimer = window.setTimeout(saveDraft, 450);
    };

    restoreButton?.addEventListener("click", () => {
      const draft = readDraft();
      if (!draft) return;
      eligibleFields().forEach((field) => {
        if (!(field.name in draft.values)) return;
        if (field.type === "checkbox" || field.type === "radio") field.checked = Boolean(draft.values[field.name]);
        else field.value = draft.values[field.name] ?? "";
        field.dispatchEvent(new Event("change", { bubbles: true }));
        field.dispatchEvent(new Event("input", { bubbles: true }));
      });
      restored = true;
      restoreButton.hidden = true;
      if (status) status.textContent = "Taslak geri getirildi. Fotoğrafları güvenlik nedeniyle yeniden seçmelisin.";
    });

    clearButton?.addEventListener("click", () => {
      try { window.localStorage.removeItem(key); } catch (_error) {}
      restored = false;
      if (restoreButton) restoreButton.hidden = true;
      if (status) status.textContent = "Tarayıcı taslağı temizlendi. Yeni yazdıkların tekrar otomatik kaydedilir.";
    });

    draftForm.addEventListener("input", scheduleSave);
    draftForm.addEventListener("change", scheduleSave);
    // The draft is cleared on the redirected success page, not before server validation.
    syncDraftNotice();
  }
});
