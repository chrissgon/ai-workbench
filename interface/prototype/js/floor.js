// Floor view: one room, the agent at its desk, the documents on the desk, the inbox tray.
import { projector, box, tile, poly, faceX, faceY, plane, cone, esc, pts } from "./iso.js";
import { store, floorDef, agentOf, pendingOf, docsOf, relTime, bandOf } from "./data.js";
import { renderTrack, chip, bar, money, kv, openDocument, tooltip, hideTip } from "./ui.js";
import { inboxCard, chatCard } from "./cards.js";

const N = 7, H = 200;

function wrap(text, max) {
  const lines = []; let cur = "";
  for (const w of String(text).split(" ")) {
    if ((cur + " " + w).trim().length > max) { lines.push(cur); cur = w; } else cur = (cur + " " + w).trim();
  }
  if (cur) lines.push(cur);
  return lines;
}

function person(P, a) {
  const [bx, by] = P.p(5.85, 3.15, 0);
  let s = "";
  s += box(P, 5.45, 2.8, 0, 0.6, 0.6, 3, "slate") + box(P, 5.67, 3.02, 3, 0.16, 0.16, 14, "slate");
  s += box(P, 5.35, 2.7, 17, 0.8, 0.8, 5, "ink");
  if (a.enabled) {
    s += `<g class="who">
      <rect class="pants" x="${bx - 30}" y="${by - 34}" width="34" height="10" rx="5"/><rect class="pants" x="${bx - 30}" y="${by - 34}" width="10" height="34" rx="5"/>
      <rect class="shirt" x="${bx - 13}" y="${by - 72}" width="26" height="42" rx="10"/>
      <g class="${a.state === "idle" ? "nod" : ""}"><circle class="skin" cx="${bx}" cy="${by - 86}" r="13"/>
        <path class="hair" d="M${bx - 13} ${by - 88} a13 13 0 0 1 26 0 q-12 -7 -26 0z"/><circle cx="${bx - 4.5}" cy="${by - 85}" r="1.6" fill="#2a3646"/><circle cx="${bx + 4.5}" cy="${by - 85}" r="1.6" fill="#2a3646"/>
        <path d="M${bx - 3.5} ${by - 79} q3.5 3 7 0" fill="none" stroke="#2a3646" stroke-width="1.4" stroke-linecap="round"/></g>`;
    if (a.state === "waiting") s += `<rect class="shirt2" x="${bx - 6}" y="${by - 118}" width="9" height="40" rx="4.5" transform="rotate(14 ${bx} ${by - 70})"/>`;
    else s += `<rect class="shirt2 ${a.state === "working" ? "typing" : ""}" x="${bx - 46}" y="${by - 64}" width="44" height="9" rx="4.5" transform="rotate(8 ${bx - 4} ${by - 60})"/>`;
    s += `</g>`;
    if (a.state === "waiting") s += `<g transform="translate(${bx + 6} ${by - 128})"><g class="bubble bob"><path d="M-17 -10 h34 a7 7 0 0 1 7 7 v12 a7 7 0 0 1 -7 7 h-12 l-5 7 l-5 -7 h-12 a7 7 0 0 1 -7 -7 v-12 a7 7 0 0 1 7 -7z"/><text y="9" style="font-size:15px">!</text></g></g>`;
    if (a.state === "working") s += `<g transform="translate(${bx + 16} ${by - 118})"><g class="bubble bob"><rect x="-4" y="-10" width="52" height="24" rx="12"/><g class="dot3"><circle cx="9" cy="2" r="3"/><circle cx="23" cy="2" r="3"/><circle cx="37" cy="2" r="3"/></g></g></g>`;
    if (a.state === "idle") s += `<text class="zzz" x="${bx + 18}" y="${by - 104}">z z</text>`;
  }
  return s;
}

