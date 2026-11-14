/* Lead actions: outreach drafts, notes, assignment, and today's due list. */
(function () {
  const ui = window.LeadPilot;
  if (!ui) return;
  const {$, api, esc, toast} = ui;

  function panel(lead) {
    return `<div class="card" id="lead-actions" style="margin-top:12px">
      <h2>Actions</h2>
      <div class="row">
        <button class="btn small" type="button" data-act="outreach">Outreach</button>
        <button class="btn secondary small" type="button" data-act="follow">Follow-up</button>
        <button class="btn secondary small" type="button" data-act="note">Add note</button>
        <button class="btn secondary small" type="button" data-act="assign">Assign POC</button>
        <button class="btn secondary small" type="button" data-act="status">Mark status</button>
      </div>
      <div id="lead-action-body"></div>
      <h2 style="margin-top:14px">Activity</h2>
      <div class="list" id="lead-activity"></div>
    </div>`;
  }

  async function activity(id) {
    const data = await api("/api/leads/" + id + "/activity");
    const host = $("lead-activity");
    if (!host) return;
    const rows = data.events || [];
    host.innerHTML = rows.length ? rows.map((row) => `<div class="item">${esc(row.summary)}</div>`).join("") : `<div class="muted">No activity yet.</div>`;
  }

  async function outreach(lead, key) {
    const data = await api("/api/leads/" + lead.id + "/outreach?template_key=" + encodeURIComponent(key || "first"));
    const host = $("lead-action-body");
    const blocked = data.blocked ? `<p class="error">${esc(data.blocked)}</p><div class="field"><label>Admin override reason</label><input id="outreach-reason"></div>` : "";
    host.innerHTML = `${blocked}
      <div class="field"><label>Subject</label><input id="outreach-subject" value="${esc(data.subject)}"></div>
      <div class="field"><label>Message</label><textarea id="outreach-body">${esc(data.body)}</textarea></div>
      <div class="field"><label>Next follow-up in days</label><input id="outreach-days" type="number" value="7" min="1"></div>
      <div class="row">
        <a class="btn secondary" id="outreach-mailto" href="${esc(data.mailto)}">Open in my mail app</a>
        <button class="btn" type="button" id="outreach-sent">I sent it</button>
        <button class="btn secondary" type="button" id="outreach-gmail">Send with Gmail</button>
      </div>`;
    const payload = () => ({
      template_key: key || data.next_key || "first",
      subject: $("outreach-subject").value,
      body: $("outreach-body").value,
      followup_days: Number($("outreach-days").value) || 7,
      override_reason: $("outreach-reason") ? $("outreach-reason").value : "",
    });
    $("outreach-sent").onclick = async () => {
      try {
        const saved = await api("/api/leads/" + lead.id + "/outreach/confirm", {method: "POST", body: payload()});
        toast(saved.summary || "Recorded");
        activity(lead.id);
        if (window.loadLeads) loadLeads();
      } catch (error) { toast(error.message); }
    };
    $("outreach-gmail").onclick = async () => {
      try {
        const saved = await api("/api/leads/" + lead.id + "/outreach", {method: "POST", body: Object.assign({channel: "gmail"}, payload())});
        toast(saved.summary || "Sent");
        activity(lead.id);
      } catch (error) { toast(error.message); }
    };
  }

  async function mount(lead) {
    const host = $("lead-actions");
    if (!host) return;
    host.addEventListener("click", async (event) => {
      const button = event.target.closest("[data-act]");
      if (!button) return;
      const act = button.dataset.act;
      if (act === "outreach") return outreach(lead, "first");
      if (act === "follow") return outreach(lead, "followup_1");
      if (act === "note") {
        $("lead-action-body").innerHTML = `<div class="field"><label>Note</label><textarea id="lead-note"></textarea></div><button class="btn small" type="button" id="lead-note-save">Save note</button>`;
        $("lead-note-save").onclick = async () => {
          await api("/api/leads/" + lead.id + "/note", {method: "POST", body: {body: $("lead-note").value}});
          toast("Note saved");
          activity(lead.id);
        };
      }
      if (act === "assign") {
        await api("/api/leads/" + lead.id + "/assign", {method: "POST", body: {}});
        toast("You are the point of contact");
        activity(lead.id);
      }
      if (act === "status") {
        await api("/api/leads/" + lead.id, {method: "PATCH", body: {status: "Contacted"}});
        toast("Marked contacted");
        if (window.loadLeads) loadLeads();
      }
    });
    activity(lead.id);
  }

  async function due() {
    const host = $("due-today-list");
    if (!host) return;
    const data = await api("/api/outreach/due");
    const items = data.items || [];
    host.innerHTML = items.length ? items.map((item) => `<div class="item"><b>${esc(item.company || item.title)}</b><div class="muted">${esc(item.title)} · ${item.covering ? "Covering a teammate" : "Yours"}</div>${item.lead_id ? `<button class="btn small" type="button" data-take="${item.lead_id}">Take over</button>` : ""}</div>`).join("") : `<div class="muted">Nothing due today.</div>`;
  }

  async function settings() {
    const host = $("outreach-settings");
    if (!host || host.dataset.ready) return;
    const data = await api("/api/outreach/templates");
    host.dataset.ready = "1";
    host.innerHTML = `<h2>Outreach templates</h2><p class="muted">Merge fields: {{first_name}}, {{full_name}}, {{company}}, {{sender_name}}, {{sender_email}}</p>
      ${(data.templates || []).map((row) => `<div class="field"><label>${esc(row.name)} subject</label><input data-template="${esc(row.key)}" data-part="subject" value="${esc(row.subject)}"></div><div class="field"><label>Body</label><textarea data-template="${esc(row.key)}" data-part="body">${esc(row.body)}</textarea></div><button class="btn secondary small" type="button" data-save-template="${esc(row.key)}">Save ${esc(row.name)}</button>`).join("")}
      <div class="field"><label>Team BCC</label><input id="team-bcc" value="${esc(data.team_bcc || "")}" placeholder="team@company.com"></div>
      <button class="btn small" type="button" id="save-bcc">Save BCC</button>`;
    host.addEventListener("click", async (event) => {
      const key = event.target.getAttribute("data-save-template");
      if (key) {
        const subject = host.querySelector(`[data-template="${key}"][data-part="subject"]`).value;
        const body = host.querySelector(`[data-template="${key}"][data-part="body"]`).value;
        await api("/api/outreach/templates/" + key, {method: "PUT", body: {subject, body}});
        toast("Template saved");
      }
      if (event.target.id === "save-bcc") {
        await api("/api/outreach/bcc", {method: "PUT", body: {team_bcc: $("team-bcc").value}});
        toast("Team BCC saved");
      }
      const take = event.target.getAttribute("data-take");
      if (take) {
        await api("/api/leads/" + take + "/takeover", {method: "POST"});
        toast("You took over the lead");
        due();
      }
    });
  }

  document.addEventListener("click", (event) => {
    if (event.target.id === "coverage-leave") {
      api("/api/me/coverage", {method: "PUT", body: {on_leave: event.target.checked}}).catch((error) => toast(error.message));
    }
  });

  window.LeadOutreach = {panel, mount, due, settings};
})();
