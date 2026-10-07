// City view: the projects are office buildings on an isometric plot of land.
import { projector, box, tile, poly, faceX, faceY, cone, shadow, esc, pts } from "./iso.js";
import { store, running, totals, pendingOf } from "./data.js";
import { renderTrack, tooltip, openPanel, kv, chip, hideTip } from "./ui.js";

const FH = 30; // floor height in pixels
const LAYOUT = { "northwind-shop": { x: 1, y: 6, w: 3, d: 3 }, "tinykv-docs": { x: 6, y: 1, w: 3, d: 3 } };

function windows(P, b, p, H) {
  let out = "";
  const n = 3;
  for (let i = 0; i < p.agents.length; i++) {
    const a = p.agents[i];
    for (let j = 0; j < n; j++) {
      let cls = "off";
      if (a.enabled) cls = a.state === "working" ? "work" : a.state === "waiting" ? "on" : j % 2 === 0 ? "on" : "off";
      const z0 = i * FH + 9, z1 = z0 + 14, step = b.w / n;
      const x0 = b.x + j * step + step * 0.22, x1 = x0 + step * 0.56;
      const door = i === 0 && j === 1;
      if (!door) out += faceY(P, b.y + b.d, x0, x1, z0, z1, `win ${cls}`, `style="animation-delay:${(i * 0.37 + j * 0.21).toFixed(2)}s"`);
      const stepD = b.d / n, y0 = b.y + j * stepD + stepD * 0.22, y1 = y0 + stepD * 0.56;
      out += faceX(P, b.x + b.w, y0, y1, z0, z1, `win ${cls}`, `style="animation-delay:${(i * 0.29 + j * 0.33).toFixed(2)}s"`);
    }
  }
  // door on the ground floor
  const step = b.w / n, x0 = b.x + step * 1.2, x1 = x0 + step * 0.6;
  out += faceY(P, b.y + b.d, x0, x1, 0, 18, "door-leaf");
  return out;
}

function buildingSvg(P, p) {
  const b = LAYOUT[p.id], H = p.agents.length * FH, live = running(p);
  const hex = [P.p(b.x, b.y + b.d, 0), P.p(b.x + b.w, b.y + b.d, 0), P.p(b.x + b.w, b.y, 0), P.p(b.x + b.w, b.y, H), P.p(b.x, b.y, H), P.p(b.x, b.y + b.d, H)];
  const body = box(P, b.x, b.y, 0, b.w, b.d, H, "paper");
  // floor bands
  let bands = "";
  for (let i = 1; i < p.agents.length; i++) {
    bands += `<polyline fill="none" stroke="rgba(40,60,90,.18)" stroke-width="1" points="${pts([P.p(b.x, b.y + b.d, i * FH), P.p(b.x + b.w, b.y + b.d, i * FH), P.p(b.x + b.w, b.y, i * FH)])}"/>`;
  }
  const roof = box(P, b.x + 0.35, b.y + 0.35, H, b.w - 0.7, b.d - 0.7, 8, "mist")
    + box(P, b.x + b.w - 1.2, b.y + 0.5, H + 8, 0.6, 0.6, 12, "slate");
  const [bx, by] = P.p(b.x + b.w - 0.9, b.y + 0.8, H + 24);
  const beacon = live ? `<circle cx="${bx}" cy="${by}" r="4" fill="var(--accent)"><animate attributeName="r" values="3;9;3" dur="1.6s" repeatCount="indefinite"/><animate attributeName="opacity" values="1;.2;1" dur="1.6s" repeatCount="indefinite"/></circle>` : "";

  const [sx, sy] = P.p(b.x + b.w / 2, b.y + b.d / 2, H + 46);
  const open = p.pending.length;
  const w = p.name.length * 7.6 + 30, run = live ? "working now" : "quiet";
  const sign = `<g class="sign" transform="translate(${sx} ${sy})"><path d="M-6 22 L0 30 L6 22 Z" fill="#fff" stroke="#cdd8e5"/><rect x="${-w / 2}" y="-18" width="${w}" height="42" rx="12"/>
      <text x="0" y="1" text-anchor="middle">${esc(p.name)}</text><text class="sub" x="0" y="17" text-anchor="middle">${esc(run)}</text></g>
    <g transform="translate(${sx + w / 2 + 6} ${sy - 18})"><g class="pin bob ${open ? "" : "zero"}"><circle r="13"/><text y="5">${open}</text></g></g>`;

  return `<g class="hot building" data-id="${esc(p.id)}" tabindex="0" role="link" aria-label="Enter ${esc(p.name)}">
    ${shadow(P, b.x, b.y, b.w, b.d, 0.2)}
    <g class="lift">${body}${bands}${windows(P, b, p, H)}${roof}${beacon}${sign}</g>
    <polygon class="halo" points="${pts(hex)}"/></g>`;
}

function vehicle(P, p) {
  const V = projector([0, 0], 64);
  const van = box(V, -0.5, -0.25, 3, 1, 0.5, 11, "accent") + box(V, 0.28, -0.25, 3, 0.35, 0.5, 8, "paper") + box(V, -0.5, -0.25, 0, 1.1, 0.5, 3, "ink");
  const a = P.p(5.0, 0.4), b = P.p(5.0, 11.6);
  const path = `M${a[0]} ${a[1]} L${b[0]} ${b[1]} L${a[0]} ${a[1]}`;
  return `<g class="hot van" tabindex="0" role="button" aria-label="Open the running task">
    <g><animateMotion dur="26s" repeatCount="indefinite" path="${path}"/>
    <circle r="26" fill="transparent"/><ellipse rx="22" ry="8" cy="6" class="shadow"/><g class="lift">${van}</g></g></g>`;
}

