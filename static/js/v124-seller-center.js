(() => {
  const root = document.querySelector("[data-v124-seller-center]");
  const bulkForm = document.querySelector("[data-v124-bulk-form]");
  if (!root || !bulkForm) return;

  const items = [...document.querySelectorAll("[data-v124-listing-select]")];
  const selectAll = bulkForm.querySelector("[data-v124-select-all]");
  const count = bulkForm.querySelector("[data-v124-selected-count]");
  const submit = bulkForm.querySelector("[data-v124-bulk-submit]");
  const action = bulkForm.querySelector('select[name="bulk_action"]');

  const refresh = () => {
    const selected = items.filter((item) => item.checked).length;
    if (count) count.textContent = `${selected} ilan seçildi`;
    if (submit) submit.disabled = selected === 0 || !action?.value;
    if (selectAll) {
      selectAll.checked = items.length > 0 && selected === items.length;
      selectAll.indeterminate = selected > 0 && selected < items.length;
    }
    items.forEach((item) => item.closest("[data-v124-listing-card]")?.classList.toggle("is-selected", item.checked));
  };

  selectAll?.addEventListener("change", () => {
    items.forEach((item) => { item.checked = selectAll.checked; });
    refresh();
  });
  items.forEach((item) => item.addEventListener("change", refresh));
  action?.addEventListener("change", refresh);
  bulkForm.addEventListener("submit", (event) => {
    const selected = items.filter((item) => item.checked).length;
    if (!selected || !action?.value) {
      event.preventDefault();
      refresh();
      return;
    }
    if (["complete", "draft"].includes(action.value)) {
      const label = action.options[action.selectedIndex]?.text || "işlemi";
      if (!window.confirm(`${selected} ilan için “${label}” işlemi uygulansın mı?`)) event.preventDefault();
    }
  });

  document.querySelector("[data-v124-status-tabs] .active")?.scrollIntoView({block: "nearest", inline: "center"});
  refresh();
})();
