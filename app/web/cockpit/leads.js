/* KPI cards: counts, a week-over-week delta, and a link into the matching page. */
(function (root) {
  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.kpis = function (summary) {
    const widgets = root.CockpitWidgets;
    const leads = summary.leads || {};
    const by = leads.by_status || {};
    const delta = Number(leads.trend && leads.trend.delta) || 0;
    const change = (delta > 0 ? "+" : "") + delta + " vs prior week";
    return [
      widgets.stat({label: "Total leads", value: Number(leads.total) || 0, id: "m-total", delta: change, go: "leads", module: "leads"}),
      widgets.stat({label: "New today", value: Number(leads.new_today) || 0, go: "leads", module: "leads"}),
      widgets.stat({label: "This week", value: Number(leads.new_this_week) || 0, delta: change, go: "leads", module: "leads"}),
      widgets.stat({label: "Qualified", value: Number(by.Qualified) || 0, id: "m-qualified", go: "leads", module: "leads", status: "Qualified"}),
      widgets.stat({label: "Conversion", value: widgets.percent(leads.conversion_rate), go: "reports", module: "reports"}),
      widgets.stat({label: "Pipeline value", value: widgets.money(leads.pipeline_value), id: "m-value", go: "pipeline", module: "pipeline"}),
    ].join("");
  };
})(window);
