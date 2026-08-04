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
  if (imageInput && preview) {
    imageInput.addEventListener("change", () => {
      preview.innerHTML = "";
      Array.from(imageInput.files || []).slice(0, 10).forEach((file, index) => {
        if (!file.type.startsWith("image/")) return;
        const reader = new FileReader();
        reader.addEventListener("load", () => {
          const item = document.createElement("div");
          item.className = "image-preview-item";
          item.innerHTML = `<img alt="Seçilen fotoğraf ${index + 1}"><span>${index === 0 ? "Kapak" : index + 1}</span>`;
          item.querySelector("img").src = reader.result;
          preview.appendChild(item);
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

  const chatMessages = document.querySelector("[data-chat-messages]");
  if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;

  // İlan türüne göre kategoriye özel alanlar.
  const listingForm = document.querySelector("[data-listing-form]");
  const kindSelect = listingForm?.querySelector("#id_kind");
  const actionSelect = listingForm?.querySelector("#id_action");
  const kindGroups = listingForm?.querySelectorAll("[data-kind-group]") || [];
  const kindEmpty = listingForm?.querySelector("[data-kind-empty]");
  const updateKindGroups = () => {
    const selectedKind = kindSelect?.value || "";
    let visibleCount = 0;
    kindGroups.forEach((group) => {
      const kinds = (group.dataset.kindGroup || "").split(",");
      const visible = kinds.includes(selectedKind);
      group.classList.toggle("is-visible", visible);
      group.querySelectorAll("input, select, textarea").forEach((field) => {
        field.disabled = !visible;
      });
      if (visible) visibleCount += 1;
    });
    kindEmpty?.classList.toggle("is-hidden", visibleCount > 0 || selectedKind === "need");

    const allowedActions = {
      product: ["sell", "rent", "swap", "wanted"],
      vehicle: ["sell", "rent", "swap", "wanted"],
      real_estate: ["sell", "rent", "wanted"],
      service: ["service_offer", "service_request"],
      need: ["wanted", "service_request"],
      job: ["job_offer", "job_request"],
    };
    if (actionSelect && selectedKind) {
      const allowed = allowedActions[selectedKind] || [];
      Array.from(actionSelect.options).forEach((option) => {
        if (!option.value) return;
        option.hidden = !allowed.includes(option.value);
        option.disabled = !allowed.includes(option.value);
      });
      if (actionSelect.value && !allowed.includes(actionSelect.value)) {
        actionSelect.value = "";
      }
    }
  };
  if (kindSelect) {
    updateKindGroups();
    kindSelect.addEventListener("change", updateKindGroups);
  }

  // Şehir → ilçe → mahalle önerileri. Alanlar serbest yazmaya devam eder.
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
      const option = document.createElement("option");
      option.value = value;
      element.appendChild(option);
    });
  };

  const loadLocations = async ({ clearDistrict = false } = {}) => {
    if (!locationUrl || !cityInput) return;
    if (clearDistrict && districtInput) {
      districtInput.value = "";
      if (neighborhoodInput) neighborhoodInput.value = "";
    }
    const params = new URLSearchParams({
      city: cityInput.value || "",
      district: districtInput?.value || "",
    });
    try {
      const response = await fetch(`${locationUrl}?${params.toString()}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!response.ok) return;
      const data = await response.json();
      fillDatalist(districtOptions, data.districts || []);
      fillDatalist(neighborhoodOptions, data.neighborhoods || []);
    } catch (_error) {
      // Konum önerileri yüklenemezse kullanıcı alanlara serbestçe yazabilir.
    }
  };

  if (cityInput) {
    loadLocations();
    cityInput.addEventListener("change", () => loadLocations({ clearDistrict: true }));
  }
  districtInput?.addEventListener("change", () => loadLocations());
  districtInput?.addEventListener("blur", () => loadLocations());
});
