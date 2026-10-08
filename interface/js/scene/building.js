// The Building scene (handoff scene.md 5.4): a cutaway stack of rooms, one floor per agent, the planning agent (the Lobby)
// at the bottom, at most eight, a ground slab, a roof and five trees. It builds a group from a plain model and returns
// what the engine needs around it: the hit objects (a floor and, in the Lobby, the door), the HTML labels' anchors (the
// floor plates, the work-order tag), the markers of the waiting figures, the figures' typing motion and the
// opening (A5: the floors separate by GAP, once). No colour and no name is written here.

import { chair, counter, cabinet, desk, door, sheet, table, tray, wallLamp } from "./furniture.js";
import { figure, workingMotion } from "./figure.js";
import { windowColour, windowUnlit } from "./look.js";
import { plant, tree } from "./props.js";
import { plateNode, tagNode } from "./plates.js";

export const W = 6.4;
export const D = 4.4;
export const P = 2.6;
export const GAP = 1.0;
const BASE = 0.16;
const TREES = [[-5.4, 3.4], [5.0, -3.4], [-5.0, -3.2], [4.5, 4.3], [-3, 4.6]];

/** The y of floor i for a pitch (P + GAP when open). */
export function floorY(i, pitch = P + GAP) {
  return BASE + i * pitch;
}

/** Where a figure and its chair stand on a floor of the building, by state (scene.md 5.2). */
export function seating(state) {
  if (state === "waiting") return { chair: [1.4, -0.2, Math.PI + 0.4], figure: [2.35, -0.25, -0.5] };
  if (state === "off") return { chair: [1.4, -0.5, Math.PI], figure: null };
  return { chair: [1.4, -0.2, Math.PI], figure: [1.4, -0.32, Math.PI] };
}

function floor(kit, parent, f, y, selected, motions, markers, outlines) {
  const { THREE, palette } = kit;
  const T = palette.T;
  const g = new THREE.Group();
  g.position.set(0, y, 0);
  parent.add(g);
  kit.box(W, 0.18, D, 0, 0, 0, selected ? palette.bg : palette.mix(palette.bg, T.emphasis, 0.5), { parent: g, edges: true, shell: true });
  // The theme line along the slab's front and right edges belongs to the floor's outline: drawn only while the floor is hovered
  // or selected (the route selects the project here, not a floor), never as a standing line (WP-9.8).
  const front = [[-W / 2, 0.19, D / 2], [W / 2, 0.19, D / 2], [W / 2, 0.19, -D / 2]];
  const edge = kit.line(front, kit.themeLine, g);
  edge.visible = false;
  outlines.push({ id: `floor:${f.name}`, lines: [edge] });
  const c = new THREE.Group();
  c.position.y = 0.18;
  g.add(c);
  kit.box(W, P - 0.18, 0.1, 0, 0, -D / 2 + 0.05, palette.shell, { parent: c, edges: true, shell: true });
  kit.box(0.1, P - 0.18, D, -W / 2 + 0.05, 0, 0, palette.shell, { parent: c, edges: true, shell: true });
  const glass = windowColour(palette, f.window);
  for (const x of [-1.7, 0.3, 2.1]) kit.box(1.3, 0.85, 0.02, x, 0.9, -D / 2 + 0.11, glass, { parent: c, cast: false, unlit: windowUnlit(f.window) });
  wallLamp(kit, c, 1.3, 2.05, -D / 2 + 0.14, true);

  const state = f.state;
  const place = seating(state);
  const d = desk(kit, c, 1.3, -1.05, state, 1.8);
  tray(kit, c, 1.85, 0, -1.1, f.decisions, state === "waiting");
  chair(kit, c, place.chair[0], place.chair[1], place.chair[2]);
  let who = null;
  if (place.figure) {
    who = figure(kit, c, state, place.figure[0], place.figure[1], place.figure[2], `${f.name}:marker`);
    if (who.marker) markers.push({ key: who.marker.key, group: who.marker.group, restY: who.marker.restY });
  }
  if (state === "working") motions.push(workingMotion(who, d, palette));
  table(kit, c, -1.4, 0.4, 1.5, 0.75);
  for (let i = 0; i < Math.min(3, f.sheets); i++) sheet(kit, c, -1.4 + (i - 1) * 0.45, 0, 0.4, 0.1 * (i - 1) + 0.05);
  cabinet(kit, c, -2.75, -1.65, f.drawers, Math.PI / 2);
  plant(kit, c, W / 2 - 0.35, D / 2 - 0.35, 0.9);
  let doorGroup = null;
  if (f.lobby) {
    counter(kit, c, -1.2, 1.55);
    doorGroup = door(kit, c, -W / 2 + 0.13, 1.2);
  }
  return { group: g, door: doorGroup };
}

/**
 * Build the Building. model: {ready, selected, focus, more, tag: {floor, text}|null, floors: [{name, label, state,
 * window, decisions, sheets, drawers, lobby, tip, interactive}]} in order from the bottom. Returns {group, hits, labels, beacons,
 * markers, motions, tag, intro, outlines, selected, text, bounds}. `text(model)` rebuilds the labels and the tips alone, for a
 * model whose `structure` is the same (a floor's meters change on a poll: the scene itself is not built again).
 */
