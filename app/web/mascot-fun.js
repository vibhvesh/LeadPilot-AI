/* Fun cast. Original cartoons. No real person, photo, or likeness. */
(function (root) {
  function svg(body) {
    return `<svg class="mascot-svg rocket-boss-svg" viewBox="0 0 80 112" aria-hidden="true">${body}</svg>`;
  }

  const rocketBoss = {
    id: "rocket-boss",
    name: "Rocket Boss",
    group: "fun",
    pose: "bounce",
    idleMs: 10000,
    blurb: "Original cartoon in a black shirt, with a toy rocket and a Mars badge",
    voice: function (line) {
      const text = String(line || "");
      if (/shipping it|Mars|rocket/i.test(text)) return text;
      return text + " Shipping it.";
    },
    svg: function () {
      return svg(`
        <g class="rocket-ship" transform="translate(58,18)">
          <path d="M8 22 L8 8 L14 2 L20 8 L20 22 Z" fill="#d8dee8" stroke="#8aa0b8" stroke-width="1"/>
          <path d="M8 22 L4 28 L10 24 M20 22 L24 28 L18 24" fill="#e25b4a"/>
          <circle cx="14" cy="12" r="2" fill="#7ec8ff"/>
        </g>
        <g class="rocket-boss-body mascot-body">
          <g class="mascot-leg mascot-leg-left"><path d="M30 78 v18" stroke="#243044" stroke-width="5" stroke-linecap="round"/><ellipse cx="28" cy="98" rx="6" ry="3" fill="#1b2430"/></g>
          <g class="mascot-leg mascot-leg-right"><path d="M50 78 v18" stroke="#243044" stroke-width="5" stroke-linecap="round"/><ellipse cx="52" cy="98" rx="6" ry="3" fill="#1b2430"/></g>
          <path class="rocket-shirt" d="M24 50 h32 v28 h-32 z" fill="#161616"/>
          <circle class="rocket-badge" cx="46" cy="62" r="5" fill="#c4554a" stroke="#f0c14a" stroke-width="1"/>
          <path d="M44 62 h4 M46 60 v4" stroke="#fff" stroke-width=".8"/>
          <circle cx="40" cy="34" r="14" fill="#f0c9a0"/>
          <path d="M28 30c2-10 22-10 24 0" fill="#2b2118"/>
          <g class="mascot-eye"><circle cx="35" cy="35" r="1.6" fill="#2b2118"/></g>
          <g class="mascot-eye mascot-eye-right"><circle cx="45" cy="35" r="1.6" fill="#2b2118"/></g>
          <path class="rocket-smile" d="M36 42 q4 3 8 0" fill="none" stroke="#8a5a3a" stroke-width="1.2" stroke-linecap="round"/>
          <g class="rocket-mug">
            <rect x="8" y="58" width="10" height="12" rx="2" fill="#f4e1a8" stroke="#c9a227"/>
            <path d="M18 61 h3 a3 3 0 0 1 0 6 h-3" fill="none" stroke="#c9a227" stroke-width="1.4"/>
            <path d="M10 56 q2-3 4 0 q2-3 4 0" fill="none" stroke="#fff" stroke-width="1"/>
          </g>
          <g class="rocket-cigar">
            <rect x="48" y="42" width="14" height="3" rx="1" fill="#6b3e26" transform="rotate(18 48 42)"/>
            <circle cx="62" cy="46" r="1.4" fill="#e25b4a"/>
          </g>
          <g class="rocket-smoke">
            <circle class="rocket-puff" cx="66" cy="40" r="2" fill="#d5dce7"/>
            <circle class="rocket-puff rocket-puff-2" cx="70" cy="34" r="2.6" fill="#e6ebf2"/>
            <circle class="rocket-puff rocket-puff-3" cx="66" cy="28" r="3" fill="#f4f7fb"/>
          </g>
        </g>`);
    },
    lines: {
      "lead-top": ["{company} scored {score}. That lead is the payload. Shipping it."],
      "lead-new": ["{company} just landed and is still a new lead. Mars can wait."],
      "followup-overdue": ["{count} follow-up{s} overdue. A rocket does not launch on a late checklist."],
      "followup-open": ["{count} open follow-up{s}. Still on the pad. Shipping it means calling them."],
      "overview-quiet": ["{count} lead{s} on the pad. Quiet is not the same as orbit."],
      "cockpit-alert": ["{label}. I would not launch through a red light."],
      "social-reply": ["{count} post{s} waiting. Copy the reply. I do not auto-post. Shipping it is still your hand."],
      "pulse-urgent": ["{count} urgent card{s}. Read the red one before the next launch window."],
      generic: ["The insight is the flight plan. Shipping it beats another speech."],
    },
  };

  const narad = {
    id: "narad",
    name: "Narad",
    group: "ramayana",
    pose: "bounce",
    blurb: "Narada Muni with a veena and a topknot",
    voice: function (line) {
      const text = String(line || "");
      if (text.indexOf("Narayan Narayan") === 0) return text;
      return "Narayan Narayan. " + text;
    },
    svg: function () { return "<svg></svg>"; },
    lines: {
      "lead-top": ["Narayan Narayan. {company} scored {score}. The veena noticed before the inbox did."],
      "followup-overdue": ["Narayan Narayan. {count} follow-up{s} overdue. Even a wandering sage keeps a date."],
      generic: ["Narayan Narayan. The page is trying to tell you something."],
    },
  };

  root.MascotCast = (root.MascotCast || []).concat([rocketBoss, narad]);
})(typeof globalThis !== "undefined" ? globalThis : this);
