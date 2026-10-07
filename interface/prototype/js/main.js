// The app: loads the fake data, owns the view state, draws the HTML around the 3D world, routes picks.
import { h, $, clear, toast, money } from "./dom.js";
import { World, W, D } from "./scene.js";
import * as P from "./panels.js";

const FILES = ["projects", "pending", "documents", "document-texts", "chat", "chains", "control"];

async function load() {
  const out = {};
  await Promise.all(FILES.map(async (f) => { out[f] = await (await fetch(`data/${f}.json`)).json(); }));
  return out;
}

const webgl = (() => { try { return !!document.createElement("canvas").getContext("webgl2"); } catch { return false; } })();
if (!webgl) { $("#fallback").hidden = false; throw new Error("no WebGL"); }

const data = await load();
const world = new World($("#scene"), data);
const state = { view: "city", pid: null, agent: null, tab: "agent", doc: null, docScope: "floor", panelOpen: false, chainPid: data.projects.projects[0].id, ctlTab: "skills", skillFilter: "" };
const chats = {};

const ctx = {
  data, state, render: () => render(), go: (v, o) => go(v, o),
  pendingFor(pid, agent) { return data.pending.pending.filter((x) => (!pid || x.project === pid) && (!agent || x.agent === agent)); },
  chat(pid) { return (chats[pid] ||= [...(data.chat[pid]?.messages || [])]); },
};
const project = (pid) => data.projects.projects.find((p) => p.id === pid);
const agentOf = (pid, id) => project(pid).agents.find((a) => a.id === id);

// ------------------------------------------------------------------ navigation
function go(view, o = {}) {
  state.view = view;
  if (view === "city") { state.pid = null; state.agent = null; }
  if (view === "building") { state.pid = o.pid ?? state.pid; state.agent = null; }
  if (view === "floor") { state.pid = o.pid ?? state.pid; state.agent = o.agent ?? state.agent; }
  if (view === "control") { state.pid = null; state.agent = null; }
  if (view === "floor") { state.tab = o.tab || (state.agent === "planning" ? "chat" : "agent"); state.doc = o.doc || null; }
  state.panelOpen = view !== "city";
  if (state.pid) state.chainPid = state.pid;
  world.setView(view, { pid: state.pid, agent: state.agent });
  try { history.replaceState(null, "", "#" + [view === "city" ? "" : view === "control" ? "control" : state.pid, state.agent].filter(Boolean).join("/")); } catch { /* file: or sandbox */ }
  render();
}
function back() {
  if (state.view === "floor") { if (state.doc) { state.doc = null; render(); } else go("building", { pid: state.pid }); }
  else if (state.view === "building" || state.view === "control") go("city");
}

// ------------------------------------------------------------------ render
function render() {
  renderCrumbs(); renderKpis(); renderPanel(); renderList(); renderChain(); buildLabels();
}

function renderCrumbs() {
  const el = clear($("#crumbs"));
  const crumbs = [["City", () => go("city"), state.view === "city"]];
  if (state.view === "control") crumbs.push(["Control room", null, true]);
  if (state.pid) crumbs.push([state.pid, () => go("building", { pid: state.pid }), state.view === "building"]);
  if (state.agent) crumbs.push([P.areaName(state.agent), null, true]);
  el.append(h("button", { class: "back", type: "button", title: "Back (Escape)", disabled: state.view === "city", onclick: back }, "←"));
  crumbs.forEach(([t, fn, last], i) => {
    if (i) el.append(h("span", { class: "sep" }, ">"));
    el.append(h("button", { class: "crumb", type: "button", disabled: last, onclick: fn || undefined }, t));
  });
}

