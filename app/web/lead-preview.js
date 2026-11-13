/* Summary preview overlay. A short tap opens it; a drag does not. */
(function () {
  const DRAG_PX = 8;
  let shell = null;
  let pointer = null;
  let suppressClick = false;

  function gestureOpensPreview(dx, dy) {
    return Math.hypot(dx, dy) <= DRAG_PX;
  }

  function ensure() {
    if (shell) return shell;
    shell = document.createElement("div");
    shell.id = "lead-preview";
    shell.hidden = true;
    shell.innerHTML = `<div class="preview-backdrop" data-close="1"></div>
      <div class="preview-panel" role="dialog" aria-modal="true" aria-label="Summary preview">
        <div class="preview-bar">
          <button class="btn secondary" type="button" id="preview-close">Close</button>
          <a class="btn" id="preview-full" href="/leads">Open full lead</a>
        </div>
        <div id="preview-body"></div>
      </div>`;
    document.body.appendChild(shell);
    shell.addEventListener("click", (event) => {
      if (event.target.closest("[data-close], #preview-close")) close();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && shell && !shell.hidden) close();
    });
    return shell;
  }

  function show(lead) {
    const root = ensure();
    document.getElementById("preview-full").href = "/leads?id=" + encodeURIComponent(lead.id);
    document.getElementById("preview-body").innerHTML = window.LeadSummary.render(lead);
    root.hidden = false;
    document.body.classList.add("preview-open");
    document.getElementById("preview-close").focus();
    document.dispatchEvent(new CustomEvent("leadpilot:mascot", {detail: {
      text: "Here's the summary!",
      selector: "#lead-preview .preview-panel",
      href: "/leads?id=" + encodeURIComponent(lead.id),
    }}));
  }

  async function open(id) {
    try {
      const lead = await window.LeadPilot.api("/api/leads/" + id);
      show(lead);
    } catch (error) {
      window.LeadPilot.toast(error.message);
    }
  }

  function close() {
    if (!shell) return;
    shell.hidden = true;
    document.body.classList.remove("preview-open");
  }

  function cardFrom(event) {
    return event.target.closest("[data-preview-lead]");
  }

  document.addEventListener("pointerdown", (event) => {
    const card = cardFrom(event);
    if (!card || event.button !== 0) {
      pointer = null;
      return;
    }
    pointer = {id: event.pointerId, x: event.clientX, y: event.clientY};
    suppressClick = false;
  });

  document.addEventListener("pointermove", (event) => {
    if (!pointer || event.pointerId !== pointer.id) return;
    if (!gestureOpensPreview(event.clientX - pointer.x, event.clientY - pointer.y)) suppressClick = true;
  });

  document.addEventListener("pointerup", () => {
    pointer = null;
    if (suppressClick) setTimeout(() => { suppressClick = false; }, 400);
  });
  document.addEventListener("pointercancel", () => { pointer = null; suppressClick = true; });

  document.addEventListener("click", (event) => {
    const card = cardFrom(event);
    if (!card) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    if (suppressClick) {
      event.preventDefault();
      event.stopPropagation();
      suppressClick = false;
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const id = Number(card.dataset.previewLead);
    if (!id) return;
    const leadsOpen = document.getElementById("leads") && document.getElementById("leads").classList.contains("active");
    if (leadsOpen && typeof openLead === "function") openLead(id, {preview: true});
    else open(id);
  }, true);

  window.LeadPreview = {open, show, close, gestureOpensPreview, DRAG_PX};
})();
