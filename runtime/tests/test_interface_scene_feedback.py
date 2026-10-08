"""Tests of the scene after the maintainer's review (WP-9.8): the prototype's motion, outlines only on hover or selection, grey windows
lit when the agent works, the person's zoom and pan with limits, the pointer's hit-test, one object per destination in a room, no
rebuild on a poll that changed only words, the request selector of the tracking bar and the compact floor card.

No browser and no model: the pure modules run under Node when it is installed (the builders with the real three.js, no WebGL), and
what only a browser can show was looked at in the browser pane by the package's report.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_interface_scene_feedback.py
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
    done = subprocess.run([NODE, str(script)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


# --- the person's camera: zoom and pan with limits ------------------------------------------------------------------------------

CAMERA = r"""
import { MIN_ZOOM, MAX_ZOOM, DRAG_PX, IDENTITY, fitView, isDrag, frustumOf, clampView, zoomAt, panBy, panPixels, wheelFactor, keyAction, pointerToNdc } from "@JS@/scene/camera.js";

const fitted = { left: -20, right: 20, top: 11.25, bottom: -11.25 };   // 40 x 22.5
const bounds = { x0: -10, x1: 10, y0: -5, y1: 5 };                      // the diorama: 20 x 10
const out = {};
const size = (f) => [f.right - f.left, f.top - f.bottom];
const inView = (v) => { const f = frustumOf(fitted, v); return { x: Math.min(f.right, bounds.x1) - Math.max(f.left, bounds.x0), y: Math.min(f.top, bounds.y1) - Math.max(f.bottom, bounds.y0) }; };

