// Building view: the project as a cross-section, one floor per area agent, Lobby at the bottom.
import { projector, box, tile, poly, plane, cone, esc, pts } from "./iso.js";
import { store, floorDef, pendingOf } from "./data.js";
import { renderTrack, tooltip, chip, bar, money, hideTip } from "./ui.js";

const LW = 380, HF = 76, RW = 112; // left plane width, floor height, right plane width
const W = LW / 32, D = RW / 32;

function sitter(a) {
  const on = a.enabled;
  let s = `<rect class="desk-leg" x="28" y="42" width="4" height="26" rx="2"/><rect class="desk-leg" x="28" y="58" width="26" height="4" rx="2"/>`;
  if (on) {
    s += `<g class="${a.state === "idle" ? "nod" : ""}"><rect class="shirt" x="40" y="36" width="18" height="23" rx="7"/>
      <circle class="skin" cx="50" cy="27" r="8.5"/><path class="hair" d="M41.5 26 a8.5 8.5 0 0 1 17 0 q-8 -4 -17 0z"/><circle cx="53" cy="28" r="1.2" fill="#2a3646"/></g>
      <rect class="shirt2 ${a.state === "working" ? "typing" : ""}" x="52" y="44" width="24" height="5" rx="2.5" ${a.state === "waiting" ? 'transform="rotate(-50 52 46)"' : ""}/>`;
  }
  // desk
  s += `<rect class="desk-top" x="14" y="58" width="118" height="5" rx="2"/><rect class="desk-leg" x="20" y="63" width="4" height="9"/><rect class="desk-leg" x="120" y="63" width="4" height="9"/>
    <rect x="76" y="33" width="28" height="19" rx="2.5" fill="#46566b"/><rect class="screen ${on ? (a.state === "working" ? "on" : "") : "off"}" x="78.5" y="35.5" width="23" height="14" rx="1.5"/>
    <rect x="88" y="52" width="4" height="6" fill="#46566b"/><rect x="108" y="53" width="16" height="5" rx="1" fill="#fff" stroke="#c9d5e3" stroke-width=".6"/><rect x="110" y="50.5" width="14" height="3" rx="1" fill="#e6edf5" stroke="#c9d5e3" stroke-width=".6"/>
    <rect x="18" y="52" width="7" height="6" rx="1.5" fill="#fff" stroke="#c9d5e3" stroke-width=".7"/>`;
  if (on && a.state === "idle") s += `<path class="steam" d="M20.5 50 q-2 -4 0 -7"/><path class="steam" style="animation-delay:.8s" d="M23 50 q-2 -4 0 -7"/>`;
  if (on && a.state === "waiting") s += `<g transform="translate(50 6)"><g class="bubble bob"><path d="M-12 -6 h24 a5 5 0 0 1 5 5 v8 a5 5 0 0 1 -5 5 h-9 l-3 5 l-3 -5 h-9 a5 5 0 0 1 -5 -5 v-8 a5 5 0 0 1 5 -5z"/><text y="9" >!</text></g></g>`;
  if (on && a.state === "working") s += `<g class="dot3" transform="translate(62 14)"><circle cx="0" cy="0" r="2.2"/><circle cx="8" cy="0" r="2.2"/><circle cx="16" cy="0" r="2.2"/></g>`;
  if (on && a.state === "idle") s += `<text class="zzz" x="62" y="16">z</text>`;
  return s;
}

