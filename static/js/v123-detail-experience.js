document.addEventListener("DOMContentLoaded", () => {
  const gallery = document.querySelector("[data-v123-gallery]");
  const mainImage = gallery?.querySelector("[data-v123-main-image]");
  const thumbs = Array.from(gallery?.querySelectorAll("[data-v123-gallery-thumb]") || []);
  const counter = gallery?.querySelector("[data-v123-gallery-counter]");
  const stage = gallery?.querySelector("[data-v123-gallery-stage]");
  const lightbox = document.querySelector("[data-v123-lightbox]");
  const lightboxImage = lightbox?.querySelector("[data-lightbox-image]");
  const lightboxCounter = lightbox?.querySelector("[data-v123-lightbox-counter]");
  const closeButton = lightbox?.querySelector("[data-gallery-close]");
  let activeIndex = Math.max(0, thumbs.findIndex((item) => item.classList.contains("active")));
  let previousFocus = null;

  const total = thumbs.length || (mainImage ? 1 : 0);
  const itemAt = (index) => thumbs[(index + thumbs.length) % thumbs.length];
  const setActive = (index, options = {}) => {
    if (!mainImage || !thumbs.length) return;
    activeIndex = (index + thumbs.length) % thumbs.length;
    const item = itemAt(activeIndex);
    const preview = item?.querySelector("img");
    stage?.classList.add("is-changing");
    mainImage.src = item.dataset.gallerySrc;
    mainImage.alt = preview?.alt || mainImage.alt;
    if (lightboxImage) {
      lightboxImage.src = mainImage.src;
      lightboxImage.alt = mainImage.alt;
    }
    thumbs.forEach((thumb, thumbIndex) => {
      const active = thumbIndex === activeIndex;
      thumb.classList.toggle("active", active);
      if (active) thumb.setAttribute("aria-current", "true");
      else thumb.removeAttribute("aria-current");
    });
    if (counter) counter.textContent = `${activeIndex + 1} / ${total}`;
    if (lightboxCounter) lightboxCounter.textContent = `${activeIndex + 1} / ${total}`;
    if (options.scrollThumb !== false) item?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    window.setTimeout(() => stage?.classList.remove("is-changing"), 150);
  };
  const next = () => setActive(activeIndex + 1);
  const previous = () => setActive(activeIndex - 1);

  thumbs.forEach((thumb, index) => thumb.addEventListener("click", () => setActive(index)));
  gallery?.querySelector("[data-v123-gallery-next]")?.addEventListener("click", (event) => { event.stopPropagation(); next(); });
  gallery?.querySelector("[data-v123-gallery-prev]")?.addEventListener("click", (event) => { event.stopPropagation(); previous(); });

  const openLightbox = () => {
    if (!lightbox || !mainImage?.src || !lightboxImage) return;
    previousFocus = document.activeElement;
    lightboxImage.src = mainImage.src;
    lightboxImage.alt = mainImage.alt;
    if (lightboxCounter) lightboxCounter.textContent = `${activeIndex + 1} / ${Math.max(total, 1)}`;
    lightbox.hidden = false;
    document.body.classList.add("v123-lightbox-open");
    closeButton?.focus();
  };
  const closeLightbox = () => {
    if (!lightbox) return;
    lightbox.hidden = true;
    document.body.classList.remove("v123-lightbox-open");
    previousFocus?.focus?.();
  };
  stage?.addEventListener("click", (event) => { if (!event.target.closest("button,a")) openLightbox(); });
  stage?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openLightbox(); }
    if (event.key === "ArrowRight") next();
    if (event.key === "ArrowLeft") previous();
  });
  closeButton?.addEventListener("click", closeLightbox);
  lightbox?.querySelector("[data-v123-lightbox-next]")?.addEventListener("click", next);
  lightbox?.querySelector("[data-v123-lightbox-prev]")?.addEventListener("click", previous);
  lightbox?.addEventListener("click", (event) => { if (event.target === lightbox) closeLightbox(); });
  document.addEventListener("keydown", (event) => {
    if (!lightbox || lightbox.hidden) return;
    if (event.key === "Escape") closeLightbox();
    if (event.key === "ArrowRight") next();
    if (event.key === "ArrowLeft") previous();
  });

  const bindSwipe = (element) => {
    if (!element || total < 2) return;
    let startX = 0;
    let startY = 0;
    element.addEventListener("touchstart", (event) => {
      const touch = event.changedTouches[0];
      startX = touch.clientX;
      startY = touch.clientY;
    }, { passive: true });
    element.addEventListener("touchend", (event) => {
      const touch = event.changedTouches[0];
      const deltaX = touch.clientX - startX;
      const deltaY = touch.clientY - startY;
      if (Math.abs(deltaX) < 48 || Math.abs(deltaX) < Math.abs(deltaY)) return;
      if (deltaX < 0) next(); else previous();
    }, { passive: true });
  };
  bindSwipe(stage);
  bindSwipe(lightbox);
  if (thumbs.length) setActive(activeIndex, { scrollThumb: false });

  const openBox = (selector) => {
    const box = document.querySelector(selector);
    if (!box) return;
    box.open = true;
    box.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => box.querySelector("input, textarea, select")?.focus(), 350);
  };
  document.querySelector("[data-open-offer]")?.addEventListener("click", () => openBox("[data-v123-offer-box]"));
  document.querySelector("[data-open-message]")?.addEventListener("click", (event) => { event.preventDefault(); openBox("[data-v123-message-box]"); });
});
