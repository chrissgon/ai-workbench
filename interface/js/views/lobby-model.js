// What the Lobby shows, worked out from what the service returned: pure functions with no document and no network, so
// they run under a test. Nothing is decided here: a request's state and a decision's actions are the service's own words.

import * as format from "../format.js";
import { PLANNING, drawersOf } from "../floor-model.js";
import { windowState } from "../scene/look.js";

export const POLL_BUSY_MS = 2000;     // the conversation is read every 2 seconds while a `say` job runs
export const POLL_IDLE_MS = 10000;    // and every 10 seconds otherwise
export const JOB_EVERY_MS = 1000;     // pollJob's period
export const MAX_BODIES = 8;          // the requests whose decisions are read with `task`: the newest few

export const TABS = Object.freeze([["conversation", "Conversation"], ["inbox", "Inbox"], ["desk", "Desk"], ["tasks", "Tasks"], ["agent", "Agent"]]);

export const HINT = "A line that starts with / is a command; /help lists them.";
export const SENDING_TEXT = "The planning agent is working on this turn. It can take minutes.";
export const BUSY_NOTICE = Object.freeze({ title: "Not sent", text: "A run is in progress for this project. Your message was not stored." });
export const NOT_ACCEPTED_TEXT = "Waiting for the configuration to be accepted.";
export const EMPTY_TEXT = "No messages yet. Describe what you want done.";
export const AUTO_FLOW = "Let the planning agent route it";
export const FORM_HINT = "A flow plans the request from a predefined route. Without one, the planning agent routes it.";
const FINAL = new Set(["done", "cancelled"]);

/** The tab a route names: one of the four ids, `conversation` for none or for a word that is not a tab. */
export function tabOf(route) {
  const wanted = route && route.tab;
  return TABS.some(([id]) => id === wanted) ? wanted : "conversation";
}

/** How long to wait before the next read of the conversation: null while the document is hidden. */
export function pollInterval({ jobRunning, hidden }) {
  if (hidden) return null;
  return jobRunning ? POLL_BUSY_MS : POLL_IDLE_MS;
}

/** The messages `have` plus the ones `got`, one per id, oldest first. */
export function mergeMessages(have, got) {
  const byId = new Map();
  for (const m of [...(have || []), ...(got || [])]) {
    if (m && Number.isInteger(m.id)) byId.set(m.id, m);
  }
  return [...byId.values()].sort((a, b) => a.id - b.id);
}

/** The id the next read asks above: the newest message's, or 0. */
export function lastId(messages) {
  return (messages || []).reduce((top, m) => (Number.isInteger(m.id) && m.id > top ? m.id : top), 0);
}

/** "4 h ago", "12 min ago" or "just now". */
export function ago(stamp, now) {
  const short = format.age(stamp, now);
  if (!short) return "";
  return short === "now" ? "just now" : `${short} ago`;
}

/** Who wrote a message, as the page words it. */
export function authorOf(role) {
  return role === "user" ? "You" : "Planning agent";
}

/** The meta line over a message: "You · 4 h ago". */
export function metaOf(message, now) {
  const when = ago(message.created_at, now);
  return when ? `${authorOf(message.role)} · ${when}` : authorOf(message.role);
}

/** The name a message carries for a screen reader: "You, 4 hours ago". */
export function nameOf(message, now) {
  const when = format.ageWords(message.created_at, now);
  return when ? `${authorOf(message.role)}, ${when === "just now" ? when : `${when} ago`}` : authorOf(message.role);
}

/**
 * Where each request's block goes: under the newest assistant message that names it (`byMessage`: message id -> request id),
 * or, for a request no message names (made from the form: OPEN-24), after the last message (`trailing`, oldest request first).
 * A request in a final state has no trailing block: nothing waits on it.
 */
export function placeBlocks(messages, requests) {
  const byMessage = new Map();
  const named = new Map();
  for (const m of messages || []) {
    if (m.role === "assistant" && Number.isInteger(m.task_id)) named.set(m.task_id, m.id);
  }
  for (const [request, message] of named) byMessage.set(message, request);
  const trailing = (requests || []).filter((r) => !named.has(r.id) && !FINAL.has(r.state)).map((r) => r.id).sort((a, b) => a - b);
  return { byMessage, trailing };
}

