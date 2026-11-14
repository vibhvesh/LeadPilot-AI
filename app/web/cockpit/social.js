/* Reply to, and the newest discussions, as two separate cards. */
(function (root) {
  root.CockpitPanels = root.CockpitPanels || {};

  function lines(widgets, items, empty) {
    if (!items.length) return '<p class="muted">' + widgets.esc(empty) + "</p>";
    return '<ul class="home-list">' + items.map(function (item) {
      const who = item.poster_name ? item.poster_name + " · " : "";
      return '<li><a href="/social">' + widgets.esc(who + (item.snippet || "Open item")) + "</a></li>";
    }).join("") + "</ul>";
  }

  root.CockpitPanels.social = function (summary) {
    const widgets = root.CockpitWidgets;
    if (!summary.social) return widgets.card("Reply to", '<p class="muted">Social is not on this account.</p>');
    const reply = Number(summary.social.reply) || 0;
    return widgets.card("Reply to", '<a class="home-count" href="/social"><b>' + reply + "</b><span>waiting</span></a>" + lines(widgets, summary.social.newest_replies || [], "Nothing waiting."));
  };

  root.CockpitPanels.discussions = function (summary) {
    const widgets = root.CockpitWidgets;
    if (!summary.social) return widgets.card("Recent discussions", '<p class="muted">Social is not on this account.</p>');
    const engage = Number(summary.social.engage) || 0;
    return widgets.card("Recent discussions", '<a class="home-count" href="/social"><b>' + engage + "</b><span>to engage</span></a>" + lines(widgets, summary.social.newest_discussions || [], "No open discussions."));
  };
})(window);
