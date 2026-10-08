// The room of a floor (handoff scene.md 5.4 and 5.5): the same room in the City's building, in the Building's cutaway and on the Floor and in
// the Lobby, because it is the same meshes (WP-9.11). A room is the floor's slab, its back wall and its left wall with the windows and the lamp,
// the desk with the agent, the inbox tray on the desk's corner, a table with up to six sheets (each opens its document), a cabinet whose drawers
// follow the documents, a bookshelf, two plants and, in the Lobby, the counter and the door. The tower (tower.js) puts a room in each of its floors
// and closes the building round them with the walls the City shows. No colour and no name is written here.

import { chair, counter, cabinet, desk, door, bookshelf, sheet, table, tray, wallLamp } from "./furniture.js";
import { figure, workingMotion } from "./figure.js";
import { windowColour, windowUnlit } from "./look.js";
import { plant } from "./props.js";

export const W = 6.4;
export const D = 4.8;
export const SLAB = 0.2;
export const H = 2.8;
export const P = SLAB + H;   // one floor, closed: the slab and its walls
export const GAP = 1.0;      // the floors open by this much
export const BASE = 0.2;

/** The y of floor i for a pitch (P + GAP when open). */
export function floorY(i, pitch = P + GAP) {
  return BASE + i * pitch;
}

/** Where a figure and its chair stand in the room, by state (scene.md 5.2). */
export function seating(state) {
  if (state === "waiting") return { chair: [1.5, -0.5, Math.PI + 0.4], figure: [2.55, -0.45, -0.5] };
  if (state === "off") return { chair: [1.5, -0.8, Math.PI], figure: null };
  return { chair: [1.5, -0.5, Math.PI], figure: [1.5, -0.62, Math.PI] };
}

/**
 * Draw the room of floor `f` into `parent` (a group at the floor's origin). f: {name, state, window, decisions, lobby, drawers, sheets: [{path, tip}]}.
 * ctx: {lot, selected, motions, markers, outlines}: `selected` is the floor the work order is on (its slab is lighter). Returns the parts a screen
 * points at: {agent, desk, tray, sheets: [{path, group}], door, frame (the slab and the two walls: the floor's outline)} and the setters that change the room in place (WP-9.11: a poll or the arrival of the
 * documents never builds a room again): setWindow(state), setDecisions(n, waiting), setSheets(list), setDrawers(n), setSelected(bool).
 */
export function fillFloor(kit, parent, f, ctx) {
  const { THREE, palette } = kit;
  const T = palette.T;
  const wall = palette.dark ? palette.mix(T.emphasis, T.text, 0.1) : palette.shell;
  // The floor's own enclosing parts (its slab and its back and left walls) are one group: what the outline of the floor is drawn from.
  const frame = new THREE.Group();
  parent.add(frame);
  const slabColour = (selected) => (selected ? palette.bg : palette.mix(palette.bg, T.emphasis, 0.45));
  const slab = kit.box(W, SLAB, D, 0, 0, 0, slabColour(ctx.selected), { parent: frame, edges: true, shell: true });
  // The theme line along the slab's front and right edges belongs to the floor's outline: drawn only for the floor the route selects (the Floor,
  // the Lobby), never as a standing line (WP-9.8).
  const edge = kit.line([[-W / 2, SLAB + 0.01, D / 2], [W / 2, SLAB + 0.01, D / 2], [W / 2, SLAB + 0.01, -D / 2]], kit.themeLine, parent);
  edge.visible = false;
  ctx.outlines.push({ id: `floor:${f.name}`, lines: [edge] });
  kit.box(W, H, 0.14, 0, SLAB, -D / 2 + 0.07, wall, { parent: frame, edges: true, shell: true });
  kit.box(0.14, H, D, -W / 2 + 0.07, SLAB, 0, wall, { parent: frame, edges: true, shell: true });
  const glass = windowColour(palette, f.window);
  const windows = [0.5, 2.1].map((x) => kit.box(1.3, 1.0, 0.02, x, SLAB + 0.75, -D / 2 + 0.15, glass, { parent, cast: false, unlit: windowUnlit(f.window) }));
  wallLamp(kit, parent, 1.3, SLAB + 2.55, -D / 2 + 0.16, true);

  const r = new THREE.Group();
  r.position.y = SLAB;
  parent.add(r);
  const state = f.state;
  const d = desk(kit, r, 1.4, -1.35, state, 1.8);
  const t = tray(kit, r, 2.05, 0, -1.3, f.decisions, state === "waiting");
  const place = seating(state);
  chair(kit, r, place.chair[0], place.chair[1], place.chair[2]);
  let who = null;
  if (place.figure) {
    who = figure(kit, r, state, place.figure[0], place.figure[1], place.figure[2], `${ctx.lot}:${f.name}:marker`);
    if (who.marker) ctx.markers.push({ key: who.marker.key, group: who.marker.group, restY: who.marker.restY });
  }
  if (state === "working") ctx.motions.push(workingMotion(who, d, palette));
  kit.box(1.4, 0.95, 0.04, -1.0, 0.775, -D / 2 + 0.16, palette.bg, { parent: r, edges: true });   // the wall board
  const cab = cabinet(kit, r, -2.75, -1.75, f.drawers, Math.PI / 2);
  bookshelf(kit, r, -W / 2 + 0.3, -0.55);
  table(kit, r, -1.2, 1.05, 1.8, 0.9);
  const sheets = [];
  const put = (s, i) => {
    const col = i % 3;
    return { path: s.path, group: sheet(kit, r, -1.75 + col * 0.5, 0, 0.85 + Math.floor(i / 3) * 0.46, 0.1 * (col - 1)) };
  };
  (f.sheets || []).slice(0, 6).forEach((s, i) => sheets.push(put(s, i)));
  plant(kit, r, 2.75, 1.95, 1.15);
  plant(kit, r, 0.5, 2.0, 0.9);
  let doorGroup = null;
  if (f.lobby) {
    counter(kit, r, -1.2, 1.55);
    doorGroup = door(kit, r, -W / 2 + 0.13, 1.2);
  }
  return {
    agent: who ? who.group : null, desk: d.group, tray: t, sheets, door: doorGroup, frame,
    setWindow(state) {
      const colour = windowColour(palette, state);
      for (const w of windows) w.material = windowUnlit(state) ? kit.unlit(colour) : kit.lit(colour);
    },
    setDecisions(count, waiting) {
      t.userData.setSheets(count, waiting);
    },
    /** The sheets on the table become `list`: a sheet that is still there stays (the same group), one that is gone leaves, a new one comes. */
    setSheets(list) {
      const want = list.slice(0, 6);
      want.forEach((s, i) => {
        if (sheets[i] && sheets[i].path === s.path) return;
        if (sheets[i]) r.remove(sheets[i].group);
        sheets[i] = put(s, i);
      });
      for (const gone of sheets.splice(want.length)) r.remove(gone.group);
    },
    setDrawers(n) {
      cab.userData.setDrawers(n);
    },
    setSelected(selected) {
      slab.material = kit.lit(slabColour(selected));
    },
  };
}
