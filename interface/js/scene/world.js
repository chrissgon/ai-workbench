// The world (WP-9.11): the one scene of the City, the Building, the Floor and the Lobby. It is the prototype's single world: the lots, the streets,
// the trees and one tower per project, each tower's floors holding their rooms. A screen does not change scenes; it sets targets on this world
// (which building is open, which floor the person is on) and the world approaches them frame by frame: the building the person clicked opens where
// it stands while the camera flies in, the other floors of a building shrink to nothing when a floor is entered, and every step reverses. The other
// buildings and the city's furniture stay where they are, drawn, throughout. A model that differs in its words, in the state of a floor, or in the
// targets changes the world in place (`update`); only a change of the set of lots builds it again.
//
// model: {ready, selectedId, marked, outlined, focus, floor, frame, room, lots: [{id, name, accepted, decisions, runningTask, tip, sub, floors: [{name,
// label, state, window, decisions, lobby, sheets: [{path, tip}], drawers, tip, interactive, plate}], selected, tag: {floor, text}|null}]}.
// `focus` is the building that is open; `floor` the floor of it the route is on (the Floor, the Lobby), with `room` the words of that room
// ({tips: {agent, desk, tray}, board, door}); `frame` the one floor a phone shows; `marked` the id of the hit that keeps a selection outline.

import { lotAt, buildGround } from "./city.js";
import { createTower, floorBox, towerBox, towerStructure } from "./tower.js";
import { EXPLODE_RATE, approach } from "./prototype-motion.js";
import { boardNode, doorNode, plateNode, tagNode } from "./plates.js";

const SETTLED = 0.005;       // a tower's open progress that is this near 0 or 1 is there
const VIS_RATE = 8;          // the prototype's `f.vis += (target - vis) * (1 - exp(-dt * 8))`
const VIS_SETTLED = 0.01;

