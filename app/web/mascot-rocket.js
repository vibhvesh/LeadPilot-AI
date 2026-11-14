/* Rocket Boss visits: random walk, talk, beer, smoke, dance, and a text song. Muted unless asked. */
(function (root) {
  const ACTS = ["walk", "talk", "beer", "smoke", "dance", "sing"];
  const TALK = [
    "The lead is the payload. Shipping it is the launch.",
    "Mars is a hobby. The follow-up is the mission.",
    "Close the lead and we can call it orbit.",
  ];
  const SONG = "♪ One small lead, one giant follow-up, shipping it tonight ♪";
  const CHEERS = "Cheers! 🍺 Close that lead first";
  let timer = 0;

  function pool(family) {
    return ACTS.filter(function (act) {
      return !(family && (act === "beer" || act === "smoke"));
    });
  }

  function clear(host) {
    ["is-walking", "is-beer", "is-smoking", "is-dancing", "is-singing"].forEach(function (name) {
      if (host) host.classList.remove(name);
    });
  }

  function notes() {
    const Context = root.AudioContext || root.webkitAudioContext;
    if (!Context) return;
    const audio = new Context();
    [523, 659, 784].forEach(function (freq, index) {
      const osc = audio.createOscillator();
      const gain = audio.createGain();
      osc.frequency.value = freq;
      osc.connect(gain);
      gain.connect(audio.destination);
      gain.gain.setValueAtTime(0.04, audio.currentTime);
      const start = audio.currentTime + index * 0.18;
      osc.start(start);
      osc.stop(start + 0.16);
    });
  }

  function begin(host, options) {
    stop(host);
    const opts = options || {};
    const choices = pool(!!opts.family);
    function step() {
      if (!host || !host.isConnected) { stop(host); return; }
      const act = choices[Math.floor(Math.random() * choices.length)] || "talk";
      clear(host);
      if (act === "walk" && !opts.reduced) host.classList.add("is-walking");
      if (act === "talk" && opts.say) opts.say(opts.insight || TALK[Math.floor(Math.random() * TALK.length)]);
      if (act === "beer") {
        host.classList.add("is-beer");
        if (opts.say) opts.say(CHEERS);
      }
      if (act === "smoke") {
        if (!opts.reduced) host.classList.add("is-smoking");
        if (opts.say) opts.say("A cartoon cigar. The lead is the thing that is actually on fire.");
      }
      if (act === "dance" && !opts.reduced) {
        host.classList.add("is-dancing");
        if (opts.say) opts.say("Short dance. Then we ship the follow-up.");
      }
      if (act === "sing") {
        host.classList.add("is-singing");
        if (opts.say) opts.say(SONG);
        if (opts.sound && !opts.reduced) notes();
      }
    }
    step();
    if (!opts.reduced) timer = root.setInterval(step, 3200);
  }

  function stop(host) {
    root.clearInterval(timer);
    timer = 0;
    clear(host);
  }

  root.MascotRocket = {begin: begin, stop: stop, pool: pool, SONG: SONG, CHEERS: CHEERS};
})(typeof globalThis !== "undefined" ? globalThis : this);
