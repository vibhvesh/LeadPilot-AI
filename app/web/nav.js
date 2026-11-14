/* Sidebar on a wide screen, and a left drawer on a phone. */
(function () {
  const nav = document.getElementById("workspace-nav");
  const backdrop = document.getElementById("nav-backdrop");
  const toggle = document.getElementById("nav-toggle");
  const more = document.getElementById("nav-more");
  const collapse = document.getElementById("nav-collapse");
  const KEY = "leadpilot-nav-collapsed";
  if (!nav) return;
  let returnFocus = null;
  let touchX = 0;

  function mobile() {
    return window.matchMedia("(max-width: 800px)").matches;
  }

  function focusable() {
    return [...nav.querySelectorAll("button, a")].filter(function (el) {
      return !el.hidden && el.offsetParent !== null;
    });
  }

  function setOpen(open) {
    if (!mobile()) open = false;
    document.body.classList.toggle("nav-open", open);
    if (backdrop) backdrop.hidden = !open;
    [toggle, more].forEach(function (button) {
      if (button) button.setAttribute("aria-expanded", open ? "true" : "false");
    });
    if (open) {
      returnFocus = document.activeElement;
      const first = focusable()[0];
      if (first) first.focus();
      return;
    }
    if (returnFocus && returnFocus.focus) returnFocus.focus();
    returnFocus = null;
  }

  function setCollapsed(collapsed) {
    document.body.classList.toggle("nav-collapsed", collapsed);
    try { localStorage.setItem(KEY, collapsed ? "1" : "0"); } catch (error) { /* private mode keeps the choice for this view */ }
    if (collapse) {
      collapse.setAttribute("aria-pressed", collapsed ? "true" : "false");
      collapse.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
      collapse.textContent = collapsed ? "⟩" : "⟨";
    }
  }

  try { setCollapsed(localStorage.getItem(KEY) === "1"); } catch (error) { setCollapsed(false); }

  [toggle, more].forEach(function (button) {
    if (!button) return;
    button.addEventListener("click", function () { setOpen(!document.body.classList.contains("nav-open")); });
  });
  if (backdrop) backdrop.addEventListener("click", function () { setOpen(false); });
  if (collapse) collapse.addEventListener("click", function () { setCollapsed(!document.body.classList.contains("nav-collapsed")); });

  nav.addEventListener("click", function (event) {
    if (event.target.closest(".nav-link")) {
      const scroll = event.target.closest("[data-scroll]");
      if (scroll && window.LeadPilot) {
        const shown = window.LeadPilot.show("settings");
        Promise.resolve(shown).then(function () {
          const target = document.querySelector(scroll.getAttribute("data-scroll"));
          if (target) target.scrollIntoView({block: "start"});
        });
      }
      if (mobile()) setOpen(false);
    }
  });
  nav.addEventListener("touchstart", function (event) {
    touchX = event.changedTouches[0].clientX;
  }, {passive: true});
  nav.addEventListener("touchend", function (event) {
    if (touchX - event.changedTouches[0].clientX > 48) setOpen(false);
  }, {passive: true});
  document.addEventListener("keydown", function (event) {
    if (!document.body.classList.contains("nav-open")) return;
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }
    if (event.key !== "Tab") return;
    const items = focusable();
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
  window.matchMedia("(max-width: 800px)").addEventListener("change", function (event) {
    if (!event.matches) setOpen(false);
  });

  document.addEventListener("click", function (event) {
    const button = event.target.closest("[data-overflow]");
    document.querySelectorAll(".overflow-menu").forEach(function (menu) {
      const owner = button && button.getAttribute("aria-controls");
      if (menu.id !== owner) {
        menu.hidden = true;
        const control = document.querySelector('[aria-controls="' + menu.id + '"]');
        if (control) control.setAttribute("aria-expanded", "false");
      }
    });
    if (!button) return;
    const menu = document.getElementById(button.getAttribute("aria-controls"));
    if (!menu) return;
    const open = menu.hidden;
    menu.hidden = !open;
    button.setAttribute("aria-expanded", open ? "true" : "false");
    event.stopPropagation();
  });
})();