function floorSvg(p, a, i) {
  const def = floorDef(a.key);
  const v0 = (store.ws.floors.length - 1 - i) * HF;
  const open = pendingOf(p, a.key).length;
  const modeCls = a.mode === "stopped" ? "stopped" : "";
  const modeW = a.mode.length * 5.6 + 16;
  const runs = a.max_runs_per_day ? Math.min(1, a.runs_today / a.max_runs_per_day) : 0;
  const usd = a.max_usd_per_day ? Math.min(1, a.usd_today / a.max_usd_per_day) : 0;
  return `<g transform="translate(0 ${v0})" class="flr" data-key="${esc(a.key)}" tabindex="0" role="link" aria-label="Enter the ${esc(def.label)} floor">
    <rect class="room-bg ${i % 2 ? "alt" : ""}" x="0" y="0" width="${LW}" height="${HF}"/>
    <rect class="room-ceil" x="0" y="0" width="${LW}" height="4"/><rect class="room-floor" x="0" y="${HF - 8}" width="${LW}" height="8"/>
    ${sitter(a)}
    <text class="floor-label" x="154" y="18">${esc(def.label.toUpperCase())}</text>
    <text class="plate-text" x="154" y="32" style="font-size:12px">${esc(a.name)}</text>
    <rect class="plate mode-plate ${modeCls}" x="154" y="37" width="${modeW}" height="15" rx="7.5"/><text class="mode-text ${modeCls}" x="${154 + modeW / 2}" y="47.5" text-anchor="middle">${esc(a.mode.toUpperCase())}</text>
    <text class="plate-sub" x="154" y="66">${a.enabled ? esc(a.state === "working" ? a.task.skill : a.state === "waiting" ? "waits for you" : "idle") : "lights off, agent disabled"}</text>
    <text class="plate-sub" x="284" y="16">runs ${a.runs_today}/${a.max_runs_per_day}</text><rect class="mini-bar" x="284" y="20" width="84" height="5" rx="2.5"/><rect class="mini-fill" x="284" y="20" width="${84 * runs}" height="5" rx="2.5"/>
    <text class="plate-sub" x="284" y="40">${money(a.usd_today)} / ${money(a.max_usd_per_day)}</text><rect class="mini-bar" x="284" y="44" width="84" height="5" rx="2.5"/><rect class="mini-fill" x="284" y="44" width="${84 * usd}" height="5" rx="2.5"/>
    ${open ? `<g transform="translate(356 64)"><g class="pin bob"><circle r="9"/><text y="4" style="font-size:11px">${open}</text></g></g>` : ""}
    ${a.enabled ? "" : `<rect class="lights-off" x="0" y="0" width="${LW}" height="${HF}"/>`}
    <rect class="frame" x="1.5" y="1.5" width="${LW - 3}" height="${HF - 3}" rx="3"/>
    <rect class="floor-hit" x="0" y="0" width="${LW}" height="${HF}"/></g>`;
}

function rightWindows(p) {
  const n = p.agents.length; let out = "";
  p.agents.forEach((a, i) => {
    const v0 = (n - 1 - i) * HF;
    [14, 62].forEach((u, j) => {
      let cls = "off";
      if (a.enabled) cls = a.state === "working" ? "work" : a.state === "waiting" ? "on" : j === 0 ? "on" : "off";
      out += `<rect class="win ${cls}" x="${u}" y="${v0 + 22}" width="30" height="30" rx="3" style="animation-delay:${(i * 0.31 + j * 0.4).toFixed(2)}s"/>`;
    });
    if (i) out += `<rect x="0" y="${v0 + HF - 1}" width="${RW}" height="2" fill="rgba(40,60,90,.18)"/>`;
  });
  return out;
}

