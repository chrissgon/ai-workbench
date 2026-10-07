// The 3D world: an orthographic isometric scene built from boxes and cylinders, flat colours, one soft light.
// Nothing here knows about panels; main.js tells the world which view to show and listens to picks.
import * as THREE from 'three';

export const W = 4.4, D = 3.2;          // a building's footprint
export const H0 = 1.3, H1 = 2.9;        // floor pitch: closed building, opened (exploded) building
const WALL_T = 0.12;
export const CITY_X = { "northwind-shop": -6.5, "tinykv-docs": 6.5 };
export const CITY_Z = -2;
export const CONTROL_POS = new THREE.Vector3(60, 0, 0);

const C = {
  bg: 0xf1f4f8, ground: 0xf7f8fb, pad: 0xffffff, road: 0xdfe3ea, line: 0xffffff,
  wall: 0xfdfdfe, wallBack: 0xf3f5f8, slab: 0xe9edf2, slabOff: 0xc9cfd8, accent: 0x2d6cff, accentSoft: 0x8fb2ff,
  dark: 0x2f3744, grey: 0x9aa5b5, amber: 0xf5a524, green: 0x22b573, red: 0xe5484d,
  tree: 0xb4dcbc, tree2: 0x9fd0a9, trunk: 0xcdbfae, desk: 0xffffff, deskTop: 0xdde3ec, wood: 0xe7d9c6,
};
const lerp = (a, b, t) => a + (b - a) * t;
const clamp01 = (x) => Math.max(0, Math.min(1, x));
const smooth = (t) => t * t * (3 - 2 * t);

const matCache = new Map();
function mat(color) {
  if (!matCache.has(color)) matCache.set(color, new THREE.MeshLambertMaterial({ color }));
  return matCache.get(color);
}
function box(w, h, d, color, x, y, z, parent, shadow = true) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), typeof color === "number" ? mat(color) : color);
  m.position.set(x, y, z);
  m.castShadow = shadow; m.receiveShadow = true;
  if (parent) parent.add(m);
  return m;
}
function cyl(rt, rb, h, color, x, y, z, parent, seg = 14) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), typeof color === "number" ? mat(color) : color);
  m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true;
  if (parent) parent.add(m);
  return m;
}
// a box whose pivot is at its bottom, so scale.y sets its height
function wallBox(w, d, color, x, z, parent) {
  const geo = new THREE.BoxGeometry(w, 1, d); geo.translate(0, 0.5, 0);
  const m = new THREE.Mesh(geo, typeof color === "number" ? mat(color) : color);
  m.position.set(x, 0, z); m.castShadow = true; m.receiveShadow = true;
  parent.add(m); return m;
}

// ---------------------------------------------------------------- figure (the agent)
function makeFigure() {
  const g = new THREE.Group();
  const bodyMat = new THREE.MeshLambertMaterial({ color: C.grey });
  const body = box(0.42, 0.5, 0.28, bodyMat, 0, 0.72, 0, g);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.19, 16, 12), mat(0xf6f7fa));
  head.position.set(0, 1.2, 0); head.castShadow = true; g.add(head);
  box(0.26, 0.08, 0.05, C.dark, 0, 1.22, -0.17, g);
  box(0.34, 0.12, 0.4, C.dark, 0, 0.42, -0.1, g);
  const arm = (sx) => {
    const p = new THREE.Group(); p.position.set(sx * 0.27, 0.92, 0);
    box(0.1, 0.42, 0.1, bodyMat, 0, -0.21, 0, p); g.add(p); return p;
  };
  const armL = arm(-1), armR = arm(1);
  const bang = new THREE.Group();
  box(0.1, 0.26, 0.1, new THREE.MeshBasicMaterial({ color: C.amber }), 0, 0.14, 0, bang, false);
  const dot = new THREE.Mesh(new THREE.SphereGeometry(0.07, 10, 8), new THREE.MeshBasicMaterial({ color: C.amber }));
  dot.position.set(0, -0.06, 0); bang.add(dot);
  bang.position.set(0, 1.75, 0); bang.visible = false; g.add(bang);
  return { g, bodyMat, armL, armR, head, bang };
}

function makeChair(parent, x, z) {
  box(0.5, 0.06, 0.5, C.dark, x, 0.36, z, parent);
  box(0.5, 0.5, 0.06, C.dark, x, 0.64, z + 0.24, parent);
  cyl(0.04, 0.04, 0.34, C.grey, x, 0.18, z, parent, 8);
  cyl(0.22, 0.22, 0.03, C.grey, x, 0.02, z, parent, 14);
}