function desk(P, a, docs, items) {
  let s = box(P, 2.4, 2.6, 0, 0.2, 1.0, 30, "wood") + box(P, 5.0, 2.6, 0, 0.2, 1.0, 30, "wood") + box(P, 2.3, 2.5, 30, 3.1, 1.2, 4, "wood");
  // monitor, screen facing the visible side
  s += box(P, 3.55, 2.85, 34, 0.3, 0.3, 8, "ink") + box(P, 3.0, 2.8, 42, 1.4, 0.14, 26, "ink");
  const on = a.enabled && a.state === "working";
  s += faceY(P, 2.94, 3.07, 4.13, 45, 65, `screen ${a.enabled ? (on ? "on" : "") : "off"}`);
  if (on) for (let i = 0; i < 4; i++) s += faceY(P, 2.95, 3.15, 3.15 + 0.5 + (i % 2) * 0.3, 48 + i * 4.2, 50.2 + i * 4.2, "code-line", `style="animation-delay:${i * 0.3}s"`);
  // mug with steam
  s += box(P, 4.55, 3.2, 34, 0.18, 0.18, 7, "paper");
  if (a.enabled && a.state === "idle") { const [mx, my] = P.p(4.64, 3.29, 44); s += `<path class="steam" d="M${mx - 2} ${my} q-3 -5 0 -9"/><path class="steam" style="animation-delay:.9s" d="M${mx + 3} ${my} q-3 -5 0 -9"/>`; }
  // documents: up to five sheets, each opens its file
  const slots = [[2.45, 2.62], [2.45, 3.15], [4.3, 2.62], [4.3, 3.15], [2.95, 3.15]];
  docs.slice(0, 5).map((d, i) => ({ d, i, k: slots[i][0] + slots[i][1] })).sort((u, v) => u.k - v.k).forEach(({ d, i }) => {
    const [x, y] = slots[i];
    s += `<g class="paper hot" data-doc="${i}" tabindex="0" role="button" aria-label="Open ${esc(d.path)}"><title>${esc(d.path)}</title>${box(P, x, y, 34, 0.42, 0.5, 1.4 + (i % 2) * 1.2, "paper")}${faceY(P, y + 0.5, x + 0.05, x + 0.33, 35 + (i % 2) * 1.2, 36.2 + (i % 2) * 1.2, "code-line", 'style="animation:none;fill:#8fb0ff"')}</g>`;
  });
  // inbox tray
  const n = items.length, [tx, ty] = P.p(5.1, 3.05, 62);
  s += `<g class="tray hot" id="tray" tabindex="0" role="button" aria-label="Inbox, ${n} decisions"><title>Inbox: ${n}</title>${box(P, 4.8, 2.65, 34, 0.55, 0.85, 5, "accent")}${n ? box(P, 4.87, 2.72, 39, 0.4, 0.7, 2.5, "paper") : ""}
    ${n ? `<g transform="translate(${tx} ${ty})"><g class="pin bob"><circle r="12"/><text y="5">${n}</text></g></g>` : ""}</g>`;
  return s;
}

function shelf(P) {
  let s = box(P, 5.3, 0.1, 0, 1.6, 0.8, 120, "mist");
  [20, 62, 100].forEach((z, r) => {
    s += faceY(P, 0.9, 5.4, 6.8, z, z + 3, "", 'fill="#c1cfdf"');
    for (let k = 0; k < 4; k++) s += box(P, 5.45 + k * 0.33, 0.25, z + 3, 0.24, 0.5, 14 + ((k + r) % 3) * 4, ["accent", "paper", "slate"][(k + r) % 3]);
  });
  return s;
}

function plant(P) {
  return box(P, 0.4, 0.4, 0, 0.55, 0.55, 18, "wood") + cone(P, 0.67, 0.67, 18, 16, 54) + cone(P, 0.5, 0.8, 18, 11, 38);
}

