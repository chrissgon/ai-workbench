"""Tests of the scene's third round (WP-9.11): one world (the clicked building opens where it stands while the camera flies, Back closes it, no
mesh is replaced and none jumps), the in-between layout (the scene is fitted in what the KPI cards, the header, the panel and the plates leave) and the
bounded request list.

No browser and no model: the pure modules run under Node when it is installed (the world with the real three.js, no WebGL); what only a browser can show
was looked at in the browser pane by the package's report.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_interface_scene_round3.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import standin_tree as st
from test_interface_floor import FAKE_DOM

INTERFACE = st.REPO / "interface"
JS = INTERFACE / "js"
SCENE = JS / "scene"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed: the pure modules are tested only by their text")


def run_node(tmp_path: Path, body: str) -> dict:
    """Run `body` (an ES module that prints one JSON line) with Node and return what it printed."""
    script = tmp_path / "check.mjs"
    script.write_text(body.replace("@JS@", JS.as_uri()).replace("@FAKE@", (tmp_path / "fake-dom.mjs").as_uri()), encoding="utf-8")
    (tmp_path / "fake-dom.mjs").write_text(FAKE_DOM, encoding="utf-8")
    done = subprocess.run([NODE, str(script)], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


# What the tests of the world share: a palette, the models of a City of three lots and the world built from them.
WORLD_JS = r"""
import * as THREE from "@JS@/three.js";
import { createKit } from "@JS@/scene/kit.js";
import { buildWorld } from "@JS@/scene/world.js";

const c = (hex) => new THREE.Color(hex);
const T = { border: c(0x101010), theme: c(0x2020f0), success: c(0x10f010), error: c(0xf01010), emphasis: c(0x303030), text: c(0x404040), warn: c(0xf0a010), textMuted: c(0x505050), mutedRole: c(0x707070) };
export const palette = { dark: false, T, mix: (a, b, t) => a.clone().lerp(b, t), bg: c(0xfafafa), shell: c(0xf8f8f8), ink: c(0x202020), metal: c(0x606060), deskTop: c(0xd0d0d0), screenOff: c(0x181818), leafA: c(0x80c080), leafB: c(0x70b070), trunk: c(0x806040),
  lot: c(0xffffff), warm: c(0xf0c040), pale: c(0xd0d8f0), glass: c(0xd0e0f0), wood: c(0xc0a080), drawer: c(0x9090d0), skin: c(0xe0c0b0), windows: { lit: c(0xf0c040), grey: T.border } };
export { THREE, createKit, buildWorld };

const floor = (name, extra = {}) => ({ name, label: name, state: "idle", window: "grey", decisions: 0, lobby: name === "planning", sheets: [{ path: "docs/a.md", tip: "docs/a.md" }, { path: "docs/b.md", tip: "docs/b.md" }], drawers: 1, tip: `tip ${name}`, interactive: true,
  plate: { name, label: name, dot: "muted", decisions: 0, word: "resting", done: 0, left: 0, queued: 0, runsText: "0 / 4", runsShare: 0, usdText: "$0 / $1", usdShare: 0, unknown: 0, mode: "supervised", pips: 2, acting: null, actingPips: 0, selected: false, off: false }, ...extra });
export const lot = (id, extra = {}) => ({ id, name: id, accepted: true, decisions: 1, runningTask: id === "a" ? 5 : null, tip: `tip ${id}`, sub: "sub", selected: null, tag: null,
  floors: [floor("planning"), floor("business", { state: "working", window: "lit" }), floor("design", { decisions: 2, state: "waiting" }), floor("engineering")], ...extra });
export const model = (extra = {}) => ({ ready: true, selectedId: null, marked: null, outlined: null, focus: null, floor: null, frame: null, room: null, lots: [lot("a"), lot("b"), lot("c")], ...extra });
export function make(extra = {}) {
  const kit = createKit(palette);
  const scene = new THREE.Scene();
  const world = buildWorld(kit, model(extra));
  scene.add(world.group);
  return { kit, scene, world };
}
// every visible mesh of the world (a hidden group hides its subtree), with the world position of its centre
export function visibleMeshes(world) {
  const out = [];
  const walk = (n) => { if (!n.visible) return; if (n.isMesh) out.push(n); n.children.forEach(walk); };
  walk(world.group);
  return out;
}
"""


@needs_node
def test_the_building_opens_in_place_while_the_route_changes_no_mesh_is_replaced_and_none_jumps(tmp_path):
    got = run_node(tmp_path, WORLD_JS + r"""
import { approach, EXPLODE_RATE, smooth } from "@JS@/scene/prototype-motion.js";
import { floorY, P, GAP } from "@JS@/scene/building.js";

