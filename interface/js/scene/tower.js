// A building of the world (WP-9.11): one tower of floors that is the same set of meshes in the City, while it opens, in the Building, on the Floor.
//
// Closed, as the City shows it: a ring slab, a front wall and a right wall with their windows on every floor, a roof with its beacon, the
// door and the awning of the lobby. Inside each floor is its room (building.js), built when the person first asks to open the building and
// kept hidden until it opens: it stands behind the opaque walls, so adding it changes no pixel. Opening is one number per tower, `open` from
// 0 to 1, approached frame by frame as the prototype's `explode` was: the floors separate (the pitch goes from P to P + GAP through a smoothstep),
// the front walls, the ring slabs, the roof and the awning fade out, and the room is left as the cutaway the Building shows. The same number run
// backwards closes the building. A floor has its own number too, `vis`, approached faster: the floors that are not the one the person is on scale
// to nothing and come back (the Floor, the Lobby, a phone's one floor). Nothing is rebuilt to open, to close or to go into a floor.

import { BASE, D, GAP, H, P, SLAB, W, fillFloor, floorY } from "./building.js";
import { windowColour, windowUnlit } from "./look.js";
import { exclamation, plant } from "./props.js";
import { smooth } from "./prototype-motion.js";

const clamp01 = (t) => Math.max(0, Math.min(1, t));

/** What a tower is made of, for a lot: everything but the words (names, tips, plates, the sub line). */
export function towerStructure(lot) {
  return [lot.accepted, lot.runningTask !== null, lot.selected || null,
    lot.floors.map((f) => [f.name, f.state, f.window, f.decisions, f.lobby, f.drawers, f.interactive, (f.sheets || []).map((s) => s.path)])];
}

/** The y of a tower's roof at open progress `s` (already read through the smoothstep). */
export function roofY(n, s) {
  return floorY(n - 1, P + GAP * s) + P;
}

/** The bounds, in the world, of a tower at (cx, cz) with `n` floors at open progress `s`: the footprint with its porch, the roof with its beacon. */
export function towerBox(THREE, cx, cz, n, s) {
  return new THREE.Box3(new THREE.Vector3(cx - W / 2 - 1.2, 0, cz - D / 2 - 0.3), new THREE.Vector3(cx + W / 2 + 1.2, roofY(n, s) + 1.4, cz + D / 2 + 1.7));
}

/** The bounds of one floor (i) of a tower, open. */
export function floorBox(THREE, cx, cz, i) {
  const y = floorY(i);
  return new THREE.Box3(new THREE.Vector3(cx - W / 2 - 0.4, y - 0.3, cz - D / 2 - 0.3), new THREE.Vector3(cx + W / 2 + 0.4, y + P + 0.3, cz + D / 2 + 0.3));
}

/**
 * Build a tower for `lot` ({id, name, accepted, runningTask, tip, floors, selected, tag, ...}) standing at (cx, cz). Returns the tower: its
 * group, the floors' groups, `open` (the progress), `vis` (each floor's) and the functions the world calls.
 */
