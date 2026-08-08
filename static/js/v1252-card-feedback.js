(() => {
  "use strict";

  const toast = (message) => {
    let box = document.querySelector("[data-card-feedback-toast]");

    if (!box) {
      box = document.createElement("div");
      box.dataset.cardFeedbackToast = "";
      box.className = "v1252-card-feedback-toast";
      box.setAttribute("role", "status");
      box.setAttribute("aria-live", "polite");
      document.body.appendChild(box);
    }

    box.textContent = message;
    box.classList.add("show");

    window.clearTimeout(box._timer);

    box._timer = window.setTimeout(() => {
      box.classList.remove("show");
    }, 1600);
  };

  const updateFavoriteButtons = (action, active) => {
    document.querySelectorAll("[data-card-favorite]").forEach((form) => {
      if (form.action !== action) return;

      const button = form.querySelector(".market-card-tool");
      if (!button) return;

      button.classList.toggle("active", active);
      button.textContent = active ? "♥" : "♡";

      button.setAttribute(
        "aria-label",
        active ? "Favorilerden çıkar" : "Favoriye ekle",
      );
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-card-favorite]").forEach((form) => {
      const button = form.querySelector(".market-card-tool");

      if (!button) return;

      form.addEventListener("submit", async (event) => {
        event.preventDefault();

        if (button.disabled) return;

        button.disabled = true;

        button.classList.remove("v1252-favorite-pop");
        void button.offsetWidth;
        button.classList.add("v1252-favorite-pop");

        try {
          const response = await fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            credentials: "same-origin",
            headers: {
              "X-Requested-With": "XMLHttpRequest",
              "Accept": "application/json",
            },
          });

          if (!response.ok) {
            throw new Error("favorite request failed");
          }

          const data = await response.json();
          const active = Boolean(data.active);

          updateFavoriteButtons(form.action, active);

          toast(
            active
              ? "♥ Favorilere eklendi"
              : "Favorilerden çıkarıldı",
          );
        } catch (_error) {
          /*
           * Ağ/AJAX sorunu olursa eski klasik POST davranışına dön.
           * Favori özelliği hiçbir zaman kullanılamaz hale gelmesin.
           */
          HTMLFormElement.prototype.submit.call(form);
          return;
        } finally {
          button.disabled = false;
        }
      });
    });
  });
})();
