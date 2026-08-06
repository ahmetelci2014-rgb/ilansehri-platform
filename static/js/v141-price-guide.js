/* İlan Şehri v1.14.1 — Akıllı Fiyat Rehberi */
document.addEventListener("DOMContentLoaded", () => {
  const assistant = document.querySelector("[data-price-guide-assistant]");
  if (!assistant) return;

  const form = assistant.closest("form");
  const runButton = assistant.querySelector("[data-price-guide-run]");
  const result = assistant.querySelector("[data-price-guide-result]");
  const endpoint = assistant.dataset.priceGuideUrl || "";
  const currentId = assistant.dataset.currentListingId || "";
  const supportedKinds = new Set(["product", "vehicle", "real_estate"]);
  const supportedActions = new Set(["sell", "rent"]);
  const watchedNames = [
    "kind", "action", "category", "price", "brand", "model_name", "model_year",
    "mileage", "room_count", "area_m2", "city", "district", "neighborhood",
    "price_on_request",
  ];
  let controller = null;
  let applyingSuggestedPrice = false;

  const field = (name) => form?.querySelector(`[name="${name}"]`);
  const value = (name) => (field(name)?.value || "").trim();
  const checked = (name) => Boolean(field(name)?.checked);
  const formatPrice = (raw) => {
    const number = Number(raw);
    return Number.isFinite(number)
      ? new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 0 }).format(number)
      : "—";
  };
  const escapeHtml = (raw) => String(raw ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const eligibilityMessage = () => {
    if (!supportedKinds.has(value("kind"))) return "Fiyat rehberi ürün, araç ve emlak ilanlarında kullanılabilir.";
    if (!supportedActions.has(value("action"))) return "Satılık veya kiralık işlem türünü seç.";
    if (!value("category")) return "Önce ilan kategorisini seç.";
    if (checked("price_on_request")) return "Teklif usulü ilanlarda fiyat karşılaştırması yapılmaz.";
    return "";
  };

  const updateState = () => {
    const message = eligibilityMessage();
    runButton.disabled = Boolean(message) || !endpoint;
    runButton.title = message;
    assistant.classList.toggle("is-disabled", Boolean(message));
    if (message && !result.dataset.loaded) {
      result.innerHTML = `<p class="v141-price-guide-hint">${escapeHtml(message)}</p>`;
    }
  };

  const markStale = () => {
    if (applyingSuggestedPrice) return;
    if (result.dataset.loaded) {
      result.dataset.loaded = "";
      result.innerHTML = "<p class=\"v141-price-guide-hint\">Bilgiler değişti. Güncel aralık için yeniden hesapla.</p>";
    }
    updateState();
  };

  const params = () => {
    const query = new URLSearchParams();
    watchedNames.forEach((name) => {
      if (name === "price_on_request") return;
      const current = value(name);
      if (current) query.set(name, current);
    });
    if (currentId) query.set("current_id", currentId);
    return query;
  };

  const renderUnavailable = (guide) => {
    result.dataset.loaded = "1";
    result.innerHTML = `<div class="v141-price-guide-unavailable"><span>ⓘ</span><p>${escapeHtml(guide.message || "Yeterli benzer ilan bulunamadı.")}</p></div>`;
  };

  const renderGuide = (guide) => {
    const criteria = Array.isArray(guide.criteria)
      ? guide.criteria.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
      : "";
    const status = escapeHtml(guide.status || "no_price");
    const statusLabel = escapeHtml(guide.status_label || "Fiyat aralığı hazır");
    const confidence = escapeHtml(guide.confidence_label || "Veri bulundu");
    const median = escapeHtml(guide.median_price || "");

    result.dataset.loaded = "1";
    result.innerHTML = `
      <article class="v141-form-guide-card tone-${status}">
        <header><div><small>SONUÇ</small><strong>${statusLabel}</strong></div><span>${confidence}</span></header>
        <div class="v141-form-guide-values">
          <div><small>Tahmini aralık</small><b>${formatPrice(guide.lower_price)} – ${formatPrice(guide.upper_price)} TL</b></div>
          <div><small>Orta değer</small><strong>${formatPrice(guide.median_price)} TL</strong></div>
          <div><small>Karşılaştırılan</small><strong>${Number(guide.sample_count || 0)} ilan</strong></div>
        </div>
        <p>${escapeHtml(guide.message || "")}</p>
        <div class="v141-form-guide-footer">
          <button type="button" data-price-guide-apply data-price="${median}">Orta değeri fiyat alanına yaz</button>
          <details><summary>Nasıl hesaplandı?</summary><ul>${criteria}</ul></details>
        </div>
      </article>`;

    result.querySelector("[data-price-guide-apply]")?.addEventListener("click", (event) => {
      const priceInput = field("price");
      if (!priceInput) return;
      applyingSuggestedPrice = true;
      priceInput.value = event.currentTarget.dataset.price || "";
      priceInput.dispatchEvent(new Event("input", { bubbles: true }));
      priceInput.dispatchEvent(new Event("change", { bubbles: true }));
      applyingSuggestedPrice = false;
      const card = result.querySelector(".v141-form-guide-card");
      card?.classList.remove("tone-no_price", "tone-low", "tone-high");
      card?.classList.add("tone-fair");
      const statusText = card?.querySelector("header strong");
      if (statusText) statusText.textContent = "Piyasa aralığında";
      event.currentTarget.textContent = "Fiyat alanına yazıldı ✓";
      priceInput.focus({ preventScroll: true });
    });
  };

  runButton?.addEventListener("click", async () => {
    const message = eligibilityMessage();
    if (message) {
      renderUnavailable({ message });
      return;
    }

    controller?.abort();
    controller = new AbortController();
    runButton.disabled = true;
    runButton.classList.add("is-loading");
    runButton.textContent = "Benzer ilanlar hesaplanıyor…";
    result.dataset.loaded = "";
    result.innerHTML = "<div class=\"v141-price-guide-loading\"><i></i><span>Aktif ilan fiyatları karşılaştırılıyor…</span></div>";

    try {
      const response = await fetch(`${endpoint}?${params().toString()}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        signal: controller.signal,
      });
      const payload = await response.json();
      const guide = payload.guide || {};
      if (!response.ok || !guide.available) renderUnavailable(guide);
      else renderGuide(guide);
    } catch (error) {
      if (error.name !== "AbortError") {
        renderUnavailable({ message: "Fiyat rehberi şu anda çalıştırılamadı. Biraz sonra yeniden dene." });
      }
    } finally {
      runButton.classList.remove("is-loading");
      runButton.textContent = "Fiyat aralığını hesapla";
      updateState();
    }
  });

  watchedNames.forEach((name) => {
    const input = field(name);
    if (!input) return;
    input.addEventListener(input.type === "checkbox" || input.tagName === "SELECT" ? "change" : "input", markStale);
  });

  updateState();
});