out.limits = [MIN_ZOOM, MAX_ZOOM];
// the zoom is clamped between the whole diorama fitted and about three times that
let v = fitView();
for (let i = 0; i < 40; i++) v = zoomAt(v, fitted, bounds, 1.3);
out.zoomMax = v.zoom;
for (let i = 0; i < 40; i++) v = zoomAt(v, fitted, bounds, 1 / 1.3);
out.zoomMin = v.zoom;
out.fitSize = size(frustumOf(fitted, IDENTITY));
out.zoomedSize = size(frustumOf(fitted, { zoom: 2, x: 0, y: 0 }));
// zoom around the pointer keeps the point under it where it was
const ndc = { x: 0.5, y: -0.25 };
const before = frustumOf(fitted, IDENTITY);
const pointBefore = [(before.left + before.right) / 2 + ndc.x * (before.right - before.left) / 2, (before.top + before.bottom) / 2 + ndc.y * (before.top - before.bottom) / 2];
const z = zoomAt(IDENTITY, fitted, { x0: -100, x1: 100, y0: -100, y1: 100 }, 2, ndc);
const after = frustumOf(fitted, z);
const pointAfter = [(after.left + after.right) / 2 + ndc.x * (after.right - after.left) / 2, (after.top + after.bottom) / 2 + ndc.y * (after.top - after.bottom) / 2];
out.anchored = [Math.abs(pointBefore[0] - pointAfter[0]) < 1e-9, Math.abs(pointBefore[1] - pointAfter[1]) < 1e-9, z.zoom];
// the pan is clamped: the diorama's box stays at least half visible on each axis, whatever the drag
let p = { zoom: 1.5, x: 0, y: 0 };
for (const [dx, dy] of [[5000, 5000], [-5000, -5000], [5000, -5000], [-5000, 5000]]) {
  const far = panPixels(p, fitted, bounds, dx, dy, { w: 1000, h: 560 });
  const seen = inView(far);
  (out.panClamp ||= []).push([seen.x >= 0.5 * 20 - 1e-9, seen.y >= 0.5 * 10 - 1e-9]);
}
// when the view is narrower than half the box, the whole view stays inside the box
const deep = panPixels({ zoom: 3, x: 0, y: 0 }, fitted, bounds, 9000, 9000, { w: 1000, h: 560 });
const deepFrustum = frustumOf(fitted, deep);
out.deepInside = [deepFrustum.left >= bounds.x0 - 1e-9 || deepFrustum.right <= bounds.x1 + 1e-9, deepFrustum.top <= bounds.y1 + 1e-9 || deepFrustum.bottom >= bounds.y0 - 1e-9];
// a drag moves the scene with the pointer: dragging right moves the view left
const moved = panPixels({ zoom: 2, x: 0, y: 0 }, fitted, bounds, 100, 0, { w: 1000, h: 560 });
out.dragDirection = [moved.x < 0, moved.y === 0];
// keys and the wheel
out.keys = ["+", "=", "-", "_", "0", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "a"].map((k) => keyAction(k));
out.wheel = [wheelFactor(-100) > 1, wheelFactor(100) < 1, wheelFactor(0) === 1, wheelFactor(-100, 1) > wheelFactor(-100), wheelFactor(-1e6) === wheelFactor(-400)];
// drag or click: a press that moves more than a few pixels is a pan
out.drag = [[0, 0], [3, 3], [DRAG_PX, 0], [4, 4], [6, 0], [0, -6]].map(([dx, dy]) => isDrag(dx, dy));
// fit restores the whole diorama
const wandered = panBy(zoomAt(IDENTITY, fitted, bounds, 2.5), fitted, bounds, 0.4, -0.3);
out.wandered = wandered.zoom > 1 && (wandered.x !== 0 || wandered.y !== 0);
out.fit = [fitView(), clampView(fitView(), fitted, bounds)];
// a resize keeps the person's zoom and offset while they are inside the limits, and brings them back when they no longer are
const kept = { zoom: 2, x: 2, y: 1 };
const resized = { left: -24, right: 24, top: 13.5, bottom: -13.5 };
out.keptOnResize = clampView(kept, resized, bounds);
out.pulledBackOnResize = clampView({ zoom: 2, x: 500, y: 0 }, resized, bounds).x < 500;
out.zoomClamped = [clampView({ zoom: 9, x: 0, y: 0 }, fitted, bounds).zoom, clampView({ zoom: 0.1, x: 0, y: 0 }, fitted, bounds).zoom, clampView({ zoom: NaN, x: 0, y: 0 }, fitted, bounds).zoom];
// pointer to normalised device coordinates: the canvas's CSS box, never its buffer, so a scaled canvas and any pixel ratio map the same
const rect = { left: 100, top: 50, width: 640, height: 360 };
out.ndc = [pointerToNdc(100, 50, rect), pointerToNdc(420, 230, rect), pointerToNdc(740, 410, rect), pointerToNdc(260, 140, rect)];
const doubled = { left: 100, top: 50, width: 640, height: 360, bufferWidth: 1280, bufferHeight: 720 };   // the buffer of a 2x display is not part of the mapping
out.ndcBuffer = pointerToNdc(420, 230, doubled);
console.log(JSON.stringify(out));
"""


@needs_node
def test_zoom_is_clamped_between_the_whole_diorama_and_three_times_that_and_zooms_around_the_pointer(tmp_path):
    got = run_node(tmp_path, CAMERA)
    assert got["limits"] == [1, 3]
    assert got["zoomMax"] == 3 and got["zoomMin"] == 1, "the wheel cannot go past the limits"
    assert got["fitSize"] == [40, 22.5] and got["zoomedSize"] == [20, 11.25], "zoom 2 shows half the width and height"
    assert got["anchored"] == [True, True, 2], "the point under the pointer stays where it was"
    assert got["zoomClamped"] == [3, 1, 1], "a zoom outside the limits (or not a number) is brought back"


@needs_node
def test_the_pan_never_lets_the_diorama_leave_the_view_and_a_drag_moves_the_scene_with_the_pointer(tmp_path):
    got = run_node(tmp_path, CAMERA)
    assert got["panClamp"] == [[True, True]] * 4, "at least half of the box stays visible on each axis, in every direction"
    assert got["deepInside"] == [True, True], "a view narrower than half the box stays inside the box"
    assert got["dragDirection"] == [True, True], "dragging right moves the view left, so the scene follows the pointer"


@needs_node
def test_a_press_that_moves_more_than_a_few_pixels_is_a_pan_not_a_click_and_fit_restores_the_whole_diorama(tmp_path):
    got = run_node(tmp_path, CAMERA)
    assert got["drag"] == [False, False, False, True, True, True], "up to 5 px is a click; beyond it a pan (the threshold is a distance, not an axis)"
    assert got["wandered"] is True and got["fit"] == [{"zoom": 1, "x": 0, "y": 0}, {"zoom": 1, "x": 0, "y": 0}], "fit is the whole diorama, no offset"
    assert got["keptOnResize"] == {"zoom": 2, "x": 2, "y": 1}, "a resize keeps the person's zoom and offset when they are inside the limits"
    assert got["pulledBackOnResize"] is True, "and brings an offset that is no longer inside them back"


@needs_node
def test_the_keys_and_the_wheel_of_the_camera_and_the_pointer_maps_to_the_canvas_by_its_css_box(tmp_path):
    got = run_node(tmp_path, CAMERA)
    assert got["keys"] == [{"zoom": 1.25}, {"zoom": 1.25}, {"zoom": 0.8}, {"zoom": 0.8}, {"fit": True}, {"pan": [0.1, 0]}, {"pan": [-0.1, 0]},
                           {"pan": [0, 0.1]}, {"pan": [0, -0.1]}, None]
    assert got["wheel"] == [True] * 5
    corner, centre, far, inner = got["ndc"]
    assert corner == {"x": -1, "y": 1} and centre == {"x": 0, "y": -0} or centre == {"x": 0, "y": 0}, "the top left is (-1, 1), the middle is (0, 0)"
    assert far == {"x": 1, "y": -1} and inner == {"x": -0.5, "y": 0.5}, "a canvas scaled by CSS maps by its box"
    assert got["ndcBuffer"] in ({"x": 0, "y": 0}, {"x": 0, "y": -0}), "the drawing buffer of a 2x display does not enter the mapping"


def test_the_engine_moves_the_camera_on_demand_only_and_offers_the_buttons_the_keys_the_wheel_the_pinch_and_the_double_click():
    engine = (SCENE / "engine.js").read_text(encoding="utf-8")
    for needle in ('"wheel", onWheel, { passive: false }', '"dblclick", onDoubleClick', '"keydown", onKeyDown', '"pointerdown", onDown',
                   'aria-label": label', "Zoom in", "Zoom out", "Fit the scene", "pinch", "setPointerCapture", "isDrag("):
        assert needle in engine, f"engine.js has {needle}"
    set_view = re.search(r"function setView\(next\) \{(.*?)\n  \}", engine, re.S).group(1)
    assert "loop.requestRender()" in set_view and "requestAnimationFrame" not in engine.replace("raf: (fn) => requestAnimationFrame(fn)", ""), \
        "a camera change asks for one frame; there is no loop for it"
    assert 'tabindex: "0"' in engine and 'role: "img"' in engine, "the canvas can have the focus for the keys"
    css = (INTERFACE / "style.css").read_text(encoding="utf-8")
    assert "touch-action: none" in css and ".wb-camera-tools" in css and ".wb-canvas:focus-visible" in css
    for name in ("plus", "maximize", "minus"):
        assert (INTERFACE / "icons" / f"{name}.svg").is_file()
    assert not re.search(r"setInterval|setTimeout\(\s*(?:animate|draw|tick)", engine), "no timer drives the camera"


# --- windows ---------------------------------------------------------------------------------------------------------------------

WINDOWS = r"""
import { windowState, windowColour, windowUnlit } from "@JS@/scene/look.js";
import * as model from "@JS@/model.js";
import * as fm from "@JS@/floor-model.js";
import { roomModel } from "@JS@/views/lobby-model.js";

