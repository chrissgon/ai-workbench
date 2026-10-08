// The Control room's small scene (handoff scene.md 5.6, control-room.md "Small scene"): a server room with three racks
// of seven units and an LED on each, a wall screen with seven bars and a console desk. It draws facts, never progress, and
// nothing in it moves. The LEDs are the `connections` facts (each class, then each secret, then the image: success lit,
// error when missing; a slot with no fact is off), the bars are `costs.rows` summed by day over the chart's seven days, scaled to
// the largest day. Hover shows a tooltip, a click opens the tab that holds the same facts as HTML (racks: Connections, wall
// screen: Costs, console: Skills). There are no labels and no text in 3D.
//
// What it shows is worked out by sceneModel in control-model.js (pure, tested under Node); the builder takes the engine's kit, as the City's does, and
// registers itself as the scene kind "server" through the engine's BUILDERS, so the engine is not edited.

import { BUILDERS } from "../scene/engine.js";
import { plant } from "../scene/props.js";
import { RACKS, UNITS } from "./control-model.js";

// --- the builder -------------------------------------------------------------------------------------------------------------

const W = 6.4;
const D = 4.8;
const H = 2.8;

/** The tool's task chair (scene.md 5.1), facing the desk that lies toward negative z: its back is on the positive side. */
function chair(kit, parent, x, z) {
  const { THREE, palette } = kit;
  const g = new THREE.Group();
  g.position.set(x, 0, z);
  parent.add(g);
  for (let k = 0; k < 5; k++) {
    const arm = new THREE.Group();
    arm.rotation.y = (k * 2 * Math.PI) / 5;
    g.add(arm);
    kit.box(0.3, 0.04, 0.05, 0.15, 0.07, 0, palette.metal, { parent: arm });
    kit.mesh(new THREE.SphereGeometry(0.035, 6, 4), palette.ink, 0.3, 0.035, 0, { parent: arm });
  }
  kit.cyl(0.03, 0.03, 0.34, 6, palette.metal, 0, 0.08, 0, { parent: g });
  kit.box(0.5, 0.08, 0.48, 0, 0.4, 0, palette.ink, { parent: g });
  kit.box(0.46, 0.62, 0.08, 0, 0.48, 0.24, palette.ink, { parent: g });
  kit.box(0.05, 0.2, 0.05, 0, 0.4, 0.2, palette.metal, { parent: g });
  for (const sx of [-0.27, 0.27]) kit.box(0.05, 0.04, 0.32, sx, 0.62, 0, palette.ink, { parent: g });
  return g;
}

function rack(kit, parent, spec, model, r) {
  const { THREE, palette } = kit;
  const T = palette.T;
  const x = -W / 2 + 0.75;
  const g = new THREE.Group();
  g.position.set(x, 0, spec.z);
  parent.add(g);
  kit.box(0.9, 2.2, 1.0, 0, 0, 0, palette.bg, { parent: g, edges: true });
  kit.box(0.02, 2.0, 0.86, 0.46, 0.1, 0, palette.ink, { parent: g });
  const unit = palette.mix(palette.ink, palette.bg, 0.15);
  for (let u = 0; u < UNITS; u++) {
    const y = 0.38 + 0.27 * u;
    kit.box(0.02, 0.19, 0.78, 0.47, y, 0, unit, { parent: g, cast: false });
    // the slot bar, then the LED: the first fact is on the top unit of the first rack
    kit.box(0.03, 0.03, 0.3, 0.48, y + 0.08, -0.15, T.border, { parent: g, cast: false });
    const state = model.leds[r * UNITS + (UNITS - 1 - u)];
    const colour = state === "ok" ? T.success : state === "bad" ? T.error : T.border;
    kit.box(0.03, 0.05, 0.05, 0.48, y + 0.07, 0.3, colour, { parent: g, cast: false, unlit: true });
  }
  return g;
}

/** Build the server room. model: sceneModel(). Returns what the engine needs, like buildCity. */
export function buildServer(kit, model) {
  const { THREE, palette } = kit;
  const T = palette.T;
  const group = new THREE.Group();
  const shell = palette.dark ? palette.mix(T.emphasis, T.text, 0.1) : palette.shell;
  kit.box(W, 0.2, D, 0, 0, 0, palette.mix(palette.bg, T.emphasis, 0.45), { parent: group, edges: true });
  kit.line([[-W / 2, 0.21, D / 2], [W / 2, 0.21, D / 2], [W / 2, 0.21, -D / 2]], kit.themeLine, group);
  kit.box(W, H, 0.14, 0, 0.2, -D / 2 + 0.07, shell, { parent: group, edges: true });
  kit.box(0.14, H, D, -W / 2 + 0.07, 0.2, 0, shell, { parent: group, edges: true });
  const room = new THREE.Group();
  room.position.y = 0.2;
  group.add(room);

  const hits = [];
  RACKS.forEach((spec, r) => hits.push({ object: rack(kit, room, spec, model, r), id: spec.id, tip: model.racks[r].tip }));

  const wall = new THREE.Group();
  room.add(wall);
  const sz = -D / 2 + 0.17;
  kit.box(3.0, 1.4, 0.06, 1.2, 1.05, sz, palette.ink, { parent: wall });
  model.bars.forEach((v, i) => {
    if (v > 0) kit.box(0.26, 1.05 * v, 0.02, i * 0.4, 1.17, sz + 0.04, T.theme, { parent: wall, cast: false, unlit: true });
  });
  hits.push({ object: wall, id: "wall", tip: model.tips.wall });

  const desk = new THREE.Group();
  room.add(desk);
  kit.box(2.4, 0.06, 0.85, 1.2, 0.72, 0.55, palette.deskTop, { parent: desk, edges: true });
  kit.box(2.4, 0.72, 0.06, 1.2, 0, 0.55 - 0.4, palette.deskTop, { parent: desk });
  for (const lx of [0.08, 2.32]) kit.cyl(0.025, 0.025, 0.72, 6, palette.metal, lx, 0, 0.55 + 0.36, { parent: desk });
  for (const mx of [0.7, 1.7]) {
    kit.box(0.04, 0.2, 0.04, mx, 0.78, 0.45, palette.metal, { parent: desk });
    kit.box(0.76, 0.48, 0.05, mx, 0.96, 0.45, palette.ink, { parent: desk });
    kit.box(0.68, 0.4, 0.01, mx, 1.0, 0.485, palette.screenOff, { parent: desk, cast: false });
  }
  chair(kit, desk, 1.2, 1.4);
  hits.push({ object: desk, id: "console", tip: model.tips.console });
  plant(kit, room, 2.75, 1.95, 1.15);

  return { group, hits, labels: [], beacons: [], markers: [] };
}

BUILDERS.server = buildServer;