const { world } = make();
const a = world.towers.get("a");
const before = new Set(visibleMeshes(world));
const groupBefore = a.group;
const floorsBefore = [...a.floorGroups];
// the click: the building is asked to open; its rooms are built, hidden behind its opaque walls
world.setFocus("a");
const afterSwap = new Set(visibleMeshes(world));
const sameSet = (x, y) => x.size === y.size && [...x].every((m) => y.has(m));
const out = { swapInvisible: sameSet(before, afterSwap), interior: a.interior };
// the frames: 30 a second; the route changes on frame 15 (the model gets its focus), the building goes on opening
let open = 0;
const ys = [];
const opacity = [];
const expectedYs = [];
const top = a.floorGroups.length - 1;
const others = [];
for (let frame = 1; frame <= 70; frame++) {
  const moving = world.step(1 / 30);
  open = approach(open, 1, 1 / 30, EXPLODE_RATE);
  if (Math.abs(open - 1) <= 0.005) open = 1;
  if (frame === 15) {
    const visibleNow = new Set(visibleMeshes(world));
    const result = world.update(model({ focus: "a" }));
    out.update = result;
    out.sameAfterRoute = sameSet(visibleNow, new Set(visibleMeshes(world)));
    out.sameGroup = world.towers.get("a").group === groupBefore && world.towers.get("a").floorGroups.every((g, i) => g === floorsBefore[i]);
    out.hitsAfterRoute = world.hits.map((h) => h.id);
  }
  ys.push(a.floorGroups[top].position.y);
  expectedYs.push(floorY(top, P + GAP * smooth(open)));
  opacity.push(a.group.children[0].children[0].children[1].material.opacity);   // a wall of the first floor's shell
  others.push(["b", "c"].map((id) => { const t = world.towers.get(id); return [t.group.visible, t.floorGroups.every((g) => g.visible), t.group.children[0].children[0].children[1].material.opacity]; }));
  if (!moving) { out.settledAt = frame; break; }
}
out.ys = { monotone: ys.every((y, i) => i === 0 || y >= ys[i - 1] - 1e-12), equalToTheCurve: ys.every((y, i) => Math.abs(y - expectedYs[i]) < 1e-9), maxStep: Math.max(...ys.map((y, i) => (i ? y - ys[i - 1] : y - floorY(top, P)))), total: ys[ys.length - 1] - floorY(top, P) };
out.opacity = { monotone: opacity.every((o, i) => i === 0 || o <= opacity[i - 1] + 1e-12), last: opacity[opacity.length - 1] };
out.othersAlways = others.every((frame) => frame.every(([g, f, o]) => g === true && f === true && o === 1));
out.groundVisible = world.group.children[0].visible;
out.hitsOpen = world.hits.map((h) => h.id);
console.log(JSON.stringify(out));
""")
    assert got["swapInvisible"] is True and got["interior"] is True, "the rooms are put in behind the opaque walls: not one visible mesh changes at that moment"
    assert got["update"] == {"rebuild": False, "structure": False, "focus": False, "floors": False}, "the route changes in the middle of the motion: the world is updated in place, nothing is built again"
    assert got["sameAfterRoute"] is True and got["sameGroup"] is True, "the building the person clicked is the same group of the same floors before and after the route changed"
    assert got["hitsAfterRoute"][:2] == ["floor:planning", "door"], "and from then on its floors are what the pointer meets (the building as one hit before)"
    ys = got["ys"]
    assert ys["monotone"] is True and ys["equalToTheCurve"] is True, "the top floor rises along the prototype's curve frame by frame: never down, never off it, on every frame of the route change"
    assert ys["maxStep"] < 0.5 and abs(ys["total"] - 3.0) < 1e-6, "no frame moves more than a fraction of the whole way (3 floors apart by 1 unit each): no jump"
    assert got["opacity"]["monotone"] is True and got["opacity"]["last"] == 0, "the front walls fade out, never back in"
    assert got["othersAlways"] is True and got["groundVisible"] is True, "the other buildings and the city furniture are drawn, whole, in every frame of the opening"
    assert got["settledAt"] < 60, "the motion ends: the loop stops, nothing draws while still"


@needs_node
def test_a_click_on_a_floor_shrinks_the_other_floors_to_nothing_and_keeps_the_chosen_one_where_it_is(tmp_path):
    got = run_node(tmp_path, WORLD_JS + r"""
