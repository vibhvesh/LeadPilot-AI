/* Total leads, today's intake, this week, qualified, and pipeline value. */
(function (root) {
  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.leads = function (summary) {
    const widgets = root.CockpitWidgets;
    const leads = summary.leads || {};
    const total = Number(leads.total) || 0;
    const by = leads.by_status || {};
    const active = (Number(by.New) || 0) + (Number(by.Contacted) || 0) + (Number(by.Qualified) || 0);
    const inner = widgets.gauge({
      angle: widgets.angleFor(active, total),
      center: String(total),
      centerId: "m-total",
      caption: "Total · arc is active",
      tone: "ok",
    }) + '<div class="readouts">' +
      widgets.readout("Today", String(Number(leads.new_today) || 0)) +
      widgets.readout("7 days", String(Number(leads.new_this_week) || 0)) +
      widgets.readout("Qualified", String(Number(by.Qualified) || 0), "m-qualified") +
      widgets.readout("Value", widgets.money(leads.pipeline_value), "m-value") +
      "</div>";
    return widgets.frame("leads", "Total leads", widgets.hit({
      "data-go": "leads",
      "data-module": "leads",
      "aria-label": "Total leads " + total + ". Open the lead list",
    }, inner), true);
  };
})(window);
