/* Pipeline column links. Each card opens the lead detail; each header filters the list. */
(function () {
  const STATUSES = ["New", "Contacted", "Qualified", "Won", "Lost"];

  function hrefForLead(id) {
    return "/leads?id=" + encodeURIComponent(id);
  }

  function hrefForStatus(status) {
    return "/leads?status=" + encodeURIComponent(status);
  }

  function render(data) {
    const esc = window.LeadPilot.esc;
    const counts = data.counts || {};
    const columns = data.columns || {};
    const max = Math.max(1, ...STATUSES.map((status) => counts[status] || 0));
    return STATUSES.map((status) => {
      const cards = (columns[status] || []).map((lead) => `<a class="mini mini-link" href="${hrefForLead(lead.id)}"><b>${esc(lead.company)}</b><div class="muted">${esc(lead.region || lead.contact_name || "")}</div></a>`).join("");
      return `<div class="col">
        <a class="col-link" href="${hrefForStatus(status)}"><h3>${esc(status)} <span>${counts[status] || 0}</span></h3></a>
        <div class="bar"><i style="width:${Math.round(((counts[status] || 0) / max) * 100)}%"></i></div>
        ${cards || `<div class="muted">None</div>`}
      </div>`;
    }).join("");
  }

  window.PipelineBoard = {render, hrefForLead, hrefForStatus, STATUSES};
})();
