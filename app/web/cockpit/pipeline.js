/* Pipeline as a stacked list. Each row opens that status. */
(function (root) {
  const STATUSES = ["New", "Contacted", "Qualified", "Won", "Lost"];
  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.pipeline = function (summary) {
    const widgets = root.CockpitWidgets;
    const by = (summary.leads && summary.leads.by_status) || {};
    const max = Math.max.apply(null, STATUSES.map(function (status) { return Number(by[status]) || 0; }).concat([1]));
    const rows = STATUSES.map(function (status) {
      const count = Number(by[status]) || 0;
      const width = Math.round((count / max) * 100);
      return '<button type="button" class="home-stage" data-go="leads" data-module="leads" data-status="' + widgets.esc(status) + '"><span>' + widgets.esc(status) + "</span><b>" + count + '</b><span class="bar"><i style="width:' + width + '%"></i></span></button>';
    }).join("");
    return widgets.card("Pipeline", rows);
  };
})(window);
