/* Won divided by every lead. The needle is that ratio, not a target. */
(function (root) {
  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.conversion = function (summary) {
    const widgets = root.CockpitWidgets;
    const leads = summary.leads || {};
    const rate = Number(leads.conversion_rate) || 0;
    const won = Number(leads.by_status && leads.by_status.Won) || 0;
    const inner = widgets.gauge({
      angle: widgets.angleFor(rate, 1),
      center: widgets.percent(rate),
      centerId: "m-rate",
      caption: "Won / all leads",
      tone: "ok",
    }) + '<div class="readouts">' + widgets.readout("Won", String(won)) + "</div>";
    return widgets.frame("conversion", "Conversion rate", widgets.hit({
      "data-go": "reports",
      "data-module": "reports",
      "aria-label": "Conversion rate " + widgets.percent(rate) + ". Open reports",
    }, inner));
  };
})(window);