function makeDesk(parent, x, z, len, deep) {
  box(len, 0.07, deep, C.deskTop, x, 0.72, z, parent);
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) box(0.06, 0.7, 0.06, C.grey, x + sx * (len / 2 - 0.08), 0.35, z + sz * (deep / 2 - 0.08), parent);
}

// ---------------------------------------------------------------- one floor: slab, walls, windows, furniture
function makeFloor(project, agent, index, mats, docsOf, pendingOf) {
  const fg = new THREE.Group();
  fg.userData.floor = { pid: project.id, agent: agent.id };
  const on = agent.enabled;
  const slab = box(W, 0.16, D, on ? C.slab : C.slabOff, 0, -0.08, 0, fg);
  box(W + 0.04, 0.05, D + 0.04, on ? C.accent : C.grey, 0, -0.11, 0, fg, false);
  const bx = wallBox(WALL_T, D, C.wallBack, -W / 2 + WALL_T / 2, 0, fg);
  const bz = wallBox(W, WALL_T, C.wallBack, 0, -D / 2 + WALL_T / 2, fg);
  // front walls and their windows fade out when the building opens
  const front = new THREE.Group(); fg.add(front);
  const fx = wallBox(WALL_T, D, mats.front, W / 2 - WALL_T / 2, 0, front);
  const fz = wallBox(W, WALL_T, mats.front, 0, D / 2 - WALL_T / 2, front);
  const winMat = agent.state === "working" ? mats.winWork : on ? mats.winIdle : mats.winOff;
  for (let k = 0; k < 3; k++) { const w = box(0.03, 0.5, 0.62, winMat, W / 2 + 0.01, 0.68, -0.95 + k * 0.95, front, false); w.castShadow = false; }
  for (let k = 0; k < 4; k++) { const w = box(0.7, 0.5, 0.03, winMat, -1.55 + k * 1.03, 0.68, D / 2 + 0.01, front, false); w.castShadow = false; }
  const inner = new THREE.Group(); fg.add(inner);
  const anim = { state: agent.state, on };

  // desk against the back wall, the agent behind it
  const dz = -1.1;
  makeDesk(inner, 0.7, dz, 1.8, 0.8);
  box(0.12, 0.05, 0.3, C.grey, 0.35, 0.78, dz, inner);
  const screenMat = new THREE.MeshLambertMaterial({ color: C.dark, emissive: 0x000000 });
  box(0.7, 0.42, 0.04, screenMat, 0.35, 1.02, dz - 0.05, inner);
  anim.screenMat = screenMat;
  makeChair(inner, 0.7, -0.45);
  if (on) {
    const fig = makeFigure();
    fig.g.position.set(0.7, 0, -0.45);
    fig.g.userData.item = { type: "agent" };
    inner.add(fig.g);
    Object.assign(anim, { fig });
    const col = agent.state === "working" ? C.accent : agent.state === "waiting" ? C.amber : C.grey;
    fig.bodyMat.color.setHex(col);
    anim.figureAnchor = new THREE.Vector3(0.7, 1.9, -0.45);
  }
  // sparks over the screen while working
  anim.sparks = [];
  if (on && agent.state === "working") {
    for (let k = 0; k < 6; k++) {
      const s = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.07, 0.07), new THREE.MeshBasicMaterial({ color: C.accent, transparent: true }));
      s.userData.phase = k / 6; inner.add(s); anim.sparks.push(s);
    }
  }
  // inbox tray on the desk
  const tray = new THREE.Group(); tray.position.set(1.38, 0.76, dz); inner.add(tray);
  box(0.4, 0.04, 0.32, C.grey, 0, 0, 0, tray);
  const n = pendingOf.length;
  for (let k = 0; k < Math.min(n, 5); k++) {
    const eff = pendingOf[k].kind === "effect";
    box(0.34, 0.035, 0.26, eff ? C.accent : 0xffffff, 0, 0.04 + k * 0.04, 0, tray);
  }
  const trayHit = box(0.44, 0.34, 0.36, mat(C.bg), 0, 0.12, 0, tray, false); trayHit.material = new THREE.MeshBasicMaterial({ visible: false });
  tray.userData.item = { type: "inbox", count: n };
  anim.tray = tray;

  // documents: a low table with sheets, a cabinet
  const table = new THREE.Group(); table.position.set(-0.9, 0, 0.85); inner.add(table);
  box(1.5, 0.06, 0.9, C.wood, 0, 0.5, 0, table);
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) box(0.06, 0.48, 0.06, C.grey, sx * 0.68, 0.24, sz * 0.38, table);
  const cols = [-0.48, 0, 0.48], rows = [-0.2, 0.22];
  docsOf.slice(0, 6).forEach((d, k) => {
    const sheet = new THREE.Group();
    sheet.position.set(cols[k % 3], 0.54, rows[Math.floor(k / 3)]);
    sheet.rotation.y = ((k * 37) % 7 - 3) * 0.05;
    box(0.36, 0.014, 0.46, 0xffffff, 0, 0, 0, sheet);
    box(0.26, 0.016, 0.03, C.accentSoft, 0, 0.002, -0.14, sheet, false);
    box(0.26, 0.016, 0.02, C.slab, 0, 0.002, -0.06, sheet, false);
    box(0.26, 0.016, 0.02, C.slab, 0, 0.002, 0.0, sheet, false);
    sheet.userData.item = { type: "doc", path: d.path, label: d.path };
    table.add(sheet);
  });
  const cab = new THREE.Group(); cab.position.set(-1.9, 0, -0.55); inner.add(cab);
  box(0.5, 0.95, 0.62, 0xeef1f6, 0, 0.475, 0, cab);
  for (let k = 0; k < 3; k++) { box(0.02, 0.2, 0.5, C.accentSoft, 0.26, 0.2 + k * 0.28, 0, cab, false); box(0.03, 0.03, 0.2, C.grey, 0.27, 0.2 + k * 0.28, 0, cab, false); }
  cab.userData.item = { type: "cabinet", label: "Documents" };
  // plant
  cyl(0.16, 0.12, 0.26, 0xffffff, 1.85, 0.13, 1.2, inner);
  const leaf = new THREE.Mesh(new THREE.IcosahedronGeometry(0.28, 0), mat(C.tree2)); leaf.position.set(1.85, 0.5, 1.2); leaf.castShadow = true; inner.add(leaf);

  // lights: a lamp on the back wall, lit only when the floor is on
  const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.05, 0.12), new THREE.MeshBasicMaterial({ color: on ? 0xfff6d6 : 0x9aa0aa }));
  lamp.position.set(0.2, 1.32, -D / 2 + 0.12); inner.add(lamp);

  if (agent.id === "planning") {
    const door = new THREE.Group(); door.position.set(-1.5, 0, -D / 2 + 0.12); inner.add(door);
    box(0.96, 1.34, 0.05, C.accent, 0, 0.67, 0, door);
    box(0.78, 1.2, 0.07, 0xdce8ff, 0, 0.62, 0.0, door, false);
    box(0.05, 0.05, 0.09, C.dark, 0.3, 0.62, 0, door, false);
    door.userData.item = { type: "door", label: "Control room" };
    anim.door = door;
  }
  return { group: fg, front, bx, bz, fx, fz, anim, slab, agent, inner };
}