function renderKpis() {
  const ps = state.pid ? [project(state.pid)] : data.projects.projects;
  const agents = ps.flatMap((p) => p.agents);
  const decisions = ctx.pendingFor(state.pid).length;
  const runs = agents.reduce((s, a) => s + a.used_today.runs, 0), runCap = agents.filter((a) => a.enabled).reduce((s, a) => s + a.max_runs_per_day, 0);
  const spend = agents.reduce((s, a) => s + a.used_today.usd, 0);
  const cap = state.pid ? agents.filter((a) => a.enabled).reduce((s, a) => s + a.max_usd_per_day, 0) : data.projects.daily_cap_usd;
  const working = agents.filter((a) => a.state === "working").length;
  const el = clear($("#kpis"));
  const k = (l, v, sub, bar) => h("div", { class: "kpi" }, h("div", { class: "l" }, l), h("div", { class: "v" }, v, sub && h("small", {}, " " + sub)), bar !== undefined && h("div", { class: "bar" }, h("i", { style: `width:${Math.min(100, bar * 100)}%` })));
  el.append(k("Open decisions", String(decisions), "waiting for you"), k("Runs today", String(runs), `of ${runCap}`, runs / runCap),
    k("Spend today", money(spend), `of ${money(cap)} cap`, spend / cap), k("Agents working", String(working), state.pid ? "in this project" : "across projects"));
}

function renderPanel() {
  const el = $("#panel"); clear(el);
  const open = state.panelOpen;
  el.hidden = !open;
  el.classList.toggle("wide", state.view === "control");
  if (!open) { world.setPanelOffset(0); return; }
  const close = h("button", { class: "x", type: "button", title: "Close", onclick: () => { state.panelOpen = false; render(); } }, "×");
  let title, sub, body, tabs = null;
  if (state.view === "building") {
    const p = project(state.pid); title = p.title; sub = "Project - an office building, one floor per area agent"; body = P.buildingPanel(p, ctx);
  } else if (state.view === "control") {
    title = "Control room"; sub = "Skills, costs and connections of this machine";
    const t = [["skills", "Skills"], ["costs", "Costs"], ["connections", "Connections"]];
    tabs = h("div", { class: "tabs" }, t.map(([id, l]) => h("button", { class: "tab" + (state.ctlTab === id ? " on" : ""), type: "button", onclick: () => { state.ctlTab = id; render(); } }, l)));
    body = P.controlPanel(ctx);
  } else if (state.view === "floor") {
    const p = project(state.pid), a = agentOf(state.pid, state.agent);
    title = `${P.areaName(a.id)} - ${a.name}`; sub = `${p.title} - floor ${p.agents.indexOf(a)}`;
    const n = ctx.pendingFor(p.id, a.id).length, nd = (data.documents[p.id] || []).filter((d) => a.id === "planning" || d.agent === a.id).length;
    const t = [...(a.id === "planning" ? [["chat", "Conversation"]] : []), ["agent", "Agent"], ["inbox", "Inbox", n], ["docs", "Documents", nd]];
    tabs = h("div", { class: "tabs" }, t.map(([id, l, c]) => h("button", { class: "tab" + (state.tab === id ? " on" : ""), type: "button", onclick: () => { state.tab = id; state.doc = null; render(); } }, l, c ? h("span", { class: "n" }, String(c)) : null)));
    body = state.tab === "chat" ? P.chatTab(p, ctx) : state.tab === "inbox" ? P.inboxTab(p, a, ctx) : state.tab === "docs" ? P.docsTab(p, a, ctx) : P.agentTab(p, a, ctx);
  }
  el.append(h("div", { class: "head" }, h("div", {}, h("h2", {}, title), h("div", { class: "sub" }, sub)), close), ...(tabs ? [tabs] : []), h("div", { class: "body" }, body));
  world.setPanelOffset(el.classList.contains("wide") ? 720 : 420);
}

