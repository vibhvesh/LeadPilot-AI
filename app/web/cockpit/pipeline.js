/* One column per pipeline stage. Each column opens that status filter. */
(function (root) {
  const STATUSES = ["New", "Contacted", "Qualified", "Won", "Lost"];

  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.pipeline = function (summary) {
    const widgets = root.CockpitWidgets;
    const by = (summary.leads && summary.leads.by_status) || {};
    const max = Math.max.apply(null, STATUSES.map(function (status) { return Number(by[status]) || 0; }).concat([1]));
    const columns = STATUSES.map(function (status) {
      const count = Number(by[status]) || 0;
      const height = Math.round((count / max) * 100);
      return '<button type="button" class="pipe" data-go="leads" data-module="leads" data-status="' + widgets.esc(status) + '" aria-label="' + widgets.esc(status) + " leads, " + count + '">' +
        '<span class="pipe-track"><i style="height:' + height + '%"></i></span><b>' + count + "</b><span>" + widgets.esc(status) + "</span></button>";
    }).join("");
    const inner = widgets.titleButton("Pipeline", {"data-go": "pipeline", "data-module": "pipeline"}) + '<div class="pipes">' + columns + "</div>";
    return widgets.frame("pipeline", "Pipeline", inner, true);
  };
})(window);