export function render(root, ctx) {
  const P = projector([600, 250], 64);
  const N = 12;
  let g = "";
  // land slab
  g += poly([P.p(0, N, 0), P.p(N, N, 0), P.p(N, N, -16), P.p(0, N, -16)], "base-slab", "style=\"fill:#b9c8d8\"");
  g += poly([P.p(N, 0, 0), P.p(N, N, 0), P.p(N, N, -16), P.p(N, 0, -16)], "base-slab", "style=\"fill:#a7b9cc\"");
  g += tile(P, 0, 0, N, N, "grass");
  // roads (axes through x = 5 and y = 5)
  g += tile(P, 4.5, 0, 1, N, "road") + tile(P, 0, 4.5, N, 1, "road");
  g += `<polyline class="road-line" points="${pts([P.p(5, 0, 0), P.p(5, N, 0)])}"/><polyline class="road-line" points="${pts([P.p(0, 5, 0), P.p(N, 5, 0)])}"/>`;
  g += tile(P, 4.2, 4.2, 1.6, 1.6, "plaza");
  // plots
  for (const p of store.projects) { const b = LAYOUT[p.id]; g += tile(P, b.x - 0.5, b.y - 0.5, b.w + 1, b.d + 1, "plaza"); }
  // park corner with a pond
  g += tile(P, 7.3, 7, 3, 3, "plaza", 0, "style=\"fill:#cfe3f6\"");
  const decor = [[0.8, 0.8], [2.4, 1.2], [1.2, 3.1], [10.6, 0.8], [10.8, 3.4], [6.5, 6.2], [10.8, 10.8], [6.4, 10.6], [0.7, 10.8], [3.2, 10.9]];
  const bench = (x, y) => box(P, x, y, 0, 0.9, 0.35, 6, "wood");
  const items = [];
  for (const [x, y] of decor) items.push({ k: x + y, s: cone(P, x, y, 0, 11, 40 + ((x * 7) % 3) * 6) });
  items.push({ k: 14, s: bench(6.4, 7.4) }, { k: 14.2, s: bench(10.2, 7.3) });
  for (const p of store.projects) { const b = LAYOUT[p.id]; items.push({ k: b.x + b.y + b.w + b.d, s: buildingSvg(P, p) }); }
  items.sort((a, b) => a.k - b.k);
  g += items.map((i) => i.s).join("");
  const withVan = store.projects.find((p) => p.van);
  if (withVan) g += vehicle(P, withVan);

  root.innerHTML = `<div class="stage"><svg viewBox="0 0 1200 680" preserveAspectRatio="xMidYMid meet" role="img" aria-label="City of projects">${g}</svg></div>
    <div class="rail right">
      <div class="card"><h3>Projects</h3><ul class="list" id="projlist">${store.projects.map((p) => `
        <li data-id="${esc(p.id)}"><span class="live ${running(p) ? "on" : ""}"></span><div class="grow"><div class="t">${esc(p.name)}</div><div class="s">${esc(p.tagline)}</div></div>
        <span class="badge ${p.pending.length ? "" : "zero"}" title="open decisions">${p.pending.length}</span></li>`).join("")}</ul></div>
      <div class="card"><h3>Waiting for you <span class="count">${totals().open}</span></h3><ul class="list" id="waitlist">${store.projects.flatMap((p) => p.pending.map((x) => ({ p, x }))).map(({ p, x }) => `
        <li data-go="#/p/${esc(p.id)}/${esc(x.agent)}"><div class="grow"><div class="t">${esc(x.title)}</div><div class="s">${esc(p.name)} · ${esc(x.agent)} · ${esc(x.kind)}</div></div></li>`).join("")}</ul></div>
    </div>`;

  const byId = (id) => store.projects.find((p) => p.id === id);
  root.querySelectorAll(".building").forEach((el) => {
    const p = byId(el.dataset.id);
    const t = totals(p);
    tooltip(el, `<b>${esc(p.name)}</b><br>${esc(p.tagline)}<br>${p.pending.length} open decisions · ${t.working} agent${t.working === 1 ? "" : "s"} working<br><span class="muted">Click to enter</span>`);
    el.onclick = () => { hideTip(); ctx.go(`#/p/${p.id}`); };
    el.onkeydown = (e) => { if (e.key === "Enter") ctx.go(`#/p/${p.id}`); };
    el.addEventListener("pointerenter", () => renderTrack(p, (s) => ctx.taskPanel(p, s)));
  });
  root.querySelectorAll("#projlist li").forEach((li) => { li.onclick = () => ctx.go(`#/p/${li.dataset.id}`); });
  root.querySelectorAll("#waitlist li").forEach((li) => { li.onclick = () => ctx.go(li.dataset.go); });

  const van = root.querySelector(".van");
  if (van && withVan) {
    tooltip(van, `<b>Run ${withVan.van.run_id}</b><br>${esc(withVan.van.skill)}<br><span class="muted">Click for the run</span>`);
    const open = () => openPanel({
      title: `Run ${withVan.van.run_id}`, subtitle: `${withVan.name} · running now`,
      build(body) {
        const a = withVan.agents.find((x) => x.key === withVan.van.agent);
        body.innerHTML = kv([["Task", esc(withVan.van.title)], ["Skill", esc(withVan.van.skill)], ["Area agent", `${esc(a.name)} (${esc(a.key)})`], ["State", chip("running")], ["Where", "the eval container, on a copy of what may enter"], ["Brings back", "only what the path rule allows"]]);
      },
    });
    van.onclick = open; van.onkeydown = (e) => { if (e.key === "Enter") open(); };
  }
  const focus = store.projects.find(running) || store.projects[0];
  renderTrack(focus, (s) => ctx.taskPanel(focus, s));
}
