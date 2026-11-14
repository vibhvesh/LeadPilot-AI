/* Ten caricature walkers for the story page. Does not touch the live mascot crew. */
(function (root) {
  const V = "crew1";
  const CAST = [
    { id: "chacha", name: "Chai Wala Chacha", scene: "s01", line: "Chai garam!", frame: 119 },
    { id: "aunty", name: "Drama Aunty", scene: "s02", line: "Hai Ram, ye kya ho raha hai!", frame: 117 },
    { id: "bunty", name: "Gamer Bunty", scene: "s03", line: "Ek aur round!", frame: 111 },
    { id: "dabbu", name: "Delivery Dabbu", scene: "s04", line: "Order aa gaya!", frame: 116 },
    { id: "golu", name: "Gym Bro Golu", scene: "s05", line: "Ek aur set!", frame: 118 },
    { id: "uncle", name: "Uncle Ji", scene: "s06", line: "Arre beta, sambhal ke!", frame: 103 },
    { id: "simran", name: "Selfie Simran", scene: "s07", line: "Ek selfie please!", frame: 114 },
    { id: "chintu", name: "Coder Chintu", scene: "s08", line: "It works on my machine", frame: 117 },
    { id: "ashok", name: "Auto Wala Ashok", scene: "s09", line: "Meter down!", frame: 105 },
    { id: "pappu", name: "Pandit Pappu", scene: "s10", line: "Aashirvad, beta!", frame: 121 },
  ];

  function byId(id) {
    for (let i = 0; i < CAST.length; i += 1) if (CAST[i].id === id) return CAST[i];
    return null;
  }

  function lineFor(person, lines) {
    const key = person.scene + ":say";
    if (lines && typeof lines[key] === "string" && lines[key].trim()) return lines[key];
    return person.line;
  }

  function slots(count) {
    const cols = 5;
    const placed = [];
    for (let i = 0; i < count; i += 1) {
      const col = i % cols;
      const row = Math.floor(i / cols);
      placed.push({
        x: 0.08 + ((col + 0.5) / cols) * 0.84,
        y: 6 + row * 18,
        fromLeft: col < 2 || (col === 2 && i % 2 === 0),
      });
    }
    const order = CAST.map(function (_, index) { return index; });
    for (let i = order.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      const swap = order[i];
      order[i] = order[j];
      order[j] = swap;
    }
    return order.map(function (index) { return { person: CAST[index], spot: placed[index] }; });
  }

  function start(host, options) {
    const opts = options || {};
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const layer = document.createElement("div");
    layer.className = "story-crew-layer" + (reduced ? " is-still" : "");
    host.appendChild(layer);
    const plan = slots(CAST.length);
    const talkers = plan.slice().sort(function () { return Math.random() - 0.5; }).slice(0, 2);
    const nodes = [];
    let alive = true;
    const waits = [];
    function later(fn, ms) {
      const id = window.setTimeout(function () { if (alive) fn(); }, ms);
      waits.push(id);
    }
    plan.forEach(function (item, index) {
      const person = item.person;
      const spot = item.spot;
      const node = document.createElement("div");
      node.className = "story-crew" + (spot.fromLeft ? "" : " is-left");
      node.style.left = (spot.fromLeft ? -20 : 108) + "%";
      node.style.bottom = spot.y + "%";
      node.setAttribute("aria-label", person.name);
      const body = document.createElement("div");
      body.className = "story-crew-body";
      const sprite = document.createElement("div");
      sprite.className = "story-crew-sprite";
      sprite.style.width = "calc(var(--crew-h) * " + (person.frame / 220) + ")";
      sprite.style.backgroundImage = "url(/static/story/crew/" + person.id + "-strip.png?v=" + V + ")";
      body.appendChild(sprite);
      node.appendChild(body);
      const shadow = document.createElement("div");
      shadow.className = "story-crew-shadow";
      node.appendChild(shadow);
      if (talkers.indexOf(item) !== -1) {
        const bubble = document.createElement("p");
        bubble.className = "story-crew-bubble";
        bubble.textContent = lineFor(person, opts.lines);
        node.appendChild(bubble);
      }
      layer.appendChild(node);
      nodes.push(node);
      if (reduced) {
        node.style.left = (spot.x * 100) + "%";
        node.classList.add("is-paused");
        return;
      }
      const delay = Math.floor(Math.random() * 2200) + index * 40;
      const travel = 2200 + Math.floor(Math.random() * 1800);
      later(function () {
        node.style.transition = "left " + travel + "ms linear, bottom " + travel + "ms ease";
        node.style.left = (spot.x * 100) + "%";
        node.style.bottom = (spot.y + Math.random() * 3) + "%";
        later(function () {
          node.classList.add("is-paused");
          later(function () { node.classList.remove("is-paused"); }, 900 + Math.floor(Math.random() * 700));
        }, travel + 200);
      }, delay);
    });
    return {
      stop: function () {
        alive = false;
        waits.forEach(function (id) { window.clearTimeout(id); });
        layer.remove();
      },
      count: function () { return nodes.length; },
    };
  }

  function mountEditor(lines) {
    const box = document.getElementById("story-lines");
    if (!box) return;
    box.innerHTML = "";
    CAST.forEach(function (person) {
      const row = document.createElement("div");
      row.className = "story-line";
      row.dataset.scene = person.scene;
      row.dataset.actor = "say";
      row.dataset.fallback = person.line;
      const label = document.createElement("label");
      label.textContent = person.name;
      const area = document.createElement("textarea");
      area.maxLength = 240;
      area.value = lineFor(person, lines);
      const saveBtn = document.createElement("button");
      saveBtn.type = "button";
      saveBtn.textContent = "Save";
      const resetBtn = document.createElement("button");
      resetBtn.type = "button";
      resetBtn.textContent = "Reset";
      const status = document.createElement("span");
      status.className = "story-save-note";
      saveBtn.addEventListener("click", async function () {
        const res = await fetch("/api/admin/story-messages", {
          method: "PUT",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scene_id: person.scene, actor: "say", text: area.value }),
        });
        status.textContent = res.ok ? "Saved" : "Could not save";
      });
      resetBtn.addEventListener("click", async function () {
        const res = await fetch("/api/admin/story-messages/reset", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scene_id: person.scene, actor: "say" }),
        });
        if (res.ok) {
          area.value = person.line;
          status.textContent = "Reset";
        }
      });
      label.appendChild(area);
      row.append(label, saveBtn, resetBtn, status);
      box.appendChild(row);
    });
  }

  const api = { CAST: CAST, V: V, byId: byId, lineFor: lineFor, start: start, mountEditor: mountEditor };
  root.StoryCrew = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  function mountSwitch() {
    const toggle = document.getElementById("story-enabled");
    if (!toggle) return;
    toggle.addEventListener("change", function () {
      fetch("/api/admin/story-overlay", {
        method: "PUT",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: toggle.checked }),
      });
    });
    fetch("/api/story/overlay", { credentials: "same-origin" }).then(function (res) {
      return res.ok ? res.json() : { enabled: false };
    }).then(function (data) { toggle.checked = data.enabled === true; }).catch(function () { toggle.checked = false; });
  }

  if (typeof document !== "undefined") {
    mountSwitch();
    fetch("/api/story/lines", { credentials: "same-origin" }).then(function (res) {
      return res.ok ? res.json() : { lines: {} };
    }).then(function (data) { mountEditor(data.lines || {}); }).catch(function () { mountEditor({}); });
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
