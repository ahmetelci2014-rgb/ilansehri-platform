(() => {
  "use strict";

  document.addEventListener("DOMContentLoaded", () => {
    const nav = document.querySelector("[data-v1252-detail-nav]");
    if (!nav) return;

    const links = Array.from(
      nav.querySelectorAll("[data-detail-nav-link]")
    );

    const sections = links
      .map((link) => {
        const id = link.dataset.detailNavLink;
        const section = document.getElementById(id);

        return section
          ? { id, link, section }
          : null;
      })
      .filter(Boolean);

    if (!sections.length) return;

    const activate = (id) => {
      sections.forEach((item) => {
        const active = item.id === id;

        item.link.classList.toggle("active", active);

        if (active) {
          item.link.setAttribute("aria-current", "true");

          if (window.innerWidth <= 780) {
            item.link.scrollIntoView({
              behavior: "smooth",
              block: "nearest",
              inline: "center",
            });
          }
        } else {
          item.link.removeAttribute("aria-current");
        }
      });
    };

    links.forEach((link) => {
      link.addEventListener("click", () => {
        activate(link.dataset.detailNavLink);
      });
    });

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort(
            (a, b) =>
              b.intersectionRatio - a.intersectionRatio
          )[0];

        if (visible?.target?.id) {
          activate(visible.target.id);
        }
      },
      {
        rootMargin: "-22% 0px -58% 0px",
        threshold: [0.05, 0.2, 0.45],
      }
    );

    sections.forEach(({ section }) => {
      observer.observe(section);
    });

    activate(sections[0].id);
  });
})();
