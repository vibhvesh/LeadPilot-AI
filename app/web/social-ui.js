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
    const label = "Open on " + (item.platform_label || "the web");
    const link = href ? (window.DeepLink ? window.DeepLink.anchor(href, label) : `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`) : "";
    const snippet = item.snippet || "Open the post for the original text.";
    const more = snippet.length > 160 ? `<button class="flash-more" type="button" data-more="social-snip-${item.id}">More</button>` : "";
    const reply = item.suggested_reply
      ? `<div class="draft" id="social-reply-${item.id}">${esc(item.suggested_reply)}</div>`
      : `<p class="muted">No reply suggested.</p>`;
    const replyButton = item.suggested_reply && href
      ? `<button class="btn" type="button" data-copy-open="social-reply-${item.id}" data-open-url="${esc(href)}">Reply</button>`
      : (item.suggested_reply ? `<button class="btn" type="button" data-copy="social-reply-${item.id}">Copy</button>` : "");
    const comments = (item.comments || []).map((comment) => `<div class="muted">${esc(comment.author_name || "Teammate")}: ${esc(comment.body)}</div>`).join("");
    const menuId = "social-more-" + item.id;
    const menu = [];
    if (item.suggested_reply) menu.push(`<button type="button" role="menuitem" data-copy="social-reply-${item.id}">Copy reply</button>`);
    if (can("social", true) && item.status === "open") {
      menu.push(`<button type="button" role="menuitem" data-social-status="done" data-id="${item.id}">Done</button>`);
      menu.push(`<button type="button" role="menuitem" data-social-status="ignored" data-id="${item.id}">Ignore</button>`);
    } else if (can("social", true)) {
      menu.push(`<button type="button" role="menuitem" data-social-status="open" data-id="${item.id}">Reopen</button>`);
    }
    if (can("social", true)) {
      menu.push(`<input id="social-note-${item.id}" placeholder="Note for the team" aria-label="Note for the team">`);
      menu.push(`<button type="button" role="menuitem" data-comment="${item.id}">Add note</button>`);
    }
    const overflow = menu.length ? `<div class="overflow"><button class="btn secondary" type="button" data-overflow aria-expanded="false" aria-controls="${menuId}" aria-label="More actions">⋯</button><div class="overflow-menu" id="${menuId}" role="menu" hidden>${menu.join("")}</div></div>` : "";
    const status = item.status !== "open" ? pillStatus(item.status) : "";
    const extra = related ? `<div class="muted">${related} related in other sections</div>` : "";
    return `<article class="flash-card social-card social-tone-${esc(item.bucket || "fyi")}">
      <div class="flash-kicker">${status}${auth}<span class="flash-chip">${esc(item.platform_label || "Web")}</span></div>
      <h2 class="flash-title">${esc(item.poster_name || item.topic || item.company || "Public post")}</h2>
      <p class="flash-meta">${esc(meta)}</p>
      ${company}${topic}${extra}
      <p class="flash-summary" id="social-snip-${item.id}">${esc(snippet)}</p>
      ${more}
      <p><b>Why it matters.</b> ${esc(item.why_it_matters || "")}</p>
      ${reply}
      ${comments}
      <div class="flash-actions">${link}${replyButton}${overflow}</div>
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
    if (!text) return false;
    try {
      await navigator.clipboard.writeText(text);
      toast("Reply copied");
      return true;
    } catch (error) {
      toast("Select the draft and copy it");
      return false;
    }
  }

  async function copyAndOpen(elementId, url) {
    await copyReply(elementId);
    if (window.DeepLink) window.DeepLink.open(url);
    else if (url) window.open(url, "_blank", "noopener");
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
      else if (button.id === "social-filters-toggle") {
        const form = $("social-filters");
        const open = form.classList.toggle("is-open");
        button.setAttribute("aria-expanded", open ? "true" : "false");
      }
      else if (button.dataset.more) {
        const summary = $(button.dataset.more);
        if (!summary) return;
        const open = summary.classList.toggle("is-open");
        button.textContent = open ? "Less" : "More";
      }
      else if (button.dataset.copyOpen) run(() => copyAndOpen(button.dataset.copyOpen, button.dataset.openUrl));
      else if (button.dataset.copy) run(() => copyReply(button.dataset.copy));
      else if (button.dataset.socialStatus) run(() => mark(button.dataset.id, button.dataset.socialStatus));
      else if (button.dataset.comment) run(() => comment(button.dataset.comment));
    });
    const form = $("social-filters");
    if (form) form.addEventListener("submit", (event) => { event.preventDefault(); run(load); });
  }

  window.SocialPage = {load};
})();
