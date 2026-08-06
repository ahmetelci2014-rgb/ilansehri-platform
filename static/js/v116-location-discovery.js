/* İlan Şehri v1.16.0/v1.17.0 — yakındaki ilanlar ve yaklaşık ilan konumu */
(() => {
  "use strict";

  const nearbyButtons = [...document.querySelectorAll("[data-nearby-search]")];
  const captureButton = document.querySelector("[data-listing-location-capture]");
  if (!nearbyButtons.length && !captureButton) return;

  function announce(message, tone = "info") {
    let box = document.querySelector("[data-location-feedback]");
    if (!box) {
      box = document.createElement("div");
      box.dataset.locationFeedback = "";
      box.className = "v116-location-feedback";
      box.setAttribute("role", "status");
      box.setAttribute("aria-live", "polite");
      document.body.appendChild(box);
    }
    box.dataset.tone = tone;
    box.textContent = message;
    box.hidden = false;
    window.clearTimeout(box._hideTimer);
    box._hideTimer = window.setTimeout(() => {
      box.hidden = true;
    }, 5200);
  }

  function targetUrl(button) {
    const configured = button.dataset.url || window.location.pathname;
    const isListingPage = window.location.pathname.includes("/ilanlar/") && !window.location.pathname.includes("/yeni/");
    const url = new URL(isListingPage ? window.location.href : configured, window.location.origin);
    url.searchParams.delete("page");
    return url;
  }

  function fallback(button) {
    const city = (button.dataset.fallbackCity || "").trim();
    const district = (button.dataset.fallbackDistrict || "").trim();
    if (city) {
      const url = targetUrl(button);
      url.searchParams.delete("lat");
      url.searchParams.delete("lng");
      url.searchParams.delete("radius");
      url.searchParams.delete("sort");
      url.searchParams.set("city", city);
      if (district) url.searchParams.set("district", district);
      announce("Konum izni verilmedi. Profilindeki şehir ve ilçe ile arama yapılıyor.", "warning");
      window.setTimeout(() => window.location.assign(url.toString()), 350);
      return;
    }
    announce("Konum izni verilmedi. Şehir seçerek yakındaki ilanları keşfedebilirsin.", "warning");
    const cityField = document.querySelector('[name="city"]');
    cityField?.focus();
    cityField?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function openNearby(button, position) {
    const url = targetUrl(button);
    url.searchParams.delete("city");
    url.searchParams.delete("district");
    url.searchParams.set("lat", position.coords.latitude.toFixed(3));
    url.searchParams.set("lng", position.coords.longitude.toFixed(3));
    url.searchParams.set("radius", button.dataset.radius || "25");
    url.searchParams.set("sort", "nearby");
    window.location.assign(url.toString());
  }

  nearbyButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (!navigator.geolocation) {
        fallback(button);
        return;
      }
      const original = button.innerHTML;
      button.disabled = true;
      button.classList.add("is-locating");
      button.innerHTML = '<span class="v116-location-spinner" aria-hidden="true"></span><span>Konum bulunuyor…</span>';
      navigator.geolocation.getCurrentPosition(
        (position) => openNearby(button, position),
        () => {
          button.disabled = false;
          button.classList.remove("is-locating");
          button.innerHTML = original;
          fallback(button);
        },
        { enableHighAccuracy: false, timeout: 9000, maximumAge: 300000 },
      );
    });
  });

  if (captureButton) {
    const latitudeField = document.querySelector("[data-listing-latitude]");
    const longitudeField = document.querySelector("[data-listing-longitude]");
    const status = document.querySelector("[data-listing-location-status]");
    const original = captureButton.innerHTML;

    const restore = () => {
      captureButton.disabled = false;
      captureButton.classList.remove("is-locating");
      captureButton.innerHTML = original;
    };

    captureButton.addEventListener("click", () => {
      if (!latitudeField || !longitudeField) {
        announce("Konum alanları yüklenemedi. Sayfayı yenileyip yeniden dene.", "warning");
        return;
      }
      if (!navigator.geolocation) {
        if (status) status.textContent = "Bu tarayıcı konum özelliğini desteklemiyor";
        announce("Tarayıcın konum paylaşımını desteklemiyor.", "warning");
        return;
      }

      captureButton.disabled = true;
      captureButton.classList.add("is-locating");
      captureButton.innerHTML = '<span class="v116-location-spinner" aria-hidden="true"></span><span>Konum alınıyor…</span>';
      if (status) status.textContent = "Konum izni bekleniyor…";

      navigator.geolocation.getCurrentPosition(
        (position) => {
          latitudeField.value = position.coords.latitude.toFixed(3);
          longitudeField.value = position.coords.longitude.toFixed(3);
          latitudeField.dispatchEvent(new Event("change", { bubbles: true }));
          longitudeField.dispatchEvent(new Event("change", { bubbles: true }));
          if (status) status.textContent = "Yaklaşık konum eklendi";
          captureButton.innerHTML = "✓ Yaklaşık konum eklendi";
          captureButton.classList.remove("is-locating");
          captureButton.classList.add("is-captured");
          captureButton.disabled = false;
          announce("Yaklaşık konum ilana eklendi. Açık adres paylaşılmayacak.");
        },
        () => {
          restore();
          if (status) status.textContent = "Konum izni alınamadı; şehir ve ilçe yeterlidir";
          announce("Konum eklenemedi. Şehir ve ilçe bilgileriyle devam edebilirsin.", "warning");
        },
        { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
      );
    });
  }
})();
