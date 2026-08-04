/* İlan Şehri v1.6 — görünür arayüz ve adımlı ilan oluşturma */
document.addEventListener("DOMContentLoaded", () => {
  const resultGrid = document.querySelector(".market-card-grid.list-grid");
  const viewButtons = document.querySelectorAll("[data-result-view]");
  if (resultGrid && viewButtons.length) {
    const applyView = (view) => {
      const compact = view === "compact";
      resultGrid.classList.toggle("v16-compact-view", compact);
      viewButtons.forEach((button) => {
        const active = button.dataset.resultView === view;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      });
      try { window.localStorage.setItem("ilansehri-result-view", view); } catch (_error) {}
    };
    let saved = "grid";
    try { saved = window.localStorage.getItem("ilansehri-result-view") || "grid"; } catch (_error) {}
    applyView(saved === "compact" ? "compact" : "grid");
    viewButtons.forEach((button) => button.addEventListener("click", () => applyView(button.dataset.resultView)));
  }

  const mainImage = document.querySelector("[data-v16-main-image]");
  const galleryThumbs = document.querySelectorAll("[data-v16-gallery-thumb]");
  galleryThumbs.forEach((button, index) => {
    if (index === 0) button.classList.add("active");
    button.addEventListener("click", () => {
      if (!mainImage) return;
      mainImage.src = button.dataset.v16GalleryThumb;
      galleryThumbs.forEach((item) => item.classList.toggle("active", item === button));
    });
  });

  const wizard = document.querySelector("[data-v16-wizard]");
  if (!wizard) return;

  const sections = Array.from(wizard.querySelectorAll("[data-v16-section]"));
  const stepButtons = Array.from(wizard.querySelectorAll("[data-v16-step]"));
  const nextButton = wizard.querySelector("[data-v16-next]");
  const backButton = wizard.querySelector("[data-v16-back]");
  const submitButton = wizard.querySelector("[data-v16-submit]");
  const stepText = wizard.querySelector("[data-v16-step-text]");
  const scoreText = document.querySelector("[data-v16-score-text]");
  const scoreBar = document.querySelector("[data-v16-score-bar]");
  let activeIndex = 0;

  const isVisible = (element) => !element.hidden && element.offsetParent !== null;
  const invalidFieldIn = (section) => {
    const fields = section.querySelectorAll("input, select, textarea");
    for (const field of fields) {
      if (!isVisible(field) || field.disabled || field.type === "hidden") continue;
      if (!field.checkValidity()) return field;
    }
    return null;
  };

  const valueOf = (selector) => wizard.querySelector(selector)?.value?.trim() || "";
  const updateLivePreview = () => {
    const title = valueOf("#id_title") || "İlan başlığın burada görünecek";
    const price = valueOf("#id_price");
    const requestPrice = wizard.querySelector("#id_price_on_request")?.checked;
    const kindSelect = wizard.querySelector("#id_kind");
    const kind = kindSelect?.selectedOptions?.[0]?.textContent || "İlan türü";
    const city = valueOf("#id_city");
    const district = valueOf("#id_district");
    document.querySelector("[data-preview-title]")?.replaceChildren(document.createTextNode(title));
    document.querySelector("[data-preview-price]")?.replaceChildren(document.createTextNode(requestPrice ? "Teklif alıyor" : price ? `${Number(price).toLocaleString("tr-TR")} TL` : "Fiyat"));
    document.querySelector("[data-preview-kind]")?.replaceChildren(document.createTextNode(kind));
    document.querySelector("[data-preview-location]")?.replaceChildren(document.createTextNode([city, district].filter(Boolean).join(" · ") || "Şehir · İlçe"));
  };

  const calculateScore = () => {
    const selectors = [
      "[name=kind]", "[name=category]", "[name=title]", "[name=description]",
      "[name=city]", "[name=district]", "[name=price]", "[name=images]"
    ];
    let completed = 0;
    selectors.forEach((selector) => {
      const field = wizard.querySelector(selector);
      if (!field) return;
      if (field.type === "file") {
        if (field.files?.length || document.querySelector("[data-sortable-images] [data-image-id]")) completed += 1;
      } else if (String(field.value || "").trim()) completed += 1;
    });
    const percent = Math.round((completed / selectors.length) * 100);
    if (scoreText) scoreText.textContent = `${percent}%`;
    if (scoreBar) scoreBar.style.width = `${percent}%`;
    updateLivePreview();
  };

  const showStep = (index, { focus = false } = {}) => {
    activeIndex = Math.max(0, Math.min(index, sections.length - 1));
    sections.forEach((section, itemIndex) => section.classList.toggle("active", itemIndex === activeIndex));
    stepButtons.forEach((button, itemIndex) => {
      button.classList.toggle("active", itemIndex === activeIndex);
      button.classList.toggle("done", itemIndex < activeIndex);
      button.setAttribute("aria-current", itemIndex === activeIndex ? "step" : "false");
    });
    if (backButton) backButton.hidden = activeIndex === 0;
    if (nextButton) nextButton.hidden = activeIndex === sections.length - 1;
    if (submitButton) submitButton.hidden = activeIndex !== sections.length - 1;
    if (stepText) stepText.textContent = `${activeIndex + 1}. adım / ${sections.length}`;
    if (focus) {
      sections[activeIndex]?.scrollIntoView({ behavior: "smooth", block: "start" });
      sections[activeIndex]?.querySelector("input:not([type=hidden]),select,textarea")?.focus({ preventScroll: true });
    }
  };

  wizard.classList.add("v16-wizard-ready");
  const errorSectionIndex = sections.findIndex((section) => section.querySelector(".field-error, .errorlist"));
  showStep(errorSectionIndex >= 0 ? errorSectionIndex : 0);
  calculateScore();

  stepButtons.forEach((button, index) => button.addEventListener("click", () => {
    if (index > activeIndex) {
      const invalid = invalidFieldIn(sections[activeIndex]);
      if (invalid) { invalid.reportValidity(); invalid.focus(); return; }
    }
    showStep(index, { focus: true });
  }));

  nextButton?.addEventListener("click", () => {
    const invalid = invalidFieldIn(sections[activeIndex]);
    if (invalid) { invalid.reportValidity(); invalid.focus(); return; }
    showStep(activeIndex + 1, { focus: true });
  });
  backButton?.addEventListener("click", () => showStep(activeIndex - 1, { focus: true }));

  wizard.addEventListener("input", calculateScore);
  wizard.addEventListener("change", calculateScore);
  wizard.querySelector("[name=images]")?.addEventListener("change", calculateScore);

  wizard.addEventListener("submit", (event) => {
    if (event.submitter?.formNoValidate || event.submitter?.value === "save_draft") return;
    if (event.submitter && event.submitter !== submitButton && event.submitter.formAction !== wizard.action) return;
    const invalidIndex = sections.findIndex((section) => invalidFieldIn(section));
    if (invalidIndex >= 0) {
      event.preventDefault();
      showStep(invalidIndex, { focus: true });
      const invalid = invalidFieldIn(sections[invalidIndex]);
      invalid?.reportValidity();
      invalid?.focus();
    }
  });
});
