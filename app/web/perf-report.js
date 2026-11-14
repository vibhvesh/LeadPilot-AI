/* Sends browser errors to the signed-in error log. It never reports its own failed posts. */
(function () {
  let sent = 0;

  function report(message, stack) {
    if (sent > 8) return;
    sent += 1;
    const body = JSON.stringify({
      message: String(message || "Browser error").slice(0, 500),
      stack: String(stack || "").slice(0, 4000),
      path: location.pathname,
    });
    fetch("/api/client-errors", {
      method: "POST",
      credentials: "same-origin",
      headers: {"Content-Type": "application/json"},
      body: body,
    }).catch(function () { /* the page stays up if the log is unreachable */ });
  }

  window.addEventListener("error", function (event) {
    report(event.message, event.error && event.error.stack);
  });
  window.addEventListener("unhandledrejection", function (event) {
    const reason = event.reason;
    const message = reason && reason.message ? reason.message : String(reason || "Unhandled rejection");
    report(message, reason && reason.stack);
  });
})();
