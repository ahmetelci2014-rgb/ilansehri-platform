(() => {
  const showToast = () => {
    const toast = document.querySelector("[data-copy-toast]");
    if (!toast) return;
    toast.hidden = false;
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => { toast.hidden = true; }, 2200);
  };
  document.addEventListener("click", async (event) => {
    const share = event.target.closest("[data-share-listing]");
    if (share) {
      const data = { title: share.dataset.shareTitle || document.title, url: share.dataset.shareUrl || location.href };
      if (navigator.share) {
        try { await navigator.share(data); } catch (error) { if (error && error.name !== "AbortError") console.warn(error); }
      } else if (navigator.clipboard) {
        await navigator.clipboard.writeText(data.url); showToast();
      }
      return;
    }
    const copy = event.target.closest("[data-copy-listing]");
    if (copy) {
      const url = copy.dataset.copyUrl || location.href;
      try {
        if (navigator.clipboard) await navigator.clipboard.writeText(url);
        else { const input = document.createElement("input"); input.value = url; document.body.append(input); input.select(); document.execCommand("copy"); input.remove(); }
        showToast();
      } catch (error) { console.warn(error); }
    }
  });
})();
