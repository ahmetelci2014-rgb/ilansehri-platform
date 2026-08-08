document.addEventListener("click", function (event) {
  if (window.innerWidth > 1100) return;

  const button = event.target.closest("[data-menu-toggle]");
  if (!button) return;

  const menu = document.querySelector("[data-mobile-menu]");
  if (!menu) return;

  event.preventDefault();
  event.stopImmediatePropagation();

  const willOpen = !menu.classList.contains("is-open");

  menu.classList.toggle("is-open", willOpen);
  button.classList.toggle("is-open", willOpen);
  button.setAttribute("aria-expanded", willOpen ? "true" : "false");

  document.body.classList.toggle("menu-open", willOpen);
}, true);

/* header konum mesafesi */
document.addEventListener("DOMContentLoaded", () => {
  const picker = document.querySelector("[data-header-radius]");
  const nearby = document.querySelector(".header-location-panel [data-nearby-search]");
  if (!picker || !nearby) return;

  picker.querySelectorAll("[data-radius-value]").forEach((button) => {
    button.addEventListener("click", () => {
      picker.querySelectorAll("[data-radius-value]").forEach((item) => {
        item.classList.remove("active");
      });
      button.classList.add("active");
      nearby.dataset.radius = button.dataset.radiusValue;
      const copy = nearby.querySelector("small");
      if (copy) copy.textContent = `${button.dataset.radiusValue} km çevrendeki ilanlar`;
    });
  });
});
