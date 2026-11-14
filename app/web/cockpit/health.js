/* Service, database, and which provider keys are actually configured. */
(function (root) {
  const LLM = {xai: "xAI", gemini: "Gemini", openai: "OpenAI"};
  const SEARCH = {tavily: "Tavily", brave: "Brave"};

  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.health = function (summary) {
    const widgets = root.CockpitWidgets;
    const health = summary.health || {};
    const llmOk = !!health.llm_present;
    const searchOk = !!health.search_present;
    const keys = health.keys;
    const lights = [
      widgets.lamp({
        id: "lamp-health-api",
        level: health.api === "ok" ? "ok" : "alert",
        name: "API",
        label: health.api === "ok" ? "API healthy" : "API not responding",
        go: root.LeadPilot && root.LeadPilot.can("settings") ? "settings" : "",
        module: root.LeadPilot && root.LeadPilot.can("settings") ? "settings" : "",
      }),
      widgets.lamp({
        id: "lamp-health-db",
        level: health.database === "ok" ? "ok" : "alert",
        name: "DB",
        label: health.database === "ok" ? "Database connected" : "Database check failed",
        go: root.LeadPilot && root.LeadPilot.can("settings") ? "settings" : "",
        module: root.LeadPilot && root.LeadPilot.can("settings") ? "settings" : "",
      }),
    ];
    if (Array.isArray(keys)) {
      keys.forEach(function (row) {
        const name = row.provider;
        const configured = !!row.configured;
        const categoryDown = (LLM[name] && !llmOk) || (SEARCH[name] && !searchOk);
        const level = configured ? "ok" : categoryDown ? "warn" : "standby";
        const label = (LLM[name] || SEARCH[name] || name) + (configured ? " key ready" : " key missing");
        const dest = root.LeadPilot && root.LeadPilot.can("apikeys") ? {go: "apis", module: "apikeys"} : {go: "", module: ""};
        lights.push(widgets.lamp({
          id: "lamp-key-" + name,
          level: level,
          name: LLM[name] || SEARCH[name] || name,
          label: label,
          go: dest.go,
          module: dest.module,
        }));
      });
    }
    const note = Array.isArray(keys) ? "" : '<p class="instrument-note">Individual keys are hidden for this role. The LLM and search lights above still show whether one is configured.</p>';
    return widgets.frame("health", "System health", "<h2>System</h2><div class=\"lamp-row\">" + lights.join("") + "</div>" + note);
  };
})(window);
