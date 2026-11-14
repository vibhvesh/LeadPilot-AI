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

  function card(item) {
    const links = (item.links || []).map(safeUrl).filter(Boolean);
    const linkHtml = links.map((href, index) => `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${index === 0 ? "Open source" : "Also " + (index + 1)}</a>`).join(" · ");
    const posted = when(item.published_at || item.created_at);
    const manage = can("pulse", true) ? `<div class="row">
        ${item.status === "open" ? `<button class="btn small" type="button" data-pulse-status="read" data-id="${item.id}">Mark read</button><button class="btn small secondary" type="button" data-pulse-status="dismissed" data-id="${item.id}">Dismiss</button>` : `<button class="btn small secondary" type="button" data-pulse-status="open" data-id="${item.id}">Reopen</button>`}
        <input id="pulse-note-${item.id}" placeholder="Note for the team" aria-label="Note for the team">
        <button class="btn small secondary" type="button" data-pulse-comment="${item.id}">Add note</button>
      </div>` : "";
    const notes = (item.comments || []).map((comment) => `<div class="muted">${esc(comment.author_name || "Teammate")}: ${esc(comment.body)}</div>`).join("");
    const status = item.status !== "open" ? `<span class="status pending">${esc(item.status)}</span>` : "";
    return `<article class="pulse-card pulse-${esc(item.urgency)}">
      <div class="row">${status}<span class="summary-chip">${esc(item.urgency_label)}</span><span class="summary-chip">${esc(item.source_label)}</span></div>
      <h2>${esc(item.headline)}</h2>
      <p class="pulse-why">${esc(item.why_it_matters || "")}</p>
      <div class="muted">${esc([item.topic, posted].filter(Boolean).join(" · "))}</div>
      <div>${linkHtml}</div>
      ${notes}
      ${manage}
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
      else if (button.dataset.pulseStatus) run(() => mark(button.dataset.id, button.dataset.pulseStatus));
      else if (button.dataset.pulseComment) run(() => comment(button.dataset.pulseComment));
    });
    const form = $("pulse-filters");
    if (form) form.addEventListener("submit", (event) => { event.preventDefault(); run(load); });
  }

  window.PulsePage = {load};
})();
