/* Watches the pointer. After a short pause, asks the mascot to visit. Movement away sends it home. */
(function (root) {
  const MOUSE_IDLE_MS = 2600;
  const TOUCH_IDLE_MS = 8000;
  const DISMISS_PX = 28;
  let mouseIdleMs = MOUSE_IDLE_MS;

  function setMouseIdle(ms) {
    const value = Number(ms);
    if (value >= 1500 && value <= 10000) mouseIdleMs = value;
  }

  function prefersTouch(signals) {
    const info = signals || {};
    if (info.pointerType === "touch" || info.forcedTouch) return true;
    return !!(info.coarse && !info.hover);
  }

  function isMovingToward(prev, next, center) {
    if (!prev || !next || !center) return false;
    const before = Math.hypot(prev.x - center.x, prev.y - center.y);
    const after = Math.hypot(next.x - center.x, next.y - center.y);
    return after + 6 < before;
  }

  function movementDismisses(state) {
    const info = state || {};
    if (!info.idle || info.overMascot || info.towardMascot) return false;
    return info.distance >= DISMISS_PX;
  }

  function anchorNear(x, y, width, height, viewportWidth, viewportHeight) {
    const margin = 8;
    const boxW = width || 112;
    const boxH = height || 140;
    let left = x - boxW - 18;
    let top = y - boxH - 14;
    let flip = false;
    let below = false;
    if (left < margin) {
      left = x + 22;
      flip = true;
    }
    if (top < margin) {
      top = y + 18;
      below = true;
    }
    const maxLeft = Math.max(margin, viewportWidth - boxW - margin);
    const maxTop = Math.max(margin, viewportHeight - boxH - margin);
    left = Math.min(Math.max(margin, left), maxLeft);
    top = Math.min(Math.max(margin, top), maxTop);
    if (left > x) flip = true;
    if (top > y) below = true;
    return {left: Math.round(left), top: Math.round(top), flip: flip, below: below};
  }

  function dockPoint(width, height, viewportWidth, viewportHeight, side) {
    const boxW = width || 112;
    const boxH = height || 140;
    const left = side === "left" ? 12 : Math.max(8, viewportWidth - boxW - 12);
    return {
      left: left,
      top: Math.max(8, viewportHeight - boxH - 12),
    };
  }

  function mediaCoarse() {
    const mq = root.matchMedia;
    if (!mq) return false;
    return prefersTouch({
      coarse: mq("(pointer: coarse)").matches,
      hover: mq("(hover: hover)").matches,
    });
  }

  function overMascot(target) {
    return !!(target && target.closest && target.closest("[data-mascot-root], [data-mascot-show]"));
  }

  function attach(handlers) {
    const hooks = handlers || {};
    let timer = 0;
    let idle = false;
    let idlePoint = null;
    let last = {
      x: root.innerWidth ? root.innerWidth - 24 : 0,
      y: root.innerHeight ? root.innerHeight - 24 : 0,
    };
    let sawPointer = false;
    let touchMode = mediaCoarse();

    function clear() {
      root.clearTimeout(timer);
      timer = 0;
    }

    function delay() {
      return touchMode ? TOUCH_IDLE_MS : mouseIdleMs;
    }

    function arm() {
      clear();
      timer = root.setTimeout(fire, delay());
    }

    function fire() {
      timer = 0;
      idle = true;
      idlePoint = {x: last.x, y: last.y};
      if (hooks.onIdle) {
        hooks.onIdle({x: last.x, y: last.y, touch: touchMode || !sawPointer, fromTap: false});
      }
    }

    function dismiss() {
      if (!idle) return;
      idle = false;
      idlePoint = null;
      if (hooks.onMove) hooks.onMove();
      arm();
    }

    function onPointerMove(event) {
      if (event.pointerType !== "mouse" && event.pointerType !== "pen") return;
      touchMode = false;
      sawPointer = true;
      const next = {x: event.clientX, y: event.clientY};
      if (idle) {
        const center = hooks.center ? hooks.center() : null;
        const toward = isMovingToward(last, next, center);
        const distance = idlePoint ? Math.hypot(next.x - idlePoint.x, next.y - idlePoint.y) : DISMISS_PX;
        last = next;
        if (movementDismisses({
          idle: true,
          overMascot: overMascot(event.target),
          towardMascot: toward,
          distance: distance,
        })) dismiss();
        return;
      }
      last = next;
      arm();
    }

    function onPointerDown(event) {
      if (event.pointerType === "touch") {
        touchMode = true;
        sawPointer = true;
        if (idle && !overMascot(event.target)) dismiss();
        else arm();
        return;
      }
      if (event.pointerType !== "mouse" && event.pointerType !== "pen") return;
      if (idle && !overMascot(event.target)) dismiss();
      else if (!idle) arm();
    }

    function onScroll() {
      if (idle) dismiss();
      else if (sawPointer || touchMode) arm();
    }

    function onKey(event) {
      if (event.key === "Tab") return;
      if (idle) dismiss();
      else if (sawPointer || touchMode) arm();
    }

    document.addEventListener("pointermove", onPointerMove, {passive: true});
    document.addEventListener("pointerdown", onPointerDown, {passive: true});
    root.addEventListener("scroll", onScroll, {passive: true, capture: true});
    document.addEventListener("keydown", onKey);

    if (touchMode) arm();

    return {
      pause: function () { idle = false; idlePoint = null; clear(); },
      arm: arm,
      beginVisit: function (point) {
        idle = true;
        idlePoint = point || {x: last.x, y: last.y};
        clear();
      },
      endVisit: function () {
        idle = false;
        idlePoint = null;
        if (sawPointer || touchMode) arm();
      },
      isTouch: function () { return touchMode; },
      setTouchMode: function (value) { touchMode = !!value; },
      stop: function () {
        clear();
        document.removeEventListener("pointermove", onPointerMove);
        document.removeEventListener("pointerdown", onPointerDown);
        root.removeEventListener("scroll", onScroll, true);
        document.removeEventListener("keydown", onKey);
      },
    };
  }

  const api = {
    MOUSE_IDLE_MS: MOUSE_IDLE_MS,
    TOUCH_IDLE_MS: TOUCH_IDLE_MS,
    setMouseIdle: setMouseIdle,
    mouseIdle: function () { return mouseIdleMs; },
    DISMISS_PX: DISMISS_PX,
    prefersTouch: prefersTouch,
    isMovingToward: isMovingToward,
    movementDismisses: movementDismisses,
    anchorNear: anchorNear,
    dockPoint: dockPoint,
    attach: attach,
  };
  root.MascotIdle = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