export function buildWorld(kit, model) {
  const { THREE } = kit;
  const group = new THREE.Group();
  const lots = model.lots;
  const ground = buildGround(kit, lots.length);
  group.add(ground.group);
  const towers = new Map();
  let focus = null;      // the building that is open: set by `setFocus` (the engine, or the test), never by the model alone
  let floorSel = null;   // the floor the route is on
  let frameSel = null;   // the one floor a phone shows
  let current = model;
  const structures = new Map();

  const content = {
    kind: "world", live: true, group, towers, hits: [], labels: [], beacons: [], markers: [], motions: [], outlines: [], tag: null,
    selected: model.outlined || null, marked: model.marked || null, intro: null,
  };

  function place(lot, i) {
    const { x, z } = lotAt(i, lots.length);
    const old = towers.get(lot.id);
    const tower = createTower(kit, lot, x, z);
    if (old) {
      tower.open = old.open;
      tower.target = old.target;
      tower.vis = lot.floors.map((f) => (old.vis[old.lot.floors.findIndex((o) => o.name === f.name)] !== undefined ? old.vis[old.lot.floors.findIndex((o) => o.name === f.name)] : 1));
      tower.visTarget = lot.floors.map((f) => (old.visTarget[old.lot.floors.findIndex((o) => o.name === f.name)] !== undefined ? old.visTarget[old.lot.floors.findIndex((o) => o.name === f.name)] : 1));
      group.remove(old.group);
      if (old.interior) tower.ensureInterior();
    }
    towers.set(lot.id, tower);
    group.add(tower.group);
    structures.set(lot.id, JSON.stringify(towerStructure(lot)));
    tower.apply();
    return tower;
  }
  lots.forEach((lot, i) => place(lot, i));

  const floorIndex = (tower) => {
    const name = floorSel || frameSel;
    return name ? tower.lot.floors.findIndex((f) => f.name === name) : -1;
  };

  /** The floor targets: in the open building, the floor the person is on stays and the others go to nothing; everywhere else all are drawn. */
  function aimFloors() {
    for (const tower of towers.values()) {
      const only = tower.id === focus ? floorIndex(tower) : -1;
      tower.visTarget = tower.lot.floors.map((f, i) => (only < 0 || i === only ? 1 : 0));
    }
  }

  /** Make the arrays the engine reads (hits, markers, motions, outlines, beacons) from the towers as they are now. */
  function collect() {
    const hits = [];
    const markers = [];
    const motions = [];
    const outlines = [];
    const beacons = [];
    lots.forEach((lot, i) => {
      const tower = towers.get(lot.id);
      markers.push(...tower.markers);
      motions.push(...tower.motions);
      outlines.push({ id: lot.id, lines: [ground.edges[i]] }, ...tower.outlines);
      if (tower.beacon) beacons.push(tower.beacon);
      if (focus === lot.id && tower.interior) {
        const only = floorSel ? tower.lot.floors.findIndex((f) => f.name === floorSel) : -1;
        const room = current.room || {};
        lot.floors.forEach((f, k) => {
          const parts = tower.parts[k];
          if (!f.interactive || !parts || tower.vis[k] <= VIS_SETTLED) return;
          if (only >= 0) {
            if (k !== only) return;
            const tips = room.tips || {};
            if (parts.agent) hits.push({ object: parts.agent, id: "agent", tip: tips.agent || "", moves: f.state === "working" });
            hits.push({ object: parts.desk, id: "desk", tip: tips.desk || "", moves: f.state === "working" });
            hits.push({ object: parts.tray, id: "tray", tip: tips.tray || "" });
            for (const s of parts.sheets) hits.push({ object: s.group, id: `sheet:${s.path}`, tip: (f.sheets.find((x) => x.path === s.path) || {}).tip || s.path });
            if (parts.door) hits.push({ object: parts.door, id: "lobby-door", tip: room.doorTip || "Control room · skills, costs, connections" });
          } else {
            hits.push({ object: tower.floorGroups[k], id: `floor:${f.name}`, tip: f.tip });
            if (parts.door) hits.push({ object: parts.door, id: "door", tip: "Control room · skills, costs, connections" });
          }
        });
      } else if (!focus && lot.floors.some((f) => f.interactive)) {
        hits.push({ object: tower.group, id: lot.id, tip: lot.tip, pad: 0.06 });
      }
    });
    for (const [key, list] of [["hits", hits], ["markers", markers], ["motions", motions], ["outlines", outlines], ["beacons", beacons]]) {
      content[key].length = 0;
      content[key].push(...list);
    }
    const focused = focus ? towers.get(focus) : null;
    content.tag = focused && focused.tag ? { group: focused.tag.group, floor: focused.tag.floor, y: focused.tagRestY() } : null;
  }

  /** The words: the cards of the City, or the plates and the tag of the open building, the board and the door of a room, and every tooltip. */
  content.text = (m) => {
    const labels = [];
    const tips = new Map();
    m.lots.forEach((lot) => {
      const tower = towers.get(lot.id);
      if (!tower) return;
      tips.set(lot.id, lot.tip);
      for (const f of lot.floors) tips.set(`floor:${f.name}`, f.tip);
      if (!m.focus) {
        labels.push({
          id: lot.id, kind: "card", name: lot.name, decisions: lot.decisions, running: lot.runningTask !== null, sub: lot.sub,
          selected: lot.id === m.selectedId, accepted: lot.accepted, anchor: tower.cardAnchor,
        });
      } else if (m.focus === lot.id) {
        const index = m.floor ? lot.floors.findIndex((f) => f.name === m.floor) : -1;
        if (index >= 0) {
          const room = m.room || {};
          const tips2 = room.tips || {};
          tips.set("agent", tips2.agent || "");
          tips.set("desk", tips2.desk || "");
          tips.set("tray", tips2.tray || "");
          tips.set("lobby-door", room.doorTip || "Control room · skills, costs, connections");
          for (const s of lot.floors[index].sheets || []) tips.set(`sheet:${s.path}`, s.tip || s.path);
          if (room.board) labels.push({ id: "board-label", kind: "board", rank: 0, title: room.board.title, lines: room.board.lines, dot: room.board.dot, decisions: 0, running: false, anchor: tower.boardAnchors[index], make: boardNode });
          if (room.door) labels.push({ id: "door-label", kind: "door", rank: 5, text: "Control room", decisions: 0, running: false, anchor: tower.doorAnchors[index], make: doorNode });
        } else {
          // a plate for each floor beside the building (desktop and tablet); the phone has the compact card in the corner instead, which is the page's
          if (!m.frame) {
            lot.floors.forEach((f, i) => {
              if (!f.interactive || !f.plate) return;
              labels.push({
                id: `floor:${f.name}`, kind: "plate", place: "column", plate: f.plate, selected: lot.selected === f.name,
                decisions: f.decisions, running: f.state === "working", anchor: tower.plateAnchors[i], make: () => plateNode(f.plate),
              });
            });
          }
          if (tower.tag && lot.tag) labels.push({ id: "tag", kind: "tag", rank: 1, text: lot.tag.text, decisions: 0, running: false, anchor: tower.tagAnchor, make: tagNode });
        }
      }
    });
    return { labels, tips };
  };

  /** The open building is the focus: its rooms are built and it starts to open (or close, for `null`). `instant` puts every tower there at once. */
  content.setFocus = (id, instant = false) => {
    focus = id || null;
    for (const tower of towers.values()) {
      tower.target = tower.id === focus ? 1 : 0;
      if (tower.target === 1) tower.ensureInterior();
    }
    aimFloors();
    if (instant) content.finish(); else collect();
  };

  /** The floor the route is on and the one floor a phone shows: the other floors of the open building go to nothing (or come back). */
  content.setFloors = (floor, frame, instant = false) => {
    floorSel = floor || null;
    frameSel = frame || null;
    aimFloors();
    if (instant) content.finish(); else collect();
  };

  const settled = (tower) => tower.open === tower.target && tower.vis.every((v, i) => v === tower.visTarget[i]);

  /** Move every tower and every floor toward its target by `dt` seconds, as the prototype moved `explode` and `vis`. Returns true while any is still moving. */
  content.step = (dt) => {
    let moving = false;
    for (const tower of towers.values()) {
      if (settled(tower)) continue;
      if (tower.open !== tower.target) {
        tower.open = approach(tower.open, tower.target, dt, EXPLODE_RATE);
        if (Math.abs(tower.open - tower.target) <= SETTLED) tower.open = tower.target; else moving = true;
      }
      tower.vis = tower.vis.map((v, i) => {
        if (v === tower.visTarget[i]) return v;
        const next = approach(v, tower.visTarget[i], dt, VIS_RATE);
        if (Math.abs(next - tower.visTarget[i]) <= VIS_SETTLED) return tower.visTarget[i];
        moving = true;
        return next;
      });
      tower.apply();
    }
    if (!moving) collect();   // a tower that has closed, opened or shrunk settles its hits
    return moving;
  };
  content.moving = () => [...towers.values()].some((t) => !settled(t));
  content.finish = () => {
    for (const tower of towers.values()) {
      tower.open = tower.target;
      tower.vis = [...tower.visTarget];
      tower.apply();
    }
    collect();
  };

  /**
   * Change the world to a model of the same lots, in place. Returns {rebuild, structure, focus, floors}: `rebuild` when the lots are not the
   * same (the engine builds the world again), `structure` when a tower was made again, `focus` when the open building changed, `floors` when the
   * floor the route is on (or a phone shows) changed.
   */
  content.update = (m) => {
    const same = m.lots.length === lots.length && m.lots.every((lot, i) => lot.id === lots[i].id);
    if (!same) return { rebuild: true };
    let structure = false;
    m.lots.forEach((lot, i) => {
      const key = JSON.stringify(towerStructure(lot));
      lots[i] = lot;
      if (structures.get(lot.id) !== key) {
        place(lot, i);
        structure = true;
      } else {
        const tower = towers.get(lot.id);
        tower.lot = lot;
        tower.setTag(lot.tag);
      }
    });
    current = m;
    content.selected = m.outlined || null;
    content.marked = m.marked || null;
    const focusChanged = (m.focus || null) !== focus;
    const floorsChanged = (m.floor || null) !== floorSel || (m.frame || null) !== frameSel;
    floorSel = m.floor || null;
    frameSel = m.frame || null;
    if (focusChanged) content.setFocus(m.focus || null);
    else {
      for (const tower of towers.values()) if (tower.target === 1) tower.ensureInterior();
      aimFloors();
      collect();
    }
    return { rebuild: false, structure, focus: focusChanged, floors: floorsChanged };
  };

  /** The part of the world the camera frames: the floor the person is on, else the open building, else the whole City. */
  content.subject = () => {
    const tower = focus ? towers.get(focus) : null;
    if (!tower) {
      const box = new THREE.Box3().setFromObject(ground.group);
      lots.forEach((lot, i) => {
        const { x, z } = lotAt(i, lots.length);
        box.union(towerBox(THREE, x, z, lot.floors.length, 0));
      });
      return box;
    }
    const i = lots.findIndex((lot) => lot.id === focus);
    const { x, z } = lotAt(i, lots.length);
    const k = floorIndex(tower);
    if (k >= 0) return floorBox(THREE, x, z, k);
    return towerBox(THREE, x, z, lots[i].floors.length, 1);
  };

  /**
   * On the Floor and in the Lobby the city furniture (the streets, the trees, the other buildings) is hidden once everything has settled, never
   * before (the prototype showed it throughout the motion); any motion draws it again at once.
   */
  content.hideSurroundings = (on) => {
    ground.group.visible = !on;
    for (const tower of towers.values()) if (tower.id !== focus) tower.group.visible = !on;
  };

  content.bounds = new THREE.Box3().setFromObject(group);
  content.focusId = () => focus;
  collect();
  content.labels = content.text(model).labels;
  return content;
}

/** What the world is made of, for a model: the lots in order (a tower's own structure is compared tower by tower). */
buildWorld.structure = (model) => ({ ready: model.ready, lots: model.lots.map((lot) => lot.id) });
