/* Urgent Industry Pulse headlines. */
(function (root) {
  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.pulse = function (summary) {
    const widgets = root.CockpitWidgets;
    if (!summary.pulse) return widgets.card("Urgent Pulse", '<p class="muted">Industry Pulse is not on this account.</p>');
    const urgent = Number(summary.pulse.urgent) || 0;
    const items = summary.pulse.urgent_items || [];
    const rows = items.length ? '<ul class="home-list">' + items.map(function (item) {
      return '<li><a href="/pulse">' + widgets.esc(item.headline || "Urgent story") + "</a></li>";
    }).join("") + "</ul>" : '<p class="muted">No urgent stories.</p>';
    return widgets.card("Urgent Pulse", '<a class="home-count" href="/pulse"><b>' + urgent + "</b><span>urgent</span></a>" + rows);
  };
})(window);