export function buildBuilding(kit, model) {
  const { THREE, palette } = kit;
  const T = palette.T;
  const group = new THREE.Group();
  const shownOf = (m) => (m.focus ? m.floors.filter((f) => f.name === m.focus) : m.floors);
  const shown = shownOf(model);
  const hits = [];
  const markers = [];
  const motions = [];
  const outlines = [];
  const floorGroups = [];
  const tagAnchor = new THREE.Vector3();
  const plateAnchors = [];   // where each floor's plate hangs: the floor's right edge, riding along while the floors separate
  const lobbyShown = shown.some((f) => f.lobby);
  if (!model.focus || lobbyShown) kit.box(W + 3, 0.16, D + 3, 0, 0, 0, palette.lot, { parent: group, edges: true });
  let tagMesh = null;
  let tagIndex = -1;
  shown.forEach((f, i) => {
    const y = floorY(i);
    const built = floor(kit, group, { ...f }, y, model.selected === f.name, motions, markers, outlines);
    floorGroups.push(built.group);
    if (!f.interactive) return;   // a placeholder floor while the data is loading: slabs only, nothing to point at
    hits.push({ object: built.group, id: `floor:${f.name}`, tip: f.tip });
    plateAnchors[i] = new THREE.Vector3(W / 2 + 0.2, y + 1.2, -D / 2);
    if (built.door) {
      hits.push({ object: built.door, id: "door", tip: "Control room · skills, costs, connections" });
    }
    if (model.tag && model.tag.floor === f.name) tagIndex = i;
  });
  if (tagIndex >= 0) {
    const y = floorY(tagIndex) + 0.18;
    tagMesh = new THREE.Group();
    tagMesh.position.set(-W / 2 + 0.6, y, D / 2 - 0.5);
    group.add(tagMesh);
    kit.box(0.5, 0.03, 0.34, 0, 0, 0, palette.bg, { parent: tagMesh });
    const outline = new THREE.LineSegments(kit.unitEdges, kit.adopt(new THREE.LineBasicMaterial({ color: T.text })));
    outline.scale.set(0.5, 0.03, 0.34);
    outline.position.y = 0.015;
    tagMesh.add(outline);
    tagAnchor.set(-W / 2 + 0.6, y + 0.45, D / 2 - 0.5);
  }
  if (!model.focus) {
    const top = BASE + (shown.length - 1) * (P + GAP) + P;
    const roof = kit.box(W + 0.2, 0.25, D + 0.2, 0, top, 0, T.emphasis, { parent: group, edges: true });
    TREES.forEach(([x, z], k) => tree(kit, group, x, z, k % 3 ? 1.15 : 1.35));
    group.userData.roof = roof;
  }

  // the words: the plates, the tag's label and the tooltips; worked out from a model of the same structure. There is no "Control room" label here: it is
  // drawn in the Lobby's room only, the header button is the Building's way to the Control room (WP-9.10).
  function text(m) {
    const labels = [];
    const tips = new Map();
    shownOf(m).forEach((f, i) => {
      if (!f.interactive) return;
      tips.set(`floor:${f.name}`, f.tip);
      // a plate for each floor beside the building (desktop and tablet); the phone shows one floor at a time and has the compact card in the
      // corner of the scene instead, which is the page's (WP-9.10: the maintainer's change of the plates was for the phone only)
      if (!m.focus && f.plate) {
        labels.push({
          id: `floor:${f.name}`, kind: "plate", place: "column", plate: f.plate, selected: m.selected === f.name,
          decisions: f.decisions, running: f.state === "working", anchor: plateAnchors[i], make: () => plateNode(f.plate),
        });
      }
    });
    if (tagMesh && m.tag) {
      labels.push({ id: "tag", kind: "tag", rank: 1, text: m.tag.text, decisions: 0, running: false, anchor: tagAnchor, make: tagNode });
    }
    return { labels, tips };
  }

  // A5: the floors separate, `t` from 0 (stacked) to 1 (open); the tag rides along with them
  const intro = model.focus || shown.length < 2 ? null : {
    apply(t) {
      const pitch = P + GAP * t;
      floorGroups.forEach((g, i) => {
        g.position.y = floorY(i, pitch);
        if (plateAnchors[i]) plateAnchors[i].y = floorY(i, pitch) + 1.2;
      });
      const roof = group.userData.roof;
      if (roof) roof.position.y = BASE + (shown.length - 1) * pitch + P + 0.125;
      if (tagMesh) {
        tagMesh.position.y = floorY(tagIndex, pitch) + 0.18;
        tagAnchor.y = tagMesh.position.y + 0.45;
      }
    },
  };
  const words = text(model);
  for (const hit of hits) hit.tip = words.tips.get(hit.id) !== undefined ? words.tips.get(hit.id) : hit.tip;
  return {
    group, hits, labels: words.labels, beacons: [], markers, motions, intro, outlines, selected: null, text,
    tag: tagMesh ? { group: tagMesh, floor: model.tag.floor, y: tagMesh.position.y } : null,
    bounds: new THREE.Box3().setFromObject(group),
  };
}

/** What the scene is made of, for a model: everything but the words (the tips, the tag's text). */
buildBuilding.structure = (model) => ({
  ready: model.ready, selected: model.selected, focus: model.focus, tag: model.tag ? model.tag.floor : null,
  floors: model.floors.map((f) => [f.name, f.state, f.window, f.decisions, f.lobby, f.sheets, f.drawers, f.interactive]),
});
