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

  function actorNode(actor, line, index, reduced) {
    const node = document.createElement("div");
    node.className = "story-actor story-from-" + (actor.entry || "left") + " story-do-" + (actor.action || "walk");
    node.style.left = actor.entry === "right" ? "108%" : actor.entry === "top" ? "42%" : "-18%";
    node.style.bottom = actor.entry === "top" ? "110%" : "8%";
    node.setAttribute("aria-label", root.RamayanaCast.name(actor.id));
    node.innerHTML = root.RamayanaCast.svg(actor.id);
    if (line) node.appendChild(bubble(line));
    const left = (6 + (index % 6) * 14) + "%";
    if (reduced) {
      node.style.left = left;
      node.style.bottom = "8%";
    } else {
      requestAnimationFrame(function () {
        node.style.left = left;
        node.style.bottom = "8%";
      });
    }
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
    star.textContent = "✦";
    star.style.left = x;
    const dust = document.createElement("span");
    dust.className = "story-dust";
    dust.style.left = x;
    stage.appendChild(star);
    stage.appendChild(dust);
  }

  function start(host, options) {
    const opts = options || {};
    const scenes = root.RamayanaScenes.list();
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let index = opts.start == null ? readIndex(scenes.length) : opts.start;
    if (index < 0 || index >= scenes.length) index = 0;
    let alive = true;
    let timer = 0;
    const stage = document.createElement("div");
    stage.className = "story-stage" + (reduced ? " story-still" : "");
    host.appendChild(stage);

    function show(next) {
      index = (next + scenes.length) % scenes.length;
      writeIndex(index);
      const scene = scenes[index];
      stage.innerHTML = "";
      stage.dataset.scene = scene.id;
      stage.dataset.backdrop = scene.backdrop;
      const caption = document.createElement("p");
      caption.className = "story-caption";
      caption.textContent = textFor(scene, "narad", opts.lines);
      stage.appendChild(caption);
      scene.extras.forEach(function (id, extraIndex) {
        const extra = actorNode({ id: id, entry: extraIndex % 2 ? "right" : "left", action: "cheer" }, "", extraIndex + 3, reduced);
        extra.classList.add("story-extra-actor");
        stage.appendChild(extra);
      });
      scene.actors.forEach(function (actor, actorIndex) {
        const node = actorNode(actor, textFor(scene, actor.id, opts.lines), actorIndex, reduced);
        stage.appendChild(node);
        if (!reduced && (actor.action === "shoot" || actor.action === "fight")) shoot(stage, (12 + actorIndex * 14) + "%");
      });
      if (opts.overlay && opts.overlay.interact) opts.overlay.interact(scene.play);
      if (scene.gag) gag(scene);
      timer = window.setTimeout(function () {
        if (alive) show(index + 1);
      }, scene.duration);
    }

    function gag(scene) {
      const elder = actorNode({ id: "old-man-boss", entry: "left", action: "walk" }, textFor(scene, "old-man-boss", opts.lines), 4, reduced);
      const boss = actorNode({ id: "rocket-boss", entry: "top", action: "fly" }, textFor(scene, "rocket-boss", opts.lines), 5, reduced);
      elder.classList.add("story-boss");
      boss.classList.add("story-boss");
      stage.append(elder, boss);
      const chase = document.createElement("p");
      chase.className = "story-chase";
      chase.textContent = textFor(scene, "chase", opts.lines);
      stage.appendChild(chase);
      if (reduced) return;
      window.setTimeout(function () {
        if (!alive) return;
        stage.querySelectorAll(".story-actor:not(.story-boss)").forEach(function (node) {
          node.classList.add("story-chase-run");
        });
        bonk(stage, "58%");
        bonk(stage, "78%");
        elder.classList.add("story-dazed");
        boss.classList.add("story-dazed");
      }, 1600);
    }

    show(index);
    return {
      index: function () { return index; },
      stop: function () {
        alive = false;
        window.clearTimeout(timer);
        writeIndex(index);
        stage.remove();
      },
    };
  }

  const api = { start: start, textFor: textFor, KEY: KEY };
  root.RamayanaStory = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
