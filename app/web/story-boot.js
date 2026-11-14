/* Arms the story overlay after two minutes of idle. The mascot crew keeps its own timer. */
(function (root) {
  const IDLE_MS = 120000;
  const STORY_V = "cut5";
  const FILES = ["ramayana-cast.js", "ramayana-scenes.js", "ramayana-story.js", "story-overlay.js"];
  let generation = 0;
  let timer = 0;
  let playing = null;
  let overlay = null;
  let enabled = false;
  let installed = false;
  let suppressUntil = 0;

  function always() {
    return document.body && document.body.dataset.storyAlways === "1";
  }

  async function refreshEnabled() {
    try {
      const res = await fetch("/api/story/overlay", { credentials: "same-origin" });
      if (!res.ok) { enabled = false; return; }
      const data = await res.json();
      enabled = data.enabled === true;
    } catch (error) {
      enabled = false;
    }
  }

  function arm() {
    window.clearTimeout(timer);
    timer = window.setTimeout(begin, IDLE_MS);
  }

  function clearPlay() {
    if (playing) { playing.stop(); playing = null; }
    if (overlay) { overlay.dismiss(); overlay = null; }
  }

  function onInput() {
    if (Date.now() < suppressUntil) return;
    generation += 1;
    clearPlay();
    arm();
  }

  async function ensureScripts() {
    if (!document.querySelector("link[data-story-css]")) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "/static/ramayana-story.css?v=" + STORY_V;
      link.dataset.storyCss = "1";
      document.head.appendChild(link);
    }
    for (let i = 0; i < FILES.length; i += 1) {
      const file = FILES[i];
      if (document.querySelector('script[data-story="' + file + '"]')) continue;
      await new Promise(function (resolve, reject) {
        const script = document.createElement("script");
        script.src = "/static/" + file + "?v=" + STORY_V;
        script.dataset.story = file;
        script.onload = resolve;
        script.onerror = reject;
        document.body.appendChild(script);
      });
    }
  }

  async function begin() {
    if (playing || overlay) return;
    const token = generation;
    suppressUntil = Date.now() + 500;
    if (!always()) {
      await refreshEnabled();
      if (token !== generation || !enabled) return;
    }
    if (document.hidden) return;
    await ensureScripts();
    if (token !== generation) return;
    let lines = {};
    try {
      const res = await fetch("/api/story/lines", { credentials: "same-origin" });
      if (res.ok) lines = (await res.json()).lines || {};
    } catch (error) { /* defaults */ }
    if (token !== generation) return;
    overlay = root.StoryOverlay.capture(document);
    if (token !== generation) {
      overlay.dismiss();
      overlay = null;
      return;
    }
    playing = root.RamayanaStory.start(overlay.stage(), { lines: lines, overlay: overlay });
  }

  function install() {
    if (installed || typeof document === "undefined") return;
    installed = true;
    document.addEventListener("pointerdown", onInput, true);
    document.addEventListener("pointermove", onInput, true);
    document.addEventListener("keydown", onInput, true);
    document.addEventListener("wheel", onInput, { capture: true, passive: true });
    document.addEventListener("touchstart", onInput, { capture: true, passive: true });
    window.addEventListener("scroll", onInput, true);
    document.addEventListener("visibilitychange", function () {
      generation += 1;
      clearPlay();
      arm();
    });
    arm();
  }

  const api = { IDLE_MS: IDLE_MS, STORY_V: STORY_V, install: install, startNow: begin };
  root.StoryBoot = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  install();
})(typeof globalThis !== "undefined" ? globalThis : this);
