/* İlan Şehri v1.22.0 — ilan verme ilerlemesi ve görsel kalite sözleşmesi */
document.addEventListener("DOMContentLoaded", () => {
  const wizard = document.querySelector("[data-v16-wizard]");
  if (!wizard) return;

  const progress = wizard.querySelector("[data-v122-wizard-progress]");
  const progressBar = progress?.querySelector("[data-v122-wizard-progress-bar]");
  const progressText = progress?.querySelector("[data-v122-wizard-progress-text]");
  const sections = Array.from(wizard.querySelectorAll("[data-v16-section]"));
  const checklist = wizard.querySelector("[data-v122-review-checklist]");
  const existingImages = () => Boolean(wizard.querySelector("[data-sortable-images] [data-image-id]"));
  const fileCount = () => wizard.querySelector('[name="images"]')?.files?.length || 0;
  const fieldValue = (name) => String(wizard.querySelector(`[name="${name}"]`)?.value || "").trim();
  const checked = (name) => Boolean(wizard.querySelector(`[name="${name}"]`)?.checked);

  const checkState = () => ({
    category: Boolean(fieldValue("kind") && fieldValue("category")),
    title: Boolean(fieldValue("title").length >= 10 && fieldValue("description").length >= 30),
    price: Boolean(fieldValue("price") || checked("price_on_request")),
    location: Boolean(fieldValue("city") && fieldValue("district")),
    photo: existingImages() || fileCount() > 0,
  });

  const update = () => {
    const activeIndex = Math.max(0, sections.findIndex((section) => section.classList.contains("active")));
    const stepPercent = sections.length ? Math.round(((activeIndex + 1) / sections.length) * 100) : 0;
    const states = checkState();
    const completed = Object.values(states).filter(Boolean).length;
    const qualityPercent = Math.round((completed / Object.keys(states).length) * 100);
    const percent = Math.max(stepPercent, qualityPercent);
    if (progressBar) progressBar.style.width = `${percent}%`;
    if (progressText) progressText.textContent = activeIndex === sections.length - 1
      ? `${completed}/5 yayın kontrolü tamamlandı`
      : `${activeIndex + 1}. adım · ilan kalitesi %${qualityPercent}`;

    Object.entries(states).forEach(([name, done]) => {
      const item = checklist?.querySelector(`[data-v122-check="${name}"]`);
      if (!item) return;
      item.classList.toggle("done", done);
      item.classList.toggle("warning", !done && activeIndex === sections.length - 1);
      const icon = item.querySelector("span");
      if (icon) icon.textContent = done ? "✓" : "○";
    });
  };

  const observer = new MutationObserver(update);
  sections.forEach((section) => observer.observe(section, { attributes: true, attributeFilter: ["class"] }));
  wizard.addEventListener("input", update);
  wizard.addEventListener("change", update);
  wizard.addEventListener("click", () => window.setTimeout(update, 0));
  update();
});
