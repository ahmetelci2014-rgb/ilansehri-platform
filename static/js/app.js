document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector("[data-menu-toggle]");
  const menu = document.querySelector("[data-mobile-menu]");
  if (toggle && menu) {
    toggle.addEventListener("click", () => {
      const open = menu.classList.toggle("is-open");
      toggle.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", String(open));
      document.body.classList.toggle("menu-open", open);
    });
  }

  const header = document.querySelector("[data-header]");
  const updateHeader = () => header?.classList.toggle("is-scrolled", window.scrollY > 12);
  updateHeader();
  window.addEventListener("scroll", updateHeader, { passive: true });

  const imageInput = document.querySelector("[data-image-input]");
  const preview = document.querySelector("[data-image-preview]");
  if (imageInput && preview && !imageInput.closest("[data-ai-quick-start]")) {
    imageInput.addEventListener("change", () => {
      preview.innerHTML = "";
      Array.from(imageInput.files || []).slice(0, 10).forEach((file, index) => {
        if (!file.type.startsWith("image/")) return;
        const reader = new FileReader();
        reader.addEventListener("load", () => {
          const item = document.createElement("div");
          item.className = "image-preview-item";
          item.innerHTML = `<img alt="Seçilen fotoğraf ${index + 1}"><span>${index === 0 ? "Yeni kapak adayı" : index + 1}</span>`;
          item.querySelector("img").src = reader.result;
          preview.appendChild(item);
          if (index === 0) {
            const liveMedia = document.querySelector("[data-preview-media]");
            if (liveMedia) {
              const liveImage = document.createElement("img");
              liveImage.src = reader.result;
              liveImage.alt = "İlan fotoğrafı önizlemesi";
              liveMedia.replaceChildren(liveImage);
            }
          }
        });
        reader.readAsDataURL(file);
      });
    });
  }

  const mainImage = document.querySelector("[data-main-image]");
  document.querySelectorAll("[data-gallery-thumb]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!mainImage) return;
      mainImage.src = button.dataset.galleryThumb;
      document.querySelectorAll("[data-gallery-thumb]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
    });
  });

  const listingForm = document.querySelector("[data-listing-form]");
  const kindSelect = listingForm?.querySelector("#id_kind");
  const actionSelect = listingForm?.querySelector("#id_action");
  const fieldKinds = {
    condition: ["product", "vehicle"], brand: ["product", "vehicle"], model_name: ["product", "vehicle"],
    color: ["product", "vehicle", "real_estate"],
    search_tags_text: ["product", "vehicle", "real_estate", "service", "need", "job"],
    technical_features_text: ["product", "vehicle", "real_estate", "service", "need", "job"],
    model_year: ["vehicle"], mileage: ["vehicle"], fuel_type: ["vehicle"], transmission: ["vehicle"],
    room_count: ["real_estate"], area_m2: ["real_estate"], building_age: ["real_estate"], floor_location: ["real_estate"], heating_type: ["real_estate"],
    service_area: ["service"], fee_type: ["service"], job_type: ["job"], experience_level: ["job"],
  };
  const allowedActions = {
    product: ["sell", "rent", "swap", "wanted"], vehicle: ["sell", "rent", "swap", "wanted"],
    real_estate: ["sell", "rent", "wanted"], service: ["service_offer", "service_request"],
    need: ["wanted", "service_request"], job: ["job_offer", "job_request"],
  };
  const updateKindFields = () => {
    const selected = kindSelect?.value || "";
    listingForm?.querySelectorAll("[data-kind-field]").forEach((wrapper) => {
      const name = wrapper.dataset.kindField;
      const visible = (fieldKinds[name] || []).includes(selected);
      wrapper.hidden = !visible;
      wrapper.querySelectorAll("input,select,textarea").forEach((field) => { field.disabled = !visible; });
    });
    if (actionSelect && selected) {
      const allowed = allowedActions[selected] || [];
      Array.from(actionSelect.options).forEach((option) => {
        if (!option.value) return;
        option.hidden = !allowed.includes(option.value);
        option.disabled = !allowed.includes(option.value);
      });
      if (actionSelect.value && !allowed.includes(actionSelect.value)) actionSelect.value = "";
    }
  };
  if (kindSelect) {
    updateKindFields();
    kindSelect.addEventListener("change", updateKindFields);
  }

  const cityInput = listingForm?.querySelector("[data-location-city]");
  const districtInput = listingForm?.querySelector("[data-location-district]");
  const neighborhoodInput = listingForm?.querySelector("[data-location-neighborhood]");
  const districtOptions = document.querySelector("#district-options");
  const neighborhoodOptions = document.querySelector("#neighborhood-options");
  const locationUrl = listingForm?.dataset.locationUrl;
  const fillDatalist = (element, values) => {
    if (!element) return;
    element.innerHTML = "";
    values.forEach((value) => {
      const option = document.createElement("option"); option.value = value; element.appendChild(option);
    });
  };
  const loadLocations = async ({ clearDistrict = false } = {}) => {
    if (!locationUrl || !cityInput) return;
    if (clearDistrict && districtInput) { districtInput.value = ""; if (neighborhoodInput) neighborhoodInput.value = ""; }
    const params = new URLSearchParams({ city: cityInput.value || "", district: districtInput?.value || "" });
    try {
      const response = await fetch(`${locationUrl}?${params.toString()}`, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!response.ok) return;
      const data = await response.json();
      fillDatalist(districtOptions, data.districts || []); fillDatalist(neighborhoodOptions, data.neighborhoods || []);
    } catch (_error) { /* Serbest giriş devam eder. */ }
  };
  if (cityInput) { loadLocations(); cityInput.addEventListener("change", () => loadLocations({ clearDistrict: true })); }
  districtInput?.addEventListener("change", () => loadLocations());
  districtInput?.addEventListener("blur", () => loadLocations());

  const sortable = document.querySelector("[data-sortable-images]");
  const orderInput = document.querySelector("[data-image-order]");
  const orderSubmit = document.querySelector("[data-image-order-submit]");
  if (sortable && orderInput) {
    let dragged = null;
    const syncImageOrder = () => {
      orderInput.value = Array.from(sortable.querySelectorAll("[data-image-id]")).map((item) => item.dataset.imageId).join(",");
    };
    sortable.querySelectorAll("[data-image-id]").forEach((item) => {
      item.draggable = true;
      item.addEventListener("dragstart", () => { dragged = item; item.classList.add("dragging"); });
      item.addEventListener("dragend", () => { dragged = null; item.classList.remove("dragging"); syncImageOrder(); });
      item.addEventListener("dragover", (event) => {
        event.preventDefault();
        if (!dragged || dragged === item) return;
        const box = item.getBoundingClientRect();
        sortable.insertBefore(dragged, event.clientX < box.left + box.width / 2 ? item : item.nextSibling);
      });
    });
    orderSubmit?.addEventListener("click", syncImageOrder);
    syncImageOrder();
  }

  document.querySelectorAll(".message").forEach((message) => {
    window.setTimeout(() => message.classList.add("fade-out"), 5000);
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const filterPanel = document.querySelector("[data-filter-panel]");
  const filterOverlay = document.querySelector("[data-filter-overlay]");
  const openFilter = () => {
    filterPanel?.classList.add("is-open");
    filterOverlay?.classList.add("is-open");
    document.body.classList.add("menu-open");
  };
  const closeFilter = () => {
    filterPanel?.classList.remove("is-open");
    filterOverlay?.classList.remove("is-open");
    document.body.classList.remove("menu-open");
  };
  document.querySelector("[data-filter-open]")?.addEventListener("click", openFilter);
  document.querySelector("[data-filter-close]")?.addEventListener("click", closeFilter);
  filterOverlay?.addEventListener("click", closeFilter);

  const gallery = document.querySelector("[data-gallery-lightbox]");
  const lightboxImage = gallery?.querySelector("[data-lightbox-image]");
  const mainImage = document.querySelector("[data-main-image]");
  const openGallery = () => {
    if (!gallery || !lightboxImage || !mainImage?.src) return;
    lightboxImage.src = mainImage.src;
    gallery.hidden = false;
    document.body.classList.add("menu-open");
  };
  document.querySelector("[data-gallery-open]")?.addEventListener("click", (event) => {
    if (event.target.closest("button,a")) return;
    openGallery();
  });
  gallery?.querySelector("[data-gallery-close]")?.addEventListener("click", () => {
    gallery.hidden = true;
    document.body.classList.remove("menu-open");
  });
  gallery?.addEventListener("click", (event) => {
    if (event.target === gallery) {
      gallery.hidden = true;
      document.body.classList.remove("menu-open");
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && gallery && !gallery.hidden) {
      gallery.hidden = true;
      document.body.classList.remove("menu-open");
    }
  });

  const actionDetails = document.querySelectorAll(".market-action-box");
  document.querySelector("[data-open-offer]")?.addEventListener("click", () => {
    const box = actionDetails[0];
    if (!box) return;
    box.open = true;
    box.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  document.querySelector("[data-open-message]")?.addEventListener("click", (event) => {
    event.preventDefault();
    const box = actionDetails[1];
    if (!box) return;
    box.open = true;
    box.scrollIntoView({ behavior: "smooth", block: "center" });
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const chatThread = document.querySelector("[data-chat-thread]");
  if (chatThread) chatThread.scrollTop = chatThread.scrollHeight;

  document.querySelectorAll(".counter-offer-box").forEach((details) => {
    details.addEventListener("toggle", () => {
      if (!details.open) return;
      document.querySelectorAll(".counter-offer-box").forEach((other) => {
        if (other !== details) other.open = false;
      });
    });
  });
});

/* v1.4 — menü ve responsive davranış düzeltmeleri */
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector("[data-menu-toggle]");
  const menu = document.querySelector("[data-mobile-menu]");
  const filterPanel = document.querySelector("[data-filter-panel]");
  const filterOverlay = document.querySelector("[data-filter-overlay]");

  const closeMenu = () => {
    if (!toggle || !menu) return;
    menu.classList.remove("is-open");
    toggle.classList.remove("is-open");
    toggle.setAttribute("aria-expanded", "false");
    if (!filterPanel?.classList.contains("is-open")) document.body.classList.remove("menu-open");
  };

  menu?.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    closeMenu();
    filterPanel?.classList.remove("is-open");
    filterOverlay?.classList.remove("is-open");
    document.body.classList.remove("menu-open");
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 780) closeMenu();
  }, { passive: true });

  document.querySelectorAll("details.counter-offer-box").forEach((details) => {
    details.querySelector("form")?.addEventListener("click", (event) => event.stopPropagation());
  });
});


