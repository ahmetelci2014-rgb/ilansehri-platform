(() => {
  "use strict";

  const showToast = (message) => {
    let toast = document.querySelector("[data-profile-follow-toast]");

    if (!toast) {
      toast = document.createElement("div");
      toast.dataset.profileFollowToast = "";
      toast.className = "v1252-card-feedback-toast";
      toast.setAttribute("role", "status");
      toast.setAttribute("aria-live", "polite");
      document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.add("show");

    clearTimeout(toast._timer);

    toast._timer = setTimeout(() => {
      toast.classList.remove("show");
    }, 1600);
  };

  document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("[data-profile-follow]");
    const button = form?.querySelector(".v1252-follow-button");

    if (!form || !button) return;

    let locked = false;

    const clearLoading = () => {
      button.disabled = false;
      button.classList.remove(
        "is-loading",
        "is-busy",
      );

      button.removeAttribute("aria-busy");

      button.style.cursor = "pointer";
      button.style.pointerEvents = "auto";
      button.style.opacity = "1";
    };

    const render = (following) => {
      form.dataset.following = following ? "1" : "0";

      button.classList.toggle(
        "is-following",
        following,
      );

      button.textContent = following
        ? "✓ Takip ediliyor"
        : "＋ Takip et";

      clearLoading();
    };

    render(form.dataset.following === "1");

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();

      if (locked) return;

      locked = true;

      const previous =
        form.dataset.following === "1";

      const next = !previous;

      /*
       * Görsel durum anında değişir.
       */
      render(next);

      showToast(
        next
          ? "✓ Satıcı takip ediliyor"
          : "Takip bırakıldı",
      );

      /*
       * Sunucu isteği arkada gider.
       * Buton görsel olarak kilitlenmez.
       */
      fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        credentials: "same-origin",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Accept": "application/json",
        },
      })
        .then(async (response) => {
          if (!response.ok) {
            throw new Error("follow request failed");
          }

          const data = await response.json();

          render(Boolean(data.following));
        })
        .catch(() => {
          /*
           * Sunucuya hiç ulaşılamadıysa eski duruma dön.
           */
          render(previous);

          showToast(
            "İşlem tamamlanamadı, tekrar dene.",
          );
        })
        .finally(() => {
          clearLoading();
        });

      /*
       * Görsel kilit yok.
       * Sadece çok hızlı çift tıklamayı engelle.
       */
      setTimeout(() => {
        locked = false;
        clearLoading();
      }, 500);
    }, true);
  });
})();
