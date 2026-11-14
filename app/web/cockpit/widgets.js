/* Card helpers for the homepage. */
(function (root) {
  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[ch];
    });
  }

  function reduced() {
    return !!(root.matchMedia && root.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function money(value) {
    if (root.LeadPilot && root.LeadPilot.money) return root.LeadPilot.money(value);
    return String(value == null ? 0 : value);
  }

  function percent(value) {
    if (root.LeadPilot && root.LeadPilot.percent) return root.LeadPilot.percent(value);
    return ((Number(value) || 0) * 100).toFixed(1) + "%";
  }

  function attrs(fields) {
    return Object.keys(fields || {}).filter(function (key) {
      return fields[key] != null && fields[key] !== "";
    }).map(function (key) {
      return key + '="' + esc(fields[key]) + '"';
    }).join(" ");
  }

  function stat(opts) {
    const id = opts.id ? ' id="' + esc(opts.id) + '"' : "";
    const delta = opts.delta ? '<div class="home-delta">' + esc(opts.delta) + "</div>" : "";
    const inner = '<div class="label">' + esc(opts.label) + '</div><div class="num"' + id + ">" + esc(opts.value) + "</div>" + delta;
    const fields = {"data-go": opts.go, "data-module": opts.module, "data-status": opts.status, "aria-label": opts.label + " " + opts.value};
    return '<button type="button" class="card home-stat" ' + attrs(fields) + ">" + inner + "</button>";
  }

  function card(title, inner) {
    return '<section class="card home-card"><h2>' + esc(title) + "</h2>" + inner + "</section>";
  }

  function alertRow(opts) {
    const fields = {
      id: opts.id,
      type: "button",
      class: "home-alert home-alert-" + (opts.level || "ok"),
      "data-cockpit-level": opts.level || "ok",
      "data-cockpit-label": opts.label,
      "data-cockpit-count": opts.count == null ? "" : opts.count,
      "data-go": opts.go,
      "data-module": opts.module,
      "data-status": opts.status,
      "data-urgency": opts.urgency,
    };
    return "<button " + attrs(fields) + "><b>" + esc(opts.name) + "</b><span>" + esc(opts.detail) + "</span></button>";
  }

  root.CockpitWidgets = {esc: esc, reduced: reduced, money: money, percent: percent, stat: stat, card: card, alertRow: alertRow};
})(window);
