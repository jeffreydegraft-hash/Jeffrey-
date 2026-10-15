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
   - SheetGesture: drag a sheet 1:1, release with velocity handoff, flick to dismiss.
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
     Drag starts only on handles (touch-action: none there), so content keeps
     native scrolling. Offset is measured along the dismiss direction:
     0 = open, size = closed. */
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
      this.bind();
    }

    // One delegated listener: handles may be re-rendered (cart drawer) without losing the gesture
    bind() {
      this.panel.addEventListener('pointerdown', this.onDown);
    }

    destroy() {
      this.panel.removeEventListener('pointerdown', this.onDown);
    }

    point(e) {
      return this.axis === 'x' ? e.clientX : e.clientY;
    }

    onDown(e) {
      if (!this.enabled() || this.pointerId !== null) return; // ignore extra fingers
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      const handle = e.target.closest('[data-sheet-handle]');
      if (!handle || !this.panel.contains(handle)) return;
      // Controls inside the handle zone (the close button) keep working as taps
      const control = e.target.closest('button, a, input, select, textarea, [role="button"]');
      if (control && control !== handle && handle.contains(control)) return;
      this.axis = this.getAxis();
      this.dir = this.getDir();
      this.pointerId = e.pointerId;
      this.startPoint = this.point(e);
      this.startCross = this.axis === 'x' ? e.clientY : e.clientX;
      this.state = 'pending';
      this.samples = [{ t: e.timeStamp, p: this.startPoint }];
      this.handle = handle;
      window.addEventListener('pointermove', this.onMove, { passive: true });
      window.addEventListener('pointerup', this.onUp);
      window.addEventListener('pointercancel', this.onUp);
    }

    onMove(e) {
      if (e.pointerId !== this.pointerId) return;
      const p = this.point(e);
      const delta = (p - this.startPoint) * this.dir; // + toward dismiss
      if (this.state === 'pending') {
        const cross = Math.abs((this.axis === 'x' ? e.clientY : e.clientX) - this.startCross);
        if (Math.abs(p - this.startPoint) < 10 && cross < 10) return; // hysteresis
        if (cross > Math.abs(p - this.startPoint)) return this.end(); // a sideways gesture, not ours
        this.state = 'dragging';
        try { this.handle.setPointerCapture(this.pointerId); } catch (err) { /* capture is best effort */ }
        stop(this.panel);
        this.size = this.axis === 'x' ? this.panel.getBoundingClientRect().width : this.panel.getBoundingClientRect().height;
        this.base = this.currentOffset();
        this.startPoint = p; // track from here: respects the grab offset
        this.panel.classList.add('is-dragging');
      }
      if (this.state !== 'dragging') return;
      const raw = this.base + (p - this.startPoint) * this.dir;
      const offset = raw < 0 ? -rubberband(-raw, this.size) : raw; // resist past the open position
      this.offset = offset;
      this.apply(offset);
      this.samples.push({ t: e.timeStamp, p });
      while (this.samples.length > 2 && e.timeStamp - this.samples[0].t > 80) this.samples.shift();
      if (this.onDrag) this.onDrag(Math.max(0, Math.min(1, offset / this.size)));
    }

    onUp(e) {
      if (e.pointerId !== this.pointerId) return;
      if (this.state === 'dragging') {
        const first = this.samples[0];
        const last = this.samples[this.samples.length - 1];
        const dt = Math.max(1, last.t - first.t);
        const velocity = (((last.p - first.p) * this.dir) / dt) * 1000; // px/s toward dismiss
        const projected = this.offset + project(velocity);
        const dismiss = (projected > this.size * 0.5 || velocity > 700) && velocity > -200;
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
      if (this.handle && this.pointerId !== null) {
        try { this.handle.releasePointerCapture(this.pointerId); } catch (err) { /* already released */ }
      }
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
      const distance = Math.abs(this.offset) || 1;
      // progress runs from offset → 0; moving toward dismiss is negative progress velocity
      const v = -velocity / distance;
      const momentum = Math.abs(velocity) > 300;
      animate(this.panel, { from: this.translate(this.offset), to: 'none' }, { duration: 0.4, bounce: momentum ? 0.15 : 0, velocity: v });
      if (this.onDrag) this.onDrag(0);
    }
  }

  Olivet.motion = { spring, animate, stop, project, rubberband, SheetGesture, reduced };
})();
