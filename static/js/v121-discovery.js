/* İlan Şehri v1.21.0 — kategori, filtre, konum ve mobil keşif */
document.addEventListener("DOMContentLoaded", () => {
  const allowedActions = {
    product: ["sell", "rent", "swap", "wanted"],
    vehicle: ["sell", "rent", "swap", "wanted"],
    real_estate: ["sell", "rent", "wanted"],
    service: ["service_offer", "service_request"],
    need: ["wanted", "service_request"],
    job: ["job_offer", "job_request"],
  };

  const fillDatalist = (input, values) => {
    const listId = input?.getAttribute("list");
    const datalist = listId ? document.getElementById(listId) : null;
    if (!datalist) return;
    datalist.replaceChildren(...values.map((value) => {
      const option = document.createElement("option");
      option.value = value;
      return option;
    }));
  };

  document.querySelectorAll("[data-v121-location-form]").forEach((form) => {
    const city = form.querySelector("[data-v121-city]");
    const district = form.querySelector("[data-v121-district]");
    const neighborhood = form.querySelector("[data-v121-neighborhood]");
    const endpoint = form.dataset.locationUrl;
    if (!city || !endpoint) return;

    let requestId = 0;
    const load = async ({ resetDistrict = false, resetNeighborhood = false } = {}) => {
      if (resetDistrict && district) district.value = "";
      if ((resetDistrict || resetNeighborhood) && neighborhood) neighborhood.value = "";
      const currentRequest = ++requestId;
      const params = new URLSearchParams({
        city: city.value || "",
        district: district?.value || "",
      });
      try {
        const response = await fetch(`${endpoint}?${params}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!response.ok || currentRequest !== requestId) return;
        const payload = await response.json();
        fillDatalist(district, payload.districts || []);
        fillDatalist(neighborhood, payload.neighborhoods || []);
        district?.setAttribute("aria-description", payload.districts?.length
          ? `${payload.districts.length} ilçe önerisi hazır`
          : "İlçeyi yazabilirsiniz");
      } catch (_error) {
        // Katalogda olmayan konumlarda serbest giriş devam eder.
      }
    };

    city.addEventListener("change", () => load({ resetDistrict: true }));
    district?.addEventListener("change", () => load({ resetNeighborhood: true }));
    district?.addEventListener("blur", () => load());
    load();
  });

  const syncActionOptions = (kindSelect, actionSelect) => {
    if (!kindSelect || !actionSelect) return;
    const selectedKind = String(kindSelect.value || "");
    const allowed = allowedActions[selectedKind] || [];
    Array.from(actionSelect.options).forEach((option) => {
      if (!option.value) return;
      const visible = !selectedKind || allowed.includes(option.value);
      option.hidden = !visible;
      option.disabled = !visible;
    });
    if (selectedKind && actionSelect.value && !allowed.includes(actionSelect.value)) {
      actionSelect.value = "";
    }
  };

  const syncCategoryOptions = (kindSelect, categorySelect, { leavesOnly = false } = {}) => {
    if (!categorySelect) return;
    const selectedKind = String(kindSelect?.value || "");
    Array.from(categorySelect.options).forEach((option) => {
      if (!option.value) return;
      const optionKind = option.dataset.categoryKind || "";
      const kindMatches = !selectedKind || !optionKind || optionKind === selectedKind;
      const leafMatches = !leavesOnly || option.dataset.categoryLeaf !== "0";
      const visible = kindMatches && leafMatches;
      option.hidden = !visible;
      option.disabled = !visible;
    });
    const current = categorySelect.selectedOptions[0];
    if (current?.value && current.disabled) categorySelect.value = "";
  };

  document.querySelectorAll("[data-v121-filter-form]").forEach((form) => {
    const kind = form.querySelector("[data-v121-kind-filter]");
    const category = form.querySelector("[data-v121-category-filter]");
    const action = form.querySelector("[data-v121-action-filter]");
    const sync = () => {
      syncCategoryOptions(kind, category);
      syncActionOptions(kind, action);
    };
    kind?.addEventListener("change", sync);
    category?.addEventListener("change", () => {
      const optionKind = category.selectedOptions[0]?.dataset.categoryKind;
      if (optionKind && kind && !kind.value) {
        kind.value = optionKind;
        kind.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
    sync();
  });

  document.querySelectorAll("[data-listing-form]").forEach((form) => {
    const kind = form.querySelector("#id_kind");
    const category = form.querySelector("[data-category-select]");
    const action = form.querySelector("#id_action");
    const help = form.querySelector("[data-category-selection-help]");
    const sync = () => {
      syncCategoryOptions(kind, category, { leavesOnly: true });
      syncActionOptions(kind, action);
      if (help) {
        const selected = category?.selectedOptions[0];
        help.textContent = selected?.value
          ? `Seçilen kategori: ${selected.dataset.categoryPath || selected.textContent.trim()}`
          : kind?.value
            ? "Bu ilan türüne uygun bir alt kategori seç."
            : "Önce ilan türünü seç; kategori listesi otomatik daralacak.";
      }
    };
    kind?.addEventListener("change", sync);
    category?.addEventListener("change", sync);
    sync();
  });

  const activeFilters = document.querySelector(".v121-active-filters");
  if (activeFilters && window.matchMedia("(max-width: 780px)").matches) {
    const last = activeFilters.querySelector("a:not(.clear-all):last-of-type");
    window.requestAnimationFrame(() => last?.scrollIntoView({ block: "nearest", inline: "nearest" }));
  }

  const drawer = document.querySelector("[data-filter-panel]");
  const openButton = document.querySelector("[data-filter-open]");
  if (drawer && openButton) {
    openButton.addEventListener("click", () => {
      window.setTimeout(() => drawer.querySelector("select,input")?.focus({ preventScroll: true }), 220);
    });
  }
});
