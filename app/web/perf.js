/* Admin performance page. Live tiles, SVG history, and the stored error log. */
(function () {
  const ui = window.LeadPilot;
  if (!ui) return;
  const {$, api, esc, toast} = ui;
  let range = "1h";
  let timer = 0;

  function tone(value, warn, alert) {
    if (value >= alert) return "perf-alert";
    if (value >= warn) return "perf-warn";
    return "perf-ok";
  }

  function tile(label, value, klass) {
    return `<div class="perf-tile ${klass}"><span>${esc(label)}</span><b>${esc(value)}</b></div>`;
  }

  function chart(title, points) {
    const values = points.map((point) => Number(point) || 0);
    const max = Math.max.apply(null, values.concat([1]));
    const step = values.length > 1 ? 100 / (values.length - 1) : 100;
    const coords = values.map((value, index) => (index * step).toFixed(2) + "," + (70 - (value / max) * 64).toFixed(2)).join(" ");
    return `<div class="perf-tile perf-chart"><span>${esc(title)}</span><svg viewBox="0 0 100 72" preserveAspectRatio="none" aria-hidden="true"><polyline points="${coords}"/></svg></div>`;
  }

  function uptime(seconds) {
    const whole = Number(seconds) || 0;
    const hours = Math.floor(whole / 3600);
    const minutes = Math.floor((whole % 3600) / 60);
    return hours + "h " + minutes + "m";
  }

  async function live() {
    const data = await api("/api/admin/perf/current");
    const sample = data.sample || {};
    const host = $("perf-live");
    if (!host) return;
    const db = sample.db_size_bytes != null ? "up" : "n/a";
    host.innerHTML = [
      tile("CPU", (sample.cpu_percent || 0).toFixed(0) + "%", tone(sample.cpu_percent || 0, 70, 90)),
      tile("Memory", (sample.memory_percent || 0).toFixed(0) + "%", tone(sample.memory_percent || 0, 70, 90)),
      tile("Disk", (sample.disk_root_percent || 0).toFixed(0) + "%", tone(sample.disk_root_percent || 0, 80, 92)),
      tile("Requests", String(sample.request_count || 0), "perf-ok"),
      tile("Errors", String(sample.error_count || 0), (sample.error_count || 0) > 0 ? "perf-alert" : "perf-ok"),
      tile("p95", (sample.latency_p95 || 0).toFixed(0) + " ms", tone(sample.latency_p95 || 0, 300, 1000)),
      tile("Database", db, db === "up" ? "perf-ok" : "perf-warn"),
      tile("Uptime", uptime(data.uptime_seconds), "perf-ok"),
    ].join("");
  }

  async function history() {
    const data = await api("/api/admin/perf/history?range=" + encodeURIComponent(range));
    const samples = data.samples || [];
    const box = $("perf-charts");
    if (!box) return;
    box.innerHTML = [
      chart("CPU", samples.map((row) => row.cpu_percent)),
      chart("Memory", samples.map((row) => row.memory_percent)),
      chart("Disk", samples.map((row) => row.disk_root_percent)),
      chart("p95 ms", samples.map((row) => row.latency_p95)),
    ].join("");
  }

  function filters() {
    const query = new URLSearchParams();
    if ($("perf-level").value) query.set("level", $("perf-level").value);
    if ($("perf-source").value) query.set("source", $("perf-source").value);
    if ($("perf-path").value.trim()) query.set("path", $("perf-path").value.trim());
    if ($("perf-user").value.trim()) query.set("user_id", $("perf-user").value.trim());
    if ($("perf-since").value) query.set("since", $("perf-since").value);
    if ($("perf-until").value) query.set("until", $("perf-until").value);
    if ($("perf-resolved").value) query.set("resolved", $("perf-resolved").value);
    return query.toString();
  }

  async function errors() {
    const query = filters();
    const data = await api("/api/admin/errors" + (query ? "?" + query : ""));
    const body = $("perf-errors");
    const rows = data.errors || [];
    body.innerHTML = rows.length ? rows.map((row) => `<tr data-error="${row.id}"><td>${esc(row.last_seen || "")}</td><td>${esc(row.level)}</td><td>${esc(row.method)} ${esc(row.path)}</td><td>${esc(row.count)}</td><td>${row.resolved ? "Resolved" : "Open"}</td></tr>`).join("") : `<tr><td colspan="5">No stored errors.</td></tr>`;
  }

  async function detail(id) {
    const data = await api("/api/admin/errors/" + id);
    const box = $("perf-detail");
    box.hidden = false;
    const events = (data.occurrences || []).map((event) => `<li>${esc(event.created_at || "")} · user ${esc(event.user_id || "—")} · ${esc(event.request_id || "")}</li>`).join("");
    box.innerHTML = `<h2>${esc(data.message || "Error")}</h2><p class="muted">${esc(data.count)} times · ${esc(data.path)}</p><pre class="perf-trace">${esc(data.sample_trace || "No stack trace stored.")}</pre><ul>${events}</ul><button class="btn" type="button" id="perf-resolve">${data.resolved ? "Reopen" : "Mark resolved"}</button>`;
    $("perf-resolve").onclick = async () => {
      await api("/api/admin/errors/" + id + "/resolve", {method: "POST", body: {resolved: !data.resolved}});
      toast(data.resolved ? "Reopened" : "Resolved");
      await errors();
      await detail(id);
    };
  }

  async function load() {
    await live();
    await history();
    await errors();
  }

  function boot() {
    const root = document.getElementById("performance");
    if (!root) return;
    root.addEventListener("click", (event) => {
      const rangeButton = event.target.closest("[data-range]");
      if (rangeButton) {
        range = rangeButton.dataset.range;
        history().catch((error) => toast(error.message));
        return;
      }
      const row = event.target.closest("[data-error]");
      if (row) detail(row.dataset.error).catch((error) => toast(error.message));
    });
    const form = $("perf-filters");
    if (form) form.addEventListener("submit", (event) => { event.preventDefault(); errors().catch((error) => toast(error.message)); });
    window.clearInterval(timer);
    timer = window.setInterval(() => {
      if (!root.classList.contains("active") || document.hidden) return;
      live().catch(() => {});
    }, 12000);
  }

  boot();
  window.PerfPage = {load: load};
})();