function wallDecor(P, p, a, task, lobby) {
  let s = "";
  // window on the left wall (plane x = 0)
  s += faceX(P, 0, 1.0, 3.6, 70, 160, "", 'fill="url(#sky)" stroke="#fff" stroke-width="5"') +
    `<polyline fill="none" stroke="#fff" stroke-width="3" points="${pts([P.p(0, 2.3, 70), P.p(0, 2.3, 160)])}"/><polyline fill="none" stroke="#fff" stroke-width="3" points="${pts([P.p(0, 1.0, 115), P.p(0, 3.6, 115)])}"/>`;
  // clock
  const [cx, cy] = P.p(0, 4.2, 150);
  s += `<g transform="translate(${cx} ${cy})"><circle r="14" fill="#fff" stroke="#b9c7d8" stroke-width="2"/><path d="M0 0 V-9 M0 0 L7 3" stroke="#3a4a5e" stroke-width="2" stroke-linecap="round" fill="none"/></g>`;
  // task board on the right wall (plane y = 0)
  const lines = task ? wrap(task.title, 25) : ["No task right now"];
  const v0 = H - 170;
  const inner = `<rect class="board" x="16" y="${v0}" width="172" height="112" rx="6"/>
    <text class="wall-muted" x="28" y="${v0 + 22}">${a.enabled ? "CURRENT TASK" : "AGENT DISABLED"}</text>
    ${lines.map((l, i) => `<text class="wall-text" x="28" y="${v0 + 42 + i * 15}">${esc(l)}</text>`).join("")}
    ${task ? `<text class="wall-muted" x="28" y="${v0 + 42 + lines.length * 15 + 8}">${esc(task.skill)}</text>
      <rect x="28" y="${v0 + 90}" width="${String(task.run_state).length * 7.4 + 16}" height="16" rx="8" fill="#e4ecff"/><text class="chipt" x="36" y="${v0 + 101.5}" fill="#1d49c4" style="fill:#1d49c4">${esc(task.run_state.toUpperCase())}</text>` : ""}`;
  s += plane(P.p(0, 0, H), "down", inner);
  return s;
}

