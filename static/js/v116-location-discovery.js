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
    const cityField = document.querySelector("[data-location-city]");
    const districtField = document.querySelector("[data-location-district]");
    const neighborhoodField = document.querySelector("[data-location-neighborhood]");
    const status = document.querySelector("[data-listing-location-status]");
    const attribution = document.querySelector("[data-listing-location-attribution]");
    const reverseUrl = captureButton.dataset.reverseUrl || "";
    const original = captureButton.innerHTML;

    const restore = () => {
      captureButton.disabled = false;
      captureButton.classList.remove("is-locating");
      captureButton.innerHTML = original;
    };

    const setCapturedButton = (withAddress) => {
      captureButton.disabled = false;
      captureButton.classList.remove("is-locating");
      captureButton.classList.add("is-captured");
      captureButton.innerHTML = withAddress
        ? "✓ Konum ve adres eklendi"
        : "✓ Yaklaşık konum eklendi";
    };

    const fillAddress = (data) => {
      if (data.city && cityField) {
        cityField.value = data.city;

        // Mevcut ilçe öneri sistemi yeni şehri görsün.
        // Bu event ilçe alanını senkron olarak temizlediği için
        // ilçe ve mahalle değerlerini bundan sonra yazıyoruz.
        cityField.dispatchEvent(
          new Event("change", { bubbles: true }),
        );
      }

      if (data.district && districtField) {
        districtField.value = data.district;
        districtField.dispatchEvent(
          new Event("change", { bubbles: true }),
        );
      }

      if (data.neighborhood && neighborhoodField) {
        neighborhoodField.value = data.neighborhood;
        neighborhoodField.dispatchEvent(
          new Event("change", { bubbles: true }),
        );
      }
    };

    const reverseAddress = async (position) => {
      if (!reverseUrl) {
        throw new Error("Adres çözümleme bağlantısı bulunamadı.");
      }

      const url = new URL(reverseUrl, window.location.origin);

      // Adres çözümü için kısa süreli daha hassas koordinat kullanılır.
      // İlanın kendisine aşağıda yalnız yaklaşık koordinat kaydedilir.
      url.searchParams.set(
        "lat",
        position.coords.latitude.toFixed(5),
      );
      url.searchParams.set(
        "lng",
        position.coords.longitude.toFixed(5),
      );

      const response = await fetch(url.toString(), {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Accept": "application/json",
        },
        credentials: "same-origin",
      });

      let data = {};
      try {
        data = await response.json();
      } catch (_error) {
        // Aşağıdaki ortak hata mesajı kullanılacak.
      }

      if (!response.ok) {
        throw new Error(
          data.error || "Adres otomatik bulunamadı.",
        );
      }

      return data;
    };

    captureButton.addEventListener("click", () => {
      if (!latitudeField || !longitudeField) {
        announce(
          "Konum alanları yüklenemedi. Sayfayı yenileyip yeniden dene.",
          "warning",
        );
        return;
      }

      if (!navigator.geolocation) {
        if (status) {
          status.textContent =
            "Bu tarayıcı konum özelliğini desteklemiyor";
        }
        announce(
          "Tarayıcın konum paylaşımını desteklemiyor.",
          "warning",
        );
        return;
      }

      captureButton.disabled = true;
      captureButton.classList.add("is-locating");
      captureButton.innerHTML =
        '<span class="v116-location-spinner" aria-hidden="true"></span>'
        + "<span>Konum bulunuyor…</span>";

      if (status) {
        status.textContent =
          "Konum izni bekleniyor…";
      }

      navigator.geolocation.getCurrentPosition(
        async (position) => {
          // Veritabanına yaklaşık konum: ~100 metre ölçeğinde.
          latitudeField.value =
            position.coords.latitude.toFixed(3);
          longitudeField.value =
            position.coords.longitude.toFixed(3);

          latitudeField.dispatchEvent(
            new Event("change", { bubbles: true }),
          );
          longitudeField.dispatchEvent(
            new Event("change", { bubbles: true }),
          );

          if (status) {
            status.textContent =
              "Konum bulundu, il / ilçe / mahalle belirleniyor…";
          }

          try {
            const data = await reverseAddress(position);
            fillAddress(data);

            const parts = [
              data.city,
              data.district,
              data.neighborhood,
            ].filter(Boolean);

            if (status) {
              status.textContent = parts.length
                ? `${parts.join(" / ")} otomatik seçildi`
                : "Yaklaşık konum eklendi";
            }

            if (attribution && data.attribution) {
              attribution.textContent =
                `Adres eşleştirme: ${data.attribution}`;
            }

            setCapturedButton(true);

            announce(
              parts.length
                ? `Konum bulundu: ${parts.join(" / ")}. Bilgileri kontrol edebilirsin.`
                : "Yaklaşık konum ilana eklendi.",
            );
          } catch (error) {
            setCapturedButton(false);

            if (status) {
              status.textContent =
                "Konum bulundu; adres alanlarını kontrol ederek tamamla";
            }

            announce(
              error?.message
                || "Konum bulundu ancak adres otomatik doldurulamadı.",
              "warning",
            );
          }
        },
        () => {
          restore();

          if (status) {
            status.textContent =
              "Konum izni alınamadı; il ve ilçe bilgilerini elle seçebilirsin";
          }

          announce(
            "Konum izni alınamadı. İl, ilçe ve mahalleyi elle seçebilirsin.",
            "warning",
          );
        },
        {
          enableHighAccuracy: true,
          timeout: 12000,
          maximumAge: 60000,
        },
      );
    });
  }
})();
