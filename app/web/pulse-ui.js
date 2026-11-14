/* Industry Pulse flashcards. This file never posts or signs in. */
(function () {
  const ui = window.LeadPilot;
  if (!ui) return;
  const {$, api, esc, can, toast} = ui;

  function params() {
    const query = new URLSearchParams();
    const urgency = $("pulse-filter-urgency").value;
    const source = $("pulse-filter-source").value;
    const topic = $("pulse-filter-topic").value.trim();
    const dateFrom = $("pulse-filter-from").value;
    const dateTo = $("pulse-filter-to").value;
    const status = $("pulse-filter-status").value;
    if (urgency) query.set("urgency", urgency);
    if (source) query.set("source_type", source);
    if (topic) query.set("topic", topic);
    if (dateFrom) query.set("date_from", dateFrom);
    if (dateTo) query.set("date_to", dateTo);
    if (status) query.set("status", status);
    return query;
  }

  function when(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleDateString(undefined, {year: "numeric", month: "short", day: "numeric"});
  }

  function safeUrl(url) {
    try {
      const parsed = new URL(url);
      if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return "";
      return parsed.href;
    } catch (error) {
      return "";
    }
  }

  function openLink(href, label) {
    if (window.DeepLink) return window.DeepLink.anchor(href, label);
    return `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`;
  }

  function card(item) {
    const links = (item.links || []).map(safeUrl).filter(Boolean);
    const primary = links[0] ? openLink(links[0], "Open") : "";
    const extra = links.slice(1).map((href, index) => openLink(href, "Also " + (index + 2))).join(" ");
    const posted = when(item.published_at || item.created_at);
    const why = item.why_it_matters || "";
    const more = why.length > 160 ? `<button class="flash-more" type="button" data-more="pulse-why-${item.id}">More</button>` : "";
    const tone = item.urgency === "urgent" ? "urgent" : item.urgency === "week" ? "week" : "fyi";
    const notes = (item.comments || []).map((comment) => `<div class="muted">${esc(comment.author_name || "Teammate")} · ${esc((comment.created_at || "").slice(0, 16).replace("T", " "))}: ${esc(comment.body)}</div>`).join("");
    const status = item.status !== "open" ? `<span class="status pending">${esc(item.status)}</span>` : "";
    const menuId = "pulse-more-" + item.id;
    const menu = [];
    if (can("pulse", true) && item.status === "open") {
      menu.push(`<button type="button" role="menuitem" data-pulse-status="read" data-id="${item.id}">Mark read</button>`);
      menu.push(`<button type="button" role="menuitem" data-pulse-status="dismissed" data-id="${item.id}">Dismiss</button>`);
    } else if (can("pulse", true)) {
      menu.push(`<button type="button" role="menuitem" data-pulse-status="open" data-id="${item.id}">Reopen</button>`);
    }
    if (can("pulse", true)) {
      menu.push(`<input id="pulse-note-${item.id}" placeholder="Note for the team" aria-label="Note for the team">`);
      menu.push(`<button type="button" role="menuitem" data-pulse-comment="${item.id}">Add note</button>`);
    }
    const overflow = menu.length ? `<div class="overflow"><button class="btn secondary" type="button" data-overflow aria-expanded="false" aria-controls="${menuId}" aria-label="More actions">⋯</button><div class="overflow-menu" id="${menuId}" role="menu" hidden>${menu.join("")}</div></div>` : "";
    return `<article class="flash-card pulse-card pulse-${esc(item.urgency)}">
      <div class="flash-kicker">${status}<span class="flash-badge flash-badge-${tone}">${esc(item.urgency_label || "FYI")}</span><span class="flash-chip">${esc(item.source_label || "Source")}</span></div>
      <h2 class="flash-title">${esc(item.headline)}</h2>
      <p class="flash-meta">${esc([posted, item.topic].filter(Boolean).join(" · "))}</p>
      <p class="flash-summary" id="pulse-why-${item.id}">${esc(why)}</p>
      ${more}
      ${extra ? `<div class="flash-meta">${extra}</div>` : ""}
      ${notes}
      <div class="flash-actions">${primary}${overflow}</div>
    </article>`;
  }

  function render(data) {
    const counts = data.counts || {};
    $("pulse-counts").textContent = `${counts.urgent || 0} urgent · ${counts.week || 0} this week · ${counts.fyi || 0} FYI`;
    const note = $("pulse-fetch-note");
    if (note) {
      note.textContent = (data.sources || {}).web_search
        ? "A search key is saved. Check public news reads stories and does not publish anything."
        : "Add a Tavily or Brave key under API keys to pull public stories. Pasting a link still works.";
    }
    const items = data.items || [];
    $("pulse-feed").innerHTML = items.length ? items.map(card).join("") : `<p class="muted">No stories in this view.</p>`;
  }

  async function load() {
    const query = params().toString();
    const data = await api("/api/pulse" + (query ? "?" + query : ""));
    render(data);
    return data;
  }

  async function save() {
    const headline = $("pulse-headline").value.trim();
    const url = $("pulse-url").value.trim();
    if (!headline || !url) { toast("Add a headline and a public link"); return; }
    const saved = await api("/api/pulse", {method: "POST", body: {
      headline,
      url,
      why_it_matters: $("pulse-why").value,
      urgency: $("pulse-urgency").value,
      source_type: $("pulse-source").value,
      published_at: $("pulse-date").value,
      topic: $("pulse-topic").value,
      links: $("pulse-links").value,
    }});
    $("pulse-headline").value = "";
    $("pulse-url").value = "";
    $("pulse-why").value = "";
    $("pulse-links").value = "";
    toast("Saved " + (saved.urgency_label || "story"));
    await load();
  }

  async function pull() {
    const result = await api("/api/pulse/fetch", {method: "POST", body: {}});
    toast(result.note || "Checked public news");
    await load();
  }

  async function mark(id, status) {
    await api("/api/pulse/" + id, {method: "PATCH", body: {status}});
    toast(status === "read" ? "Marked read" : status === "dismissed" ? "Dismissed" : "Reopened");
    await load();
  }

  async function comment(id) {
    const input = $("pulse-note-" + id);
    await api("/api/pulse/" + id + "/comments", {method: "POST", body: {body: input.value}});
    input.value = "";
    toast("Note saved");
    await load();
  }

  function run(work) {
    Promise.resolve().then(work).catch((error) => toast(error.message));
  }

  const root = document.getElementById("pulse");
  if (root) {
    root.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button || !root.contains(button)) return;
      if (button.id === "pulse-save") run(save);
      else if (button.id === "pulse-fetch") run(pull);
      else if (button.id === "pulse-filters-toggle") {
        const form = $("pulse-filters");
        const open = form.classList.toggle("is-open");
        button.setAttribute("aria-expanded", open ? "true" : "false");
      }
      else if (button.dataset.more) {
        const summary = $(button.dataset.more);
        if (!summary) return;
        const open = summary.classList.toggle("is-open");
        button.textContent = open ? "Less" : "More";
      }
      else if (button.dataset.pulseStatus) run(() => mark(button.dataset.id, button.dataset.pulseStatus));
      else if (button.dataset.pulseComment) run(() => comment(button.dataset.pulseComment));
    });
    const form = $("pulse-filters");
    if (form) form.addEventListener("submit", (event) => { event.preventDefault(); run(load); });
  }

  window.PulsePage = {load};
})();
