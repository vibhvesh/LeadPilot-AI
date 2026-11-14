/* Builds app links for public posts. Opening a link never posts, likes, or signs in. */
(function (root) {
  const FALLBACK_MS = 1500;

  function device(env) {
    const info = env || {};
    const ua = String(info.ua || (typeof navigator !== "undefined" ? navigator.userAgent : ""));
    const android = /Android/i.test(ua);
    const ios = /iPhone|iPad|iPod/i.test(ua);
    return {android: android, ios: ios, mobile: android || ios};
  }

  function parse(url) {
    try {
      const parsed = new URL(url);
      if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
      return parsed;
    } catch (error) {
      return null;
    }
  }

  function host(parsed) {
    return parsed.hostname.replace(/^www\./i, "").toLowerCase();
  }

  function xStatusId(parsed) {
    const name = host(parsed);
    if (name !== "x.com" && name !== "twitter.com" && name !== "mobile.twitter.com") return "";
    const match = parsed.pathname.match(/\/status\/(\d+)/);
    return match ? match[1] : "";
  }

  function isLinkedIn(parsed) {
    return host(parsed) === "linkedin.com" || host(parsed).endsWith(".linkedin.com");
  }

  function isFacebook(parsed) {
    const name = host(parsed);
    return name === "facebook.com" || name.endsWith(".facebook.com") || name === "fb.com" || name === "fb.me" || name.endsWith(".fb.com");
  }

  function isDice(parsed) {
    const name = host(parsed);
    return name === "dice.com" || name.endsWith(".dice.com");
  }

  function intent(scheme, path, packageName, https) {
    return "intent://" + path + "#Intent;scheme=" + scheme + ";package=" + packageName + ";S.browser_fallback_url=" + encodeURIComponent(https) + ";end";
  }

  function httpsPath(parsed) {
    return parsed.host + (parsed.pathname || "/") + parsed.search;
  }

  function build(url, env) {
    const https = String(url || "");
    const parsed = parse(https);
    const where = device(env);
    const web = {https: https, app: "", mode: "web", fallbackMs: 0, target: "_blank"};
    if (!parsed) return web;
    if (!where.mobile) return web;
    const statusId = xStatusId(parsed);
    if (statusId) {
      if (where.android) {
        return {https: https, app: intent("twitter", "status?id=" + statusId, "com.twitter.android", https), mode: "intent", fallbackMs: 0, target: ""};
      }
      return {https: https, app: "twitter://status?id=" + statusId, mode: "scheme", fallbackMs: FALLBACK_MS, target: ""};
    }
    if (isLinkedIn(parsed)) {
      const path = parsed.pathname.replace(/^\//, "") + parsed.search;
      if (where.android) {
        return {https: https, app: intent("https", httpsPath(parsed), "com.linkedin.android", https), mode: "intent", fallbackMs: 0, target: ""};
      }
      return {https: https, app: "linkedin://" + path, mode: "scheme", fallbackMs: FALLBACK_MS, target: ""};
    }
    if (isFacebook(parsed)) {
      return {https: https, app: "fb://facewebmodal/f?href=" + encodeURIComponent(https), mode: "scheme", fallbackMs: FALLBACK_MS, target: ""};
    }
    if (isDice(parsed) && where.android) {
      return {https: https, app: intent("https", httpsPath(parsed), "com.dice.app", https), mode: "intent", fallbackMs: 0, target: ""};
    }
    return web;
  }

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[ch];
    });
  }

  function anchor(url, text, env) {
    const plan = build(url, env);
    if (plan.mode === "intent") {
      return '<a href="' + esc(plan.app) + '">' + esc(text) + "</a>";
    }
    if (plan.mode === "scheme") {
      return '<a href="' + esc(plan.https) + '" data-deeplink="' + esc(plan.app) + '" data-fallback="' + esc(plan.https) + '" data-fallback-ms="' + plan.fallbackMs + '">' + esc(text) + "</a>";
    }
    return '<a href="' + esc(plan.https) + '" target="_blank" rel="noopener noreferrer">' + esc(text) + "</a>";
  }

  function open(url, env) {
    const plan = build(url, env);
    if (plan.mode === "web") {
      if (typeof window !== "undefined") window.open(plan.https, "_blank", "noopener");
      return plan;
    }
    if (plan.mode === "intent") {
      if (typeof window !== "undefined") window.location.href = plan.app;
      return plan;
    }
    if (typeof window === "undefined" || typeof document === "undefined") return plan;
    const timer = window.setTimeout(function () {
      if (!document.hidden) window.location.href = plan.https;
    }, plan.fallbackMs || FALLBACK_MS);
    function cancel() {
      if (!document.hidden) return;
      window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", cancel);
    }
    document.addEventListener("visibilitychange", cancel);
    window.location.href = plan.app;
    return plan;
  }

  function onClick(event) {
    const link = event.target && event.target.closest ? event.target.closest("[data-deeplink]") : null;
    if (!link) return;
    event.preventDefault();
    open(link.getAttribute("data-fallback") || link.href);
  }

  if (typeof document !== "undefined") {
    document.addEventListener("click", onClick);
  }

  const api = {FALLBACK_MS: FALLBACK_MS, build: build, anchor: anchor, open: open, device: device};
  root.DeepLink = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
