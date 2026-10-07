// Shared HTML pieces laid over the scene: top bar, KPI cards, side panel, toast, tracking bar, cards.
import { esc } from "./iso.js";
import { store, totals, money, relTime, bandOf } from "./data.js";

const $ = (id) => document.getElementById(id);

// --- toast -----------------------------------------------------------------------------------------------------
let toastTimer = null;
export function toast(text) {
  const el = $("toast");
  el.textContent = text;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3600);
}

// What the page would call: the operations of runtime/operations.py, with the arguments of the card.
export function wouldCall(op, args) {
  const body = Object.entries(args).map(([k, v]) => `${k}=${typeof v === "number" ? v : `'${String(v).slice(0, 18)}${String(v).length > 18 ? "..." : ""}'`}`).join(", ");
  return `would call ${op}(${body})`;
}

// --- top bar ---------------------------------------------------------------------------------------------------
export function renderTop(crumbs, scopeProject) {
  const bc = crumbs.map((c, i) => c.href && i < crumbs.length - 1
    ? `<a href="${c.href}">${esc(c.label)}</a>` : `<span class="here">${esc(c.label)}</span>`).join('<span class="sep">&rsaquo;</span>');
  const back = crumbs.length > 1 ? crumbs[crumbs.length - 2].href : null;
  $("breadcrumbs").innerHTML = `${back ? `<a class="back" href="${back}" title="Back (Escape)">&larr; Back</a>` : ""}<nav>${bc}</nav>`;

  const t = totals(scopeProject);
  const pct = Math.min(100, Math.round((t.usd / t.cap) * 100));
  const scope = scopeProject ? scopeProject.name : "all projects";
  $("kpis").innerHTML = `
    <div class="kpi"><div class="kpi-label">Open decisions</div><div class="kpi-value ${t.open ? "hot" : ""}">${t.open}</div><div class="kpi-sub">${esc(scope)}</div></div>
    <div class="kpi"><div class="kpi-label">Runs today</div><div class="kpi-value">${t.runs}<small> / ${t.runsCap}</small></div><div class="kpi-sub">${t.working} working now</div></div>
    <div class="kpi wide"><div class="kpi-label">Spend today</div><div class="kpi-value">${money(t.usd)}<small> of ${money(t.cap)}</small></div>
      <div class="meter"><i style="width:${pct}%"></i></div><div class="kpi-sub">${pct}% of the daily cap</div></div>`;
}

// --- side panel ------------------------------------------------------------------------------------------------
export function openPanel({ title, subtitle = "", build }) {
  const el = $("sidepanel");
  el.innerHTML = `<header><div><h2>${esc(title)}</h2><p>${esc(subtitle)}</p></div><button class="close" aria-label="Close panel">&times;</button></header><div class="body"></div>`;
  el.querySelector(".close").onclick = closePanel;
  build(el.querySelector(".body"));
  el.classList.add("open");
}
export function closePanel() { $("sidepanel").classList.remove("open"); }
export const panelOpen = () => $("sidepanel").classList.contains("open");

export function openDocument(doc) {
  openPanel({
    title: doc.path, subtitle: `Owner skill ${doc.owner} · modified ${relTime(doc.modified)}`,
    build(body) {
      const pre = document.createElement("pre");
      pre.className = "doctext";
      pre.textContent = doc.text; // plain text, never markup
      body.append(pre);
      const note = document.createElement("p");
      note.className = "hint";
      note.textContent = "Shown as plain text. In the runtime this is the project file as it is.";
      body.append(note);
    },
  });
}

export function kv(rows) {
  return `<dl class="kv">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("")}</dl>`;
}

export function openTask(p, step) {
  const band = bandOf(step.skill);
  openPanel({
    title: `Task ${step.id}: ${step.key}`, subtitle: `${p.name} · request ${p.request.id}`,
    build(body) {
      body.innerHTML = kv([
        ["State", chip(step.state)], ["Skill", esc(step.skill)], ["Area agent", esc(step.agent)],
        ["Note", esc(step.note || "none")],
        ["Proof (reference model)", band ? `${chip(band.band)} <span class="muted">pessimistic ${band.pessimistic}, ${band.runs} runs</span>` : "unknown"]]);
    },
  });
}

// --- small parts -----------------------------------------------------------------------------------------------
const CHIP_CLASS = {
  done: "ok", reliable: "ok", found: "ok", running: "accent", working: "accent", waiting: "warn", watch: "warn",
  blocked: "bad", failed: "bad", "needs a test": "bad", missing: "bad", ready: "neutral", idle: "neutral", todo: "neutral",
};
export const chip = (word) => `<span class="chip ${CHIP_CLASS[word] || "neutral"}">${esc(word)}</span>`;

export function bar(label, value, max, fmt = (v) => String(v)) {
  const pct = max ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return `<div class="usage"><span>${esc(label)}</span><div class="meter"><i style="width:${pct}%"></i></div><b>${fmt(value)} / ${fmt(max)}</b></div>`;
}

// --- tracking bar ----------------------------------------------------------------------------------------------
export function renderTrack(p, onStep) {
  const el = $("trackbar");
  if (!p || !p.request) { el.innerHTML = ""; el.classList.add("hidden"); return; }
  el.classList.remove("hidden");
  const r = p.request;
  el.innerHTML = `<div class="track-head"><b>Request ${r.id}</b> ${esc(r.title)} <span class="muted">· ${esc(p.name)} · flow ${esc(r.flow)}</span></div>
    <ol class="steps">${r.tasks.map((t, i) => `<li class="step s-${t.state}" data-i="${i}" tabindex="0" title="${esc(t.note)}">
      <span class="dot">${t.state === "done" ? "&#10003;" : i + 1}</span><span class="name">${esc(t.key)}</span><span class="st">${esc(t.state)}</span></li>`).join("")}</ol>`;
  el.querySelectorAll(".step").forEach((li) => {
    const go = () => onStep(r.tasks[Number(li.dataset.i)]);
    li.onclick = go; li.onkeydown = (e) => { if (e.key === "Enter") go(); };
  });
}

// --- tooltip ---------------------------------------------------------------------------------------------------
export function tooltip(el, html) {
  const tip = $("tooltip");
  const move = (e) => { tip.style.left = `${Math.min(e.clientX + 16, innerWidth - 270)}px`; tip.style.top = `${Math.min(e.clientY + 16, innerHeight - 140)}px`; };
  el.addEventListener("pointerenter", (e) => { tip.innerHTML = html; tip.classList.add("show"); move(e); });
  el.addEventListener("pointermove", move);
  el.addEventListener("pointerleave", () => tip.classList.remove("show"));
}
export const hideTip = () => $("tooltip").classList.remove("show");
export { money } from "./data.js";
