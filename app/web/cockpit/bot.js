/* Last Grok Bot ingest and the deep-search request queue. */
(function (root) {
  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.bot = function (summary) {
    const widgets = root.CockpitWidgets;
    if (!summary.bot) {
      return widgets.frame("bot", "Grok Bot", "<h2>Grok Bot</h2><p class=\"instrument-note\">Grok Bot is not on your instruments</p>");
    }
    const bot = summary.bot;
    const requests = bot.requests || {};
    const failed = Number(bot.webhook_failed) || 0;
    const pending = Number(requests.pending) || 0;
    const claimed = Number(requests.claimed) || 0;
    const completed = Number(requests.completed) || 0;
    const when = bot.last_ingest_at
      ? '<div class="readout"><span class="readout-label">Last ingest</span><time class="readout-value" datetime="' + widgets.esc(bot.last_ingest_at) + '">' + widgets.esc(widgets.ago(bot.last_ingest_at)) + "</time></div>"
      : widgets.readout("Last ingest", "No ingest yet");
    const inner = "<h2>Grok Bot</h2>" + when +
      '<div class="readouts">' +
      widgets.readout("Pending", String(pending), "", pending ? "warn" : "") +
      widgets.readout("Claimed", String(claimed)) +
      widgets.readout("Done", String(completed)) +
      widgets.readout("Webhook", String(failed), "", failed ? "alert" : "") +
      "</div>";
    const go = root.LeadPilot && root.LeadPilot.can("search") ? "search" : "grokbot";
    return widgets.frame("bot", "Grok Bot", widgets.hit({
      "data-go": go,
      "data-module": "search,grokbot",
      "aria-label": "Grok Bot last ingest " + widgets.ago(bot.last_ingest_at) + ". " + pending + " pending requests",
    }, inner));
  };
})(window);
