/* Themed confirmation in place of window.confirm. */
(function () {
  function confirm(message, options) {
    const settings = options || {};
    return new Promise((resolve) => {
      const root = document.createElement("div");
      root.className = "azure-dialog";
      root.innerHTML = `<div class="azure-dialog-card" role="alertdialog" aria-modal="true" aria-labelledby="azure-dialog-title">
        <h2 id="azure-dialog-title">${settings.title || "Please confirm"}</h2>
        <p></p>
        <div class="row">
          <button type="button" class="btn secondary" data-no>Cancel</button>
          <button type="button" class="btn ${settings.danger === false ? "" : "danger"}" data-yes>${settings.confirmLabel || "Confirm"}</button>
        </div>
      </div>`;
      root.querySelector("p").textContent = String(message || "");
      function finish(value) {
        document.removeEventListener("keydown", onKey);
        root.remove();
        resolve(value);
      }
      function onKey(event) {
        if (event.key === "Escape") finish(false);
        if (event.key === "Enter") finish(true);
      }
      root.addEventListener("click", (event) => {
        if (event.target === root) finish(false);
      });
      root.querySelector("[data-no]").addEventListener("click", () => finish(false));
      root.querySelector("[data-yes]").addEventListener("click", () => finish(true));
      document.addEventListener("keydown", onKey);
      document.body.appendChild(root);
      root.querySelector("[data-yes]").focus();
    });
  }

  window.AzureDialog = {confirm};
})();
