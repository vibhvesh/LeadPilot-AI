/* Social feed. Drafts are copied by a person. This file never posts. */
(function () {
  const ui = window.LeadPilot;
  if (!ui) return;
  const {$, api, esc, can, toast} = ui;
  const sections = [
    ["reply", "Reply to", "Someone is asking for vendors, C2C partners, or recruiters.", "social-reply"],
    ["engage", "Engage", "Relevant discussions worth a like or a comment.", "social-engage"],
    ["fyi", "FYI", "Context only. No reply is suggested.", "social-fyi"],
  ];

  function params() {
    const query = new URLSearchParams();
    const platform = $("social-filter-platform").value;
    const topic = $("social-filter-topic").value.trim();
    const company = $("social-filter-company").value.trim();
    const dateFrom = $("social-filter-from").value;
    const dateTo = $("social-filter-to").value;
    const status = $("social-filter-status").value;
    if (platform) query.set("platform", platform);
    if (topic) query.set("topic", topic);
    if (company) query.set("company", company);
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

  function card(item, related) {
    const href = safeUrl(item.url);
    const posted = when(item.posted_at || item.created_at);
    const who = [item.poster_name, item.poster_role].filter(Boolean).join(" · ");
    const meta = [who, posted, item.platform_label].filter(Boolean).join(" · ");
    const auth = item.work_auth ? `<span class="summary-chip">${esc(item.work_auth)}</span>` : "";
    const company = item.company ? `<div class="muted">Company mentioned: ${esc(item.company)}</div>` : "";
    const topic = item.topic ? `<div class="muted">Topic: ${esc(item.topic)}</div>` : "";
    const link = href ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">Open on ${esc(item.platform_label || "the web")}</a>` : "";
    const reply = item.suggested_reply
      ? `<div class="draft" id="social-reply-${item.id}">${esc(item.suggested_reply)}</div><button class="btn small secondary" type="button" data-copy="social-reply-${item.id}">Copy reply</button>`
      : `<p class="muted">No reply suggested.</p>`;
    const comments = (item.comments || []).map((comment) => `<div class="muted">${esc(comment.author_name || "Teammate")}: ${esc(comment.body)}</div>`).join("");
    const manage = can("social", true) ? `<div class="row" style="margin-top:8px">
        ${item.status === "open" ? `<button class="btn small" type="button" data-social-status="done" data-id="${item.id}">Mark done</button><button class="btn small secondary" type="button" data-social-status="ignored" data-id="${item.id}">Ignore</button>` : `<button class="btn small secondary" type="button" data-social-status="open" data-id="${item.id}">Reopen</button>`}
        <input id="social-note-${item.id}" placeholder="Note for the team" aria-label="Note for the team">
        <button class="btn small secondary" type="button" data-comment="${item.id}">Add note</button>
      </div>` : "";
    const status = item.status !== "open" ? pillStatus(item.status) : "";
    const extra = related ? `<div class="muted">${related} related in other sections</div>` : "";
    return `<article class="social-card">
      <div class="row">${status}${auth}</div>
      <div class="muted">${esc(meta)}</div>
      ${company}${topic}${extra}
      <p>${esc(item.snippet || "Open the post for the original text.")}</p>
      <p><b>Why it matters.</b> ${esc(item.why_it_matters || "")}</p>
      ${link}
      ${reply}
      ${comments}
      ${manage}
    </article>`;
  }

  function pillStatus(status) {
    return `<span class="status pending">${esc(status)}</span>`;
  }

  function render(data) {
    const items = data.items || [];
    $("social-counts").textContent = `${data.counts.reply || 0} to reply · ${data.counts.engage || 0} to engage · ${data.counts.fyi || 0} for context`;
    const sources = data.sources || {};
    const note = $("social-fetch-note");
    if (note) {
      if (sources.x_api) note.textContent = "An X API key is saved. Check public posts reads recent posts and does not publish anything.";
      else if (sources.web_search) note.textContent = "No X API key. Check public posts uses web search and keeps public links only. LinkedIn login pages are skipped.";
      else note.textContent = "Add an X API key or a search key under API keys to pull public posts. Pasting a link still works.";
    }
    $("social-feed").innerHTML = sections.map(([bucket, title, blurb, klass]) => {
      const mine = items.filter((item) => item.bucket === bucket);
      const groups = [];
      const seen = new Map();
      mine.forEach((item) => {
        const key = item.discussion_key || ("item-" + item.id);
        if (!seen.has(key)) {
          seen.set(key, []);
          groups.push(key);
        }
        seen.get(key).push(item);
      });
      const body = groups.length ? groups.map((key) => {
        const rows = seen.get(key);
        const sample = rows[0];
        const related = items.filter((item) => item.discussion_key === key && item.bucket !== bucket).length;
        const heading = rows.length > 1 || sample.topic || sample.company
          ? `<h3>${esc(sample.topic || sample.company || "Related discussion")}${sample.company && sample.topic ? " · " + esc(sample.company) : ""}</h3>`
          : "";
        return `<div class="social-group">${heading}${rows.map((item) => card(item, related)).join("")}</div>`;
      }).join("") : `<p class="muted">Nothing in this section.</p>`;
      return `<section class="social-column ${klass}"><h2>${esc(title)}</h2><p class="muted">${esc(blurb)}</p>${body}</section>`;
    }).join("");
  }

  async function load() {
    const query = params().toString();
    const data = await api("/api/social" + (query ? "?" + query : ""));
    render(data);
    return data;
  }

  async function save() {
    const url = $("social-url").value.trim();
    if (!url) { toast("Paste a public link"); return; }
    const body = {
      url,
      platform: $("social-platform").value,
      bucket: $("social-bucket").value,
      poster_name: $("social-poster").value,
      poster_role: $("social-role").value,
      posted_at: $("social-date").value,
      topic: $("social-topic").value,
      company: $("social-company").value,
      snippet: $("social-snippet").value,
    };
    const saved = await api("/api/social", {method: "POST", body});
    $("social-url").value = "";
    $("social-snippet").value = "";
    toast("Saved " + (saved.platform_label || "link"));
    await load();
  }

  async function pull() {
    const result = await api("/api/social/fetch", {method: "POST", body: {}});
    toast(result.note || "Checked public posts");
    await load();
  }

  async function mark(id, status) {
    await api("/api/social/" + id, {method: "PATCH", body: {status}});
    toast(status === "done" ? "Marked done" : status === "ignored" ? "Ignored" : "Reopened");
    await load();
  }

  async function comment(id) {
    const input = $("social-note-" + id);
    await api("/api/social/" + id + "/comments", {method: "POST", body: {body: input.value}});
    input.value = "";
    toast("Note saved");
    await load();
  }

  async function copyReply(elementId) {
    const node = $(elementId);
    const text = node ? node.textContent : "";
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      toast("Reply copied");
    } catch (error) {
      toast("Select the draft and copy it");
    }
  }

  function run(work) {
    Promise.resolve()
      .then(work)
      .catch((error) => toast(error.message));
  }

  const root = document.getElementById("social");
  if (root) {
    root.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button || !root.contains(button)) return;
      if (button.id === "social-save") run(save);
      else if (button.id === "social-fetch") run(pull);
      else if (button.dataset.copy) run(() => copyReply(button.dataset.copy));
      else if (button.dataset.socialStatus) run(() => mark(button.dataset.id, button.dataset.socialStatus));
      else if (button.dataset.comment) run(() => comment(button.dataset.comment));
    });
    const form = $("social-filters");
    if (form) form.addEventListener("submit", (event) => { event.preventDefault(); run(load); });
  }

  window.SocialPage = {load};
})();
