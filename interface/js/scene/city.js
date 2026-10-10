// The City's ground (round 4, R-16, `scene.css` and the drawing of `city.html`): a low-poly city in flat faces. Streets with a lane line, blocks with
// a kerb and a walk, each block a paved square or a park, faceted trees. One block holds each project's building (at most four, in a row); the
// rest is the city round them, drawn far enough that no zoom or pan of the camera shows its edge. Nothing in it is a fact of a project and
// nothing takes a click: the buildings stand on it as towers (tower.js) and the world (world.js) puts the two together.
//
// Everything static is baked into a few batches (kit.batch) and the trees are two instanced meshes, so the ground is a handful of draw calls
// whatever the number of blocks. No colour is written here: colours come from the palette (`cityTones`, the recipes of `scene.css`).

import { beaconPulse } from "./prototype-motion.js";
import { cityTones } from "./palette.js";

// Sizes in world units, from the drawing (a block's walk, its paving and a street; the building's footprint is 6.4 by 4.8, building.js).
export const BLOCK_W = 11.5;                 // a block with its walk, along x
export const BLOCK_D = 14.1;                 // along z
export const PAVED_W = 10.1;                 // the paving or the grass inside the walk
export const PAVED_D = 12.7;
export const STREET = 3.3;
export const PITCH_X = BLOCK_W + STREET;     // the grid's steps
export const PITCH_Z = BLOCK_D + STREET;
export const KERB = 0.2;                     // a block's height: the floor of every building stands on it (building.js BASE)
const ABOVE = 0.01;                          // what lies on a surface stands this far over it
export const MARGIN_X = 6;                   // blocks drawn beyond the row of lots, on each side, and rows above and below it
export const ROWS = 5;
const DASH = 0.62;
const GAP = 0.72;
const LANE = 0.14;

/** The centre of the block of lot i of n: the lots stand in a row along x, centred on the origin, one block each. */
export function lotAt(i, n) {
  return { x: (i - (n - 1) / 2) * PITCH_X, z: 0 };
}

