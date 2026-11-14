/* How many leads have both a phone and an email, or only one of them. */
(function (root) {
  root.CockpitPanels = root.CockpitPanels || {};
  root.CockpitPanels.contact = function (summary) {
    const widgets = root.CockpitWidgets;
    const leads = summary.leads || {};
    const contact = leads.contact || {};
    const total = Number(leads.total) || 0;
    const full = Number(contact.full) || 0;
    const phone = Number(contact.phone_only) || 0;
    const email = Number(contact.email_only) || 0;
    const missing = Number(contact.missing) || 0;
    const ratio = total ? full / total : 0;
    const tone = !total || ratio >= 0.6 ? "ok" : ratio >= 0.3 ? "warn" : "alert";
    const inner = widgets.gauge({
      angle: widgets.angleFor(full, total),
      center: total ? Math.round(ratio * 100) + "%" : "—",
      caption: "Full contact",
      tone: tone,
    }) + '<div class="readouts">' +
      widgets.readout("Full", String(full)) +
      widgets.readout("Phone", String(phone)) +
      widgets.readout("Email", String(email)) +
      widgets.readout("Neither", String(missing), "", missing ? "warn" : "") +
      "</div>";
    return widgets.frame("contact", "Contact completeness", widgets.hit({
      "data-go": "leads",
      "data-module": "leads",
      "aria-label": "Contact completeness. " + full + " leads have phone and email. Open leads",
    }, inner));
  };
})(window);
