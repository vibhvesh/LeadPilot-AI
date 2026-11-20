/* Owner, status, and close controls for the leads table. */
(function (root) {
  const STATUSES = ["New", "Contacted", "Replied", "Meeting set", "Proposal", "Qualified", "In review", "Won", "Lost", "Not a fit"];
  const CLOSED = ["Won", "Lost", "Not a fit"];
  let people = [];

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[char]));
  }

  async function ensurePeople() {
    const data = await root.api("/api/leads/assignees");
    people = data.users || [];
    const owner = document.getElementById("lead-owner");
    const bulk = document.getElementById("lead-bulk-owner");
    if (owner && owner.options.length <= 1) {
      owner.insertAdjacentHTML("beforeend", people.map((person) => `<option value="${person.id}">${esc(person.name)}</option>`).join(""));
    }
    if (bulk && bulk.options.length <= 1) {
      bulk.insertAdjacentHTML("beforeend", people.map((person) => `<option value="${person.id}">${esc(person.name)}</option>`).join(""));
      const status = document.getElementById("lead-bulk-status");
      if (status && status.options.length <= 1) {
        status.insertAdjacentHTML("beforeend", STATUSES.filter((item) => item !== "Qualified").map((item) => `<option>${esc(item)}</option>`).join(""));
      }
    }
    return people;
  }

  function statusSelect(lead) {
    const options = STATUSES.map((status) => `<option ${lead.status === status ? "selected" : ""}>${esc(status)}</option>`).join("");
    return `<select class="lead-status" data-lead="${lead.id}">${options}</select>`;
  }

  function ownerSelect(lead) {
    const options = [`<option value="">Unassigned</option>`].concat(people.map((person) => `<option value="${person.id}" ${Number(lead.owner_id) === person.id ? "selected" : ""}>${esc(person.name)}</option>`));
    return `<select class="lead-owner" data-lead="${lead.id}">${options.join("")}</select>`;
  }

  function isAdmin() {
    const role = document.documentElement.dataset.role || (root.state && root.state.me && root.state.me.role) || "";
    return role === "admin" || role === "super_admin";
  }

  function meId() {
    return root.state && root.state.me ? root.state.me.id : null;
  }

  function cells(lead) {
    const tag = lead.contact_type ? `<div class="muted">${esc(lead.contact_type)}</div>` : "";
    const pending = Number(lead.pending_owner_id) === Number(meId())
      ? `<div class="muted">Pending for you</div><button type="button" class="btn small lead-accept" data-lead="${lead.id}">Accept</button> <button type="button" class="btn secondary small lead-decline" data-lead="${lead.id}">Decline</button>`
      : (lead.pending_owner_name ? `<div class="muted">Waiting on ${esc(lead.pending_owner_name)}</div>` : "");
    const review = lead.in_review ? `<div class="muted">Awaiting review${lead.review_outcome ? ": " + esc(lead.review_outcome) : ""}</div>` : "";
    return `<td><input type="checkbox" class="lead-pick" data-lead="${lead.id}"></td><td>${esc(lead.company)}${tag}</td><td>${esc(lead.contact_name || "—")}<div class="muted">${esc(lead.email || "")}</div></td><td>${esc(lead.source)}</td><td>${esc(lead.region || "—")}</td><td>${lead.score ?? "—"}</td><td>${ownerSelect(lead)}${pending}</td><td>${statusSelect(lead)}${review}${lead.contacted_badge ? `<div class="muted">${esc(lead.contacted_badge)}</div>` : ""}</td>`;
  }

  function selectedIds() {
    return Array.from(document.querySelectorAll(".lead-pick:checked")).map((box) => Number(box.dataset.lead));
  }

  function refreshBulk() {
    const bar = document.getElementById("lead-bulk");
    if (bar) bar.hidden = selectedIds().length === 0;
  }

  function bind() {
    const rows = document.getElementById("lead-rows");
    if (!rows || rows.dataset.manageBound) return;
    rows.dataset.manageBound = "1";
    rows.addEventListener("click", async (event) => {
      const button = event.target.closest("button");
      if (event.target.closest("select, input, button")) event.stopPropagation();
      if (!button) return;
      const id = button.dataset.lead;
      if (!id) return;
      try {
        if (button.classList.contains("lead-accept")) {
          await root.api("/api/leads/" + id + "/accept", {method: "POST", body: {}});
          root.toast("Lead accepted");
        } else if (button.classList.contains("lead-decline")) {
          const reason = window.prompt("Why are you declining?");
          if (!reason || reason.trim().length < 3) { root.toast("A short reason is required"); return; }
          await root.api("/api/leads/" + id + "/decline", {method: "POST", body: {reason}});
          root.toast("Returned to the previous owner");
        } else return;
        if (root.loadLeads) root.loadLeads();
      } catch (error) { root.toast(error.message); }
    });
    rows.addEventListener("change", async (event) => {
      const target = event.target;
      const id = target.dataset.lead;
      if (!id) return;
      try {
        if (target.classList.contains("lead-pick")) {
          refreshBulk();
          return;
        }
        if (target.classList.contains("lead-owner")) {
          if (!target.value) return;
          const result = await root.api("/api/leads/" + id + "/assign", {method: "POST", body: {user_id: Number(target.value)}});
          root.toast(result.pending_owner_id ? "Waiting for them to accept" : "Owner updated");
        }
        if (target.classList.contains("lead-status")) {
          const status = target.value;
          if (status === "In review") {
            root.toast("Use Submit for review");
            if (root.loadLeads) root.loadLeads();
            return;
          }
          if (CLOSED.includes(status)) {
            const reason = window.prompt("Short reason for closing as " + status);
            if (!reason || reason.trim().length < 3) {
              root.toast("A short reason is required");
              if (root.loadLeads) root.loadLeads();
              return;
            }
            const outcome = status === "Won" ? "won" : status === "Lost" ? "lost" : "not_a_fit";
            const path = isAdmin() ? "/close" : "/request-close";
            await root.api("/api/leads/" + id + path, {method: "POST", body: {outcome, reason}});
          } else if (status === "Qualified") {
            await root.api("/api/leads/" + id + "/review", {method: "POST", body: {decision: "qualify"}});
          } else {
            await root.api("/api/leads/" + id, {method: "PATCH", body: {status}});
          }
          root.toast("Status updated");
        }
        if (root.loadLeads) root.loadLeads();
      } catch (error) {
        root.toast(error.message);
        if (root.loadLeads) root.loadLeads();
      }
    });
    const assign = document.getElementById("lead-bulk-assign");
    if (assign) assign.addEventListener("click", async () => {
      const owner = document.getElementById("lead-bulk-owner").value;
      if (!owner) { root.toast("Choose a person"); return; }
      try {
        await root.api("/api/leads/bulk-assign", {method: "POST", body: {ids: selectedIds(), owner_id: Number(owner)}});
        root.toast("Assigned");
        root.loadLeads();
      } catch (error) { root.toast(error.message); }
    });
    const move = document.getElementById("lead-bulk-move");
    if (move) move.addEventListener("click", async () => {
      const status = document.getElementById("lead-bulk-status").value;
      if (!status) { root.toast("Choose a status"); return; }
      let reason = "";
      if (CLOSED.includes(status)) {
        reason = window.prompt("Short reason for closing as " + status) || "";
        if (reason.trim().length < 3) { root.toast("A short reason is required"); return; }
      }
      try {
        await root.api("/api/leads/bulk-status", {method: "POST", body: {ids: selectedIds(), status, reason}});
        root.toast("Status updated");
        root.loadLeads();
      } catch (error) { root.toast(error.message); }
    });
  }

  function detailActions(lead, manage) {
    const statusOptions = STATUSES.map((status) => `<option ${lead.status === status ? "selected" : ""}>${esc(status)}</option>`).join("");
    const owners = [`<option value="">Unassigned</option>`].concat(people.map((person) => `<option value="${person.id}" ${Number(lead.owner_id) === person.id ? "selected" : ""}>${esc(person.name)}</option>`)).join("");
    const admin = isAdmin();
    const mine = Number(lead.pending_owner_id) === Number(meId());
    const closeButtons = admin
      ? `<button class="btn small" type="button" id="detail-won">Close as Won</button>
      <button class="btn secondary small" type="button" id="detail-lost">Close as Lost</button>
      <button class="btn secondary small" type="button" id="detail-fit">Not a fit</button>
      ${lead.closed ? `<button class="btn secondary small" type="button" id="detail-reopen">Reopen</button>` : ""}
      ${lead.in_review ? `<button class="btn small" type="button" id="detail-approve">Approve close</button><button class="btn secondary small" type="button" id="detail-reject">Reject</button>` : ""}`
      : `<button class="btn small" type="button" id="detail-request">Submit for review</button>`;
    return `<div class="row">
      <div class="field" style="margin:0"><label>Owner</label><select id="detail-owner">${owners}</select></div>
      <div class="field" style="margin:0"><label>Status</label><select id="detail-status">${statusOptions}</select></div>
      ${manage ? `<button class="btn small" type="button" id="detail-move">Save status</button>` : ""}
      <button class="btn secondary small" type="button" id="detail-assign">Save owner</button>
    </div>
    ${lead.in_review ? `<p class="muted">Proposed ${esc(lead.review_outcome)}: ${esc(lead.review_reason)}</p>` : ""}
    ${mine ? `<div class="row"><button class="btn small" type="button" id="detail-accept">Accept</button><button class="btn secondary small" type="button" id="detail-decline">Decline</button></div>` : ""}
    <div class="row">
      <div class="field" style="margin:0;min-width:220px"><label>${admin ? "Close reason" : "Reason for review"}</label><input id="detail-reason" value="${esc(lead.review_reason || lead.close_reason || "")}" placeholder="Required"></div>
      ${closeButtons}
    </div>
    <div class="list" id="detail-activity" style="margin-top:12px"></div>`;
  }

  function mountDetail(lead) {
    const id = lead.id;
    const assign = document.getElementById("detail-assign");
    if (assign) assign.onclick = async () => {
      const owner = document.getElementById("detail-owner").value;
      if (!owner) { root.toast("Choose a person"); return; }
      try {
        await root.api("/api/leads/" + id + "/assign", {method: "POST", body: {user_id: Number(owner)}});
        root.toast("Owner updated");
        root.loadLeads();
      } catch (error) { root.toast(error.message); }
    };
    async function close(outcome) {
      const reason = document.getElementById("detail-reason").value;
      try {
        await root.api("/api/leads/" + id + "/close", {method: "POST", body: {outcome, reason}});
        root.toast("Lead closed");
        root.loadLeads();
      } catch (error) { root.toast(error.message); }
    }
    const won = document.getElementById("detail-won");
    if (won) won.onclick = () => close("won");
    const lost = document.getElementById("detail-lost");
    if (lost) lost.onclick = () => close("lost");
    const fit = document.getElementById("detail-fit");
    if (fit) fit.onclick = () => close("not_a_fit");
    const request = document.getElementById("detail-request");
    if (request) request.onclick = async () => {
      const status = document.getElementById("detail-status").value;
      const outcome = status === "Won" ? "won" : status === "Lost" ? "lost" : "not_a_fit";
      const reason = document.getElementById("detail-reason").value;
      try {
        await root.api("/api/leads/" + id + "/request-close", {method: "POST", body: {outcome, reason}});
        root.toast("Sent for review");
        root.loadLeads();
      } catch (error) { root.toast(error.message); }
    };
    const approve = document.getElementById("detail-approve");
    if (approve) approve.onclick = async () => {
      try {
        await root.api("/api/leads/" + id + "/review-close", {method: "POST", body: {decision: "approve"}});
        root.toast("Close approved");
        root.loadLeads();
      } catch (error) { root.toast(error.message); }
    };
    const reject = document.getElementById("detail-reject");
    if (reject) reject.onclick = async () => {
      const comment = document.getElementById("detail-reason").value;
      try {
        await root.api("/api/leads/" + id + "/review-close", {method: "POST", body: {decision: "reject", comment}});
        root.toast("Sent back");
        root.loadLeads();
      } catch (error) { root.toast(error.message); }
    };
    const accept = document.getElementById("detail-accept");
    if (accept) accept.onclick = async () => {
      try {
        await root.api("/api/leads/" + id + "/accept", {method: "POST", body: {}});
        root.toast("Lead accepted");
        root.loadLeads();
      } catch (error) { root.toast(error.message); }
    };
    const decline = document.getElementById("detail-decline");
    if (decline) decline.onclick = async () => {
      const reason = document.getElementById("detail-reason").value;
      try {
        await root.api("/api/leads/" + id + "/decline", {method: "POST", body: {reason}});
        root.toast("Returned to the previous owner");
        root.loadLeads();
      } catch (error) { root.toast(error.message); }
    };
    const reopen = document.getElementById("detail-reopen");
    if (reopen) reopen.onclick = async () => {
      try {
        await root.api("/api/leads/" + id + "/reopen", {method: "POST", body: {}});
        root.toast("Lead reopened");
        root.loadLeads();
      } catch (error) { root.toast(error.message); }
    };
    root.api("/api/leads/" + id + "/activity").then((data) => {
      const host = document.getElementById("detail-activity");
      if (!host) return;
      const events = data.events || [];
      host.innerHTML = events.map((row) => `<div class="item"><b>${esc(row.at || "")}</b><div>${esc(row.summary || "")}</div></div>`).join("") || `<div class="muted">No activity yet.</div>`;
    }).catch(() => {});
  }

  async function refreshCounts() {
    try {
      const data = await root.api("/api/leads/queues");
      const review = document.getElementById("review-badge");
      const pending = document.getElementById("pending-transfer-badge");
      if (review) {
        review.hidden = !data.awaiting_review;
        review.textContent = data.awaiting_review;
      }
      if (pending) {
        pending.hidden = !data.pending_for_me;
        pending.textContent = data.pending_for_me;
      }
      const reviewLabel = document.getElementById("lead-review-label");
      if (reviewLabel) reviewLabel.hidden = !isAdmin();
    } catch (error) { /* counts are optional */ }
  }

  root.LeadManage = { STATUSES, CLOSED, ensurePeople, cells, bind, detailActions, mountDetail, refreshCounts };
})(window);