function renderList() {
  const el = $("#list"); clear(el);
  const items = ctx.pendingFor(state.pid);
  el.hidden = state.panelOpen || !items.length;
  if (el.hidden) return;
  el.append(h("h3", {}, h("span", {}, "Waiting for you"), h("span", { class: "badge" }, String(items.length))),
    ...items.sort((a, b) => a.created_at.localeCompare(b.created_at)).map((x) =>
      h("div", { class: "row click", onclick: () => go("floor", { pid: x.project, agent: x.agent, tab: "inbox" }) },
        h("span", { class: "chip " + ({ effect: "red", question: "amber", review: "blue", acceptance: "green", plan: "blue" }[x.kind] || "") }, x.kind),
        h("div", { class: "grow" }, h("div", { class: "t" }, x.title), h("div", { class: "s" }, h("span", { class: "proj" }, x.project), ` - ${P.areaName(x.agent)}`)))));
}

function renderChain() {
  const el = clear($("#chain"));
  const chain = data.chains[state.chainPid];
  const pills = state.view === "city" || state.view === "control"
    ? data.projects.projects.map((p) => h("button", { class: "pill" + (p.id === state.chainPid ? " on" : ""), type: "button", onclick: () => { state.chainPid = p.id; renderChain(); } }, p.id))
    : [h("span", { class: "pill on" }, state.chainPid)];
  el.append(h("div", { class: "top" }, h("b", {}, `Request #${chain.request_id}: ${chain.title}`), ...pills,
    h("span", { class: "muted s", style: "margin-left:auto" }, `${chain.steps.filter((s) => s.state === "done").length} of ${chain.steps.length} steps done`)),
    h("div", { class: "steps" }, chain.steps.map((s) => h("div", {
      class: `step ${s.state}` + (state.agent === s.agent && state.pid === state.chainPid ? " here" : ""), title: `task #${s.id} - ${s.skill}`,
      onclick: () => go("floor", { pid: state.chainPid, agent: s.agent, tab: ctx.pendingFor(state.chainPid, s.agent).length && s.state === "waiting" ? "inbox" : "agent" }),
    }, h("div", { class: "node" }, s.state === "done" ? "✓" : ""), h("div", { class: "nm" }, s.title), h("div", { class: "st" }, `${P.areaName(s.agent)} - ${s.state}`)))));
}

// ------------------------------------------------------------------ labels that follow the 3D objects
let labels = [];
function buildLabels() {
  const layer = clear($("#labels")); labels = [];
  const add = (el, anchor, dx = 0, dy = 0) => { layer.append(el); labels.push({ el, anchor, dx, dy }); };
  if (state.view === "city") {
    for (const p of data.projects.projects) {
      const n = ctx.pendingFor(p.id).length;
      add(h("div", { class: "label plabel", onclick: () => go("building", { pid: p.id }) },
        h("div", { class: "n" }, p.id, n > 0 && h("span", { class: "badge", title: "open decisions" }, String(n))),
        h("div", { class: "s" }, h("span", { class: "dot " + (p.running_task_id ? "running" : "idle") }), p.running_task_id ? `task #${p.running_task_id} running` : "no task running")),
      () => world.anchor("roof", p.id), -75, -60);
    }
  } else if (state.view === "building") {
    const p = project(state.pid);
    for (const a of p.agents) {
      const n = ctx.pendingFor(p.id, a.id).length;
      add(h("div", { class: "label fchip" + (a.enabled ? "" : " off"), onclick: () => go("floor", { pid: p.id, agent: a.id }) },
        h("div", { class: "n" }, h("span", { class: "dot " + a.state }), P.areaName(a.id), n > 0 && h("span", { class: "badge" }, String(n)), h("span", { class: "lamp" }, a.enabled ? "lights on" : "lights off")),
        h("div", { class: "m" }, P.modePlate(a.mode)),
        h("div", { class: "u" }, h("div", {}, h("div", {}, `runs ${a.used_today.runs} / ${a.max_runs_per_day}`), meterEl(a.used_today.runs, a.max_runs_per_day)),
          h("div", {}, h("div", {}, `${money(a.used_today.usd)} / ${money(a.max_usd_per_day)}`), meterEl(a.used_today.usd, a.max_usd_per_day)))),
      () => world.anchor("chip", p.id, a.id), 12, -48);
    }
  } else if (state.view === "floor") {
    const p = project(state.pid), a = agentOf(state.pid, state.agent);
    add(h("div", { class: "label bubble" },
      h("div", { class: "n" }, h("span", { class: "dot " + a.state }), a.enabled ? (a.task ? a.task.title : "Idle") : "Off"),
      h("div", { class: "s" }, a.task ? [`skill `, h("span", { class: "mono" }, a.task.skill), ` - run ${a.task.state}`] : a.enabled ? "waiting for the next task" : "mode is stopped")),
    () => world.anchor("agent", p.id, a.id), -115, -92);
    if (a.id === "planning") add(h("div", { class: "label doorlabel", onclick: () => go("control") }, "Control room →"), () => world.anchor("door", p.id, a.id), -50, -34);
  }
  updateLabels();
}
const meterEl = (u, c) => h("div", { class: "meter" + (c > 0 && u / c >= 0.8 ? " warn" : "") }, h("i", { style: `width:${c > 0 ? Math.min(100, (u / c) * 100) : 0}%` }));
function updateLabels() {
  for (const l of labels) {
    const s = world.screen(l.anchor());
    l.el.classList.toggle("hidden", s.behind);
    l.el.style.transform = `translate(${Math.round(s.x + l.dx)}px, ${Math.round(s.y + l.dy)}px)`;
  }
}
world.onFrame = updateLabels;