// ---------------------------------------------------------------- building
function makeBuilding(project, docsByAgent, pendingByAgent) {
  const g = new THREE.Group();
  g.userData.building = project.id;
  const mats = {
    front: new THREE.MeshLambertMaterial({ color: C.wall, transparent: true }),
    winWork: new THREE.MeshBasicMaterial({ color: C.accent, transparent: true }),
    winIdle: new THREE.MeshBasicMaterial({ color: 0xd8e5fb, transparent: true }),
    winOff: new THREE.MeshBasicMaterial({ color: 0xd3d9e2, transparent: true }),
    roof: new THREE.MeshLambertMaterial({ color: C.accent, transparent: true }),
  };
  const floors = project.agents.map((a, i) => {
    const f = makeFloor(project, a, i, mats, docsByAgent[a.id] || [], pendingByAgent[a.id] || []);
    g.add(f.group); f.index = i; return f;
  });
  const roof = new THREE.Group(); g.add(roof);
  box(W + 0.2, 0.2, D + 0.2, mats.roof, 0, 0, 0, roof);
  box(1.0, 0.4, 0.8, 0xffffff, 1.2, 0.3, -0.6, roof);
  box(0.7, 0.3, 0.6, 0xe9edf2, -1.1, 0.25, 0.5, roof);
  const beacon = new THREE.Mesh(new THREE.TorusGeometry(1.6, 0.05, 6, 40), new THREE.MeshBasicMaterial({ color: C.accent, transparent: true, opacity: 0.6 }));
  beacon.rotation.x = Math.PI / 2; beacon.position.y = 0.25; beacon.visible = !!project.running_task_id; roof.add(beacon);
  // entrance awning
  const awn = box(1.5, 0.08, 0.5, C.accent, 0, 0.95, D / 2 + 0.25, g);
  const b = { id: project.id, group: g, floors, roof, mats, beacon, awn, explode: 0, explodeTarget: 0, project };
  g.position.set(CITY_X[project.id] ?? 0, 0, CITY_Z);
  applyExplode(b);
  return b;
}