const { world } = make();
world.setFocus("a", true);
const a = world.towers.get("a");
const chosen = a.floorGroups[1];
const snap = (g) => [g.position.x, g.position.y, g.position.z, g.scale.x, g.scale.y, g.scale.z, g.rotation.x, g.rotation.y, g.rotation.z];
const chosenBefore = snap(chosen);
const meshes = new Set();
a.group.traverse((n) => { if (n.isMesh) meshes.add(n); });
world.setFloors("business", null);          // the click on the floor
const scales = [[], [], []];
let frame = 0;
const sameChosen = [];
let routed = false;
while (world.moving() && frame < 80) {
  world.step(1 / 30);
  frame += 1;
  if (frame === 10) { world.update(model({ focus: "a", floor: "business", room: { tips: { agent: "a", desk: "d", tray: "t" }, board: null, door: false } })); routed = true; }
  [0, 2, 3].forEach((i, k) => scales[k].push(a.floorGroups[i].scale.x));
  sameChosen.push(snap(chosen).every((v, i) => v === chosenBefore[i]));
}
const after = new Set();
a.group.traverse((n) => { if (n.isMesh) after.add(n); });
const meshesKept = [...meshes].every((m) => after.has(m));
const entered = { routed, frames: frame, scales: scales.map((s) => ({ monotone: s.every((v, i) => i === 0 || v <= s[i - 1] + 1e-12), last: s[s.length - 1], first: s[0] })), sameChosen: sameChosen.every(Boolean), meshesKept,
  visible: [0, 1, 2, 3].map((i) => a.floorGroups[i].visible), hits: world.hits.map((h) => h.id), others: ["b", "c"].map((id) => world.towers.get(id).group.visible) };
// Back from the floor: the floors grow back by the same approach
world.setFloors(null, null);
const back = [];
while (world.moving()) { world.step(1 / 30); back.push(a.floorGroups[0].scale.x); }
console.log(JSON.stringify({ ...entered, back: { monotone: back.every((v, i) => i === 0 || v >= back[i - 1] - 1e-12), last: back[back.length - 1], steps: back.length } }));
""")
    assert got["routed"] is True and got["frames"] < 40, "the route changes during the motion and the motion ends within a second"
    assert all(s["monotone"] and s["last"] <= 0.001 for s in got["scales"]), "every other floor shrinks, never grows, to nothing"
    assert got["sameChosen"] is True, "the chosen floor's transform is not touched in any frame"
    assert got["meshesKept"] is True, "no mesh is replaced: the floor the person is on is the one they clicked"
    assert got["visible"] == [False, True, False, False], "the others are out of the scene when they have reached nothing"
    assert got["hits"] == ["agent", "desk", "tray", "sheet:docs/a.md", "sheet:docs/b.md"], "the objects of the room are what the pointer meets"
    assert got["others"] == [True, True] or got["others"] == [False, False], "the city furniture goes only when the engine hides it after everything settled (not by the world's own motion)"
    assert got["back"]["monotone"] is True and got["back"]["last"] == 1, "Back: the floors grow back by the same approach"


@needs_node
def test_back_closes_the_building_by_the_same_curve_from_wherever_it_is_and_the_other_buildings_stay(tmp_path):
    got = run_node(tmp_path, WORLD_JS + r"""
const { world } = make();
const a = world.towers.get("a");
const tops = () => a.floorGroups.map((g) => g.position.y);
const closedYs = tops();
const closedOpacity = a.group.children[0].children[0].children[1].material.opacity;
world.setFocus("a", true);
const frames = [];
world.setFocus(null);
for (let f = 0; f < 80 && world.moving(); f++) { world.step(1 / 30); frames.push({ open: a.open, y: tops()[3], others: ["b", "c"].every((id) => world.towers.get(id).group.visible) }); }
const out = {
  monotoneDown: frames.every((fr, i) => i === 0 || fr.open <= frames[i - 1].open + 1e-12),
  yMonotone: frames.every((fr, i) => i === 0 || fr.y <= frames[i - 1].y + 1e-12),
  othersAlways: frames.every((fr) => fr.others),
  endsClosed: tops().every((y, i) => Math.abs(y - closedYs[i]) < 1e-9),
  opacityBack: a.group.children[0].children[0].children[1].material.opacity === closedOpacity,
  hitsCity: world.hits.map((h) => h.id),
  firstStep: frames[0].open,
};
// reverse in the middle of the opening: the progress is continuous, it turns round where it was
world.setFocus("a");
for (let f = 0; f < 8; f++) world.step(1 / 30);
const mid = a.open;
world.setFocus(null);
world.step(1 / 30);
out.turn = [mid, a.open];
console.log(JSON.stringify(out));
""")
    assert got["monotoneDown"] and got["yMonotone"], "Back runs the opening backwards: the floors come down, nothing the other way"
    assert got["othersAlways"] is True, "the other buildings never leave"
    assert got["endsClosed"] is True and got["opacityBack"] is True, "and the building ends exactly as it was: the same floors at the same heights, the walls opaque"
    assert got["hitsCity"] == ["a", "b", "c"], "the City is whole again: every building a hit"
    assert got["firstStep"] < 1, "Back starts from where the building is"
    mid, after = got["turn"]
    assert 0 < mid < 1 and after < mid and mid - after < 0.35, "a Back in the middle of the opening turns the motion round where it was, with no jump"


@needs_node
def test_a_poll_changes_the_world_in_place_only_the_tower_whose_floors_changed_is_made_again(tmp_path):
    got = run_node(tmp_path, WORLD_JS + r"""
