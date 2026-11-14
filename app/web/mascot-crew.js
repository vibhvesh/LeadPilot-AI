/* Staged idle crew. One arrives each minute, they play, and Rocket Boss makes a round. */
(function (root) {
  const ROSTER = ["hanuman", "rama", "lakshmana", "sita", "jambavan", "krishna", "arjuna", "bhima", "narad", "rocket-boss"];
  const DECLINE = {hanuman: 1, rama: 1, narad: 1};

  function arrivals(idleMs, startMs, stepMs, cap) {
    const start = Number(startMs) || 60000;
    const step = Math.max(1000, Number(stepMs) || 60000);
    const limit = Math.max(1, Math.min(10, Number(cap) || 4));
    if (Number(idleMs) < start) return 0;
    return Math.min(limit, 1 + Math.floor((Number(idleMs) - start) / step));
  }

  function crewIds(idleMs, options) {
    const opts = options || {};
    const roster = opts.roster || ROSTER;
    const chosen = opts.chosen && roster.indexOf(opts.chosen) !== -1 ? opts.chosen : roster[0];
    const count = arrivals(idleMs, opts.startMs, opts.stepMs, opts.cap);
    const order = [chosen].concat(roster.filter(function (id) { return id !== chosen; }));
    return order.slice(0, count);
  }

  function withBoss(ids, idleMs, cheersMs) {
    const list = ids.slice();
    if (Number(idleMs) < (Number(cheersMs) || 300000)) return list;
    if (list.indexOf("rocket-boss") === -1) list.push("rocket-boss");
    return list;
  }

  function offer(family) {
    return family ? "Chai and a laddoo?" : "A cigar and a beer?";
  }

  function reply(id, family) {
    if (DECLINE[id]) {
      if (id === "narad") return family ? "Narayan Narayan. One laddoo, then back to the veena." : "Narayan Narayan. Not for me.";
      if (id === "rama") return family ? "Chai is welcome. The laddoo can wait." : "The bow stays clear of that. No, thank you.";
      return family ? "A laddoo is enough. Thank you." : "The mace does not clink with that. I will pass.";
    }
    return family ? "Chai. I accept." : "Ha! Cheers!";
  }

  const TIPS = {
    overview: "Home shows the cards that need you first.",
    leads: "Open a lead before you write. The summary is the short version.",
    social: "Copy the reply, then open the post yourself.",
    pulse: "Urgent cards are the ones with the red edge.",
    search: "Save a search, then run it. Nothing is sent.",
    pipeline: "Tap a stage to see who is sitting there.",
    followups: "Overdue reminders are the ones to clear first.",
  };

  function tip(page) {
    return TIPS[page] || "This page keeps the work in front of you.";
  }

  function headline(doc) {
    const scope = doc || root.document;
    if (!scope || !scope.querySelector) return "No headline on the page yet.";
    const node = scope.querySelector("#pulse-feed a, #social-feed a, .home-list a, .flash-title");
    const text = node && node.textContent ? node.textContent.trim() : "";
    return text ? text.slice(0, 80) : "No headline on the page yet.";
  }

  const api = {ROSTER: ROSTER, arrivals: arrivals, crewIds: crewIds, withBoss: withBoss, offer: offer, reply: reply, tip: tip, headline: headline};
  root.MascotCrewPlan = api;

  if (!root.document || !root.document.body) {
    if (typeof module !== "undefined" && module.exports) module.exports = api;
    return;
  }

  const doc = root.document;
  let prefs = {character: "hanuman", crew_cap: 4, crew_start_ms: 60000, crew_step_ms: 60000, cheers_ms: 300000, family_friendly: false, enabled: true};
  let idleMs = 0;
  let clock = 0;
  let members = [];
  let leaving = false;
  let playTimer = 0;
  let cheersDone = false;

  function reduced() {
    return root.matchMedia && root.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function page() {
    const active = doc.querySelector("section.page.active");
    return active ? active.id : "overview";
  }

  function say(el, text) {
    const bubble = el.querySelector(".crew-bubble");
    bubble.hidden = !text;
    bubble.textContent = text || "";
  }

  function place(el, index, total) {
    const width = root.innerWidth || 360;
    const height = root.innerHeight || 700;
    const slot = total <= 1 ? 0.5 : index / (total - 1);
    const left = 12 + slot * Math.max(40, width - 120);
    const top = height - 150 - (index % 2) * 24;
    el.style.left = Math.round(left) + "px";
    el.style.top = Math.round(Math.max(80, top)) + "px";
  }

  function paint() {
    const layer = doc.getElementById("mascot-crew");
    members.forEach(function (el, index) { place(el, index, members.length); });
    if (layer) layer.dataset.count = String(members.length);
  }

  function add(id, text) {
    if (members.some(function (el) { return el.dataset.character === id; })) return;
    const spec = root.MascotCharacters && root.MascotCharacters.byId(id);
    if (!spec) return;
    const el = doc.createElement("div");
    el.className = "crew-member" + (reduced() ? "" : " is-walking");
    el.dataset.character = id;
    el.innerHTML = `<div class="crew-figure">${spec.svg}</div><button type="button" class="crew-bubble" hidden></button>`;
    doc.body.appendChild(el);
    members.push(el);
    say(el, text || "");
    paint();
    root.setTimeout(function () { el.classList.remove("is-walking"); }, reduced() ? 0 : 700);
  }

  function removeOne() {
    const el = members.shift();
    if (!el) { leaving = false; return; }
    el.classList.add("is-walking", "is-leaving");
    root.setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, reduced() ? 0 : 500);
    paint();
    if (members.length) root.setTimeout(removeOne, 450);
    else leaving = false;
  }

  function sync() {
    if (!prefs.enabled || doc.hidden) return;
    const ids = withBoss(crewIds(idleMs, {
      chosen: prefs.character,
      cap: prefs.crew_cap,
      startMs: prefs.crew_start_ms,
      stepMs: prefs.crew_step_ms,
    }), idleMs, prefs.cheers_ms);
    ids.forEach(function (id, index) {
      const line = index === 0 ? (root.MascotCrewPlan.tip(page())) : "";
      add(id, line);
    });
    if (idleMs >= (Number(prefs.cheers_ms) || 300000) && !cheersDone && members.length > 1) {
      cheersDone = true;
      cheers();
    }
  }

  function cheers() {
    const boss = members.filter(function (el) { return el.dataset.character === "rocket-boss"; })[0];
    const others = members.filter(function (el) { return el !== boss; });
    if (!boss) return;
    others.forEach(function (other, index) {
      root.setTimeout(function () {
        say(boss, offer(!!prefs.family_friendly));
        say(other, reply(other.dataset.character, !!prefs.family_friendly));
        root.setTimeout(function () { say(boss, "Cheers!"); }, 900);
      }, index * 1600);
    });
  }

  function interact() {
    if (members.length < 2) return;
    const kinds = ["happy", "surprised", "laughing", "sleepy"];
    const mood = kinds[Math.floor(Math.random() * kinds.length)];
    const actor = members[Math.floor(Math.random() * members.length)];
    members.forEach(function (el) { el.classList.remove("crew-happy", "crew-surprised", "crew-angry", "crew-laughing", "crew-sleepy"); });
    actor.classList.add("crew-" + mood);
    const roll = Math.floor(Math.random() * 4);
    if (roll === 0) say(actor, "Boop. A playful shove, nothing sharp.");
    else if (roll === 1) say(actor, "News: " + headline(doc));
    else if (roll === 2) say(actor, mood === "sleepy" ? "zzz" : "Ha!");
    else {
      const width = root.innerWidth || 360;
      actor.style.left = Math.round(24 + Math.random() * Math.max(40, width - 140)) + "px";
    }
  }

  function bump() {
    idleMs += 1000;
    sync();
  }

  function reset() {
    idleMs = 0;
    cheersDone = false;
    if (!leaving && members.length) {
      leaving = true;
      removeOne();
    }
  }

  doc.addEventListener("pointerdown", reset, {passive: true});
  doc.addEventListener("keydown", reset);
  root.addEventListener("scroll", reset, {passive: true});
  doc.addEventListener("leadpilot:mascot-prefs", function (event) {
    prefs = Object.assign(prefs, event.detail || {});
  });
  clock = root.setInterval(bump, 1000);
  playTimer = root.setInterval(interact, 5000);

  api.noteActivity = reset;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
