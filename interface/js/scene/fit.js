// Fitting the camera: pure arithmetic on rectangles, no three.js and no document.

/**
 * The orthographic frustum that puts a subject (its bounds in camera space: {x0, x1, y0, y1}) inside the free rectangle
 * of a view of `size` {w, h} left by the panels (`insets` {left, right, top, bottom}, in pixels), padded by `pad`.
 * `maxScale` (pixels a unit of the camera's space may take, optional) stops the fit from zooming past it. Returns {left, right, top, bottom} in camera space.
 */
export function fitFrustum(bounds, size, insets, pad, maxScale) {
  const ins = { left: 0, right: 0, top: 0, bottom: 0, ...(insets || {}) };
  const w = Math.max(1, size.w);
  const h = Math.max(1, size.h);
  const fw = Math.max(50, w - ins.left - ins.right);
  const fh = Math.max(50, h - ins.top - ins.bottom);
  let s = Math.max((bounds.x1 - bounds.x0) / fw, (bounds.y1 - bounds.y0) / fh, 1e-6) * (pad || 1);
  if (maxScale > 0) s = Math.max(s, 1 / maxScale);   // not closer than `maxScale` pixels to a unit: a subject that is small in the free rectangle stays as large as it is drawn
  const cx = (bounds.x0 + bounds.x1) / 2 - (ins.left + fw / 2 - w / 2) * s;
  const cy = (bounds.y0 + bounds.y1) / 2 + (ins.top + fh / 2 - h / 2) * s;
  return { left: cx - (w / 2) * s, right: cx + (w / 2) * s, top: cy + (h / 2) * s, bottom: cy - (h / 2) * s };
}

/**
 * The frustum of a camera move at progress `p` (0 to 1), the prototype's way: the centre is moved in a straight line and the ZOOM
 * (the reciprocal of the frustum's half width, the prototype's `cam.zoom`) is moved in a straight line, not the frustum's sides.
 * Moving the sides in a straight line made a fly-in start slowly and end fast; moving the zoom is what the prototype did.
 */
export function moveFrustum(a, b, p) {
  const read = (f) => ({ x: (f.left + f.right) / 2, y: (f.top + f.bottom) / 2, zoom: 2 / (f.right - f.left), aspect: (f.top - f.bottom) / (f.right - f.left) });
  const from = read(a);
  const to = read(b);
  const mix = (x, y) => x + (y - x) * p;
  const zoom = mix(from.zoom, to.zoom);
  const half = 1 / zoom;
  const x = mix(from.x, to.x);
  const y = mix(from.y, to.y);
  const hh = half * mix(from.aspect, to.aspect);
  return { left: x - half, right: x + half, top: y + hh, bottom: y - hh };
}

/** A frustum between two, at t from 0 to 1 (the sides moved in a straight line). */
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