const { world } = make({ focus: "a" });
world.setFocus("a", true);
const groups = () => ["a", "b", "c"].map((id) => world.towers.get(id).group);
const g0 = groups();
const out = {};
const same = (x, y) => x.every((g, i) => g === y[i]);
// the same model: nothing
out.same = world.update(model({ focus: "a" }));
// other words: a tooltip, a name, a plate, the sub line: nothing is built again
const words = model({ focus: "a" });
words.lots[0].tip = "other"; words.lots[1].name = "renamed"; words.lots[0].floors[1].plate.runsText = "9 / 9"; words.lots[2].sub = "x";
out.words = world.update(words);
out.wordsKept = same(g0, groups());
// a floor of b changes state: b alone is made again, a (open) and c keep their groups
const changed = model({ focus: "a" });
changed.lots[1].floors[0].state = "working"; changed.lots[1].floors[0].window = "lit";
out.state = world.update(changed);
const g1 = groups();
out.stateKept = [g1[0] === g0[0], g1[1] === g0[1], g1[2] === g0[2]];
// the open building's own floor changes: it is made again, still open, with its rooms
const open = model({ focus: "a" });
open.lots[0].floors[2].state = "working"; open.lots[0].floors[2].window = "lit";
out.openState = world.update(open);
const a = world.towers.get("a");
out.stillOpen = [a.open, a.interior, a.group !== g0[0]];
// another set of lots builds the world again
out.lots = world.update(model({ lots: [lot("a"), lot("b")] }));
console.log(JSON.stringify(out));
""")
    assert got["same"] == {"rebuild": False, "structure": False, "focus": False, "floors": False}
    assert got["words"]["structure"] is False and got["wordsKept"] is True, "other words never build anything"
    assert got["state"]["structure"] is True and got["stateKept"] == [True, False, True], "a floor that changed state makes its own building again and no other"
    assert got["stillOpen"] == [1, True, True], "the open building made again stays open, with its rooms, at once"
    assert got["lots"]["rebuild"] is True, "only another set of lots builds the world again"


def test_the_engine_hands_the_scene_over_between_the_screens_and_the_views_never_take_it_down():
    engine = (SCENE / "engine.js").read_text(encoding="utf-8")
    assert "updateWorld(nextModel)" in engine and "content.update(next)" in engine and "setOptions(next)" in engine, "the world is updated in place; the next screen takes over its handlers"
    assert "else content.setFocus(id, reducedQuery.matches);" in engine and "refocus(true, FLY_SETTLE_AT)" in engine, "a click opens the building (or goes into the floor) and flies the camera together"
    assert "tween.retarget(goal)" in engine, "the camera goes on from where it is when the page's panels appear"
    assert "loop.start(\"world\", { ambient: false })" in engine and "if (!moving) {" in engine, "the opening runs every frame and stops when it is done: nothing draws while still"
    assert "content.finish()" in engine and "reducedQuery.matches" in engine, "reduced motion skips to the end state"
    frame = (JS / "frame" / "frame.js").read_text(encoding="utf-8")
    assert "acquireWorld(options)" in frame and "releaseWorld()" in frame and '["city", "building", "floor", "lobby"].includes(route.screen)' in frame
    for name in ("city.js", "building.js"):
        view = (JS / "views" / name).read_text(encoding="utf-8")
        assert "frame.acquireWorld(" in view and "engine.dispose()" not in view, f"{name}: the screen takes the scene over and leaves it to the frame"
        assert 'engine.show("world"' in view
    assert "snapshot, now" in (JS / "main.js").read_text(encoding="utf-8")


@needs_node
def test_the_camera_goes_on_from_where_it_is_when_its_goal_changes(tmp_path):
    got = run_node(tmp_path, r"""
