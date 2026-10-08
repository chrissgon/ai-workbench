// What the City shows, worked out from what the service returned: pure functions with no document and no network, so
// they run under a test. The inputs are the bodies of the service's reads, kept in one snapshot:
//   projects  the `projects` list: [{id, name, config: {accepted}, message?, open_pending?, running_task?}]
//   details   {[projectId]: {status, agents}}: the `status` body (its task rows carry `title` and `agent`, its pending
//             decisions carry `agent`) and the `agents` array of an accepted project
//   tasks     {["<projectId>:<taskId>"]: the `task` body {task, runs, pending}}: only the running task of the followed
//             project's open request, for the time its run started (`status` has no run)
// Nothing is decided here: a count is a count of what came, a state is the service's own word. A decision on a request
// (a plan, a router question) and a request itself have no agent: they belong to the planning agent, the Lobby.

import * as format from "./format.js";
import * as router from "./router.js";

export const MAX_LOTS = 4;       // at most four lots are drawn (EDGE-9); the rest are reached from the lists
export const MAX_FLOORS = 8;
const FINAL = new Set(["done", "cancelled"]);

/** The key of a task in the snapshot's `tasks`. */
export function taskKey(project, id) {
  return `${project}:${id}`;
}

/** The agents of a project in floor order: the planning agent first (the Lobby, floor 0), then the others in the order given. */
export function floorsOf(agents) {
  const list = Array.isArray(agents) ? agents : [];
  const planning = list.filter((a) => a && a.name === "planning");
  const others = list.filter((a) => a && a.name !== "planning");
  return [...planning, ...others].slice(0, MAX_FLOORS);
}

/** The number a floor is called: the planning agent is floor 0 when there is one, else the first agent is floor 1. */
export function floorNumber(ordered, name) {
  const index = ordered.findIndex((a) => a.name === name);
  if (index < 0) return null;
  return ordered.some((a) => a.name === "planning") ? index : index + 1;
}

/** Every row of every request of a status body: the requests and their tasks, each as {id, state, ...}. */
function rowsOf(status) {
  const out = [];
  for (const request of (status && Array.isArray(status.requests)) ? status.requests : []) {
    out.push({ ...request, tasks: undefined, request: true });
    for (const t of Array.isArray(request.tasks) ? request.tasks : []) out.push({ ...t, request: false, requestId: request.id });
  }
  return out;
}

/** The newest request that is not final (done or cancelled) of a status body, or null. */
export function openRequest(status) {
  const open = (status && Array.isArray(status.requests) ? status.requests : []).filter((r) => !FINAL.has(r.state));
  if (!open.length) return null;
  return open.reduce((a, b) => (b.id > a.id ? b : a));
}

/** The tasks whose `task` body the page needs: {project, id, state}. Only the running task of the followed project's open request (its run's start time). */
export function neededTasks(projects, details, followed) {
  const wanted = [];
  for (const p of projects) {
    if (p.id !== followed) continue;
    const request = openRequest(details[p.id] && details[p.id].status);
    const running = request && (request.tasks || []).find((t) => t.state === "running");
    if (running) wanted.push({ project: p.id, id: running.id, state: running.state });
  }
  return wanted;
}

/** The decisions of one project, each with the agent that owns it ("planning" for a decision on a request). */
function decisionsOf(status) {
  return (Array.isArray(status && status.pending) ? status.pending : []).map((item) => ({ item, agent: item.agent || "planning" }));
}