function applyExplode(b) {
  const t = smooth(b.explode);
  const pitch = lerp(H0, H1, t), h = lerp(H0, 1.55, t);
  b.floors.forEach((f, i) => {
    f.group.position.y = i * pitch + 0.16;
    for (const w of [f.bx, f.bz, f.fx, f.fz]) w.scale.y = h;
    f.front.visible = t < 0.98;
  });
  const fade = 1 - clamp01(t / 0.55);
  b.mats.front.opacity = fade; b.mats.winWork.opacity = fade; b.mats.winIdle.opacity = fade; b.mats.winOff.opacity = fade;
  b.mats.roof.opacity = 1 - clamp01(t / 0.7);
  b.roof.position.y = b.floors.length * pitch + 0.16 + 0.1;
  b.roof.visible = t < 0.98;
  b.awn.visible = t < 0.5;
  b.awn.position.y = 0.95 * (pitch / H0) * 0.5 + 0.16;
}

// ---------------------------------------------------------------- city furniture
function makeTree(x, z, s = 1) {
  const g = new THREE.Group();
  cyl(0.09 * s, 0.11 * s, 0.5 * s, C.trunk, 0, 0.25 * s, 0, g, 6);
  const a = new THREE.Mesh(new THREE.IcosahedronGeometry(0.55 * s, 0), mat(C.tree)); a.position.y = 0.85 * s; a.castShadow = true; g.add(a);
  const b = new THREE.Mesh(new THREE.IcosahedronGeometry(0.38 * s, 0), mat(C.tree2)); b.position.set(0.25 * s, 1.15 * s, 0.1 * s); b.castShadow = true; g.add(b);
  g.position.set(x, 0.15, z); return g;
}
function makeCar(color) {
  const g = new THREE.Group();
  box(1.1, 0.28, 0.55, color, 0, 0.3, 0, g);
  box(0.55, 0.26, 0.5, 0xffffff, -0.1, 0.55, 0, g);
  box(0.5, 0.2, 0.52, 0xcfe0ff, -0.1, 0.55, 0, g, false);
  for (const sx of [-0.35, 0.35]) for (const sz of [-0.28, 0.28]) {
    const w = cyl(0.12, 0.12, 0.1, C.dark, sx, 0.14, sz, g, 10); w.rotation.x = Math.PI / 2;
  }
  return g;
}
function makeForklift() {
  const g = new THREE.Group();
  box(0.7, 0.35, 0.5, C.accent, 0, 0.35, 0, g);
  box(0.35, 0.3, 0.46, C.dark, -0.1, 0.65, 0, g);
  box(0.06, 0.8, 0.4, C.dark, 0.42, 0.55, 0, g);
  box(0.4, 0.05, 0.4, C.grey, 0.62, 0.2, 0, g);
  const cargo = box(0.34, 0.26, 0.34, 0xffffff, 0.62, 0.36, 0, g);
  for (const sx of [-0.2, 0.2]) for (const sz of [-0.27, 0.27]) { const w = cyl(0.1, 0.1, 0.08, C.dark, sx, 0.1, sz, g, 10); w.rotation.x = Math.PI / 2; }
  return { g, cargo };
}

function makeControlRoom() {
  const g = new THREE.Group(); g.position.copy(CONTROL_POS);
  box(11, 0.2, 8, C.pad, 0, -0.1, 0, g);
  box(11, 2.6, 0.2, C.wallBack, 0, 1.3, -4, g);
  box(0.2, 2.6, 8, C.wallBack, -5.5, 1.3, 0, g);
  const screen = box(5.2, 1.4, 0.1, C.dark, 0, 1.5, -3.85, g);
  const bars = [];
  for (let k = 0; k < 9; k++) { const bh = 0.3 + ((k * 53) % 9) / 12; const b = box(0.28, bh, 0.05, C.accent, -2 + k * 0.5, 1.05 + bh / 2 - 0.3, -3.78, g, false); b.userData.base = bh; bars.push(b); }
  const leds = [];
  for (let k = 0; k < 4; k++) {
    const rack = new THREE.Group(); rack.position.set(-3.5 + k * 1.2, 0, -2.2); g.add(rack);
    box(0.9, 2.0, 0.9, 0xeef1f6, 0, 1.0, 0, rack);
    for (let r = 0; r < 6; r++) {
      box(0.78, 0.16, 0.04, C.slab, 0, 0.3 + r * 0.28, 0.46, rack, false);
      const led = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.05, 0.03), new THREE.MeshBasicMaterial({ color: C.accent }));
      led.position.set(0.28, 0.3 + r * 0.28, 0.49); led.userData.phase = (k * 6 + r) * 0.7; rack.add(led); leds.push(led);
    }
  }
  box(3.4, 0.08, 1.2, C.deskTop, 1.5, 0.75, 1.0, g);
  for (const sx of [-1, 1]) box(0.08, 0.75, 1.0, C.grey, 1.5 + sx * 1.6, 0.37, 1.0, g);
  box(0.9, 0.5, 0.06, C.dark, 0.8, 1.15, 0.8, g); box(0.9, 0.5, 0.06, C.dark, 2.2, 1.15, 0.8, g);
  g.userData.leds = leds; g.userData.bars = bars;
  return g;
}

