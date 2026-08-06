document.addEventListener("DOMContentLoaded", () => {
  const assistant = document.querySelector("[data-ai-listing-assistant]");
  if (!assistant) return;

  const form = assistant.closest("form");
  const imageInput = form?.querySelector("[data-image-input]");
  const preview = assistant.querySelector("[data-image-preview]");
  const dropZone = assistant.querySelector("[data-ai-drop-zone]");
  const button = assistant.querySelector("[data-ai-analyze]");
  const progress = assistant.querySelector("[data-ai-progress]");
  const resultBox = assistant.querySelector("[data-ai-result]");
  const statusBox = assistant.querySelector("[data-ai-status]");
  const fileSummary = assistant.querySelector("[data-ai-file-summary]");
  const clearButton = assistant.querySelector("[data-ai-clear-images]");
  const analysisInput = form?.querySelector("[data-ai-analysis-id]");
  const maxImages = Number(assistant.dataset.maxImages || 8);
  const maxImageSizeMb = Number(assistant.dataset.maxImageSize || 8);
  const endpoint = assistant.dataset.analyzeUrl;
  const canAnalyze = assistant.dataset.aiCanAnalyze === "1";
  const lockedMessage = assistant.dataset.aiStatusMessage || "Yapay zekâ özelliği şu anda kullanılamıyor.";
  let previewUrls = [];
  let analysisCompleted = false;

  if (!form || !imageInput) return;
  imageInput.dataset.aiUploadManaged = "true";

  const escapeHtml = (value) => String(value || "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  }[char]));

  const setMessage = (message, type = "") => {
    if (!resultBox) return;
    resultBox.innerHTML = `<div class="ai-listing-message ${type}">${escapeHtml(message)}</div>`;
  };

  const setStatus = (message, type = "") => {
    if (!statusBox) return;
    statusBox.textContent = message;
    statusBox.className = `ai-listing-status ${type}`.trim();
  };

  const files = () => Array.from(imageInput.files || []);

  const syncFileList = (nextFiles) => {
    if (typeof DataTransfer === "undefined") {
      imageInput.value = "";
      return false;
    }
    const transfer = new DataTransfer();
    nextFiles.forEach((file) => transfer.items.add(file));
    imageInput.files = transfer.files;
    imageInput.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  };

  const clearPreviewUrls = () => {
    previewUrls.forEach((url) => URL.revokeObjectURL(url));
    previewUrls = [];
  };

  const updateLiveCover = (file) => {
    const liveMedia = document.querySelector("[data-preview-media]");
    if (!liveMedia) return;
    if (!file) {
      liveMedia.innerHTML = "<div><span>📷</span><small>İlk fotoğraf burada görünecek</small></div>";
      return;
    }
    const url = URL.createObjectURL(file);
    previewUrls.push(url);
    const image = document.createElement("img");
    image.src = url;
    image.alt = "İlan fotoğrafı önizlemesi";
    liveMedia.replaceChildren(image);
  };

  const renderPreviews = () => {
    if (!preview) return;
    clearPreviewUrls();
    preview.innerHTML = "";
    const selected = files();
    selected.forEach((file, index) => {
      if (!file.type.startsWith("image/")) return;
      const url = URL.createObjectURL(file);
      previewUrls.push(url);
      const item = document.createElement("article");
      item.className = "ai-image-preview-item";
      item.innerHTML = `
        <img src="${url}" alt="Seçilen fotoğraf ${index + 1}">
        <div><b>${index === 0 ? "Kapak adayı" : `${index + 1}. fotoğraf`}</b><small>${escapeHtml(file.name)}</small></div>
        <button type="button" aria-label="${index + 1}. fotoğrafı kaldır" data-ai-remove-image="${index}">×</button>
      `;
      preview.appendChild(item);
    });
    updateLiveCover(selected[0]);
    if (fileSummary) {
      fileSummary.textContent = selected.length
        ? `${selected.length} fotoğraf seçildi. İlk fotoğraf kapak adayıdır.`
        : "Henüz fotoğraf seçilmedi.";
    }
    if (clearButton) clearButton.hidden = selected.length === 0;
    document.querySelector("[data-ai-review-photo-count]")?.replaceChildren(
      document.createTextNode(selected.length ? `${selected.length} fotoğraf hazır.` : "Henüz fotoğraf eklenmedi.")
    );
  };

  const validateFiles = () => {
    const selected = files();
    if (!selected.length) return { ok: false, message: `Önce en fazla ${maxImages} fotoğraf seç.`, type: "" };
    if (selected.length > maxImages) return { ok: false, message: `En fazla ${maxImages} fotoğraf analiz edilebilir.`, type: "error" };
    const unsupported = selected.find((file) => !["image/jpeg", "image/png", "image/webp"].includes(file.type));
    if (unsupported) return { ok: false, message: "Yalnızca JPG, JPEG, PNG ve WEBP fotoğraflar desteklenir.", type: "error" };
    const oversized = selected.find((file) => file.size > maxImageSizeMb * 1024 * 1024);
    if (oversized) return { ok: false, message: `Her fotoğraf en fazla ${maxImageSizeMb} MB olabilir.`, type: "error" };
    return { ok: true, message: `${selected.length} fotoğraf hazır. Yapay zekâ analizini başlatabilirsin.`, type: "success" };
  };

  const updateState = () => {
    renderPreviews();
    const validation = validateFiles();
    if (button) {
      button.disabled = !canAnalyze || !validation.ok;
      button.innerHTML = analysisCompleted
        ? "<span>↻</span> Fotoğrafları Yeniden Analiz Et"
        : "<span>✦</span> Yapay Zekâ ile İlan Hazırla";
    }
    if (!canAnalyze) {
      setStatus(lockedMessage, "warning");
      return;
    }
    if (analysisCompleted) {
      setStatus("Analiz tamamlandı. AI önerilerini adım adım kontrol et.", "success");
      return;
    }
    setStatus(validation.message, validation.type);
  };

  const markSuggested = (field, confidence) => {
    const wrapper = field?.closest(".field");
    if (!wrapper) return;
    wrapper.classList.add("ai-suggested");
    let badge = wrapper.querySelector(".ai-suggestion-badge");
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "ai-suggestion-badge";
      const label = wrapper.querySelector("label");
      (label || wrapper).appendChild(badge);
    }
    badge.textContent = Number.isFinite(Number(confidence)) ? `AI önerisi · %${Math.round(confidence)}` : "AI önerisi";
    field.dataset.aiFilled = "1";
  };

  const applyValue = (fieldName, value, confidence, minimum) => {
    if (value === null || value === undefined || value === "" || Number(confidence || 0) < minimum) return false;
    const field = form.querySelector(`[name="${fieldName}"]`);
    if (!field || field.disabled) return false;
    const existing = String(field.value || "").trim();
    if (existing && field.dataset.aiFilled !== "1") return false;
    const normalized = String(value);
    if (field.tagName === "SELECT" && !Array.from(field.options).some((option) => option.value === normalized)) return false;
    field.value = normalized;
    field.dispatchEvent(new Event("change", { bubbles: true }));
    field.dispatchEvent(new Event("input", { bubbles: true }));
    markSuggested(field, confidence);
    return true;
  };

  const appendDescriptionSections = (output, confidence, minimum) => {
    const description = form.querySelector('[name="description"]');
    if (!description || Number(confidence || 0) < minimum) return false;
    const sections = [];
    if ((output.detected_features || []).length) {
      sections.push(`Öne çıkan özellikler:\n${output.detected_features.map((item) => `• ${item}`).join("\n")}`);
    }
    if ((output.possible_defects || []).length) {
      sections.push(`Fotoğraflarda görülebilen kusurlar:\n${output.possible_defects.map((item) => `• ${item}`).join("\n")}`);
    }
    if (!sections.length) return false;
    const current = String(description.value || "").trim();
    const extra = sections.join("\n\n");
    if (!current.includes(extra)) description.value = [current, extra].filter(Boolean).join("\n\n");
    description.dispatchEvent(new Event("input", { bubbles: true }));
    markSuggested(description, confidence);
    return true;
  };

  const questionInput = (item, index) => {
    const field = escapeHtml(item.field || "");
    const question = escapeHtml(item.question || item);
    const required = item.required ? "required" : "";
    const options = Array.isArray(item.options) ? item.options : [];
    if (item.type === "choice" && options.length) {
      return `<label class="ai-question"><span>${question}</span><select data-ai-question-field="${field}" ${required}><option value="">Seçiniz</option>${options.map((option) => `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`).join("")}</select></label>`;
    }
    if (item.type === "boolean") {
      return `<label class="ai-question"><span>${question}</span><select data-ai-question-field="${field}" ${required}><option value="">Seçiniz</option><option value="Evet">Evet</option><option value="Hayır">Hayır</option></select></label>`;
    }
    return `<label class="ai-question"><span>${question}</span><input type="${item.type === "number" ? "number" : "text"}" data-ai-question-field="${field}" ${required} autocomplete="off"></label>`;
  };

  const questionValueMap = {
    kind: {
      "Ürün / Eşya": "product",
      "Araç": "vehicle",
      "Emlak": "real_estate",
      "Hizmet": "service",
      "İş": "job",
      "İhtiyaç / Arıyorum": "need",
    },
    action: {
      "Satmak": "sell",
      "Kiralama": "rent",
      "Kiralamak": "rent",
      "Takas": "swap",
      "Takas etmek": "swap",
      "Arıyorum": "wanted",
    },
    fuel_type: { Benzin: "gasoline", Dizel: "diesel", LPG: "lpg", Hibrit: "hybrid", Elektrik: "electric", Diğer: "other" },
    transmission: { Otomatik: "automatic", Manuel: "manual", "Yarı otomatik": "semi_automatic" },
    fee_type: { "Sabit ücret": "fixed", Saatlik: "hourly", Günlük: "daily", Aylık: "monthly", Görüşülür: "negotiable" },
    job_type: { "Tam zamanlı": "full_time", "Yarı zamanlı": "part_time", "Günlük / dönemsel": "daily", Uzaktan: "remote", Staj: "internship" },
  };

  const applyQuestionAnswers = () => {
    resultBox?.querySelectorAll("[data-ai-question-field]").forEach((answer) => {
      const fieldName = answer.dataset.aiQuestionField;
      const rawValue = String(answer.value || "").trim();
      if (!fieldName || !rawValue) return;
      const targetMap = { model: "model_name", tags: "search_tags_text", detected_features: "technical_features_text" };
      const targetName = targetMap[fieldName] || fieldName;
      const target = form.querySelector(`[name="${targetName}"]`);
      if (!target) return;
      const mapped = questionValueMap[fieldName]?.[rawValue] || rawValue;
      if (target.tagName === "SELECT" && !Array.from(target.options).some((option) => option.value === mapped)) return;
      target.value = mapped;
      target.dispatchEvent(new Event("change", { bubbles: true }));
      target.dispatchEvent(new Event("input", { bubbles: true }));
      markSuggested(target, 100);
    });
  };

  const openWizard = () => {
    document.querySelector('[data-v16-step="1"]')?.click();
    document.querySelector("[data-ai-wizard-start]")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const renderResult = (data) => {
    if (data.status === "blocked" || data.safety_status === "blocked") {
      setMessage("Güvenlik kontrolü nedeniyle bu fotoğraflardan ilan oluşturulmadı. Fotoğrafları değiştirebilir veya normal forma devam edebilirsin.", "error");
      return;
    }
    const output = data.result || {};
    if (analysisInput && data.analysis_id) analysisInput.value = data.analysis_id;
    const minimum = Number(data.minimum_confidence || 60);
    const fc = output.field_confidence || {};
    const technical = output.technical_attributes || {};
    let applied = 0;

    applied += applyValue("title", output.title, fc.title ?? output.confidence_score, minimum) ? 1 : 0;
    applied += applyValue("description", output.description, fc.description ?? output.confidence_score, minimum) ? 1 : 0;
    applied += applyValue("condition", output.condition, fc.condition ?? 0, minimum) ? 1 : 0;
    applied += applyValue("brand", output.brand, fc.brand ?? 0, minimum) ? 1 : 0;
    applied += applyValue("model_name", output.model, fc.model ?? 0, minimum) ? 1 : 0;
    applied += applyValue("color", output.color, fc.color ?? 0, minimum) ? 1 : 0;
    applied += applyValue("kind", output.kind, fc.category ?? output.confidence_score, minimum) ? 1 : 0;
    applied += applyValue("category", output.category_id, fc.category ?? output.confidence_score, minimum) ? 1 : 0;
    Object.entries(technical).forEach(([name, value]) => {
      applied += applyValue(name, value, fc[name] ?? output.confidence_score, minimum) ? 1 : 0;
    });
    if ((output.tags || []).length) applied += applyValue("search_tags_text", output.tags.join(", "), output.confidence_score, minimum) ? 1 : 0;
    if ((output.detected_features || []).length) applied += applyValue("technical_features_text", output.detected_features.join("\n"), output.confidence_score, minimum) ? 1 : 0;
    appendDescriptionSections(output, fc.description ?? output.confidence_score, minimum);

    const messages = [
      `<div class="ai-listing-message success"><b>İlan taslağın hazır.</b> ${applied ? `${applied} güvenli öneri forma yerleştirildi.` : "Düşük güvenli tahminler otomatik yazılmadı."} Şimdi fiyat, konum ve emin olunmayan alanları tamamla.</div>`,
    ];
    const visibleNotes = [
      output.color ? `Renk: ${escapeHtml(output.color)}` : "",
      ...(output.possible_defects || []).map((item) => `Görülen kusur: ${escapeHtml(item)}`),
    ].filter(Boolean);
    if (visibleNotes.length) messages.push(`<div class="ai-listing-message warning">${visibleNotes.join("<br>")}</div>`);
    const warnings = data.safety_warnings || [];
    if (warnings.length) messages.push(`<div class="ai-listing-message warning"><b>Dikkat:</b><br>${warnings.map(escapeHtml).join("<br>")}</div>`);
    const questions = data.missing_questions || [];
    if (questions.length) {
      messages.push(`<div class="ai-question-box"><b>AI'nin emin olamadığı bilgiler</b><div class="ai-question-grid">${questions.map(questionInput).join("")}</div><button type="button" data-ai-apply-answers>Cevapları forma uygula</button></div>`);
    }
    messages.push('<button type="button" class="ai-review-button" data-ai-review-form>Önerileri kontrol et →</button>');
    resultBox.innerHTML = messages.join("");
    resultBox.querySelector("[data-ai-apply-answers]")?.addEventListener("click", () => {
      applyQuestionAnswers();
      setStatus("Cevapların forma aktarıldı. İlan alanlarını kontrol et.", "success");
    });
    resultBox.querySelector("[data-ai-review-form]")?.addEventListener("click", openWizard);
    analysisCompleted = true;
    setStatus("Analiz tamamlandı. AI önerilerini adım adım kontrol et.", "success");
  };

  imageInput.addEventListener("change", () => {
    if (analysisCompleted && analysisInput) {
      analysisInput.value = "";
      analysisCompleted = false;
      setMessage("Fotoğraflar değişti. Güncel fotoğraflara göre yeniden analiz başlatabilirsin.", "warning");
    }
    updateState();
  });

  preview?.addEventListener("click", (event) => {
    const remove = event.target.closest("[data-ai-remove-image]");
    if (!remove) return;
    const index = Number(remove.dataset.aiRemoveImage);
    syncFileList(files().filter((_file, itemIndex) => itemIndex !== index));
  });

  clearButton?.addEventListener("click", () => syncFileList([]));

  ["dragenter", "dragover"].forEach((name) => dropZone?.addEventListener(name, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  }));
  ["dragleave", "drop"].forEach((name) => dropZone?.addEventListener(name, (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
  }));
  dropZone?.addEventListener("drop", (event) => {
    const incoming = Array.from(event.dataTransfer?.files || []).filter((file) => file.type.startsWith("image/"));
    if (incoming.length) syncFileList([...files(), ...incoming].slice(0, maxImages));
  });

  assistant.querySelector("[data-ai-manual-start]")?.addEventListener("click", openWizard);
  form.querySelector("[data-ai-scroll-upload]")?.addEventListener("click", () => assistant.scrollIntoView({ behavior: "smooth", block: "start" }));

  const formSnapshot = () => {
    const snapshot = {};
    ["kind", "action", "category", "condition", "brand", "model_name"].forEach((name) => {
      const value = String(form.querySelector(`[name="${name}"]`)?.value || "").trim();
      if (value) snapshot[name] = value;
    });
    return snapshot;
  };

  button?.addEventListener("click", async () => {
    const selected = files();
    const validation = validateFiles();
    if (!canAnalyze) {
      setMessage(lockedMessage, "error");
      return;
    }
    if (!validation.ok || !endpoint) return;
    button.disabled = true;
    progress.hidden = false;
    setStatus("Fotoğraflar inceleniyor, ilanınız hazırlanıyor…", "loading");
    resultBox.innerHTML = "";
    const payload = new FormData();
    selected.forEach((file) => payload.append("images", file));
    payload.append("request_id", globalThis.crypto?.randomUUID?.() || `ai-${Date.now()}-${Math.random().toString(16).slice(2)}`);
    payload.append("form_snapshot", JSON.stringify(formSnapshot()));
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
      setStatus("Yapay zekâ analizi tamamlanamadı. Form kullanılmaya devam edebilir.", "error");
    } finally {
      progress.hidden = true;
      updateState();
    }
  });

  updateState();
});
