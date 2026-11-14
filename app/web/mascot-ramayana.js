/* Ramayana cast. The jokes are about leads and follow-ups, never about the tradition. */
(function (root) {
  function svg(body) {
    return `<svg class="mascot-svg hanuman-svg" viewBox="0 0 80 88" aria-hidden="true">${body}</svg>`;
  }

  function person(skin, cloth, propClass, prop) {
    return svg(`<g class="mascot-body">
      <ellipse cx="40" cy="82" rx="14" ry="3" fill="#e6d3b3"/>
      <path d="M28 50 h24 v20 h-24 z" fill="${cloth}"/>
      <circle cx="40" cy="36" r="12" fill="${skin}"/>
      <g class="mascot-eye"><circle cx="35" cy="37" r="1.7" fill="#2b2118"/></g>
      <g class="mascot-eye mascot-eye-right"><circle cx="45" cy="37" r="1.7" fill="#2b2118"/></g>
      <g class="${propClass}">${prop}</g>
    </g>`);
  }

  function voice(prefix, suffix) {
    return function (line) {
      const text = String(line || "");
      if (prefix && text.indexOf(prefix) === 0) return text;
      if (suffix && text.indexOf(suffix) !== -1) return text;
      if (prefix) return prefix + text;
      return text + suffix;
    };
  }

  const bow = `<path d="M62 28c8 10 8 24 0 34" fill="none" stroke="#8a5a2b" stroke-width="2"/><path d="M62 28 L62 62" stroke="#c9a227" stroke-width="1"/>`;
  const cast = [
    {
      id: "rama",
      name: "Rama",
      group: "ramayana",
      pose: "bounce",
      blurb: "Bow kept for the one lead that matters",
      voice: voice("", " The bow stays patient."),
      svg: function () { return person("#e7b48a", "#c4554a", "rama-bow", bow); },
      lines: {
        "lead-top": ["{company} scored {score}. That is the lead the bow is pointing at."],
        "followup-overdue": ["{count} follow-up{s} overdue. A steady aim beats another promise."],
        generic: ["The useful lead is the one still waiting for a person."],
      },
    },
    {
      id: "lakshmana",
      name: "Lakshmana",
      group: "ramayana",
      pose: "scratch",
      blurb: "Keeps watch on the side of the pipeline",
      voice: voice("On watch. ", ""),
      svg: function () { return person("#e7b48a", "#2f6f4e", "lakshmana-bow", bow + `<path d="M68 40 h6" stroke="#8a5a2b" stroke-width="2"/>`); },
      lines: {
        "lead-top": ["I have the flank. You still need to greet {company} ({score})."],
        "followup-overdue": ["{count} follow-up{s} slipped past the watch. They are overdue."],
        generic: ["On watch. The page has one clear next step."],
      },
    },
    {
      id: "sita",
      name: "Sita",
      group: "ramayana",
      pose: "wink",
      blurb: "Lotus in hand, standards intact",
      voice: voice("", " A lotus is not a follow-up."),
      svg: function () {
        return person("#e7b48a", "#f0c14a", "sita-lotus", `<circle cx="64" cy="58" r="5" fill="#f4a7b9"/><circle cx="64" cy="58" r="2" fill="#f0c14a"/>`);
      },
      lines: {
        "lead-top": ["{company} scored {score} and is still a new lead. Grace includes a reply."],
        "overview-quiet": ["The workspace is calm. {count} lead{s} are still yours to tend."],
        generic: ["Hold the standard. Then do the one useful thing on the page."],
      },
    },
    {
      id: "jambavan",
      name: "Jambavan",
      group: "ramayana",
      pose: "bounce",
      blurb: "Bear with a club and a long memory",
      voice: voice("Old bear says: ", ""),
      svg: function () {
        return person("#8a5a3b", "#6b412c", "jambavan-club", `<ellipse cx="22" cy="30" rx="4" ry="3" fill="#6b412c"/><ellipse cx="58" cy="30" rx="4" ry="3" fill="#6b412c"/><rect x="60" y="46" width="4" height="18" rx="2" fill="#c9a227"/>`);
      },
      lines: {
        "lead-top": ["I have seen longer roads. {company} ({score}) is still the next step."],
        "followup-overdue": ["{count} follow-up{s} are overdue. Even a patient bear taps the club."],
        generic: ["Old bear says: pick up the lead that is already in front of you."],
      },
    },
    {
      id: "jatayu",
      name: "Jatayu",
      group: "ramayana",
      pose: "wink",
      blurb: "Eagle who spots the stalled lead",
      voice: voice("From up here: ", ""),
      svg: function () {
        return svg(`<g class="mascot-body">
          <ellipse cx="40" cy="48" rx="14" ry="10" fill="#8d6a43"/>
          <circle cx="40" cy="32" r="8" fill="#c9a227"/>
          <g class="mascot-eye"><circle cx="37" cy="32" r="1.4" fill="#2b2118"/></g>
          <g class="mascot-eye mascot-eye-right"><circle cx="43" cy="32" r="1.4" fill="#2b2118"/></g>
          <path class="jatayu-wing" d="M26 48c-16 2-20 14-8 16 8 1 12-6 12-12z M54 48c16 2 20 14 8 16-8 1-12-6-12-12z" fill="#6b412c"/>
        </g>`);
      },
      lines: {
        "lead-top": ["I circled the list. {company} ({score}) is the one still waiting."],
        "followup-overdue": ["{count} follow-up{s} overdue. I can see them from here."],
        generic: ["From up here: one row on this page needs a person."],
      },
    },
    {
      id: "sugriva",
      name: "Sugriva",
      group: "ramayana",
      pose: "bounce",
      blurb: "Calls the troop, then the lead",
      voice: voice("", " The troop is waiting on you."),
      svg: function () {
        return person("#e07a2f", "#2f6f4e", "sugriva-crown", `<path d="M30 26 l4-8 6 6 6-8 4 10z" fill="#f0c14a"/>`);
      },
      lines: {
        "lead-top": ["The troop is assembled. {company} still has not been greeted ({score})."],
        "followup-open": ["{count} open follow-up{s}. Rally them before they go quiet."],
        generic: ["Gather the next step. Then actually take it."],
      },
    },
    {
      id: "vibhishana",
      name: "Vibhishana",
      group: "ramayana",
      pose: "scratch",
      blurb: "Says the awkward true thing",
      voice: voice("Plainly: ", ""),
      svg: function () {
        return person("#e7b48a", "#3d5a80", "vibhishana-banner", `<path d="M60 30 v24" stroke="#3d5a80" stroke-width="2"/><path d="M60 30 h12 l-3 5 3 5 h-12z" fill="#f0c14a"/>`);
      },
      lines: {
        "lead-top": ["Plainly: {company} scored {score} and nobody has called."],
        "cockpit-alert": ["Plainly: {label}. The warning light is telling the truth."],
        generic: ["Plainly: the useful bit is already on the page."],
      },
    },
    {
      id: "ravana",
      name: "Ravana",
      group: "ramayana",
      pose: "scratch",
      blurb: "Ten heads, all cross about missed follow-ups",
      voice: voice("Hmph. ", ""),
      svg: function () {
        const heads = [18, 28, 38, 48, 58, 23, 33, 43, 53, 63].map(function (x, index) {
          const y = index < 5 ? 16 : 22;
          return `<circle cx="${x}" cy="${y}" r="3.2" fill="#c4554a"/>`;
        }).join("");
        return person("#e7b48a", "#7a1f2b", "ravana-heads", heads + `<path d="M33 34 h5 M42 34 h5" stroke="#2b2118" stroke-width="1"/>`);
      },
      lines: {
        "followup-overdue": ["Ten heads, and every one of them noticed {count} overdue follow-up{s}."],
        "lead-top": ["Hmph. {company} scored {score} and is still sitting there, uncontacted."],
        "cockpit-alert": ["Hmph. {label}. I do not enjoy being right about a red light."],
        generic: ["Hmph. The work is still the work."],
      },
    },
  ];

  root.MascotCast = (root.MascotCast || []).concat(cast);
  if (typeof module !== "undefined" && module.exports) module.exports = cast;
})(typeof globalThis !== "undefined" ? globalThis : this);
