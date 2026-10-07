// Control room: skills with a band per model, costs by day and agent, connections.
import { projector, box, tile, poly, esc } from "./iso.js";
import { store, floorDef } from "./data.js";
import { chip, money } from "./ui.js";

const COLORS = ["#2f6bff", "#82a6ff", "#2fa39a", "#e0a53a", "#c76bb0", "#8c99ab"];

function backdrop() {
  const P = projector([420, 250], 64);
  let g = "";
  for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) g += tile(P, i, j, 1, 1, (i + j) % 2 ? "fl-a" : "fl-b");
  g += poly([P.p(0, 0, 0), P.p(0, 8, 0), P.p(0, 8, 170), P.p(0, 0, 170)], "wallA") + poly([P.p(0, 0, 0), P.p(8, 0, 0), P.p(8, 0, 170), P.p(0, 0, 170)], "wallB");
  const racks = [];
  for (let k = 0; k < 4; k++) racks.push({ k: 1 + k * 1.6, s: box(P, 0.3, 0.6 + k * 1.7, 0, 0.9, 1.3, 110, "ink") });
  for (let k = 0; k < 3; k++) racks.push({ k: 1.8 + k * 1.6, s: box(P, 2.2 + k * 1.7, 0.3, 0, 1.3, 0.9, 110, "ink") });
  let lights = "";
  racks.forEach((r) => (g += r.s));
  for (let k = 0; k < 4; k++) for (let r = 0; r < 6; r++) {
    const [x, y] = P.p(1.2, 0.6 + k * 1.7 + 1.3, 14 + r * 16);
    lights += `<circle cx="${x - 22}" cy="${y + (r % 2 ? 1 : 0) - 12}" r="2.2" class="${(k + r) % 3 ? "win on" : "win work"}" style="animation-delay:${(k * 6 + r) * 0.17}s"/>`;
  }
  g += lights;
  g += box(P, 3.2, 4.4, 0, 3, 1.2, 30, "wood") + box(P, 3.8, 4.6, 30, 1.2, 0.14, 26, "ink");
  return `<svg viewBox="0 0 1200 600" preserveAspectRatio="xMinYMid meet" aria-hidden="true">${g}</svg>`;
}

function costsChart(c) {
  const keys = Object.keys(c.by_agent), n = c.days.length;
  const totals = c.days.map((_, d) => keys.reduce((m, k) => m + c.by_agent[k][d], 0));
  const max = Math.ceil(Math.max(...totals));
  const W = 440, Hh = 190, left = 34, bottom = 22, bw = 30, gap = (W - left - 8 - bw * n) / (n - 1);
  let s = "";
  for (let t = 0; t <= max; t++) { const y = Hh - bottom - ((Hh - bottom - 12) * t) / max; s += `<line x1="${left}" x2="${W}" y1="${y}" y2="${y}" stroke="#e3eaf2"/><text x="${left - 6}" y="${y + 3}" text-anchor="end" font-size="9" fill="#66768a">$${t}</text>`; }
  c.days.forEach((day, d) => {
    let acc = 0; const x = left + 6 + d * (bw + gap);
    keys.forEach((k, i) => {
      const v = c.by_agent[k][d]; if (!v) return;
      const h = ((Hh - bottom - 12) * v) / max, y = Hh - bottom - ((Hh - bottom - 12) * (acc + v)) / max;
      s += `<rect x="${x}" y="${y}" width="${bw}" height="${h}" fill="${COLORS[i]}" rx="2"><title>${esc(floorDef(k).label)} ${esc(day)}: ${money(v)}</title></rect>`; acc += v;
    });
    s += `<text x="${x + bw / 2}" y="${Hh - 6}" text-anchor="middle" font-size="9" fill="#66768a">${esc(day.slice(5))}</text>`;
  });
  const legend = keys.map((k, i) => `<span><i style="background:${COLORS[i]}"></i>${esc(floorDef(k).label)} ${money(c.by_agent[k].reduce((a, b) => a + b, 0))}</span>`).join("");
  return `<svg viewBox="0 0 ${W} ${Hh}" width="100%" role="img" aria-label="Cost by day and agent">${s}</svg><div class="legend">${legend}</div>`;
}

export function render(root) {
  const c = store.control;
  const skills = `<div class="card skills-card"><h3>Skills and the proof under them</h3><div class="hint" style="margin-bottom:8px">The band each skill has on each model, with its pessimistic score. Only the reference model's band decides what a skill may do.</div>
    <table class="bands"><thead><tr><th>Skill</th><th>Area</th>${c.models.map((m) => `<th>${esc(m.label)}</th>`).join("")}</tr></thead><tbody>
    ${c.skills.map((s) => `<tr><td><b>${esc(s.skill)}</b></td><td class="muted">${esc(s.area)}</td>${c.models.map((m) => { const x = s.models[m.key]; return `<td>${chip(x.band)}<small>${x.pessimistic.toFixed(2)} · ${x.runs} runs</small></td>`; }).join("")}</tr>`).join("")}
    </tbody></table></div>`;
  const costs = `<div class="card"><h3>Costs by day and agent</h3>${costsChart(c.costs)}</div>`;
  const k = c.connections;
  const conn = `<div class="card"><h3>Connections</h3>
    <h4>Requirement classes</h4><div class="conn">${k.classes.map((x) => `<code>${esc(x.class)}</code><span>${chip(x.state)} <span class="muted">${esc(x.provider || "no provider")}</span></span>`).join("")}</div>
    <h4>Secrets, by name only</h4><div class="conn">${k.secrets.map((x) => `<code>${esc(x.name)}</code><span>${chip(x.state)} <span class="muted">${esc(x.where || "not set")}</span></span>`).join("")}</div>
    <h4>Eval container</h4><div class="conn"><code>${esc(k.image.name)}</code><span>${chip(k.image.present ? "found" : "missing")} <span class="muted">built ${esc(k.image.built)}</span></span></div></div>`;
  root.innerHTML = `<div class="stage">${backdrop()}</div><div class="control">${skills}${costs}${conn}</div>`;
}
