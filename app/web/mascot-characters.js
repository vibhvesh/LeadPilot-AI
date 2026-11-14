/* Cartoon cast for the corner mascot. Lines roast the pipeline, never a person. */
(function (root) {
  const STORAGE_KEY = "leadpilot-mascot-character";

  function svgWrap(body) {
    return `<svg class="mascot-svg hanuman-svg" viewBox="0 0 80 88" aria-hidden="true">${body}</svg>`;
  }

  function hanumanSvg() {
    return svgWrap(`
      <path class="hanuman-tail mascot-tail" d="M16 60c-16 4-16 18-4 18 10 0 12-8 8-12" fill="none" stroke="#e07a2f" stroke-width="4" stroke-linecap="round"/>
      <g class="hanuman-body mascot-body">
        <ellipse cx="40" cy="64" rx="15" ry="13" fill="#ef8a3a"/>
        <g class="mascot-leg mascot-leg-left"><ellipse cx="32" cy="76" rx="5" ry="2.4" fill="#d86e28"/></g>
        <g class="mascot-leg mascot-leg-right"><ellipse cx="48" cy="76" rx="5" ry="2.4" fill="#d86e28"/></g>
        <g class="hanuman-gada" transform="translate(58,34) rotate(28)">
          <rect x="-1.6" y="5" width="3.2" height="14" rx="1" fill="#c8960e"/>
          <circle cx="0" cy="3" r="5.5" fill="#f0c14a"/>
        </g>
        <circle cx="40" cy="42" r="18" fill="#ef8a3a"/>
        <ellipse cx="40" cy="48" rx="10" ry="8" fill="#f6d2b0"/>
        <g class="mascot-eye"><circle cx="33" cy="40" r="2.1" fill="#2b2118"/><circle cx="33.7" cy="39.3" r=".7" fill="#fff"/></g>
        <g class="mascot-eye mascot-eye-right"><circle cx="47" cy="40" r="2.1" fill="#2b2118"/><circle cx="47.7" cy="39.3" r=".7" fill="#fff"/></g>
        <path d="M34 47q6 5 12 0" fill="none" stroke="#8a4b2a" stroke-width="1.2" stroke-linecap="round"/>
        <path class="hanuman-tilak" d="M40 31v5" stroke="#c0392b" stroke-width="2" stroke-linecap="round"/>
        <path class="hanuman-crown" d="M27 30l6-13 7 8 8-10 6 15z" fill="#f0c14a" stroke="#c8960e" stroke-width=".6"/>
        <g class="mascot-paw"><ellipse cx="22" cy="50" rx="6.5" ry="3.6" fill="#ef8a3a"/></g>
      </g>`);
  }

  function mangoSvg() {
    return svgWrap(`
      <path class="mascot-tail" d="M18 58c-14 8-16 20-6 22 8 1 12-8 10-14" fill="none" stroke="#1f8a5b" stroke-width="4" stroke-linecap="round"/>
      <g class="mascot-body">
        <ellipse cx="42" cy="64" rx="14" ry="12" fill="#2f9e6b"/>
        <ellipse cx="30" cy="62" rx="11" ry="7" fill="#187a50" transform="rotate(-18 30 62)"/>
        <g class="mascot-leg mascot-leg-left"><path d="M34 74 l-4 6 M34 74 l0 7 M34 74 l4 6" stroke="#e07a2f" stroke-width="1.6" fill="none" stroke-linecap="round"/></g>
        <g class="mascot-leg mascot-leg-right"><path d="M50 74 l-4 6 M50 74 l0 7 M50 74 l4 6" stroke="#e07a2f" stroke-width="1.6" fill="none" stroke-linecap="round"/></g>
        <circle cx="46" cy="40" r="16" fill="#2f9e6b"/>
        <path d="M36 30c2-10 8-12 10-4 2-10 8-8 8 0-4 2-8 2-18 4z" fill="#e15b4a"/>
        <ellipse cx="50" cy="44" rx="8" ry="7" fill="#f6e27a"/>
        <path d="M56 42 l12 3 l-12 5z" fill="#f0a030"/>
        <g class="mascot-eye"><circle cx="42" cy="38" r="2.2" fill="#2b2118"/><circle cx="42.7" cy="37.3" r=".7" fill="#fff"/></g>
        <g class="mascot-eye mascot-eye-right"><circle cx="50" cy="37" r="2.2" fill="#2b2118"/><circle cx="50.7" cy="36.3" r=".7" fill="#fff"/></g>
        <g class="mascot-paw"><ellipse cx="30" cy="48" rx="6" ry="3.4" fill="#187a50" transform="rotate(-30 30 48)"/></g>
      </g>`);
  }

  function noodleSvg() {
    return svgWrap(`
      <ellipse class="mascot-tail" cx="16" cy="70" rx="10" ry="5" fill="#6b412c"/>
      <g class="mascot-body">
        <ellipse cx="40" cy="66" rx="16" ry="13" fill="#8a5a3a"/>
        <ellipse cx="40" cy="68" rx="9" ry="8" fill="#f3ddc4"/>
        <g class="mascot-leg mascot-leg-left"><ellipse cx="30" cy="78" rx="5" ry="3" fill="#6b412c"/></g>
        <g class="mascot-leg mascot-leg-right"><ellipse cx="50" cy="78" rx="5" ry="3" fill="#6b412c"/></g>
        <circle cx="42" cy="40" r="17" fill="#8a5a3a"/>
        <circle cx="28" cy="30" r="5" fill="#8a5a3a"/><circle cx="28" cy="30" r="2.4" fill="#f3ddc4"/>
        <circle cx="54" cy="28" r="5" fill="#8a5a3a"/><circle cx="54" cy="28" r="2.4" fill="#f3ddc4"/>
        <ellipse cx="44" cy="46" rx="9" ry="7" fill="#f3ddc4"/>
        <g class="mascot-eye"><circle cx="36" cy="40" r="2.1" fill="#2b2118"/><circle cx="36.6" cy="39.4" r=".6" fill="#fff"/></g>
        <g class="mascot-eye mascot-eye-right"><circle cx="48" cy="39" r="2.1" fill="#2b2118"/><circle cx="48.6" cy="38.4" r=".6" fill="#fff"/></g>
        <ellipse cx="42" cy="46" rx="2" ry="1.4" fill="#5c3b32"/>
        <path d="M32 49h-6M54 48h6M33 52h-5M53 51h5" stroke="#5c3b32" stroke-width=".7" stroke-linecap="round"/>
        <g class="mascot-paw">
          <rect x="54" y="50" width="12" height="16" rx="2" fill="#f7f1e4" stroke="#c8960e" stroke-width=".6"/>
          <path d="M57 55h6M57 58h6M57 61h4" stroke="#8a94a6" stroke-width=".7"/>
        </g>
      </g>`);
  }

  function pickleSvg() {
    return svgWrap(`
      <path class="mascot-tail" d="M14 62c-10 2-12 14-2 16 9 2 14-6 12-12" fill="#e07a2f" stroke="#c45e1a" stroke-width="1"/>
      <g class="mascot-body">
        <ellipse cx="42" cy="66" rx="14" ry="12" fill="#e07a2f"/>
        <ellipse cx="42" cy="70" rx="8" ry="7" fill="#fff7ea"/>
        <g class="mascot-leg mascot-leg-left"><path d="M32 76h8" stroke="#c45e1a" stroke-width="2.4" stroke-linecap="round"/></g>
        <g class="mascot-leg mascot-leg-right"><path d="M46 76h8" stroke="#c45e1a" stroke-width="2.4" stroke-linecap="round"/></g>
        <circle cx="44" cy="40" r="15" fill="#e07a2f"/>
        <path d="M30 32 L26 16 L38 28Z" fill="#e07a2f"/>
        <path d="M54 30 L64 14 L58 32Z" fill="#e07a2f"/>
        <path d="M31 30 L29 20 L36 28Z" fill="#f6d2b0"/>
        <path d="M55 29 L60 18 L57 31Z" fill="#f6d2b0"/>
        <ellipse cx="44" cy="46" rx="8" ry="6" fill="#fff7ea"/>
        <g class="mascot-eye"><circle cx="38" cy="40" r="2" fill="#2b2118"/><circle cx="38.6" cy="39.4" r=".6" fill="#fff"/></g>
        <g class="mascot-eye mascot-eye-right"><circle cx="50" cy="39" r="2" fill="#2b2118"/><circle cx="50.6" cy="38.4" r=".6" fill="#fff"/></g>
        <ellipse cx="44" cy="47" rx="1.7" ry="1.2" fill="#2b2118"/>
        <path d="M44 54 l-4 8 4 3 4-3z" fill="#14213d"/>
        <g class="mascot-paw"><ellipse cx="28" cy="54" rx="6" ry="3.5" fill="#e07a2f"/></g>
      </g>`);
  }

  function biscuitSvg() {
    return svgWrap(`
      <g class="mascot-body">
        <ellipse cx="40" cy="64" rx="16" ry="15" fill="#1f2a37"/>
        <ellipse cx="40" cy="68" rx="10" ry="11" fill="#f4f7fb"/>
        <g class="mascot-leg mascot-leg-left"><ellipse cx="32" cy="80" rx="6" ry="3" fill="#f0a05a"/></g>
        <g class="mascot-leg mascot-leg-right"><ellipse cx="48" cy="80" rx="6" ry="3" fill="#f0a05a"/></g>
        <circle cx="40" cy="38" r="16" fill="#1f2a37"/>
        <ellipse cx="40" cy="44" rx="9" ry="8" fill="#f4f7fb"/>
        <path d="M26 50h28c-2 6-8 8-14 8s-12-2-14-8z" fill="#2563eb"/>
        <path d="M48 54v12" stroke="#2563eb" stroke-width="4" stroke-linecap="round"/>
        <g class="mascot-eye"><circle cx="34" cy="38" r="2.2" fill="#2b2118"/><circle cx="34.7" cy="37.3" r=".7" fill="#fff"/></g>
        <g class="mascot-eye mascot-eye-right"><circle cx="46" cy="38" r="2.2" fill="#2b2118"/><circle cx="46.7" cy="37.3" r=".7" fill="#fff"/></g>
        <path d="M36 46 l4 3 4-3" fill="#f0a05a"/>
        <g class="mascot-paw"><ellipse cx="22" cy="58" rx="7" ry="3.2" fill="#1f2a37" transform="rotate(-16 22 58)"/></g>
      </g>`);
  }

  const CLASSIC = [
    {id: "hanuman", name: "Hanuman", group: "classic", pose: "bounce", blurb: "Orange monkey with a crown and mace", svg: hanumanSvg},
    {id: "mango", name: "Mango", group: "classic", pose: "wink", blurb: "Parrot who repeats the awkward number", svg: mangoSvg},
    {id: "noodle", name: "Noodle", group: "classic", pose: "scratch", blurb: "Otter with a clipboard", svg: noodleSvg},
    {id: "pickle", name: "Pickle", group: "classic", pose: "wink", blurb: "Fox in a tiny tie", svg: pickleSvg},
    {id: "biscuit", name: "Biscuit", group: "classic", pose: "bounce", blurb: "Penguin who files the cold leads", svg: biscuitSvg},
  ];
  const CHARACTERS = CLASSIC.concat(root.MascotCast || []);

  /* Fully voiced lines for the pages people actually live on. */
  const VOICED = {
    "lead-top": {
      hanuman: [
        "{company} scored {score} and is still a new lead. The mace is tapping its foot.",
        "Top new lead on this page: {company} ({score}). A crown does not send the email.",
      ],
      mango: [
        "{company}, score {score}, still a new lead. SQUAWK. I can say it again.",
        "Pretty number on {company} ({score}). Zero hellos. Even a parrot sees the next step.",
      ],
      noodle: [
        "Clipboard: {company}, {score}, still a new lead. I brought snacks, not a sales team.",
        "{company} is floating at {score} and still a new lead. The shell-phone works.",
      ],
      pickle: [
        "{company} at {score}, still a new lead. I would send the note, but I am busy looking clever.",
        "Hottest new lead here is {company} ({score}). Silence is a bold negotiation tactic.",
      ],
      biscuit: [
        "Formal notice: {company} ({score}) is still a new lead. I waddled over.",
        "{company} scored {score} and is still on the ice. Unwaved-at. Still a new lead.",
      ],
    },
    "lead-new": {
      hanuman: ["{company} is the newest new lead, and nobody has said hello. The quest log noticed."],
      mango: ["{company} is the newest new lead. SQUAWK. Fresh, and already lonely."],
      noodle: ["Clipboard says {company} is the newest new lead. I underlined it. Twice."],
      pickle: ["{company} just arrived and is still a new lead. The tiny tie expected a faster hello."],
      biscuit: ["Formal note: {company} is the newest new lead. The ice has not been broken."],
    },
    "followup-overdue": {
      hanuman: ["{count} follow-up{s} overdue. I checked the sun. It moved. These did not."],
      mango: ["{count} overdue follow-up{s}. SQUAWK. That was the count, not a threat."],
      noodle: ["{count} follow-up{s} are past due. The clipboard snagged on the dates."],
      pickle: ["{count} overdue follow-up{s}. A clever fox would call this a pattern."],
      biscuit: ["{count} follow-up{s} overdue. The dates thawed. The queue did not."],
    },
    "followup-open": {
      hanuman: ["{count} open follow-up{s}, none overdue yet. Future-you is already sighing."],
      mango: ["{count} open follow-up{s}. SQUAWK. Not late. Merely lurking."],
      noodle: ["{count} open follow-up{s} on the clipboard. None are late. I remain moist with suspicion."],
      pickle: ["{count} open follow-up{s}. The tiny tie calls this a head start. Use it."],
      biscuit: ["{count} open follow-up{s}, all still in the future. How rare. How fragile."],
    },
    "pipeline-stalled": {
      hanuman: ["{count} lead{s} camped in {status}. That column has built a small kingdom."],
      mango: ["{status} is holding {count} lead{s}. SQUAWK. I will repeat the stage until someone moves a card. {status}."],
      noodle: ["{count} in {status}. Stalled. I wrote the stage name twice so it feels seen."],
      pickle: ["{status} has {count} lead{s} sitting pretty. Politely stuck. The tiny tie is unimpressed."],
      biscuit: ["{count} stuck in {status}. A penguin can spot a traffic jam."],
    },
    "report-metric": {
      hanuman: ["The number worth a small bow: {label} is {value}."],
      mango: ["{label}: {value}. SQUAWK. I memorized it. Unfortunately."],
      noodle: ["Key metric, circled on the clipboard: {label} {value}."],
      pickle: ["{label} is {value}. That is the tell on this page."],
      biscuit: ["Report headline: {label} {value}. I brought it up to the surface."],
    },
    "team-pending": {
      hanuman: ["{count} account{s} waiting for access. The gate is a button, not a riddle."],
      mango: ["{count} waiting for access. SQUAWK. Someone is standing outside the workspace."],
      noodle: ["Clipboard: {count} account{s} waiting for access. I did not let them in. I cannot."],
      pickle: ["{count} account{s} waiting for access. Leaving them there is not a strategy."],
      biscuit: ["Formal note: {count} waiting for access. The bench is cold."],
    },
    "users-pending": {
      hanuman: ["{count} account{s} waiting for access. Approve, or the badge will keep clearing its throat."],
      mango: ["{count} waiting for access. SQUAWK. The pending row is right there."],
      noodle: ["{count} account{s} waiting for access. I highlighted the row. The button is yours."],
      pickle: ["{count} waiting for access. The tiny tie does not do approvals. You do."],
      biscuit: ["{count} account{s} waiting for access. I waddled to the queue on purpose."],
    },
    "apis-missing": {
      hanuman: ["No saved key for {providers}. The mace is free. The APIs are not."],
      mango: ["Missing key: {providers}. SQUAWK. I cannot search with charm alone."],
      noodle: ["Clipboard: no key saved for {providers}. I checked the hint column. It is a shrug."],
      pickle: ["No saved key for {providers}. Bold. Also how searches come back empty."],
      biscuit: ["Formal notice: {providers} is not configured. The ice is lovely. The key is not."],
    },
    "ai-missing": {
      hanuman: ["No LLM is configured. Scoring and drafts are currently interpretive dance."],
      mango: ["No model key. SQUAWK. The agents have a script and nowhere to read it."],
      noodle: ["Clipboard: no LLM configured. Research, scoring, and outreach are on a snack break."],
      pickle: ["No LLM key. The tiny tie cannot bluff a model into existing."],
      biscuit: ["Formal note: no LLM provider. The pipeline can still be moved by a person."],
    },
    "overview-followups": {
      hanuman: ["{count} follow-up{s} still open. The overview put the number where I could point at it."],
      mango: ["{count} open follow-up{s}. SQUAWK. The big number on the card is the assignment."],
      noodle: ["{count} follow-up{s} open. I circled the overview card. Gently."],
      pickle: ["{count} open follow-up{s}. The overview is trying to be polite about it."],
      biscuit: ["{count} follow-up{s} open. I would slide them across the ice toward you."],
    },
    "overview-lead": {
      hanuman: ["{company}{scorePhrase} is the new lead on the overview. Still uncontacted."],
      mango: ["Overview pick: {company}{scorePhrase}. SQUAWK. Still a new lead."],
      noodle: ["Clipboard from the overview: {company}{scorePhrase}, still a new lead."],
      pickle: ["{company}{scorePhrase} is the new lead worth a look. The tiny tie concurs."],
      biscuit: ["Formal pick from the overview: {company}{scorePhrase}. Still a new lead."],
    },
    "overview-start": {
      hanuman: ["No leads yet. The banner is being polite. I am being slightly less polite."],
      mango: ["Empty workspace. SQUAWK. Start with a search. I will watch."],
      noodle: ["No leads yet. The clipboard is blank and emotionally unprepared."],
      pickle: ["Nothing in the pipeline. A saved search would give the tiny tie something to judge."],
      biscuit: ["No leads yet. The ice is clean. That is not the same as finished."],
    },
    preview: {
      hanuman: ["Here's the summary! I hopped. You're welcome."],
      mango: ["Here's the summary! SQUAWK. Short version, on purpose."],
      noodle: ["Here's the summary! I did not add extra pages. Growth."],
      pickle: ["Here's the summary! The tiny tie prefers it to a novel."],
      biscuit: ["Here's the summary! Formal, brief, and already on screen."],
    },
    generic: {
      hanuman: ["I looked around. The useful bit is trying to make eye contact."],
      mango: ["SQUAWK. You tapped the parrot. The page still has a point."],
      noodle: ["Boop. I was filing a shell. The page can go first."],
      pickle: ["Careful. This fox charges by the smirk, and the page is the actual job."],
      biscuit: ["A tap. How formal. I was judging the ice, but the page wins."],
    },
  };

  /* Shorter pages share a joke, then each character seasons it. */
  const SHARED = {
    "lead-empty": ["No leads on this page. The table is a blank stare."],
    "lead-quiet": ["Nothing here is still a new lead. Either the list is handled, or the filter is showing off."],
    "followup-clear": ["No open follow-ups. I am suspicious, and also a little proud."],
    "pipeline-empty": ["The pipeline board is empty. A fresh kingdom. Try not to take it personally."],
    "pipeline-won": ["{count} won. Lovely. The other columns are still looking at me."],
    "report-empty": ["Reports have not loaded a number yet. I refuse to invent one."],
    "team-roster": ["{count} approved people. I am not roasting the roster."],
    "team-empty": ["No approved people on this list yet. The bench is empty."],
    "users-clear": ["Nobody is waiting for access. The queue is clear, which ruins my bit."],
    "apis-ok": ["Every provider key on this page is set. Unsettling, in a good way."],
    "ai-ready": ["A model is routed. Scoring and drafts have somewhere to go."],
    "overview-quiet": ["Overview is calm. {count} lead{s} in the workspace. I checked twice so I could look busy."],
    "cockpit-alert": ["Cockpit warning: {label}. The red light is the one I would read first."],
    "cockpit-caution": ["Cockpit caution: {label}. Amber means look before the next pass."],
    "search-missing": ["No search provider is configured. The presets are dressed up with nowhere to go."],
    "search-empty": ["No saved search yet. The chips are glittering for nobody."],
    "search-ready": ["{count} saved search{s} on file. I would run one, but I do not have thumbs."],
    "geo-empty": ["No default country yet. New searches are guessing."],
    "geo-set": ["Searches start in {country}. A pin is not a pipeline, but it is a start."],
    "grok-missing": ["GrokBot has no model key. The specialists are on an unpaid break."],
    "grok-idle": ["Pick a lead before running the agents. They get nervous without a company to study."],
    "grok-ready": ["The agents are lined up. They still only draft. A person marks Qualified."],
    "bots-pending": ["{count} bot{s} waiting for access. Even bots have to knock."],
    "bots-unread": ["{count} unread bot message{s}. I did not read them. Boundaries."],
    "bots-clear": ["The bots are quiet. Enjoy the hush."],
    "settings-profile": ["The business profile is missing a company name or an offer. Drafts will improvise."],
    "settings-ready": ["Workspace settings are filled in. I have nothing to file."],
    "activity-failed": ["{count} failed event{s} in the log. The log is counting, not being dramatic."],
    "activity-today": ["Activities today: {count}. Hopping almost counts."],
    "comments-empty": ["No workspace updates yet. The silence is very professional."],
    "comments-ready": ["Updates are posted. I left them on the page, un-roasted."],
    "social-reply": ["{count} post{s} to reply to. Copy the draft. I will not post it for you."],
    "social-engage": ["{count} discussion{s} worth a comment. Still your fingers, not mine."],
    "social-clear": ["The social feed has nothing waiting. Copy stays a human job."],
    "pulse-urgent": ["{count} urgent staffing card{s}. The red edge is the one I would read first."],
    "pulse-week": ["{count} staffing card{s} for this week. Not a siren. Still worth a glance."],
    "pulse-clear": ["Industry Pulse is quiet. No urgent headline on the board."],
  };

  function spice(id, line) {
    const character = byId(id);
    if (character && character.voice) return character.voice(line);
    if (id === "mango") return /^squawk/i.test(line) ? line : "SQUAWK. " + line;
    if (id === "noodle") return /clipboard/i.test(line) ? line : "Clipboard note: " + line;
    if (id === "pickle") return /tiny tie/i.test(line) ? line : line + " The tiny tie agrees.";
    if (id === "biscuit") return /^(Formal|Noted)/.test(line) ? line : "Formal note: " + line;
    return line;
  }

  function applyTone(line, tone) {
    const text = String(line || "");
    if (tone === "polite") {
      return text
        .replace(/^SQUAWK\.\s*/i, "")
        .replace(/^Hmph\.\s*/i, "")
        .replace(/^Boo, kindly\.\s*/i, "")
        .replace(/\s*The tiny tie agrees\./, "")
        .replace(/\s{2,}/g, " ")
        .trim();
    }
    if (tone === "savage" && !/Here's the summary!/.test(text)) {
      return /\.$/.test(text) ? text.replace(/\.$/, ". Kindly, do not leave it there.") : text + " Kindly, do not leave it there.";
    }
    return text;
  }

  function fill(template, facts) {
    const source = facts || {};
    const count = Number(source.count);
    const safeCount = Number.isFinite(count) ? count : 0;
    const data = Object.assign({}, source, {count: safeCount, s: safeCount === 1 ? "" : "s"});
    return String(template).replace(/\{(\w+)\}/g, function (_, key) {
      const value = data[key];
      return value == null ? "" : String(value);
    });
  }

  function linesFor(characterId, kind) {
    const character = byId(characterId) || byId("hanuman");
    const id = character.id;
    if (character.lines && character.lines[kind] && character.lines[kind].length) return character.lines[kind];
    const voiced = VOICED[kind];
    if (voiced && voiced[id] && voiced[id].length) return voiced[id];
    const shared = SHARED[kind];
    if (shared && shared.length) return shared.map(function (line) { return spice(id, line); });
    if (VOICED.generic && VOICED.generic[id] && VOICED.generic[id].length) return VOICED.generic[id];
    const fallback = (VOICED.generic && VOICED.generic.hanuman) || ["I looked around."];
    return fallback.map(function (line) { return spice(id, line); });
  }

  function byId(id) {
    for (let i = 0; i < CHARACTERS.length; i += 1) {
      if (CHARACTERS[i].id === id) return CHARACTERS[i];
    }
    return null;
  }

  function next(id) {
    const index = CHARACTERS.findIndex(function (character) { return character.id === id; });
    return CHARACTERS[(index + 1 + CHARACTERS.length) % CHARACTERS.length];
  }

  function quip(characterId, insight, random) {
    const kind = insight && insight.kind ? insight.kind : "generic";
    const lines = linesFor(characterId, kind);
    const roll = typeof random === "function" ? Number(random()) : Math.random();
    const index = Math.abs(Math.floor(roll * lines.length)) % lines.length;
    return applyTone(fill(lines[index], insight && insight.facts), insight && insight.tone);
  }

  function describe(id) {
    const character = byId(id) || CHARACTERS[0];
    return {
      id: character.id,
      name: character.name,
      pose: character.pose,
      blurb: character.blurb,
      group: character.group || "classic",
      idleMs: character.idleMs || 0,
      svg: character.svg(),
    };
  }

  const api = {
    STORAGE_KEY: STORAGE_KEY,
    GROUPS: [
      {id: "classic", label: "Classic"},
      {id: "ramayana", label: "Ramayana"},
      {id: "mahabharata", label: "Mahabharata"},
      {id: "fun", label: "Fun"},
    ],
    list: function () { return CHARACTERS.map(function (character) { return describe(character.id); }); },
    byId: function (id) { const character = byId(id); return character ? describe(character.id) : null; },
    next: function (id) { return describe(next(id).id); },
    quip: quip,
    fill: fill,
  };

  root.MascotCharacters = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