export function render(root, ctx) {
  const p = ctx.project, n = p.agents.length;
  const P = projector([466, 510], 64);
  const H = n * HF;
  const left = P.p(0, D, H), rightBase = P.p(W, D, H);
  let g = "";
  g += tile(P, -4, -4, W + 8, D + 8, "grass");
  g += tile(P, -1.5, -1.5, W + 3, D + 3, "plaza");
  g += tile(P, W + 0.2, -4, 1.2, D + 8, "road");
  g += `<polyline class="road-line" points="${pts([P.p(W + 0.8, -4, 0), P.p(W + 0.8, D + 4, 0)])}"/>`;
  const trees = [[-3, -2], [-3, 2], [-2.4, 5.5], [W + 3, -2.5], [W - 2, D + 3], [3, D + 3.4], [8, D + 3.6]];
  g += trees.filter((t) => t[1] < D).map((t) => cone(P, t[0], t[1], 0, 12, 52)).join("");
  // shell: back wall (right plane) and roof; the left face is the cut-away
  g += poly([P.p(0, 0, 0), P.p(W, 0, 0), P.p(W, 0, H), P.p(0, 0, H)], "", 'fill="#cfdae7"');
  g += poly([P.p(W, 0, 0), P.p(W, D, 0), P.p(W, D, H), P.p(W, 0, H)], "", 'fill="#d5dfeb" stroke="rgba(40,60,90,.2)"');
  g += plane(P.p(W, D, H), "up", rightWindows(p));
  g += poly([P.p(0, D, 0), P.p(0, 0, 0), P.p(0, 0, H), P.p(0, D, H)], "", 'fill="#dbe5ef" stroke="rgba(40,60,90,.2)"');
  g += plane(left, "down", `<g>${p.agents.map((a, i) => floorSvg(p, a, i)).join("")}</g>`);
  g += poly([P.p(0, D, 0), P.p(W, D, 0), P.p(W, D, H), P.p(0, D, H)], "", 'fill="none" stroke="rgba(40,60,90,.35)" stroke-width="1.4"');
  g += box(P, -0.3, -0.3, H, W + 0.6, D + 0.6, 9, "mist") + box(P, W - 3, 0.4, H + 9, 1.2, 1, 14, "slate");
  const [sx, sy] = P.p(W / 2, D / 2, H + 40);
  const open = p.pending.length, w = p.name.length * 8 + 34;
  g += `<g class="sign" transform="translate(${sx} ${sy})"><rect x="${-w / 2}" y="-18" width="${w}" height="36" rx="12"/><text x="0" y="5" text-anchor="middle">${esc(p.name)}</text></g>
        <g transform="translate(${sx + w / 2 + 6} ${sy - 14})"><g class="pin bob ${open ? "" : "zero"}"><circle r="13"/><text y="5">${open}</text></g></g>`;

  const info = `<div class="card"><h3>${esc(p.name)}</h3><div class="hint">${esc(p.tagline)}</div>
      ${bar("runs", p.agents.reduce((m, a) => m + a.runs_today, 0), p.agents.filter((a) => a.enabled).reduce((m, a) => m + a.max_runs_per_day, 0))}
      ${bar("spend", p.agents.reduce((m, a) => m + a.usd_today, 0), p.agents.filter((a) => a.enabled).reduce((m, a) => m + a.max_usd_per_day, 0), money)}
      <div class="hint" style="margin-top:8px">Configuration ${esc(p.config.path)}<br>accepted hash ${esc(p.config.sha256.slice(0, 16))}...</div></div>`;
  const floors = [...p.agents].reverse();
  const list = `<div class="card"><h3>Floors</h3><ul class="list" id="floorlist">${floors.map((a) => {
    const def = floorDef(a.key), open = pendingOf(p, a.key).length;
    return `<li data-key="${esc(a.key)}"><span class="live ${a.state === "working" ? "on" : ""}"></span><div class="grow"><div class="t">${esc(def.label)} · ${esc(a.name)}</div>
      <div class="s">${a.enabled ? esc(a.mode) : "disabled"} · ${a.state === "working" ? esc(a.task.title) : esc(a.state)}</div></div>
      <span class="badge ${open ? "" : "zero"}">${open}</span></li>`;
  }).join("")}</ul></div>`;
  root.innerHTML = `<div class="stage"><svg viewBox="250 20 700 770" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Cross-section of ${esc(p.name)}">${g}</svg></div>
    <div class="rail left">${info}</div><div class="rail right">${list}</div>`;

  const enter = (key) => { hideTip(); ctx.go(`#/p/${p.id}/${key}`); };
  root.querySelectorAll(".flr").forEach((el) => {
    const a = p.agents.find((x) => x.key === el.dataset.key), def = floorDef(a.key);
    tooltip(el, `<b>${esc(def.label)} · ${esc(a.name)}</b><br>${esc(store.ws.modes[a.mode])}<br>${a.enabled ? "lights on" : "lights off"} · ${pendingOf(p, a.key).length} decisions<br><span class="muted">Click to enter</span>`);
    el.onclick = () => enter(a.key);
    el.onkeydown = (e) => { if (e.key === "Enter") enter(a.key); };
  });
  root.querySelectorAll("#floorlist li").forEach((li) => {
    const el = root.querySelector(`.flr[data-key="${li.dataset.key}"]`);
    li.onclick = () => enter(li.dataset.key);
    li.onpointerenter = () => el.classList.add("hl");
    li.onpointerleave = () => el.classList.remove("hl");
  });
  renderTrack(p, (s) => ctx.taskPanel(p, s));
}
