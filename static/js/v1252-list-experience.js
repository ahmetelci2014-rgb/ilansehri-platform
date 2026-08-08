(() => {
  "use strict";

  document.addEventListener("DOMContentLoaded", () => {
    if (!window.matchMedia("(max-width:780px)").matches) return;

    [
      ".market-list-chips",
      ".v121-category-shortcuts",
    ].forEach((selector) => {
      const strip = document.querySelector(selector);
      const active = strip?.querySelector(".active");

      if (!strip || !active) return;

      window.setTimeout(() => {
        active.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
          inline: "center",
        });
      }, 120);
    });
  });
})();
