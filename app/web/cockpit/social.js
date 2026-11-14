/* Open Social items in Reply to and Engage. */
(function (root) {
  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.social = function (summary) {
    const widgets = root.CockpitWidgets;
    if (!summary.social) {
      return widgets.frame("social", "Social", "<h2>Social</h2><p class=\"instrument-note\">Social is not on your instruments</p>");
    }
    const reply = Number(summary.social.reply) || 0;
    const engage = Number(summary.social.engage) || 0;
    const newest = summary.social.newest_replies || [];
    const talks = summary.social.newest_discussions || [];
    function lines(items, empty) {
      if (!items.length) return "";
      return '<ul class="reply-tile">' + items.map(function (item) {
        const who = item.poster_name ? item.poster_name + " · " : "";
        return '<li><a href="/social">' + widgets.esc(who + (item.snippet || empty)) + "</a></li>";
      }).join("") + "</ul>";
    }
    const inner = '<h2>Reply to</h2><a class="mini-hit" href="/social">' +
      widgets.readout("Waiting", String(reply), "", reply ? "warn" : "ok") + "</a>" +
      lines(newest, "Reply waiting") +
      (talks.length ? "<h2>Discussions</h2>" + lines(talks, "Discussion") : "") +
      (engage ? '<a class="mini-hit" href="/social">' + widgets.readout("Engage", String(engage), "", "warn") + "</a>" : "");
    return widgets.frame("social", "Social", inner);
  };
})(window);
