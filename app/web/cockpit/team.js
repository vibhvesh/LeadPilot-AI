/* Approved people, and the activity tape when this account may see it. */
(function (root) {
  function when(iso) {
    if (!iso) return "No sign-in yet";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "No sign-in yet";
    return date.toLocaleString();
  }

  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.team = function (summary) {
    const widgets = root.CockpitWidgets;
    if (!summary.team && !summary.activity) {
      return widgets.frame("team", "Team", "<h2>Team</h2><p class=\"instrument-note\">Team activity is not on your instruments</p>");
    }
    let body = "<h2>Team</h2>";
    if (summary.team) {
      const roster = summary.team.roster || [];
      body += widgets.titleButton("Crew · " + (Number(summary.team.approved) || 0), {"data-go": "team", "data-module": "team"});
      body += '<ul class="tape">' + (roster.length ? roster.map(function (person) {
        const name = person.name || person.email || "Teammate";
        return "<li><span>" + widgets.esc(name) + "</span><span>" + widgets.esc(when(person.last_login_at)) + "</span></li>";
      }).join("") : "<li><span>No approved people yet</span></li>") + "</ul>";
    }
    if (summary.activity) {
      const recent = summary.activity.recent || [];
      body += widgets.titleButton("Activity today · " + (Number(summary.activity.activities_today) || 0), {"data-go": "activity", "data-module": "activity"});
      body += '<ul class="tape">' + (recent.length ? recent.map(function (event) {
        const label = [event.action, event.module].filter(Boolean).join(" · ");
        return '<li><span class="' + (event.success ? "" : "fail") + '">' + widgets.esc(event.email || "System") + " · " + widgets.esc(label) + "</span></li>";
      }).join("") : "<li><span>No events yet</span></li>") + "</ul>";
    }
    return widgets.frame("team", "Team activity", body, true);
  };
})(window);
