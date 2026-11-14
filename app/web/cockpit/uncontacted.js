/* Highest-scored leads still in New. A row opens the existing summary preview. */
(function (root) {
  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.uncontacted = function (summary) {
    const widgets = root.CockpitWidgets;
    const rows = (summary.leads && summary.leads.top_uncontacted) || [];
    const body = rows.length ? rows.map(function (lead) {
      const score = lead.score == null ? "—" : String(lead.score);
      return '<tr class="clicky" data-preview-lead="' + widgets.esc(lead.id) + '" data-score="' + widgets.esc(lead.score == null ? "" : lead.score) + '" data-status="' + widgets.esc(lead.status || "New") + '" data-company="' + widgets.esc(lead.company || "") + '"><td>' + widgets.esc(lead.company) + "</td><td>" + widgets.esc(score) + "</td><td>" + widgets.esc(lead.status || "New") + "</td></tr>";
    }).join("") : '<tr><td colspan="3">No uncontacted leads.</td></tr>';
    const inner = widgets.titleButton("Top uncontacted", {"data-go": "leads", "data-module": "leads", "data-status": "New"}) +
      '<div class="tablewrap"><table><thead><tr><th>Company</th><th>Score</th><th>Status</th></tr></thead><tbody id="recent-leads">' + body + "</tbody></table></div>";
    return widgets.frame("uncontacted", "Top uncontacted leads", inner, true);
  };
})(window);
