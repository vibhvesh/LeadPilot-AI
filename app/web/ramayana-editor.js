/* Admin editor for captions and speech, plus the overlay kill switch. */
(function () {
  const box = document.getElementById("story-lines");
  const toggle = document.getElementById("story-enabled");
  if (!box || !window.RamayanaScenes) return;

  function note(row, message) {
    const status = row.querySelector(".story-save-note");
    status.textContent = message;
  }

  async function save(row) {
    const res = await fetch("/api/admin/story-messages", {
      method: "PUT",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scene_id: row.dataset.scene, actor: row.dataset.actor, text: row.querySelector("textarea").value }),
    });
    note(row, res.ok ? "Saved" : "Could not save");
  }

  async function reset(row) {
    const res = await fetch("/api/admin/story-messages/reset", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scene_id: row.dataset.scene, actor: row.dataset.actor }),
    });
    if (res.ok) {
      row.querySelector("textarea").value = row.dataset.fallback;
      note(row, "Reset");
    }
  }

  function render(overrides) {
    const scenes = window.RamayanaScenes.list();
    box.innerHTML = "";
    scenes.forEach(function (scene) {
      const details = document.createElement("details");
      details.className = "story-scene";
      const summary = document.createElement("summary");
      summary.textContent = scene.id + " " + scene.title + (scene.gag ? " · Rocket Boss and Old Man Boss" : "") + (scene.blessing ? " · Valmiki" : "");
      details.appendChild(summary);
      window.RamayanaScenes.rows().filter(function (item) { return item.scene_id === scene.id; }).forEach(function (item) {
        const row = document.createElement("div");
        row.className = "story-line";
        row.dataset.scene = item.scene_id;
        row.dataset.actor = item.actor;
        row.dataset.fallback = item.text;
        const key = item.scene_id + ":" + item.actor;
        const label = document.createElement("label");
        label.textContent = item.label;
        const area = document.createElement("textarea");
        area.maxLength = 240;
        area.value = overrides[key] || item.text;
        const saveBtn = document.createElement("button");
        saveBtn.type = "button";
        saveBtn.textContent = "Save";
        const resetBtn = document.createElement("button");
        resetBtn.type = "button";
        resetBtn.textContent = "Reset";
        const status = document.createElement("span");
        status.className = "story-save-note";
        saveBtn.addEventListener("click", function () { save(row); });
        resetBtn.addEventListener("click", function () { reset(row); });
        label.appendChild(area);
        row.append(label, saveBtn, resetBtn, status);
        details.appendChild(row);
      });
      box.appendChild(details);
    });
  }

  if (toggle) {
    toggle.addEventListener("change", async function () {
      await fetch("/api/admin/story-overlay", {
        method: "PUT",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: toggle.checked }),
      });
    });
    fetch("/api/story/overlay", { credentials: "same-origin" }).then(function (res) { return res.ok ? res.json() : { enabled: false }; }).then(function (data) {
      toggle.checked = data.enabled === true;
    }).catch(function () { toggle.checked = false; });
  }

  const play = document.getElementById("story-play");
  if (play) {
    play.addEventListener("click", function () {
      if (window.StoryBoot) window.StoryBoot.startNow();
    });
  }

  fetch("/api/story/lines", { credentials: "same-origin" }).then(function (res) { return res.ok ? res.json() : { lines: {} }; }).then(function (data) {
    render(data.lines || {});
  }).catch(function () { render({}); });
})();
