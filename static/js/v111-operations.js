document.addEventListener("DOMContentLoaded", () => {
  const selectAll = document.querySelector("[data-moderation-select-all]");
  const checkboxes = [...document.querySelectorAll("[data-moderation-checkbox]")];
  if (selectAll && checkboxes.length) {
    selectAll.addEventListener("change", () => {
      checkboxes.forEach((checkbox) => {
        checkbox.checked = selectAll.checked;
      });
    });
    checkboxes.forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        selectAll.checked = checkboxes.every((item) => item.checked);
        selectAll.indeterminate = !selectAll.checked && checkboxes.some((item) => item.checked);
      });
    });
  }

  const bulkForm = document.querySelector("#bulk-moderation-form");
  if (bulkForm) {
    bulkForm.addEventListener("submit", (event) => {
      const selected = checkboxes.filter((item) => item.checked);
      const action = bulkForm.querySelector("[name='bulk_action']")?.value;
      const note = bulkForm.querySelector("[name='bulk_note']")?.value.trim();
      if (!selected.length) {
        event.preventDefault();
        window.alert("Toplu işlem için en az bir ilan seç.");
        return;
      }
      if (action === "reject" && !note) {
        event.preventDefault();
        window.alert("Düzeltme istenirken ortak bir açıklama yazmalısın.");
        return;
      }
      const verb = action === "approve" ? "yayınlamak" : "düzeltme istemek";
      if (!window.confirm(`${selected.length} ilan için ${verb} istediğine emin misin?`)) {
        event.preventDefault();
      }
    });
  }
});