import { createTween } from "@JS@/scene/tween.js";
const a = { left: -20, right: 20, top: 11.25, bottom: -11.25 };
const b = { left: 3, right: 9, top: 4, bottom: -1 };
const b2 = { left: 6, right: 14, top: 5, bottom: -3 };
const t = createTween();
const settled = [];
t.start(a, b, 0, 0.9).then((v) => settled.push(v));
let f = null;
let now = 0;
for (let i = 0; i < 12; i++) { now += 1000 / 60; f = t.step(now); }
const before = f;
t.retarget(b2);
now += 1000 / 60;
const after = t.step(now);
const jump = Math.max(...["left", "right", "top", "bottom"].map((k) => Math.abs(after[k] - before[k])));
const lastStep = Math.max(...["left", "right", "top", "bottom"].map((k) => Math.abs(before[k] - 0)));
let end = after;
for (let i = 0; i < 200 && t.active(); i++) { now += 1000 / 60; end = t.step(now); }
await new Promise((r) => setTimeout(r, 5));
console.log(JSON.stringify({ jump, end: [end.left, end.right, end.top, end.bottom].map((x) => Math.round(x * 1e6) / 1e6), settled, active: t.active(), retargetIdle: createTween().retarget(b) }));
""")
    assert got["jump"] < 3.0, "a goal that changes in flight bends the move: no frame jumps to the new place"
    assert got["end"] == [6, 14, 5, -3], "and the camera lands exactly on the new goal"
    assert got["settled"] == [True] and got["active"] is False and got["retargetIdle"] is False


@needs_node
def test_the_scene_is_fitted_in_what_the_parts_over_it_leave(tmp_path):
    got = run_node(tmp_path, r"""
import { obstacleInset } from "@JS@/frame/frame.js";
const r = (left, top, w, h) => ({ left, top, width: w, height: h, right: left + w, bottom: top + h });
const wide = r(0, 0, 1280, 720);
const out = {};
out.kpiColumn = obstacleInset(r(16, 62, 188, 190), wide);
out.kpiRow = obstacleInset(r(16, 62, 480, 62), r(0, 0, 900, 700));
out.panel = obstacleInset(r(1280 - 16 - 400, 62, 400, 508), wide);
out.waiting = obstacleInset(r(1280 - 16 - 380, 300, 380, 270), wide);
out.header = obstacleInset(r(16, 16, 440, 36), wide);
out.track = obstacleInset(r(16, 570, 1248, 134), wide);
out.dockedPanel = obstacleInset(r(16, 380, 668, 300), r(0, 0, 680, 380));   // below the scene: it does not touch it
out.nothing = obstacleInset(r(0, 0, 0, 0), wide);
console.log(JSON.stringify(out));
""")
    assert got["kpiColumn"] == {"side": "left", "amount": 220}, "a column of cards at the left takes the left"
    assert got["kpiRow"] == {"side": "top", "amount": 136}, "a row of cards takes the top (the tablet layout), below its bottom edge"
    assert got["panel"] == {"side": "right", "amount": 432} and got["waiting"] == {"side": "right", "amount": 412}
    assert got["header"] == {"side": "top", "amount": 64} and got["track"] == {"side": "bottom", "amount": 166}
    assert got["dockedPanel"] is None and got["nothing"] is None, "a part that does not touch the scene (the panel docked below it) takes nothing"
    frame = (JS / "frame" / "frame.js").read_text(encoding="utf-8")
    assert "obstacleInset(part.getBoundingClientRect(), scene)" in frame and "kpis.el, header, actions" in frame, "every part over the scene is measured, none is assumed"


def test_the_in_between_layout_has_the_tablet_rules_of_the_handoff_and_the_panel_docks_below_900_px():
    css = (INTERFACE / "style.css").read_text(encoding="utf-8")
    block = css[css.index("the in-between layout (WP-9.11"):]
    assert "@media (min-width: 640px) and (max-width: 1099px)" in block and "@media (min-width: 640px) and (max-width: 899px)" in block
    mid = block[:block.index("@media (min-width: 640px) and (max-width: 899px)")]
    for rule in (".wb-kpis { display: flex;", ".wb-kpi-long { display: none; }", ".wb-kpi-short { display: inline; }", ".wb-door-label, .wb-wait-btn-label { display: none; }",
                 "--wb-panel-narrow: 340px", "--wb-plate-w: 230px", ".wb-track-left .wb-steps { overflow-x: auto; }", ".wb-plate:not(.is-row) .wb-plate-chips > .pui-badge { display: none; }"):
        assert rule in mid, f"the tablet rule: {rule}"
    docked = block[block.index("@media (min-width: 640px) and (max-width: 899px)"):]
    for rule in ("grid-template-areas: \"scene\" \"content\" \"track\"", ".wb-main { position: static;", ".wb-track { position: static;", ".wb-panel-floor, .wb-panel-building { height: auto; }"):
        assert rule in docked, f"the docked panel: {rule}"
    assert ".wb-plate.is-tiny" in css and "is-tiny" in (SCENE / "labels.js").read_text(encoding="utf-8"), "a plate shortens to its name row when the stack still would not fit"
    kpis = (JS / "frame" / "kpis.js").read_text(encoding="utf-8")
    assert all(word in kpis for word in ('"Decisions"', '"Runs"', '"Spend"', "wb-kpi-short", "wb-kpi-long")), "the cards carry their short labels"
    assert "plateWidth()" in (JS / "views" / "building.js").read_text(encoding="utf-8"), "the fit leaves the width of the plates as the stylesheet has them now"


@needs_node
def test_the_request_list_has_a_height_of_about_six_rows_a_width_and_ellipsised_titles_with_the_whole_title_as_the_tooltip(tmp_path):
    got = run_node(tmp_path, r"""
