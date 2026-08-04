document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector("[data-menu-toggle]");
  const menu = document.querySelector("[data-mobile-menu]");
  if (toggle && menu) {
    toggle.addEventListener("click", () => {
      const open = menu.classList.toggle("is-open");
      toggle.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", String(open));
      document.body.classList.toggle("menu-open", open);
    });
  }

  const header = document.querySelector("[data-header]");
  const updateHeader = () => header?.classList.toggle("is-scrolled", window.scrollY > 12);
  updateHeader();
  window.addEventListener("scroll", updateHeader, { passive: true });

  const imageInput = document.querySelector("[data-image-input]");
  const preview = document.querySelector("[data-image-preview]");
  if (imageInput && preview) {
    imageInput.addEventListener("change", () => {
      preview.innerHTML = "";
      Array.from(imageInput.files || []).slice(0, 10).forEach((file, index) => {
        if (!file.type.startsWith("image/")) return;
        const reader = new FileReader();
        reader.addEventListener("load", () => {
          const item = document.createElement("div");
          item.className = "image-preview-item";
          item.innerHTML = `<img alt="Seçilen fotoğraf ${index + 1}"><span>${index === 0 ? "Kapak" : index + 1}</span>`;
          item.querySelector("img").src = reader.result;
          preview.appendChild(item);
        });
        reader.readAsDataURL(file);
      });
    });
  }

  const mainImage = document.querySelector("[data-main-image]");
  document.querySelectorAll("[data-gallery-thumb]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!mainImage) return;
      mainImage.src = button.dataset.galleryThumb;
      document.querySelectorAll("[data-gallery-thumb]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
    });
  });
});
