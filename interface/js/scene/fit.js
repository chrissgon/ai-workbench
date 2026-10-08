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

/** Ease in and out (cubic) for t from 0 to 1. */
export function ease(t) {
  const c = Math.max(0, Math.min(1, t));
  return c < 0.5 ? 4 * c * c * c : 1 - Math.pow(-2 * c + 2, 3) / 2;
}