import { FakeNode, find, all } from "@FAKE@";
import { createTrack } from "@JS@/frame/track.js";
const task = (id) => ({ id, key: `k${id}`, title: `Task ${id}`, state: "ready", agent: "engineering" });
const long = "A very long title that goes on and on and would stretch the list as wide as the page if nothing held it in";
const requests = Array.from({ length: 9 }, (_, i) => ({ id: i + 1, title: i === 3 ? long : `Request ${i + 1}`, state: "ready", running: false, selected: i === 8 }));
const model = { request: { id: 9, title: "Request 9", state: "ready", project: "shop", projectId: "p" }, requests, steps: [], doneCount: 0, total: 0, now: null };
document.activeElement = null;
FakeNode.prototype.getBoundingClientRect = () => ({ left: 10, top: 500 });
const scrolled = [];
FakeNode.prototype.scrollIntoView = function (o) { scrolled.push([this.attrs["data-request"], o && o.block]); };
const track = createTrack({ onOpenSteps() {}, onSelectRequest() {} });
track.set(model, "ready");
const options = all(track.el, ".wb-track-desktop .wb-req-option");
const longOption = options[3];
const list = find(track.el, ".wb-track-desktop .wb-req-menu");
const chip = find(track.el, ".wb-track-desktop .wb-req-chip");
chip.click();
const press = (key) => { for (const fn of list.listeners.keydown || []) fn({ key, preventDefault() {}, stopPropagation() {} }); };
press("ArrowUp"); press("ArrowUp");
console.log(JSON.stringify({ rows: options.length, longTitle: longOption.attrs.title === long, spanTitle: find(longOption, ".wb-req-option-title").attrs.title === long, shortTitle: options[0].attrs.title, scrolled }));
""")
    assert got["rows"] == 9 and got["longTitle"] is True and got["spanTitle"] is True and got["shortTitle"] == "Request 1", "each row carries its whole title as the tooltip"
    assert got["scrolled"] == [["8", "nearest"], ["7", "nearest"]], "the arrows keep the row they reach in view of the bounded list"
    css = (INTERFACE / "style.css").read_text(encoding="utf-8")
    menu = css[css.index(".wb-req-menu {"):css.index(".wb-req-menu[hidden]")]
    assert "max-width: min(28rem, 90vw)" in menu and "max-height: min(calc(6 * var(--wb-req-row) + 5 * 2px + 8px), 60vh)" in menu and "overflow-y: auto" in menu, "about six rows, then it scrolls; 28 rem wide at most"
    assert "grid-template-columns: minmax(0, 1fr)" in menu, "the single column is limited by the box: a long title is cut, it never widens the rows (seen in the pane)"
    assert "--wb-req-row: 2.25rem" in css and "min-height: var(--wb-req-row)" in css
    assert re.search(r"\.wb-req-option-title \{[^}]*text-overflow: ellipsis", css), "a long title is cut with an ellipsis"


# --- the six corrections of the maintainer's last test (2026-10-09) ---------------------------------------------------------------------------------

@needs_node
def test_the_outline_is_the_outer_parts_only_a_few_edges_per_object_and_never_an_inner_part(tmp_path):
    got = run_node(tmp_path, WORLD_JS + r"""
