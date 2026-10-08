// The City scene (handoff scene.md 5.3): one lot per project (at most four), a building on each with one floor per
// agent, streets, trees. It builds a group from a plain model and returns what the engine needs around it: the hit
// objects (a building), the HTML labels' anchors, the running buildings' beacons and the waiting markers. No colour and no
// project name is written here: colours come from the palette, names from the model.

import { exclamation, plant, tree } from "./props.js";

export const LOT = 13;
export const STREET = 3.2;
const STEP = LOT + STREET;
const W = 4.4;
const D = 3.2;
const P = 2.9;
const BASE = 0.14;
const TREES = [[-5, -5], [-5, -1.5], [-5, 2.5], [-5, 5], [-2.4, 5.2], [2.4, 5.2], [5, 5], [5, 1.5], [5, -2.5], [4.6, -5.2], [1, -5.3]];

/** The height of the top of a building of n floors. */
export function roofHeight(n) {
  return BASE + n * P;
}

function building(kit, lot, cx, cz, group) {
  const { THREE, palette } = kit;
  const T = palette.T;
  const g = new THREE.Group();
  g.position.set(cx, 0, cz);
  group.add(g);
  const markers = [];
  lot.floors.forEach((floor, f) => {
    const y = BASE + f * P;
    const state = floor.window;
    const colour = palette.windows[state];
    kit.box(W + 0.2, 0.24, D + 0.2, 0, y, 0, T.emphasis, { parent: g, edges: true });
    kit.box(W, P - 0.24, D, 0, y + 0.24, 0, palette.shell, { parent: g, edges: true });
    if (f === 0) {
      const glass = state === "lit" ? palette.warm : palette.glass;
      kit.box(W - 0.6, P - 0.7, 0.06, 0, y + 0.34, D / 2 + 0.02, glass, { cast: false, parent: g, unlit: true });
      [-1.3, -0.45, 0.45, 1.3].forEach((dx) => kit.box(0.06, P - 0.7, 0.08, dx, y + 0.34, D / 2 + 0.04, T.emphasis, { parent: g }));
      kit.box(0.06, P - 0.7, D - 0.6, W / 2 + 0.02, y + 0.34, 0, glass, { cast: false, parent: g, unlit: true });
      kit.box(2.4, 0.14, 1.2, 0, y + P - 0.45, D / 2 + 0.6, T.emphasis, { parent: g, edges: true });
      [-1.05, 1.05].forEach((dx) => kit.box(0.1, P - 0.6, 0.1, dx, y, D / 2 + 1.1, palette.bg, { parent: g, edges: true }));
      kit.box(0.9, 1.7, 0.08, 0, y + 0.24, D / 2 + 0.06, palette.pale, { cast: false, parent: g, unlit: true });
      kit.box(0.04, 1.7, 0.1, 0, y + 0.24, D / 2 + 0.08, T.textMuted, { parent: g });
      kit.box(2.0, 0.08, 0.5, 0, 0, D / 2 + 1.55, T.emphasis, { parent: g, edges: true });
      plant(kit, g, -1.7, D / 2 + 0.9);
      plant(kit, g, 1.7, D / 2 + 0.9);
    } else {
      const wy = y + 0.24 + 0.5;
      const wh = P - 1.1;
      const isLit = state === "lit";
      [-1.5, -0.5, 0.5, 1.5].forEach((dx) => {
        kit.box(0.78, wh, 0.05, dx, wy, D / 2 + 0.02, colour, { cast: false, parent: g, unlit: isLit });
        kit.box(0.03, wh, 0.07, dx, wy, D / 2 + 0.04, T.emphasis, { cast: false, parent: g });
      });
      [-1.0, 0, 1.0].forEach((dz) => {
        kit.box(0.05, wh, 0.78, W / 2 + 0.02, wy, dz, colour, { cast: false, parent: g, unlit: isLit });
        kit.box(0.07, wh, 0.03, W / 2 + 0.04, wy, dz, T.emphasis, { cast: false, parent: g });
      });
      [-W / 2 + 0.06, -1, 0, 1, W / 2 - 0.06].forEach((dx) => kit.box(0.12, P - 0.24, 0.1, dx, y + 0.24, D / 2 + 0.05, palette.shell, { parent: g, edges: true }));
    }
    if (floor.waits) {
      const marker = exclamation(kit, g, W / 2 + 0.85, y + 0.75, D / 2 - 0.4);
      markers.push({ key: `${lot.id}:${f}`, group: marker, restY: y + 0.75 });
    }
  });
  const top = roofHeight(lot.floors.length);
  kit.box(W + 0.36, 0.32, D + 0.36, 0, top, 0, T.emphasis, { parent: g, edges: true });
  kit.box(W + 0.36, 0.3, 0.1, 0, top + 0.32, D / 2 + 0.13, palette.shell, { parent: g, edges: true });
  kit.box(0.1, 0.3, D + 0.36, W / 2 + 0.13, top + 0.32, 0, palette.shell, { parent: g, edges: true });
  kit.box(1.2, 0.6, 0.9, -1.2, top + 0.32, -0.7, T.emphasis, { parent: g, edges: true });
  kit.box(0.8, 0.45, 0.8, 0.2, top + 0.32, -0.8, palette.bg, { parent: g, edges: true });
  let beacon = null;
  if (lot.runningTask !== null && lot.accepted) {
    const material = kit.adopt(new THREE.MeshBasicMaterial({ color: T.theme, transparent: true, opacity: 1 }));
    const ring = new THREE.Mesh(kit.track(new THREE.TorusGeometry(0.42, 0.09, 6, 16)), material);
    ring.rotation.x = Math.PI / 2;
    ring.position.set(W / 2 - 0.8, top + 0.9, D / 2 - 0.8);
    g.add(ring);
    kit.box(0.12, 0.5, 0.12, W / 2 - 0.8, top + 0.32, D / 2 - 0.8, T.textMuted, { parent: g });
    beacon = { ring, material, id: lot.id };
  }
  return { group: g, markers, beacon, top };
}

