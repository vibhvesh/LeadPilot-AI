/* Open Industry Pulse cards marked urgent. */
(function (root) {
  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.pulse = function (summary) {
    const widgets = root.CockpitWidgets;
    if (!summary.pulse) {
      return widgets.frame("pulse", "Industry Pulse", "<h2>Industry Pulse</h2><p class=\"instrument-note\">Industry Pulse is not on your instruments</p>");
    }
    const urgent = Number(summary.pulse.urgent) || 0;
    const items = summary.pulse.urgent_items || [];
    const rows = items.map(function (item) {
      return '<li><a href="/pulse">' + widgets.esc(item.headline || "Urgent story") + "</a></li>";
    }).join("");
    const inner = '<h2>Urgent Pulse</h2><a class="mini-hit" href="/pulse">' +
      widgets.readout("Urgent", String(urgent), "", urgent ? "alert" : "ok") + "</a>" +
      (rows ? '<ul class="reply-tile">' + rows + "</ul>" : "");
    return widgets.frame("pulse", "Urgent Pulse", inner);
  };
})(window);
