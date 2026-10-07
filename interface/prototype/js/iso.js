// Isometric drawing helpers: tile coordinates (x, y) and a height z in pixels become screen points.
// x grows down-right, y grows down-left, z grows up. Everything returns SVG strings.

export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export function projector(origin, tw = 64) {
  const sx = tw / 2, sy = tw / 4;
  const p = (x, y, z = 0) => [origin[0] + (x - y) * sx, origin[1] + (x + y) * sy - z];
  return { p, tw, sx, sy };
}

const f = (n) => Math.round(n * 10) / 10;
export const pts = (list) => list.map((q) => `${f(q[0])},${f(q[1])}`).join(" ");

export function poly(list, cls = "", extra = "") {
  return `<polygon class="${cls}" points="${pts(list)}" ${extra}/>`;
}

// A box with a top, a left face (the plane y = y + d) and a right face (the plane x = x + w).
export function box(P, x, y, z, w, d, h, tone = "paper", extra = "") {
  const top = [P.p(x, y, z + h), P.p(x + w, y, z + h), P.p(x + w, y + d, z + h), P.p(x, y + d, z + h)];
  const left = [P.p(x, y + d, z), P.p(x + w, y + d, z), P.p(x + w, y + d, z + h), P.p(x, y + d, z + h)];
  const right = [P.p(x + w, y, z), P.p(x + w, y + d, z), P.p(x + w, y + d, z + h), P.p(x + w, y, z + h)];
  return `<g class="box tone-${tone}" ${extra}>${poly(left, "l")}${poly(right, "r")}${poly(top, "t")}</g>`;
}

// A flat tile on the ground (or at height z).
export function tile(P, x, y, w, d, cls = "", z = 0, extra = "") {
  return poly([P.p(x, y, z), P.p(x + w, y, z), P.p(x + w, y + d, z), P.p(x, y + d, z)], cls, extra);
}

// A quad standing on the plane y = const (a face looking down-left) between x0..x1 and heights z0..z1.
export function faceY(P, y, x0, x1, z0, z1, cls = "", extra = "") {
  return poly([P.p(x0, y, z0), P.p(x1, y, z0), P.p(x1, y, z1), P.p(x0, y, z1)], cls, extra);
}
// A quad standing on the plane x = const (a face looking down-right) between y0..y1 and heights z0..z1.
export function faceX(P, x, y0, y1, z0, z1, cls = "", extra = "") {
  return poly([P.p(x, y0, z0), P.p(x, y1, z0), P.p(x, y1, z1), P.p(x, y0, z1)], cls, extra);
}

export function cone(P, x, y, z, r, h, tone = "leaf") {
  const [cx, cy] = P.p(x, y, z);
  const [tx, ty] = P.p(x, y, z + h);
  return `<g class="tree tone-${tone}"><ellipse class="shadow" cx="${f(cx + 4)}" cy="${f(cy + 2)}" rx="${r + 4}" ry="${r / 2 + 2}"/>`
    + `<polygon class="l" points="${f(cx - r)},${f(cy)} ${f(cx)},${f(cy + r / 2)} ${f(tx)},${f(ty)}"/>`
    + `<polygon class="r" points="${f(cx + r)},${f(cy)} ${f(cx)},${f(cy + r / 2)} ${f(tx)},${f(ty)}"/></g>`;
}

export function shadow(P, x, y, w, d, grow = 0.5) {
  return poly([P.p(x + grow, y + grow, 0), P.p(x + w + grow * 2, y + grow, 0), P.p(x + w + grow * 2, y + d + grow * 2, 0), P.p(x + grow, y + d + grow * 2, 0)], "ground-shadow");
}

// A group whose content is drawn in a flat local space (u right, v down) laid on a wall plane.
//   dir = "down": reading direction goes down-right (the plane y = const, a left face)
//   dir = "up":   reading direction goes up-right (the plane x = const seen from inside the room on the left wall)
export function plane(origin, dir, inner) {
  const m = dir === "up" ? "1,-0.5,0,1" : "1,0.5,0,1";
  return `<g transform="translate(${f(origin[0])} ${f(origin[1])}) matrix(${m},0,0)">${inner}</g>`;
}
