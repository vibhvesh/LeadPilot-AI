/* Status rows that replace the old warning lights. */
(function (root) {
  function can(module) {
    return !!(root.LeadPilot && root.LeadPilot.can(module));
  }

  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.alerts = function (summary) {
    const widgets = root.CockpitWidgets;
    const health = summary.health || {};
    const rows = [];
    if (summary.followups) {
      const open = Number(summary.followups.open) || 0;
      const overdue = Number(summary.followups.overdue) || 0;
      rows.push('<p id="m-follow">' + open + " open follow-ups</p>");
      rows.push(widgets.alertRow({
        id: "lamp-overdue",
        level: overdue ? "alert" : "ok",
        name: "Overdue",
        detail: overdue + " follow-ups",
        count: overdue,
        label: "Overdue follow-ups",
        go: can("followups") ? "followups" : "",
        module: can("followups") ? "followups" : "",
      }));
    }
    if (summary.pulse) {
      const urgent = Number(summary.pulse.urgent) || 0;
      rows.push(widgets.alertRow({
        id: "lamp-pulse",
        level: urgent ? "alert" : "ok",
        name: "Pulse",
        detail: urgent + " urgent",
        count: urgent,
        label: "Urgent Industry Pulse cards",
        go: can("pulse") ? "pulse" : "",
        module: can("pulse") ? "pulse" : "",
        urgency: "urgent",
      }));
    }
    rows.push(widgets.alertRow({
      id: "lamp-llm",
      level: health.llm_present ? "ok" : "warn",
      name: "LLM",
      detail: health.llm_present ? (health.llm_provider || "ready") : "No key",
      label: health.llm_present ? "LLM " + (health.llm_provider || "ready") : "No LLM key",
      go: can("ai") ? "ai" : (can("apikeys") ? "apis" : ""),
      module: can("ai") ? "ai" : (can("apikeys") ? "apikeys" : ""),
    }));
    rows.push(widgets.alertRow({
      id: "lamp-search",
      level: health.search_present ? "ok" : "warn",
      name: "Search",
      detail: health.search_present ? (health.search_provider || "ready") : "No key",
      label: health.search_present ? "Search " + (health.search_provider || "ready") : "No search key",
      go: can("apikeys") ? "apis" : (can("search") ? "search" : ""),
      module: can("apikeys") ? "apikeys" : (can("search") ? "search" : ""),
    }));
    return widgets.card("Status", rows.join(""));
  };
})(window);
