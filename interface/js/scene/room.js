// The room scene of the Floor (handoff scene.md 5.5): one room with the agent at its desk, the inbox tray, a table with up to
// six sheets (each opens its document), a cabinet whose drawers follow the documents, a bookshelf, two plants, a window band,
// a lamp and the wall board. It builds a group from a plain model and returns the hits (the agent, the desk, the tray, the
// cabinet, the board and each sheet), the board's label anchor, the marker of a waiting figure and the typing motion.

import { chair, cabinet, desk, door, bookshelf, sheet, table, tray, wallLamp } from "./furniture.js";
import { figure, workingMotion } from "./figure.js";
import { windowColour, windowUnlit } from "./look.js";
import { plant } from "./props.js";
import { boardNode, doorNode } from "./plates.js";

export const W = 6.4;
export const D = 4.8;
export const H = 2.8;

/** Where the figure and its chair stand in the room, by state (scene.md 5.2). */
export function seating(state) {
  if (state === "waiting") return { chair: [1.5, -0.5, Math.PI + 0.4], figure: [2.55, -0.45, -0.5] };
  if (state === "off") return { chair: [1.5, -0.8, Math.PI], figure: null };
  return { chair: [1.5, -0.5, Math.PI], figure: [1.5, -0.62, Math.PI] };
}

/**
 * Build the room. model: {ready, state, window, decisions, drawers, sheets: [{path, tip}], tips: {agent, desk, tray, cabinet,
 * board}, board: {title, lines, dot}|null}. Returns {group, hits, labels, beacons, markers, motions, intro, outlines, selected, text,
 * bounds}. `text(model)` rebuilds the labels and the tooltips alone, for a model of the same structure (a poll that changed the
 * board's words must not build the room again).
 */
export function buildRoom(kit, model) {
  const { THREE, palette } = kit;
  const T = palette.T;
  const group = new THREE.Group();
  const wall = palette.dark ? palette.mix(T.emphasis, T.text, 0.1) : palette.shell;
  const hits = [];
  const markers = [];
  const motions = [];
  kit.box(W, 0.2, D, 0, 0, 0, palette.mix(palette.bg, T.emphasis, 0.45), { parent: group, edges: true });
  // the floor's outline: the route selects this floor, so it is drawn while the room is on screen (WP-9.8)
  const edge = kit.line([[-W / 2, 0.21, D / 2], [W / 2, 0.21, D / 2], [W / 2, 0.21, -D / 2]], kit.themeLine, group);
  edge.visible = false;
  kit.box(W, H, 0.14, 0, 0.2, -D / 2 + 0.07, wall, { parent: group, edges: true });
  kit.box(0.14, H, D, -W / 2 + 0.07, 0.2, 0, wall, { parent: group, edges: true });
  const glass = windowColour(palette, model.window);
  for (const x of [0.5, 2.1]) kit.box(1.3, 1.0, 0.02, x, 0.2 + 1.25 - 0.5, -D / 2 + 0.15, glass, { parent: group, cast: false, unlit: windowUnlit(model.window) });
  wallLamp(kit, group, 1.3, 0.2 + 2.55, -D / 2 + 0.16, true);

  const f = new THREE.Group();
  f.position.y = 0.2;
  group.add(f);
  const state = model.state;
  const d = desk(kit, f, 1.4, -1.35, state, 1.8);
  hits.push({ object: d.group, id: "desk", tip: model.tips.desk, shape: true });
  const t = tray(kit, f, 2.05, 0, -1.3, model.decisions, state === "waiting");
  hits.push({ object: t, id: "tray", tip: model.tips.tray, shape: true });
  const place = seating(state);
  chair(kit, f, place.chair[0], place.chair[1], place.chair[2]);
  let who = null;
  if (place.figure) {
    who = figure(kit, f, state, place.figure[0], place.figure[1], place.figure[2], "figure:marker");
    if (who.marker) markers.push(who.marker);
    hits.push({ object: who.group, id: "agent", tip: model.tips.agent, shape: true });
  }
  if (state === "working") motions.push(workingMotion(who, d, palette));
  // One object per destination (WP-9.8): the figure opens the Agent tab, the desk the Desk tab, the tray the Inbox and a sheet its
  // document. The wall board and the cabinet are scenery: no hit, no outline, no tooltip, nothing opens.
  kit.box(1.4, 0.95, 0.04, -1.0, 0.775, -D / 2 + 0.16, palette.bg, { parent: f, edges: true });
  cabinet(kit, f, -2.75, -1.75, model.drawers, Math.PI / 2);
  bookshelf(kit, f, -W / 2 + 0.3, -0.55);
  table(kit, f, -1.2, 1.05, 1.8, 0.9);
  model.sheets.slice(0, 6).forEach((s, i) => {
    const col = i % 3;
    const g = sheet(kit, f, -1.75 + col * 0.5, 0, 0.85 + Math.floor(i / 3) * 0.46, 0.1 * (col - 1));
    hits.push({ object: g, id: `sheet:${s.path}`, tip: s.tip, shape: true });
  });
  plant(kit, f, 2.75, 1.95, 1.15);
  plant(kit, f, 0.5, 2.0, 0.9);

  const doorAt = new THREE.Vector3(-W / 2 + 0.2, 3.0, 1.2);
  if (model.door) {   // the Lobby's room: the door to the Control room on the left wall (scene.md 5.1)
    hits.push({ object: door(kit, f, -W / 2 + 0.13, 1.2), id: "lobby-door", tip: "Control room · skills, costs, connections" });
  }
  const boardAt = new THREE.Vector3(-1.0, 2.6, -D / 2 + 0.2);
  function text(m) {
    const labels = [];
    const tips = new Map([["agent", m.tips.agent], ["desk", m.tips.desk], ["tray", m.tips.tray], ["lobby-door", m.tips.door || "Control room · skills, costs, connections"]]);
    m.sheets.slice(0, 6).forEach((sh) => tips.set(`sheet:${sh.path}`, sh.tip));
    if (m.door) labels.push({ id: "door-label", kind: "door", rank: 5, text: "Control room", decisions: 0, running: false, anchor: doorAt, make: doorNode });
    if (m.board) {
      labels.push({ id: "board-label", kind: "board", rank: 0, title: m.board.title, lines: m.board.lines, dot: m.board.dot, decisions: 0, running: false, anchor: boardAt, make: boardNode });
    }
    return { labels, tips };
  }
  const words = text(model);
  for (const hit of hits) if (words.tips.get(hit.id) !== undefined) hit.tip = words.tips.get(hit.id);
  return {
    group, hits, labels: words.labels, beacons: [], markers, motions, intro: { zoom: 1.45 }, tag: null, text,
    outlines: [{ id: "room", lines: [edge] }], selected: "room", bounds: new THREE.Box3().setFromObject(group),
  };
}

/** What the room is made of, for a model: everything but the words (the tips, the board's lines). */
buildRoom.structure = (model) => ({
  ready: model.ready, state: model.state, window: model.window, decisions: model.decisions, drawers: model.drawers,
  sheets: model.sheets.slice(0, 6).map((s) => s.path), door: Boolean(model.door),
});
