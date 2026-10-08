// The scene engine: one WebGL renderer for the page, an isometric orthographic camera, the palette read from the page's
// tokens, picking, HTML labels and the render scheduler. It draws a scene only when something changed (loop.js), at most
// 30 frames a second while an ambient animation runs, never while the tab is hidden, at a pixel ratio of at most 2, and
// with no ambient animation under reduced motion. Without WebGL it throws NoWebGL and the screen shows its HTML alone.
//
// What it draws is built by a scene builder (city.js now; the building, floor, lobby and control room scenes come with
// their packages through the same `show(kind, model)`).

import * as THREE from "../three.js";
import { h } from "../dom.js";
import { buildBuilding } from "./building.js";
import { buildCity, pulseBeacon, restBeacon } from "./city.js";
import { fitFrustum } from "./fit.js";
import { createKit } from "./kit.js";
import { mountLabels, placeLabels } from "./labels.js";
import { createLoop } from "./loop.js";
import { LIGHT_WHITE, readPalette } from "./palette.js";
import { buildRoom } from "./room.js";
import { createTween } from "./tween.js";

export const BUILDERS = { city: buildCity, building: buildBuilding, room: buildRoom };
const DISTANCE = 150;
const AZIMUTH = (45 * Math.PI) / 180;
const ELEVATION = (35 * Math.PI) / 180;
export const CAMERA_MS = 600;     // A5: the camera moves in over 600 ms
export const DROP_MS = 300;       // A3: a waiting marker drops in once
export const TAG_MS = 600;        // A6: the work-order tag moves to the next floor once

