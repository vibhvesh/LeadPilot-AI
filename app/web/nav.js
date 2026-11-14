/* Opens and closes the More menu. Tab buttons themselves are handled with the rest of the workspace. */
(function () {
  const sheet = document.getElementById("more-sheet");
  const toggles = [document.getElementById("nav-more"), document.getElementById("nav-more-mobile")].filter(Boolean);
  if (!sheet || !toggles.length) return;

  function setOpen(open) {
    sheet.hidden = !open;
    toggles.forEach(function (button) { button.setAttribute("aria-expanded", open ? "true" : "false"); });
    if (!open) return;
    const first = sheet.querySelector("button:not([hidden])");
    if (first) first.focus();
  }

  toggles.forEach(function (button) {
    button.addEventListener("click", function () { setOpen(sheet.hidden); });
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !sheet.hidden) setOpen(false);
  });
  document.addEventListener("click", function (event) {
    if (sheet.hidden) return;
    if (event.target.closest("#more-sheet, #nav-more, #nav-more-mobile")) {
      if (event.target.closest("#more-sheet .tab, #signout, #mascot-settings-open")) setOpen(false);
      return;
    }
    setOpen(false);
  });

  document.addEventListener("click", function (event) {
    const toggle = event.target.closest("[data-overflow]");
    document.querySelectorAll(".overflow-menu").forEach(function (menu) {
      const owner = toggle && toggle.getAttribute("aria-controls");
      if (menu.id !== owner) {
        menu.hidden = true;
        const button = document.querySelector('[aria-controls="' + menu.id + '"]');
        if (button) button.setAttribute("aria-expanded", "false");
      }
    });
    if (!toggle) return;
    const menu = document.getElementById(toggle.getAttribute("aria-controls"));
    if (!menu) return;
    const open = menu.hidden;
    menu.hidden = !open;
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    event.stopPropagation();
  });
})();