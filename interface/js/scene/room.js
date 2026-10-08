// The room scene of the Floor (handoff scene.md 5.5): one room with the agent at its desk, the inbox tray, a table with up to
// six sheets (each opens its document), a cabinet whose drawers follow the documents, a bookshelf, two plants, a window band,
// a lamp and the wall board. It builds a group from a plain model and returns the hits (the agent, the desk, the tray, the
// cabinet, the board and each sheet), the board's label anchor, the marker of a waiting figure and the typing motion.

import { chair, cabinet, desk, bookshelf, sheet, table, tray, wallLamp } from "./furniture.js";
import { figure } from "./figure.js";
import { plant } from "./props.js";
import { boardNode } from "./plates.js";

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
 * board}, board: {title, lines, dot}|null}. Returns {group, hits, labels, beacons, markers, motions, intro, bounds}.
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
  kit.line([[-W / 2, 0.21, D / 2], [W / 2, 0.21, D / 2], [W / 2, 0.21, -D / 2]], kit.themeLine, group);
  kit.box(W, H, 0.14, 0, 0.2, -D / 2 + 0.07, wall, { parent: group, edges: true });
  kit.box(0.14, H, D, -W / 2 + 0.07, 0.2, 0, wall, { parent: group, edges: true });
  const window = palette.windows[model.window];
  for (const x of [0.5, 2.1]) kit.box(1.3, 1.0, 0.02, x, 0.2 + 1.25 - 0.5, -D / 2 + 0.15, window, { parent: group, cast: false, unlit: model.window === "lit" });
  wallLamp(kit, group, 1.3, 0.2 + 2.55, -D / 2 + 0.16, true);

  const f = new THREE.Group();
  f.position.y = 0.2;
  group.add(f);
  const state = model.state;
  const d = desk(kit, f, 1.4, -1.35, state, 1.8);
  hits.push({ object: d.group, id: "desk", tip: model.tips.desk });
  const t = tray(kit, f, 2.05, 0, -1.3, model.decisions, state === "waiting");
  hits.push({ object: t, id: "tray", tip: model.tips.tray });
  const place = seating(state);
  chair(kit, f, place.chair[0], place.chair[1], place.chair[2]);
  let who = null;
  if (place.figure) {
    who = figure(kit, f, state, place.figure[0], place.figure[1], place.figure[2], "figure:marker");
    if (who.marker) markers.push(who.marker);
    hits.push({ object: who.group, id: "agent", tip: model.tips.agent });
  }
  if (state === "working") {
    motions.push({
      tick(seconds) {
        if (who) who.typing(seconds);
        if (d.scan) d.scan.position.y = 0.95 + 0.04 + ((seconds * 0.7) % 1) * 0.36;
      },
      rest() {
        if (who) who.rest();
        if (d.scan) d.scan.position.y = 0.95 + 0.2;
      },
    });
  }
  const board = kit.box(1.4, 0.95, 0.04, -1.0, 0.775, -D / 2 + 0.16, palette.bg, { parent: f, edges: true });
  hits.push({ object: board, id: "board", tip: model.tips.board });
  const c = cabinet(kit, f, -2.75, -1.75, model.drawers, Math.PI / 2);
  hits.push({ object: c, id: "cabinet", tip: model.tips.cabinet });
  bookshelf(kit, f, -W / 2 + 0.3, -0.55);
  table(kit, f, -1.2, 1.05, 1.8, 0.9);
  model.sheets.slice(0, 6).forEach((s, i) => {
    const col = i % 3;
    const g = sheet(kit, f, -1.75 + col * 0.5, 0, 0.85 + Math.floor(i / 3) * 0.46, 0.1 * (col - 1));
    hits.push({ object: g, id: `sheet:${s.path}`, tip: s.tip });
  });
  plant(kit, f, 2.75, 1.95, 1.15);
  plant(kit, f, 0.5, 2.0, 0.9);

  const labels = [];
  if (model.board) {
    labels.push({
      id: "board-label", kind: "board", rank: 0, title: model.board.title, lines: model.board.lines, dot: model.board.dot, decisions: 0, running: false,
      anchor: new THREE.Vector3(-1.0, 2.6, -D / 2 + 0.2), make: boardNode,
    });
  }
  return { group, hits, labels, beacons: [], markers, motions, intro: { zoom: 1.45 }, tag: null, bounds: new THREE.Box3().setFromObject(group) };
}