export function render(root, ctx) {
  const p = ctx.project, key = ctx.floor, a = agentOf(p, key), def = floorDef(key);
  const lobby = key === "planning";
  const docs = docsOf(p, key), items = pendingOf(p, key), task = a.task;
  const P = projector([600, 250], 72);

  let g = `<defs><linearGradient id="sky" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#cfe3ff"/><stop offset="1" stop-color="#f2f8ff"/></linearGradient></defs>`;
  g += `<ellipse class="shadow" cx="600" cy="520" rx="270" ry="26" style="fill:rgba(30,50,80,.10)"/>`;
  g += poly([P.p(0, N, 0), P.p(N, N, 0), P.p(N, N, -14), P.p(0, N, -14)], "", 'fill="#b9c8d8"') + poly([P.p(N, 0, 0), P.p(N, N, 0), P.p(N, N, -14), P.p(N, 0, -14)], "", 'fill="#a7b9cc"');
  for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) g += tile(P, i, j, 1, 1, (i + j) % 2 ? "fl-a" : "fl-b");
  g += tile(P, 1.9, 1.6, 5.2, 3.9, "rug", 0.5);
  g += poly([P.p(0, 0, 0), P.p(0, N, 0), P.p(0, N, H), P.p(0, 0, H)], "wallA") + poly([P.p(0, 0, 0), P.p(N, 0, 0), P.p(N, 0, H), P.p(0, 0, H)], "wallB");
  g += poly([P.p(0, 0, 8), P.p(0, N, 8), P.p(0, N, 0), P.p(0, 0, 0)], "", 'fill="#cdd9e6"') + poly([P.p(0, 0, 8), P.p(N, 0, 8), P.p(N, 0, 0), P.p(0, 0, 0)], "", 'fill="#c3d0df"');
  g += wallDecor(P, p, a, task, lobby);
  if (lobby) {
    // the door to the control room, on the left wall
    const [dx, dy] = P.p(0, 5.6, 135);
    g += `<g class="door hot" id="door" tabindex="0" role="link" aria-label="Open the control room"><title>Control room</title>${faceX(P, 0, 4.9, 6.3, 0, 120, "door-leaf", 'stroke="#fff" stroke-width="4"')}
      <circle cx="${P.p(0, 6.15, 55)[0]}" cy="${P.p(0, 6.15, 55)[1]}" r="3.5" fill="#fff"/>
      <g transform="translate(${dx} ${dy})"><rect x="-52" y="-14" width="104" height="26" rx="8" fill="#fff" stroke="#c9d5e3"/><text text-anchor="middle" y="4" class="plate-text">CONTROL ROOM</text></g></g>`;
  }
  const objs = [{ k: 0.8, s: plant(P) }, { k: 6, s: shelf(P) }, { k: 6.6, s: desk(P, a, docs, items) }, { k: 9, s: person(P, a) }];
  g += objs.sort((u, v) => u.k - v.k).map((o) => o.s).join("");
  if (!a.enabled) g += poly([P.p(0, 0, 0), P.p(0, N, 0), P.p(0, N, H), P.p(0, 0, H)], "lights-off", 'style="opacity:.3"') + poly([P.p(0, 0, 0), P.p(N, 0, 0), P.p(N, 0, H), P.p(0, 0, H)], "lights-off", 'style="opacity:.3"') + tile(P, 0, 0, N, N, "lights-off", 0, 'style="opacity:.3"');

  // left rail: the desk
  const deskCard = `<div class="card"><h3>Desk <span class="count">${docs.length}</span></h3><div class="hint" style="margin-bottom:6px">Artifacts under docs/ this agent's skills own. Click one to read it.</div>
    <ul class="list" id="doclist">${docs.map((d, i) => `<li data-i="${i}"><div class="grow"><div class="t">${esc(d.path)}</div><div class="s">${esc(d.owner)} · ${esc(relTime(d.modified))}</div></div></li>`).join("") || '<li style="cursor:default"><div class="s">No artifact yet.</div></li>'}</ul></div>`;
  const band = task ? bandOf(task.skill) : null;
  const agentCard = `<div class="card compact"><h3>${esc(def.label)} · ${esc(a.name)} ${a.enabled ? "" : chip("failed").replace("failed", "disabled")}</h3>
    <div style="margin-bottom:8px"><span class="plate-mode ${a.mode === "stopped" ? "stopped" : ""}">${esc(a.mode.toUpperCase())}</span> <span class="hint">${esc(store.ws.modes[a.mode])}</span></div>
    ${bar("runs", a.runs_today, a.max_runs_per_day)}${bar("spend", a.usd_today, a.max_usd_per_day, money)}
    ${kv([["State", chip(a.enabled ? a.state : "idle") + (a.enabled ? "" : ' <span class="muted">lights off</span>')],
      ["Task", task ? esc(task.title) : "none"], ["Skill", task ? esc(task.skill) : "none"], ["Run", task ? `${chip(task.run_state)} <span class="muted">since ${esc(relTime(task.since))}</span>` : "none"],
      ["Proof", band ? `${chip(band.band)} <span class="muted">on the reference model</span>` : "none"]])}</div>`;

  root.innerHTML = `<div class="stage"><svg viewBox="300 30 600 520" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${esc(def.label)} floor of ${esc(p.name)}">${g}</svg></div>
    <div class="rail left">${deskCard}</div><div class="rail right" id="rightrail">${agentCard}</div>`;
  const right = root.querySelector("#rightrail");
  if (lobby) right.append(chatCard(p, store.chat[p.id]));
  const inbox = inboxCard(p, items);
  right.append(inbox);

  const openDoc = (i) => { hideTip(); openDocument(docs[i]); };
  root.querySelectorAll("#doclist li[data-i]").forEach((li) => { li.onclick = () => openDoc(Number(li.dataset.i)); });
  root.querySelectorAll(".paper").forEach((el) => {
    const i = Number(el.dataset.doc), d = docs[i];
    tooltip(el, `<b>${esc(d.path)}</b><br>${esc(d.owner)}<br><span class="muted">Click to read</span>`);
    el.onclick = () => openDoc(i);
    el.onkeydown = (e) => { if (e.key === "Enter") openDoc(i); };
  });
  const tray = root.querySelector("#tray");
  const goInbox = () => { inbox.scrollIntoView({ behavior: "smooth", block: "nearest" }); inbox.classList.remove("flash"); void inbox.offsetWidth; inbox.classList.add("flash"); };
  tray.onclick = goInbox; tray.onkeydown = (e) => { if (e.key === "Enter") goInbox(); };
  const door = root.querySelector("#door");
  if (door) { door.onclick = () => ctx.go(`#/p/${p.id}/planning/control`); door.onkeydown = (e) => { if (e.key === "Enter") ctx.go(`#/p/${p.id}/planning/control`); }; }
  renderTrack(p, (s) => ctx.taskPanel(p, s));
}
