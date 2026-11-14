/* A short row of the lights that change what you do next. */
(function (root) {
  function can(module) {
    return !!(root.LeadPilot && root.LeadPilot.can(module));
  }

  function target(go, module) {
    if (can(module)) return {go: go, module: module};
    return {};
  }

  root.CockpitAnnunciator = function (summary) {
    const lamp = root.CockpitWidgets.lamp;
    const health = summary.health || {};
    const lights = [];
    if (summary.followups) {
      const overdue = Number(summary.followups.overdue) || 0;
      lights.push(lamp(Object.assign({
        id: "lamp-overdue",
        level: overdue ? "alert" : "ok",
        name: "OVERDUE",
        label: "Overdue follow-ups",
        count: overdue,
      }, target("followups", "followups"))));
    }
    if (summary.pulse) {
      const urgent = Number(summary.pulse.urgent) || 0;
      lights.push(lamp(Object.assign({
        id: "lamp-pulse",
        level: urgent ? "alert" : "ok",
        name: "PULSE",
        label: "Urgent Industry Pulse cards",
        count: urgent,
        urgency: "urgent",
      }, target("pulse", "pulse"))));
    }
    lights.push(lamp(Object.assign({
      id: "lamp-llm",
      level: health.llm_present ? "ok" : "warn",
      name: "LLM",
      label: health.llm_present ? "LLM " + (health.llm_provider || "ready") : "No LLM key",
    }, can("ai") ? {go: "ai", module: "ai"} : (can("apikeys") ? {go: "apis", module: "apikeys"} : {}))));
    lights.push(lamp(Object.assign({
      id: "lamp-search",
      level: health.search_present ? "ok" : "warn",
      name: "SEARCH",
      label: health.search_present ? "Search " + (health.search_provider || "ready") : "No search key",
    }, can("apikeys") ? {go: "apis", module: "apikeys"} : (can("search") ? {go: "search", module: "search"} : {}))));
    return lights.join("");
  };
})(window);
