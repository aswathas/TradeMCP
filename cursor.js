/* TradeMCP showcase — "The Touch".

   WHAT THIS IS
   A fountain-pen nib drawn in code that takes the place of the browser
   arrow, plus the one effect it drives: a panel you point at is
   transfigured — the hard rule softens into an organic seam and the box
   lifts a hair off the page. That is Mahito's Idle Transfiguration, where
   the shape of the soul decides the shape of the body.

   WHAT YOU SEE, AND WHERE IT COMES FROM
   - The nib follows the pointer with weight, dragging a fading ink smear.
       cursor.js tracks the pointer and lerps toward it.
   - Over a link or button a ring opens with four focus ticks.
       cursor.js adds .is-target when the element under the pointer is
       interactive; the ring also answers to CSS :has() on its own.
   - Over a panel the panel softens and lifts.
       Pure CSS :hover in styles.css — no script involved, so it works even
       where pointer events never reach the page.
   - Over a text field the nib steps aside so the caret stays readable.
       cursor.js adds .is-text and the caret keeps the browser's own cursor.

   RULES THIS FILE KEEPS
   - The native arrow is only given up on the FIRST real pointer move, and
     handed straight back when the pointer leaves the window. If this script
     never runs, the visitor still has the browser's own cursor.
   - Touch devices, reduced motion and ?cursor=system keep the native cursor.
   - The caret in a text field is never covered.
   - One rAF loop drives everything, and it parks itself when the pointer rests.

   TWO LESSONS ARE BAKED IN, because both cost the first build:
   - The mark must be shown on EVERY pointer move, not only on the first one.
     A mark shown once and hidden on a leave event leaves the visitor with no
     cursor at all, because the native arrow has already been hidden.
   - The mark is hidden when the pointer leaves the WINDOW, not when it leaves
     an element. Chromium fires pointerleave on the document for every element
     boundary the pointer crosses, so listening for it there hides the mark
     every time the reader moves from one thing to the next.
*/