/**
 * The requests whose `task` body is read: every one that has an open decision in `pending` (by task_id: its card must be drawn
 * so that it can be answered), then the newest of the rest the conversation shows, up to MAX_BODIES in all (more when more than
 * MAX_BODIES have an open decision).
 */
export function wantedBodies(placed, requests, pending = []) {
  const known = new Set((requests || []).map((r) => r.id));
  const shown = [...new Set([...placed.byMessage.values(), ...placed.trailing])].filter((id) => known.has(id));
  const open = new Set((pending || []).map((p) => p.task_id));
  const must = shown.filter((id) => open.has(id)).sort((a, b) => b - a);
  const rest = shown.filter((id) => !open.has(id)).sort((a, b) => b - a);
  return [...must, ...rest.slice(0, Math.max(0, MAX_BODIES - must.length))];
}

/** A change signature of one request in a status body: the state, the task count and the open decisions' ids. */
export function signatureOf(request, pending) {
  const open = (pending || []).filter((p) => p.task_id === request.id).map((p) => p.id).join(",");
  return `${request.state}|${(request.tasks || []).length}|${open}`;
}

/** The decisions of the planning agent in a status body: those on a request (agent null) or of the planning agent. */
export function lobbyDecisions(status) {
  return (Array.isArray(status && status.pending) ? status.pending : []).filter((p) => !p.agent || p.agent === "planning");
}

/**
 * The Lobby's open decisions split between the Inbox's cards and the lines that point at the Conversation (OPEN-24). A plan on a
 * request that a message of the planning agent names has its card under that message, so the Inbox shows a line that points to it;
 * every other decision (a plan on a request made from the form, a question, an acceptance, a decision on the planning agent's own
 * task) has its card in the Inbox. Returns {cards, pointers}, each in the order of `status.pending`.
 */
export function inboxParts(status, messages) {
  const requests = Array.isArray(status && status.requests) ? status.requests : [];
  const named = new Set(placeBlocks(messages, requests).byMessage.values());
  const cards = [];
  const pointers = [];
  for (const item of lobbyDecisions(status)) {
    (item.kind === "plan" && named.has(item.task_id) ? pointers : cards).push(item);
  }
  return { cards, pointers };
}

/** True when a message of the planning agent names the request: its plan card is in the Conversation, not in the Inbox. */
export function isNamed(messages, requestId) {
  return (messages || []).some((m) => m.role === "assistant" && m.task_id === requestId);
}

/** The documents of the Lobby's Desk: the rows of `artifacts` whose agent is the planning agent or none (no owner, or no single agent owns the skill). */
export function lobbyDocuments(rows) {
  return (Array.isArray(rows) ? rows : []).filter((d) => d && (!d.agent || d.agent === PLANNING));
}

/** The words of a request's state for its chip. */
export function stateWord(state) {
  if (typeof state !== "string" || !state) return "";
  return state.charAt(0).toUpperCase() + state.slice(1);
}

/** What the request line shows: {id, title, state, name, cancellable, routable}. `open` is the number of open decisions on it. */
export function requestLine(request, open) {
  const final = FINAL.has(request.state);
  return {
    id: request.id, title: request.title || `Request ${request.id}`, state: stateWord(request.state), final,
    name: `Request ${request.id}, ${request.title || ""}, ${request.state}`,
    cancellable: !final,
    routable: request.state === "requested" && open === 0,
  };
}

/** The count line of the cancel dialog, from the request's tasks (`status`). */
export function cancelCount(request) {
  const tasks = Array.isArray(request && request.tasks) ? request.tasks : [];
  if (!tasks.length) return "No task has been created yet.";
  const untouched = new Set(["planned", "ready", "requested"]);
  const started = tasks.filter((t) => !untouched.has(t.state)).length;
  const n = `${tasks.length} task${tasks.length === 1 ? "" : "s"}`;
  return started === 0 ? `${n}, none started` : `${n}, ${started} started`;
}

