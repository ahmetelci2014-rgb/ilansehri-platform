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
