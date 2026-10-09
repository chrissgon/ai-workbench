// The Tasks tab of a floor (adjustment A-8; handoff floor.md and lobby.md, "Tasks tab"): every task of the project whose agent is
// this floor's, in groups by state (running, waiting for you, ready, planned or blocked, done, failed, cancelled), each group with
// its count. A row shows the number, the title, the skill, the state, the request, the age and the actions its state allows: Retry
// on a failed or blocked task, "Open in the Inbox" when a decision waits. A done task shows the paths it returned (each with
// "Open" under docs/); a failed one its failure word and the ending of its last run. A row expands into the task's runs, the block
// the Agent tab draws for its current task. The rows come from `status`; `task` is read for the first twelve rows while the tab is
// open (the failed ones first, then the done ones, then the rest, since their failure and their paths are only in the body) and for a row
// when it is expanded. A body is kept until the page's reload stamp moves (the store changed) or the task's state changes. Every value is text. The one write is Retry, sent through
// the client the view hands in (floor/actions.js), never through a client of this file.

import * as client from "../api.js";
import { fill, h } from "../dom.js";
import { arrowNav } from "../frame/arrows.js";
import { runBlock } from "./run-block.js";
import { groupTasks, rowOf } from "./tasks-model.js";
import { busyLine, chip, errorText, notice, ring } from "./widgets.js";

const MAX_READS = 12;       // the first rows read without being expanded (the Inbox reads twelve too)
export const NONE_TEXT = "This agent has no task yet.";

/** Run `render`, then put the keyboard focus back on the control with the same `data-key` when it was inside `container`. */
function keepFocus(container, render) {
  const active = document.activeElement;
  const key = active && container.contains(active) && active.getAttribute ? active.getAttribute("data-key") : null;
  render();
  if (!key) return;
  const next = [...container.querySelectorAll("[data-key]")].find((n) => n.getAttribute("data-key") === key);
  if (next && next.focus) next.focus({ preventScroll: true });
}

/**
 * Create the tab. env: {project, now() (a Date), refresh() (read the page's data again), api: {retry} (floor/actions.js),
 * links: {request(requestId), inbox(pendingId or null), open(path)} (hashes built with the router)}.
 * Returns {el, update({tasks, requests, pending, loading})}: tasks are floor-model.agentTasks(...) rows, requests and pending
 * the status's, loading true before the first read.
 */
