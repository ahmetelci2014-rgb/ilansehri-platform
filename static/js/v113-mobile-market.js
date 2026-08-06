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

  document.querySelectorAll(".market-card").forEach((card) => {
    card.addEventListener("touchstart", () => card.classList.add("is-touching"), { passive: true });
    ["touchend", "touchcancel"].forEach((name) => card.addEventListener(name, () => {
      window.setTimeout(() => card.classList.remove("is-touching"), 120);
    }, { passive: true }));
  });
});