(function () {
  "use strict";

  const doc = document;
  const root = doc.documentElement;
  const params = new URLSearchParams(location.search);

  /* ---------- the gate ------------------------------------------------------
     Every one of these has to pass before the native cursor is given up. */
  if (params.get("cursor") === "system") return;
  if (params.get("flat") === "1") return;                 // still capture wants the native pointer
  if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  /* One mark, one set of ears. A second copy of this file would fight the
     first one over the is-touched class and blank the mark. */
  if (doc.querySelector(".cursor")) return;

  const INTERACTIVE = [
    "a", "button", "summary", "label[for]",
    '[role="button"]', '[role="tab"]',
    ".tool", ".preset", ".theme-toggle", ".domain-toggle__btn",
  ].join(", ");

  const TOUCHABLE = ".panel, .tool, .metric-panel, .step, .source, .call__board";
  const TEXTUAL = "input, textarea, select, [contenteditable]";

  /* ---------- the mark ------------------------------------------------------ */
  const layer = doc.createElement("div");
  layer.className = "cursor";
  layer.setAttribute("aria-hidden", "true");
  layer.innerHTML = [
    '<span class="cursor__trail"></span>',
    '<span class="cursor__nib">',
    '  <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false">',
    '    <path class="cursor__nib-body" d="M5.8 22 L8.7 4.2 L15.3 4.2 L18.2 22 Z"></path>',
    '    <path class="cursor__nib-slit" d="M12 21.6 L12 12.4"></path>',
    '    <circle class="cursor__nib-hole" cx="12" cy="9.8" r="1.45"></circle>',
    '    <path class="cursor__nib-tip" d="M12 22 L9.9 15 L14.1 15 Z"></path>',
    "  </svg>",
    "</span>",
    '<span class="cursor__ring"></span>',
  ].join("");
  doc.body.appendChild(layer);

  const trail = layer.querySelector(".cursor__trail");

  /* ---------- state --------------------------------------------------------- */
  const target = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
  const pos = { x: target.x, y: target.y };
  const lag = { x: target.x, y: target.y };
  let angle = 0;
  let raf = 0;
  let running = false;

  let touched = null;    // the element currently being transfigured
  let lastTarget = null; // the element the pointer is over

  /* ---------- movement ------------------------------------------------------ */
  function onMove(event) {
    target.x = event.clientX;
    target.y = event.clientY;

    /* The mark is shown on every move. If it is ever hidden by anything else,
       the next move brings it straight back. */
    layer.classList.add("is-on");

    /* The native arrow is given up only now, on the first real pointer move.
       Until this point the visitor still has the browser's own cursor, so a
       page where pointer events never arrive is still perfectly usable. */
    root.classList.add("has-cursor");

    if (!running) {
      // First sighting: do not sweep in from the middle of the screen.
      pos.x = lag.x = target.x;
      pos.y = lag.y = target.y;
      write();
      start();
    }
    classify(event.target, event);
  }
  function start() {
    if (running) return;
    running = true;
    raf = requestAnimationFrame(step);
  }

  function stop() {
    running = false;
    cancelAnimationFrame(raf);
  }

  function step() {
    if (!running) return;

    const dx = target.x - pos.x;
    const dy = target.y - pos.y;
    const dist = Math.hypot(dx, dy);

    if (dist < 0.4) {
      // At rest. Park the loop; the next pointermove wakes it.
      pos.x = target.x;
      pos.y = target.y;
      lag.x = target.x;
      lag.y = target.y;
      write();
      running = false;
      return;
    }

    pos.x += dx * 0.35;
    pos.y += dy * 0.35;
    lag.x += (pos.x - lag.x) * 0.18;
    lag.y += (pos.y - lag.y) * 0.18;

    if (Math.abs(pos.x - lag.x) > 0.2 || Math.abs(pos.y - lag.y) > 0.2) {
      angle = Math.atan2(pos.y - lag.y, pos.x - lag.x);
    }

    write();
    raf = requestAnimationFrame(step);
  }

  function write() {
    layer.style.transform = `translate3d(${pos.x.toFixed(2)}px, ${pos.y.toFixed(2)}px, 0)`;

    const smear = Math.hypot(pos.x - lag.x, pos.y - lag.y);
    const reach = Math.min(smear * 6, 26);
    trail.style.transform = `translate3d(${lag.x.toFixed(2)}px, ${lag.y.toFixed(2)}px, 0) rotate(${angle.toFixed(3)}rad) scaleX(${(0.35 + reach / 34).toFixed(3)})`;
    trail.style.opacity = Math.min(smear * 0.9, 0.75).toFixed(3);
  }

  /* ---------- what is under the pointer ------------------------------------- */
  function classify(node, event) {
    if (!(node instanceof Element)) return;

    const el = node.closest(INTERACTIVE);
    if (el !== lastTarget) {
      lastTarget = el;
      layer.classList.toggle("is-target", Boolean(el));
    }

    /* the caret wins: a text field keeps its own cursor and the nib steps aside */
    if (node.closest(TEXTUAL)) {
      layer.classList.add("is-text");
      clearTouch();
      return;
    }
    layer.classList.remove("is-text");

    const hit = node.closest(TOUCHABLE);
    if (hit !== touched) {
      clearTouch();
      if (hit) {
        touched = hit;
        touched.classList.add("is-touched");
      }
    }

    /* the angle follows the pointer for as long as the touch lasts */
    if (touched && event) aim(touched, event);
  }

  function aim(el, event) {
    const rect = el.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    el.style.setProperty("--touch-x", `${(-y * 2).toFixed(2)}deg`);
    el.style.setProperty("--touch-y", `${(x * 2).toFixed(2)}deg`);
  }

  function clearTouch() {
    if (touched) {
      touched.classList.remove("is-touched");
      touched.style.removeProperty("--touch-x");
      touched.style.removeProperty("--touch-y");
      touched = null;
    }
  }

  /* ---------- press --------------------------------------------------------- */
  function onDown(event) {
    layer.classList.add("is-press");
    if (event.target instanceof Element) {
      const el = event.target.closest(INTERACTIVE);
      if (el) el.classList.add("is-hit");
    }
  }

  function onUp() {
    layer.classList.remove("is-press");
    layer.querySelectorAll(".is-hit").forEach((el) => el.classList.remove("is-hit"));
  }

  /* ---------- the pointer leaves the window ---------------------------------
     Only this hides the mark. A pointer that crosses from one element to the
     next is still over the page, and the mark must survive that. */
  function hide() {
    layer.classList.remove("is-on", "is-target", "is-text");
    /* Off the page means the native arrow comes back. The visitor can always
       point at something outside the window. */
    root.classList.remove("has-cursor");
    clearTouch();
    onUp();
    stop();
  }

  doc.addEventListener("pointermove", onMove, { passive: true });
  /* Some embedded surfaces deliver mouse events but not pointer events. The
     handler is idempotent, so hearing both costs nothing. */
  doc.addEventListener("mousemove", onMove, { passive: true });
  doc.addEventListener("pointerdown", onDown, { passive: true });
  doc.addEventListener("pointerup", onUp, { passive: true });
  doc.addEventListener("pointercancel", onUp, { passive: true });

  /* relatedTarget is null only when the pointer really left the window. */
  const leave = (event) => {
    if (event.relatedTarget === null) hide();
  };
  root.addEventListener("pointerleave", leave, { passive: true });
  root.addEventListener("mouseleave", leave, { passive: true });
  root.addEventListener("pointerenter", () => layer.classList.add("is-on"), { passive: true });

  window.addEventListener("blur", hide);
  doc.addEventListener("visibilitychange", () => {
    if (doc.hidden) hide();
  });

  /* ---------- handover ------------------------------------------------------
     The mark is built and listening. The native cursor is not touched here —
     it is handed over by the first pointer move, and handed back when the
     pointer leaves the window. */
  layer.dataset.ready = "1";
})();
