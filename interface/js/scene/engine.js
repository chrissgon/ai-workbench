// The scene engine: one WebGL renderer for the page, an isometric orthographic camera, the palette read from the page's
// tokens, picking, HTML labels and the render scheduler. It draws a scene only when something changed (loop.js), at most
// 30 frames a second while an ambient animation runs, never while the tab is hidden, at a pixel ratio of at most 2, and
// with no ambient animation under reduced motion. Without WebGL it throws NoWebGL and the screen shows its HTML alone.
//
// What it draws is built by a scene builder (city.js now; the building, floor, lobby and control room scenes come with
// their packages through the same `show(kind, model)`).

import * as THREE from "../three.js";
import { h } from "../dom.js";
import { icon } from "../frame/icons.js";
import { buildBuilding } from "./building.js";
import { clampView, fitView, frustumOf, panBy, panPixels, pointerToNdc, zoomAt } from "./camera.js";
import { buildCity, pulseBeacon, restBeacon } from "./city.js";
import { ease, fitFrustum } from "./fit.js";
import { createKit } from "./kit.js";
import { cornerPosition, fitInsets, mountLabels, placeLabels } from "./labels.js";
import { applyOutlineVisibility, showPlan } from "./look.js";
import { createLoop } from "./loop.js";
import { outlineGeometry } from "./outline.js";
import { pickHit, pickList, visibleSamples } from "./pick.js";
import { createPointer } from "./pointer.js";
import { LIGHT_WHITE, readPalette } from "./palette.js";
import { buildRoom } from "./room.js";
import { contentBounds, createCamera } from "./rig.js";
import { createTween } from "./tween.js";
import { EXPLODE_RATE, createApproach, frameSeconds, smooth } from "./prototype-motion.js";

export const BUILDERS = { city: buildCity, building: buildBuilding, room: buildRoom };
// The motions of the prototype (WP-9.10: its own functions, prototype-motion.js, stepped frame by frame): the camera approaches its
// goal by `1 - exp(-dt * 4.5)` a frame and the building opens by `1 - exp(-dt * 3.2)` read through a smoothstep. A move ends when it is
// within one percent of its goal, which takes ln(100) over the rate: the two durations below are what that comes to, for the page's
// checks, not times the engine counts.
export const CAMERA_MS = 1023;    // A5: the camera moves in (ln 100 / 4.5 seconds)
export const OPEN_MS = 1439;      // A5: the building opens, the floors separate once (ln 100 / 3.2 seconds)
export const FLY_SETTLE_AT = 0.9; // the screen waits for the fly-in only until the move is nine tenths done (about 0.5 s)
export const DROP_MS = 300;       // A3: a waiting marker drops in once
export const TAG_MS = 600;        // A6: the work-order tag moves to the next floor once
export const OUTLINE_PAD = 0.04;  // the hover outline stands this far off the object (the prototype's, for a piece of furniture)


export class NoWebGL extends Error {
  constructor() {
    super("WebGL is not available");
    this.name = "NoWebGL";
  }
}

/**
 * Create the engine in `host`: it makes the canvas and the label overlay itself.
 * options: {label, getInsets() -> {left, right, top, bottom, pad}, onOpen(id), onHover(id|null), onUnavailable()}.
 */