const palette = { warm: "WARM", windows: { lit: "WARM", grey: "BORDER" } };
const out = {};
out.state = [windowState(true), windowState(false)];
out.colour = [windowColour(palette, "lit"), windowColour(palette, "grey"), windowColour(palette, "pale"), windowColour(palette, "dark"), windowColour(palette, undefined)];
out.unlit = [windowUnlit("lit"), windowUnlit("grey"), windowUnlit("pale")];
// the City: only a floor whose agent has a running task is lit
const project = { id: "aaaaaaaaaaaa", name: "shop", config: { accepted: true }, running_task: 5, open_pending: 0 };
const agents = [{ name: "planning", enabled: true, acting_mode: "supervised" }, { name: "engineering", enabled: true, acting_mode: "autonomous" },
  { name: "design", enabled: false, acting_mode: "stopped" }, { name: "marketing", enabled: true, acting_mode: "milestones" }];
const status = { requests: [{ id: 1, title: "R", state: "ready", tasks: [{ id: 5, key: "a", title: "A", state: "running", agent: "engineering" }, { id: 6, key: "b", title: "B", state: "waiting", agent: "marketing" }] }], pending: [{ id: 9, task_id: 6, agent: "marketing", kind: "question", title: "q" }] };
const b = model.buildingOf(project, { status, agents });
out.city = b.floors.map((f) => [f.agent, f.window]);
const unaccepted = model.buildingOf({ ...project, config: { accepted: false } }, { status, agents });
out.cityUnaccepted = unaccepted.floors.map((f) => f.window);
// the Building and the Lobby's room
const view = fm.building({ projects: [project], details: { [project.id]: { status, agents: agents.map((a) => ({ ...a, mode: a.acting_mode, max_runs_per_day: 5, max_usd_per_day: 5, runs_today: 0, usd_today: 0, runs_without_cost: 0, queued: 0 })) } }, tasks: {}, loaded: true }, project.id);
out.building = view.rows.map((r) => [r.name, r.state, r.window]);
const lobby = (extra) => roomModel({ working: false, decisions: 0, hasMessages: true, accepted: true, request: null, ...extra }).window;
out.lobby = [lobby({ working: true }), lobby({ decisions: 2 }), lobby({}), lobby({ accepted: false })];
console.log(JSON.stringify(out));
"""


@needs_node
def test_a_window_is_warm_when_its_agent_works_and_grey_in_every_other_state_and_there_is_no_pale(tmp_path):
    got = run_node(tmp_path, WINDOWS)
    assert got["state"] == ["lit", "grey"]
    assert got["colour"] == ["WARM", "BORDER", "BORDER", "BORDER", "BORDER"], "working -> the warm recipe; every other state, even an old word, the border tone"
    assert got["unlit"] == [True, False, False], "only a lit window is an unlit (self-lit) material"
    assert got["city"] == [["planning", "grey"], ["engineering", "lit"], ["design", "grey"], ["marketing", "grey"]], "a waiting, stopped or idle floor is grey"
    assert got["cityUnaccepted"] == ["grey"] * 4
    assert got["building"] == [["planning", "idle", "grey"], ["engineering", "working", "lit"], ["design", "off", "grey"], ["marketing", "waiting", "grey"]]
    assert got["lobby"] == ["lit", "grey", "grey", "grey"]
    palette = (SCENE / "palette.js").read_text(encoding="utf-8")
    assert re.search(r"palette\.windows = \{ lit: palette\.warm, grey: T\.border \};", palette), "the grey is the border token, the same recipe in light and in dark"
    for path in sorted(JS.rglob("*.js")):
        if "vendor" in path.parts or path.name == "three.js":
            continue
        assert not re.search(r"""["']pale["']""", path.read_text(encoding="utf-8")), f"{path.name} has no pale window state"


# --- outlines ----------------------------------------------------------------------------------------------------------------------

OUTLINES = r"""
import * as THREE from "@JS@/three.js";
import { createKit } from "@JS@/scene/kit.js";
import { outlineVisible, applyOutlineVisibility } from "@JS@/scene/look.js";
import { buildCity } from "@JS@/scene/city.js";
import { buildBuilding } from "@JS@/scene/building.js";
import { buildRoom } from "@JS@/scene/room.js";
import { buildServer } from "@JS@/views/control-scene.js";
import { sceneModel as serverModel } from "@JS@/views/control-model.js";
import * as model from "@JS@/model.js";
import * as fm from "@JS@/floor-model.js";

const c = (hex) => new THREE.Color(hex);
const T = { border: c(0x101010), theme: c(0x2020f0), success: c(0x10f010), error: c(0xf01010), emphasis: c(0x303030), text: c(0x404040), warn: c(0xf0a010), textMuted: c(0x505050), mutedRole: c(0x707070) };
const mix = (a, b, t) => a.clone().lerp(b, t);
const bg = c(0xfafafa);
const palette = { dark: false, T, mix, bg, shell: c(0xf8f8f8), ink: c(0x202020), metal: c(0x606060), deskTop: c(0xd0d0d0), screenOff: c(0x181818), leafA: c(0x80c080), leafB: c(0x70b070), trunk: c(0x806040),
  lot: c(0xffffff), warm: c(0xf0c040), pale: c(0xd0d8f0), glass: c(0xd0e0f0), wood: c(0xc0a080), drawer: c(0x9090d0), skin: c(0xe0c0b0), windows: { lit: c(0xf0c040), grey: T.border } };

const out = {};
out.rule = [outlineVisible("a", null, null), outlineVisible("a", "a", null), outlineVisible("a", null, "a"), outlineVisible("a", "b", "c"), outlineVisible(null, null, null), outlineVisible("a", "a", "a")];
const visible = (built) => built.outlines.flatMap((o) => o.lines.map((l) => [o.id, l.visible]));

// the City: no lot line stands; only the hovered lot's shows
const lots = [0, 1].map((i) => ({ id: `lot${i}`, name: `p${i}`, accepted: true, decisions: 0, runningTask: i === 0 ? 5 : null, floors: [{ window: "grey", waits: false }, { window: "lit", waits: false }], tip: "t", sub: "s" }));
let kit = createKit(palette);
const city = buildCity(kit, { selectedId: "lot0", outlined: null, ready: true, lots });
out.cityBuilt = visible(city);
applyOutlineVisibility(city.outlines, null, city.selected);
out.cityNothing = visible(city);
applyOutlineVisibility(city.outlines, "lot1", city.selected);
out.cityHover = visible(city);
out.citySelected = city.selected;
kit.dispose();

// the Building: no floor line without a hover
kit = createKit(palette);
const mk = (name, extra = {}) => ({ name, label: name, state: "idle", window: "grey", decisions: 0, lobby: name === "planning", sheets: 0, drawers: 1, tip: `${name} tip`, interactive: true, ...extra });
const building = buildBuilding(kit, { ready: true, selected: "b", focus: null, more: 0, tag: { floor: "b", text: "#1" }, doorText: "Control room", floors: [mk("planning"), mk("b", { state: "working", window: "lit" })] });
applyOutlineVisibility(building.outlines, null, building.selected);
out.buildingNothing = visible(building);
applyOutlineVisibility(building.outlines, "floor:b", building.selected);
out.buildingHover = visible(building);
out.buildingSelected = building.selected;
kit.dispose();

// the room (the Floor, the Lobby) and the Control room: the route selects them, so their floor line is drawn
kit = createKit(palette);
const tips = { agent: "a", desk: "d", tray: "t", cabinet: "c", board: "b" };
const room = buildRoom(kit, { ready: true, state: "working", window: "lit", decisions: 1, drawers: 1, sheets: [{ path: "docs/a.md", tip: "docs/a.md" }], tips, board: { title: "t", lines: [], dot: "theme" }, door: false });
applyOutlineVisibility(room.outlines, null, room.selected);
out.room = [visible(room), room.selected];
const server = buildServer(kit, serverModel({ accepted: true, connections: null, costs: null }));
applyOutlineVisibility(server.outlines, null, server.selected);
out.server = [visible(server), server.selected];
kit.dispose();
console.log(JSON.stringify(out));
"""


@needs_node
def test_no_outline_line_is_drawn_without_a_hover_or_a_selection_and_the_route_selects_the_room(tmp_path):
    got = run_node(tmp_path, OUTLINES)
    assert got["rule"] == [False, True, True, False, False, True], "an outline shows for the hovered or the selected object, never otherwise"
    assert got["cityBuilt"] == [["lot0", False], ["lot1", False]], "built hidden: no standing lot line"
    assert got["cityNothing"] == [["lot0", False], ["lot1", False]] and got["citySelected"] is None, "the City selects nothing (the route has no project)"
    assert got["cityHover"] == [["lot0", False], ["lot1", True]], "only the hovered lot's line"
    assert got["buildingNothing"] == [["floor:planning", False], ["floor:b", False]], "no floor line stands, not even for the work order's floor"
    assert got["buildingHover"] == [["floor:planning", False], ["floor:b", True]] and got["buildingSelected"] is None
    assert got["room"] == [[["room", True]], "room"] and got["server"] == [[["room", True]], "room"], "the room the route selects keeps its floor line"


def test_the_hover_outline_is_the_prototypes_thin_depth_tested_line_that_follows_a_shape_where_the_object_is_not_a_box():
    engine = (SCENE / "engine.js").read_text(encoding="utf-8")
    assert "new THREE.LineBasicMaterial({ color: 0xffffff });" in engine, "a one-pixel line of the theme colour, full opacity, depth-tested (no depthTest: false, no renderOrder)"
    assert "depthTest: false" not in engine and "renderOrder" not in engine
    assert "OUTLINE_PAD = 0.04" in engine and "SHAPE_GROW" in engine and "EdgesGeometry(node.geometry" in engine, "the outline of a figure, a desk, a tray, a sheet is the edges of its own meshes"
    room = (SCENE / "room.js").read_text(encoding="utf-8")
    assert len(re.findall(r"shape: true", room)) == 4, "the figure, the desk, the tray and each sheet are outlined by their shape"
    city = (SCENE / "city.js").read_text(encoding="utf-8")
    assert "kit.themeLine, group);" in city and "edge.visible = false" in city, "the lot line is built hidden"
    assert "beacon = null" in city and "lot.runningTask !== null && lot.accepted" in city, "the beacon ring exists only for a running task"
    assert "Math.sin(seconds * 3)" in city and "0.12 * wave" in city and "0.35 + 0.3" in city, "the beacon is the prototype's: sin(3 t), scale 1 +- .12, opacity .35 to .65"


# --- one object per destination ------------------------------------------------------------------------------------------------------

HITS = r"""
import * as THREE from "@JS@/three.js";
import { createKit } from "@JS@/scene/kit.js";
import { buildRoom } from "@JS@/scene/room.js";

const c = (hex) => new THREE.Color(hex);
const T = { border: c(0x101010), theme: c(0x2020f0), success: c(0x10f010), error: c(0xf01010), emphasis: c(0x303030), text: c(0x404040), warn: c(0xf0a010), textMuted: c(0x505050), mutedRole: c(0x707070) };
const palette = { dark: false, T, mix: (a, b, t) => a.clone().lerp(b, t), bg: c(0xfafafa), shell: c(0xf8f8f8), ink: c(0x202020), metal: c(0x606060), deskTop: c(0xd0d0d0), screenOff: c(0x181818), leafA: c(0x80c080), leafB: c(0x70b070), trunk: c(0x806040),
  lot: c(0xffffff), warm: c(0xf0c040), pale: c(0xd0d8f0), glass: c(0xd0e0f0), wood: c(0xc0a080), drawer: c(0x9090d0), skin: c(0xe0c0b0), windows: { lit: c(0xf0c040), grey: T.border } };
const tips = { agent: "a", desk: "d", tray: "t", cabinet: "cab", board: "board" };
const out = {};
for (const [state, door] of [["working", false], ["waiting", false], ["idle", true], ["off", false]]) {
  const kit = createKit(palette);
  const room = buildRoom(kit, { ready: true, state, window: "grey", decisions: 2, drawers: 3, sheets: [{ path: "docs/a.md", tip: "a" }, { path: "docs/b.md", tip: "b" }], tips, board: { title: "t", lines: ["x"], dot: "theme" }, door });
  out[`${state}${door ? "+door" : ""}`] = room.hits.map((h) => h.id);
  kit.dispose();
}
console.log(JSON.stringify(out));
"""


@needs_node
def test_a_room_has_one_object_for_each_destination_and_the_cabinet_and_the_board_are_only_scenery(tmp_path):
    got = run_node(tmp_path, HITS)
    assert got["working"] == ["desk", "tray", "agent", "sheet:docs/a.md", "sheet:docs/b.md"], "figure -> Agent, desk -> Desk, tray -> Inbox, a sheet -> its document"
    assert got["waiting"] == got["working"]
    assert got["off"] == ["desk", "tray", "sheet:docs/a.md", "sheet:docs/b.md"], "no figure, no agent hit"
    assert got["idle+door"][-1] == "lobby-door" and "cabinet" not in got["idle+door"] and "board" not in got["idle+door"]
    for ids in got.values():
        assert "cabinet" not in ids and "board" not in ids, "nothing opens from the cabinet or the board, and they get no outline"
    for name, tab_by_id in (("floor.js", {"tray": "inbox", "desk": "desk", "agent": "agent"}), ("lobby.js", {"tray": "inbox", "desk": "desk", "agent": "agent"})):
        text = (JS / "views" / name).read_text(encoding="utf-8")
        for hit, tab in tab_by_id.items():
            assert re.search(rf'id === "{hit}"\) window\.location\.hash = router\.\w+\((?:project, agent|project), "{tab}"\)', text), f"{name}: {hit} opens {tab}"
        assert '"cabinet"' not in text and '"board"' not in text, f"{name} maps no click from the cabinet or the board"


# --- no rebuild on a poll that changed only words -----------------------------------------------------------------------------------

REBUILD = r"""
import { showPlan } from "@JS@/scene/look.js";
import { BUILDERS } from "@JS@/scene/engine.js";

const lot = (extra = {}) => ({ id: "a", name: "shop", accepted: true, decisions: 1, runningTask: 5, floors: [{ window: "lit", waits: false }, { window: "grey", waits: true }], tip: "shop: 1 decision waiting, task #5 running", sub: "task #5 running", ...extra });
const city = (l) => ({ selectedId: "a", outlined: null, ready: true, lots: [l] });
const floor = (extra = {}) => ({ name: "eng", label: "Engineering", state: "working", window: "lit", decisions: 0, lobby: false, sheets: 2, drawers: 1, tip: "Engineering: working, 2 of 8 runs", interactive: true, ...extra });
const building = (f, extra = {}) => ({ ready: true, selected: "eng", focus: null, more: 0, tag: { floor: "eng", text: "#1" }, doorText: "Control room →", floors: [f], ...extra });
const room = (extra = {}) => ({ ready: true, state: "working", window: "lit", decisions: 1, drawers: 1, sheets: [{ path: "docs/a.md", tip: "docs/a.md" }], tips: { agent: "a", desk: "Current task · A", tray: "t", cabinet: "c", board: "b" }, board: { title: "A", lines: ["run #1 Running"], dot: "theme" }, door: false, ...extra });

// a sequence of polls, as the engine's show() sees them: the plan each one gets
function sequence(kind, models) {
  const structureOf = (BUILDERS[kind] || {}).structure;
  let before = { signature: "", structure: "", built: false };
  return models.map((m) => {
    const plan = showPlan(before, kind, m, structureOf);
    if (plan.action !== "none") before = { signature: plan.signature, structure: plan.action === "build" ? plan.structure : before.structure, built: true };
    return plan.action;
  });
}
const out = {};
out.city = sequence("city", [city(lot()), city(lot()), city(lot({ decisions: 3, tip: "x", sub: "task #6 running", name: "shop2" })), city(lot({ runningTask: null })), city(lot({ runningTask: null })),
  city(lot({ runningTask: null, floors: [{ window: "grey", waits: false }, { window: "grey", waits: true }] }))]);
out.building = sequence("building", [building(floor()), building(floor()), building(floor({ tip: "Engineering: working, 3 of 8 runs" })), building(floor(), { doorText: "Control room" }),
  building(floor({ state: "idle", window: "grey" })), building(floor({ state: "idle", window: "grey" }), { tag: { floor: "eng", text: "#2" } }), building(floor({ state: "idle", window: "grey" }), { tag: null })]);
out.room = sequence("room", [room(), room(), room({ board: { title: "A", lines: ["run #1 Running · 1m 02s"], dot: "theme" }, tips: { agent: "a", desk: "Current task · A", tray: "t", cabinet: "c", board: "bb" } }),
  room({ decisions: 2 }), room({ decisions: 2, sheets: [{ path: "docs/b.md", tip: "docs/b.md" }] })]);
out.unknownKind = sequence("nowhere", [{ a: 1 }, { a: 1 }, { a: 2 }]);
console.log(JSON.stringify(out));
"""


@needs_node
def test_a_poll_that_found_the_same_state_or_only_other_words_does_not_build_the_scene_again(tmp_path):
    got = run_node(tmp_path, REBUILD)
    assert got["city"] == ["build", "none", "relabel", "build", "none", "build"], "the same model: nothing; other words: the labels only; a task that stopped or a window that changed: build"
    assert got["building"] == ["build", "none", "relabel", "relabel", "build", "relabel", "build"], \
        "a meter or a tip is words; a state, a window or the work order's floor is structure"
    assert got["room"] == ["build", "none", "relabel", "build", "build"], "the board's lines and the tooltips are words; the decisions and the sheets are structure"
    assert got["unknownKind"] == ["build", "none", "build"], "a scene with no builder is its own structure"


def test_the_engine_never_restarts_a_motion_when_it_rebuilds_and_every_builder_that_labels_has_a_structure():
    engine = (SCENE / "engine.js").read_text(encoding="utf-8")
    assert "const epoch = clock();" in engine and "(now - epoch) / 1000" in engine and "pulseStart" not in engine, "the ambient clock is the engine's, never reset by a rebuild"
    assert "showPlan(" in engine and "relabel();" in engine and "content.text(model)" in engine
    for name, builder in (("city.js", "buildCity"), ("building.js", "buildBuilding"), ("room.js", "buildRoom")):
        text = (SCENE / name).read_text(encoding="utf-8")
        assert f"{builder}.structure = " in text and "function text(" in text and " text," in text, f"{name}: the structure and the words are apart"
    for name in ("views/city.js", "views/building.js", "views/floor.js", "views/lobby-scene.js"):
        text = (JS / name).read_text(encoding="utf-8")
        assert "engine.show(" in text or "engine.show" in text, f"{name} shows the scene through the engine"


# --- the motions of the prototype ----------------------------------------------------------------------------------------------------

MOTION = r"""
import { workingMotion, scanY, SCAN_PERIOD, TYPING_RATE, TYPING_AMPLITUDE, TYPING_PHASE } from "@JS@/scene/figure.js";
import { pulseBeacon, restBeacon } from "@JS@/scene/city.js";
import { createTween } from "@JS@/scene/tween.js";

const out = {};
out.constants = [TYPING_RATE, TYPING_AMPLITUDE, TYPING_PHASE, SCAN_PERIOD];
const elbows = [{ rotation: { x: -1 } }, { rotation: { x: -1 } }];
let calls = 0;
const who = { typing(s) { calls += 1; elbows[0].rotation.x = -1 + TYPING_AMPLITUDE * Math.sin(s * TYPING_RATE); elbows[1].rotation.x = -1 + TYPING_AMPLITUDE * Math.sin(s * TYPING_RATE + TYPING_PHASE); }, rest() { elbows.forEach((e) => { e.rotation.x = -1; }); } };
const scan = { position: { y: 0 } };
const motion = workingMotion(who, { scan });
motion.tick(0.1);
out.ticked = [calls, scan.position.y > 0.95, scan.position.y < 1.35];
motion.rest();
out.rest = [elbows[0].rotation.x, elbows[1].rotation.x, scan.position.y];
// the scan line is a slow sine: no jump, back where it started after one period, always on the screen (y .95 to 1.35)
let maxStep = 0; let lo = 9; let hi = -9;
for (let t = 0; t < 2 * SCAN_PERIOD; t += 0.01) { maxStep = Math.max(maxStep, Math.abs(scanY(t + 0.01) - scanY(t))); lo = Math.min(lo, scanY(t)); hi = Math.max(hi, scanY(t)); }
out.scan = [maxStep < 0.01, lo >= 0.95, hi <= 1.35, Math.abs(scanY(SCAN_PERIOD) - scanY(0)) < 1e-9];
// the beacon: sin(3 t), scale 1 +- .12 in its plane only, opacity .35 to .65
const beacon = { ring: { scale: { x: 1, y: 1, z: 1, set(a, b, c) { this.x = a; this.y = b; this.z = c; } } }, material: { opacity: 1 } };
const samples = [];
for (let t = 0; t < 2.2; t += 0.01) { pulseBeacon(beacon, t); samples.push([beacon.ring.scale.x, beacon.ring.scale.z, beacon.material.opacity]); }
out.beacon = [Math.min(...samples.map((s) => s[0])), Math.max(...samples.map((s) => s[0])), samples.every((s) => s[1] === 1), Math.min(...samples.map((s) => s[2])), Math.max(...samples.map((s) => s[2]))];
out.period = Math.abs(Math.sin(2 * Math.PI / 3 * 3)) < 1e-9;
restBeacon(beacon);
out.beaconRest = [beacon.ring.scale.x, beacon.material.opacity];
// a move may settle early (the screen is opened while the camera is still on its way) and still runs to its end
const t = createTween();
const a = { left: 0, right: 10, top: 10, bottom: 0 }; const b = { left: 2, right: 6, top: 8, bottom: 4 };
const settled = [];
const move = t.start(a, b, 0, 1000, 0.5); move.then((v) => settled.push(v));
t.step(100); await new Promise((r) => setTimeout(r, 5)); out.early = [settled.slice(), t.active()];
t.step(500); await new Promise((r) => setTimeout(r, 5)); out.atHalf = [settled.slice(), t.active()];
const last = t.step(1000); out.end = [last.left, t.active()];
const cut = t.start(a, b, 0, 1000, 0.5); const cutSettled = []; cut.then((v) => cutSettled.push(v)); t.cancel(); await new Promise((r) => setTimeout(r, 5)); out.cut = cutSettled;
const late = t.start(a, b, 0, 1000, 0.5); const lateSettled = []; late.then((v) => lateSettled.push(v)); t.step(600); t.cancel(); await new Promise((r) => setTimeout(r, 5)); out.lateCancel = lateSettled;
console.log(JSON.stringify(out));
"""


@needs_node
def test_the_motions_are_the_prototypes_numbers_the_scan_line_never_jumps_and_a_move_may_hand_over_early(tmp_path):
    got = run_node(tmp_path, MOTION)
    assert got["constants"] == [11, 0.22, 2, 3.2], "the forearms swing 0.22 rad at 11 rad/s with the second 2 rad behind; the scan line's round trip is 3.2 s"
    assert got["ticked"] == [1, True, True] and got["rest"] == [-1, -1, 1.15], "tick moves the forearms and the scan, rest puts them back"
    assert got["scan"] == [True, True, True, True], "a smooth sine on the screen that is back where it began after a period"
    lo, hi, flat, olo, ohi = got["beacon"]
    assert abs(lo - 0.88) < 1e-3 and abs(hi - 1.12) < 1e-3 and flat is True, "scale 1 +- .12 in the ring's plane, the thickness stays"
    assert abs(olo - 0.35) < 1e-3 and abs(ohi - 0.65) < 1e-3 and got["period"] is True, "opacity .35 to .65, a cycle of 2 pi / 3 s"
    assert got["beaconRest"] == [1, 1]
    assert got["early"] == [[], True] and got["atHalf"] == [[True], True], "settled at the hand-over fraction, still moving"
    assert got["end"] == [2, False], "the move runs to its end"
    assert got["cut"] == [False] and got["lateCancel"] == [True], "a cut before the hand-over settles false, after it stays true"


def test_the_state_animations_keep_the_rules_of_the_scene_and_the_figure_does_not_fidget():
    figure = (SCENE / "figure.js").read_text(encoding="utf-8")
    for fidget in ("position.y = Math.sin", "head.rotation", "rotation.y = t", "Math.random", "spark"):
        assert fidget not in figure, f"the figure does not {fidget}: only the forearms type"
    engine = (SCENE / "engine.js").read_text(encoding="utf-8")
    assert re.search(r"export const CAMERA_MS = 1023;", engine) and "OPEN_MS = 1439" in engine and "FLY_SETTLE_AT = 0.5" in engine
    assert "openEase(t)" in engine and "positionLabels();   // the labels ride along with the camera" in engine, "the labels follow the camera and the opening instead of vanishing"
    assert 'loop.start("beacon", { ambient: true })' in engine, "typing and the beacon are ambient: held to 30 frames a second"
    assert "pulseStart = clock()" not in engine


# --- the request selector of the tracking bar -----------------------------------------------------------------------------------------

REQUESTS = r"""
import * as model from "@JS@/model.js";
import { FakeNode, find, all } from "@FAKE@";
import { createTrack } from "@JS@/frame/track.js";

const task = (id, state, agent = "engineering") => ({ id, key: `k${id}`, title: `Task ${id}`, state, agent });
const status = { requests: [
  { id: 1, title: "Old and done", state: "done", tasks: [task(1, "done")] },
  { id: 2, title: "Spring", state: "ready", tasks: [task(2, "done"), task(3, "running")] },
  { id: 3, title: "Fix cart", state: "ready", tasks: [task(4, "waiting")] },
  { id: 4, title: "Docs", state: "ready", tasks: [task(5, "ready")] },
  { id: 5, title: "Dropped", state: "cancelled", tasks: [] }], pending: [] };
const idle = { requests: [{ id: 7, title: "A", state: "ready", tasks: [task(8, "ready")] }, { id: 9, title: "B", state: "ready", tasks: [task(10, "waiting")] }], pending: [] };
const none = { requests: [{ id: 1, title: "x", state: "done", tasks: [] }], pending: [] };
const out = {};
model.resetRequestChoices();
out.open = model.openRequests(status).map((r) => r.id);
out.defaultRunning = model.pickRequest(status).id;          // the newest with a running task, not the newest open (4)
out.defaultNewest = model.pickRequest(idle).id;             // no running task: the newest open
out.defaultNone = [model.pickRequest(none), model.pickRequest({ requests: [] }), model.pickRequest(null)];
out.chosen = model.pickRequest(status, 3).id;
out.choiceGone = model.pickRequest(status, 1).id;           // a request that is done is no choice: back to the default
out.cycle = [model.cycleRequest(status, 4, 1).id, model.cycleRequest(status, 3, 1).id, model.cycleRequest(status, 2, 1).id, model.cycleRequest(status, 4, -1).id, model.cycleRequest(status, 2, -1).id, model.cycleRequest(status, 99, 1).id, model.cycleRequest(none, 1, 1)];
// the choice is kept for each project, in memory, and forgotten with a new session
model.chooseRequest("p1", 3);
out.kept = [model.requestChoice("p1"), model.requestChoice("p2")];
model.resetRequestChoices();
out.forgotten = model.requestChoice("p1");

const snapshot = (c) => ({ projects: [{ id: "p1", name: "shop", config: { accepted: true }, running_task: 3 }], details: { p1: { status, agents: [{ name: "engineering", enabled: true }] } }, tasks: {}, loaded: true, ...c });
const bar = (choice) => { model.resetRequestChoices(); if (choice) model.chooseRequest("p1", choice); return model.tracking(snapshot(), "p1", new Date("2026-10-08T12:00:00Z")); };
const def = bar(null); const picked = bar(3);
out.tracking = [def.request.id, def.requests.map((r) => [r.id, r.selected, r.running]), def.now.title, picked.request.id, picked.steps.map((s) => s.title), picked.now.title, picked.now.state];
out.needed = (() => { model.resetRequestChoices(); const a = model.neededTasks(snapshot().projects, snapshot().details, "p1").map((t) => t.id); model.chooseRequest("p1", 3); const b = model.neededTasks(snapshot().projects, snapshot().details, "p1").map((t) => t.id); return [a, b]; })();
model.resetRequestChoices();

// the bar: one open request is a plain badge; several are a chip with a list and the two buttons; none hides the bar
const chosen = [];
const track = createTrack({ onOpenSteps() {}, onSelectRequest: (p, id) => chosen.push([p, id]) });
document.activeElement = null;
FakeNode.prototype.getBoundingClientRect = () => ({ left: 10, top: 500 });
track.set(def, "ready");
out.barShown = !track.el.hidden;
const chip = find(track.el, ".wb-req-chip");
out.selectorParts = [Boolean(chip), all(track.el, ".wb-track-desktop .wb-req-step").map((b) => b.attrs["aria-label"]), all(track.el, ".wb-track-desktop .wb-req-option").map((o) => [o.attrs["data-request"], o.attrs["aria-selected"]]), chip.attrs["aria-expanded"], find(track.el, ".wb-req-menu").hidden];
chip.click();
out.opened = [chip.attrs["aria-expanded"], find(track.el, ".wb-req-menu").hidden];
all(track.el, ".wb-track-desktop .wb-req-option")[1].click();
out.chose = [chosen.slice(), chip.attrs["aria-expanded"]];
const steps = all(track.el, ".wb-track-desktop .wb-req-step");
steps[0].click(); steps[1].click();
out.stepped = chosen.slice(1);
const single = { ...def, requests: [def.requests[0]] };
track.set(single, "ready");
out.single = [Boolean(find(track.el, ".wb-req-chip")), Boolean(find(track.el, ".wb-req-id"))];
track.set(null, "empty");
out.emptyHidden = track.el.hidden;
track.set(null, "loading");
out.loadingShown = !track.el.hidden;
console.log(JSON.stringify(out));
"""


@needs_node
def test_the_bar_shows_the_newest_request_with_a_running_task_else_the_newest_open_one_and_the_choice_is_kept_per_project(tmp_path):
    got = run_node(tmp_path, REQUESTS)
    assert got["open"] == [4, 3, 2], "the open requests, newest first (done and cancelled are not open)"
    assert got["defaultRunning"] == 2, "the newest request that has a running task, even when a newer one is open"
    assert got["defaultNewest"] == 9 and got["defaultNone"] == [None, None, None]
    assert got["chosen"] == 3 and got["choiceGone"] == 2, "a choice holds while that request is open"
    assert got["cycle"] == [3, 2, 4, 2, 3, 4, None], "next goes to the older one, previous to the newer one, and both wrap round"
    assert got["kept"] == [3, None] and got["forgotten"] is None, "in memory, for each project, forgotten with the session"
    track = got["tracking"]
    assert track[:3] == [2, [[4, False, False], [3, False, False], [2, True, True]], "Task 3"], "the bar and Now on follow the default request"
    assert track[3:] == [3, ["Task 4"], "Task 4", "Waiting for you"], "after a choice, the steps and the Now on card are the chosen request's"
    assert got["needed"] == [[3], []], "the running task whose start time is read follows the request shown"


@needs_node
def test_the_request_selector_opens_a_list_chooses_steps_both_ways_and_the_bar_hides_when_nothing_is_open(tmp_path):
    got = run_node(tmp_path, REQUESTS)
    assert got["barShown"] is True
    assert got["selectorParts"] == [True, ["Previous request", "Next request"], [["4", "false"], ["3", "false"], ["2", "true"]], "false", True]
    assert got["opened"] == ["true", False], "the chip opens the list"
    assert got["chose"] == [[["p1", 3]], "false"], "choosing sends the request and closes the list"
    assert got["stepped"] == [["p1", 3], ["p1", 4]], "previous and next step through the list from the selected one, wrapping"
    assert got["single"] == [False, True], "with one open request the number is a plain badge"
    assert got["emptyHidden"] is True and got["loadingShown"] is True, "no open request: the bar is hidden; loading: it shows its line"
    track = (JS / "frame" / "track.js").read_text(encoding="utf-8")
    for needle in ('"aria-haspopup": "listbox"', 'role: "listbox"', 'role: "option"', '"ArrowDown"', '"ArrowUp"', '"Escape"', "focusout"):
        assert needle in track, f"track.js: {needle} (keyboard path of the selector)"
    assert "model.chooseRequest" in (JS / "main.js").read_text(encoding="utf-8") and "resetRequestChoices()" in (JS / "main.js").read_text(encoding="utf-8")
    css = (INTERFACE / "style.css").read_text(encoding="utf-8")
    assert ".wb-track[hidden]" in css and ".wb-req-menu" in css and "position: fixed" in css


# --- the pointer's pick is never dropped --------------------------------------------------------------------------------------------------

def test_the_last_move_of_a_motion_is_always_picked_and_the_pick_runs_again_when_the_camera_moves_under_a_still_mouse():
    engine = (SCENE / "engine.js").read_text(encoding="utf-8")
    assert "pendingTimer = setTimeout(runPending, wait)" in engine, "a move that comes too soon is picked when the interval is over"
    assert "pointerToNdc(event.clientX, event.clientY, rect)" in engine and "pointerToNdc(clientX, clientY, canvas.getBoundingClientRect())" in engine
    assert re.search(r"hoverAt\(lastMouse\)", engine), "the camera moved under a still mouse: the object under it is picked again"
    assert "clearTimeout(pendingTimer)" in engine, "the timer goes with the engine"
