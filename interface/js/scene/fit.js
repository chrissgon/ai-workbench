// Fitting the camera: pure arithmetic on rectangles, no three.js and no document.

/**
 * The orthographic frustum that puts a subject (its bounds in camera space: {x0, x1, y0, y1}) inside the free rectangle
 * of a view of `size` {w, h} left by the panels (`insets` {left, right, top, bottom}, in pixels), padded by `pad`.
 * Returns {left, right, top, bottom} in camera space.
 */
export function fitFrustum(bounds, size, insets, pad) {
  const ins = { left: 0, right: 0, top: 0, bottom: 0, ...(insets || {}) };
  const w = Math.max(1, size.w);
  const h = Math.max(1, size.h);
  const fw = Math.max(50, w - ins.left - ins.right);
  const fh = Math.max(50, h - ins.top - ins.bottom);
  const s = Math.max((bounds.x1 - bounds.x0) / fw, (bounds.y1 - bounds.y0) / fh, 1e-6) * (pad || 1);
  const cx = (bounds.x0 + bounds.x1) / 2 - (ins.left + fw / 2 - w / 2) * s;
  const cy = (bounds.y0 + bounds.y1) / 2 + (ins.top + fh / 2 - h / 2) * s;
  return { left: cx - (w / 2) * s, right: cx + (w / 2) * s, top: cy + (h / 2) * s, bottom: cy - (h / 2) * s };
}

/** A frustum between two, at t from 0 to 1. */
export function lerpFrustum(a, b, t) {
  const mix = (x, y) => x + (y - x) * t;
  return { left: mix(a.left, b.left), right: mix(a.right, b.right), top: mix(a.top, b.top), bottom: mix(a.bottom, b.bottom) };
}

/**
 * The prototype's feel (its `scene.js`): the camera approached its goal exponentially, `1 - exp(-4.5 t)` a second (a fast start
 * that settles softly), and the building opened with `1 - exp(-3.2 t)` read through a smoothstep. A move here runs for the time
 * those take to settle to one percent (ln 100 over the rate) and the curve is normalised so it ends exactly on its goal.
 */
export const CAMERA_RATE = 4.5;
export const OPEN_RATE = 3.2;
const SETTLE = Math.log(100);

/** Milliseconds a move of the prototype's rate takes to settle to one percent. */
export function settleMs(rate) {
  return Math.round((SETTLE / rate) * 1000);
}

const clamp01 = (t) => Math.max(0, Math.min(1, t));

/** The prototype's exponential approach for t from 0 to 1: fast at first, soft at the end, exactly 1 at t = 1. */
export function ease(t) {
  return (1 - Math.exp(-SETTLE * clamp01(t))) / (1 - Math.exp(-SETTLE));
}

/** The prototype's opening curve: the approach read through a smoothstep, so it also starts softly. */
export function openEase(t) {
  const e = ease(t);
  return e * e * (3 - 2 * e);
}