/** The words of a decision that is no longer open: "Plan approved", "Question cancelled". */
export function resolvedWord(item) {
  const kind = format.kindWord(item.kind);
  if (item.status === "cancelled") return `${kind} cancelled`;
  return item.resolution ? `${kind} ${item.resolution}` : `${kind} resolved`;
}

/** The options of the Flow select: the first is the planning agent's own route, then one per flow, labelled by its title. */
export function flowOptions(flows) {
  const listed = (Array.isArray(flows) ? flows : []).filter((f) => f && typeof f.flow === "string" && !f.error);
  return [{ value: "", label: AUTO_FLOW }, ...listed.map((f) => ({ value: f.flow, label: typeof f.title === "string" && f.title ? f.title : f.flow }))];
}

/**
 * The notice a `say` that did not run shows, {title, text}. `phase` is "post" when the service refused the call itself (nothing
 * was stored: the 409 busy answer has the drawing's words, any other refusal its own message) and "job" when the job failed (the
 * job's own message, OPEN-23).
 */
export function noticeFor(error, phase = "post") {
  if (error && error.status === 409 && error.word === "busy") return BUSY_NOTICE;
  const text = (error && typeof error.message === "string" && error.message) || "The planning agent's turn failed.";
  return { title: phase === "job" ? "The turn failed" : "Not sent", text };
}

/** The notice after a request was made but not routed (the 409 busy answer of `route`, or the router's run failing). */
export function notRoutedNotice(id, reason) {
  return { title: "Not routed yet", text: `Request #${id} was created. ${reason} Use "Route it" on its request line.` };
}

const DOT = { working: "theme", waiting: "warn", idle: "muted", off: "border" };

/**
 * What the Lobby's room needs, as the plain model of the room scene (the shape the Floor's room builder reads: `ready`, `state`,
 * `window`, `decisions`, `drawers`, `sheets`, `tips`, `board`) with `door: true` for the door to the Control room. The planning agent
 * works while a turn or a route of this screen runs, waits when a decision of the Lobby waits, is off when the project is not
 * accepted and is idle otherwise. `documents` are the Desk's rows (see lobbyDocuments), as the Floor takes them: the sheets and the cabinet's
 * drawers; null while they are unread (the world keeps what the table shows: an empty cabinet at first).
 */
export function roomModel({ working, decisions, hasMessages, accepted, request, ready = true, documents = null }) {
  let state = "idle";
  if (!accepted) state = "off";
  else if (working) state = "working";
  else if (decisions > 0) state = "waiting";
  const words = { working: "working", waiting: "waiting for you", idle: "idle", off: "off" }[state];
  const docs = Array.isArray(documents) ? documents : null;
  const board = request
    ? { title: request.title || `Request ${request.id}`, lines: [`request #${request.id} · ${request.state}`], dot: DOT[state] }
    : { title: accepted ? "No request is open" : NOT_ACCEPTED_TEXT, lines: [], dot: DOT[state] };
  return {
    kind: "room", ready, door: true, state, window: windowState(state === "working"), decisions, drawers: docs ? drawersOf(docs.length) : null,
    sheets: docs ? docs.slice(0, 6).map((d) => ({ path: d.path, tip: d.path })) : null, empty: !hasMessages,
    tips: {
      agent: `Planning agent · ${words}`, desk: request ? `Current task · ${request.title || `request #${request.id}`}` : "Current task · none yet",
      tray: `Inbox · ${decisions} waiting`,
      cabinet: docs ? `${docs.length} document${docs.length === 1 ? "" : "s"} · open the Desk tab` : "Documents · open the Desk tab", board: board.lines[0] || board.title,
      door: "Control room · skills, costs, connections",
    },
    board,
  };
}

/** The canvas label of the Lobby, built from the data. */
export function canvasLabel(projectName, room) {
  const n = room.decisions;
  return `Lobby of ${projectName || "the project"}, planning agent ${room.state}, ${n} decision${n === 1 ? "" : "s"}, door to the Control room`;
}
