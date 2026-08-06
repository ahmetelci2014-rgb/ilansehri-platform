(() => {
  "use strict";

  const conversation = document.querySelector("[data-v125-conversation]");
  if (conversation) {
    const thread = conversation.querySelector("[data-v125-thread]");
    if (thread && !new URLSearchParams(window.location.search).has("history")) {
      requestAnimationFrame(() => { thread.scrollTop = thread.scrollHeight; });
    }

    const composer = conversation.querySelector("[data-v125-composer]");
    const textarea = composer?.querySelector("textarea[name='body']");
    conversation.querySelectorAll("[data-v125-quick-reply]").forEach((button) => {
      button.addEventListener("click", () => {
        if (!textarea) return;
        const reply = button.getAttribute("data-v125-quick-reply") || "";
        const current = textarea.value.trim();
        textarea.value = current ? `${current}\n${reply}` : reply;
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
        textarea.focus();
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);
      });
    });
  }

  const focusedOffer = document.querySelector("[data-v125-offer-card].focused");
  if (focusedOffer && !window.location.hash) {
    requestAnimationFrame(() => focusedOffer.scrollIntoView({ block: "center", behavior: "smooth" }));
  }

  document.querySelectorAll(".v125-counter-box").forEach((details) => {
    details.addEventListener("toggle", () => {
      if (!details.open) return;
      document.querySelectorAll(".v125-counter-box[open]").forEach((other) => {
        if (other !== details) other.open = false;
      });
      const input = details.querySelector("input[name='amount']");
      if (input) window.setTimeout(() => input.focus(), 50);
    });
  });
})();
