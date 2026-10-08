// The furniture of the building and room scenes (handoff scene.md 5.1): desk, chair, tray, sheet, table, cabinet, wall
// lamp, bookshelf and the Lobby's door. Each takes the kit and the group to add to, builds boxes and cylinders from
// palette colours only, and returns the group (or the pieces a motion needs). Nothing here knows a project or an agent.

const TAU = Math.PI * 2;

/** The state of a desk's screen: working theme (unlit), waiting and idle dim, off the text colour. */
export function screenColour(palette, state) {
  if (state === "working") return palette.T.theme;
  if (state === "off") return palette.T.text;
  return palette.screenOff;
}

/** A chair at (x, z) facing `rotY` (a rotation of the chair whose back is at -z). `pushed` tucks it under the desk. */
export function chair(kit, parent, x, z, rotY = 0, pushed = false) {
  const { THREE, palette } = kit;
  const group = new THREE.Group();
  group.position.set(x, 0, z);
  group.rotation.y = rotY;
  parent.add(group);
  const ink = palette.ink;
  for (let i = 0; i < 5; i++) {
    const angle = (i / 5) * TAU;
    const lx = Math.cos(angle) * 0.15;
    const lz = Math.sin(angle) * 0.15;
    const leg = kit.box(0.3, 0.04, 0.05, lx / 2, 0.08, lz / 2, palette.metal, { parent: group });
    leg.rotation.y = -angle;
    kit.mesh(new THREE.SphereGeometry(0.035, 6, 4), ink, lx, 0.035, lz, { parent: group });
  }
  kit.cyl(0.03, 0.03, 0.34, 6, palette.metal, 0, 0.06, 0, { parent: group });
  kit.box(0.5, 0.08, 0.48, 0, 0.4, 0, ink, { parent: group });
  kit.box(0.46, 0.62, 0.08, 0, 0.48, -0.24, ink, { parent: group });
  kit.box(0.05, 0.1, 0.05, 0, 0.38, -0.2, palette.metal, { parent: group });
  for (const side of [-1, 1]) kit.box(0.05, 0.04, 0.32, side * 0.27, 0.62, -0.02, ink, { parent: group });
  return group;
}

/**
 * A desk of width w at (x, z): top, legs, modesty panel, monitor (the screen coloured by state), keyboard and a paper
 * block. Returns {group, screen, lines, scan}: the pieces the working motion moves.
 */
export function desk(kit, parent, x, z, state, w = 1.8) {
  const { THREE, palette } = kit;
  const group = new THREE.Group();
  group.position.set(x, 0, z);
  parent.add(group);
  kit.box(w, 0.05, 0.8, 0, 0.66, 0, palette.deskTop, { parent: group, edges: true });
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) kit.cyl(0.025, 0.025, 0.66, 6, palette.metal, sx * (w / 2 - 0.08), 0, sz * 0.32, { parent: group });
  kit.box(w - 0.2, 0.2, 0.03, 0, 0.42, -0.36, palette.metal, { parent: group });
  kit.box(0.22, 0.02, 0.16, 0, 0.71, -0.22, palette.ink, { parent: group });
  kit.box(0.04, 0.24, 0.04, 0, 0.71, -0.26, palette.ink, { parent: group });
  kit.box(0.78, 0.46, 0.04, 0, 0.92, -0.26, palette.ink, { parent: group });
  const working = state === "working";
  const screen = kit.box(0.72, 0.4, 0.01, 0, 0.95, -0.235, screenColour(palette, state), { parent: group, unlit: true, cast: false });
  // a working screen changes tone (the prototype's flip between two blues): it has a material of its own, since the kit shares one per colour
  if (state === "working") screen.material = kit.adopt(screen.material.clone());
  const lines = [];
  if (working) {
    for (let i = 0; i < 4; i++) {
      const width = 0.4 - 0.06 * i;
      lines.push(kit.box(width, 0.02, 0.005, -0.3 + width / 2, 1.27 - 0.09 * i, -0.226, palette.bg, { parent: group, unlit: true, cast: false }));
    }
  }
  let scan = null;
  if (working) scan = kit.box(0.7, 0.012, 0.004, 0, 0.97, -0.224, palette.T.theme.clone().lerp(palette.bg, 0.5), { parent: group, unlit: true, cast: false });
  kit.box(0.5, 0.025, 0.16, 0, 0.71, 0.08, palette.ink, { parent: group });
  kit.box(0.45, 0.03, 0.32, -(w / 2 - 0.35), 0.71, 0.1, palette.bg, { parent: group, edges: true });
  return { group, screen, lines, scan };
}