/** One building of the City from a project, its status, its agents and the loaded tasks. */
export function buildingOf(project, detail) {
  const accepted = Boolean(project.config && project.config.accepted) && !(detail && detail.error && detail.error.status === 412);
  const ordered = floorsOf(detail && detail.agents);
  const status = detail && detail.status;
  const decided = decisionsOf(status);
  const running = new Set();
  for (const r of rowsOf(status)) {
    if (r.state !== "running") continue;
    running.add(r.request ? "planning" : r.agent || "planning");
  }
  const waits = new Set(decided.map((d) => d.agent));
  const floors = (ordered.length ? ordered : [{ name: null, enabled: true, acting_mode: null }]).map((a) => {
    let window = "pale";
    if (!accepted) window = "dark";
    else if (a.name && running.has(a.name)) window = "lit";
    else if (a.enabled === false || a.acting_mode === "stopped") window = "dark";
    return { agent: a.name, window, waits: accepted && (a.name ? waits.has(a.name) : decided.length > 0) };
  });
  const open = !accepted ? 0 : status ? decided.length : format.count(project.open_pending);
  const runningTask = accepted && project.running_task !== null && project.running_task !== undefined ? project.running_task : null;
  return { id: project.id, name: project.name, accepted, floors, decisions: open, runningTask, message: project.message || "" };
}

/** The tooltip sentence of a building (the specification's). */
export function tooltipOf(building) {
  if (!building.accepted) return `${building.name}: not accepted yet`;
  const running = building.runningTask === null ? "no task running" : `task #${building.runningTask} running`;
  return `${building.name}: ${format.decisions(building.decisions)} waiting, ${running}`;
}

/** The sub line of a building's label card. */
export function subOf(building) {
  if (!building.accepted) return "not accepted yet";
  return building.runningTask === null ? "no task running" : `task #${building.runningTask} running`;
}

/** The name a link to a building carries for a screen reader. */
export function linkNameOf(building) {
  if (!building.accepted) return `${building.name}, not accepted yet`;
  return `${building.name}, ${format.decisions(building.decisions)} waiting, ${building.runningTask === null ? "no task running" : `task #${building.runningTask} running`}`;
}

/** The City's data in one value: its buildings, the waiting rows and the canvas label. */
export function city(snapshot, now) {
  const projects = Array.isArray(snapshot.projects) ? snapshot.projects : [];
  const buildings = projects.map((p) => buildingOf(p, snapshot.details[p.id]));
  const waiting = waitingRows(snapshot, now);
  const canvasLabel = projects.length
    ? `City with ${projects.length} project${projects.length === 1 ? "" : "s"}, ${waiting.length} decision${waiting.length === 1 ? "" : "s"} waiting`
    : "City with no project";
  return { buildings, waiting, canvasLabel };
}

/** The sums the three KPI cards show for one scope: `projectId` null is every project (the City). */
export function kpiSums(snapshot, projectId) {
  const projects = (snapshot.projects || []).filter((p) => projectId === null || p.id === projectId);
  const sums = { decisions: 0, runs: 0, runsCap: 0, usd: 0, usdCap: 0 };
  for (const p of projects) {
    const detail = snapshot.details[p.id];
    sums.decisions += detail && detail.status ? (detail.status.pending || []).length : 0;
    for (const a of (detail && Array.isArray(detail.agents)) ? detail.agents : []) {
      sums.runs += format.count(a.runs_today);
      sums.runsCap += format.count(a.max_runs_per_day);
      sums.usd += format.count(a.usd_today);
      sums.usdCap += format.count(a.max_usd_per_day);
    }
  }
  return sums;
}

/** The rows of "Waiting for you": every open decision of the given projects (all when `only` is null), oldest first. */
export function waitingRows(snapshot, now, only = null) {
  const rows = [];
  for (const p of snapshot.projects || []) {
    if (only !== null && p.id !== only) continue;
    const status = snapshot.details[p.id] && snapshot.details[p.id].status;
    for (const { item, agent } of decisionsOf(status)) {
      const lobby = agent === "planning";
      const link = lobby ? router.lobbyHash(p.id, "inbox", item.id) : router.floorHash(p.id, agent, "inbox", item.id);
      const kind = format.kindWord(item.kind);
      const where = `${p.name} · ${format.agentWord(agent)}`;
      rows.push({
        project: p.id, id: item.id, kind, title: item.title || "", where, link, createdAt: item.created_at || "",
        age: format.age(item.created_at, now),
        name: `${kind}, ${item.title || ""}, ${p.name}, ${format.agentWord(agent)}${item.created_at ? `, waiting ${format.ageWords(item.created_at, now)}` : ""}`,
      });
    }
  }
  rows.sort((a, b) => (a.createdAt < b.createdAt ? -1 : a.createdAt > b.createdAt ? 1 : a.id - b.id));
  return rows;
}