import { outlineGeometry, outlineMeshes } from "@JS@/scene/outline.js";
const { world } = make();
world.update(model({ focus: "a", floor: "business", room: { tips: { agent: "a", desk: "d", tray: "t" }, board: null, door: false } }));
world.setFocus("a", true);
world.setFloors("business", null, true);
const out = { objects: {} };
for (const hit of world.hits) {
  const meshes = outlineMeshes(hit.object);
  const geometry = outlineGeometry(THREE, hit.object, 0.04);
  out.objects[hit.id] = { parts: meshes.length, allShell: meshes.every((m) => m.userData.shell === true), segments: geometry.getAttribute("position").count / 2 };
}
// the City: a building is its bodies and roof
world.setFocus(null, true);
world.setFloors(null, null, true);
const tower = world.hits.find((h) => h.id === "a");
const city = outlineMeshes(tower.object);
out.city = { parts: city.length, allShell: city.every((m) => m.userData.shell === true), segments: outlineGeometry(THREE, tower.object, 0.06).getAttribute("position").count / 2 };
// an object with no part marked has no outline at all (no fall back to every mesh)
const bare = new THREE.Group(); bare.add(new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshBasicMaterial()));
out.bare = outlineMeshes(bare).length;
console.log(JSON.stringify(out));
""")
    assert got["bare"] == 0, "no shell part, no outline: never every mesh"
    for hit, o in got["objects"].items():
        assert o["allShell"] is True and o["parts"] >= 1, f"{hit}: only parts marked as the outer shell"
        assert 0 < o["segments"] <= 160, f"{hit}: a handful of edges ({o['segments']}), not every edge of every part"
    assert got["objects"]["tray"]["parts"] == 1 and got["objects"]["desk"]["parts"] == 1, "the tray is its box, the desk its top"
    assert got["city"]["allShell"] is True and got["city"]["segments"] <= 400


@needs_node
def test_the_tray_is_on_every_floor_with_one_sheet_for_each_decision_and_the_top_floor_has_no_roof_when_open(tmp_path):
    got = run_node(tmp_path, WORLD_JS + r"""
const states = (n) => lot("a", { floors: lot("a").floors.map((f, i) => ({ ...f, decisions: [0, 1, 2, 7][i] })) });
const { world } = make({ lots: [states(), lot("b"), lot("c")] });
world.setFocus("a", true);
const a = world.towers.get("a");
// the tray's sheets: the boxes standing on its base (a base, four rims, then one sheet per decision up to five, then one thicker block)
const traySheets = (i) => a.parts[i].tray.children.filter((c) => c.isMesh).length - 5;
const out = { sheets: [0, 1, 2, 3].map(traySheets), hit: [0, 1, 2, 3].map((i) => !!a.parts[i].tray) };
// the roof: gone when the building is open, and the top floor has no ceiling slab
out.roof = a.group.children.filter((c) => c.position.y > a.floorGroups[3].position.y + 2).map((c) => c.visible);
out.shells = a.floorGroups.map((g) => g.children[0].visible);
console.log(JSON.stringify(out));
""")
    assert got["hit"] == [True, True, True, True], "the tray stands on the desk of every floor, with or without a decision"
    assert got["sheets"] == [0, 1, 2, 6], "one sheet per decision up to five, then a thicker block: nothing for none"
    assert got["roof"] == [False] and got["shells"] == [False] * 4, "no roof slab over the top floor and no front wall: the room is open like the others"
    floor_model = (JS / "floor-model.js").read_text(encoding="utf-8")
    assert "Inbox · ${row.decisions} waiting" in floor_model, "the tooltip says how many wait"


def test_escape_has_one_handler_in_the_frame_and_none_in_the_screens():
    frame = (JS / "frame" / "frame.js").read_text(encoding="utf-8")
    assert "escapeStep({" in frame and frame.count('addEventListener("keydown", onKey)') == 1
    for name in ("floor.js", "building.js", "control.js", "lobby.js"):
        assert 'event.key !== "Escape"' not in (JS / "views" / name).read_text(encoding="utf-8"), f"{name} has no Escape handler of its own"


@needs_node
def test_escape_goes_through_its_steps_in_order_and_goes_up_from_every_screen(tmp_path):
    got = run_node(tmp_path, r"""
