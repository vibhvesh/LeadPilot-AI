const TAB_MODULE = {
  overview: "dashboard", leads: "leads", pipeline: "pipeline", followups: "followups",
  team: "team", reports: "reports", grokbot: "grokbot", bots: "dashboard", users: "users", search: "search",
  apis: "apikeys", ai: "ai", geo: "geo", activity: "activity", updates: "comments", settings: "settings",
};
const ROLE_LABEL = {super_admin: "Super Admin", admin: "Admin", member: "Member"};
const state = {me: null, leads: [], selectedLead: null, selectedUser: null, modules: [], roles: {}};

const $ = (id) => document.getElementById(id);
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[ch]));
}
function pill(status) {
  const warm = status === "Contacted" || status === "Lost" || status === "pending" || status === "rejected";
  return `<span class="status${warm ? " pending" : ""}">${esc(status)}</span>`;
}
function money(value) {
  const amount = Number(value) || 0;
  if (amount >= 100000) {
    const lakhs = amount / 100000;
    return "₹" + (lakhs >= 10 ? Math.round(lakhs) : lakhs.toFixed(1)) + "L";
  }
  return "₹" + amount.toLocaleString("en-IN");
}
function percent(value) { return ((Number(value) || 0) * 100).toFixed(1) + "%"; }
function can(module, manage = false) {
  const flags = (state.me && state.me.permissions[module]) || {};
  return manage ? !!flags.manage : !!(flags.view || flags.manage);
}
function toast(text) {
  const el = $("toast");
  el.hidden = false;
  el.textContent = text;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { el.hidden = true; }, 2800);
}
async function api(path, options = {}) {
  const opts = {credentials: "same-origin", headers: {}, ...options};
  if (opts.body && typeof opts.body !== "string") {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(path, opts);
  if (res.status === 401) { location.href = "/login"; throw new Error("Sign-in required"); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Request failed");
  return data;
}
function greeting(name) {
  const hour = new Date().getHours();
  const part = hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening";
  const first = (name || "there").split(" ")[0];
  return `Good ${part}, ${first}`;
}
function show(tab, options = {}) {
  document.querySelectorAll(".tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
  document.querySelectorAll(".page").forEach((page) => page.classList.toggle("active", page.id === tab));
  history.replaceState(null, "", options.url || ("#" + tab));
  const loader = loaders[tab];
  if (loader) loader().catch((error) => toast(error.message));
}

function readLeadRoute() {
  const path = location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/leads" || path.endsWith("/leads")) {
    const params = new URLSearchParams(location.search);
    return {id: params.get("id"), status: params.get("status")};
  }
  const hash = location.hash.replace(/^#/, "");
  if (hash === "leads" || hash.startsWith("leads?")) {
    const params = new URLSearchParams(hash.includes("?") ? hash.slice(hash.indexOf("?") + 1) : "");
    return {id: params.get("id"), status: params.get("status")};
  }
  return null;
}

document.querySelectorAll(".tab").forEach((button) => button.addEventListener("click", () => show(button.dataset.tab)));
document.querySelectorAll("[data-jump]").forEach((button) => button.addEventListener("click", () => show(button.dataset.jump)));
$("signout").addEventListener("click", async () => { await fetch("/auth/logout", {method: "POST"}); location.href = "/login"; });

function missingProviders() {
  const notes = [];
  if (state.me && !state.me.search_provider) notes.push("No search provider configured. Add a Tavily or Brave key on API keys before running a search.");
  if (state.me && !state.me.llm_provider) notes.push("No LLM provider configured. Add an xAI, Gemini, or OpenAI key before research, scoring, or outreach.");
  return notes;
}
function showProviderStatus() {
  const text = missingProviders().join(" ");
  ["provider-status", "search-provider-status", "agent-provider-status", "ai-provider-status"].forEach((id) => {
    const node = $(id);
    if (!node) return;
    node.hidden = !text;
    node.textContent = text;
  });
}
function applyAccess() {
  document.querySelectorAll(".tab").forEach((button) => { button.hidden = !can(TAB_MODULE[button.dataset.tab]); });
  document.querySelectorAll("[data-manage]").forEach((el) => { el.hidden = !can(el.dataset.manage, true); });
  const badge = $("pending-badge");
  if (state.me.pending_users) { badge.hidden = false; badge.textContent = state.me.pending_users; }
  else badge.hidden = true;
  $("who-email").textContent = state.me.email;
  $("who-role").textContent = ROLE_LABEL[state.me.role] || state.me.role;
  $("greeting").textContent = greeting(state.me.name || state.me.email);
  const bits = [];
  if (state.me.demo_mode) bits.push("DEMO SIGN-IN");
  if (state.me.llm_provider || state.me.search_provider) bits.push("LIVE PROVIDERS");
  $("mode-pill").textContent = bits.join(" · ") || "WORKSPACE";
  showProviderStatus();
  $("role-save").hidden = state.me.role !== "super_admin";
}

async function boot() {
  state.me = await api("/api/me");
  applyAccess();
  const route = readLeadRoute();
  const wanted = location.hash.slice(1).split("?")[0];
  const first = document.querySelector(".tab:not([hidden])");
  if (route && can("leads")) {
    const status = route.status || "";
    if (status && [...$("lead-status").options].some((option) => option.value === status)) $("lead-status").value = status;
    if (route.id && Number(route.id)) {
      state.selectedLead = Number(route.id);
      state.previewOnLoad = true;
    }
    show("leads", {url: "/leads" + location.search});
  } else if (wanted && document.getElementById(wanted) && can(TAB_MODULE[wanted])) show(wanted);
  else if (first) show(first.dataset.tab);
}

const loaders = {
  overview: loadOverview,
  leads: loadLeads,
  pipeline: loadPipeline,
  followups: loadFollowups,
  team: loadTeam,
  reports: loadReports,
  grokbot: loadGrok,
  bots: loadBots,
  users: loadUsers,
  search: loadSearch,
  apis: loadApis,
  ai: loadAi,
  geo: loadGeo,
  activity: loadActivity,
  updates: loadComments,
  settings: loadSettings,
};

async function loadOverview() {
  const data = await api("/api/dashboard");
  $("m-total").textContent = data.total_leads;
  $("m-qualified").textContent = data.qualified_leads;
  $("m-value").textContent = money(data.pipeline_value);
  $("m-rate").textContent = percent(data.conversion_rate);
  $("m-follow").textContent = data.followups_due + " follow-ups open · won / all leads";
  $("start-banner").hidden = data.total_leads > 0;
  $("recent-leads").innerHTML = data.recent_leads.length ? data.recent_leads.map((lead) =>
    `<tr class="clicky" data-preview-lead="${lead.id}"><td>${esc(lead.contact_name || "—")}</td><td>${esc(lead.company)}</td><td>${esc(lead.region || "—")}</td><td>${lead.score ?? "—"}</td><td>${pill(lead.status)}</td></tr>`
  ).join("") : `<tr><td colspan="5">No leads yet.</td></tr>`;
  const admin = data.admin;
  $("admin-summary").innerHTML = admin ? `
    <div class="item"><b>Pending approval</b>${admin.pending} account${admin.pending === 1 ? "" : "s"}</div>
    <div class="item"><b>Approved people</b>${admin.approved}</div>
    <div class="item"><b>New user policy</b>${esc(admin.policy)}</div>` : `<div class="item"><b>Your role</b>${esc(ROLE_LABEL[state.me.role] || state.me.role)}</div>`;
}

async function ensureLeads() {
  state.leads = await api("/api/leads");
  return state.leads;
}
function fillLeadSelect(select, placeholder) {
  const current = select.value;
  select.innerHTML = `<option value="">${esc(placeholder || "Select a lead")}</option>` + state.leads.map((lead) => `<option value="${lead.id}">${esc(lead.company)}</option>`).join("");
  if (current) select.value = current;
}

async function loadLeads() {
  const params = new URLSearchParams();
  if ($("lead-q").value.trim()) params.set("q", $("lead-q").value.trim());
  if ($("lead-status").value) params.set("status", $("lead-status").value);
  const query = params.toString();
  state.leads = await api("/api/leads" + (query ? "?" + query : ""));
  $("lead-rows").innerHTML = state.leads.length ? state.leads.map((lead) =>
    `<tr class="clicky" data-preview-lead="${lead.id}"><td>${esc(lead.company)}</td><td>${esc(lead.contact_name || "—")}<div class="muted">${esc(lead.email || "")}</div></td><td>${esc(lead.source)}</td><td>${esc(lead.region || "—")}</td><td>${lead.score ?? "—"}</td><td>${pill(lead.status)}</td></tr>`
  ).join("") : `<tr><td colspan="6">No leads match. Run a search or add one.</td></tr>`;
  if (state.selectedLead) openLead(state.selectedLead, {preview: !!state.previewOnLoad});
  state.previewOnLoad = false;
}

const LEAD_STATUSES = ["New", "Contacted", "Qualified", "Won", "Lost"];

async function openLead(id, opts = {}) {
  let lead = state.leads.find((item) => item.id === id);
  if (!lead) {
    try { lead = await api("/api/leads/" + id); }
    catch (error) { toast(error.message); return; }
  }
  state.selectedLead = id;
  const manage = can("leads", true);
  const statusOptions = LEAD_STATUSES.map((status) => `<option value="${esc(status)}" ${lead.status === status ? "selected" : ""}>${esc(status)}</option>`).join("");
  $("lead-detail").innerHTML = `${window.LeadSummary ? LeadSummary.render(lead) : ""}
    <div class="note"><b>${esc(lead.company)}</b> ${esc(lead.qualification_summary || "Not scored yet.")}</div>
    <div class="split3">
      <div class="item"><b>Contact</b>${esc(lead.contact_name || "—")}<div class="muted">${esc(lead.email || "No email")} · ${esc(lead.phone || "No phone")}</div></div>
      <div class="item"><b>Location</b>${esc([lead.city, lead.district, lead.state, lead.country, lead.postal_code].filter(Boolean).join(", ") || "—")}</div>
      <div class="item"><b>Web</b>${lead.website ? `<a href="${esc(lead.website)}" target="_blank" rel="noreferrer">${esc(lead.website)}</a>` : "No website yet"}</div>
    </div>
    <div class="field"><label>Notes</label><textarea id="detail-notes">${esc(lead.notes || "")}</textarea></div>
    <div class="row">
      ${manage ? `<div class="field" style="margin:0"><label for="detail-status">Move to column</label><select id="detail-status">${statusOptions}</select></div>
      <button class="btn small" type="button" id="detail-move">Move</button>
      <button class="btn secondary small" type="button" id="detail-save">Save notes</button>` : ""}
      <button class="btn secondary small" type="button" id="detail-agent">Score in GrokBot</button>
    </div>
    <div class="list" id="detail-comments" style="margin-top:12px"></div>`;
  api("/api/comments?lead_id=" + id).then((rows) => {
    const host = $("detail-comments");
    if (!host) return;
    host.innerHTML = rows.map((row) => `<div class="item"><b>${esc(row.author_name || row.author_email)}</b>${esc(row.body)}</div>`).join("") || `<div class="muted">No comments on this lead.</div>`;
  }).catch(() => {});
  $("detail-agent").onclick = () => { $("agent-lead").dataset.prefer = String(id); show("grokbot"); };
  if (manage) {
    $("detail-save").onclick = async () => {
      try {
        await api("/api/leads/" + id, {method: "PATCH", body: {notes: $("detail-notes").value}});
        toast("Notes saved");
        loadLeads();
      } catch (error) { toast(error.message); }
    };
    $("detail-move").onclick = async () => {
      const status = $("detail-status").value;
      try {
        if (status === "Qualified") await api("/api/leads/" + id + "/review", {method: "POST", body: {decision: "qualify"}});
        else await api("/api/leads/" + id, {method: "PATCH", body: {status}});
        toast("Moved to " + status);
        if ($("lead-status") && $("lead-status").value && $("lead-status").value !== status) $("lead-status").value = status;
        history.replaceState(null, "", "/leads?id=" + id);
        loadLeads();
      } catch (error) { toast(error.message); }
    };
  }
  if (opts.preview && window.LeadPreview) LeadPreview.show(lead);
}

$("toggle-lead-form").addEventListener("click", () => { $("lead-form").hidden = !$("lead-form").hidden; });
$("reload-leads").addEventListener("click", () => loadLeads().catch((error) => toast(error.message)));
$("save-lead").addEventListener("click", async () => {
  $("lead-error").textContent = "";
  try {
    await api("/api/leads", {method: "POST", body: {
      company: $("lead-company").value, contact_name: $("lead-contact").value, email: $("lead-email").value,
      phone: $("lead-phone").value, website: $("lead-website").value, industry: $("lead-industry").value,
      country: $("lead-country").value, state: $("lead-state").value, city: $("lead-city").value, notes: $("lead-notes").value,
    }});
    $("lead-form").hidden = true;
    toast("Lead added");
    loadLeads();
    document.dispatchEvent(new CustomEvent("leadpilot:mascot", {detail: {
      text: "New lead!",
      selector: "#lead-rows [data-preview-lead]",
      href: "/leads?status=New",
    }}));
  } catch (error) { $("lead-error").textContent = error.message; }
});

async function loadPipeline() {
  const data = await api("/api/pipeline");
  $("pipeline-board").innerHTML = window.PipelineBoard.render(data);
}

async function loadFollowups() {
  await ensureLeads();
  fillLeadSelect($("fu-lead"), "Workspace reminder");
  const rows = await api("/api/followups");
  $("fu-list").innerHTML = rows.length ? rows.map((row) => `
    <div class="item"><b>${esc(row.title)}</b><span class="muted">${esc(row.company || "Workspace")} · ${row.due_at ? esc(new Date(row.due_at).toLocaleString()) : "No due date"} · ${esc(row.status)}</span>
    ${row.status === "open" && can("followups", true) ? `<div><button class="btn small secondary" type="button" data-done="${row.id}">Mark done</button></div>` : ""}</div>`).join("") : `<div class="muted">No follow-ups yet.</div>`;
  $("fu-list").querySelectorAll("[data-done]").forEach((button) => button.addEventListener("click", async () => {
    await api("/api/followups/" + button.dataset.done, {method: "PATCH", body: {status: "done"}});
    loadFollowups();
  }));
}
$("fu-save").addEventListener("click", async () => {
  try {
    const due = $("fu-due").value ? new Date($("fu-due").value).toISOString() : null;
    await api("/api/followups", {method: "POST", body: {title: $("fu-title").value, lead_id: $("fu-lead").value || null, due_at: due, notes: $("fu-notes").value}});
    $("fu-title").value = ""; $("fu-notes").value = "";
    toast("Follow-up saved");
    loadFollowups();
  } catch (error) { toast(error.message); }
});

async function loadTeam() {
  const rows = await api("/api/team");
  $("team-list").innerHTML = rows.map((row) => `<div class="item"><b>${esc(row.name || row.email)}</b>${esc(ROLE_LABEL[row.role] || row.role)} · ${esc(row.email)}</div>`).join("") || `<div class="muted">No approved members yet.</div>`;
}

async function loadReports() {
  const data = await api("/api/reports");
  const cards = [
    ["Leads this month", data.leads_this_month],
    ["Qualified or won", data.qualified],
    ["Conversion", percent(data.conversion_rate)],
    ["Saved searches", data.active_campaigns],
  ];
  $("report-stats").innerHTML = cards.map(([label, value]) => `<div class="card"><div class="label">${esc(label)}</div><div class="num">${esc(value)}</div></div>`).join("");
  $("report-countries").innerHTML = data.by_country.length ? data.by_country.map((row) => `<div class="activity"><div><b>${esc(row.country)}</b></div><span>${row.count}</span></div>`).join("") : `<div class="muted">No countries recorded yet.</div>`;
}

async function loadGrok() {
  await ensureLeads();
  const prefer = $("agent-lead").dataset.prefer;
  fillLeadSelect($("agent-lead"), "Choose a lead");
  if (prefer) $("agent-lead").value = prefer;
  const leadId = Number($("agent-lead").value || 0);
  if (!leadId) { $("agent-steps").innerHTML = `<div class="muted">Choose a lead to see previous runs.</div>`; return; }
  const runs = await api("/api/agents/runs?lead_id=" + leadId);
  renderRun(runs[0]);
}
function renderRun(run) {
  if (!run) {
    $("agent-steps").innerHTML = `<div class="item">Head Thinker / Orchestrator</div><div class="item">Company Research</div><div class="item">Enrichment</div><div class="item">Lead qualification</div><div class="item">Outreach draft</div><div class="item">Quality and deduplication</div>`;
    $("draft-subject").value = "";
    $("draft-body").textContent = "Run the pipeline to write a draft. It stays a draft.";
    $("agent-meta").textContent = "";
    return;
  }
  $("agent-meta").textContent = `Provider ${run.provider} · ${run.model || "default"} · score ${run.score} · recommendation ${run.recommend_qualify ? "review for qualification" : "hold"} · status ${run.lead_status || "unchanged"}`;
  $("agent-steps").innerHTML = (run.steps || []).map((step) => `<div class="step"><b>${esc(step.title)}</b><div>${esc(step.summary || "")}</div></div>`).join("");
  $("draft-subject").value = (run.outreach && run.outreach.subject) || "";
  $("draft-body").textContent = (run.outreach && run.outreach.body) || "";
}
$("agent-lead").addEventListener("change", () => loadGrok().catch((error) => toast(error.message)));
$("agent-run").addEventListener("click", async () => {
  const leadId = Number($("agent-lead").value || 0);
  if (!leadId) { toast("Choose a lead first"); return; }
  $("agent-run").disabled = true;
  try {
    const run = await api("/api/agents/run", {method: "POST", body: {lead_id: leadId}});
    renderRun(run);
    toast(run.recommend_qualify ? "Scored. Ready for your review." : "Scored. Left as not qualified.");
  } catch (error) {
    $("agent-meta").textContent = error.message;
    $("agent-steps").innerHTML = `<div class="muted">The pipeline did not run. No score or outreach draft was saved.</div>`;
    $("draft-subject").value = "";
    $("draft-body").textContent = error.message;
    toast(error.message);
  }
  finally { $("agent-run").disabled = false; }
});
async function reviewSelected(decision) {
  const leadId = Number($("agent-lead").value || 0);
  if (!leadId) return;
  await api("/api/leads/" + leadId + "/review", {method: "POST", body: {decision}});
  toast(decision === "qualify" ? "Marked qualified" : "Marked lost");
  loadGrok();
}
$("agent-qualify").addEventListener("click", () => reviewSelected("qualify").catch((error) => toast(error.message)));
$("agent-reject").addEventListener("click", () => reviewSelected("reject").catch((error) => toast(error.message)));

function matrix(host, permissions, attribute) {
  const modules = state.modules.length ? state.modules : Object.keys(permissions).map((key) => ({key, label: key}));
  host.innerHTML = `<div class="checks"><b>Module</b><b>View</b><b>Manage</b></div>` + modules.map((module) => {
    const flags = permissions[module.key] || {view: false, manage: false};
    return `<label class="checks"><span>${esc(module.label || module.key)}</span><input type="checkbox" ${attribute}="${module.key}:view" ${flags.view ? "checked" : ""}><input type="checkbox" ${attribute}="${module.key}:manage" ${flags.manage ? "checked" : ""}></label>`;
  }).join("");
}
function readMatrix(host, attribute) {
  const permissions = {};
  host.querySelectorAll("[" + attribute + "]").forEach((input) => {
    const [module, flag] = input.getAttribute(attribute).split(":");
    permissions[module] = permissions[module] || {view: false, manage: false};
    permissions[module][flag] = input.checked;
    if (flag === "manage" && input.checked) permissions[module].view = true;
  });
  return permissions;
}

async function loadUsers() {
  const data = await api("/api/users");
  state.modules = data.modules;
  state.roles = data.roles;
  $("user-rows").innerHTML = data.users.map((user) => `<tr>
    <td><button class="linkish" type="button" data-user="${user.id}">${esc(user.email)}</button><div class="muted">${esc(user.name || "")}</div></td>
    <td>${esc(ROLE_LABEL[user.role] || user.role)}</td>
    <td>${pill(user.status === "approved" ? "Approved" : user.status === "pending" ? "Pending" : "Rejected")}</td>
    <td>${can("users", true) && user.role !== "super_admin" ? `<div class="row">
      ${user.status !== "approved" ? `<button class="btn small" type="button" data-approve="${user.id}">Approve</button>` : ""}
      ${user.status !== "rejected" ? `<button class="btn small danger" type="button" data-reject="${user.id}">Reject</button>` : ""}
      <select data-role="${user.id}"><option value="member" ${user.role === "member" ? "selected" : ""}>Member</option><option value="admin" ${user.role === "admin" ? "selected" : ""}>Admin</option></select>
    </div>` : ""}</td></tr>`).join("");
  $("user-rows").querySelectorAll("[data-approve]").forEach((button) => button.addEventListener("click", () => decide(button.dataset.approve, "approve")));
  $("user-rows").querySelectorAll("[data-reject]").forEach((button) => button.addEventListener("click", () => decide(button.dataset.reject, "reject")));
  $("user-rows").querySelectorAll("[data-role]").forEach((select) => select.addEventListener("change", async () => {
    try { await api("/api/users/" + select.dataset.role, {method: "PATCH", body: {role: select.value}}); toast("Role updated"); loadUsers(); }
    catch (error) { toast(error.message); loadUsers(); }
  }));
  $("user-rows").querySelectorAll("[data-user]").forEach((button) => button.addEventListener("click", () => selectUser(Number(button.dataset.user))));
  renderRoleTemplate();
  if (state.selectedUser) selectUser(state.selectedUser);
}
async function decide(id, decision) {
  await api("/api/users/" + id + "/decision", {method: "POST", body: {decision}});
  state.me = await api("/api/me");
  applyAccess();
  toast(decision === "approve" ? "Account approved" : "Account rejected");
  loadUsers();
}
async function selectUser(id) {
  state.selectedUser = id;
  const user = await api("/api/users/" + id);
  $("perm-target").textContent = user.email + " · " + (ROLE_LABEL[user.role] || user.role);
  matrix($("perm-grid"), user.permissions, "data-userperm");
}
function renderRoleTemplate() {
  const role = $("role-template").value;
  matrix($("role-grid"), state.roles[role] || {}, "data-roleperm");
}
$("role-template").addEventListener("change", renderRoleTemplate);
$("perm-save").addEventListener("click", async () => {
  if (!state.selectedUser) { toast("Select a user first"); return; }
  await api("/api/users/" + state.selectedUser + "/permissions", {method: "PUT", body: {permissions: readMatrix($("perm-grid"), "data-userperm")}});
  toast("Permissions saved");
});
$("perm-clear").addEventListener("click", async () => {
  if (!state.selectedUser) return;
  await api("/api/users/" + state.selectedUser + "/permissions", {method: "PUT", body: {permissions: {}}});
  toast("Using role defaults");
  selectUser(state.selectedUser);
});
$("role-save").addEventListener("click", async () => {
  const role = $("role-template").value;
  try {
    await api("/api/permissions/roles/" + role, {method: "PUT", body: {permissions: readMatrix($("role-grid"), "data-roleperm")}});
    toast("Role template saved");
    loadUsers();
  } catch (error) { toast(error.message); }
});

async function loadSearch() {
  if (window.SearchForm) await SearchForm.refresh();
  const [saved, runs] = await Promise.all([api("/api/search/criteria"), api("/api/search/runs")]);
  $("s-list").innerHTML = saved.map((row) => `<div class="item"><b>${esc(row.name)}</b><div class="muted">${esc([row.industry, row.keywords, row.city, row.country].filter(Boolean).join(" · "))}</div>
    ${can("search", true) ? `<div class="row"><button class="btn small" type="button" data-run="${row.id}">Run again</button><button class="btn small secondary" type="button" data-del="${row.id}">Delete</button></div>` : ""}</div>`).join("")
    + (runs.length ? `<div class="muted" style="margin-top:8px">Latest run: ${esc(runs[0].provider)} · ${runs[0].created_count} new · ${runs[0].duplicate_count} duplicates</div>` : "");
  if (!saved.length) $("s-list").innerHTML = `<div class="muted">No saved profiles yet.</div>`;
  $("s-list").querySelectorAll("[data-run]").forEach((button) => button.addEventListener("click", () => runSearch(button.dataset.run)));
  $("s-list").querySelectorAll("[data-del]").forEach((button) => button.addEventListener("click", async () => {
    await api("/api/search/criteria/" + button.dataset.del, {method: "DELETE"});
    loadSearch();
  }));
  await loadAiSearch();
}
function renderPlan(plan) {
  if (!plan) return "";
  const queries = (plan.queries || []).map((query) => `<div class="item">${esc(query)}</div>`).join("");
  return `<div class="item"><b>Profile</b>${esc(plan.profile || "")}</div>
    <div class="item"><b>Locations</b>${esc((plan.locations || []).join(", ") || "—")}</div>
    <div class="item"><b>Signals</b>${esc((plan.signals || []).join(", ") || "—")}</div>
    <div class="list">${queries}</div>`;
}
async function loadAiSearch() {
  const [ai, deep] = await Promise.all([api("/api/search/ai"), api("/api/search/deep")]);
  const counts = ai.sources || {};
  $("source-counts").textContent = `Leads from the app: ${counts.app || 0} · Leads from Grok Bot: ${counts.grokbot || 0}`;
  const latest = (ai.runs || [])[0];
  if (latest) {
    const sources = (latest.sources || []).slice(0, 6).map((source) => `<div class="item"><b>${esc(source.title || source.provider)}</b><div class="muted">${esc(source.provider)} · ${esc(source.url || "")}</div></div>`).join("");
    const providers = (latest.providers || []).filter(Boolean).join(", ") || "none";
    $("ai-output").innerHTML = `<div class="note">Round ${latest.rounds}. Saved ${latest.created_count} lead${latest.created_count === 1 ? "" : "s"} and skipped ${latest.duplicate_count} duplicate${latest.duplicate_count === 1 ? "" : "s"}. Provider ${esc(providers)}.</div>${renderPlan(latest.plan)}${sources}`;
  } else {
    const notes = missingProviders();
    $("ai-output").innerHTML = notes.length ? notes.map((note) => `<div class="error">${esc(note)}</div>`).join("") : `<div class="muted">No AI searches yet.</div>`;
  }
  $("deep-list").innerHTML = (deep || []).map((row) => `<div class="item"><b>${esc(row.status)}</b> ${esc(row.text)}<div class="muted">${row.lead_count} Grok Bot lead${row.lead_count === 1 ? "" : "s"} · webhook ${esc(row.webhook_status)}</div></div>`).join("") || "";
}
$("ai-run").addEventListener("click", async () => {
  try {
    const criteria = window.SearchForm ? SearchForm.payload("ai") : {};
    const result = await api("/api/search/ai", {method: "POST", body: {text: $("ai-text").value, criteria}});
    toast(`Saved ${result.created_count} leads`);
    loadSearch();
  } catch (error) {
    $("ai-output").innerHTML = `<div class="error">${esc(error.message)}</div><div class="muted">No leads were saved.</div>`;
    toast(error.message);
  }
});
$("ai-deep").addEventListener("click", async () => {
  try {
    const criteria = window.SearchForm ? SearchForm.payload("ai") : {};
    const extra = (criteria.query_templates || []).join("\n");
    const text = [$("ai-text").value.trim(), extra].filter(Boolean).join("\n");
    const result = await api("/api/search/deep", {method: "POST", body: {text}});
    toast(result.webhook_status === "sent" ? "Grok Bot notified" : "Deep search queued");
    loadSearch();
  } catch (error) {
    $("ai-output").innerHTML = `<div class="error">${esc(error.message)}</div>`;
    toast(error.message);
  }
});
async function runSearch(id) {
  $("s-error").textContent = "";
  try {
    const result = await api("/api/search/criteria/" + id + "/run", {method: "POST"});
    const saved = Number(result.created_count || 0) + Number(result.duplicate_count || 0);
    $("s-result").innerHTML = saved
      ? `<div class="note">Provider <b>${esc(result.provider)}</b>. Saved ${result.created_count} new lead${result.created_count === 1 ? "" : "s"} and skipped ${result.duplicate_count} duplicate${result.duplicate_count === 1 ? "" : "s"}.</div>`
      : `<div class="muted">The search returned no leads.</div>`;
    toast("Search finished");
    loadSearch();
  } catch (error) {
    $("s-error").textContent = error.message;
    $("s-result").innerHTML = `<div class="muted">No leads were saved.</div>`;
    toast(error.message);
  }
}
$("s-save").addEventListener("click", async () => {
  $("s-error").textContent = "";
  try {
    const saved = await api("/api/search/criteria", {method: "POST", body: SearchForm.payload("saved")});
    await runSearch(saved.id);
  } catch (error) { $("s-error").textContent = error.message; }
});

async function loadApis() {
  const data = await api("/api/providers");
  $("key-rows").innerHTML = data.keys.map((row) => `<tr><td>${esc(row.provider)}</td><td>${row.configured ? esc(row.source) : "Not set"}</td><td>${esc(row.hint || "—")}</td><td>${row.database_copy && can("apikeys", true) ? `<button class="btn small secondary" type="button" data-forget="${esc(row.provider)}">Remove saved key</button>` : ""}</td></tr>`).join("");
  $("key-rows").querySelectorAll("[data-forget]").forEach((button) => button.addEventListener("click", async () => {
    await api("/api/providers/keys/" + button.dataset.forget, {method: "DELETE"});
    toast("Removed the saved copy");
    loadApis();
  }));
  $("usage-list").innerHTML = data.usage.map((row) => `<div class="item"><b>${esc(row.provider)}</b>${row.enabled ? "Enabled" : "Disabled"} · today ${row.used_today}/${row.daily_quota} · month ${row.used_this_month}/${row.monthly_quota}</div>`).join("");
}
$("key-save").addEventListener("click", async () => {
  try {
    const saved = await api("/api/providers/keys", {method: "PUT", body: {provider: $("key-provider").value, api_key: $("key-value").value}});
    $("key-value").value = "";
    toast("Stored " + saved.hint);
    loadApis();
  } catch (error) { toast(error.message); }
});
$("acc-save").addEventListener("click", async () => {
  try {
    await api("/api/providers/access", {method: "PUT", body: {
      provider: $("acc-provider").value, role: $("acc-role").value, enabled: $("acc-enabled").value === "true",
      daily_quota: Number($("acc-daily").value), monthly_quota: Number($("acc-monthly").value),
    }});
    toast("Access updated");
    loadApis();
  } catch (error) { toast(error.message); }
});

async function loadAi() {
  const data = await api("/api/ai/config");
  $("ai-primary").value = data.primary_provider;
  $("ai-model").value = data.primary_model || "";
  $("ai-fallback").value = data.fallback_provider;
  $("ai-temp").value = data.temperature;
  $("ai-tokens").value = data.max_tokens;
  $("ai-effective").textContent = `Effective provider: ${data.effective.provider} (${data.effective.model}). ${data.effective.note || ""}`;
}
$("ai-save").addEventListener("click", async () => {
  try {
    await api("/api/ai/config", {method: "PUT", body: {
      primary_provider: $("ai-primary").value, primary_model: $("ai-model").value, fallback_provider: $("ai-fallback").value,
      temperature: Number($("ai-temp").value), max_tokens: Number($("ai-tokens").value),
    }});
    toast("AI settings saved");
    state.me = await api("/api/me");
    applyAccess();
    loadAi();
  } catch (error) { toast(error.message); }
});

async function loadGeo() {
  const data = await api("/api/geo");
  $("g-country").value = data.country || "";
  $("g-state").value = data.state || "";
  $("g-district").value = data.district || "";
  $("g-city").value = data.city || "";
  $("g-postal").value = data.postal_code || "";
  $("g-radius").value = data.radius_km ?? "";
}
$("g-save").addEventListener("click", async () => {
  await api("/api/geo", {method: "PUT", body: {
    country: $("g-country").value, state: $("g-state").value, district: $("g-district").value,
    city: $("g-city").value, postal_code: $("g-postal").value, radius_km: $("g-radius").value,
  }});
  toast("Geographic target saved");
});

async function loadActivity() {
  const [summary, events] = await Promise.all([api("/api/activity/summary"), api("/api/activity")]);
  const cards = [["Activities today", summary.activities_today], ["API calls", summary.api_calls], ["Searches", summary.searches], ["Failed", summary.failed_requests]];
  $("activity-stats").innerHTML = cards.map(([label, value]) => `<div class="card"><div class="label">${label}</div><div class="num">${value}</div></div>`).join("");
  $("activity-list").innerHTML = events.map((event) => `<div class="activity"><div><b>${esc(event.email || "System")}</b><div class="label">${esc(event.action)}${event.module ? " · " + esc(event.module) : ""}${event.success ? "" : " · failed"}</div></div><span class="label">${esc(event.created_at ? new Date(event.created_at).toLocaleString() : "")}</span></div>`).join("") || `<div class="muted">No events yet.</div>`;
}

async function loadComments() {
  const rows = await api("/api/comments");
  $("comment-list").innerHTML = rows.length ? rows.map((row) => `<div class="item"><b>${esc(row.author_name || row.author_email)}</b>${esc(row.body)}<div class="muted">${esc(row.created_at ? new Date(row.created_at).toLocaleString() : "")}</div></div>`).join("") : `<div class="item"><b>No updates yet</b><span class="muted">Post the first workspace note.</span></div>`;
}
$("comment-save").addEventListener("click", async () => {
  try {
    await api("/api/comments", {method: "POST", body: {body: $("comment-body").value}});
    $("comment-body").value = "";
    toast("Posted");
    loadComments();
  } catch (error) { toast(error.message); }
});

async function loadSettings() {
  const data = await api("/api/settings");
  $("set-workspace").value = data.workspace_name;
  $("set-product").value = data.product_name;
  $("set-currency").value = data.currency;
  $("set-retention").value = data.retention_days;
  $("set-seller").value = data.seller_name || "";
  $("set-offering").value = data.offering || "";
  $("set-customer").value = data.ideal_customer || "";
  if (window.SearchForm) await SearchForm.mountSettings(data);
  const tokens = await api("/api/settings/bot-tokens");
  $("bot-tokens").innerHTML = tokens.map((token) => `<div class="item"><b>${esc(token.name)}</b> ${esc(token.hint)} · ${token.revoked ? "Revoked" : "Active"}
    ${!token.revoked && can("settings", true) ? `<div><button class="btn small secondary" type="button" data-revoke="${token.id}">Revoke</button></div>` : ""}</div>`).join("") || `<div class="muted">No bot tokens yet.</div>`;
  $("bot-tokens").querySelectorAll("[data-revoke]").forEach((button) => button.addEventListener("click", async () => {
    await api("/api/settings/bot-tokens/" + button.dataset.revoke, {method: "DELETE"});
    toast("Token revoked");
    loadSettings();
  }));
  $("set-info").innerHTML = [
    ["Workspace", data.workspace_name], ["Product", data.product_name], ["Authentication", data.authentication],
    ["Database", data.database], ["Demo mode", data.demo_mode ? "On" : "Off"], ["Super Admin", data.super_admin],
  ].map(([label, value]) => `<div class="item"><b>${esc(label)}</b>${esc(value)}</div>`).join("");
}
$("set-save").addEventListener("click", async () => {
  const icp = window.SearchForm ? SearchForm.icpPayload() : {};
  await api("/api/settings", {method: "PUT", body: {
    workspace_name: $("set-workspace").value, product_name: $("set-product").value,
    seller_name: $("set-seller").value, offering: $("set-offering").value, ideal_customer: $("set-customer").value,
    currency: $("set-currency").value, retention_days: Number($("set-retention").value),
    ...icp,
  }});
  toast("Settings saved");
  loadSettings();
});

$("bot-create").addEventListener("click", async () => {
  try {
    const created = await api("/api/settings/bot-tokens", {method: "POST", body: {name: $("bot-name").value}});
    const box = $("bot-once");
    box.hidden = false;
    box.textContent = "Copy this token now. It will not be shown again: " + created.token;
    $("bot-name").value = "";
    loadSettings();
  } catch (error) { toast(error.message); }
});

const talk = {connectionId: null, name: "", approved: false, refreshing: false};
async function loadBots() {
  const rows = await api("/api/bots");
  talk.rows = rows;
  $("bot-connections").innerHTML = rows.length ? rows.map((row) => `<div class="item"><b>${esc(row.name)}</b> ${pill(row.status)}
    <div class="muted">${esc(row.description || "No description")}${row.user_email ? " · " + esc(row.user_email) : ""}${row.unread ? " · " + row.unread + " unread" : ""}</div>
    <div class="row">
      <button class="btn small secondary" type="button" data-open-bot="${row.id}">Open</button>
      ${row.can_decide && row.status !== "approved" && row.status !== "revoked" ? `<button class="btn small" type="button" data-bot-decision="${row.id}" data-choice="approve">Approve</button>` : ""}
      ${row.can_decide && row.status !== "blocked" && row.status !== "revoked" ? `<button class="btn small secondary" type="button" data-bot-decision="${row.id}" data-choice="block">Block</button>` : ""}
      ${row.can_decide && row.status !== "revoked" ? `<button class="btn small danger" type="button" data-bot-decision="${row.id}" data-choice="revoke">Revoke</button>` : ""}
    </div></div>`).join("") : `<div class="muted">No bots have asked to talk yet.</div>`;
  $("bot-connections").querySelectorAll("[data-open-bot]").forEach((button) => button.addEventListener("click", () => openBot(Number(button.dataset.openBot))));
  $("bot-connections").querySelectorAll("[data-bot-decision]").forEach((button) => button.addEventListener("click", async () => {
    await api("/api/bots/" + button.dataset.botDecision + "/decision", {method: "POST", body: {decision: button.dataset.choice}});
    toast("Updated");
    loadBots();
  }));
  if (talk.connectionId) openBot(talk.connectionId);
}
async function openBot(id) {
  talk.connectionId = id;
  const row = (talk.rows || []).find((item) => item.id === id);
  if (row) { talk.name = row.name; talk.approved = row.status === "approved"; }
  $("chat-title").textContent = talk.name || "Chat";
  $("chat-compose").hidden = !talk.approved;
  const messages = await api("/api/bots/" + id + "/messages");
  $("chat-log").innerHTML = messages.map(renderChatMessage).join("") || `<div class="muted">No messages yet.</div>`;
  $("chat-log").querySelectorAll("[data-add-lead]").forEach((button) => button.addEventListener("click", () => addCardLead(button)));
}
function renderChatMessage(message) {
  const cards = (message.cards || []).map((card) => {
    if (card.type === "leads") {
      const leads = (card.leads || []).map((lead, index) => `<div class="item"><b>${esc(lead.company)}</b><div class="muted">${esc(lead.email || lead.city || "")}</div>${can("leads", true) ? `<button class="btn small" type="button" data-add-lead="${index}" data-lead='${esc(JSON.stringify(lead))}'>Add to pipeline</button>` : ""}</div>`).join("");
      return `<div class="note"><b>${esc(card.title || "Leads")}</b>${leads}</div>`;
    }
    return card.body ? `<div class="note">${esc(card.body)}</div>` : "";
  }).join("");
  return `<div class="item"><b>${message.sender === "bot" ? "Bot" : "You"}</b>${esc(message.text || "")}${cards}</div>`;
}
async function addCardLead(button) {
  const lead = JSON.parse(button.dataset.lead);
  lead.source = lead.source || "bot-chat";
  try {
    await api("/api/leads", {method: "POST", body: lead});
    toast("Added " + lead.company);
  } catch (error) { toast(error.message); }
}
$("chat-send").addEventListener("click", async () => {
  if (!talk.connectionId) return;
  try {
    await api("/api/bots/" + talk.connectionId + "/messages", {method: "POST", body: {text: $("chat-text").value}});
    $("chat-text").value = "";
    openBot(talk.connectionId);
  } catch (error) { toast(error.message); }
});
async function pollUnread() {
  try {
    const data = await api("/api/bots/unread");
    const badge = $("bots-badge");
    if (!badge) return;
    if (data.unread) { badge.hidden = false; badge.textContent = data.unread; }
    else badge.hidden = true;
    const page = document.getElementById("bots");
    if (talk.connectionId && page && page.classList.contains("active") && !talk.refreshing) {
      talk.refreshing = true;
      try { await openBot(talk.connectionId); } finally { talk.refreshing = false; }
    }
  } catch (error) { /* stay on the page if a poll fails */ }
}
setInterval(pollUnread, 8000);
window.LeadPilot = { $, api, esc, can, toast };

boot().then(() => {
  pollUnread();
  if (window.Hanuman) Hanuman.start();
}).catch((error) => { $("greeting").textContent = error.message; });
