/* Preferences for the corner cast. The account is the source of truth; this browser remembers a copy. */
(function (root) {
  const STORAGE_KEY = "leadpilot-mascot-prefs";
  const DEFAULTS = {character: "hanuman", enabled: true, idle_ms: 2600, tone: "cheeky", size: "medium", side: "right"};
  let panel = null;
  let current = Object.assign({}, DEFAULTS);
  let workspaceDefault = "hanuman";
  let canSetDefault = false;
  let saving = false;

  function readLocal() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch (error) {
      return null;
    }
  }

  function writeLocal(prefs) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); }
    catch (error) { /* the account copy still applies on the next visit */ }
  }

  function emit(prefs) {
    current = Object.assign({}, DEFAULTS, prefs || {});
    root.dispatchEvent(new CustomEvent("leadpilot:mascot-prefs", {detail: current}));
  }

  function characters() {
    return (root.MascotCharacters && root.MascotCharacters.list()) || [];
  }

  function groups() {
    return (root.MascotCharacters && root.MascotCharacters.GROUPS) || [{id: "classic", label: "Classic"}];
  }

  function grid() {
    return groups().map(function (group) {
      const cards = characters().filter(function (item) { return item.group === group.id; }).map(function (item) {
        const selected = item.id === current.character ? " is-selected" : "";
        return `<button type="button" class="mascot-card${selected}" data-character="${item.id}"><span>${item.svg}</span><b>${item.name}</b></button>`;
      }).join("");
      if (!cards) return "";
      return `<h3>${group.label}</h3><div class="mascot-grid">${cards}</div>`;
    }).join("");
  }

  function field(name, label, options, value) {
    const choices = options.map(function (option) {
      const selected = option[0] === value ? " selected" : "";
      return `<option value="${option[0]}"${selected}>${option[1]}</option>`;
    }).join("");
    return `<label>${label}<select data-pref="${name}">${choices}</select></label>`;
  }

  function paint() {
    if (!panel) return;
    const seconds = (Number(current.idle_ms) || 2600) / 1000;
    panel.querySelector("[data-grid]").innerHTML = grid();
    panel.querySelector("[data-enabled]").checked = current.enabled !== false;
    panel.querySelector("[data-pref='tone']").value = current.tone || "cheeky";
    panel.querySelector("[data-pref='size']").value = current.size || "medium";
    panel.querySelector("[data-pref='side']").value = current.side || "right";
    panel.querySelector("[data-idle]").value = String(current.idle_ms || 2600);
    panel.querySelector("[data-idle-label]").textContent = seconds.toFixed(1) + " seconds";
    const note = panel.querySelector("[data-default-note]");
    note.textContent = canSetDefault
      ? "Workspace default for people who have not chosen: " + workspaceDefault + "."
      : "Your character is saved on your account.";
  }

  function ensure() {
    if (panel) return panel;
    panel = document.createElement("div");
    panel.className = "mascot-panel";
    panel.hidden = true;
    panel.innerHTML = `<div class="mascot-sheet" role="dialog" aria-modal="true" aria-label="Mascot settings">
      <h2>Mascot</h2>
      <p class="mascot-note">Pick who keeps you company. The jokes stay about the work.</p>
      <div data-grid></div>
      <div class="mascot-options">
        <label><span><input type="checkbox" data-enabled> Show the mascot</span></label>
        <label>Stillness before it visits<span data-idle-label>2.6 seconds</span>
          <input type="range" min="1500" max="10000" step="100" data-idle>
        </label>
        ${field("tone", "Joke level", [["polite", "Polite"], ["cheeky", "Cheeky"], ["savage", "Savage, still kind"]], "cheeky")}
        ${field("size", "Size", [["small", "Small"], ["medium", "Medium"], ["large", "Large"]], "medium")}
        ${field("side", "Resting side", [["right", "Right"], ["left", "Left"]], "right")}
      </div>
      <p class="mascot-note" data-default-note></p>
      <div class="mascot-row" data-admin hidden>
        <label>Workspace default<select data-workspace></select></label>
        <button type="button" class="btn small" data-save-default>Save default</button>
      </div>
      <div class="mascot-row">
        <button type="button" class="btn" data-close>Close</button>
      </div>
    </div>`;
    document.body.appendChild(panel);
    panel.addEventListener("click", function (event) {
      if (event.target === panel) close();
    });
    panel.querySelector("[data-close]").addEventListener("click", close);
    panel.querySelector("[data-grid]").addEventListener("click", function (event) {
      const card = event.target.closest("[data-character]");
      if (!card) return;
      save({character: card.getAttribute("data-character")});
    });
    panel.querySelector("[data-enabled]").addEventListener("change", function (event) {
      save({enabled: event.target.checked});
    });
    panel.querySelector("[data-idle]").addEventListener("input", function (event) {
      current.idle_ms = Number(event.target.value);
      panel.querySelector("[data-idle-label]").textContent = (current.idle_ms / 1000).toFixed(1) + " seconds";
    });
    panel.querySelector("[data-idle]").addEventListener("change", function (event) {
      save({idle_ms: Number(event.target.value)});
    });
    ["tone", "size", "side"].forEach(function (name) {
      panel.querySelector("[data-pref='" + name + "']").addEventListener("change", function (event) {
        const patch = {};
        patch[name] = event.target.value;
        save(patch);
      });
    });
    panel.querySelector("[data-save-default]").addEventListener("click", saveDefault);
    return panel;
  }

  function close() {
    if (panel) panel.hidden = true;
  }

  function open() {
    ensure();
    paint();
    panel.hidden = false;
  }

  function fillDefaultSelect() {
    const select = panel && panel.querySelector("[data-workspace]");
    const admin = panel && panel.querySelector("[data-admin]");
    if (!select || !admin) return;
    admin.hidden = !canSetDefault;
    select.innerHTML = characters().map(function (item) {
      return `<option value="${item.id}">${item.name}</option>`;
    }).join("");
    select.value = workspaceDefault;
  }

  async function save(patch) {
    const next = Object.assign({}, current, patch);
    current = next;
    writeLocal(next);
    emit(next);
    if (panel && !panel.hidden) paint();
    if (!root.LeadPilot) return;
    saving = true;
    try {
      const saved = await root.LeadPilot.api("/api/me/preferences", {method: "PUT", body: patch});
      current = saved;
      workspaceDefault = saved.workspace_default || workspaceDefault;
      canSetDefault = !!saved.can_set_default;
      writeLocal(saved);
      emit(saved);
      if (panel && !panel.hidden) { fillDefaultSelect(); paint(); }
    } catch (error) {
      if (root.LeadPilot.toast) root.LeadPilot.toast("Saved in this browser. " + error.message);
    } finally {
      saving = false;
    }
  }

  async function saveDefault() {
    if (!root.LeadPilot || !panel) return;
    const character = panel.querySelector("[data-workspace]").value;
    try {
      const saved = await root.LeadPilot.api("/api/settings/mascot", {method: "PUT", body: {character: character}});
      workspaceDefault = saved.character;
      if (root.LeadPilot.toast) root.LeadPilot.toast("Workspace mascot saved");
      paint();
    } catch (error) {
      if (root.LeadPilot.toast) root.LeadPilot.toast(error.message);
    }
  }

  async function load() {
    const local = readLocal();
    if (local) emit(local);
    if (!root.LeadPilot) return;
    try {
      const data = await root.LeadPilot.api("/api/me/preferences");
      workspaceDefault = data.workspace_default || "hanuman";
      canSetDefault = !!data.can_set_default;
      if (data.explicit) {
        current = data;
        writeLocal(data);
        emit(data);
      } else if (!local && data.character) {
        emit(data);
      }
      ensure();
      fillDefaultSelect();
      const slot = document.getElementById("mascot-default-slot");
      if (slot && canSetDefault) {
        slot.innerHTML = `<div class="row"><label for="mascot-workspace-character">Default character</label>
          <select id="mascot-workspace-character"></select>
          <button class="btn small" type="button" id="mascot-workspace-save">Save default</button></div>`;
        const select = document.getElementById("mascot-workspace-character");
        select.innerHTML = characters().map(function (item) {
          return `<option value="${item.id}">${item.name}</option>`;
        }).join("");
        select.value = workspaceDefault;
        document.getElementById("mascot-workspace-save").addEventListener("click", async function () {
          try {
            const saved = await root.LeadPilot.api("/api/settings/mascot", {method: "PUT", body: {character: select.value}});
            workspaceDefault = saved.character;
            root.LeadPilot.toast("Workspace mascot saved");
          } catch (error) {
            root.LeadPilot.toast(error.message);
          }
        });
      }
    } catch (error) { /* local copy keeps the mascot visible */ }
  }

  function bootButton() {
    const button = document.getElementById("mascot-settings-open");
    if (button) button.addEventListener("click", open);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bootButton);
  else bootButton();

  root.MascotSettings = {readLocal: readLocal, open: open, load: load, save: save, STORAGE_KEY: STORAGE_KEY};
})(window);
