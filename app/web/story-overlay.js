/* Clones the visible page into a fixed layer. The real DOM is left alone. */
(function (root) {
  const CAP = 40;
  const WANT = "article, .card, .story-card, .flash-card, tr, h1, h2, h3, button, img";
  const SKIP = "input, textarea, select, [type=password]";

  function reduced() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function slash(node) {
    const rect = node.getBoundingClientRect();
    const parent = node.parentElement;
    const clips = [
      "polygon(0 0, 100% 0, 62% 100%, 0 70%)",
      "polygon(55% 0, 100% 18%, 100% 100%, 28% 100%)",
      "polygon(20% 30%, 80% 10%, 70% 90%, 10% 80%)",
    ];
    clips.forEach(function (clip, index) {
      const piece = node.cloneNode(true);
      piece.style.clipPath = clip;
      piece.style.left = (rect.left + index * 10) + "px";
      piece.style.top = (rect.top + index * 6) + "px";
      piece.dataset.piece = "1";
      parent.appendChild(piece);
      if (!reduced()) {
        const kick = rect.top + 24 + index * 18;
        requestAnimationFrame(function () { piece.style.top = kick + "px"; piece.style.left = (rect.left + 28 * index) + "px"; });
      }
    });
    const cut = document.createElement("div");
    cut.className = "story-cut";
    cut.style.left = rect.left + "px";
    cut.style.top = (rect.top + rect.height / 2) + "px";
    cut.style.width = rect.width + "px";
    parent.appendChild(cut);
    node.remove();
  }

  function stack(pool) {
    pool.slice(0, 8).forEach(function (node, index) {
      if (!reduced()) node.style.transition = "left 700ms ease, top 700ms ease";
      node.style.left = (72 + index * 34) + "px";
      node.style.top = (window.innerHeight - 86 - index * 16) + "px";
      node.style.width = "70px";
      node.style.height = "28px";
    });
  }

  function juggle(node) {
    if (reduced() || !node) return;
    const start = node.getBoundingClientRect().top;
    const began = performance.now();
    function frame(now) {
      if (!node.isConnected) return;
      const t = (now - began) / 1000;
      if (t > 2.2) return;
      node.style.top = (start - Math.abs(Math.sin(t * 6)) * 64) + "px";
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function capture(doc) {
    const body = doc.body;
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    const layer = doc.createElement("div");
    layer.className = "story-overlay";
    layer.setAttribute("aria-hidden", "true");
    const dim = doc.createElement("div");
    dim.className = "story-dim";
    const clones = doc.createElement("div");
    clones.className = "story-clones";
    const stage = doc.createElement("div");
    stage.className = "story-host";
    layer.append(dim, clones, stage);

    const ranked = Array.from(body.querySelectorAll(WANT)).map(function (node) {
      return { node: node, rect: node.getBoundingClientRect() };
    }).filter(function (item) {
      const rect = item.rect;
      if (rect.width < 24 || rect.height < 16) return false;
      if (rect.bottom < 0 || rect.top > window.innerHeight || rect.right < 0 || rect.left > window.innerWidth) return false;
      if (item.node.closest(".story-overlay, .crew-member, .hanuman")) return false;
      if (item.node.matches(SKIP) || item.node.querySelector(SKIP)) return false;
      return true;
    }).sort(function (a, b) {
      return (b.rect.width * b.rect.height) - (a.rect.width * a.rect.height);
    });

    const chosen = [];
    ranked.forEach(function (item) {
      if (chosen.length >= CAP) return;
      if (chosen.some(function (parent) { return parent.contains(item.node); })) return;
      chosen.push(item.node);
      const copy = item.node.cloneNode(true);
      copy.querySelectorAll("[id]").forEach(function (el) { el.removeAttribute("id"); });
      copy.removeAttribute("id");
      copy.classList.add("story-clone");
      copy.style.position = "fixed";
      copy.style.left = item.rect.left + "px";
      copy.style.top = item.rect.top + "px";
      copy.style.width = item.rect.width + "px";
      copy.style.height = item.rect.height + "px";
      copy.style.margin = "0";
      copy.style.pointerEvents = "none";
      if (item.node.closest("[data-sensitive]") || item.node.hasAttribute("data-sensitive")) copy.style.filter = "blur(6px)";
      clones.appendChild(copy);
    });

    body.appendChild(layer);
    if (window.scrollX !== scrollX || window.scrollY !== scrollY) window.scrollTo(scrollX, scrollY);

    return {
      stage: function () { return stage; },
      count: function () { return chosen.length; },
      interact: function (kind) {
        const pool = Array.from(clones.querySelectorAll(".story-clone")).filter(function (node) { return node.isConnected && !node.dataset.piece; });
        if (!pool.length) return;
        if (kind === "slash") slash(pool[0]);
        else if (kind === "stack") stack(pool);
        else if (kind === "juggle") juggle(pool[0]);
        else if (kind === "sit" && pool[0]) pool[0].classList.add("story-perch");
      },
      dismiss: function () {
        if (!layer.isConnected) return;
        layer.classList.add("story-overlay-out");
        window.setTimeout(function () { layer.remove(); }, 180);
      },
    };
  }

  const api = { capture: capture, CAP: CAP };
  root.StoryOverlay = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
