/* Plays the scripted Ramayana on a host element. Does not touch the live mascot crew. */
(function (root) {
  const KEY = "leadpilot-character-story";

  function textFor(scene, actor, overrides) {
    const key = scene.id + ":" + actor;
    if (overrides && typeof overrides[key] === "string" && overrides[key].trim()) return overrides[key];
    return (scene.lines && scene.lines[actor]) || "";
  }

  function readIndex(total) {
    try {
      const n = Number(localStorage.getItem(KEY));
      if (Number.isFinite(n) && n >= 0 && n < total) return n;
    } catch (error) { /* private mode */ }
    return 0;
  }

  function writeIndex(index) {
    try { localStorage.setItem(KEY, String(index)); } catch (error) { /* ignore */ }
  }

  function bubble(text) {
    const node = document.createElement("p");
    node.className = "story-bubble";
    node.textContent = text;
    return node;
  }

  const WEAPON = {
    rama: "bow", lakshmana: "bow", hanuman: "gada", sugriva: "club", kumbhakarna: "club",
    ravana: "sword", jambavan: "staff", narad: "veena", sita: "lotus",
  };

  function spread(count) {
    const spots = [];
    const slots = Math.max(count, 1);
    for (let i = 0; i < slots; i += 1) spots.push(0.08 + ((i + 0.5) / slots) * 0.84);
    for (let i = spots.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      const swap = spots[i];
      spots[i] = spots[j];
      spots[j] = swap;
    }
    return spots;
  }

  function actorNode(actor, line, spot, reduced, later) {
    const node = document.createElement("div");
    const fromLeft = Math.random() < 0.5;
    node.className = "story-actor story-do-" + (actor.action || "walk") + (fromLeft ? "" : " story-face-left");
    node.setAttribute("aria-label", root.RamayanaCast.name(actor.id));
    const kind = WEAPON[actor.id] ? '<span class="story-weapon story-weapon-' + WEAPON[actor.id] + '" aria-hidden="true"></span>' : "";
    const figure = document.createElement("div");
    figure.className = "story-figure";
    figure.innerHTML = root.RamayanaCast.svg(actor.id) + kind;
    node.appendChild(figure);
    if (line) node.appendChild(bubble(line));
    const land = 4 + Math.random() * 12;
    node.style.left = (fromLeft ? -24 : 108) + "%";
    node.style.bottom = land + "%";
    if (reduced) {
      node.style.left = (spot * 100) + "%";
      return node;
    }
    const delay = Math.floor(Math.random() * 1400);
    const travel = 1500 + Math.floor(Math.random() * 1700);
    later(function () {
      node.style.transition = "left " + travel + "ms ease, bottom " + travel + "ms ease";
      node.style.left = (spot * 100) + "%";
      node.style.bottom = land + "%";
      later(function () {
        const drift = Math.max(0.06, Math.min(0.9, spot + (Math.random() - 0.5) * 0.08));
        node.style.transition = "left 2400ms ease";
        node.style.left = (drift * 100) + "%";
      }, travel + 500);
    }, delay);
    return node;
  }

  function shoot(stage, fromLeft) {
    const arrow = document.createElement("div");
    arrow.className = "story-arrow";
    arrow.textContent = "➤";
    arrow.style.left = fromLeft;
    stage.appendChild(arrow);
    let x = parseFloat(fromLeft) || 20;
    let frame = 0;
    function step() {
      if (!arrow.isConnected) return;
      x += 7;
      frame += 1;
      arrow.style.left = x + "%";
      if (x < 78 && frame < 40) requestAnimationFrame(step);
      else arrow.classList.add("story-hit");
    }
    requestAnimationFrame(step);
  }

  function bonk(stage, x) {
    const star = document.createElement("span");
    star.className = "story-bonk";
    star.textContent = "BONK";
    star.style.left = x;
    const dust = document.createElement("span");
    dust.className = "story-dust";
    dust.style.left = x;
    stage.appendChild(star);
    stage.appendChild(dust);
  }

  const HANDS = '<svg class="story-namaste" viewBox="0 0 24 28" aria-hidden="true"><path d="M12 6 v14 M8 9 v9 M16 9 v9" fill="none" stroke="#e0b08a" stroke-width="2.4" stroke-linecap="round"/></svg>';

  function start(host, options) {
    const opts = options || {};
    const scenes = root.RamayanaScenes.list();
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let index = opts.start == null ? readIndex(scenes.length) : opts.start;
    if (index < 0 || index >= scenes.length) index = 0;
    let alive = true;
    const waits = [];
    let spots = [];
    let spotAt = 0;
    let bubblesLeft = 1;
    const stage = document.createElement("div");
    stage.className = "story-stage" + (reduced ? " story-still" : "");
    host.appendChild(stage);

    function later(fn, ms) {
      const id = window.setTimeout(function () { if (alive) fn(); }, ms);
      waits.push(id);
    }

    function takeLine(line) {
      if (!line || bubblesLeft <= 0) return "";
      bubblesLeft -= 1;
      return line;
    }

    function place(actor, line) {
      const spot = spots[spotAt] == null ? 0.2 + Math.random() * 0.6 : spots[spotAt];
      spotAt += 1;
      return actorNode(actor, takeLine(line), spot, reduced, later);
    }

    function show(next) {
      index = (next + scenes.length) % scenes.length;
      writeIndex(index);
      const scene = scenes[index];
      stage.innerHTML = "";
      stage.classList.remove("story-in-blessing");
      stage.dataset.scene = scene.id;
      stage.dataset.backdrop = scene.backdrop;
      const population = scene.actors.length + scene.extras.length + (scene.gag ? 2 : 0) + (scene.blessing ? 1 : 0);
      spots = spread(population);
      spotAt = 0;
      bubblesLeft = 1;
      const caption = document.createElement("p");
      caption.className = "story-caption";
      caption.textContent = textFor(scene, "narad", opts.lines);
      stage.appendChild(caption);
      scene.extras.forEach(function (id) {
        const extra = place({ id: id, action: "cheer" }, "");
        extra.classList.add("story-extra-actor");
        stage.appendChild(extra);
      });
      scene.actors.forEach(function (actor, actorIndex) {
        const node = place(actor, textFor(scene, actor.id, opts.lines));
        stage.appendChild(node);
        if (!reduced && (actor.action === "shoot" || actor.action === "fight")) shoot(stage, (18 + actorIndex * 8) + "%");
      });
      if (opts.overlay && opts.overlay.interact) opts.overlay.interact(scene.play);
      if (scene.gag) gag(scene);
      if (scene.blessing) bless(scene);
      later(function () { show(index + 1); }, scene.duration);
    }

    function gag(scene) {
      const elder = place({ id: "old-man-boss", action: "walk" }, textFor(scene, "old-man-boss", opts.lines));
      const boss = place({ id: "rocket-boss", action: "fly" }, textFor(scene, "rocket-boss", opts.lines));
      elder.classList.add("story-boss");
      boss.classList.add("story-boss");
      stage.append(elder, boss);
      if (reduced) return;
      later(function () {
        if (stage.classList.contains("story-in-blessing")) return;
        stage.querySelectorAll(".story-actor:not(.story-boss):not(.story-sage)").forEach(function (node) {
          node.classList.add("story-chase-run");
        });
        bonk(stage, "58%");
        bonk(stage, "78%");
        elder.classList.add("story-dazed");
        boss.classList.add("story-dazed");
      }, scene.blessing ? 3600 : 1600);
    }

    function bless(scene) {
      const sage = place({ id: "valmiki", action: "walk" }, textFor(scene, "valmiki", opts.lines));
      sage.classList.add("story-sage");
      const glow = document.createElement("div");
      glow.className = "story-glow";
      stage.append(glow, sage);
      function bow() {
        stage.classList.add("story-in-blessing");
        stage.querySelectorAll(".story-actor:not(.story-sage)").forEach(function (node) {
          node.classList.add("story-pranam");
          if (!node.querySelector(".story-namaste")) node.insertAdjacentHTML("beforeend", HANDS);
        });
        stage.querySelectorAll(".story-boss").forEach(function (node) {
          node.classList.add("story-sheepish");
          if (node.querySelector(".story-dropped")) return;
          const loot = document.createElement("span");
          loot.className = "story-dropped";
          const spot = node.getBoundingClientRect();
          const frame = stage.getBoundingClientRect();
          loot.style.left = Math.max(8, spot.left - frame.left) + "px";
          loot.style.bottom = "6%";
          stage.appendChild(loot);
        });
        stage.querySelectorAll(".story-arrow, .story-chase").forEach(function (node) {
          node.classList.add("story-paused");
        });
        sage.classList.add("story-blessing");
        glow.classList.add("story-glow-on");
      }
      function resume() {
        stage.classList.remove("story-in-blessing");
        stage.querySelectorAll(".story-pranam").forEach(function (node) { node.classList.remove("story-pranam"); });
        stage.querySelectorAll(".story-paused").forEach(function (node) { node.classList.remove("story-paused"); });
      }
      if (reduced) {
        bow();
        return;
      }
      later(bow, 800);
      later(resume, 3200);
    }

    show(index);
    return {
      index: function () { return index; },
      stop: function () {
        alive = false;
        waits.forEach(function (id) { window.clearTimeout(id); });
        writeIndex(index);
        stage.remove();
      },
    };
  }

  const api = { start: start, textFor: textFor, KEY: KEY };
  root.RamayanaStory = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