/* v1.5 — arama önerileri ve ilan oluşturma deneyimi */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-search-suggest]").forEach((form) => {
    const input = form.querySelector("[data-search-input]");
    const panel = form.querySelector("[data-search-results]");
    const endpoint = form.dataset.searchUrl;
    if (!input || !panel || !endpoint) return;

    let timer;
    let controller;
    const close = () => { panel.hidden = true; panel.replaceChildren(); };
    const render = (items) => {
      panel.replaceChildren();
      if (!items.length) { close(); return; }
      items.forEach((item) => {
        const link = document.createElement("a");
        link.href = item.url;
        link.className = `search-suggestion-item type-${item.type || "query"}`;
        const icon = document.createElement("span");
        icon.textContent = item.type === "listing" ? "▣" : item.type === "category" ? "⌘" : "⌕";
        const copy = document.createElement("div");
        const label = document.createElement("b");
        label.textContent = item.label;
        const meta = document.createElement("small");
        meta.textContent = item.meta || "";
        copy.append(label, meta);
        link.append(icon, copy);
        panel.append(link);
      });
      panel.hidden = false;
    };
    input.addEventListener("input", () => {
      window.clearTimeout(timer);
      const query = input.value.trim();
      if (query.length < 2) { controller?.abort(); close(); return; }
      timer = window.setTimeout(async () => {
        controller?.abort();
        controller = new AbortController();
        try {
          const response = await fetch(`${endpoint}?q=${encodeURIComponent(query)}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
            signal: controller.signal,
          });
          if (!response.ok) throw new Error("search failed");
          const data = await response.json();
          render(Array.isArray(data.results) ? data.results : []);
        } catch (error) {
          if (error.name !== "AbortError") close();
        }
      }, 220);
    });
    input.addEventListener("focus", () => {
      if (panel.childElementCount) panel.hidden = false;
    });
    document.addEventListener("click", (event) => {
      if (!form.contains(event.target)) close();
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") close();
    });
  });

  const listingForm = document.querySelector("[data-listing-form]");
  const progress = document.querySelector("[data-listing-progress]");
  if (!listingForm || !progress) return;

  const percent = progress.querySelector("[data-progress-percent]");
  const bar = progress.querySelector("[data-progress-bar]");
  const label = progress.querySelector("[data-progress-label]");
  const sections = Array.from(listingForm.querySelectorAll("[data-form-step]"));
  const links = Array.from(progress.querySelectorAll("[data-step-link]"));
  const required = Array.from(listingForm.querySelectorAll("input[required], select[required], textarea[required]"));

  const valueOf = (selector) => listingForm.querySelector(selector)?.value?.trim() || "";
  const updatePreview = () => {
    const title = valueOf("#id_title") || "İlan başlığın";
    const price = valueOf("#id_price");
    const requestPrice = listingForm.querySelector("#id_price_on_request")?.checked;
    const kindSelect = listingForm.querySelector("#id_kind");
    const kind = kindSelect?.selectedOptions?.[0]?.textContent || "İlan türü";
    const city = valueOf("#id_city");
    const district = valueOf("#id_district");
    document.querySelector("[data-preview-title]")?.replaceChildren(document.createTextNode(title));
    document.querySelector("[data-preview-price]")?.replaceChildren(document.createTextNode(requestPrice ? "Teklif alıyor" : price ? `${Number(price).toLocaleString("tr-TR")} TL` : "Fiyat"));
    document.querySelector("[data-preview-kind]")?.replaceChildren(document.createTextNode(kind));
    document.querySelector("[data-preview-location]")?.replaceChildren(document.createTextNode([city, district].filter(Boolean).join(" · ") || "Şehir · İlçe"));
  };

  const updateProgress = () => {
    const visibleRequired = required.filter((field) => field.offsetParent !== null && !field.disabled);
    const completed = visibleRequired.filter((field) => field.type === "checkbox" ? field.checked : Boolean(field.value.trim())).length;
    const total = Math.max(visibleRequired.length, 1);
    const value = Math.min(100, Math.round((completed / total) * 100));
    if (percent) percent.textContent = `${value}%`;
    if (bar) bar.style.width = `${value}%`;
    if (label) label.textContent = value >= 100 ? "İlanın yayınlanmaya hazır" : value >= 70 ? "Son kontrolleri tamamla" : value >= 35 ? "İlanın şekilleniyor" : "Temel bilgileri doldur";
    updatePreview();
  };

  listingForm.addEventListener("input", updateProgress);
  listingForm.addEventListener("change", updateProgress);
  links.forEach((link) => link.addEventListener("click", () => {
    links.forEach((item) => item.classList.remove("active"));
    link.classList.add("active");
  }));
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      const step = visible.target.dataset.formStep;
      links.forEach((link) => link.classList.toggle("active", link.dataset.stepLink === step));
    }, { rootMargin: "-25% 0px -60%", threshold: [0.05, 0.4] });
    sections.forEach((section) => observer.observe(section));
  }
  updateProgress();
});
