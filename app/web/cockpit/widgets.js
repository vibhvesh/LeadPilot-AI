/* Shared cockpit drawings: gauges, lamps, horizon, and readouts. No data of its own. */
(function (root) {
  let paintToken = 0;

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[ch];
    });
  }

  function reduced() {
    return !!(root.matchMedia && root.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function point(cx, cy, radius, deg) {
    const rad = (deg - 90) * Math.PI / 180;
    return [cx + radius * Math.cos(rad), cy + radius * Math.sin(rad)];
  }

  function arc(cx, cy, radius, start, end) {
    const from = point(cx, cy, radius, start);
    const to = point(cx, cy, radius, end);
    const large = end - start > 180 ? 1 : 0;
    return "M " + from[0].toFixed(2) + " " + from[1].toFixed(2) + " A " + radius + " " + radius + " 0 " + large + " 1 " + to[0].toFixed(2) + " " + to[1].toFixed(2);
  }

  function ticks(cx, cy, radius) {
    let path = "";
    for (let deg = -120; deg <= 120; deg += 30) {
      const outer = point(cx, cy, radius, deg);
      const inner = point(cx, cy, radius - 5, deg);
      path += "M " + inner[0].toFixed(2) + " " + inner[1].toFixed(2) + " L " + outer[0].toFixed(2) + " " + outer[1].toFixed(2) + " ";
    }
    return path;
  }

  function drawGauge(svg, deg) {
    const cx = Number(svg.getAttribute("data-cx"));
    const cy = Number(svg.getAttribute("data-cy"));
    const radius = Number(svg.getAttribute("data-r"));
    const value = svg.querySelector(".gauge-value");
    const needle = svg.querySelector(".gauge-needle");
    if (value) value.setAttribute("d", deg <= -120 ? "" : arc(cx, cy, radius, -120, deg));
    if (needle) {
      const tip = point(cx, cy, radius - 10, deg);
      needle.setAttribute("x1", String(cx));
      needle.setAttribute("y1", String(cy));
      needle.setAttribute("x2", tip[0].toFixed(2));
      needle.setAttribute("y2", tip[1].toFixed(2));
    }
  }

  function settle(scope) {
    paintToken += 1;
    const token = paintToken;
    const still = reduced();
    scope.querySelectorAll("[data-gauge]").forEach(function (svg) {
      const to = Number(svg.getAttribute("data-to"));
      const target = Number.isFinite(to) ? to : -120;
      if (still) {
        drawGauge(svg, target);
        return;
      }
      const from = -120;
      drawGauge(svg, from);
      const started = root.performance ? root.performance.now() : Date.now();
      function step(now) {
        if (token !== paintToken) return;
        const t = Math.min(1, (now - started) / 700);
        const eased = 1 - Math.pow(1 - t, 3);
        drawGauge(svg, from + (target - from) * eased);
        if (t < 1) root.requestAnimationFrame(step);
      }
      root.requestAnimationFrame(step);
    });
    scope.querySelectorAll("[data-pitch]").forEach(function (node) {
      const pitch = Number(node.getAttribute("data-pitch")) || 0;
      node.style.setProperty("--pitch", still ? String(pitch) : "0");
      if (!still) {
        root.requestAnimationFrame(function () {
          if (token !== paintToken) return;
          node.style.setProperty("--pitch", String(pitch));
        });
      }
    });
  }

  function gauge(opts) {
    const cx = 60;
    const cy = 70;
    const radius = 42;
    const tone = opts.tone || "ok";
    const angle = Number(opts.angle);
    const to = Number.isFinite(angle) ? Math.max(-120, Math.min(120, angle)) : -120;
    const id = opts.centerId ? ' id="' + esc(opts.centerId) + '"' : "";
    return '<div class="gauge"><svg viewBox="0 0 120 88" data-gauge data-to="' + to + '" data-cx="' + cx + '" data-cy="' + cy + '" data-r="' + radius + '" aria-hidden="true">' +
      '<path class="gauge-track" d="' + arc(cx, cy, radius, -120, 120) + '"/>' +
      '<path class="gauge-ticks" d="' + ticks(cx, cy, radius + 7) + '"/>' +
      '<path class="gauge-value gauge-' + esc(tone) + '" d=""/>' +
      '<line class="gauge-needle"/><circle class="gauge-hub" cx="' + cx + '" cy="' + cy + '" r="3.5"/>' +
      '</svg><div class="gauge-read"' + id + ">" + esc(opts.center) + '</div><div class="gauge-caption">' + esc(opts.caption || "") + "</div></div>";
  }

  function readout(label, value, id, tone) {
    const mark = id ? ' id="' + esc(id) + '"' : "";
    const paint = tone ? " readout-" + tone : "";
    return '<div class="readout"><span class="readout-label">' + esc(label) + '</span><span class="readout-value' + paint + '"' + mark + ">" + esc(value) + "</span></div>";
  }

  function lamp(opts) {
    const level = opts.level || "ok";
    const visual = opts.visual || (level === "standby" ? "warn" : level);
    const attrs = [
      'type="button"',
      'class="lamp lamp-' + esc(visual) + '"',
      'id="' + esc(opts.id) + '"',
      'data-cockpit-level="' + esc(level) + '"',
      'data-cockpit-label="' + esc(opts.label || opts.name || "Status") + '"',
    ];
    if (opts.count != null && opts.count !== "") attrs.push('data-cockpit-count="' + esc(opts.count) + '"');
    if (opts.go) attrs.push('data-go="' + esc(opts.go) + '"');
    if (opts.module) attrs.push('data-module="' + esc(opts.module) + '"');
    if (opts.status) attrs.push('data-status="' + esc(opts.status) + '"');
    if (opts.urgency) attrs.push('data-urgency="' + esc(opts.urgency) + '"');
    if (opts.scroll) attrs.push('data-scroll="' + esc(opts.scroll) + '"');
    const count = opts.count != null && opts.count !== "" ? '<span class="lamp-count">' + esc(opts.count) + "</span>" : "";
    return "<button " + attrs.join(" ") + '><span class="lamp-bulb" aria-hidden="true"></span><span class="lamp-name">' + esc(opts.name) + "</span>" + count + "</button>";
  }

  function frame(id, label, inner, wide) {
    return '<section class="instrument' + (wide ? " instrument-wide" : "") + '" id="panel-' + esc(id) + '" aria-label="' + esc(label) + '">' + inner + "</section>";
  }

  function hit(fields, inner) {
    const attrs = ['class="instrument-hit"', 'type="button"'];
    Object.keys(fields || {}).forEach(function (key) {
      if (fields[key] == null || fields[key] === "") return;
      attrs.push(key + '="' + esc(fields[key]) + '"');
    });
    return "<button " + attrs.join(" ") + ">" + inner + "</button>";
  }

  function titleButton(label, fields) {
    const attrs = ['class="instrument-title"', 'type="button"'];
    Object.keys(fields || {}).forEach(function (key) {
      if (fields[key] == null || fields[key] === "") return;
      attrs.push(key + '="' + esc(fields[key]) + '"');
    });
    return "<button " + attrs.join(" ") + ">" + esc(label) + "</button>";
  }

  function angleFor(part, whole) {
    if (!whole) return -120;
    const ratio = Math.max(0, Math.min(1, part / whole));
    return -120 + ratio * 240;
  }

  function dayLabel(iso) {
    const date = new Date(String(iso) + "T00:00:00Z");
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleDateString(undefined, {weekday: "narrow", timeZone: "UTC"});
  }

  function attitude(trend) {
    const data = trend || {};
    const pitch = Number(data.pitch) || 0;
    const delta = Number(data.delta) || 0;
    const sign = delta > 0 ? "+" : "";
    const days = data.days || [];
    const max = Math.max.apply(null, days.map(function (day) { return Number(day.count) || 0; }).concat([1]));
    const bars = days.map(function (day) {
      const count = Number(day.count) || 0;
      const height = Math.round((count / max) * 100);
      return '<span class="day" title="' + esc(day.date) + ": " + count + '"><i style="height:' + height + '%"></i><b>' + esc(dayLabel(day.date)) + "</b></span>";
    }).join("");
    const state = pitch > 0.05 ? "Climb" : pitch < -0.05 ? "Descend" : "Level";
    return '<div class="attitude" data-pitch="' + pitch + '"><div class="attitude-bezel"><div class="attitude-ball"><div class="attitude-sky"></div><div class="attitude-ground"></div><div class="attitude-horizon"></div></div><div class="attitude-wings" aria-hidden="true"></div></div>' +
      '<div class="gauge-read">' + esc(sign + String(delta)) + '</div><div class="gauge-caption">' + esc(state) + " · vs prior 7 UTC days</div>" +
      '<div class="days">' + bars + "</div></div>";
  }

  function ago(iso) {
    if (!iso) return "No ingest yet";
    const then = Date.parse(iso);
    if (!Number.isFinite(then)) return "No ingest yet";
    const seconds = Math.max(0, Math.round((Date.now() - then) / 1000));
    if (seconds < 60) return seconds + "s ago";
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return minutes + "m ago";
    const hours = Math.round(minutes / 60);
    if (hours < 48) return hours + "h ago";
    return Math.round(hours / 24) + "d ago";
  }

  function money(value) {
    if (root.LeadPilot && root.LeadPilot.money) return root.LeadPilot.money(value);
    return String(value == null ? 0 : value);
  }

  function percent(value) {
    if (root.LeadPilot && root.LeadPilot.percent) return root.LeadPilot.percent(value);
    return ((Number(value) || 0) * 100).toFixed(1) + "%";
  }

  root.CockpitWidgets = {
    esc: esc,
    reduced: reduced,
    settle: settle,
    gauge: gauge,
    readout: readout,
    lamp: lamp,
    frame: frame,
    hit: hit,
    titleButton: titleButton,
    angleFor: angleFor,
    attitude: attitude,
    ago: ago,
    money: money,
    percent: percent,
  };
})(window);
