/* Steppers for number fields and an azure sheet for date and time. */
(function () {
  function enhance(root) {
    (root || document).querySelectorAll("input[type='number']:not([data-stepper])").forEach(stepper);
    (root || document).querySelectorAll("input[type='datetime-local']:not([data-azure-date]), input[type='date']:not([data-azure-date]), input[type='time']:not([data-azure-date])").forEach(dateField);
  }

  function stepper(input) {
    if (input.closest(".azure-date")) return;
    input.dataset.stepper = "1";
    const wrap = document.createElement("div");
    wrap.className = "azure-number";
    input.parentNode.insertBefore(wrap, input);
    const minus = document.createElement("button");
    minus.type = "button";
    minus.className = "azure-step";
    minus.textContent = "−";
    minus.setAttribute("aria-label", "Decrease");
    const plus = document.createElement("button");
    plus.type = "button";
    plus.className = "azure-step";
    plus.textContent = "+";
    plus.setAttribute("aria-label", "Increase");
    wrap.append(minus, input, plus);
    function bump(direction) {
      if (direction < 0) input.stepDown();
      else input.stepUp();
      input.dispatchEvent(new Event("input", {bubbles: true}));
      input.dispatchEvent(new Event("change", {bubbles: true}));
    }
    minus.addEventListener("click", () => bump(-1));
    plus.addEventListener("click", () => bump(1));
  }

  function dateField(input) {
    input.dataset.azureDate = "1";
    const wrap = document.createElement("div");
    wrap.className = "azure-select";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    input.classList.add("azure-native");
    const face = document.createElement("button");
    face.type = "button";
    face.className = "azure-face";
    wrap.appendChild(face);
    const menu = document.createElement("div");
    menu.className = "azure-menu azure-sheet";
    menu.hidden = true;
    const parts = input.type === "time" ? ["hour", "minute"] : input.type === "date" ? ["year", "month", "day"] : ["year", "month", "day", "hour", "minute"];
    menu.innerHTML = `<div class="azure-date">${parts.map((part) => `<label>${part}<input type="number" data-part="${part}" data-stepper="1"></label>`).join("")}</div>
      <div class="row"><button type="button" class="btn secondary" data-clear>Clear</button><button type="button" class="btn" data-done>Done</button></div>`;
    document.body.appendChild(menu);
    const field = (part) => menu.querySelector(`[data-part="${part}"]`);
    function paint() {
      face.textContent = input.value ? input.value.replace("T", " ") : "Choose date and time";
    }
    function read() {
      const [date, time] = (input.value || "").split("T");
      const [year, month, day] = (date || "").split("-");
      const [hour, minute] = (time || "").split(":");
      if (field("year")) field("year").value = year || "";
      if (field("month")) field("month").value = month || "";
      if (field("day")) field("day").value = day || "";
      if (field("hour")) field("hour").value = hour || "";
      if (field("minute")) field("minute").value = minute || "";
    }
    function pad(value) { return String(value).padStart(2, "0"); }
    function write() {
      const year = field("year") && field("year").value;
      const month = field("month") && field("month").value;
      const day = field("day") && field("day").value;
      const hour = field("hour") && field("hour").value;
      const minute = field("minute") && field("minute").value;
      if (input.type === "time") input.value = hour && minute ? `${pad(hour)}:${pad(minute)}` : "";
      else if (input.type === "date") input.value = year && month && day ? `${year}-${pad(month)}-${pad(day)}` : "";
      else input.value = year && month && day ? `${year}-${pad(month)}-${pad(day)}T${pad(hour || 0)}:${pad(minute || 0)}` : "";
      input.dispatchEvent(new Event("input", {bubbles: true}));
      input.dispatchEvent(new Event("change", {bubbles: true}));
      paint();
    }
    function place() {
      const mobile = window.innerWidth <= 800 || window.matchMedia("(max-width: 800px)").matches;
      menu.classList.toggle("is-sheet", mobile);
      if (mobile) return;
      const box = face.getBoundingClientRect();
      menu.style.top = (box.bottom + 6) + "px";
      menu.style.left = Math.max(8, box.left) + "px";
      menu.style.width = Math.max(box.width, 280) + "px";
    }
    face.addEventListener("click", () => {
      read();
      menu.hidden = !menu.hidden;
      if (!menu.hidden) place();
    });
    menu.querySelector("[data-done]").addEventListener("click", () => { write(); menu.hidden = true; });
    menu.querySelector("[data-clear]").addEventListener("click", () => { input.value = ""; paint(); menu.hidden = true; });
    input.addEventListener("change", paint);
    paint();
  }

  function boot() { enhance(document); }
  if (document.body) boot();
  new MutationObserver(() => enhance(document)).observe(document.documentElement, {childList: true, subtree: true});
  window.AzureControls = {enhance};
})();
