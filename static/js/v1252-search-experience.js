(() => {
  "use strict";

  const STORAGE_KEY = "ilansehri_recent_searches_v1";
  const MAX_ITEMS = 6;

  const readRecent = () => {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      return Array.isArray(value)
        ? value.filter((item) => typeof item === "string" && item.trim()).slice(0, MAX_ITEMS)
        : [];
    } catch (_error) {
      return [];
    }
  };

  const writeRecent = (items) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, MAX_ITEMS)));
    } catch (_error) {
      // Tarayıcı depolaması kapalıysa arama normal çalışmaya devam eder.
    }
  };

  const remember = (query) => {
    const value = String(query || "").trim().slice(0, 80);
    if (!value) return;

    const items = readRecent().filter(
      (item) => item.toLocaleLowerCase("tr-TR") !== value.toLocaleLowerCase("tr-TR"),
    );

    items.unshift(value);
    writeRecent(items);
  };

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-search-suggest]").forEach((form) => {
      const input = form.querySelector("[data-search-input]");
      const panel = form.querySelector("[data-search-results]");

      if (!input || !panel) return;

      const renderRecent = () => {
        if (input.value.trim()) return;

        const recent = readRecent();

        panel.replaceChildren();

        if (!recent.length) {
          panel.hidden = true;
          return;
        }

        const header = document.createElement("div");
        header.className = "v1252-search-recent-head";

        const title = document.createElement("b");
        title.textContent = "Son aramalar";

        const clear = document.createElement("button");
        clear.type = "button";
        clear.textContent = "Temizle";

        clear.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          writeRecent([]);
          panel.hidden = true;
          panel.replaceChildren();
          input.focus();
        });

        header.append(title, clear);
        panel.append(header);

        const locationLabel = String(
          form.dataset.searchLocation || "",
        ).trim();

        recent.forEach((query) => {
          const link = document.createElement("a");

          const url = new URL(
            form.action || "/ilanlar/",
            window.location.origin,
          );

          url.searchParams.set("q", query);

          link.href = url.toString();
          link.className =
            "search-suggestion-item type-query v1252-recent-search";

          const icon = document.createElement("span");
          icon.textContent = "↺";

          const copy = document.createElement("div");

          const label = document.createElement("b");
          label.textContent = query;

          const meta = document.createElement("small");

          if (locationLabel && locationLabel !== "Tüm Türkiye") {
            meta.textContent = `${locationLabel} içinde tekrar ara`;
          } else {
            meta.textContent = "Tekrar ara";
          }

          copy.append(label, meta);
          link.append(icon, copy);

          link.addEventListener("click", () => remember(query));

          panel.append(link);
        });

        panel.hidden = false;
      };

      form.addEventListener("submit", () => {
        remember(input.value);
      });

      input.addEventListener("focus", () => {
        window.setTimeout(renderRecent, 0);
      });

      input.addEventListener("input", () => {
        if (!input.value.trim()) {
          window.setTimeout(renderRecent, 0);
        }
      });
    });
  });
})();
