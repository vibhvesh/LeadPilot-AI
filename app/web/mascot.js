/* Host for the corner cast. Hide still uses leadpilot-hanuman. Characters, idle, and insights are separate modules. */
(function () {
  const STORAGE_KEY = "leadpilot-hanuman";
  const POSES = ["pose-bounce", "pose-wink", "pose-scratch"];
  let host = null;
  let restore = null;
  let bubble = null;
  let hit = null;
  let picker = null;
  let nameButton = null;
  let live = null;
  let idleControl = null;
  let characterId = "hanuman";
  let visiting = false;
  let currentCue = null;
  let poseTimer = 0;
  let poseIndex = 0;
  let pinToken = 0;
  let spotlightTimer = 0;
  let prefs = {enabled: true, idle_ms: 2600, tone: "cheeky", size: "medium", side: "right", character: "hanuman"};

  function reducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function hidden() {
    try { return localStorage.getItem(STORAGE_KEY) === "hidden"; }
    catch (error) { return false; }
  }

  function setHidden(value) {
    try { localStorage.setItem(STORAGE_KEY, value ? "hidden" : "shown"); }
    catch (error) { /* private mode keeps the choice for this page only */ }
  }

  function readCharacter() {
    try {
      const stored = localStorage.getItem(window.MascotCharacters.STORAGE_KEY);
      if (stored && window.MascotCharacters.byId(stored)) return stored;
    } catch (error) { /* keep the default monkey */ }
    return "hanuman";
  }

  function character() {
    return window.MascotCharacters.byId(characterId) || window.MascotCharacters.byId("hanuman");
  }

  function setPose(name) {
    POSES.forEach(function (pose) { host.classList.toggle(pose, pose === name); });
  }

  function restorePose() {
    if (reducedMotion()) {
      setPose("");
      return;
    }
    setPose("pose-" + (character().pose || "bounce"));
  }

  function renderPicker() {
    picker.innerHTML = window.MascotCharacters.list().map(function (item) {
      const selected = item.id === characterId ? "true" : "false";
      return `<button type="button" class="hanuman-option" role="option" data-pick="${item.id}" aria-selected="${selected}"><b>${item.name}</b><span>${item.blurb}</span></button>`;
    }).join("");
  }

  function renderCharacter() {
    const item = character();
    hit.innerHTML = item.svg;
    hit.setAttribute("aria-label", item.name + ". Show what matters on this page.");
    nameButton.textContent = item.name;
    nameButton.setAttribute("aria-label", "Choose mascot. Current: " + item.name);
    restore.textContent = "Show " + item.name;
    host.dataset.character = item.id;
    renderPicker();
    if (!host.classList.contains("is-walking")) restorePose();
  }

  function closePicker() {
    picker.hidden = true;
    nameButton.setAttribute("aria-expanded", "false");
  }

  function selectCharacter(id) {
    const item = window.MascotCharacters.byId(id);
    if (!item) return;
    characterId = item.id;
    try { localStorage.setItem(window.MascotCharacters.STORAGE_KEY, item.id); }
    catch (error) { /* the choice still applies until reload */ }
    if (!host) return;
    renderCharacter();
    if (currentCue && currentCue.kind && currentCue.kind !== "event" && !bubble.hidden) {
      const text = window.MascotCharacters.quip(characterId, Object.assign({tone: prefs.tone}, currentCue));
      currentCue.text = text;
      showBubble(text);
    }
    closePicker();
  }

  function mount() {
    characterId = readCharacter();
    host = document.createElement("div");
    host.id = "hanuman";
    host.className = "hanuman is-fixed";
    host.setAttribute("data-mascot-root", "");
    host.innerHTML = `<button type="button" class="hanuman-bubble" hidden></button>
      <div id="mascot-picker" class="hanuman-picker" role="listbox" aria-label="Mascots" hidden></div>
      <button type="button" class="hanuman-hit"></button>
      <div class="hanuman-tools">
        <button type="button" class="hanuman-name" aria-expanded="false" aria-controls="mascot-picker"></button>
        <button type="button" class="hanuman-next" aria-label="Next mascot">Next</button>
        <button type="button" class="hanuman-settings">Settings</button>
        <button type="button" class="hanuman-hide">Hide</button>
      </div>`;
    restore = document.createElement("button");
    restore.type = "button";
    restore.className = "hanuman-show";
    restore.setAttribute("data-mascot-show", "");
    live = document.createElement("div");
    live.className = "mascot-live";
    live.setAttribute("aria-live", "polite");
    document.body.appendChild(host);
    document.body.appendChild(restore);
    document.body.appendChild(live);
    bubble = host.querySelector(".hanuman-bubble");
    hit = host.querySelector(".hanuman-hit");
    picker = host.querySelector(".hanuman-picker");
    nameButton = host.querySelector(".hanuman-name");
    renderCharacter();
    hit.addEventListener("click", onCharacterClick);
    bubble.addEventListener("click", onBubbleClick);
    nameButton.addEventListener("click", function () {
      const open = picker.hidden;
      picker.hidden = !open;
      nameButton.setAttribute("aria-expanded", open ? "true" : "false");
    });
    host.querySelector(".hanuman-next").addEventListener("click", function () {
      selectCharacter(window.MascotCharacters.next(characterId).id);
    });
    picker.addEventListener("click", function (event) {
      const button = event.target.closest("[data-pick]");
      if (button) selectCharacter(button.getAttribute("data-pick"));
    });
    host.querySelector(".hanuman-settings").addEventListener("click", function () {
      if (window.MascotSettings) window.MascotSettings.open();
    });
    host.querySelector(".hanuman-hide").addEventListener("click", function () {
      prefs.enabled = false;
      setHidden(true);
      applyVisibility();
      if (window.MascotSettings) window.MascotSettings.save({enabled: false});
    });
    restore.addEventListener("click", function () {
      prefs.enabled = true;
      setHidden(false);
      applyVisibility();
      if (window.MascotSettings) window.MascotSettings.save({enabled: true});
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && picker && !picker.hidden) closePicker();
    });
    document.addEventListener("pointerdown", function (event) {
      if (picker && !picker.hidden && !event.target.closest("[data-mascot-root]")) closePicker();
    });
    applyVisibility();
  }

  function applyVisibility() {
    const off = hidden();
    host.hidden = off;
    restore.hidden = !off;
    if (off) {
      hideBubble();
      visiting = false;
      if (idleControl) idleControl.pause();
      window.clearInterval(poseTimer);
    } else if (idleControl) {
      idleControl.arm();
      startPoses();
    }
  }

  function showBubble(text) {
    bubble.hidden = !text;
    bubble.textContent = text || "";
    live.textContent = text || "";
  }

  function hideBubble() {
    bubble.hidden = true;
    bubble.textContent = "";
  }

  function moveTo(left, top, layout) {
    if (reducedMotion()) host.classList.remove("is-walking");
    if (host.classList.contains("is-fixed")) {
      const rect = host.getBoundingClientRect();
      host.classList.remove("is-fixed");
      host.style.left = rect.left + "px";
      host.style.top = rect.top + "px";
      void host.offsetWidth;
    }
    if (layout) {
      host.classList.toggle("bubble-flip", !!layout.flip);
      host.classList.toggle("bubble-below", !!layout.below);
    }
    if (!reducedMotion()) host.classList.add("is-walking");
    host.style.left = left + "px";
    host.style.top = top + "px";
  }

  function schedulePin() {
    const token = ++pinToken;
    function done() {
      if (token !== pinToken || visiting) return;
      host.classList.remove("is-walking");
      host.classList.add("is-fixed");
      host.style.left = "";
      host.style.top = "";
      host.classList.remove("bubble-flip", "bubble-below");
      restorePose();
    }
    function onEnd(event) {
      if (event.propertyName !== "left") return;
      host.removeEventListener("transitionend", onEnd);
      done();
    }
    host.addEventListener("transitionend", onEnd);
    window.setTimeout(function () {
      host.removeEventListener("transitionend", onEnd);
      done();
    }, 700);
  }

  function goHome() {
    visiting = false;
    currentCue = null;
    hideBubble();
    closePicker();
    if (idleControl) idleControl.endVisit();
    host.classList.remove("bubble-flip", "bubble-below");
    if (host.classList.contains("is-fixed") && !host.classList.contains("is-walking")) {
      restorePose();
      return;
    }
    if (reducedMotion()) {
      host.classList.add("is-fixed");
      host.classList.remove("is-walking");
      host.style.left = "";
      host.style.top = "";
      restorePose();
      return;
    }
    const dock = window.MascotIdle.dockPoint(host.offsetWidth || 112, host.offsetHeight || 140, window.innerWidth, window.innerHeight, prefs.side);
    moveTo(dock.left, dock.top);
    schedulePin();
  }

  function currentInsight() {
    try { return window.MascotInsights.choose(window.MascotInsights.read(document)); }
    catch (error) { return {kind: "generic", selector: "section.page.active h1", facts: {}}; }
  }

  function reveal(info) {
    if (hidden()) return;
    closePicker();
    const insight = currentInsight();
    const text = window.MascotCharacters.quip(characterId, Object.assign({tone: prefs.tone}, insight));
    currentCue = Object.assign({}, insight, {text: text});
    showBubble(text);
    visiting = true;
    pinToken += 1;
    const docked = !info || info.touch || info.fromTap;
    if (docked) {
      host.classList.remove("bubble-flip", "bubble-below", "is-walking");
      host.classList.add("is-fixed");
      host.style.left = "";
      host.style.top = "";
      if (!reducedMotion()) setPose("pose-" + (character().pose || "bounce"));
      if (idleControl) idleControl.beginVisit(null);
      return;
    }
    const point = window.MascotIdle.anchorNear(
      info.x, info.y, host.offsetWidth || 112, host.offsetHeight || 140, window.innerWidth, window.innerHeight
    );
    moveTo(point.left, point.top, point);
    if (idleControl) idleControl.beginVisit({x: info.x, y: info.y});
  }

  function focusTarget(cue) {
    if (!cue) return;
    let el = null;
    if (cue.selector) {
      try { el = document.querySelector(cue.selector); }
      catch (error) { el = null; }
    }
    if (el) {
      el.scrollIntoView({behavior: reducedMotion() ? "auto" : "smooth", block: "center", inline: "nearest"});
      document.querySelectorAll(".mascot-spotlight").forEach(function (node) { node.classList.remove("mascot-spotlight"); });
      el.classList.add("mascot-spotlight");
      window.clearTimeout(spotlightTimer);
      spotlightTimer = window.setTimeout(function () { el.classList.remove("mascot-spotlight"); }, 2200);
      return;
    }
    const href = cue.href || "";
    if (href.startsWith("#")) {
      const tab = document.querySelector('[data-tab="' + href.slice(1) + '"]');
      if (tab) tab.click();
      return;
    }
    if (href) window.location.href = href;
  }

  function onBubbleClick() {
    const cue = currentCue;
    goHome();
    focusTarget(cue);
  }

  function onCharacterClick() {
    if (hidden()) return;
    if (!bubble.hidden && visiting && currentCue && currentCue.kind !== "event") return;
    reveal({touch: true, fromTap: true});
  }

  function say(cue) {
    if (!cue || hidden()) return;
    currentCue = {kind: "event", text: cue.text || "", selector: cue.selector || "", href: cue.href || ""};
    showBubble(currentCue.text);
    visiting = true;
    pinToken += 1;
    const touch = idleControl && idleControl.isTouch();
    if (!touch && cue.selector) {
      let el = null;
      try { el = document.querySelector(cue.selector); } catch (error) { el = null; }
      if (el) {
        const box = el.getBoundingClientRect();
        const point = window.MascotIdle.anchorNear(box.right, box.top, host.offsetWidth || 112, host.offsetHeight || 140, window.innerWidth, window.innerHeight);
        moveTo(point.left, point.top, point);
      }
    }
    if (idleControl) idleControl.beginVisit(null);
  }

  function cues() {
    const insight = currentInsight();
    if (!insight) return [];
    const text = window.MascotCharacters.quip(characterId, Object.assign({tone: prefs.tone}, insight), function () { return 0; });
    return [Object.assign({}, insight, {text: text})];
  }

  function startPoses() {
    window.clearInterval(poseTimer);
    if (reducedMotion()) return;
    poseTimer = window.setInterval(function () {
      if (host.classList.contains("is-walking") || hidden()) return;
      poseIndex = (poseIndex + 1) % POSES.length;
      setPose(POSES[poseIndex]);
    }, 4200);
  }

  function applyLook() {
    if (!host) return;
    host.classList.toggle("hanuman-left", prefs.side === "left");
    host.classList.toggle("hanuman-small", prefs.size === "small");
    host.classList.toggle("hanuman-large", prefs.size === "large");
    if (restore) restore.classList.toggle("hanuman-show-left", prefs.side === "left");
  }

  function usePrefs(next) {
    const incoming = next || {};
    if (typeof incoming.enabled === "boolean") prefs.enabled = incoming.enabled;
    if (incoming.idle_ms) prefs.idle_ms = Number(incoming.idle_ms) || prefs.idle_ms;
    if (incoming.tone) prefs.tone = incoming.tone;
    if (incoming.size) prefs.size = incoming.size;
    if (incoming.side) prefs.side = incoming.side === "left" ? "left" : "right";
    if (incoming.character && window.MascotCharacters && window.MascotCharacters.byId(incoming.character)) {
      prefs.character = incoming.character;
      characterId = incoming.character;
    }
    if (window.MascotIdle && window.MascotIdle.setMouseIdle) window.MascotIdle.setMouseIdle(prefs.idle_ms);
    if (!host) return;
    applyLook();
    renderCharacter();
    setHidden(!prefs.enabled);
    applyVisibility();
  }

  function start() {
    if (host) return;
    if (!window.MascotCharacters || !window.MascotIdle || !window.MascotInsights) return;
    if (window.MascotSettings && window.MascotSettings.readLocal) {
      const stored = window.MascotSettings.readLocal();
      if (stored) usePrefs(stored);
      else if (hidden()) prefs.enabled = false;
    } else if (hidden()) prefs.enabled = false;
    if (!prefs.enabled) setHidden(true);
    mount();
    applyLook();
    idleControl = window.MascotIdle.attach({
      onIdle: reveal,
      onMove: function () { if (visiting) goHome(); },
      center: function () {
        const rect = host.getBoundingClientRect();
        return {x: rect.left + rect.width / 2, y: rect.top + rect.height / 2};
      },
    });
    document.addEventListener("leadpilot:mascot", function (event) { say(event.detail || {}); });
    if (!hidden()) startPoses();
    else if (idleControl) idleControl.pause();
  }

  window.Hanuman = {
    start: start,
    say: say,
    cues: cues,
    STORAGE_KEY: STORAGE_KEY,
    setCharacter: selectCharacter,
    usePrefs: usePrefs,
    current: function () { return characterId; },
  };
  document.addEventListener("leadpilot:mascot-prefs", function (event) { usePrefs(event.detail || {}); });
  start();
})();