/**
 * Build the City. model: {selectedId, lots: [{id, name, accepted, decisions, runningTask, floors: [{window, waits}], tip, sub}]}.
 * Returns {group, hits, labels, beacons, markers, extraDisposables}; the engine adds the group to the scene.
 */
export function buildCity(kit, model) {
  const { THREE, palette } = kit;
  const T = palette.T;
  const group = new THREE.Group();
  const lots = model.lots;
  const x0 = -((lots.length - 1) * STEP) / 2;
  const n = Math.max(1, lots.length);
  kit.box(n * STEP + STREET + 8, 0.04, STREET, 0, 0, LOT / 2 + STREET / 2, T.emphasis, { cast: false, parent: group });
  for (let k = 0; k <= n; k++) {
    kit.box(STREET, 0.04, LOT + 14, x0 - STEP / 2 + k * STEP, 0, -2, T.emphasis, { cast: false, parent: group });
  }
  for (let k = -8; k <= 8; k++) kit.box(0.9, 0.045, 0.12, k * 2.4, 0, LOT / 2 + STREET / 2, palette.bg, { cast: false, parent: group });
  const hits = [];
  const labels = [];
  const beacons = [];
  const markers = [];
  lots.forEach((lot, i) => {
    const cx = x0 + i * STEP;
    const cz = 0;
    kit.box(LOT, 0.12, LOT, cx, 0, cz, palette.lot, { cast: false, parent: group, edges: true });
    kit.box(1.4, 0.13, LOT / 2 - 2.6, cx, 0, cz + (LOT / 2 + 2.6) / 2, T.emphasis, { cast: false, parent: group });
    const built = building(kit, lot, cx, cz - 0.6, group);
    if (lot.id === model.selectedId) {
      const h = LOT / 2 + 0.05;
      kit.line([[cx - h, 0.14, cz - h], [cx + h, 0.14, cz - h], [cx + h, 0.14, cz + h], [cx - h, 0.14, cz + h], [cx - h, 0.14, cz - h]], kit.themeLine, group);
    }
    TREES.forEach(([dx, dz], k) => tree(kit, group, cx + dx, cz + dz, k % 3 ? 1.15 : 1.35));
    hits.push({ object: built.group, id: lot.id, tip: lot.tip });
    labels.push({
      id: lot.id, kind: "card", name: lot.name, decisions: lot.decisions, running: lot.runningTask !== null, sub: lot.sub,
      selected: lot.id === model.selectedId, accepted: lot.accepted, anchor: new THREE.Vector3(cx, built.top + 1.8, cz - 0.6),
    });
    if (built.beacon) beacons.push(built.beacon);
    markers.push(...built.markers);
  });
  return { group, hits, labels, beacons, markers, bounds: new THREE.Box3().setFromObject(group) };
}

/** The beacon's pulse at `seconds`: a 2 s cycle, scale 1 +/- .12, opacity .35 to .65 (the prototype's numbers). */
export function pulseBeacon(beacon, seconds) {
  const wave = Math.sin(seconds * Math.PI);
  const s = 1 + 0.12 * wave;
  beacon.ring.scale.set(s, s, s);
  beacon.material.opacity = 0.35 + 0.3 * (0.5 + 0.5 * wave);
}

/** The beacon at rest (no ambient animation): full size and opaque. */
export function restBeacon(beacon) {
  beacon.ring.scale.set(1, 1, 1);
  beacon.material.opacity = 1;
}