export function createTasksTab(env) {
  const el = h("div", { class: "wb-tasks-tab" });
  const groupsBox = h("div", { class: "wb-tasks-groups" });
  arrowNav(groupsBox, "button.wb-task-toggle");
  let last = { tasks: [], requests: [], pending: [], loading: true };
  const bodies = new Map();        // task id -> {body, state, at}
  const reading = new Set();
  const expanded = new Set();
  const opened = new Map();        // group id -> the person's choice, over "open when it holds a task"
  const retrying = new Set();
  const retryError = new Map();
  let shown = "";
  let reloaded = null;             // the page's reload stamp last seen; null until one is given
  let changes = 0;                 // how many times it moved: a read that began before the last move is not fresh when it ends

  // --- reading ---------------------------------------------------------------------------------------------------------------
  const fresh = (cached, task) => cached.state === task.state && cached.at !== 0;     // at 0: the store changed since it was read

  function ensure(task) {
    const cached = bodies.get(task.id);
    if (reading.has(task.id)) return;
    if (cached && fresh(cached, task)) return;
    reading.add(task.id);
    const began = changes;
    const stamped = () => (began === changes ? Date.now() : 0);     // 0: the store changed meanwhile, read again at once
    client.task(env.project, task.id).then((body) => {
      bodies.set(task.id, { body, state: task.state, at: stamped() });
    }).catch(() => {
      bodies.set(task.id, { body: cached ? cached.body : null, state: task.state, at: stamped() });
    }).finally(() => {
      reading.delete(task.id);
      if (began !== changes) read();
      draw();
    });
  }

  // The rows whose body is read without being expanded: the failed ones first (their failure word and ending), then the done ones
  // (their paths), then the rest in the groups' order, at most twelve; and every expanded row.
  const READ_ORDER = ["failed", "done"];

  function read() {
    if (last.loading) return;
    const groups = groupTasks(last.tasks);
    const first = READ_ORDER.map((id) => groups.find((g) => g.id === id)).filter(Boolean);
    const rest = groups.filter((g) => !READ_ORDER.includes(g.id));
    for (const task of [...first, ...rest].flatMap((g) => g.tasks).slice(0, MAX_READS)) ensure(task);
    for (const id of expanded) {
      const task = last.tasks.find((t) => t.id === id);
      if (task) ensure(task);
    }
  }

  // --- Retry -----------------------------------------------------------------------------------------------------------------
  async function retryTask(id) {
    if (retrying.has(id)) return;
    retrying.add(id);
    retryError.delete(id);
    draw();
    try {
      await env.api.retry(env.project, id);
      bodies.delete(id);
    } catch (e) {
      retryError.set(id, errorText(e));
    }
    retrying.delete(id);
    draw();
    env.refresh();
  }

  // --- drawing ---------------------------------------------------------------------------------------------------------------
  function toggleRow(task) {
    if (expanded.has(task.id)) expanded.delete(task.id);
    else expanded.add(task.id);
    if (expanded.has(task.id)) ensure(task);
    draw();
  }

  function pathRow(file) {
    const link = file.openable ? h("a", { class: "pui-link pui-theme", href: env.links.open(file.path), "aria-label": `Open ${file.path}`, text: "Open" }) : null;
    return h("li", { class: "wb-path-row" }, h("code", { class: "wb-path", text: file.path }), link);
  }

  function detailOf(task, row) {
    if (!row.hasBody) {
      const cached = bodies.get(task.id);
      return cached && !reading.has(task.id) ? h("p", { class: "wb-empty-line", text: "The runs could not be read." }) : busyLine("Loading the runs...");
    }
    if (!row.runs.length) return h("p", { class: "wb-empty-line", text: "No run yet." });
    return [h("div", { class: "wb-section-label", text: "Runs, newest first" }), ...row.runs.map(runBlock)];
  }

  function rowNode(task) {
    const row = rowOf(task, { requests: last.requests, pending: last.pending, body: (bodies.get(task.id) || {}).body || null, now: env.now() });
    const isOpen = expanded.has(task.id);
    const detailId = `wb-task-detail-${task.id}`;
    const toggle = h("button", { class: "pui-btn pui-link wb-task-toggle", type: "button", "data-key": `toggle-${task.id}`, "aria-expanded": isOpen ? "true" : "false", "aria-controls": detailId },
      h("span", { class: "wb-task-num", text: row.number }), h("span", { class: "wb-task-title", text: row.title }));
    toggle.addEventListener("click", () => toggleRow(task));
    const meta = h("div", { class: "wb-task-meta wb-muted" },
      row.skill ? h("code", { class: "wb-task-skill", text: row.skill }) : null,
      row.request ? h("span", { class: "wb-task-request" }, h("a", { class: "pui-link pui-theme", href: env.links.request(row.request.id), text: row.request.label })) : null,
      h("span", { class: "wb-task-age", text: row.age }));
    const actions = row.actions.map((action) => {
      if (action.kind === "inbox") return h("a", { class: "pui-link pui-theme wb-task-inbox", href: env.links.inbox(action.pending), "data-key": `inbox-${task.id}`, text: "Open in the Inbox" });
      const busy = retrying.has(task.id);
      const button = h("button", { class: "pui-btn pui-surface pui-outline wb-small-button wb-task-retry", type: "button", "data-key": `retry-${task.id}`, "aria-label": `Retry task ${task.id}`, "aria-busy": busy ? "true" : null },
        busy ? ring(true) : null, busy ? "Retrying..." : "Retry");
      button.disabled = busy;
      button.addEventListener("click", () => retryTask(task.id));
      return button;
    });
    const showNote = row.note && (task.state === "failed" || task.state === "blocked" || task.state === "cancelled");
    const failure = row.failure ? `${row.failure.failure}${row.failure.ending ? ` · ${row.failure.ending}` : ""}` : "";
    return h("li", { class: "wb-task", "data-task": String(task.id) },
      h("div", { class: "wb-task-head" }, toggle, chip(row.word, row.tone)),
      meta,
      failure ? h("p", { class: "wb-task-failure", text: failure }) : null,
      showNote ? h("p", { class: "wb-task-note wb-muted", text: row.note }) : null,
      row.returned.length ? h("ul", { class: "wb-paths wb-task-paths" }, row.returned.map(pathRow)) : null,
      actions.length ? h("div", { class: "wb-task-actions" }, actions) : null,
      retryError.has(task.id) ? notice(retryError.get(task.id), "error") : null,
      h("div", { class: "wb-task-detail", id: detailId, hidden: !isOpen }, isOpen ? detailOf(task, row) : null));
  }

  function groupNode(group) {
    const isOpen = group.count > 0 && (opened.has(group.id) ? opened.get(group.id) : true);
    const summary = h("summary", { class: "wb-task-group-head", "data-key": `group-${group.id}` },
      h("span", { class: "wb-task-group-name", text: group.label }), h("span", { class: "pui-badge pui-muted pui-soft pui-rounded-full", text: String(group.count) }));
    const details = h("details", { class: "wb-task-group", "data-group": group.id, open: isOpen },
      summary, isOpen ? h("ul", { class: "wb-task-list", role: "list" }, group.tasks.map(rowNode)) : null);
    details.addEventListener("toggle", () => {
      if (details.open === isOpen) return;
      opened.set(group.id, details.open);
      draw();
    });
    return details;
  }

  function draw() {
    if (last.loading) {
      if (shown !== "loading") {
        shown = "loading";
        fill(el, busyLine("Loading the tasks..."));
      }
      return;
    }
    const groups = groupTasks(last.tasks);
    const now = env.now();
    // the signature is everything a row draws: a poll that changed nothing draws nothing, so it never takes the focus away
    const key = JSON.stringify([groups.map((g) => [g.id, g.count, g.tasks.map((t) => [t.id, t.title, t.skill, t.state, t.note, t.requestId])]), last.requests.map((r) => [r.id, r.title]),
      last.pending.map((p) => [p.id, p.task_id]), [...bodies].map(([id, v]) => [id, Boolean(v.body), v.body ? [v.body.runs, v.body.pending, v.body.task] : null]), [...expanded].sort(), [...opened], [...retrying], [...retryError],
      [...reading], last.tasks.map((t) => (bodies.get(t.id) && bodies.get(t.id).body ? rowOf(t, { requests: last.requests, pending: last.pending, body: bodies.get(t.id).body, now }).age : ""))]);
    if (key === shown) return;
    shown = key;
    if (!last.tasks.length) {
      fill(el, h("p", { class: "wb-empty-line", text: NONE_TEXT }));
      return;
    }
    keepFocus(groupsBox, () => fill(groupsBox, groups.map(groupNode)));
    if (el.children[0] !== groupsBox) fill(el, groupsBox);
  }

  return {
    el,
    /** data: {tasks, requests, pending, loading, reload, unaccepted}; reload is the page's stamp, which moves when the store changed; unaccepted: nothing is read (the bodies held stay). */
    update(data) {
      if (data.reload !== undefined) {
        if (reloaded !== null && data.reload !== reloaded) {     // the store changed: every body held is stale, whatever its age
          changes += 1;
          for (const entry of bodies.values()) entry.at = 0;
        }
        reloaded = data.reload;
      }
      last = { tasks: data.tasks || [], requests: data.requests || [], pending: data.pending || [], loading: Boolean(data.loading) };
      if (!data.unaccepted) read();
      draw();
    },
  };
}
