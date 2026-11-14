/* Triple-click tracker and the lines said on the way out and back. */
(function (root) {
  const LINES = {
    hanuman: {
      leave: "Enough poking! I'm off to fetch the Sanjeevani, back in 10!",
      back: "The mountain was closer than it looked. I am back, and the follow-ups are too.",
    },
    "rocket-boss": {
      leave: "I'm going to Mars. Bye.",
      back: "Reentry complete. The lead is still on the pad.",
    },
  };
  const GENERIC = {
    leave: "Enough poking. I am taking ten seconds. The work can hold still.",
    back: "I cooled off. The queue did not.",
  };

  function createTracker(options) {
    const opts = options || {};
    const windowMs = Number(opts.windowMs) || 600;
    const need = Number(opts.need) || 3;
    const cooldownMs = Number(opts.cooldownMs) || 10000;
    let stamps = [];
    let coolingUntil = 0;
    return function note(now) {
      const time = Number(now) || 0;
      if (time < coolingUntil) return {fired: false, ignored: true};
      stamps = stamps.filter(function (stamp) { return time - stamp <= windowMs; });
      stamps.push(time);
      if (stamps.length >= need) {
        stamps = [];
        coolingUntil = time + cooldownMs;
        return {fired: true, ignored: false};
      }
      return {fired: false, ignored: false};
    };
  }

  function leaveLine(id) {
    return (LINES[id] || GENERIC).leave;
  }

  function returnLine(id) {
    return (LINES[id] || GENERIC).back;
  }

  const api = {createTracker: createTracker, leaveLine: leaveLine, returnLine: returnLine, COOLDOWN_MS: 10000};
  root.MascotAnger = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
