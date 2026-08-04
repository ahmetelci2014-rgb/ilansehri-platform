document.addEventListener("DOMContentLoaded", () => {
  const assistant = document.querySelector("[data-ai-listing-assistant]");
  if (!assistant) return;
  const form = assistant.closest("form");
  const imageInput = form?.querySelector("#id_images");
  const button = assistant.querySelector("[data-ai-analyze]");
  const progress = assistant.querySelector("[data-ai-progress]");
  const resultBox = assistant.querySelector("[data-ai-result]");
  const analysisInput = form?.querySelector("[data-ai-analysis-id]");
  const maxImages = Number(assistant.dataset.maxImages || 8);
  const endpoint = assistant.dataset.analyzeUrl;

  const escapeHtml = (value) => String(value || "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  }[char]));

  const setMessage = (message, type = "") => {
    if (!resultBox) return;
    resultBox.innerHTML = `<div class="ai-listing-message ${type}">${escapeHtml(message)}</div>`;
  };

  const updateVisibility = () => {
    const count = imageInput?.files?.length || 0;
    assistant.hidden = count === 0;
    if (button) button.disabled = count === 0 || count > maxImages;
    if (count > maxImages) setMessage(`En fazla ${maxImages} fotoğraf analiz edilebilir.`, "error");
  };

  const markSuggested = (field) => {
    const wrapper = field?.closest(".field");
    if (!wrapper || wrapper.querySelector(".ai-suggestion-badge")) return;
    wrapper.classList.add("ai-suggested");
    const label = wrapper.querySelector("label");
    const badge = document.createElement("span");
    badge.className = "ai-suggestion-badge";
    badge.textContent = "AI önerisi";
    (label || wrapper).appendChild(badge);
  };

  const applyValue = (fieldId, value, confidence, minimum) => {
    if (!value || Number(confidence || 0) < minimum) return false;
    const field = form?.querySelector(`#${fieldId}`);
    if (!field) return false;
    field.value = value;
    field.dispatchEvent(new Event("change", { bubbles: true }));
    field.dispatchEvent(new Event("input", { bubbles: true }));
    markSuggested(field);
    return true;
  };

  const renderResult = (data) => {
    if (data.status === "blocked" || data.safety_status === "blocked") {
      setMessage("Güvenlik kontrolü nedeniyle bu fotoğraflardan ilan taslağı oluşturulmadı. Normal formu kullanabilir veya fotoğrafları değiştirebilirsin.", "error");
      return;
    }
    const output = data.result || {};
    if (analysisInput && data.analysis_id) analysisInput.value = data.analysis_id;
    const minimum = Number(data.minimum_confidence || 60);
    const fc = output.field_confidence || {};
    let applied = 0;
    applied += applyValue("id_title", output.title, fc.title ?? output.confidence_score, minimum) ? 1 : 0;
    applied += applyValue("id_description", output.description, fc.description ?? output.confidence_score, minimum) ? 1 : 0;
    applied += applyValue("id_condition", output.condition, fc.condition ?? 0, minimum) ? 1 : 0;
    applied += applyValue("id_brand", output.brand, fc.brand ?? 0, minimum) ? 1 : 0;
    applied += applyValue("id_model_name", output.model, fc.model ?? 0, minimum) ? 1 : 0;
    applied += applyValue("id_kind", output.kind, fc.category ?? output.confidence_score, minimum) ? 1 : 0;
    applied += applyValue("id_category", output.category_id, fc.category ?? output.confidence_score, minimum) ? 1 : 0;

    const messages = [];
    messages.push(`<div class="ai-listing-message"><b>Analiz tamamlandı.</b> ${applied ? `${applied} güvenli öneri forma yerleştirildi.` : "Düşük güvenli tahminler forma otomatik yazılmadı."} Bütün bilgileri kontrol ederek düzenleyebilirsin.</div>`);
    const suggestions = [
      output.color ? `Renk önerisi: ${escapeHtml(output.color)}` : "",
      ...(output.tags || []).length ? `Etiketler: ${(output.tags || []).map(escapeHtml).join(", ")}` : "",
      ...(output.detected_features || []).map((item) => `Görülen özellik: ${escapeHtml(item)}`),
      ...(output.possible_defects || []).map((item) => `Olası kusur: ${escapeHtml(item)}`),
    ].filter(Boolean);
    if (suggestions.length) messages.push(`<div class="ai-listing-message warning">${suggestions.join("<br>")}</div>`);
    const warnings = data.safety_warnings || [];
    if (warnings.length) messages.push(`<div class="ai-listing-message warning"><b>Dikkat:</b><br>${warnings.map(escapeHtml).join("<br>")}</div>`);
    const questions = data.missing_questions || [];
    if (questions.length) messages.push(`<ul class="ai-listing-questions">${questions.map((item) => `<li><b>Eksik bilgi:</b> ${escapeHtml(item.question || item)}</li>`).join("")}</ul>`);
    resultBox.innerHTML = messages.join("");
  };

  imageInput?.addEventListener("change", updateVisibility);
  updateVisibility();

  button?.addEventListener("click", async () => {
    const files = Array.from(imageInput?.files || []);
    if (!files.length || files.length > maxImages || !endpoint) return;
    button.disabled = true;
    progress.hidden = false;
    resultBox.innerHTML = "";
    const payload = new FormData();
    files.forEach((file) => payload.append("images", file));
    payload.append("request_id", globalThis.crypto?.randomUUID?.() || `ai-${Date.now()}-${Math.random().toString(16).slice(2)}`);
    const snapshot = {};
    ["kind", "action", "category", "condition", "brand", "model_name"].forEach((name) => {
      const field = form.querySelector(`[name="${name}"]`);
      if (field?.value) snapshot[name] = field.value;
    });
    payload.append("form_snapshot", JSON.stringify(snapshot));
    const csrf = form.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
        body: payload,
        credentials: "same-origin",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Fotoğraf analizi tamamlanamadı.");
      renderResult(data);
    } catch (error) {
      setMessage(`${error.message} Normal ilan verme işlemine devam edebilirsin.`, "error");
    } finally {
      progress.hidden = true;
      button.disabled = false;
    }
  });
});
