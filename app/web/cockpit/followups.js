/* Open reminders, and how many of those are already past due. */
(function (root) {
  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.followups = function (summary) {
    const widgets = root.CockpitWidgets;
    if (!summary.followups) {
      return widgets.frame("followups", "Follow-ups", '<h2>Follow-ups</h2><p class="instrument-note" id="m-follow">Follow-ups are not on your instruments</p>');
    }
    const open = Number(summary.followups.open) || 0;
    const overdue = Number(summary.followups.overdue) || 0;
    const tone = overdue ? "alert" : "ok";
    const inner = '<h2>Follow-ups</h2>' + widgets.readout("Overdue", String(overdue), "", tone) +
      '<p class="instrument-note" id="m-follow">' + open + " follow-ups open</p>";
    return widgets.frame("followups", "Follow-ups", widgets.hit({
      "data-go": "followups",
      "data-module": "followups",
      "aria-label": overdue + " overdue, " + open + " follow-ups open. Open follow-ups",
    }, inner));
  };
})(window);