import { escapeStep } from "@JS@/frame/escape.js";
import * as router from "@JS@/router.js";
const P = "0123456789ab";
const r = (h) => router.parse(`#/p/${P}${h}`);
const out = {};
const step = (route, extra = {}) => escapeStep({ route, ...extra });
out.field = step(r("/floor/marketing"), { field: true, dialog: true, menu: true });
out.dialog = step(r("/floor/marketing/desk/docs%2Fa.md"), { dialog: true, menu: true, selection: true });
out.floorDocument = step(r("/floor/marketing/desk/docs%2Fa.md"), { menu: true, selection: true });
out.floorPending = step(r("/floor/marketing/inbox/4"), {});
out.lobbyDocument = step(r("/lobby/desk/docs%2Fa.md"), {});
out.lobbyPending = step(r("/lobby/inbox/4"), {});
out.menu = step(r("/floor/marketing"), { menu: true, selection: true });
out.selection = step(r("/lobby"), { selection: true });
out.floorUp = step(r("/floor/marketing"));
out.lobbyUp = step(r("/lobby"));
out.lobbyUpWithTab = step(r("/lobby/inbox"));
out.buildingUp = step(r(""));
out.controlUp = step(r("/control"));
out.controlFrom = step(r("/control/costs"), { from: `#/p/${P}/floor/marketing` });
out.controlSelected = step(r("/control"), { selection: true });
out.cityNothing = step(router.parse("#/"));
console.log(JSON.stringify(out));
""")
    p = "0123456789ab"
    assert got["field"] == {"step": "none"}, "a field has the focus: nothing"
    assert got["dialog"] == {"step": "dialog"}, "a dialog closes before anything else"
    assert got["floorDocument"] == {"step": "document", "hash": f"#/p/{p}/floor/marketing/desk"}, "a document closes back to the Desk"
    assert got["floorPending"] == {"step": "document", "hash": f"#/p/{p}/floor/marketing/inbox"}
    assert got["lobbyDocument"] == {"step": "document", "hash": f"#/p/{p}/lobby/desk"} and got["lobbyPending"] == {"step": "document", "hash": f"#/p/{p}/lobby/inbox"}, "the Lobby too (it did nothing)"
    assert got["menu"] == {"step": "menu"} and got["selection"] == {"step": "selection"}, "a menu closes, then a selection is cleared"
    assert got["floorUp"] == {"step": "up", "hash": f"#/p/{p}"} and got["lobbyUp"] == {"step": "up", "hash": f"#/p/{p}"} and got["lobbyUpWithTab"] == {"step": "up", "hash": f"#/p/{p}"}, "the Floor and the Lobby go up to the Building"
    assert got["buildingUp"] == {"step": "up", "hash": "#/"}, "the Building goes up to the City"
    assert got["controlUp"] == {"step": "up", "hash": f"#/p/{p}"} and got["controlFrom"] == {"step": "up", "hash": f"#/p/{p}/floor/marketing"}, "the Control room goes back to where it was opened from, else the Building"
    assert got["controlSelected"] == {"step": "selection"}, "after an object was used in the Control room the first Escape clears it, the next goes up"
    assert got["cityNothing"] == {"step": "none"}


@needs_node
def test_the_list_rows_are_the_plate_beside_the_floor_and_the_compact_card_is_the_phones(tmp_path):
    got = run_node(tmp_path, r"""
import { FakeNode, find } from "@FAKE@";
import { plateNode } from "@JS@/scene/plates.js";
const p = { name: "engineering", label: "Engineering", dot: "theme", decisions: 2, word: "working", done: 1, left: 2, queued: 0, runsText: "3 / 14", runsShare: 0.2, usdText: "$0 / $5", usdShare: 0, unknown: 0, mode: "autonomous", pips: 3, acting: null, actingPips: 0, selected: false, off: false };
const plate = plateNode(p);
const row = plateNode(p, { class: "wb-floor-row is-row", href: "#/p/x/floor/engineering", "aria-label": "Engineering, working" }, "a");
const shape = (n) => ({ tag: n.tagName, parts: n.children.map((c) => c.cls().join(" ")), text: n.textContent });
console.log(JSON.stringify({ plate: shape(plate), row: shape(row), href: row.attrs.href, classes: row.cls() }));
""")
    assert got["plate"]["tag"] == "DIV" and got["row"]["tag"] == "A" and got["href"] == "#/p/x/floor/engineering"
    assert got["plate"]["parts"] == got["row"]["parts"] == ["wb-plate-row", "wb-plate-chips", "wb-plate-meters"], "name row, the done, left and queued chips with the mode plate, the two meters: the plate's design in both places"
    assert got["plate"]["text"] == got["row"]["text"], "the same words"
    assert "wb-plate" in got["classes"] and "is-row" in got["classes"] and "wb-floor-row" in got["classes"]


def test_the_chosen_building_keeps_a_thin_outline_in_the_city_besides_the_hover():
    engine = (SCENE / "engine.js").read_text(encoding="utf-8")
    assert "function drawMarked()" in engine and "content.marked" in engine and "markedOutline" in engine
    world = (SCENE / "world.js").read_text(encoding="utf-8")
    assert "marked: model.marked || null" in world and "content.marked = m.marked || null" in world
    city = (JS / "views" / "city.js").read_text(encoding="utf-8")
    assert "marked: selectedId" in city, "the project the switcher has chosen (the City's selectedId)"
    wm = (JS / "world-model.js").read_text(encoding="utf-8")
    assert "marked && lots.some((l) => l.id === marked) && !there ? marked : null" in wm, "only in the City, only for a project that is drawn"


def test_the_route_changes_at_the_click_and_never_waits_for_the_scene():
    for name in ("city.js", "building.js"):
        source = (JS / "views" / name).read_text(encoding="utf-8")
        assert "engine.flyTo(id);" in source and ".then(go)" not in source and "flying" not in source, f"{name}: the scene starts and the route changes in the same moment"
    city = (JS / "views" / "city.js").read_text(encoding="utf-8")
    assert city.index("engine.flyTo(id);") < city.index("window.location.hash = router.buildingHash(id);")
