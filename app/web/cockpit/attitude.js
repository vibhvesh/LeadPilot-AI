/* Artificial horizon for the lead-volume trend against the prior seven UTC days. */
(function (root) {
  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.attitude = function (summary) {
    const widgets = root.CockpitWidgets;
    const trend = (summary.leads && summary.leads.trend) || {};
    const inner = widgets.attitude(trend);
    return widgets.frame("attitude", "Lead trend", widgets.hit({
      "data-go": "reports",
      "data-module": "reports",
      "aria-label": "Lead trend " + (Number(trend.delta) || 0) + " versus the prior seven days. Open reports",
    }, inner), true);
  };
})(window);
