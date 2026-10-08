// The City's ground (handoff scene.md 5.3): one lot per project (at most four), the streets and the trees, and the roof beacon's pulse.
// The buildings stand on it as towers (tower.js); the world (world.js) puts the two together. No colour and no project name is written
// here: colours come from the palette.

import { beaconPulse } from "./prototype-motion.js";
import { tree } from "./props.js";

export const LOT = 13;
export const STREET = 3.2;
export const STEP = LOT + STREET;
const TREES = [[-5, -5], [-5, -1.5], [-5, 2.5], [-5, 5], [-2.4, 5.2], [2.4, 5.2], [5, 5], [5, 1.5], [5, -2.5], [4.6, -5.2], [1, -5.3]];

/** The x of the centre of lot i of n, and its z. */
export function lotAt(i, n) {
  return { x: -(((n - 1) * STEP) / 2) + i * STEP, z: 0 };
}

/**
 * The streets, and for each lot its slab, the path to its door and its trees. Returns {group, edges}: `edges[i]` is the theme line at
 * the edge of lot i, built hidden (it is drawn only for the lot the route selects, never as a standing line).
 */
export function buildGround(kit, n) {
  const { THREE, palette } = kit;
  const T = palette.T;
  const group = new THREE.Group();
  const count = Math.max(1, n);
  const x0 = lotAt(0, count).x;
  kit.box(count * STEP + STREET + 8, 0.04, STREET, 0, 0, LOT / 2 + STREET / 2, T.emphasis, { cast: false, parent: group });
  for (let k = 0; k <= count; k++) {
    kit.box(STREET, 0.04, LOT + 14, x0 - STEP / 2 + k * STEP, 0, -2, T.emphasis, { cast: false, parent: group });
  }
  for (let k = -8; k <= 8; k++) kit.box(0.9, 0.045, 0.12, k * 2.4, 0, LOT / 2 + STREET / 2, palette.bg, { cast: false, parent: group });
  const edges = [];
  for (let i = 0; i < n; i++) {
    const { x: cx, z: cz } = lotAt(i, n);
    kit.box(LOT, 0.12, LOT, cx, 0, cz, palette.lot, { cast: false, parent: group, edges: true });
    kit.box(1.4, 0.13, LOT / 2 - 2.6, cx, 0, cz + (LOT / 2 + 2.6) / 2, T.emphasis, { cast: false, parent: group });
    const h = LOT / 2 + 0.05;
    const edge = kit.line([[cx - h, 0.14, cz - h], [cx + h, 0.14, cz - h], [cx + h, 0.14, cz + h], [cx - h, 0.14, cz + h], [cx - h, 0.14, cz - h]], kit.themeLine, group);
    edge.visible = false;
    edges.push(edge);
    TREES.forEach(([dx, dz], k) => tree(kit, group, cx + dx, cz + dz, k % 3 ? 1.15 : 1.35));
  }
  return { group, edges };
}

/**
 * The beacon's pulse at `seconds`, the prototype's (prototype-motion.js `beaconPulse`): `sin(3 t)` (a 2.09 s cycle), scale 1 plus or minus .12
 * in the ring's own plane (its thickness stays), opacity .35 to .65, times the roof's fade (the ring goes with the roof while the building
 * opens). Ambient, held to 30 frames a second by the scheduler.
 */
export function pulseBeacon(beacon, seconds) {
  const pulse = beaconPulse(seconds);
  beacon.ring.scale.set(pulse.scale, pulse.scale, 1);
  beacon.material.opacity = pulse.opacity * (beacon.fade === undefined ? 1 : beacon.fade);
}

/** The beacon at rest (no ambient animation): full size and opaque (times the roof's fade). */
export function restBeacon(beacon) {
  beacon.ring.scale.set(1, 1, 1);
  beacon.material.opacity = beacon.fade === undefined ? 1 : beacon.fade;
}