// ---------------------------------------------------------------- the world
export class World {
  constructor(canvas, data) {
    this.canvas = canvas; this.data = data;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(C.bg);
    this.camera = new THREE.OrthographicCamera(-10, 10, 10, -10, 1, 400);
    this.cam = { target: new THREE.Vector3(0, 2, 0), zoom: 0.8, offX: 0 };
    this.camGoal = { target: new THREE.Vector3(0, 2, 0), zoom: 0.8, offX: 0 };
    this.dir = new THREE.Vector3(1, 1, 1).normalize();
    this.raycaster = new THREE.Raycaster();
    this.view = { name: "city" };
    this.time = 0;
    this.buildLights();
    this.buildGround();
    this.buildBuildings();
    this.buildTraffic();
    this.control = makeControlRoom(); this.scene.add(this.control);
    this.hoverBox = new THREE.Box3Helper(new THREE.Box3(), C.accent); this.hoverBox.visible = false; this.scene.add(this.hoverBox);
    this.resize();
    this.snapCamera();
    this.last = performance.now();
    const loop = (now) => { const dt = Math.min(0.05, (now - this.last) / 1000); this.last = now; this.tick(dt); requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
    window.addEventListener("resize", () => this.resize());
  }

  buildLights() {
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0xdfe6f0, 1.55));
    const sun = new THREE.DirectionalLight(0xffffff, 1.5);
    sun.position.set(-8, 16, 9);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    const s = sun.shadow.camera; s.left = -22; s.right = 22; s.top = 22; s.bottom = -22; s.near = 1; s.far = 80;
    sun.shadow.radius = 5; sun.shadow.bias = -0.0006; sun.shadow.normalBias = 0.03;
    this.sun = sun; this.sunOffset = sun.position.clone();
    this.scene.add(sun); this.scene.add(sun.target);
  }

  buildGround() {
    const g = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.MeshLambertMaterial({ color: C.bg }));
    g.rotation.x = -Math.PI / 2; g.position.y = -0.02; g.receiveShadow = true; this.scene.add(g);
    const pad = box(30, 0.3, 20, C.pad, 0, -0.15 + 0.0, -0.5, this.scene); pad.castShadow = false;
    // roads
    const road1 = box(30, 0.04, 2.2, C.road, 0, 0.16, 6.3, this.scene, false);
    const road2 = box(1.8, 0.04, 14, C.road, 0, 0.16, -1.5, this.scene, false);
    for (let x = -14; x <= 14; x += 2) box(0.9, 0.05, 0.08, C.line, x, 0.17, 6.3, this.scene, false);
    for (let z = -7; z <= 4; z += 2) box(0.08, 0.05, 0.9, C.line, 0, 0.17, z, this.scene, false);
    // paths from the doors to the roads
    for (const x of Object.values(CITY_X)) box(1.6, 0.03, 4.5, 0xeceff4, x, 0.16, CITY_Z + 3.9, this.scene, false);
    const trees = [[-12.5, -7, 1.1], [-10, -8, 0.9], [-3.4, -8.2, 1], [3.5, -8, 1.2], [10.5, -8.2, 1], [12.8, -6, 1.1], [-12.8, 2, 1], [12.8, 2.5, 1],
      [-3.2, 3, 0.8], [3.2, 3.2, 0.9], [-9.5, 3.8, 0.9], [9.6, 3.8, 0.8], [-13, -2, 0.9], [13, -2.5, 1]];
    trees.forEach(([x, z, s]) => this.scene.add(makeTree(x, z, s)));
  }

  buildBuildings() {
    this.buildings = new Map();
    this.buildingsRoot = new THREE.Group(); this.scene.add(this.buildingsRoot);
    const docs = this.data.documents, pend = this.data.pending.pending;
    this.data.projects.projects.forEach((p) => {
      const byAgent = {}, pByAgent = {};
      (docs[p.id] || []).forEach((d) => (byAgent[d.agent] ||= []).push(d));
      byAgent.planning = docs[p.id] || [];
      pend.filter((x) => x.project === p.id).forEach((x) => (pByAgent[x.agent] ||= []).push(x));
      const b = makeBuilding(p, byAgent, pByAgent);
      this.buildings.set(p.id, b); this.buildingsRoot.add(b.group);
    });
  }

  buildTraffic() {
    this.cars = [];
    const mk = (color, x, z, speed) => { const c = makeCar(color); c.position.set(x, 0.18, z); this.scene.add(c); this.cars.push({ g: c, speed, z, axis: "x" }); };
    mk(0xffffff, -8, 6.75, 2.2); mk(C.accent, 4, 6.75, 2.6); mk(0xcfd6e2, 10, 5.85, -1.8);
    const c = makeCar(0xffffff); c.rotation.y = Math.PI / 2; c.position.set(0.45, 0.18, 2); this.scene.add(c); this.cars.push({ g: c, speed: 1.8, x: 0.45, axis: "z" });
    this.forklifts = [];
    for (const b of this.buildings.values()) {
      if (!b.project.running_task_id) continue;
      const f = makeForklift(); f.g.rotation.y = Math.PI / 2; this.scene.add(f.g);
      this.forklifts.push({ ...f, b });
    }
  }

  // ------------------------------------------------------------ camera
  resize() {
    const w = this.canvas.clientWidth || window.innerWidth, h = this.canvas.clientHeight || window.innerHeight;
    this.size = { w, h };
    this.renderer.setSize(w, h, false);
    this.updateCamera();
  }
  snapCamera(all) {
    this.cam.target.copy(this.camGoal.target); this.cam.zoom = this.camGoal.zoom; this.cam.offX = this.camGoal.offX; this.updateCamera();
    if (all) for (const b of this.buildings.values()) { b.explode = b.explodeTarget; applyExplode(b); b.floors.forEach((f) => { f.vis = f.visTarget ?? 1; f.group.scale.setScalar(Math.max(f.vis, 0.001)); f.group.visible = f.vis > 0.01; }); }
  }
  updateCamera() {
    const { w, h } = this.size, S = 10, a = w / h, c = this.camera;
    c.left = -a * S; c.right = a * S; c.top = S; c.bottom = -S;
    c.zoom = this.cam.zoom * Math.min(1, a / 1.6);
    c.position.copy(this.cam.target).addScaledVector(this.dir, 100);
    c.lookAt(this.cam.target);
    c.setViewOffset(w, h, this.cam.offX, 0, w, h);
    c.updateProjectionMatrix();
    this.sun.position.copy(this.cam.target).add(this.sunOffset);
    this.sun.target.position.copy(this.cam.target); this.sun.target.updateMatrixWorld();
  }
  fly(goal) { Object.assign(this.camGoal, { zoom: goal.zoom ?? this.camGoal.zoom, offX: goal.offX ?? this.camGoal.offX }); if (goal.target) this.camGoal.target.set(...goal.target); }
  setPanelOffset(px) { this.camGoal.offX = px / 2; }

  buildingPos(pid) { return this.buildings.get(pid).group.position; }
  floorWorld(pid, agentId, local = new THREE.Vector3()) {
    const b = this.buildings.get(pid), f = b.floors.find((x) => x.agent.id === agentId);
    f.group.updateWorldMatrix(true, false);
    return f.group.localToWorld(local.clone());
  }

  // ------------------------------------------------------------ views
  setView(name, o = {}) {
    this.view = { name, ...o };
    const wide = Math.min(1, this.size.w / 1500);
    if (name === "city") {
      for (const b of this.buildings.values()) { b.explodeTarget = 0; b.floors.forEach((f) => (f.visTarget = 1)); }
      this.fly({ target: [0, 3.2, 0.5], zoom: 0.52 + 0.1 * wide });
    } else if (name === "building") {
      for (const b of this.buildings.values()) { b.explodeTarget = b.id === o.pid ? 1 : 0; b.floors.forEach((f) => (f.visTarget = 1)); }
      const p = this.buildingPos(o.pid);
      this.fly({ target: [p.x, 8.6, p.z], zoom: 0.66 + 0.12 * wide });
    } else if (name === "floor") {
      for (const b of this.buildings.values()) { b.explodeTarget = b.id === o.pid ? 1 : 0; b.floors.forEach((f) => (f.visTarget = b.id === o.pid && f.agent.id !== o.agent ? 0 : 1)); }
      const p = this.buildingPos(o.pid), b = this.buildings.get(o.pid), f = b.floors.find((x) => x.agent.id === o.agent);
      this.fly({ target: [p.x, f.index * H1 + 0.16 + 0.55, p.z], zoom: 2.35 + 0.35 * wide });
    } else if (name === "control") {
      for (const b of this.buildings.values()) { b.explodeTarget = 0; b.floors.forEach((f) => (f.visTarget = 1)); }
      this.fly({ target: [CONTROL_POS.x, 1.4, CONTROL_POS.z], zoom: 1.35 });
    }
    for (const b of this.buildings.values()) b.otherHidden = (name === "building" || name === "floor") && b.id !== o.pid;
    this.hoverBox.visible = false;
  }

  // ------------------------------------------------------------ picking
  visibleInTree(o) { for (let p = o; p; p = p.parent) if (!p.visible) return false; return true; }
  pick(clientX, clientY) {
    const r = this.canvas.getBoundingClientRect();
    const ndc = new THREE.Vector2(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
    this.raycaster.setFromCamera(ndc, this.camera);
    const roots = [this.buildingsRoot, this.control];
    const hits = this.raycaster.intersectObjects(roots, true);
    const name = this.view.name;
    for (const h of hits) {
      const o = h.object;
      if (!this.visibleInTree(o) || o.material?.visible === false && !this.findUp(o, "item")) continue;
      if (name === "city") {
        const b = this.findUp(o, "building"); if (b) return { type: "project", id: b.userData.building, object: b };
      } else if (name === "building") {
        const f = this.findUp(o, "floor");
        if (f && f.userData.floor.pid === this.view.pid) {
          // the closed front walls are not pickable once open
          return { type: "floor", pid: f.userData.floor.pid, agent: f.userData.floor.agent, object: f };
        }
      } else if (name === "floor") {
        const f = this.findUp(o, "floor");
        if (!f || f.userData.floor.pid !== this.view.pid || f.userData.floor.agent !== this.view.agent) continue;
        const it = this.findUp(o, "item");
        if (it) return { ...it.userData.item, object: it };
      }
    }
    return null;
  }
  findUp(o, key) { for (let p = o; p; p = p.parent) if (p.userData && p.userData[key]) return p; return null; }
  outline(pick) {
    if (!pick) { this.hoverBox.visible = false; return; }
    const box3 = this.hoverBox.box;
    if (pick.type === "floor") {
      const o = pick.object; o.updateWorldMatrix(true, false);
      const p = o.getWorldPosition(new THREE.Vector3());
      box3.min.set(p.x - W / 2, p.y - 0.17, p.z - D / 2); box3.max.set(p.x + W / 2, p.y + 1.6, p.z + D / 2);
    } else if (pick.type === "project") {
      const p = pick.object.position, n = this.buildings.get(pick.id).floors.length;
      box3.min.set(p.x - W / 2 - 0.1, 0, p.z - D / 2 - 0.1); box3.max.set(p.x + W / 2 + 0.1, n * H0 + 0.6, p.z + D / 2 + 0.1);
    } else if (pick.object) {
      pick.object.updateWorldMatrix(true, true);
      box3.setFromObject(pick.object); box3.expandByScalar(0.04);
    }
    this.hoverBox.visible = true;
  }

  // ------------------------------------------------------------ projection for the HTML labels
  screen(v) {
    const p = v.clone().project(this.camera);
    return { x: (p.x * 0.5 + 0.5) * this.size.w, y: (-p.y * 0.5 + 0.5) * this.size.h, behind: p.z > 1 };
  }
  anchor(kind, pid, agentId) {
    const b = this.buildings.get(pid);
    if (kind === "roof") return b.group.localToWorld(new THREE.Vector3(0, b.floors.length * H0 + 1.0, 0));
    const f = b.floors.find((x) => x.agent.id === agentId);
    f.group.updateWorldMatrix(true, false);
    if (kind === "chip") return f.group.localToWorld(new THREE.Vector3(W / 2 + 0.1, 0.9, -D / 2));
    if (kind === "agent") return f.group.localToWorld((f.anim.figureAnchor || new THREE.Vector3(0.7, 1.7, -0.45)).clone());
    if (kind === "door") return f.group.localToWorld(new THREE.Vector3(-1.5, 1.7, -D / 2 + 0.12));
    if (kind === "floor") return f.group.localToWorld(new THREE.Vector3(0, 0.6, 0));
    return b.group.position.clone();
  }

  // ------------------------------------------------------------ animation
  tick(dt) {
    this.time += dt; const t = this.time;
    const k = 1 - Math.exp(-dt * 4.5);
    this.cam.target.lerp(this.camGoal.target, k);
    this.cam.zoom = lerp(this.cam.zoom, this.camGoal.zoom, k);
    this.cam.offX = lerp(this.cam.offX, this.camGoal.offX, k);
    this.updateCamera();

    for (const b of this.buildings.values()) {
      b.group.visible = !b.otherHidden;
      if (Math.abs(b.explode - b.explodeTarget) > 0.001) {
        b.explode += (b.explodeTarget - b.explode) * (1 - Math.exp(-dt * 3.2));
        if (Math.abs(b.explode - b.explodeTarget) < 0.004) b.explode = b.explodeTarget;
        applyExplode(b);
      }
      if (b.beacon.visible) { const s = 1 + 0.12 * Math.sin(t * 3); b.beacon.scale.set(s, s, 1); b.beacon.material.opacity = 0.35 + 0.3 * (0.5 + 0.5 * Math.sin(t * 3)); }
      for (const f of b.floors) {
        const vt = f.visTarget ?? 1; f.vis = f.vis ?? 1;
        if (f.vis !== vt) { f.vis += (vt - f.vis) * (1 - Math.exp(-dt * 8)); if (Math.abs(f.vis - vt) < 0.01) f.vis = vt; f.group.scale.setScalar(Math.max(f.vis, 0.001)); f.group.visible = f.vis > 0.01; }
        if (f.group.visible) this.animateFloor(f, t);
      }
    }
    const traffic = this.view.name !== "floor";
    this.cars.forEach((c) => { c.g.visible = traffic; });
    for (const f of this.forklifts) f.g.visible = traffic;
    this.cars.forEach((c) => {
      if (c.axis === "x") { c.g.position.x += c.speed * dt; if (c.g.position.x > 16) c.g.position.x = -16; if (c.g.position.x < -16) c.g.position.x = 16; c.g.rotation.y = c.speed < 0 ? Math.PI : 0; }
      else { c.g.position.z += c.speed * dt; if (c.g.position.z > 7) c.g.position.z = -8; c.g.rotation.y = Math.PI / 2 * (c.speed > 0 ? -1 : 1); }
    });
    for (const f of this.forklifts) {
      const p = f.b.group.position, ph = (t * 0.22) % 1, back = ph > 0.5, u = back ? (ph - 0.5) * 2 : ph * 2;
      const z0 = p.z + D / 2 + 0.9, z1 = 5.2;
      f.g.position.set(p.x + 0.9, 0.18, lerp(z0, z1, back ? 1 - u : u));
      f.g.rotation.y = back ? -Math.PI / 2 : Math.PI / 2;
      f.cargo.visible = !back;
    }
    this.control.userData.leds.forEach((l) => { l.material.color.setHex(Math.sin(t * 2 + l.userData.phase) > 0.2 ? C.accent : 0xb9c6dc); });
    this.control.userData.bars.forEach((b, i) => { const s = 0.7 + 0.3 * Math.sin(t * 1.5 + i); b.scale.y = s; });
    if (this.view.name === "city" || this.view.name === "building") this.hoverBox.material.opacity = 1;
    this.renderer.render(this.scene, this.camera);
    if (this.onFrame) this.onFrame();
  }

  animateFloor(f, t) {
    const a = f.anim; if (!a.fig) { if (a.screenMat) a.screenMat.emissive.setHex(0x000000); return; }
    const { fig } = a;
    fig.bang.visible = a.state === "waiting";
    if (a.state === "working") {
      fig.armL.rotation.x = 1.25 + Math.sin(t * 11) * 0.22; fig.armR.rotation.x = 1.25 + Math.sin(t * 11 + 2) * 0.22;
      fig.armR.rotation.z = 0; fig.g.position.y = Math.sin(t * 6) * 0.01;
      fig.head.rotation.y = Math.sin(t * 1.3) * 0.12;
      a.screenMat.emissive.setHex(Math.sin(t * 9) > 0 ? 0x2a58d8 : 0x3b78ff);
      a.sparks.forEach((s) => { const ph = (t * 0.6 + s.userData.phase) % 1; s.position.set(0.35 + Math.sin(ph * 9 + s.userData.phase * 20) * 0.28, 1.3 + ph * 0.9, -1.15); s.material.opacity = 1 - ph; s.scale.setScalar(1 - ph * 0.5); });
    } else if (a.state === "waiting") {
      fig.armL.rotation.x = 1.0; fig.armR.rotation.z = 2.55 + Math.sin(t * 6) * 0.35; fig.armR.rotation.x = 0;
      fig.bang.position.y = 1.75 + Math.sin(t * 4) * 0.07; fig.bang.rotation.y = t * 1.5;
      a.screenMat.emissive.setHex(0x6b4a0f);
    } else {
      fig.armL.rotation.x = 0.35; fig.armR.rotation.x = 0.35; fig.armR.rotation.z = 0;
      fig.head.rotation.x = 0.12 + Math.sin(t * 0.9) * 0.04;
      a.screenMat.emissive.setHex(0x1a2a46);
    }
  }
}
