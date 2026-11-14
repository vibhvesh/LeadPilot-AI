/* Loads the summary, paints the homepage cards, and refreshes about once a minute. */
(function (root) {
  const PANELS = ["pipeline", "social", "discussions", "pulse", "alerts", "uncontacted"];
  let timer = 0;
  let started = false;
  let last = null;
  let refreshing = false;

  function reduced() {
    return root.CockpitWidgets.reduced();
  }

  function host() {
    return document.getElementById("cockpit");
  }

  function arm(seconds) {
    root.clearInterval(timer);
    const every = Math.min(180, Math.max(30, Number(seconds) || 60));
    timer = root.setInterval(function () {
      if (document.hidden) return;
      const page = document.getElementById("overview");
      if (!page || !page.classList.contains("active")) return;
      refresh({quiet: true});
    }, every * 1000);
  }

  function paint(summary) {
    const node = host();
    if (!node || !root.CockpitWidgets) return;
    const widgets = root.CockpitWidgets;
    const updated = summary.generated_at ? new Date(summary.generated_at).toLocaleTimeString() : "";
    const panels = PANELS.map(function (name) {
      const draw = root.CockpitPanels && root.CockpitPanels[name];
      if (!draw) return "";
      try {
        return draw(summary);
      } catch (error) {
        return widgets.card(name, "<p class=\"muted\">This card could not be drawn.</p>");
      }
    }).join("");
    const kpis = root.CockpitPanels && root.CockpitPanels.kpis ? root.CockpitPanels.kpis(summary) : "";
    node.innerHTML = '<p class="muted" id="cockpit-updated">Updated ' + widgets.esc(updated) + " · refreshes every " + widgets.esc(summary.refresh_seconds || 60) + "s</p>" +
      '<div class="home-kpis">' + kpis + "</div>" +
      '<div class="home-grid">' + panels + "</div>" +
      '<p class="error" id="cockpit-fault" hidden></p>';
    const banner = document.getElementById("start-banner");
    if (banner) banner.hidden = !!(summary.leads && Number(summary.leads.total) > 0);
    arm(summary.refresh_seconds);
  }

  function paintError(message) {
    const node = host();
    if (!node || !root.CockpitWidgets) return;
    node.innerHTML = '<p class="cockpit-fault" id="cockpit-fault">' + root.CockpitWidgets.esc(message || "Instruments unavailable") + "</p>";
  }

  async function refresh(options) {
    const opts = options || {};
    if (refreshing || !root.LeadPilot) return;
    refreshing = true;
    try {
      const data = await root.LeadPilot.api("/api/dashboard/summary");
      last = data;
      paint(data);
    } catch (error) {
      const fault = document.getElementById("cockpit-fault");
      if (last && fault) {
        fault.hidden = false;
        fault.textContent = error.message;
      } else if (!last) {
        paintError(error.message);
      }
      if (!opts.quiet) root.LeadPilot.toast(error.message);
    } finally {
      refreshing = false;
    }
  }

  function allowed(hit) {
    const modules = (hit.getAttribute("data-module") || "").split(",").map(function (item) { return item.trim(); }).filter(Boolean);
    if (!modules.length) return true;
    return modules.some(function (name) { return root.LeadPilot.can(name); });
  }

  function goFrom(hit) {
    if (!hit || !root.LeadPilot) return;
    if (!allowed(hit)) {
      root.LeadPilot.toast("That page is not on your account");
      return;
    }
    let tab = hit.getAttribute("data-go");
    if (!tab) return;
    if (tab === "search" && !root.LeadPilot.can("search") && root.LeadPilot.can("grokbot")) tab = "grokbot";
    if (tab === "apis" && !root.LeadPilot.can("apikeys") && root.LeadPilot.can("ai")) tab = "ai";
    if (tab === "activity" && !root.LeadPilot.can("activity") && root.LeadPilot.can("team")) tab = "team";
    if (tab === "leads") {
      const select = document.getElementById("lead-status");
      if (select) select.value = hit.getAttribute("data-status") || "";
    }
    if (tab === "pulse") {
      const select = document.getElementById("pulse-filter-urgency");
      const urgency = hit.getAttribute("data-urgency");
      if (select && urgency) select.value = urgency;
    }
    const scroll = hit.getAttribute("data-scroll");
    const shown = root.LeadPilot.show(tab);
    if (scroll) {
      Promise.resolve(shown).then(function () {
        const target = document.querySelector(scroll);
        if (target) target.scrollIntoView({behavior: reduced() ? "auto" : "smooth", block: "start"});
      });
    }
  }

  function bind() {
    const node = host();
    if (!node || node.dataset.bound) return;
    node.dataset.bound = "1";
    node.addEventListener("click", function (event) {
      if (event.target.closest("[data-preview-lead]")) return;
      const hit = event.target.closest("[data-go]");
      if (!hit || !node.contains(hit)) return;
      goFrom(hit);
    });
  }

  function start() {
    if (started) return;
    started = true;
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) refresh({quiet: true});
    });
  }

  bind();
  root.Cockpit = {refresh: refresh, start: start};
})(window);
