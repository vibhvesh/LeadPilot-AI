/* Story-page cast. Separate from the live mascot crew. */
(function (root) {
  const NAMES = {
    rama: "Rama",
    lakshmana: "Lakshmana",
    sita: "Sita",
    hanuman: "Hanuman",
    jambavan: "Jambavan",
    sugriva: "Sugriva",
    vibhishana: "Vibhishana",
    ravana: "Ravana",
    kumbhakarna: "Kumbhakarna",
    narad: "Narad",
    "rocket-boss": "Rocket Boss",
    "old-man-boss": "Old Man Boss",
  };

  function wrap(body, extra) {
    return `<svg class="story-svg ${extra || ""}" viewBox="0 0 90 150" aria-hidden="true">${body}</svg>`;
  }

  function legs(color) {
    return `<g class="story-leg story-leg-l"><path d="M34 96 L30 132" stroke="${color}" stroke-width="7" stroke-linecap="round"/></g>
      <g class="story-leg story-leg-r"><path d="M56 96 L60 132" stroke="${color}" stroke-width="7" stroke-linecap="round"/></g>`;
  }

  function arms(skin, prop) {
    return `<g class="story-arm story-arm-l"><path d="M28 62 L12 84" stroke="${skin}" stroke-width="6" stroke-linecap="round"/></g>
      <g class="story-arm story-arm-r"><path d="M62 62 L80 78" stroke="${skin}" stroke-width="6" stroke-linecap="round"/>${prop || ""}</g>`;
  }

  function face(skin, extra) {
    return `<circle cx="45" cy="36" r="16" fill="${skin}"/>
      <circle cx="39" cy="34" r="1.6" fill="#2b2118"/><circle cx="51" cy="34" r="1.6" fill="#2b2118"/>
      <path d="M40 42 Q45 46 50 42" fill="none" stroke="#2b2118" stroke-width="1.2"/>${extra || ""}`;
  }

  function torso(cloth) {
    return `<path d="M28 54 h34 v40 h-34 z" fill="${cloth}" rx="6"/>`;
  }

  function bow() {
    return `<path d="M78 70 Q92 86 78 102" fill="none" stroke="#8a5a2a" stroke-width="2"/>
      <path d="M78 70 L78 102" stroke="#f2c14e" stroke-width="1"/>`;
  }

  function person(opts) {
    return wrap(`
      ${legs(opts.leg || opts.cloth)}
      ${torso(opts.cloth)}
      ${arms(opts.skin, opts.prop || "")}
      ${face(opts.skin, opts.face || "")}
      ${opts.hat || ""}
      ${opts.extra || ""}
    `, opts.className || "");
  }

  function rama() {
    return person({
      skin: "#6f93ff",
      cloth: "#f2c14e",
      className: "story-rama",
      hat: `<path d="M30 24 L45 10 L60 24" fill="#f2c14e"/><circle cx="45" cy="12" r="3" fill="#e07a2f"/>`,
      prop: bow(),
      extra: `<path class="rama-quiver" d="M22 58 l6 4 l-2 16 l-6 -2 z" fill="#8a5a2a"/>`,
    });
  }

  function lakshmana() {
    return person({
      skin: "#f0c9a0",
      cloth: "#e07a3d",
      className: "story-lakshmana",
      hat: `<path d="M32 24 h26 l-4 6 h-18 z" fill="#f2c14e"/>`,
      prop: bow(),
    });
  }

  function sita() {
    return person({
      skin: "#f0c9a0",
      cloth: "#c23b4a",
      leg: "#c23b4a",
      className: "story-sita",
      face: `<circle cx="45" cy="28" r="2" fill="#c23b4a"/>`,
      prop: `<ellipse class="sita-lotus" cx="82" cy="84" rx="7" ry="4" fill="#f4a7c5"/><circle cx="82" cy="84" r="2" fill="#f2c14e"/>`,
      extra: `<path d="M30 52 Q45 46 60 52" fill="none" stroke="#f2c14e" stroke-width="2"/>`,
    });
  }

  function hanuman() {
    return wrap(`
      <g class="story-tail"><path d="M20 100 C -8 90, -16 48, 16 28 C 40 14, 58 40, 40 58" fill="none" stroke="#e07a2f" stroke-width="7" stroke-linecap="round"/></g>
      ${legs("#c4622a")}
      ${torso("#e07a2f")}
      ${arms("#e07a2f", `<rect class="hanuman-gada" x="76" y="70" width="6" height="22" rx="2" fill="#e2b657"/><circle cx="79" cy="68" r="6" fill="#f2c14e"/>`)}
      ${face("#e07a2f", `<ellipse cx="45" cy="30" rx="7" ry="4" fill="#f3c08a"/>`)}
      <ellipse cx="28" cy="34" rx="6" ry="7" fill="#e07a2f"/><ellipse cx="62" cy="34" rx="6" ry="7" fill="#e07a2f"/>
    `, "story-hanuman");
  }

  function jambavan() {
    return person({
      skin: "#8d939c",
      cloth: "#6e7580",
      className: "story-jambavan",
      face: `<ellipse cx="34" cy="40" rx="4" ry="3" fill="#6e7580"/><ellipse cx="56" cy="40" rx="4" ry="3" fill="#6e7580"/>`,
      prop: `<path class="jambavan-staff" d="M80 60 L86 108" stroke="#8a5a2a" stroke-width="3" stroke-linecap="round"/>`,
      extra: `<ellipse cx="24" cy="36" rx="7" ry="8" fill="#8d939c"/><ellipse cx="66" cy="36" rx="7" ry="8" fill="#8d939c"/>`,
    });
  }

  function sugriva() {
    return person({
      skin: "#c9844a",
      cloth: "#f2c14e",
      className: "story-sugriva",
      hat: `<path d="M30 22 L45 12 L60 22" fill="#f2c14e"/>`,
      prop: `<path class="sugriva-branch" d="M76 72 C 88 68, 96 86, 84 96" fill="none" stroke="#6b4423" stroke-width="4" stroke-linecap="round"/>`,
      extra: `<ellipse cx="27" cy="34" rx="5" ry="6" fill="#c9844a"/><ellipse cx="63" cy="34" rx="5" ry="6" fill="#c9844a"/>`,
    });
  }

  function vibhishana() {
    return person({
      skin: "#f4e2c4",
      cloth: "#f7f1df",
      leg: "#e6d7b0",
      className: "story-vibhishana",
      hat: `<path d="M32 22 h26 v6 h-26 z" fill="#e2b657"/>`,
      prop: "",
      extra: `<path class="vibhishana-hands" d="M40 70 h10 v8 h-10 z" fill="#f4e2c4"/>`,
    });
  }

  function ravana() {
    let heads = "";
    for (let i = 0; i < 10; i += 1) {
      const x = 14 + (i % 5) * 15;
      const y = i < 5 ? 12 : 22;
      heads += `<circle class="ravana-head" cx="${x}" cy="${y}" r="6" fill="#d98a72"/>`;
    }
    return wrap(`
      ${heads}
      ${legs("#5c3d8a")}
      ${torso("#6b4c9a")}
      ${arms("#d98a72", `<path class="ravana-sword" d="M78 64 L88 92" stroke="#d9dde3" stroke-width="3"/>`)}
      ${face("#d98a72")}
    `, "story-ravana");
  }

  function kumbhakarna() {
    return wrap(`
      <g class="story-giant">
        ${legs("#5c4a86")}
        ${torso("#6b4c9a")}
        ${arms("#c9a27a", `<rect class="kumbha-club" x="74" y="66" width="10" height="28" rx="4" fill="#6b4423"/>`)}
        ${face("#c9a27a", `<ellipse cx="45" cy="42" rx="6" ry="4" fill="#2b2118"/>`)}
        <path d="M32 20 h26" stroke="#2b2118" stroke-width="3"/>
      </g>
    `, "story-kumbhakarna");
  }

  function narad() {
    return person({
      skin: "#f0c9a0",
      cloth: "#e07a2f",
      className: "story-narad",
      hat: `<circle class="narad-topknot" cx="45" cy="16" r="5" fill="#2b2118"/>`,
      prop: `<path class="narad-veena" d="M74 78 Q 88 70, 84 96" fill="none" stroke="#8a5a2a" stroke-width="3"/>`,
    });
  }

  function rocketBoss() {
    return `<svg class="story-svg story-rocket" viewBox="0 0 120 160" aria-hidden="true">
      <path class="rocket-cape" d="M48 62 Q18 78 28 132 L52 108 Q40 86 54 64" fill="#c23b4a"/>
      <path class="rocket-cape" d="M72 62 Q108 86 96 136 L70 108 Q84 84 68 64" fill="#a32d3c"/>
      <g class="rocket-jetpack">
        <rect x="22" y="66" width="16" height="40" rx="5" fill="#c4554a"/>
        <rect x="25" y="70" width="10" height="24" rx="2" fill="#d5dbe3"/>
        <rect x="28" y="76" width="4" height="10" fill="#f4f7fb"/>
        <path class="story-flame" d="M26 108 L30 132 L34 108" fill="#f2a03a"/>
        <path class="story-flame" d="M30 108 L34 126 L38 108" fill="#f6d36b"/>
      </g>
      <g class="story-leg story-leg-l">
        <path d="M50 108 L44 138" stroke="#3a4150" stroke-width="11" stroke-linecap="round"/>
        <rect x="40" y="118" width="8" height="7" rx="1.5" fill="#2a3140"/>
      </g>
      <g class="story-leg story-leg-r">
        <path d="M70 108 L78 138" stroke="#3a4150" stroke-width="11" stroke-linecap="round"/>
        <rect x="72" y="118" width="8" height="7" rx="1.5" fill="#2a3140"/>
      </g>
      <path class="rocket-sneaker" d="M34 140 h20 l2 6 h-24 z" fill="#f7f4ee"/>
      <path d="M36 140 h12 v3 h-12 z" fill="#2b2118"/>
      <path class="rocket-sneaker" d="M68 140 h22 l2 6 h-26 z" fill="#f7f4ee"/>
      <path d="M72 140 h12 v3 h-12 z" fill="#2b2118"/>
      <path d="M46 64 h28 v40 h-28 z" fill="#b7b7b7"/>
      <path class="rocket-shirt" d="M36 60 h16 l2 46 h-12 z" fill="#c9e0d6"/>
      <path class="rocket-shirt" d="M68 60 h16 l-6 46 h-12 z" fill="#b7d4c8"/>
      <path class="rocket-chain" d="M52 70 Q60 78 68 70" fill="none" stroke="#e2b657" stroke-width="1.6"/>
      <g class="story-arm story-arm-l"><path d="M40 72 L30 96" stroke="#d7b294" stroke-width="6" stroke-linecap="round"/></g>
      <g class="story-arm story-arm-r">
        <path d="M78 70 L96 58" stroke="#d7b294" stroke-width="6" stroke-linecap="round"/>
        <g class="rocket-gada">
          <rect x="78" y="40" width="28" height="5" rx="2" transform="rotate(-28 78 40)" fill="#e2b657"/>
          <circle cx="70" cy="36" r="11" fill="#f2c14e"/>
          <path d="M64 36 h12 M70 30 v12" stroke="#c9962e" stroke-width="1"/>
        </g>
      </g>
      <circle cx="60" cy="40" r="15" fill="#e7b892"/>
      <path class="rocket-hair" d="M46 34 Q44 16 58 14 Q70 8 78 20 Q84 30 76 36 Q66 18 52 28 Z" fill="#241910"/>
      <path class="rocket-sunglasses" d="M46 40 h12 l2 6 h-16 z M62 40 h12 l2 6 h-16 z" fill="#1a1a1a"/>
      <path d="M58 42 h4" stroke="#1a1a1a" stroke-width="2"/>
      <path class="rocket-stubble" d="M54 50 h4 M62 50 h4 M57 54 h6" stroke="#8d6b52" stroke-width="1"/>
      <path class="rocket-goatee" d="M58 52 Q60 58 62 52" fill="#3a2a22"/>
      <path d="M55 48 Q60 51 65 48" fill="none" stroke="#6b3e32" stroke-width="1"/>
    </svg>`;
  }

  const TEAMS = [
    { cloth: "#f2c14e", skin: "#e8b896", hat: `<path d="M30 22 L45 10 L60 22" fill="#f2c14e"/>`, prop: bow() },
    { cloth: "#f2c14e", skin: "#d7a57a", prop: `<path d="M76 74 Q86 68 84 86" fill="none" stroke="#f7f1df" stroke-width="3"/>` },
    { cloth: "#3d6fbf", skin: "#f0c9a0", leg: "#3d6fbf", face: `<circle cx="45" cy="28" r="2" fill="#c23b4a"/>`, prop: `<ellipse cx="82" cy="84" rx="6" ry="3" fill="#f4a7c5"/>` },
    { cloth: "#f2c14e", skin: "#c9844a", prop: `<rect x="76" y="68" width="8" height="22" rx="3" fill="#6b4423"/>` },
    { cloth: "#f2c14e", skin: "#e0b08a", hat: `<rect x="32" y="18" width="26" height="8" rx="2" fill="#2b6cb0"/>`, prop: bow() },
    { cloth: "#f2c14e", skin: "#e8b896", face: `<rect x="36" y="32" width="16" height="6" rx="2" fill="none" stroke="#2b2118"/>` },
    { cloth: "#f2c14e", skin: "#d7a57a", hat: `<path d="M34 22 Q45 12 56 22" fill="#2b2118"/>`, prop: `<path d="M78 66 L86 104" stroke="#8a5a2a" stroke-width="3"/>` },
  ];

  function team(index) {
    const item = TEAMS[index];
    return person({
      skin: item.skin,
      cloth: item.cloth,
      leg: item.leg || item.cloth,
      className: "story-extra",
      hat: item.hat || "",
      prop: item.prop || "",
      face: item.face || "",
    });
  }

  function oldManBoss() {
    return `<svg class="story-svg story-old-boss" viewBox="0 0 110 160" aria-hidden="true">
      <g class="story-leg story-leg-l"><path d="M42 104 L36 140" stroke="#5c6570" stroke-width="11" stroke-linecap="round"/></g>
      <g class="story-leg story-leg-r"><path d="M64 104 L70 140" stroke="#5c6570" stroke-width="11" stroke-linecap="round"/></g>
      <path class="old-shoe" d="M26 140 h22 l2 7 h-26 z" fill="#6b3e22"/>
      <path class="old-shoe" d="M58 140 h24 l2 7 h-28 z" fill="#6b3e22"/>
      <path class="old-sweater" d="M32 58 h42 v48 h-42 z" fill="#8a6244"/>
      <path d="M51 62 v40" stroke="#d9cfc2" stroke-width="2"/>
      <path d="M38 58 Q53 48 70 58" fill="#6e4c34"/>
      <g class="story-arm story-arm-l">
        <path d="M34 70 L24 46" stroke="#8a6244" stroke-width="8" stroke-linecap="round"/>
        <circle cx="22" cy="42" r="6" fill="#e0b08a"/>
        <path class="old-finger" d="M22 36 L22 22" stroke="#e0b08a" stroke-width="3.5" stroke-linecap="round"/>
      </g>
      <g class="story-arm story-arm-r">
        <path d="M72 72 L84 102" stroke="#8a6244" stroke-width="8" stroke-linecap="round"/>
        <circle class="old-watch" cx="80" cy="98" r="5" fill="#e2b657"/>
        <circle cx="80" cy="98" r="2" fill="#f7f4ee"/>
        <path class="old-stick" d="M86 104 L90 150" stroke="#8a5a2a" stroke-width="4" stroke-linecap="round"/>
        <path d="M78 106 Q90 96 98 108" fill="none" stroke="#8a5a2a" stroke-width="3.5" stroke-linecap="round"/>
      </g>
      <circle cx="52" cy="40" r="16" fill="#e0b08a"/>
      <path class="old-hair" d="M36 38 Q34 16 54 16 Q74 16 74 36 Q62 22 42 30 Z" fill="#2a241c"/>
      <path class="old-moustache" d="M42 48 Q52 54 62 48 Q52 50 42 48" fill="#3a342c"/>
      <circle cx="46" cy="40" r="1.6" fill="#2b2118"/>
      <circle cx="60" cy="40" r="1.6" fill="#2b2118"/>
      <path d="M46 54 Q52 58 58 54" fill="none" stroke="#6b3e32" stroke-width="1.2"/>
    </svg>`;
  }

  function svg(id) {
    const drawn = {
      rama, lakshmana, sita, hanuman, jambavan, sugriva, vibhishana, ravana, kumbhakarna, narad,
      "rocket-boss": rocketBoss,
      "old-man-boss": oldManBoss,
    }[id];
    if (drawn) return drawn();
    const teamMatch = /^team-(\d)$/.exec(id || "");
    if (teamMatch) return team(Number(teamMatch[1]) - 1);
    return person({ skin: "#f0c9a0", cloth: "#f2c14e" });
  }

  function name(id) {
    if (NAMES[id]) return NAMES[id];
    const teamMatch = /^team-(\d)$/.exec(id || "");
    return teamMatch ? `Team ${teamMatch[1]}` : id;
  }

  const api = { svg, name, ids: Object.keys(NAMES).concat(["team-1", "team-2", "team-3", "team-4", "team-5", "team-6", "team-7"]) };
  root.RamayanaCast = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
