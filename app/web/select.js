/* Azure listbox layered on the native select so values and labels stay in sync. */
(function () {
  let openWrap = null;

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[ch]));
  }

  function installValueHook() {
    const proto = HTMLSelectElement.prototype;
    const desc = Object.getOwnPropertyDescriptor(proto, "value");
    if (!desc || !desc.set || proto.__azureHook) return;
    proto.__azureHook = true;
    Object.defineProperty(proto, "value", {
      configurable: true,
      enumerable: desc.enumerable,
      get() { return desc.get.call(this); },
      set(next) {
        desc.set.call(this, next);
        this.dispatchEvent(new Event("azure-sync"));
      },
    });
  }

  function enhance(root) {
    (root || document).querySelectorAll("select:not([data-azure])").forEach(build);
  }

  function build(select) {
    if (select.multiple || select.dataset.azure) return;
    select.dataset.azure = "1";
    const wrap = document.createElement("div");
    wrap.className = "azure-select";
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);
    select.classList.add("azure-native");
    select.tabIndex = -1;
    select.setAttribute("aria-hidden", "true");

    const face = document.createElement("button");
    face.type = "button";
    face.className = "azure-face";
    face.setAttribute("aria-haspopup", "listbox");
    face.setAttribute("aria-expanded", "false");
    wrap.appendChild(face);

    const menu = document.createElement("div");
    menu.className = "azure-menu";
    menu.hidden = true;
    menu.setAttribute("role", "listbox");
    menu.id = "azure-menu-" + Math.random().toString(36).slice(2, 8);
    face.setAttribute("aria-controls", menu.id);
    document.body.appendChild(menu);

    let active = 0;
    let typed = "";
    let typedAt = 0;
    let backdrop = null;

    function choices() { return [...select.options]; }
    function paint() {
      const current = select.selectedOptions[0];
      face.textContent = current ? current.textContent : "Choose";
      face.disabled = select.disabled;
    }
    function render() {
      menu.innerHTML = choices().map((opt, index) => {
        const selected = index === select.selectedIndex;
        return `<button type="button" class="azure-option${selected ? " is-selected" : ""}" role="option" aria-selected="${selected}" data-index="${index}"><span>${esc(opt.textContent)}</span><span class="azure-check" aria-hidden="true">✓</span></button>`;
      }).join("");
      [...menu.querySelectorAll(".azure-option")].forEach((button) => {
        button.addEventListener("click", () => choose(Number(button.dataset.index)));
      });
    }
    function mark(index) {
      const buttons = [...menu.querySelectorAll(".azure-option")];
      if (!buttons.length) return;
      active = Math.max(0, Math.min(index, buttons.length - 1));
      buttons.forEach((button, item) => button.classList.toggle("is-active", item === active));
      buttons[active].scrollIntoView({block: "nearest"});
    }
    function sheet() {
      return window.innerWidth <= 800 || window.matchMedia("(max-width: 800px)").matches;
    }
    function place() {
      menu.classList.toggle("is-sheet", sheet());
      if (menu.classList.contains("is-sheet")) {
        menu.style.left = "0";
        menu.style.width = "100%";
        return;
      }
      const box = face.getBoundingClientRect();
      const height = Math.min(menu.scrollHeight, 280);
      const below = window.innerHeight - box.bottom;
      const top = below > height + 12 || below > box.top ? box.bottom + 6 : Math.max(8, box.top - height - 6);
      menu.style.top = top + "px";
      menu.style.left = Math.max(8, box.left) + "px";
      menu.style.width = box.width + "px";
    }
    function open() {
      if (face.disabled) return;
      if (openWrap && openWrap !== wrap) openWrap.azureClose();
      render();
      menu.hidden = false;
      face.setAttribute("aria-expanded", "true");
      if (sheet()) {
        backdrop = document.createElement("button");
        backdrop.type = "button";
        backdrop.className = "azure-backdrop";
        backdrop.setAttribute("aria-label", "Close list");
        backdrop.addEventListener("click", close);
        document.body.appendChild(backdrop);
      }
      place();
      mark(Math.max(0, select.selectedIndex));
      openWrap = wrap;
    }
    function close() {
      menu.hidden = true;
      face.setAttribute("aria-expanded", "false");
      if (backdrop) { backdrop.remove(); backdrop = null; }
      if (openWrap === wrap) openWrap = null;
    }
    function choose(index) {
      select.selectedIndex = index;
      select.dispatchEvent(new Event("change", {bubbles: true}));
      select.dispatchEvent(new Event("input", {bubbles: true}));
      paint();
      close();
      face.focus();
    }
    wrap.azureClose = close;
    face.addEventListener("click", () => (menu.hidden ? open() : close()));
    face.addEventListener("keydown", (event) => {
      const buttons = [...menu.querySelectorAll(".azure-option")];
      if (event.key === "ArrowDown") { event.preventDefault(); if (menu.hidden) open(); else mark(active + 1); }
      else if (event.key === "ArrowUp") { event.preventDefault(); if (menu.hidden) open(); else mark(active - 1); }
      else if (event.key === "Home") { event.preventDefault(); open(); mark(0); }
      else if (event.key === "End") { event.preventDefault(); open(); mark(buttons.length - 1); }
      else if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (menu.hidden) open();
        else choose(active);
      } else if (event.key === "Escape") close();
      else if (event.key.length === 1 && /\S/.test(event.key)) {
        const now = Date.now();
        typed = now - typedAt > 600 ? event.key.toLowerCase() : typed + event.key.toLowerCase();
        typedAt = now;
        const found = choices().findIndex((opt) => opt.textContent.trim().toLowerCase().startsWith(typed));
        if (found >= 0) { if (menu.hidden) open(); mark(found); }
      }
    });
    select.addEventListener("change", paint);
    select.addEventListener("azure-sync", () => { paint(); if (!menu.hidden) render(); });
    new MutationObserver(() => { paint(); if (!menu.hidden) render(); }).observe(select, {childList: true, subtree: true});
    paint();
  }

  document.addEventListener("click", (event) => {
    if (!openWrap) return;
    if (event.target.closest(".azure-select, .azure-menu, .azure-backdrop")) return;
    openWrap.azureClose();
  });
  window.addEventListener("resize", () => { if (openWrap) openWrap.azureClose(); });

  installValueHook();
  function boot() { enhance(document); }
  if (document.body) boot();
  else document.addEventListener("DOMContentLoaded", boot);
  new MutationObserver(() => enhance(document)).observe(document.documentElement, {childList: true, subtree: true});
  window.AzureSelect = {enhance};
})();