/** The inbox tray: a base and up to six sheets, the top one in the warn colour when something waits. */
export function tray(kit, parent, x, y, z, count, waiting) {
  const { palette } = kit;
  const group = new kit.THREE.Group();
  group.position.set(x, y, z);
  parent.add(group);
  kit.box(0.42, 0.05, 0.32, 0, 0.69, 0, palette.metal, { parent: group });
  const n = Math.min(6, Math.max(0, count));
  for (let i = 0; i < n; i++) {
    const top = i === n - 1 && waiting;
    kit.box(0.36, 0.018, 0.27, 0, 0.74 + i * 0.022, 0, top ? palette.T.warn : palette.bg, { parent: group, edges: true, cast: false });
  }
  return group;
}

/** A sheet of paper lying at (x, z) at table height: a theme bar and four grey lines. Returns its group. */
export function sheet(kit, parent, x, y, z, rotY = 0) {
  const { palette } = kit;
  const group = new kit.THREE.Group();
  group.position.set(x, y, z);
  group.rotation.y = rotY;
  parent.add(group);
  kit.box(0.34, 0.01, 0.44, 0, 0.715, 0, palette.bg, { parent: group, edges: true, cast: false });
  kit.box(0.2, 0.004, 0.03, -0.04, 0.726, -0.15, palette.T.theme, { parent: group, unlit: true, cast: false });
  for (let i = 0; i < 4; i++) kit.box(0.26, 0.004, 0.015, 0, 0.726, -0.07 + i * 0.07, palette.T.border, { parent: group, unlit: true, cast: false });
  return group;
}

/** A table with a wooden top and four metal legs. Returns its group. */
export function table(kit, parent, x, z, w, d) {
  const { palette } = kit;
  const group = new kit.THREE.Group();
  group.position.set(x, 0, z);
  parent.add(group);
  kit.box(w, 0.06, d, 0, 0.64, 0, palette.wood, { parent: group, edges: true });
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) kit.box(0.06, 0.64, 0.06, sx * (w / 2 - 0.08), 0, sz * (d / 2 - 0.08), palette.metal, { parent: group });
  return group;
}

/** A filing cabinet of one to three drawers, its front facing +x after the quarter turn the scenes give it. */
export function cabinet(kit, parent, x, z, drawers, rotY = 0) {
  const { palette } = kit;
  const group = new kit.THREE.Group();
  group.position.set(x, 0, z);
  group.rotation.y = rotY;
  parent.add(group);
  kit.box(0.62, 1.3, 0.62, 0, 0, 0, palette.bg, { parent: group, edges: true });
  const n = Math.max(1, Math.min(3, drawers));
  for (let i = 0; i < n; i++) {
    kit.box(0.54, 0.34, 0.02, 0, 0.1 + 0.4 * i, 0.32, palette.drawer, { parent: group });
    kit.box(0.16, 0.03, 0.03, 0, 0.26 + 0.4 * i, 0.345, palette.metal, { parent: group });
  }
  return group;
}

/** A wall lamp, lit (unlit material), along x or along z. */
export function wallLamp(kit, parent, x, y, z, alongX = true) {
  return kit.box(alongX ? 0.7 : 0.05, 0.06, alongX ? 0.05 : 0.7, x, y, z, kit.palette.warm, { parent, unlit: true, cast: false });
}

/** A bookshelf on the left wall: a frame, three boards and fifteen books in three colours. */
export function bookshelf(kit, parent, x, z) {
  const { palette } = kit;
  const group = new kit.THREE.Group();
  group.position.set(x, 0, z);
  parent.add(group);
  kit.box(0.36, 1.7, 1.2, 0, 0, 0, palette.bg, { parent: group, edges: true });
  const colours = [palette.drawer, palette.T.border, palette.wood];
  for (let k = 0; k < 3; k++) {
    kit.box(0.4, 0.04, 1.2, 0.02, 0.06 + 0.55 * k, 0, palette.T.emphasis, { parent: group });
    for (let b = 0; b < 5; b++) kit.box(0.06, 0.34, 0.14, 0.08, 0.1 + 0.55 * k, -0.45 + b * 0.22, colours[(k * 5 + b) % 3], { parent: group });
  }
  return group;
}

/** The Lobby's door on the left wall: a leaf, a frame in the theme colour and a handle. Returns its group. */
export function door(kit, parent, x, z) {
  const { palette } = kit;
  const group = new kit.THREE.Group();
  group.position.set(x, 0, z);
  parent.add(group);
  kit.box(0.06, 2.1, 1.1, 0, 0, 0, palette.T.emphasis, { parent: group, edges: true });
  for (const dz of [-0.62, 0.62]) kit.box(0.08, 2.22, 0.08, 0, 0, dz, palette.T.theme, { parent: group, unlit: true });
  kit.box(0.08, 0.08, 1.24, 0, 2.22, 0, palette.T.theme, { parent: group, unlit: true });
  kit.box(0.04, 0.04, 0.16, 0.05, 1.0, 0.4, palette.metal, { parent: group });
  return group;
}

/** A reception counter (the Lobby floor of the cutaway). */
export function counter(kit, parent, x, z) {
  return kit.box(1.6, 0.95, 0.55, x, 0, z, kit.palette.bg, { parent, edges: true });
}
