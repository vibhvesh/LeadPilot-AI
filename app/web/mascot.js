/* A small cartoon Hanuman. He hops toward new leads, the busiest column, an open summary, or pending requests. */
(function () {
  const STORAGE_KEY = "leadpilot-hanuman";
  let host = null;
  let restore = null;
  let destination = null;
  let timer = 0;

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

  function svg() {
    return `<svg class="hanuman-svg" viewBox="0 0 80 88" aria-hidden="true">
      <path class="hanuman-tail" d="M16 60c-16 4-16 18-4 18 10 0 12-8 8-12" fill="none" stroke="#e07a2f" stroke-width="4" stroke-linecap="round"/>
      <g class="hanuman-body">
        <ellipse cx="40" cy="64" rx="15" ry="13" fill="#ef8a3a"/>
        <g class="hanuman-gada" transform="translate(58,34) rotate(28)">
          <rect x="-1.6" y="5" width="3.2" height="14" rx="1" fill="#c8960e"/>
          <circle cx="0" cy="3" r="5.5" fill="#f0c14a"/>
        </g>
        <circle cx="40" cy="42" r="18" fill="#ef8a3a"/>
        <ellipse cx="40" cy="48" rx="10" ry="8" fill="#f6d2b0"/>
        <circle cx="33" cy="40" r="2.1" fill="#2b2118"/>
        <circle cx="47" cy="40" r="2.1" fill="#2b2118"/>
        <circle cx="33.7" cy="39.3" r=".7" fill="#fff"/>
        <circle cx="47.7" cy="39.3" r=".7" fill="#fff"/>
        <path d="M34 47q6 5 12 0" fill="none" stroke="#8a4b2a" stroke-width="1.2" stroke-linecap="round"/>
        <path class="hanuman-tilak" d="M40 31v5" stroke="#c0392b" stroke-width="2" stroke-linecap="round"/>
        <path class="hanuman-crown" d="M27 30l6-13 7 8 8-10 6 15z" fill="#f0c14a" stroke="#c8960e" stroke-width=".6"/>
      </g>
    </svg>`;
  }

  function mount() {
    host = document.createElement("div");
    host.id = "hanuman";
    host.className = "hanuman is-fixed";
    host.innerHTML = `<button type="button" class="hanuman-bubble" hidden></button>
      <button type="button" class="hanuman-hit" aria-label="Little Hanuman">${svg()}</button>
      <button type="button" class="hanuman-hide">Hide</button>`;
    restore = document.createElement("button");
    restore.type = "button";
    restore.className = "hanuman-show";
    restore.textContent = "Show Hanuman";
    restore.hidden = true;
    document.body.appendChild(host);
    document.body.appendChild(restore);
    host.querySelector(".hanuman-hit").addEventListener("click", go);
    host.querySelector(".hanuman-bubble").addEventListener("click", go);
    host.querySelector(".hanuman-hide").addEventListener("click", () => {
      setHidden(true);
      applyVisibility();
    });
    restore.addEventListener("click", () => {
      setHidden(false);
      applyVisibility();
    });
    applyVisibility();
  }

  function applyVisibility() {
    const off = hidden();
    host.hidden = off;
    restore.hidden = !off;
  }

  function go() {
    if (!destination) return;
    const href = destination.href || "";
    if (href.startsWith("#") && typeof show === "function") {
      show(href.slice(1));
      return;
    }
    if (href) location.href = href;
  }

  function place(selector) {
    const target = selector ? document.querySelector(selector) : null;
    host.classList.remove("is-fixed");
    if (!target) {
      host.classList.add("is-fixed");
      host.style.left = "";
      host.style.top = "";
      return;
    }
    const box = target.getBoundingClientRect();
    const width = host.offsetWidth || 72;
    const height = host.offsetHeight || 80;
    const x = Math.min(window.innerWidth - width - 8, Math.max(8, box.left + box.width - width));
    let y = box.top - height - 6;
    if (y < 8) y = Math.min(window.innerHeight - height - 8, box.bottom + 6);
    if (!reducedMotion()) host.classList.add("is-hopping");
    host.style.left = x + "px";
    host.style.top = y + "px";
  }

  function say(cue) {
    if (!cue || hidden()) return;
    destination = cue;
    const bubble = host.querySelector(".hanuman-bubble");
    bubble.hidden = !cue.text;
    bubble.textContent = cue.text || "";
    place(cue.selector);
  }

  function cues() {
    const found = [];
    const preview = document.getElementById("lead-preview");
    if (preview && !preview.hidden) {
      const full = document.getElementById("preview-full");
      found.push({text: "Here's the summary!", selector: "#lead-preview .preview-panel", href: full ? full.getAttribute("href") : "/leads"});
    }
    const badge = document.getElementById("pending-badge");
    if (badge && !badge.hidden && Number(badge.textContent) > 0) {
      const count = Number(badge.textContent);
      found.push({text: count + " waiting for access!", selector: "[data-tab=users]", href: "#users"});
    }
    const column = document.querySelector('#pipeline-board [data-status="New"] h3 span');
    const count = column ? Number(column.textContent) || 0 : 0;
    if (count > 0) {
      found.push({
        text: count + " new lead" + (count === 1 ? "" : "s") + "!",
        selector: '#pipeline-board [data-status="New"]',
        href: "/leads?status=New",
      });
    }
    return found;
  }

  function visitNext() {
    const list = cues();
    if (!list.length || hidden()) return;
    const index = (visitNext.n || 0) % list.length;
    visitNext.n = index + 1;
    say(list[index]);
  }

  function start() {
    if (host) return;
    mount();
    document.addEventListener("leadpilot:mascot", (event) => say(event.detail || {}));
    timer = window.setInterval(visitNext, 20000);
    window.setTimeout(visitNext, 1200);
  }

  window.Hanuman = {start, say, cues, STORAGE_KEY};
})();
