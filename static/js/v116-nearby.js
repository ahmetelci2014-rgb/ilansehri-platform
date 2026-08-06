/* İlan Şehri v1.16.0 — yakındaki ilanlar ve ilan konumu */
(() => {
  "use strict";

  const GEO_OPTIONS = {
    enableHighAccuracy: false,
    timeout: 12000,
    maximumAge: 300000,
  };

  const errorMessage = (error) => {
    if (!error) return "Konum alınamadı. Lütfen yeniden dene.";
    if (error.code === 1) return "Konum izni verilmedi. Tarayıcı adres çubuğundan konum iznini açabilirsin.";
    if (error.code === 2) return "Cihaz konumu belirleyemedi. İnternet ve konum servislerini kontrol et.";
    if (error.code === 3) return "Konum isteği zaman aşımına uğradı. Yeniden dene.";
    return "Konum alınamadı. Lütfen yeniden dene.";
  };

  const requestPosition = (onSuccess, onError) => {
    if (!("geolocation" in navigator)) {
      onError({ code: 0 });
      return;
    }
    navigator.geolocation.getCurrentPosition(onSuccess, onError, GEO_OPTIONS);
  };

  const initializeNearbyDiscovery = () => {
    const panel = document.querySelector("[data-nearby-discovery]");
    if (!panel) return;

    const runButton = panel.querySelector("[data-nearby-run]");
    const radius = panel.querySelector("[data-nearby-radius]");
    const status = panel.querySelector("[data-nearby-status]");
    const sessionForm = panel.querySelector("[data-nearby-session-form]");
    if (!runButton || !radius || !status || !sessionForm) return;

    runButton.addEventListener("click", () => {
      runButton.disabled = true;
      runButton.setAttribute("aria-busy", "true");
      status.textContent = "Konumun alınıyor…";
      panel.classList.remove("has-error");

      requestPosition(
        async (position) => {
          const body = new FormData(sessionForm);
          body.set("latitude", Number(position.coords.latitude).toFixed(4));
          body.set("longitude", Number(position.coords.longitude).toFixed(4));
          body.set("radius", radius.value || "25");
          body.set("area_city", panel.dataset.fallbackCity || "");
          body.set("area_district", panel.dataset.fallbackDistrict || "");

          try {
            const response = await fetch(sessionForm.action, {
              method: "POST",
              body,
              credentials: "same-origin",
              headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const payload = await response.json();
            if (!response.ok || !payload.ok) throw new Error(payload.message || "Konum kaydedilemedi.");

            const url = new URL(window.location.href);
            url.searchParams.set("nearby", "1");
            url.searchParams.set("radius", String(payload.radius_km || radius.value || "25"));
            url.searchParams.set("sort", "distance");
            ["lat", "lon", "area_city", "area_district", "page"].forEach((key) => url.searchParams.delete(key));
            status.textContent = "Yakındaki ilanlar hazırlanıyor…";
            window.location.assign(url.toString());
          } catch (error) {
            panel.classList.add("has-error");
            status.textContent = error.message || "Konum kaydedilemedi. Yeniden dene.";
            runButton.disabled = false;
            runButton.removeAttribute("aria-busy");
          }
        },
        (error) => {
          panel.classList.add("has-error");
          status.textContent = errorMessage(error);
          runButton.disabled = false;
          runButton.removeAttribute("aria-busy");
        }
      );
    });
  };

  const initializeListingLocation = () => {
    const box = document.querySelector("[data-listing-location-box]");
    if (!box) return;

    const latitude = document.querySelector("[data-listing-latitude]");
    const longitude = document.querySelector("[data-listing-longitude]");
    const capture = box.querySelector("[data-listing-location-capture]");
    const clear = box.querySelector("[data-listing-location-clear]");
    const status = box.querySelector("[data-listing-location-status]");
    if (!latitude || !longitude || !capture || !clear || !status) return;

    const markSet = () => {
      box.classList.add("is-set");
      capture.textContent = "Konumu yenile";
      clear.hidden = false;
      status.textContent = "Konum işaretlendi. Tam koordinatlar ilan sayfasında gösterilmez.";
    };

    capture.addEventListener("click", () => {
      capture.disabled = true;
      capture.setAttribute("aria-busy", "true");
      status.textContent = "Konumun alınıyor…";
      box.classList.remove("has-error");

      requestPosition(
        (position) => {
          latitude.value = Number(position.coords.latitude).toFixed(4);
          longitude.value = Number(position.coords.longitude).toFixed(4);
          markSet();
          capture.disabled = false;
          capture.removeAttribute("aria-busy");
          latitude.dispatchEvent(new Event("change", { bubbles: true }));
          longitude.dispatchEvent(new Event("change", { bubbles: true }));
        },
        (error) => {
          box.classList.add("has-error");
          status.textContent = errorMessage(error);
          capture.disabled = false;
          capture.removeAttribute("aria-busy");
        }
      );
    });

    clear.addEventListener("click", () => {
      latitude.value = "";
      longitude.value = "";
      box.classList.remove("is-set", "has-error");
      capture.textContent = "Konumumu işaretle";
      clear.hidden = true;
      status.textContent = "Konum kaldırıldı; ilan şehir ve ilçe bilgisiyle bulunmaya devam eder.";
      latitude.dispatchEvent(new Event("change", { bubbles: true }));
      longitude.dispatchEvent(new Event("change", { bubbles: true }));
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    initializeNearbyDiscovery();
    initializeListingLocation();
  });
})();
