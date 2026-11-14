/* Highest-scored leads still in New. A row opens the existing summary preview. */
(function (root) {
  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.uncontacted = function (summary) {
    const widgets = root.CockpitWidgets;
    const rows = (summary.leads && summary.leads.top_uncontacted) || [];
    const body = rows.length ? rows.map(function (lead) {
      const score = lead.score == null ? "—" : String(lead.score);
      return '<tr class="clicky" data-preview-lead="' + widgets.esc(lead.id) + '" data-score="' + widgets.esc(lead.score == null ? "" : lead.score) + '" data-status="' + widgets.esc(lead.status || "New") + '" data-company="' + widgets.esc(lead.company || "") + '"><td>' + widgets.esc(lead.company || "Lead") + "</td><td>" + widgets.esc(score) + "</td></tr>";
    }).join("") : '<tr><td colspan="2">No uncontacted leads.</td></tr>';
    return widgets.card("Recent leads", '<div class="tablewrap"><table class="home-table"><thead><tr><th>Company</th><th>Score</th></tr></thead><tbody id="recent-leads">' + body + "</tbody></table></div>");
  };
})(window);
