/* İlan Şehri v1.13 — mobil ilan odaklı etkileşimler */
document.addEventListener("DOMContentLoaded", () => {
  const mobileQuery = window.matchMedia("(max-width: 780px)");
  const resultGrid = document.querySelector(".market-card-grid.list-grid");
  const viewButtons = Array.from(document.querySelectorAll("[data-result-view]"));

  if (resultGrid && viewButtons.length && mobileQuery.matches) {
    const mobileKey = "ilansehri-mobile-result-view";
    let preferred = "compact";
    try { preferred = window.localStorage.getItem(mobileKey) || "compact"; } catch (_error) {}

    const button = viewButtons.find((item) => item.dataset.resultView === preferred)
      || viewButtons.find((item) => item.dataset.resultView === "compact");
    window.requestAnimationFrame(() => button?.click());

    viewButtons.forEach((item) => item.addEventListener("click", () => {
      if (!mobileQuery.matches) return;
      try { window.localStorage.setItem(mobileKey, item.dataset.resultView || "compact"); } catch (_error) {}
    }));
  }

  const filterPanel = document.querySelector("[data-filter-panel]");
  if (filterPanel) {
    const close = () => document.querySelector("[data-filter-close]")?.click();
    filterPanel.querySelector("form")?.addEventListener("submit", () => {
      filterPanel.classList.add("is-submitting");
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && filterPanel.classList.contains("is-open")) close();
    });
  }


  // Mobil aramada tek dokunuşla temizleme.
  document.querySelectorAll("[data-mobile-search-form]").forEach((form) => {
    const input = form.querySelector("[data-mobile-search-input]");
    const clearButton = form.querySelector("[data-mobile-search-clear]");
    if (!input || !clearButton) return;
    const sync = () => { clearButton.hidden = !String(input.value || "").trim(); };
    sync();
    input.addEventListener("input", sync);
    clearButton.addEventListener("click", () => {
      input.value = "";
      sync();
      input.focus();
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
  });

  // Seçilen ilan türüne göre yalnız ilgili ayrıntılı filtreleri göster.
  document.querySelectorAll("[data-filter-panel]").forEach((panel) => {
    const kindSelect = panel.querySelector("[data-kind-filter]");
    const sections = Array.from(panel.querySelectorAll("[data-kind-section]"));
    if (!kindSelect || !sections.length) return;
    const syncKindSections = () => {
      const selected = String(kindSelect.value || "");
      sections.forEach((section) => {
        const visible = section.dataset.kindSection === selected;
        section.hidden = !visible;
        section.querySelectorAll("input,select,textarea").forEach((field) => {
          field.disabled = !visible;
        });
      });
    };
    syncKindSections();
    kindSelect.addEventListener("change", syncKindSections);
  });

  // Aktif hızlı filtreyi mobilde görünür alana getir.
  document.querySelectorAll(".v131-mobile-quick-filters").forEach((nav) => {
    const active = nav.querySelector("a.active");
    if (active && mobileQuery.matches) {
      window.requestAnimationFrame(() => active.scrollIntoView({ block: "nearest", inline: "center" }));
    }
  });

  document.querySelectorAll(".market-card").forEach((card) => {
    card.addEventListener("touchstart", () => card.classList.add("is-touching"), { passive: true });
    ["touchend", "touchcancel"].forEach((name) => card.addEventListener(name, () => {
      window.setTimeout(() => card.classList.remove("is-touching"), 120);
    }, { passive: true }));
  });
});