export function createTower(kit, lot, cx, cz) {
  const { THREE, palette } = kit;
  const T = palette.T;
  const n = lot.floors.length;
  const group = new THREE.Group();
  group.position.set(cx, 0, cz);
  const floorGroups = [];
  const shells = [];
  const outsideMarkers = [];
  const tower = {
    id: lot.id, lot, group, n, floorGroups, open: 0, target: 0, interior: false,
    vis: lot.floors.map(() => 1), visTarget: lot.floors.map(() => 1),
    motions: [], markers: [], outlines: [], inner: [], parts: [], beacon: null, tag: null,
    cardAnchor: new THREE.Vector3(cx, 0, cz), plateAnchors: [], boardAnchors: [], doorAnchors: [], tagAnchor: new THREE.Vector3(),
  };
  const fadeMats = [];
  const roofMats = [];

  // --- the closed shell of every floor --------------------------------------------------------------------------------------------
  lot.floors.forEach((f, i) => {
    const fg = new THREE.Group();
    fg.position.y = floorY(i, P);
    group.add(fg);
    floorGroups.push(fg);
    const shell = new THREE.Group();
    fg.add(shell);
    shells.push(shell);
    kit.box(W + 0.2, SLAB, D + 0.2, 0, 0, 0, T.emphasis, { parent: shell, edges: true });
    kit.box(W, H, 0.14, 0, SLAB, D / 2 - 0.07, palette.shell, { parent: shell, edges: true, shell: true });
    kit.box(0.14, H, D, W / 2 - 0.07, SLAB, 0, palette.shell, { parent: shell, edges: true, shell: true });
    const colour = windowColour(palette, f.window);
    const lit = windowUnlit(f.window);
    if (i === 0) {
      const glass = lit ? palette.warm : palette.glass;
      kit.box(W - 1.4, H - 0.9, 0.06, 0, SLAB + 0.1, D / 2 + 0.02, glass, { cast: false, parent: shell, unlit: true });
      [-1.5, -0.55, 0.55, 1.5].forEach((dx) => kit.box(0.06, H - 0.9, 0.08, dx, SLAB + 0.1, D / 2 + 0.04, T.emphasis, { parent: shell }));
      kit.box(0.06, H - 0.9, D - 0.8, W / 2 + 0.02, SLAB + 0.1, 0, glass, { cast: false, parent: shell, unlit: true });
      kit.box(2.6, 0.14, 1.3, 0, P - 0.45, D / 2 + 0.65, T.emphasis, { parent: shell, edges: true });
      [-1.15, 1.15].forEach((dx) => kit.box(0.1, P - 0.6, 0.1, dx, 0, D / 2 + 1.2, palette.bg, { parent: shell, edges: true }));
      kit.box(1.0, 1.7, 0.08, 0, SLAB, D / 2 + 0.06, palette.pale, { cast: false, parent: shell, unlit: true });
      kit.box(0.04, 1.7, 0.1, 0, SLAB, D / 2 + 0.08, T.textMuted, { parent: shell });
      kit.box(2.2, 0.08, 0.5, 0, 0, D / 2 + 1.7, T.emphasis, { parent: shell, edges: true });
      plant(kit, shell, -2.0, D / 2 + 1.0);
      plant(kit, shell, 2.0, D / 2 + 1.0);
    } else {
      const wy = SLAB + 0.55;
      const wh = H - 1.1;
      [-2.4, -1.2, 0, 1.2, 2.4].forEach((dx) => {
        kit.box(0.9, wh, 0.05, dx, wy, D / 2 + 0.02, colour, { cast: false, parent: shell, unlit: lit });
        kit.box(0.04, wh, 0.07, dx, wy, D / 2 + 0.04, T.emphasis, { cast: false, parent: shell });
      });
      [-1.5, 0, 1.5].forEach((dz) => {
        kit.box(0.05, wh, 0.9, W / 2 + 0.02, wy, dz, colour, { cast: false, parent: shell, unlit: lit });
        kit.box(0.07, wh, 0.04, W / 2 + 0.04, wy, dz, T.emphasis, { cast: false, parent: shell });
      });
    }
    if (f.decisions > 0 && lot.accepted) {
      const marker = exclamation(kit, fg, W / 2 + 0.9, 0.75, D / 2 - 0.4);
      outsideMarkers[i] = marker;
      tower.markers.push({ key: `${lot.id}:${i}`, group: marker, restY: 0.75 });
    }
  });

  // --- the roof (it fades with the opening and does not come back: the top floor's room is open like the others) ----------------------------
  const roof = new THREE.Group();
  group.add(roof);
  kit.box(W + 0.3, 0.3, D + 0.3, 0, 0, 0, T.emphasis, { parent: roof, edges: true, shell: true });
  kit.box(W + 0.3, 0.3, 0.1, 0, 0.3, D / 2 + 0.1, palette.shell, { parent: roof, edges: true, shell: true });
  kit.box(0.1, 0.3, D + 0.3, W / 2 + 0.1, 0.3, 0, palette.shell, { parent: roof, edges: true, shell: true });
  kit.box(1.6, 0.7, 1.2, -1.4, 0.3, -0.9, T.emphasis, { parent: roof, edges: true });
  kit.box(1.0, 0.5, 1.0, 0.4, 0.3, -1.0, palette.bg, { parent: roof, edges: true });
  if (lot.runningTask !== null && lot.accepted) {
    const material = kit.adopt(new THREE.MeshBasicMaterial({ color: T.theme, transparent: true, opacity: 1 }));
    const ring = new THREE.Mesh(kit.track(new THREE.TorusGeometry(0.5, 0.1, 6, 16)), material);
    ring.rotation.x = Math.PI / 2;
    ring.position.set(W / 2 - 1.0, 1.2, D / 2 - 1.0);
    roof.add(ring);
    kit.box(0.14, 0.6, 0.14, W / 2 - 1.0, 0.3, D / 2 - 1.0, T.textMuted, { parent: roof });
    tower.beacon = { ring, material, id: lot.id, fade: 1 };
  }

  // The walls, the ring slabs, the awning and the roof fade as the building opens: each has materials of its own (a clone of the kit's shared
  // one, same tone), so fading this tower touches no other.
  const own = new Map();
  const claim = (root, list) => root.traverse((node) => {
    if (!node.material || node === (tower.beacon && tower.beacon.ring)) return;
    if (!own.has(node.material)) {
      const clone = node.material.clone();
      clone.transparent = true;
      own.set(node.material, clone);
      list.push(clone);
    }
    node.material = own.get(node.material);
  });
  shells.forEach((shell) => claim(shell, fadeMats));
  claim(roof, roofMats);
  const setOpacity = (list, value) => {
    for (const m of list) {
      m.opacity = value;
      m.depthWrite = value >= 0.999;
    }
  };

  // --- the room of every floor, when the building is first asked to open --------------------------------------------------------------
  // The work-order tag stands on a floor of the open building: made when the rooms are, moved when the work order moves.
  tower.setTag = (tag) => {
    const index = tag ? tower.lot.floors.findIndex((f) => f.name === tag.floor) : -1;
    if (!tower.interior || index < 0) {
      if (tower.tag && index < 0) {
        group.remove(tower.tag.group);
        tower.tag = null;
      }
      return;
    }
    if (!tower.tag) {
      const mark = new THREE.Group();
      group.add(mark);
      kit.box(0.5, 0.03, 0.34, 0, 0, 0, palette.bg, { parent: mark });
      const outline = new THREE.LineSegments(kit.unitEdges, kit.adopt(new THREE.LineBasicMaterial({ color: T.text })));
      outline.scale.set(0.5, 0.03, 0.34);
      outline.position.y = 0.015;
      mark.add(outline);
      tower.tag = { group: mark, floor: tag.floor, index };
    }
    tower.tag.floor = tag.floor;
    tower.tag.index = index;
    tower.apply();
  };

  tower.ensureInterior = () => {
    if (tower.interior) return false;
    tower.interior = true;
    lot.floors.forEach((f, i) => {
      const inner = new THREE.Group();
      inner.visible = tower.open > 0;
      floorGroups[i].add(inner);
      tower.inner[i] = inner;
      if (!f.interactive) return;
      tower.parts[i] = fillFloor(kit, inner, f, { lot: lot.id, selected: lot.selected === f.name, motions: tower.motions, markers: tower.markers, outlines: tower.outlines });
    });
    tower.setTag(tower.lot.tag);
    tower.apply();
    return true;
  };

  // --- the opening: every position, every fade, from one number --------------------------------------------------------------------------
  /** Put the tower in the state of `tower.open` and of each floor's `vis`. */
  tower.apply = () => {
    const s = smooth(tower.open);
    const pitch = P + GAP * s;
    floorGroups.forEach((g, i) => {
      g.position.y = floorY(i, pitch);
      g.scale.setScalar(Math.max(tower.vis[i], 0.001));
      g.visible = tower.vis[i] > 0.01;
    });
    roof.position.y = roofY(n, s);
    const fade = 1 - clamp01(s / 0.55);
    const roofFade = 1 - clamp01(s / 0.7);
    setOpacity(fadeMats, fade);
    setOpacity(roofMats, roofFade);
    shells.forEach((shell) => { shell.visible = fade > 0.01; });
    roof.visible = roofFade > 0.01 && tower.vis[n - 1] > 0.01;
    if (tower.beacon) tower.beacon.fade = roofFade;
    outsideMarkers.forEach((marker) => {
      if (!marker) return;
      const k = clamp01(1 - s * 3);
      marker.scale.setScalar(Math.max(k, 0.0001));
      marker.visible = k > 0.01;
    });
    tower.inner.forEach((inner) => { if (inner) inner.visible = tower.open > 0; });
    if (tower.tag) {
      tower.tag.group.position.set(-W / 2 + 0.6, floorY(tower.tag.index, pitch) + SLAB, D / 2 - 0.5);
      tower.tagAnchor.set(cx - W / 2 + 0.6, floorY(tower.tag.index, pitch) + SLAB + 0.45, cz + D / 2 - 0.5);
    }
    tower.lot.floors.forEach((f, i) => {
      const y = floorY(i, pitch);
      (tower.plateAnchors[i] = tower.plateAnchors[i] || new THREE.Vector3()).set(cx + W / 2 + 0.2, y + 1.2, cz - D / 2);
      (tower.boardAnchors[i] = tower.boardAnchors[i] || new THREE.Vector3()).set(cx - 1.0, y + 2.6, cz - D / 2 + 0.2);
      (tower.doorAnchors[i] = tower.doorAnchors[i] || new THREE.Vector3()).set(cx - W / 2 + 0.2, y + 3.0, cz + 1.2);
    });
    tower.cardAnchor.set(cx, roofY(n, s) + 2.4, cz);
  };

  /** The y the work-order tag rests at when the building is open: where the tag goes to, whatever the progress now. */
  tower.tagRestY = () => (tower.tag ? floorY(tower.tag.index, P + GAP) + SLAB : null);
  tower.apply();
  return tower;
}
