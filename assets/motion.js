/* ==========================================================================
   Olivet — motion.js  →  window.Olivet.motion
   Springs, momentum and gestures, after Apple's "Designing Fluid Interfaces"
   (skills/apple-design §3–§10), on the Web Animations API.

   - spring({ duration, bounce, velocity }) → { easing: 'linear(...)', duration }
       Apple's two-parameter model: duration = response (s), bounce = 1 − damping ratio.
       The curve is the exact damped-oscillator solution, sampled into CSS linear().
   - animate(el, { from, to }, opts) → Promise
       Starts from the element's CURRENT on-screen value when `from` is omitted,
       so an interrupted animation reverses without a jump. Commits the end value.
   - project(velocity, decelerationRate) → distance a flick will travel
   - rubberband(overshoot, dimension, constant) → resisted offset past a bound
   - SheetGesture: drag a sheet 1:1 (from its handle, or on touch from content
       scrolled to the top), catch it mid-flight, release with velocity
       handoff, flick to dismiss.
   ========================================================================== */
(() => {
  const Olivet = (window.Olivet = window.Olivet || {});
  if (Olivet.motion) return;

  const reduced = () => window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const TAU = Math.PI * 2;

  /* ---------- spring curve ----------
     x(t): progress from 0 to 1. y = x − 1 is the displacement from rest.
     ω0 = 2π / response, ζ = 1 − bounce. Initial velocity v0 in progress units / s. */
  function springPosition(t, w0, zeta, v0) {
    if (zeta < 1) {
      const wd = w0 * Math.sqrt(1 - zeta * zeta);
      const A = -1;
      const B = (v0 + zeta * w0 * A) / wd;
      return 1 + Math.exp(-zeta * w0 * t) * (A * Math.cos(wd * t) + B * Math.sin(wd * t));
    }
    // critically damped
    const A = -1;
    const B = v0 + w0 * A;
    return 1 + (A + B * t) * Math.exp(-w0 * t);
  }

  const cache = new Map();
  function spring({ duration = 0.5, bounce = 0, velocity = 0 } = {}) {
    const response = Math.max(0.05, duration);
    const zeta = Math.min(1, Math.max(0.05, 1 - Math.max(0, bounce)));
    const v0 = Number.isFinite(velocity) ? Math.max(-40, Math.min(40, velocity)) : 0;
    const key = `${response.toFixed(3)}|${zeta.toFixed(3)}|${v0.toFixed(2)}`;
    if (cache.has(key)) return cache.get(key);

    const w0 = TAU / response;
    // Settle time: first moment after which the oscillation stays within 0.1%
    const dt = 1 / 120;
    let settle = response * 3;
    let lastOutside = 0;
    for (let t = 0; t < response * 4; t += dt) {
      if (Math.abs(springPosition(t, w0, zeta, v0) - 1) > 0.002) lastOutside = t; // <1px on a 420px sheet
    }
    settle = Math.min(response * 4, Math.max(response * 0.6, lastOutside + dt));

    const samples = Math.min(120, Math.max(24, Math.ceil(settle * 60)));
    const points = [];
    for (let i = 0; i <= samples; i++) {
      const t = (settle * i) / samples;
      const x = i === samples ? 1 : springPosition(t, w0, zeta, v0);
      points.push(Math.round(x * 10000) / 10000);
    }
    const result = { easing: `linear(${points.join(', ')})`, duration: Math.round(settle * 1000) };
    cache.set(key, result);
    return result;
  }

  /* ---------- animate ---------- */
  const running = new WeakMap();

  function currentValue(el, property) {
    const cs = getComputedStyle(el);
    return property === 'transform' ? cs.transform : cs.getPropertyValue(property);
  }

  function animate(el, { from, to }, { duration = 0.5, bounce = 0, velocity = 0, property = 'transform', commit = true } = {}) {
    if (!el) return Promise.resolve(false);
    // Read the presentation value BEFORE cancelling: it includes the running animation.
    const start = from !== undefined ? from : currentValue(el, property);
    const previous = running.get(el);
    if (previous) previous.cancel();

    if (commit) el.style[property] = to;

    if (reduced() && property === 'transform') {
      running.delete(el);
      return Promise.resolve(true);
    }

    const { easing, duration: ms } = spring({ duration, bounce, velocity });
    if (!el.animate) return Promise.resolve(true);
    const anim = el.animate([{ [property]: start }, { [property]: to }], { duration: ms, easing, fill: commit ? 'none' : 'forwards' });
    running.set(el, anim);
    return new Promise((resolve) => {
      anim.onfinish = () => {
        if (running.get(el) === anim) running.delete(el);
        resolve(true);
      };
      anim.oncancel = () => resolve(false);
    });
  }

  function stop(el) {
    const anim = running.get(el);
    if (!anim) return;
    const value = getComputedStyle(el).transform;
    anim.cancel();
    el.style.transform = value;
    running.delete(el);
  }

  /* ---------- momentum & boundaries (apple-design §6, §9) ---------- */
  const project = (velocity, decelerationRate = 0.998) => ((velocity / 1000) * decelerationRate) / (1 - decelerationRate);

  const rubberband = (overshoot, dimension, constant = 0.55) =>
    (overshoot * dimension * constant) / (dimension + constant * Math.abs(overshoot));

  /* ---------- sheet gesture ----------
     A drag starts on a handle (touch-action: none there) or, on a bottom
     sheet with touch/pen, on the content when every scroller under the finger
     is at its top (APPLE-SPEC §3/§4). That content pull is decided on the
     first clear move: downward claims it for the sheet, and the panel's
     non-passive touchmove listener cancels the browser's pan; upward or
     sideways is left to native scrolling. Offset is measured along the
     dismiss direction: 0 = open, size = closed. */
  const NOT_DRAGGABLE = 'input, select, textarea, [contenteditable]:not([contenteditable="false"])';

  class SheetGesture {
    constructor(panel, { axis, dismissDirection, onDrag, onRelease, onDismiss, enabled } = {}) {
      this.panel = panel;
      this.getAxis = typeof axis === 'function' ? axis : () => axis || 'y';
      this.getDir = typeof dismissDirection === 'function' ? dismissDirection : () => dismissDirection || 1;
      this.enabled = typeof enabled === 'function' ? enabled : () => true;
      this.onDrag = onDrag;
      this.onRelease = onRelease;
      this.onDismiss = onDismiss;
      this.pointerId = null;
      this.onDown = this.onDown.bind(this);
      this.onMove = this.onMove.bind(this);
      this.onUp = this.onUp.bind(this);
      this.onTouchMove = this.onTouchMove.bind(this);
      this.bind();
    }

    // Delegated listeners on the panel: handles and scrollers may be re-rendered
    // (cart drawer) without losing the gesture. touchmove is non-passive and bound
    // for the panel's lifetime, so the browser knows from touchstart that a pull
    // from the scroll top may be claimed.
    bind() {
      this.panel.addEventListener('pointerdown', this.onDown);
      this.panel.addEventListener('touchmove', this.onTouchMove, { passive: false });
    }

    destroy() {
      this.panel.removeEventListener('pointerdown', this.onDown);
      this.panel.removeEventListener('touchmove', this.onTouchMove, { passive: false });
    }

    point(e) {
      return this.axis === 'x' ? e.clientX : e.clientY;
    }

    // Every scroller from the press target up to the panel sits at its top
    atScrollTop(target) {
      for (let el = target; el; el = el.parentElement) {
        if (el.scrollTop > 0) return false;
        if (el === this.panel) return true;
      }
      return true;
    }

    onDown(e) {
      if (!this.enabled() || this.pointerId !== null) return; // ignore extra fingers
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      const handle = e.target.closest('[data-sheet-handle]');
      let source = 'handle';
      if (handle && this.panel.contains(handle)) {
        // Controls inside the handle zone (the close button) keep working as taps
        const control = e.target.closest('button, a, input, select, textarea, [role="button"]');
        if (control && control !== handle && handle.contains(control)) return;
      } else {
        // A pull from the content: touch/pen on a bottom sheet scrolled to the top
        if (e.pointerType !== 'touch' && e.pointerType !== 'pen') return;
        if (e.target.closest(NOT_DRAGGABLE)) return;
        source = 'scroll';
      }
      this.axis = this.getAxis();
      this.dir = this.getDir();
      if (source === 'scroll' && (this.axis !== 'y' || this.dir !== 1 || !this.atScrollTop(e.target))) return;
      this.source = source;
      this.claimed = source === 'handle'; // a content pull is claimed on its first downward move
      this.pointerId = e.pointerId;
      this.startPoint = this.point(e);
      this.startCross = this.axis === 'x' ? e.clientY : e.clientX;
      this.state = 'pending';
      this.samples = [{ t: e.timeStamp, p: this.startPoint }];
      this.raw = 0;
      this.handle = handle;
      this.captureEl = source === 'handle' ? handle : this.panel;
      // Catch a sheet that is still moving (apple-design §3): it stops under the finger
      this.caught = running.has(this.panel);
      if (this.caught) stop(this.panel);
      window.addEventListener('pointermove', this.onMove, { passive: true });
      window.addEventListener('pointerup', this.onUp);
      window.addEventListener('pointercancel', this.onUp);
    }

    /* A content pull decides on its first clear move (3px): down along the
       dismiss axis claims it for the sheet; up or sideways ends the gesture so
       native scrolling proceeds. Returns true once claimed. */
    claim(along, cross) {
      if (this.claimed) return true;
      if (Math.abs(along) < 3 && Math.abs(cross) < 3) return false; // not decided yet
      if (along > 0 && along >= Math.abs(cross)) {
        this.claimed = true;
        return true;
      }
      this.end();
      return false;
    }

    // Pointer events precede the touch events of the same move, so onMove has
    // usually decided already; this cancels the browser's pan for a claimed pull.
    onTouchMove(e) {
      if (this.source !== 'scroll' || this.pointerId === null) return;
      if (!this.claimed && e.touches.length === 1) {
        const t = e.touches[0];
        this.claim(t.clientY - this.startPoint, t.clientX - this.startCross);
      }
      if (this.claimed && this.pointerId !== null && e.cancelable) e.preventDefault();
    }

    onMove(e) {
      if (e.pointerId !== this.pointerId) return;
      const p = this.point(e);
      if (this.state === 'pending') {
        const along = p - this.startPoint;
        const crossDelta = (this.axis === 'x' ? e.clientY : e.clientX) - this.startCross;
        if (!this.claim(along * this.dir, crossDelta)) return; // content pull not (yet) ours
        const cross = Math.abs(crossDelta);
        if (Math.abs(along) < 10 && cross < 10) return; // hysteresis
        if (cross > Math.abs(along)) return this.end(); // a sideways gesture, not ours
        this.state = 'dragging';
        try { this.captureEl.setPointerCapture(this.pointerId); } catch (err) { /* capture is best effort */ }
        stop(this.panel);
        this.size = this.axis === 'x' ? this.panel.getBoundingClientRect().width : this.panel.getBoundingClientRect().height;
        this.base = this.currentOffset();
        // Keep the original grab point: once the 10px threshold commits the
        // drag, the sheet sits exactly where the finger is (1:1 from the grab).
        this.panel.classList.add('is-dragging');
      }
      if (this.state !== 'dragging') return;
      const raw = this.base + (p - this.startPoint) * this.dir;
      const offset = raw < 0 ? -rubberband(-raw, this.size) : raw; // resist past the open position
      this.raw = raw;
      this.offset = offset;
      this.apply(offset);
      this.samples.push({ t: e.timeStamp, p });
      while (this.samples.length > 2 && e.timeStamp - this.samples[0].t > 80) this.samples.shift();
      if (this.onDrag) this.onDrag(Math.max(0, Math.min(1, offset / this.size)));
    }

    onUp(e) {
      if (e.pointerId !== this.pointerId) return;
      if (this.state === 'dragging') {
        // Velocity at release (apple-design §5): only moves from the last 100ms
        // before the pointerup count, so a finger that rested before lifting
        // carries no stale flick. A cancelled pointer never dismisses.
        const cancelled = e.type === 'pointercancel';
        const recent = this.samples.filter((s) => e.timeStamp - s.t <= 100);
        let velocity = 0;
        if (!cancelled && recent.length >= 2) {
          const first = recent[0];
          const last = recent[recent.length - 1];
          velocity = (((last.p - first.p) * this.dir) / Math.max(1, last.t - first.t)) * 1000; // px/s toward dismiss
        }
        const projected = this.offset + project(velocity);
        const dismiss = !cancelled && (projected > this.size * 0.5 || velocity > 700) && velocity > -200;
        this.panel.classList.remove('is-dragging');
        if (dismiss && this.onDismiss) {
          this.onDismiss({ velocity, offset: this.offset, size: this.size });
        } else {
          this.settle(velocity);
          if (this.onRelease) this.onRelease();
        }
      }
      this.end();
    }

    end() {
      window.removeEventListener('pointermove', this.onMove);
      window.removeEventListener('pointerup', this.onUp);
      window.removeEventListener('pointercancel', this.onUp);
      if (this.captureEl && this.pointerId !== null) {
        try { this.captureEl.releasePointerCapture(this.pointerId); } catch (err) { /* already released */ }
      }
      // A press that caught a moving sheet but never became a drag (tap, sideways
      // or upward scroll, cancel) lets it settle open again. Not if it closed meanwhile.
      if (this.state === 'pending' && this.caught && this.enabled()) {
        this.offset = this.currentOffset();
        this.settle(0);
      }
      this.caught = false;
      this.claimed = false;
      this.source = null;
      this.pointerId = null;
      this.state = null;
    }

    translate(offset) {
      const v = offset * this.dir;
      return this.axis === 'x' ? `translateX(${v}px)` : `translateY(${v}px)`;
    }

    apply(offset) {
      this.panel.style.transform = this.translate(offset);
    }

    currentOffset() {
      const m = new DOMMatrixReadOnly(getComputedStyle(this.panel).transform);
      return (this.axis === 'x' ? m.m41 : m.m42) * this.dir;
    }

    /* Spring back to open, carrying the release velocity (apple-design §5) */
    settle(velocity) {
      // Progress runs offset → 0, so position = offset·(1 − p) and dp/dt = −(sheet velocity) / offset,
      // sign kept: past the open position (offset < 0) a sheet still rising keeps rising before it turns.
      // There the sheet moves at the rubber band's slope, not at the finger's speed.
      const slope = this.offset < 0 && this.size ? (0.55 * this.size * this.size) / Math.pow(this.size + 0.55 * Math.abs(this.raw || 0), 2) : 1;
      const v = -(velocity * slope) / (this.offset || 1);
      const momentum = Math.abs(velocity) > 300;
      animate(this.panel, { from: this.translate(this.offset), to: 'none' }, { duration: 0.4, bounce: momentum ? 0.15 : 0, velocity: v });
      if (this.onDrag) this.onDrag(0);
    }
  }

  Olivet.motion = { spring, animate, stop, project, rubberband, SheetGesture, reduced };
})();
