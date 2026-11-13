/* Renders search dropdowns, preset chips, and keyword suggestions. */
(function () {
  const { $, api, esc, can, toast } = window.LeadPilot;
  const templates = { saved: [], ai: [], edit: [], icp: [] };
  const built = {};
  let catalog = null;

  function choices(prefix, key, label, items, includeAny) {
    const options = [];
    if (includeAny) options.push(`<option value="">Any</option>`);
    items.forEach((item) => {
      const value = typeof item === "string" ? item : item.value;
      const text = typeof item === "string" ? item : item.label;
      options.push(`<option value="${esc(value)}">${esc(text)}</option>`);
    });
    return `<div class="field"><label>${esc(label)}</label><select id="${prefix}-${key}">${options.join("")}</select></div>`;
  }

  function statePicker(prefix) {
    const boxes = [`<label><input type="checkbox" data-any="1" checked> Any</label>`].concat(
      catalog.options.us_states.map((name) => `<label><input type="checkbox" value="${esc(name)}"> ${esc(name)}</label>`)
    );
    return `<div class="field" id="${prefix}-state-field"><label>US state</label><details class="multi" id="${prefix}-states-wrap"><summary id="${prefix}-states-label">Any</summary><div class="multi-list">${boxes.join("")}</div></details></div>`;
  }

  function cityField(prefix) {
    const cities = catalog.options.cities.map((city) => `<option value="${esc(city)}"></option>`).join("");
    return `<div class="field"><label>City</label><input id="${prefix}-city" list="${prefix}-cities" placeholder="Optional" autocomplete="off"><datalist id="${prefix}-cities">${cities}</datalist></div>`;
  }

  function keywordField(prefix) {
    return `<div class="field suggest"><label>Keywords</label><input id="${prefix}-keywords" autocomplete="off" placeholder="staffing services, agencies welcome"><div class="suggest-list" id="${prefix}-suggest" hidden></div></div>`;
  }

  function render(prefix, host) {
    const options = catalog.options;
    host.innerHTML = `<div class="split3">
      ${choices(prefix, "country", "Country", options.countries, false)}
      ${statePicker(prefix)}
      ${cityField(prefix)}
      ${choices(prefix, "opportunity", "Opportunity type", options.opportunity_types, true)}
      ${choices(prefix, "buyer", "Buyer type", options.buyer_types, true)}
      ${choices(prefix, "role", "Role category", options.role_categories, true)}
      ${choices(prefix, "industry", "Industry", options.industries, true)}
      ${choices(prefix, "size", "Company size", options.company_sizes, true)}
      ${choices(prefix, "window", "Posted / due", options.posted_windows, true)}
      ${choices(prefix, "score", "Minimum score", options.min_scores, true)}
    </div>${keywordField(prefix)}`;
    bindStates(prefix);
    bindCountry(prefix);
    bindKeywords(prefix);
    host.addEventListener("change", () => preview(prefix));
  }

  function bindCountry(prefix) {
    $(prefix + "-country").addEventListener("change", () => {
      const united = $(prefix + "-country").value === "United States";
      $(prefix + "-state-field").hidden = !united;
      if (!united) setStates(prefix, []);
      preview(prefix);
    });
  }

  function bindStates(prefix) {
    const wrap = $(prefix + "-states-wrap");
    wrap.addEventListener("change", (event) => {
      const boxes = [...wrap.querySelectorAll("input")];
      const any = boxes.find((box) => box.dataset.any);
      if (event.target === any && any.checked) boxes.forEach((box) => { if (box !== any) box.checked = false; });
      else if (event.target !== any && event.target.checked) any.checked = false;
      if (!boxes.some((box) => box.checked)) any.checked = true;
      $(prefix + "-states-label").textContent = stateLabel(prefix);
      preview(prefix);
    });
  }

  function stateLabel(prefix) {
    const picked = selectedStates(prefix);
    if (!picked.length) return "Any";
    if (picked.length === 1) return picked[0];
    return picked.length + " states";
  }

  function selectedStates(prefix) {
    const wrap = $(prefix + "-states-wrap");
    if (!wrap) return [];
    return [...wrap.querySelectorAll("input")].filter((box) => box.checked && !box.dataset.any).map((box) => box.value);
  }

  function setStates(prefix, names) {
    const wrap = $(prefix + "-states-wrap");
    const wanted = new Set(names || []);
    const boxes = [...wrap.querySelectorAll("input")];
    const any = boxes.find((box) => box.dataset.any);
    boxes.forEach((box) => { if (!box.dataset.any) box.checked = wanted.has(box.value); });
    any.checked = wanted.size === 0;
    $(prefix + "-states-label").textContent = stateLabel(prefix);
  }

  function setValue(id, value) {
    const node = $(id);
    if (node) node.value = value || "";
  }

  function apply(prefix, data) {
    setValue(prefix + "-country", data.country || "United States");
    setValue(prefix + "-opportunity", data.opportunity_type || "");
    setValue(prefix + "-buyer", data.buyer_type || "");
    setValue(prefix + "-role", data.role_category || "");
    setValue(prefix + "-industry", data.industry || "");
    setValue(prefix + "-size", data.company_size || "");
    setValue(prefix + "-window", data.posted_window || "");
    setValue(prefix + "-score", data.min_score == null ? "" : String(data.min_score));
    setValue(prefix + "-city", data.city || "");
    setValue(prefix + "-keywords", data.keywords || "");
    setStates(prefix, data.states || []);
    templates[prefix] = data.query_templates || [];
    const united = (data.country || "United States") === "United States";
    const stateField = $(prefix + "-state-field");
    if (stateField) stateField.hidden = !united;
    preview(prefix);
  }

  function payload(prefix) {
    const read = (key) => ($(prefix + "-" + key) ? $(prefix + "-" + key).value : "");
    const body = {
      country: read("country"),
      states: selectedStates(prefix),
      city: read("city"),
      opportunity_type: read("opportunity"),
      buyer_type: read("buyer"),
      role_category: read("role"),
      industry: read("industry"),
      company_size: read("size"),
      posted_window: read("window"),
      min_score: read("score"),
      keywords: read("keywords"),
      query_templates: templates[prefix] || [],
    };
    if (prefix === "saved") {
      body.name = $("s-name").value;
      body.results_limit = Number($("s-limit").value || 10);
    }
    return body;
  }

  async function preview(prefix) {
    const targetId = prefix === "ai" ? "ai-query-preview" : prefix === "saved" ? "saved-query-preview" : "";
    const target = targetId ? $(targetId) : null;
    if (!target || !built[prefix]) return;
    try {
      const data = await api("/api/search/preview", {method: "POST", body: payload(prefix)});
      target.textContent = data.query ? "Search text: " + data.query : "";
    } catch (error) {
      target.textContent = "";
    }
  }

  function bindKeywords(prefix) {
    const input = $(prefix + "-keywords");
    const list = $(prefix + "-suggest");
    let timer = 0;
    input.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        try {
          const data = await api("/api/search/suggestions?q=" + encodeURIComponent(input.value));
          list.innerHTML = (data.suggestions || []).map((item) => `<button type="button">${esc(item)}</button>`).join("");
          list.hidden = !(data.suggestions || []).length;
          list.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => {
            input.value = button.textContent;
            list.hidden = true;
            preview(prefix);
          }));
        } catch (error) {
          list.hidden = true;
        }
      }, 180);
    });
    input.addEventListener("keydown", (event) => { if (event.key === "Escape") list.hidden = true; });
    input.addEventListener("blur", () => setTimeout(() => { list.hidden = true; }, 200));
  }

  function renderChips(prefix, host) {
    if (!host) return;
    host.innerHTML = (catalog.presets || []).map((preset) => `<button type="button" class="chip" data-id="${preset.id}">${esc(preset.label)}</button>`).join("");
    host.querySelectorAll(".chip").forEach((button) => button.addEventListener("click", () => {
      host.querySelectorAll(".chip").forEach((item) => item.classList.toggle("active", item === button));
      const preset = catalog.presets.find((item) => String(item.id) === button.dataset.id);
      if (!preset) return;
      apply(prefix, preset);
      if (prefix === "ai") $("ai-text").value = preset.ai_text || preset.label;
      if (prefix === "saved") $("s-name").value = preset.label;
      preview(prefix);
    }));
  }

  function ensure(prefix, host) {
    if (!host || built[prefix]) return;
    render(prefix, host);
    built[prefix] = true;
  }

  async function loadCatalog() {
    catalog = await api("/api/search/presets");
    return catalog;
  }

  async function refresh() {
    await loadCatalog();
    ensure("ai", $("ai-criteria-fields"));
    ensure("saved", $("saved-criteria-fields"));
    renderChips("ai", $("ai-preset-chips"));
    renderChips("saved", $("saved-preset-chips"));
    if (!refresh.seeded) {
      apply("ai", catalog.defaults || {});
      apply("saved", catalog.defaults || {});
      refresh.seeded = true;
    }
  }

  async function mountSettings(settings) {
    if (!catalog) await loadCatalog();
    const host = $("icp-fields");
    ensure("icp", host);
    apply("icp", {
      country: settings.icp_country,
      states: settings.icp_states || [],
      city: settings.icp_city,
      opportunity_type: settings.icp_opportunity_type,
      buyer_type: settings.icp_buyer_type,
      role_category: settings.icp_role_category,
      industry: settings.icp_industry,
      company_size: settings.icp_company_size,
      posted_window: settings.icp_posted_window,
      min_score: settings.icp_min_score,
      keywords: settings.icp_keywords,
      query_templates: [],
    });
    await mountAdmin();
  }

  function icpPayload() {
    const data = payload("icp");
    return {
      icp_country: data.country,
      icp_states: data.states,
      icp_city: data.city,
      icp_opportunity_type: data.opportunity_type,
      icp_buyer_type: data.buyer_type,
      icp_role_category: data.role_category,
      icp_industry: data.industry,
      icp_company_size: data.company_size,
      icp_posted_window: data.posted_window,
      icp_min_score: data.min_score,
      icp_keywords: data.keywords,
    };
  }

  function fillEditor(preset) {
    $("edit-label").value = preset ? preset.label : "";
    $("edit-ai").value = preset ? preset.ai_text : "";
    $("edit-templates").value = preset ? (preset.query_templates || []).join("\n") : "";
    $("preset-delete").hidden = !preset;
    apply("edit", preset || catalog.defaults || {});
  }

  async function mountAdmin() {
    const editor = $("preset-editor");
    if (!editor) return;
    if (!can("settings", true)) {
      editor.innerHTML = `<p class="muted">Only an Admin can change presets.</p>`;
      return;
    }
    if (!catalog) await loadCatalog();
    const current = $("preset-pick") ? $("preset-pick").value : "";
    editor.innerHTML = `<div class="field"><label>Preset</label><select id="preset-pick"><option value="">New preset</option>${catalog.presets.map((preset) => `<option value="${preset.id}">${esc(preset.label)}</option>`).join("")}</select></div>
      <div class="field"><label>Chip label</label><input id="edit-label" placeholder="Open US staffing RFPs"></div>
      <div class="field"><label>AI search text</label><textarea id="edit-ai"></textarea></div>
      <div class="field"><label>Query templates</label><textarea id="edit-templates" placeholder="One search per line"></textarea></div>
      <div id="edit-criteria-fields"></div>
      <div class="row"><button class="btn" type="button" id="preset-save">Save preset</button><button class="btn danger" type="button" id="preset-delete" hidden>Delete</button></div>`;
    built.edit = false;
    ensure("edit", $("edit-criteria-fields"));
    $("preset-pick").value = current;
    $("preset-pick").addEventListener("change", () => {
      const preset = catalog.presets.find((item) => String(item.id) === $("preset-pick").value);
      fillEditor(preset || null);
    });
    $("preset-save").addEventListener("click", saveEditor);
    $("preset-delete").addEventListener("click", deleteEditor);
    const selected = catalog.presets.find((item) => String(item.id) === current);
    fillEditor(selected || null);
  }

  async function saveEditor() {
    templates.edit = $("edit-templates").value.split("\n").map((line) => line.trim()).filter(Boolean);
    const body = payload("edit");
    body.label = $("edit-label").value;
    body.ai_text = $("edit-ai").value;
    body.query_templates = templates.edit;
    const id = $("preset-pick").value;
    try {
      if (id) await api("/api/search/presets/" + id, {method: "PUT", body});
      else await api("/api/search/presets", {method: "POST", body});
      toast("Preset saved");
      await loadCatalog();
      renderChips("ai", $("ai-preset-chips"));
      renderChips("saved", $("saved-preset-chips"));
      await mountAdmin();
    } catch (error) { toast(error.message); }
  }

  async function deleteEditor() {
    const id = $("preset-pick").value;
    if (!id || !confirm("Delete this preset?")) return;
    try {
      await api("/api/search/presets/" + id, {method: "DELETE"});
      toast("Preset deleted");
      await loadCatalog();
      renderChips("ai", $("ai-preset-chips"));
      renderChips("saved", $("saved-preset-chips"));
      await mountAdmin();
    } catch (error) { toast(error.message); }
  }

  window.SearchForm = { refresh, payload, mountSettings, icpPayload, mountAdmin };
})();