/** The steps of a request and what is "Now on": {request, steps, doneCount, now}, or null when no request is open. */
export function tracking(snapshot, projectId, now) {
  const project = (snapshot.projects || []).find((p) => p.id === projectId);
  const detail = project && snapshot.details[project.id];
  const request = detail ? openRequest(detail.status) : null;
  if (!project || !request) return null;
  const ordered = floorsOf(detail.agents);
  const tasks = request.tasks || [];
  const steps = tasks.map((t) => {
    const agent = t.agent || null;               // null: the project has no area agents
    const title = t.title || t.key;
    const word = agent ? format.agentWord(agent) : "";
    return {
      id: t.id, state: t.state, title, agent,
      sub: word ? `${word} · ${t.state}` : t.state,
      link: !agent || agent === "planning" ? router.lobbyHash(project.id) : router.floorHash(project.id, agent),
      name: `${title}, ${word ? `${word}, ` : ""}${t.state}`,
    };
  });
  const current = steps.find((s) => s.state === "running") || steps.find((s) => s.state === "waiting") || null;
  let nowCard = null;
  if (current) {
    const body = snapshot.tasks[taskKey(project.id, current.id)];
    const floor = current.agent ? floorNumber(ordered, current.agent) : null;
    const running = current.state === "running";
    const runs = (body && Array.isArray(body.runs)) ? body.runs : [];
    const started = runs.length ? format.clock(runs[runs.length - 1].started_at) : "";
    const open = (detail.status.pending || []).filter((p) => p.task_id === current.id).length;
    nowCard = {
      where: `${running ? "Now on" : "Waiting on"}${floor === null ? "" : ` floor ${floor}`}${current.agent ? ` · ${current.agent === "planning" ? "lobby" : current.agent}` : ""}`,
      title: current.title, state: running ? "Running" : "Waiting for you", running,
      sub: `task #${current.id}${running ? (started ? ` · since ${started}` : "") : ` · ${format.decisions(open)}`}`,
      link: current.link,
    };
  }
  return {
    request: { id: request.id, title: request.title || "", state: request.state, project: project.name },
    steps, doneCount: tasks.filter((t) => t.state === "done").length, total: tasks.length, now: nowCard,
  };
}

/** The sub line of a project in the switcher: "Request #14 · 2 of 6 steps done", "No request is open" or "..." while unknown. */
export function projectSub(snapshot, projectId) {
  const project = (snapshot.projects || []).find((p) => p.id === projectId);
  if (!project) return "";
  if (!(project.config && project.config.accepted)) return "Not accepted";
  const detail = snapshot.details[projectId];
  if (!detail || !detail.status) return "...";
  const request = openRequest(detail.status);
  if (!request) return "No request is open";
  const tasks = request.tasks || [];
  return `Request #${request.id} · ${tasks.filter((t) => t.state === "done").length} of ${tasks.length} steps done`;
}

/** What the scene needs of the City: the first four buildings in a plain shape, with the id of the selected one; `ready` is false while the first read is loading (nothing arrives then). */
export function sceneModel(buildings, selectedId, ready = true) {
  return {
    selectedId, ready,
    lots: buildings.slice(0, MAX_LOTS).map((b) => ({
      id: b.id, name: b.name, accepted: b.accepted, decisions: b.decisions, runningTask: b.runningTask,
      floors: b.floors.map((f) => ({ window: f.window, waits: f.waits })),
      tip: tooltipOf(b), sub: subOf(b),
    })),
  };
}

/** The state of a screen's data: "loading" before the first read has answered, "error" when it failed and nothing was ever read, else "ready" (a later failure keeps the last data, dimmed). */
export function screenState(snapshot, failure) {
  if (snapshot.loaded) return "ready";
  return failure ? "error" : "loading";
}

/** Whether the City says the service has no project: only when a read answered and the list was empty. */
export function emptyCityVisible(state, buildingCount) {
  return state === "ready" && buildingCount === 0;
}
