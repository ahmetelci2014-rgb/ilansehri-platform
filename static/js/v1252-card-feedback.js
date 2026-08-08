(() => {
  "use strict";

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-market-card]").forEach((card) => {
      const favorite = card.querySelector(
        ".market-card-tool:not(.compare-tool)"
      );

      favorite?.addEventListener("click", () => {
        favorite.classList.remove("v1252-favorite-pop");
        void favorite.offsetWidth;
        favorite.classList.add("v1252-favorite-pop");
      });
    });
  });
})();