// ------------------------------------------------------------------ pointer and keyboard
const canvas = $("#scene"), tip = $("#tip");
let hovered = null;
function describe(pk) {
  if (!pk) return null;
  if (pk.type === "project") return `${pk.id} - click to enter`;
  if (pk.type === "floor") return `${P.areaName(pk.agent)} - click to enter`;
  if (pk.type === "doc") return pk.label;
  if (pk.type === "inbox") return `Inbox: ${pk.count} waiting`;
  if (pk.type === "cabinet") return "Documents (open the list)";
  if (pk.type === "door") return "Control room";
  if (pk.type === "agent") return "The agent: open its card";
  return null;
}
canvas.addEventListener("pointermove", (e) => {
  const pk = world.pick(e.clientX, e.clientY);
  hovered = pk;
  world.outline(pk);
  canvas.style.cursor = pk ? "pointer" : "default";
  const t = describe(pk);
  tip.hidden = !t;
  if (t) { tip.textContent = t; tip.style.left = e.clientX + "px"; tip.style.top = e.clientY + "px"; }
});
canvas.addEventListener("pointerleave", () => { tip.hidden = true; world.outline(null); });
canvas.addEventListener("click", (e) => {
  const pk = world.pick(e.clientX, e.clientY);
  if (!pk) return;
  tip.hidden = true;
  if (pk.type === "project") go("building", { pid: pk.id });
  else if (pk.type === "floor") go("floor", { pid: pk.pid, agent: pk.agent });
  else if (pk.type === "door") go("control");
  else if (pk.type === "doc") { state.tab = "docs"; state.doc = pk.path; state.panelOpen = true; render(); }
  else if (pk.type === "cabinet") { state.tab = "docs"; state.doc = null; state.panelOpen = true; render(); }
  else if (pk.type === "inbox") { state.tab = "inbox"; state.doc = null; state.panelOpen = true; render(); }
  else if (pk.type === "agent") { state.tab = "agent"; state.doc = null; state.panelOpen = true; render(); }
});
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !(e.target instanceof HTMLInputElement && e.target.value)) { e.preventDefault(); back(); }
});
$("#btn-control").addEventListener("click", () => go("control"));
window.addEventListener("resize", () => { world.resize(); });

// ------------------------------------------------------------------ start
function fromHash() {
  const [a, b] = decodeURIComponent(location.hash.slice(1)).split("/");
  if (a === "control") return go("control");
  if (a && project(a)) return b && agentOf(a, b) ? go("floor", { pid: a, agent: b }) : go("building", { pid: a });
  go("city");
}
fromHash();
world.snapCamera(true);
window.addEventListener("hashchange", fromHash);
window.__world = world; window.__go = go; window.__state = state;