export function createEngine(host, options) {
  const canvas = h("canvas", { class: "wb-canvas", role: "img", tabindex: "0", "aria-label": options.label || "Scene" });
  canvas.setAttribute("aria-describedby", "wb-camera-help");
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  } catch (e) {
    throw new NoWebGL();
  }
  if (!renderer.getContext()) throw new NoWebGL();
  const overlay = h("div", { class: "wb-overlay", "aria-hidden": "true" });
  const tooltip = h("div", { class: "pui-tooltip wb-tooltip", role: "tooltip", hidden: true });
  overlay.append(tooltip);
  // The HTML equivalent of the camera: zoom in, zoom out and fit, in reach of the keyboard. With the focus on the scene, + and -
  // zoom, the arrows pan and 0 fits; the wheel and a pinch zoom, a drag pans, a double click on the ground fits.
  const cameraButton = (label, name) => h("button", { class: "pui-btn pui-surface pui-outline wb-camera-btn", type: "button", "aria-label": label, title: label }, icon(name, 16));
  const zoomInButton = cameraButton("Zoom in", "plus");
  const zoomOutButton = cameraButton("Zoom out", "minus");
  const fitButton = cameraButton("Fit the scene", "maximize");
  const tools = h("div", { class: "wb-camera-tools", role: "group", "aria-label": "Scene view" }, zoomInButton, zoomOutButton, fitButton,
    h("span", { class: "wb-sr", id: "wb-camera-help", text: "Scene view: plus and minus zoom, the arrow keys move, zero fits the whole scene." }));
  host.append(canvas, overlay, tools);

  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;   // the library's soft filter: the PCFSoft name was folded into it, and `shadow.radius` softens it
  renderer.shadowMap.autoUpdate = false;   // the sun does not move: shadows are drawn again only when the geometry changes
  const scene = new THREE.Scene();
  const camera = createCamera(THREE);

  const reducedQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
  const clock = () => performance.now();
  const loop = createLoop({
    raf: (fn) => requestAnimationFrame(fn), caf: (id) => cancelAnimationFrame(id),
    render: (ts) => draw(ts), hidden: () => document.hidden, reduced: () => reducedQuery.matches,
  });

  let palette = null;
  let worldKit = null;
  let contentKit = null;
  let content = null;             // what the builder returned
  let labelEntries = [];
  let model = null;
  let kind = null;
  let signature = "";
  let size = { w: 0, h: 0 };
  let frustum = null;             // the fitted frustum: the whole diorama in the free rectangle
  let bounds = null;              // the diorama's bounds in camera space
  let view = fitView();           // the person's zoom and pan on top of it (camera.js)
  const tween = createTween();    // the camera move in flight, if any
  let drops = [];                 // {marker, start}
  let intro = null;               // {approach, last}: the building opening (A5), the floors separating
  let introPlayed = false;
  let tagRun = null;              // {group, from, to, start}: the work-order tag moving (A6)
  let previousTag = null;         // {y}: where the tag was on the build before
  let lastInsets = null;
  let previousMarkers = new Set();
  let previousReady = false;      // the build before this one held real data: a marker not in it has arrived
  let previousDecisions = new Map();
  let outline = null;
  let hoverId = null;
  let lostText = false;
  let disposed = false;
  const epoch = clock();          // the ambient animations' clock: it is never restarted, so a rebuild cannot restart a motion
  let structureSignature = "";
  let builds = 0;                 // how many times the scene was built and how many times only its words changed: the page's check that a poll does not rebuild
  let relabels = 0;
  let frameMs = 0;                // the browser-side cost of the last frame (submitting the draw calls)
  // The hover outline is the prototype's: a one-pixel line of the theme colour, full opacity, tested against the depth so the
  // edges behind the object stay hidden, standing OUTLINE_PAD off the object.
  const outlineMaterial = new THREE.LineBasicMaterial({ color: 0xffffff });

  // --- the world: lights and ground, rebuilt when the palette changes -----------------------------------------------------
  function buildWorld() {
    if (worldKit) {
      const old = scene.children.filter((c) => c.userData.world);
      scene.remove(...old);
      for (const light of old) if (light.shadow) light.shadow.dispose();   // the 2048 px shadow map of the sun being replaced
      worldKit.dispose();
    }
    palette = readPalette(host);
    worldKit = createKit(palette);
    const world = [];
    const hemi = new THREE.HemisphereLight(LIGHT_WHITE, palette.T.emphasis, palette.hemiIntensity);
    const sun = new THREE.DirectionalLight(LIGHT_WHITE, palette.sunIntensity);
    sun.position.set(-14, 34, 22);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    Object.assign(sun.shadow.camera, { left: -45, right: 45, top: 45, bottom: -45, near: 1, far: 140 });
    sun.shadow.radius = 5;
    sun.shadow.bias = -0.0006;
    const ground = new THREE.Mesh(worldKit.track(new THREE.PlaneGeometry(600, 600)), worldKit.unlit(palette.ground));
    ground.rotation.x = -Math.PI / 2;
    const shade = new THREE.Mesh(worldKit.track(new THREE.PlaneGeometry(600, 600)),
      worldKit.adopt(new THREE.ShadowMaterial({ color: palette.shadowColor, opacity: palette.shadowOpacity })));
    shade.rotation.x = -Math.PI / 2;
    shade.position.y = 0.01;
    shade.receiveShadow = true;
    world.push(hemi, sun, ground, shade);
    for (const object of world) object.userData.world = true;
    scene.add(...world);
    renderer.setClearColor(palette.ground, 1);
    outlineMaterial.color.copy(palette.T.theme);
  }

  // --- the content: a scene builder's group, rebuilt when the model changes ------------------------------------------------
  function clearContent() {
    stopAnimations();
    if (outline) {
      scene.remove(outline);
      outline.geometry.dispose();
      outline = null;
    }
    hoverId = null;
    if (content) scene.remove(content.group);
    if (contentKit) contentKit.dispose();
    for (const entry of labelEntries) entry.node.remove();
    labelEntries = [];
    content = null;
    contentKit = null;
  }

  function stopAnimations() {
    for (const name of ["camera", "drops", "beacon", "intro", "tag"]) loop.stop(name);
    tween.cancel();   // settles a waiting fly-in with false: nobody is left waiting for a move that will not finish
    drops = [];
    intro = null;
    tagRun = null;
  }

  function build() {
    builds += 1;
    clearContent();
    if (!model || !BUILDERS[kind]) return;
    contentKit = createKit(palette);
    content = BUILDERS[kind](contentKit, model);
    content.beacons = content.beacons || [];
    content.motions = content.motions || [];
    content.markers = content.markers || [];
    content.outlines = content.outlines || [];
    scene.add(content.group);
    applyOutlines();
    labelEntries = mountLabels(overlay, content.labels.map((l) => ({ ...l, anchor: l.anchor })), { popped: poppedOf(content.labels) });
    markLabels();
    const markerKeys = new Set(content.markers.map((m) => m.key));
    const fresh = previousReady ? content.markers.filter((m) => !previousMarkers.has(m.key)) : [];
    previousReady = Boolean(model.ready);
    previousMarkers = markerKeys;
    renderer.shadowMap.needsUpdate = true;
    fit();
    if (fresh.length && !reducedQuery.matches) {
      drops = fresh.map((marker) => ({ marker, start: clock() }));
      for (const d of drops) d.marker.group.position.y = d.marker.restY + 1.5;
      loop.start("drops", { ambient: false });
    }
    startIntro();
    startTag();
    syncBeacons();
  }

  // The labels whose decisions went up since the last build pop once (the badge's A3).
  function poppedOf(labels) {
    const popped = new Set();
    for (const label of labels) {
      if (previousDecisions.has(label.id) && label.decisions > previousDecisions.get(label.id)) popped.add(label.id);
    }
    previousDecisions = new Map(labels.map((l) => [l.id, l.decisions]));
    return reducedQuery.matches ? new Set() : popped;
  }

  // The same scene, other words (a meter moved, a title changed on a poll): the labels and tooltips are made again and nothing
  // else is touched, so no motion restarts, no shadow is drawn again and the camera stays where it is.
  function relabel() {
    relabels += 1;
    const words = content.text(model);
    for (const hit of content.hits) if (words.tips.has(hit.id)) hit.tip = words.tips.get(hit.id);
    content.labels = words.labels;
    const popped = poppedOf(words.labels);
    for (const entry of labelEntries) entry.node.remove();
    labelEntries = mountLabels(overlay, words.labels.map((l) => ({ ...l, anchor: l.anchor })), { popped });
    markLabels();
    positionLabels();
    const hit = hoverId ? content.hits.find((x) => x.id === hoverId) : null;
    if (hit && !tooltip.hidden) tooltip.textContent = hit.tip;
  }

  // The outline lines of the lot, the floor or the room are drawn only for the object that is hovered or selected by the route.
  // A building's card is drawn with the theme border while the person has that project: hovered (on the scene or in the list) or
  // chosen by the route. The tracking bar's default project does not count.
  function markLabels() {
    for (const entry of labelEntries) {
      if (entry.spec.kind === "card") entry.node.classList.toggle("is-selected", Boolean(entry.spec.selected) || entry.spec.id === hoverId);
    }
  }

  function applyOutlines() {
    if (content) applyOutlineVisibility(content.outlines, content.selected);
  }

  // A5: a building opens (its floors separate) and a room is entered (the camera moves in), once; a cut under reduced motion.
  function startIntro() {
    if (!content.intro || !model.ready || introPlayed) return;
    introPlayed = true;
    if (reducedQuery.matches) return;
    if (content.intro.apply) {
      content.intro.apply(0);
      intro = { approach: createApproach(EXPLODE_RATE), last: clock() };
      loop.start("intro", { ambient: false });
    } else if (content.intro.zoom && frustum) {
      const k = content.intro.zoom;
      const cx = (frustum.left + frustum.right) / 2;
      const cy = (frustum.top + frustum.bottom) / 2;
      const hw = ((frustum.right - frustum.left) / 2) * k;
      const hh = ((frustum.top - frustum.bottom) / 2) * k;
      const from = { left: cx - hw, right: cx + hw, top: cy + hh, bottom: cy - hh };
      applyFrustum(from);
      tween.start(from, { ...frustum }, clock());
      loop.start("camera", { ambient: false });
    }
  }

  // A6: the work-order tag moves from its old floor to its new one, once.
  function startTag() {
    const tag = content.tag;
    const before = previousTag;
    previousTag = tag ? { y: tag.y } : null;
    if (!tag || !before || before.y === tag.y || reducedQuery.matches || !model.ready || intro) return;
    tag.group.position.y = before.y;
    tagRun = { group: tag.group, from: before.y, to: tag.y, start: clock() };
    loop.start("tag", { ambient: false });
  }

  function syncBeacons() {
    if (!content || (!content.beacons.length && !content.motions.length)) {
      loop.stop("beacon");
      return;
    }
    if (reducedQuery.matches) {
      loop.stop("beacon");
      content.beacons.forEach(restBeacon);
      content.motions.forEach((m) => m.rest());
      loop.requestRender();
    } else {
      loop.start("beacon", { ambient: true });
    }
  }

  // --- layout and camera --------------------------------------------------------------------------------------------------
  function applyFrustum(f) {
    camera.left = f.left;
    camera.right = f.right;
    camera.top = f.top;
    camera.bottom = f.bottom;
    camera.updateProjectionMatrix();
  }

  function fit() {
    if (!content || !size.w || !size.h) return;
    const insets = options.getInsets ? options.getInsets() : {};
    lastInsets = insets;
    tools.style.setProperty("--wb-y", `${Math.max(16, insets.bottom || 0)}px`);   // above the tracking bar, whatever its height
    bounds = contentBounds(THREE, camera, content.group);
    frustum = fitFrustum(bounds, size, fitInsets(insets, corner ? corner.offsetHeight : 0), insets.pad || 1.04);   // below the corner card, when there is one
    view = clampView(view, frustum, bounds);   // the person's zoom and pan stay while they are inside the limits
    if (!tween.active()) applyView();
    positionLabels();
    loop.requestRender();
  }

  function applyView() {
    if (frustum) applyFrustum(frustumOf(frustum, view));
  }

  // The camera on the person's command (wheel, pinch, drag, keys, buttons): one frame on demand per change, never a loop.
  function setView(next) {
    view = next;
    applyView();
    positionLabels();
    loop.requestRender();
    pointerControl.again();   // the scene moved under a still mouse
  }
  const canMove = () => Boolean(content && frustum && bounds && !tween.active());
  const ndcOf = (clientX, clientY) => pointerToNdc(clientX, clientY, canvas.getBoundingClientRect());
  function zoomBy(factor, ndc = { x: 0, y: 0 }) {
    if (canMove()) setView(zoomAt(view, frustum, bounds, factor, ndc));
  }
  function moveBy(fx, fy) {
    if (canMove()) setView(panBy(view, frustum, bounds, fx, fy));
  }
  function resetView() {
    if (!frustum) return;
    setView(fitView());
  }

  function project(anchor) {
    const v = anchor.clone().project(camera);
    return { x: ((v.x + 1) / 2) * size.w, y: ((1 - v.y) / 2) * size.h };
  }

  function positionLabels() {
    placeCorner();
    if (!labelEntries.length) return;
    placeLabels(labelEntries, project, { hidden: false, insets: lastInsets, size });
  }

  // The corner slot: one card the page puts at the top right of the free rectangle (the Building's floor card).
  let corner = null;
  function placeCorner() {
    if (!corner || !lastInsets) return;
    const at = cornerPosition(size, lastInsets);
    corner.style.setProperty("--wb-x", `${at.x.toFixed(1)}px`);
    corner.style.setProperty("--wb-y", `${at.y.toFixed(1)}px`);
  }

  function measure() {
    const w = host.clientWidth;
    const hh = host.clientHeight;
    if (!w || !hh) return false;
    size = { w, h: hh };
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(w, hh, false);
    return true;
  }

  const observer = new ResizeObserver(() => {
    if (disposed || !measure()) return;
    fit();
  });
  observer.observe(host);

  // --- drawing ------------------------------------------------------------------------------------------------------------
  function draw(ts) {
    if (disposed || lostText) return;
    const now = clock();
    const moved = tween.step(now);
    if (moved) {
      applyFrustum(moved);
      positionLabels();   // the labels ride along with the camera (the prototype projected them every frame)
      if (!tween.active()) loop.stop("camera");
    }
    if (intro) {
      const p = intro.approach.step(frameSeconds(now, intro.last));
      intro.last = now;
      content.intro.apply(smooth(p));
      renderer.shadowMap.needsUpdate = true;
      refreshOutline();   // the outline is in world space: it follows the floors while they separate
      positionLabels();   // the plates ride along with their floors
      if (intro.approach.done()) {
        intro = null;
        loop.stop("intro");
      }
    }
    if (tagRun) {
      const t = Math.min(1, (now - tagRun.start) / TAG_MS);
      tagRun.group.position.y = tagRun.from + (tagRun.to - tagRun.from) * ease(t);
      renderer.shadowMap.needsUpdate = true;
      if (t >= 1) {
        tagRun = null;
        loop.stop("tag");
      }
    }
    if (drops.length) {
      renderer.shadowMap.needsUpdate = true;
      for (const d of drops) {
        const t = Math.min(1, (now - d.start) / DROP_MS);
        d.marker.group.position.y = d.marker.restY + 1.5 * Math.pow(1 - t, 3);
      }
      if (now - drops[0].start >= DROP_MS) {
        drops = [];
        loop.stop("drops");
      }
    }
    if (content && (content.beacons.length || content.motions.length) && !reducedQuery.matches) {
      const seconds = (now - epoch) / 1000;
      content.beacons.forEach((b) => pulseBeacon(b, seconds));
      content.motions.forEach((m) => m.tick(seconds));
      if (hoveredHit() && hoveredHit().moves) refreshOutline();   // a hovered figure or desk that is working moves: its outline moves with it
    }
    const started = clock();
    renderer.render(scene, camera);
    frameMs = clock() - started;
  }

  // --- picking, hover, tooltip ---------------------------------------------------------------------------------------------
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  // The pick (pick.js): the mesh under the pointer among the meshes of the pickable objects, never a line. The list is made again
  // when the content is built or an object moved, not on every pointer move.
  let pickCache = null;
  function pick(event) {
    if (!content) return { x: 0, y: 0, hit: null };
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const ndc = pointerToNdc(event.clientX, event.clientY, rect);
    pointer.set(ndc.x, ndc.y);
    if (!pickCache || pickCache.content !== content || intro || tagRun || drops.length) pickCache = { content, list: pickList(content.hits) };
    return { x, y, hit: pickHit(raycaster, camera, content.hits, pointer, pickCache.list) };
  }

  // The outline of the hovered object (outline.js): the edges of its own meshes, OUTLINE_PAD off the surface; its pad is the hit's own
  // when it has one. It is made in world space, so it is made again while the object moves (the building opening).
  function setOutline(id) {
    if (outline) {
      scene.remove(outline);
      outline.geometry.dispose();
      outline = null;
    }
    const hit = id && content ? content.hits.find((x) => x.id === id) : null;
    applyOutlines();
    markLabels();
    if (hit) {
      outline = new THREE.LineSegments(outlineGeometry(THREE, hit.object, hit.pad !== undefined ? hit.pad : OUTLINE_PAD), outlineMaterial);
      scene.add(outline);
    }
    loop.requestRender();
  }

  const hoveredHit = () => (hoverId && content ? content.hits.find((x) => x.id === hoverId) || null : null);

  // The same outline made again from where the object is now (the opening moves a floor, typing moves a figure's arms): one geometry
  // swapped in place, nothing else touched.
  function refreshOutline() {
    const hit = hoveredHit();
    if (!hit || !outline) return;
    outline.geometry.dispose();
    outline.geometry = outlineGeometry(THREE, hit.object, hit.pad !== undefined ? hit.pad : OUTLINE_PAD);
  }

  // What the page's checks read: the object the outline is drawn for and where its box is on the screen (CSS pixels of the canvas),
  // so a test can put the pointer at an object's drawn centre and compare the tooltip, the pick and the outline.
  function outlineProbe() {
    if (!outline || !outline.geometry) return null;
    outline.geometry.computeBoundingBox();
    const box = outline.geometry.boundingBox.clone().applyMatrix4(outline.matrixWorld);
    const at = project(box.getCenter(new THREE.Vector3()));
    return { id: hoverId, x: Math.round(at.x * 10) / 10, y: Math.round(at.y * 10) / 10 };
  }

  function showHover(result) {
    const id = result.hit ? result.hit.id : null;
    if (id !== hoverId) {
      hoverId = id;
      setOutline(id);
      if (options.onHover) options.onHover(id);
    }
    canvas.classList.toggle("is-pointer", Boolean(id));
    if (result.hit) {
      tooltip.textContent = result.hit.tip;
      tooltip.hidden = false;
      tooltip.style.setProperty("--wb-x", `${Math.min(size.w - 20, result.x + 14).toFixed(1)}px`);
      tooltip.style.setProperty("--wb-y", `${(result.y + 16).toFixed(1)}px`);
    } else {
      tooltip.hidden = true;
    }
  }

  // The pointer and the keys (pointer.js): a pan, a click, a pinch, the wheel, the keys; the hover pick is never stale.
  const pointerControl = createPointer({
    clock, setTimer: (fn, ms) => setTimeout(fn, ms), clearTimer: (id) => clearTimeout(id),
    pick, showHover, open: (id) => { if (options.onOpen) options.onOpen(id); }, canMove,
    pan: (dx, dy) => setView(panPixels(view, frustum, bounds, dx, dy, size)),
    zoomBy: (factor, x, y) => zoomBy(factor, x === null || x === undefined ? { x: 0, y: 0 } : ndcOf(x, y)),
    moveBy, resetView,
    dragging: (on) => {
      if (on) tooltip.hidden = true;
      canvas.classList.toggle("is-dragging", on);
    },
    capture: (id, on) => {
      const call = on ? canvas.setPointerCapture : canvas.releasePointerCapture;
      if (!call) return;
      try { call.call(canvas, id); } catch (e) { /* a pointer that is already gone */ }
    },
    hovering: () => hoverId !== null, disposed: () => disposed,
  });
  const onDown = (event) => pointerControl.down(event);
  const onMove = (event) => pointerControl.move(event);
  const onUp = (event) => pointerControl.up(event);
  const onLeave = () => pointerControl.leave();
  const onClick = (event) => pointerControl.click(event);
  const onDoubleClick = (event) => pointerControl.doubleClick(event);
  const onWheel = (event) => pointerControl.wheel(event);
  const onKeyDown = (event) => pointerControl.key(event);
  canvas.addEventListener("pointerdown", onDown);
  canvas.addEventListener("pointermove", onMove);
  canvas.addEventListener("pointerup", onUp);
  canvas.addEventListener("pointercancel", onUp);
  canvas.addEventListener("pointerleave", onLeave);
  canvas.addEventListener("click", onClick);
  canvas.addEventListener("dblclick", onDoubleClick);
  canvas.addEventListener("wheel", onWheel, { passive: false });
  canvas.addEventListener("keydown", onKeyDown);
  const onZoomIn = () => zoomBy(1.25);
  const onZoomOut = () => zoomBy(1 / 1.25);
  zoomInButton.addEventListener("click", onZoomIn);
  zoomOutButton.addEventListener("click", onZoomOut);
  fitButton.addEventListener("click", resetView);

  // --- the page's own signals: visibility, reduced motion, colour scheme, context loss ---------------------------------------
  const onVisibility = () => {
    loop.setHidden(document.hidden);
    if (!document.hidden && options.onVisible) options.onVisible();
  };
  const onReduced = () => {
    if (reducedQuery.matches) {
      if (tween.cancel()) {
        applyView();
        loop.stop("camera");
      }
      drops.forEach((d) => { d.marker.group.position.y = d.marker.restY; });
      drops = [];
      loop.stop("drops");
      if (intro) {
        content.intro.apply(1);
        intro = null;
        loop.stop("intro");
        positionLabels();
      }
      if (tagRun) {
        tagRun.group.position.y = tagRun.to;
        tagRun = null;
        loop.stop("tag");
      }
    }
    syncBeacons();
  };
  const onScheme = () => {
    buildWorld();
    build();
  };
  const onLost = (event) => {
    event.preventDefault();
    lostText = true;
    loop.stop("beacon");
    if (options.onUnavailable) options.onUnavailable();
  };
  const onRestored = () => {
    lostText = false;
    buildWorld();
    build();
    if (options.onRestored) options.onRestored();
  };
  document.addEventListener("visibilitychange", onVisibility);
  reducedQuery.addEventListener("change", onReduced);
  darkQuery.addEventListener("change", onScheme);
  canvas.addEventListener("webglcontextlost", onLost);
  canvas.addEventListener("webglcontextrestored", onRestored);

  buildWorld();
  measure();
  // The test hook of the acceptance (scene.md section 10): the frames drawn so far, read from the canvas element.
  const stats = () => ({ ...loop.stats(), hover: hoverId, outline: outlineProbe(), view: { left: camera.left, right: camera.right, top: camera.top, bottom: camera.bottom }, builds, relabels, zoom: view.zoom, panX: view.x, panY: view.y, frameMs, pixelRatio: renderer.getPixelRatio(), drawCalls: renderer.info.render.calls, geometries: renderer.info.memory.geometries });
  canvas.wbStats = stats;
  canvas.wbSamples = () => (content ? visibleSamples(THREE, camera, scene, content.hits, size) : []);

  return {
    canvas,
    /**
     * Show a scene: `kind` names a builder, `model` is its plain data. The same model is not built twice, and a model that
     * differs only in its words (the builder's `structure` is the same) changes the labels and tooltips alone: nothing that moves
     * is built again, so no motion restarts on a poll that found the same state.
     */
    show(nextKind, nextModel, label) {
      if (label) canvas.setAttribute("aria-label", label);
      const builder = BUILDERS[nextKind];
      const plan = showPlan({ signature, structure: structureSignature, built: Boolean(content && content.text) }, nextKind, nextModel, builder && builder.structure);
      if (plan.action === "none") return false;
      kind = nextKind;
      model = nextModel;
      signature = plan.signature;
      if (plan.action === "relabel") {
        relabel();
        return true;
      }
      structureSignature = plan.structure;
      build();
      return true;
    },
    /** Measure the insets again and refit (a panel changed size). */
    refit() {
      if (!disposed && measure()) fit();
    },
    /** Outline a building from the HTML list (hover or focus there), with no tooltip. */
    highlight(id) {
      if (id !== hoverId) {
        hoverId = id;
        setOutline(id);
      }
    },
    /** Move the camera in on a building (A5, the prototype's curve); resolves true when it is nine tenths done, false when it was a cut. */
    flyTo(id) {
      const hit = content && content.hits.find((x) => x.id === id);
      if (!hit || reducedQuery.matches || !frustum) return Promise.resolve(false);
      const insets = options.getInsets ? options.getInsets() : {};
      const target = fitFrustum(contentBounds(THREE, camera, hit.object), size, insets, 1.6);
      const move = tween.start(frustumOf(frustum, view), target, clock(), FLY_SETTLE_AT);
      tooltip.hidden = true;
      positionLabels();
      loop.start("camera", { ambient: false });
      return move;
    },
    /** Put `node` (or nothing) in the corner slot: the top right of the free rectangle, over the scene, never over a panel. */
    setCorner(node) {
      if (corner) corner.remove();
      corner = node || null;
      if (corner) {
        corner.classList.add("wb-corner-card");
        overlay.append(corner);
        placeCorner();
      }
      fit();   // the scene is fitted below the card: its height is measured now
    },
    /** The person's camera, for the page's checks and the keyboard-free callers: zoom in, zoom out, fit, move. */
    zoomBy: (factor) => zoomBy(factor),
    resetView,
    moveBy,
    /** What the page can read to check the rules: frames drawn so far, animations running, hidden or not, the zoom and pan. */
    stats,
    dispose() {
      if (disposed) return;
      disposed = true;
      pointerControl.dispose();
      observer.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      reducedQuery.removeEventListener("change", onReduced);
      darkQuery.removeEventListener("change", onScheme);
      canvas.removeEventListener("pointerdown", onDown);
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerup", onUp);
      canvas.removeEventListener("pointercancel", onUp);
      canvas.removeEventListener("pointerleave", onLeave);
      canvas.removeEventListener("click", onClick);
      canvas.removeEventListener("dblclick", onDoubleClick);
      canvas.removeEventListener("wheel", onWheel);
      canvas.removeEventListener("keydown", onKeyDown);
      zoomInButton.removeEventListener("click", onZoomIn);
      zoomOutButton.removeEventListener("click", onZoomOut);
      fitButton.removeEventListener("click", resetView);
      canvas.removeEventListener("webglcontextlost", onLost);
      canvas.removeEventListener("webglcontextrestored", onRestored);
      loop.dispose();
      clearContent();
      if (worldKit) worldKit.dispose();
      outlineMaterial.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      canvas.remove();
      overlay.remove();
      tools.remove();
      corner = null;
    },
  };
}
