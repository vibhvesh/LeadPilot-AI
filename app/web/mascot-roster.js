/* One full-body cartoon used by the ten-character roster. Props differ; the walk does not. */
(function (root) {
  function figure(opts) {
    const skin = opts.skin || "#f0c9a0";
    const cloth = opts.cloth || "#1d4ed8";
    const pants = opts.pants || "#243044";
    return `<svg class="mascot-svg crew-svg" viewBox="0 0 80 120" aria-hidden="true"><g class="crew-body mascot-body">
      <g class="mascot-leg mascot-leg-left"><path d="M32 78 v24" stroke="${pants}" stroke-width="5" stroke-linecap="round"/><ellipse cx="30" cy="104" rx="6" ry="3" fill="#1b2430"/></g>
      <g class="mascot-leg mascot-leg-right"><path d="M48 78 v24" stroke="${pants}" stroke-width="5" stroke-linecap="round"/><ellipse cx="50" cy="104" rx="6" ry="3" fill="#1b2430"/></g>
      <path class="crew-arm crew-arm-left" d="M26 54 l-10 14" stroke="${skin}" stroke-width="4" stroke-linecap="round"/>
      <path class="crew-arm crew-arm-right" d="M54 54 l10 14" stroke="${skin}" stroke-width="4" stroke-linecap="round"/>
      <path class="crew-torso" d="M26 48 h28 v30 h-28 z" fill="${cloth}"/>
      <circle class="crew-head" cx="40" cy="32" r="14" fill="${skin}"/>
      <g class="crew-face">
        <g class="mascot-eye"><circle cx="35" cy="32" r="1.6" fill="#2b2118"/></g>
        <g class="mascot-eye mascot-eye-right"><circle cx="45" cy="32" r="1.6" fill="#2b2118"/></g>
        <path class="crew-mouth" d="M34 40 q6 4 12 0" fill="none" stroke="#8a5a3a" stroke-width="1.3" stroke-linecap="round"/>
      </g>
      ${opts.extra || ""}
    </g></svg>`;
  }

  root.MascotBodies = {
    hanuman: function () {
      return figure({skin: "#ef8a3a", cloth: "#c4554a", pants: "#d86e28", extra: `<path class="hanuman-tail mascot-tail" d="M18 70c-14 6-12 20 0 18" fill="none" stroke="#e07a2f" stroke-width="4"/><path class="hanuman-crown" d="M30 22 l4-8 6 6 6-8 4 10z" fill="#f0c14a"/><g class="hanuman-gada"><rect x="60" y="40" width="3" height="14" fill="#c8960e"/><circle cx="61" cy="38" r="4" fill="#f0c14a"/></g>`});
    },
    rama: function () {
      return figure({skin: "#e7b48a", cloth: "#c4554a", extra: `<path class="rama-bow" d="M62 36c8 8 8 22 0 30" fill="none" stroke="#8a5a2b" stroke-width="2"/>`});
    },
    lakshmana: function () {
      return figure({skin: "#e7b48a", cloth: "#2457c5", extra: `<path class="lakshmana-bow" d="M62 40c6 8 6 18 0 26" fill="none" stroke="#6b4423" stroke-width="2"/>`});
    },
    sita: function () {
      return figure({skin: "#f3c7a1", cloth: "#d4a017", extra: `<circle class="sita-lotus" cx="62" cy="62" r="5" fill="#f4b4c4"/>`});
    },
    jambavan: function () {
      return figure({skin: "#6b4a32", cloth: "#3d2a1c", extra: `<rect class="jambavan-club" x="60" y="36" width="5" height="18" rx="2" fill="#8a5a2b"/>`});
    },
    krishna: function () {
      return figure({skin: "#7ec8c3", cloth: "#f0c14a", extra: `<path class="krishna-flute" d="M56 58 h16" stroke="#2b2118" stroke-width="2"/>`});
    },
    arjuna: function () {
      return figure({skin: "#e7b48a", cloth: "#f4f7fb", pants: "#2457c5", extra: `<path class="arjuna-bow" d="M64 34c7 10 7 24 0 34" fill="none" stroke="#8a5a2b" stroke-width="2"/>`});
    },
    bhima: function () {
      return figure({skin: "#e7b48a", cloth: "#b45309", extra: `<rect class="bhima-mace" x="60" y="34" width="4" height="20" fill="#6b4423"/><circle cx="62" cy="32" r="5" fill="#8a5a2b"/>`});
    },
    narad: function () {
      return figure({skin: "#f0c9a0", cloth: "#f4e1a8", extra: `<path class="narad-topknot" d="M40 18 l4-8 4 8" fill="#2b2118"/><path class="narad-veena" d="M18 60 q16 10 28-6" fill="none" stroke="#8a5a2b" stroke-width="2"/>`});
    },
    "rocket-boss": function () {
      return figure({skin: "#f0c9a0", cloth: "#161616", pants: "#243044", extra: `<path class="rocket-shirt" d="M26 48 h28 v30 h-28 z" fill="#161616"/><g class="rocket-ship" transform="translate(56,16)"><path d="M6 16 L6 6 L12 1 L18 6 V16 Z" fill="#d8dee8"/></g><circle class="rocket-badge" cx="48" cy="60" r="4" fill="#c4554a"/><g class="rocket-mug"><rect x="8" y="58" width="8" height="10" rx="1" fill="#f4e1a8"/></g><g class="rocket-cigar"><rect x="50" y="40" width="12" height="2" fill="#6b3e26"/></g><g class="rocket-smoke"><circle class="rocket-puff" cx="64" cy="36" r="2" fill="#e6ebf2"/></g>`});
    },
  };
})(typeof globalThis !== "undefined" ? globalThis : this);
