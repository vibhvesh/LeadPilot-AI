/* Mahabharata cast. Cheeky about the pipeline. Respectful of the people they represent. */
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

  const bow = `<path d="M64 30c7 9 7 20 0 30" fill="none" stroke="#8a5a2b" stroke-width="2"/><path d="M64 30 L64 60" stroke="#c9a227" stroke-width="1"/>`;
  const cast = [
    {
      id: "krishna",
      name: "Krishna",
      group: "mahabharata",
      pose: "wink",
      blurb: "Flute, peacock feather, and a short truth",
      voice: voice("A small truth: ", ""),
      svg: function () {
        return person("#3d5a80", "#f0c14a", "krishna-flute", `<path class="krishna-feather" d="M48 20c6-10 10-8 8 2-4 2-8 2-8-2z" fill="#2f6f4e"/><rect x="58" y="48" width="12" height="3" rx="1.5" fill="#c9a227" transform="rotate(-20 64 49)"/>`);
      },
      lines: {
        "lead-top": ["Set the flute down. {company} ({score}) is the counsel for this hour."],
        "cockpit-caution": ["A small truth: {label}. Amber is a nudge, not a decoration."],
        generic: ["A small truth: the page already knows the next step."],
      },
    },
    {
      id: "arjuna",
      name: "Arjuna",
      group: "mahabharata",
      pose: "scratch",
      blurb: "One arrow, one target lead",
      voice: voice("", " Focus on the target lead."),
      svg: function () { return person("#e7b48a", "#f7f3ea", "arjuna-bow", bow); },
      lines: {
        "lead-top": ["Not the whole list. {company}. Score {score}. That is the target lead."],
        "followup-overdue": ["{count} overdue follow-up{s}. Pick one and loose the arrow."],
        generic: ["Focus on the target lead. The rest of the field can wait."],
      },
    },
    {
      id: "bhima",
      name: "Bhima",
      group: "mahabharata",
      pose: "bounce",
      blurb: "Mace, and a large appetite for open leads",
      voice: voice("", " The mace is already hungry."),
      svg: function () {
        return person("#c4865a", "#7a1f2b", "bhima-mace", `<rect x="60" y="40" width="5" height="20" rx="2" fill="#8a5a2b"/><circle cx="62" cy="38" r="6" fill="#c9a227"/>`);
      },
      lines: {
        "lead-top": ["I could eat this queue. Start with {company} ({score})."],
        "followup-open": ["{count} open follow-up{s}. A big appetite still needs a first bite."],
        generic: ["The mace is already hungry. Feed it a finished follow-up."],
      },
    },
    {
      id: "karna",
      name: "Karna",
      group: "mahabharata",
      pose: "bounce",
      blurb: "Gives the lead the courtesy of a reply",
      voice: voice("", " Generosity looks like a reply."),
      svg: function () {
        return person("#e7b48a", "#c9a227", "karna-armor", `<path d="M30 52 h20 v8 h-20z" fill="#f0c14a" opacity=".9"/><circle cx="28" cy="38" r="2" fill="#f0c14a"/><circle cx="52" cy="38" r="2" fill="#f0c14a"/>`);
      },
      lines: {
        "lead-top": ["Give {company} the courtesy of a reply. Score {score}, still new."],
        "overview-quiet": ["{count} lead{s} in the workspace. Kindness here is a clear next step."],
        generic: ["Generosity looks like a reply, not another speech."],
      },
    },
    {
      id: "draupadi",
      name: "Draupadi",
      group: "mahabharata",
      pose: "wink",
      blurb: "Will not let the hall postpone a decision",
      voice: voice("", " The hall is waiting."),
      svg: function () {
        return person("#e7b48a", "#7a1f2b", "draupadi-flame", `<path d="M64 58c4-6 8-4 4 2 4-6 8-2 2 6-6 2-10-2-6-8z" fill="#e07a2f"/>`);
      },
      lines: {
        "lead-top": ["The hall can debate later. {company} ({score}) needs an answer."],
        "followup-overdue": ["{count} follow-up{s} overdue. Postponing them is still a choice."],
        generic: ["The hall is waiting. Make the call that is already obvious."],
      },
    },
    {
      id: "bhishma",
      name: "Bhishma",
      group: "mahabharata",
      pose: "scratch",
      blurb: "Keeps the vow to finish the queue",
      voice: voice("The vow stands. ", ""),
      svg: function () { return person("#d7c4a3", "#f7f3ea", "bhishma-bow", bow); },
      lines: {
        "followup-overdue": ["A vow is simple: {count} overdue follow-up{s} get a call."],
        "lead-quiet": ["Nothing here is still a new lead. The vow moves to the next column."],
        generic: ["The vow stands. Do the thing you already said you would do."],
      },
    },
    {
      id: "shakuni",
      name: "Shakuni",
      group: "mahabharata",
      pose: "wink",
      blurb: "Dice in hand, still tells you to call",
      voice: voice("The dice say: ", ""),
      svg: function () {
        return person("#e7b48a", "#3d2a4a", "shakuni-dice", `<rect x="58" y="52" width="10" height="10" rx="2" fill="#f7f3ea"/><circle cx="61" cy="55" r="1" fill="#2b2118"/><circle cx="65" cy="59" r="1" fill="#2b2118"/>`);
      },
      lines: {
        "lead-top": ["The dice like {company} ({score}). I would still pick up the phone."],
        "cockpit-caution": ["The dice say: {label}. Odds are better if you look."],
        generic: ["The dice say: luck is not a follow-up system."],
      },
    },
    {
      id: "ghatotkacha",
      name: "Ghatotkacha",
      group: "mahabharata",
      pose: "bounce",
      blurb: "Giant, playful, hard to ignore",
      voice: voice("Boo, kindly. ", ""),
      svg: function () {
        return svg(`<g class="mascot-body ghatotkacha-club">
          <ellipse cx="40" cy="84" rx="18" ry="3" fill="#e6d3b3"/>
          <path d="M22 48 h36 v24 h-36 z" fill="#2f6f4e"/>
          <circle cx="40" cy="34" r="16" fill="#6b8f71"/>
          <g class="mascot-eye"><circle cx="33" cy="34" r="2" fill="#2b2118"/></g>
          <g class="mascot-eye mascot-eye-right"><circle cx="47" cy="34" r="2" fill="#2b2118"/></g>
          <rect x="60" y="28" width="6" height="22" rx="2" fill="#8a5a2b"/>
          <circle cx="63" cy="26" r="7" fill="#c9a227"/>
        </g>`);
      },
      lines: {
        "followup-overdue": ["I am large and the queue is larger. {count} follow-up{s} are overdue."],
        "lead-top": ["Boo, kindly. {company} scored {score} and is still a new lead."],
        generic: ["Boo, kindly. The page will not finish itself."],
      },
    },
  ];

  root.MascotCast = (root.MascotCast || []).concat(cast);
  if (typeof module !== "undefined" && module.exports) module.exports = cast;
})(typeof globalThis !== "undefined" ? globalThis : this);