const PICK_EVERY_MS = 40;

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
  const canvas = h("canvas", { class: "wb-canvas", role: "img", "aria-label": options.label || "Scene" });
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
  host.append(canvas, overlay);

  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;   // the library's soft filter: the PCFSoft name was folded into it, and `shadow.radius` softens it
  renderer.shadowMap.autoUpdate = false;   // the sun does not move: shadows are drawn again only when the geometry changes
  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 500);
  camera.position.set(DISTANCE * Math.cos(ELEVATION) * Math.sin(AZIMUTH), DISTANCE * Math.sin(ELEVATION), DISTANCE * Math.cos(ELEVATION) * Math.cos(AZIMUTH));
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld();

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
  let frustum = null;             // the resting frustum (fitted)
  const tween = createTween();    // the camera move in flight, if any
  let drops = [];                 // {marker, start}
  let intro = null;               // {start, ms}: the building opening (A5), the floors separating
  let introPlayed = false;
  let tagRun = null;              // {group, from, to, start}: the work-order tag moving (A6)
  let previousTag = null;         // {y}: where the tag was on the build before
  let lastInsets = null;
  let previousMarkers = new Set();
  let previousReady = false;      // the build before this one held real data: a marker not in it has arrived
  let previousDecisions = new Map();
  let outline = null;
  let hoverId = null;
  let stickyId = null;
  let lostText = false;
  let disposed = false;
  let lastPick = 0;
  let pulseStart = 0;
  let frameMs = 0;                // the browser-side cost of the last frame (submitting the draw calls)
  const outlineMaterial = new THREE.LineBasicMaterial({ color: 0xffffff, depthTest: false, transparent: true });

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
    clearContent();
    if (!model || !BUILDERS[kind]) return;
    contentKit = createKit(palette);
    content = BUILDERS[kind](contentKit, model);
    content.beacons = content.beacons || [];
    content.motions = content.motions || [];
    content.markers = content.markers || [];
    scene.add(content.group);
    const popped = new Set();
    for (const label of content.labels) {
      if (previousDecisions.has(label.id) && label.decisions > previousDecisions.get(label.id)) popped.add(label.id);
    }
    previousDecisions = new Map(content.labels.map((l) => [l.id, l.decisions]));
    labelEntries = mountLabels(overlay, content.labels.map((l) => ({ ...l, anchor: l.anchor })), { popped: reducedQuery.matches ? new Set() : popped });
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

  // A5: a building opens (its floors separate) and a room is entered (the camera moves in), once, 600 ms; a cut under reduced motion.
  function startIntro() {
    if (!content.intro || !model.ready || introPlayed) return;
    introPlayed = true;
    if (reducedQuery.matches) return;
    if (content.intro.apply) {
      content.intro.apply(0);
      intro = { start: clock(), ms: CAMERA_MS };
      loop.start("intro", { ambient: false });
    } else if (content.intro.zoom && frustum) {
      const k = content.intro.zoom;
      const cx = (frustum.left + frustum.right) / 2;
      const cy = (frustum.top + frustum.bottom) / 2;
      const hw = ((frustum.right - frustum.left) / 2) * k;
      const hh = ((frustum.top - frustum.bottom) / 2) * k;
      const from = { left: cx - hw, right: cx + hw, top: cy + hh, bottom: cy - hh };
      applyFrustum(from);
      tween.start(from, { ...frustum }, clock(), CAMERA_MS);
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
    } else if (loop.start("beacon", { ambient: true })) {
      pulseStart = clock();
    }
  }

  // --- layout and camera --------------------------------------------------------------------------------------------------
  function contentBounds(object) {
    const box = new THREE.Box3().setFromObject(object);
    camera.updateMatrixWorld();
    const inverse = camera.matrixWorldInverse;
    const xs = [];
    const ys = [];
    for (const x of [box.min.x, box.max.x]) for (const y of [box.min.y, box.max.y]) for (const z of [box.min.z, box.max.z]) {
      const p = new THREE.Vector3(x, y, z).applyMatrix4(inverse);
      xs.push(p.x);
      ys.push(p.y);
    }
    return { x0: Math.min(...xs), x1: Math.max(...xs), y0: Math.min(...ys), y1: Math.max(...ys) };
  }

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
    frustum = fitFrustum(contentBounds(content.group), size, insets, insets.pad || 1.04);
    if (!tween.active()) applyFrustum(frustum);
    positionLabels();
    loop.requestRender();
  }

  function project(anchor) {
    const v = anchor.clone().project(camera);
    return { x: ((v.x + 1) / 2) * size.w, y: ((1 - v.y) / 2) * size.h };
  }

  function positionLabels() {
    if (!labelEntries.length) return;
    placeLabels(labelEntries, project, { hidden: tween.active() || Boolean(intro), insets: lastInsets, size });
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
      positionLabels();
      if (!tween.active()) {
        loop.stop("camera");
        positionLabels();
      }
    }
    if (intro) {
      const t = Math.min(1, (now - intro.start) / intro.ms);
      content.intro.apply(ease(t));
      renderer.shadowMap.needsUpdate = true;
      if (t >= 1) {
        intro = null;
        loop.stop("intro");
        positionLabels();
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
      const seconds = (now - pulseStart) / 1000;
      content.beacons.forEach((b) => pulseBeacon(b, seconds));
      content.motions.forEach((m) => m.tick(seconds));
    }
    const started = clock();
    renderer.render(scene, camera);
    frameMs = clock() - started;
  }

  // --- picking, hover, tooltip ---------------------------------------------------------------------------------------------
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  function pick(event) {
    if (!content) return { x: 0, y: 0, hit: null };
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    pointer.set((x / rect.width) * 2 - 1, -(y / rect.height) * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const objects = content.hits.map((hit) => hit.object);
    const found = raycaster.intersectObjects(objects, true);
    if (!found.length) return { x, y, hit: null };
    let object = found[0].object;
    while (object && !objects.includes(object)) object = object.parent;
    return { x, y, hit: content.hits.find((hit) => hit.object === object) || null };
  }

  function setOutline(id) {
    if (outline) {
      scene.remove(outline);
      outline.geometry.dispose();
      outline = null;
    }
    const hit = id && content ? content.hits.find((x) => x.id === id) : null;
    if (hit) {
      const box = new THREE.Box3().setFromObject(hit.object).expandByScalar(0.08);
      const dims = box.getSize(new THREE.Vector3());
      const centre = box.getCenter(new THREE.Vector3());
      const boxGeometry = new THREE.BoxGeometry(dims.x, dims.y, dims.z);
      outline = new THREE.LineSegments(new THREE.EdgesGeometry(boxGeometry), outlineMaterial);
      boxGeometry.dispose();
      outline.position.copy(centre);
      outline.renderOrder = 10;
      scene.add(outline);
    }
    loop.requestRender();
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

  const onMove = (event) => {
    if (event.pointerType === "touch" || stickyId) return;
    const now = clock();
    if (now - lastPick < PICK_EVERY_MS) return;
    lastPick = now;
    showHover(pick(event));
  };
  const onLeave = () => {
    if (!stickyId) showHover({ hit: null });
  };
  const onClick = (event) => {
    const result = pick(event);
    if (!result.hit) {
      stickyId = null;
      showHover(result);
      return;
    }
    if (event.pointerType === "touch" && stickyId !== result.hit.id) {
      stickyId = result.hit.id;
      showHover(result);
      return;
    }
    stickyId = null;
    showHover({ hit: null });
    if (options.onOpen) options.onOpen(result.hit.id);
  };
  canvas.addEventListener("pointermove", onMove);
  canvas.addEventListener("pointerleave", onLeave);
  canvas.addEventListener("click", onClick);

  // --- the page's own signals: visibility, reduced motion, colour scheme, context loss ---------------------------------------
  const onVisibility = () => {
    loop.setHidden(document.hidden);
    if (!document.hidden && options.onVisible) options.onVisible();
  };
  const onReduced = () => {
    if (reducedQuery.matches) {
      if (tween.cancel()) {
        applyFrustum(frustum);
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
  const stats = () => ({ ...loop.stats(), frameMs, pixelRatio: renderer.getPixelRatio(), drawCalls: renderer.info.render.calls, geometries: renderer.info.memory.geometries });
  canvas.wbStats = stats;

  return {
    canvas,
    /** Show a scene: `kind` names a builder, `model` is its plain data. The same model is not built twice. */
    show(nextKind, nextModel, label) {
      if (label) canvas.setAttribute("aria-label", label);
      const next = JSON.stringify([nextKind, nextModel]);
      if (next === signature) return false;
      kind = nextKind;
      model = nextModel;
      build();
      signature = next;
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
    /** Move the camera in on a building over CAMERA_MS (A5); resolves true when it ended, false when it was a cut. */
    flyTo(id, ms = CAMERA_MS) {
      const hit = content && content.hits.find((x) => x.id === id);
      if (!hit || reducedQuery.matches || !frustum) return Promise.resolve(false);
      const insets = options.getInsets ? options.getInsets() : {};
      const target = fitFrustum(contentBounds(hit.object), size, insets, 1.6);
      const move = tween.start({ ...frustum }, target, clock(), ms);
      tooltip.hidden = true;
      positionLabels();
      loop.start("camera", { ambient: false });
      return move;
    },
    /** What the page can read to check the rules: frames drawn so far, animations running, hidden or not. */
    stats,
    dispose() {
      if (disposed) return;
      disposed = true;
      observer.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      reducedQuery.removeEventListener("change", onReduced);
      darkQuery.removeEventListener("change", onScheme);
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerleave", onLeave);
      canvas.removeEventListener("click", onClick);
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
    },
  };
}