/** A repeatable pseudo-random number from 0 to 1 for three integers (the same city every time: nothing is drawn by chance). */
export function hash(a, b, c = 0) {
  let h = (Math.imul(a | 0, 374761393) + Math.imul(b | 0, 668265263) + Math.imul(c | 0, 2147483647)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}

/** What a block is: "lot" (a project's, paved), "plaza" (paved) or "park" (grass), from its place in the grid. `col` 0 is the first lot. */
export function blockKind(col, row, n) {
  if (row === 0 && col >= 0 && col < n) return "lot";
  return (((col + row) % 2) + 2) % 2 === 0 ? "plaza" : "park";
}

/** Where the trees of a block stand, as [x, z, size] from the block's centre: four at the corners of a lot, a few on a plaza, a grove on a park. */
export function treesOf(kind, col, row) {
  const hx = PAVED_W / 2 - 1.1;
  const hz = PAVED_D / 2 - 1.1;
  if (kind === "lot") return [[-hx, -hz, 1.1], [hx, -hz, 1.0], [hx, hz - 0.6, 1.05], [-hx, hz - 0.6, 1.15]];
  const count = kind === "park" ? 6 + Math.floor(hash(col, row, 1) * 3) : 3;
  const out = [];
  for (let k = 0; k < count; k++) {
    const x = (hash(col, row, 10 + k) * 2 - 1) * hx;
    const z = (hash(col, row, 40 + k) * 2 - 1) * hz;
    if (out.some(([ox, oz]) => Math.hypot(ox - x, oz - z) < 2.2)) continue;   // two on one spot are one: keep a gap
    out.push([x, z, 0.9 + hash(col, row, 70 + k) * 0.35]);
  }
  return out;
}

/** A non-indexed geometry with a colour on every facet, `tone(facetIndex)`: a flat-shaded solid, three vertices a facet. */
function paint(THREE, geometry, tone) {
  const source = geometry.index ? geometry.toNonIndexed() : geometry;
  const count = source.getAttribute("position").count;
  const colours = new Float32Array(count * 3);
  for (let i = 0; i < count; i += 3) {
    const colour = tone(i / 3);
    for (let k = 0; k < 3; k++) colour.toArray(colours, (i + k) * 3);
  }
  source.setAttribute("color", new THREE.BufferAttribute(colours, 3));
  return source;
}

/** The crown of a tree (eight facets in four tones, lit from the upper left) and its trunk, as geometries painted from `tones`. */
export function treeGeometries(THREE, tones) {
  const light = new THREE.Vector3(-0.3, 0.8, 0.5).normalize();
  const crown = new THREE.OctahedronGeometry(1, 0).toNonIndexed();
  crown.scale(0.85, 0.84, 0.85);
  crown.translate(0, 1.75, 0);
  const position = crown.getAttribute("position");
  const centre = new THREE.Vector3(0, 1.75, 0);
  const shade = [];
  for (let i = 0; i < position.count; i += 3) {
    const facet = new THREE.Vector3();
    for (let k = 0; k < 3; k++) facet.add(new THREE.Vector3().fromBufferAttribute(position, i + k));
    shade.push({ facet: i / 3, value: facet.divideScalar(3).sub(centre).normalize().dot(light) });
  }
  shade.sort((p, q) => q.value - p.value);
  const tone = new Map(shade.map((s, rank) => [s.facet, Math.min(tones.crown.length - 1, Math.floor((rank * tones.crown.length) / shade.length))]));
  const painted = paint(THREE, crown, (facet) => tones.crown[tone.get(facet)]);
  const trunk = paint(THREE, new THREE.BoxGeometry(0.22, 0.95, 0.22).translate(0, 0.475, 0), () => tones.trunk);
  return { crown: painted, trunk };
}

/**
 * The ground for `n` lots. Returns {group, trees}: `group` holds the batches and the instanced trees; `trees` is how many were planted.
 * Streets and kerbs are one batch, the lane marks another, the paving and the parks a third; the trees are two instanced meshes.
 */
export function buildGround(kit, n) {
  const { THREE, palette } = kit;
  const tones = cityTones(palette);
  const group = new THREE.Group();
  const count = Math.max(1, n);
  const col0 = -MARGIN_X;
  const col1 = count - 1 + MARGIN_X;
  const gx = (col) => lotAt(0, count).x + col * PITCH_X;
  const gz = (row) => row * PITCH_Z;
  const x0 = gx(col0) - PITCH_X;
  const x1 = gx(col1) + PITCH_X;
  const z0 = gz(-ROWS) - PITCH_Z;
  const z1 = gz(ROWS) + PITCH_Z;

  const base = kit.batch();          // the road, then every block's kerb and walk
  const paving = kit.batch();        // the paved squares and the parks, on the blocks
  const lanes = kit.batch();         // the dashes of the lane lines
  base.flat(x0, z0, x1, z1, 0, tones.road);
  const planted = [];
  for (let row = -ROWS; row <= ROWS; row++) {
    for (let col = col0; col <= col1; col++) {
      const cx = gx(col);
      const cz = gz(row);
      const kind = blockKind(col, row, count);
      base.box(BLOCK_W, KERB, BLOCK_D, cx, 0, cz, { top: tones.walk, left: tones.kerb, right: tones.kerb });
      paving.flat(cx - PAVED_W / 2, cz - PAVED_D / 2, cx + PAVED_W / 2, cz + PAVED_D / 2, KERB + ABOVE, kind === "park" ? tones.grass : tones.plaza);
      for (const [dx, dz, size] of treesOf(kind, col, row)) planted.push([cx + dx, cz + dz, size, hash(col, row, Math.round(dx * 7)) * Math.PI * 2]);
      // the lane line runs down the middle of each street beside the block: along x under it, along z beside it
      for (let t = -BLOCK_W / 2 + DASH / 2; t <= BLOCK_W / 2 - DASH / 2; t += DASH + GAP) {
        lanes.flat(cx + t - DASH / 2, cz + BLOCK_D / 2 + STREET / 2 - LANE / 2, cx + t + DASH / 2, cz + BLOCK_D / 2 + STREET / 2 + LANE / 2, ABOVE, tones.lane);
      }
      for (let t = -BLOCK_D / 2 + DASH / 2; t <= BLOCK_D / 2 - DASH / 2; t += DASH + GAP) {
        lanes.flat(cx + BLOCK_W / 2 + STREET / 2 - LANE / 2, cz + t - DASH / 2, cx + BLOCK_W / 2 + STREET / 2 + LANE / 2, cz + t + DASH / 2, ABOVE, tones.lane);
      }
    }
  }
  base.mesh(group, { cast: false });
  paving.mesh(group, { cast: false });
  lanes.mesh(group, { cast: false });

  const { crown, trunk } = treeGeometries(THREE, tones);
  const crowns = kit.instanced(crown, planted.length, group);
  const trunks = kit.instanced(trunk, planted.length, group);
  const matrix = new THREE.Matrix4();
  const turn = new THREE.Quaternion();
  const up = new THREE.Vector3(0, 1, 0);
  planted.forEach(([x, z, size, angle], i) => {
    matrix.compose(new THREE.Vector3(x, KERB + ABOVE, z), turn.setFromAxisAngle(up, angle), new THREE.Vector3(size, size, size));
    crowns.setMatrixAt(i, matrix);
    trunks.setMatrixAt(i, matrix);
  });
  crowns.instanceMatrix.needsUpdate = true;
  trunks.instanceMatrix.needsUpdate = true;
  return { group, trees: planted.length };
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
