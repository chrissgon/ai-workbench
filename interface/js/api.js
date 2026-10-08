// The client of the local service (runtime/service.py): one function per route of its ROUTES table, named after the
// operation. Each sends the token as "Authorization: Bearer", a POST sends "Content-Type: application/json", and
// only a route that takes a query (progress, conversation, costs, artifact) is sent one. An error body {error, message} becomes an ApiError with
// the status and the word. A route whose operation calls a model or a platform answers 202 with a job: the function
// returns that job and pollJob(job.job, every) asks for it again until it is done or failed. The token is read from
// token.js for each request and appears nowhere else here.

import { getToken } from "./token.js";

const PREFIX = "/api/v1";

// The words the service gives an error (runtime/service.py WORDS), by status, for a body that carries none.
const WORD_OF_STATUS = {
  400: "usage", 401: "token", 403: "host", 404: "not_found", 405: "method", 409: "refused", 411: "length",
  412: "not_configured", 413: "too_large", 415: "content_type", 500: "internal", 503: "stopping",
};

/** An answer the service refused, or a request that did not get one (status 0, word "network"). */
export class ApiError extends Error {
  constructor(status, word, message) {
    super(message || word);
    this.name = "ApiError";
    this.status = status;
    this.word = word;
  }

  /** 409 busy: a job that calls a model is already running for this project. */
  get busy() { return this.status === 409 && this.word === "busy"; }

  /** 409 refused: the operation refused (a rule of the work, not a malformed request). */
  get refused() { return this.status === 409 && this.word === "refused"; }

  /** 412: the project's configuration is not accepted yet (the terminal's accept-config does that). */
  get notConfigured() { return this.status === 412; }

  /** 401: the token is missing or is not the service's current one. */
  get unauthorized() { return this.status === 401; }

  /** 400: the request is malformed. */
  get usage() { return this.status === 400; }
}

let authFailure = null;

/** Register the one function called when the service answers 401 (the page then asks for the token again). */
export function onAuthFailure(fn) {
  authFailure = fn;
}

const enc = (part) => encodeURIComponent(String(part));

async function send(method, path, options = {}) {
  const token = getToken();
  if (!token) {
    if (authFailure) authFailure();
    throw new ApiError(401, "token", "There is no token yet.");
  }
  let url = PREFIX + path;
  if (options.query) {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(options.query)) {
      if (value !== undefined && value !== null) query.append(key, String(value));
    }
    const text = query.toString();
    if (text) url += "?" + text;
  }
  const headers = { Authorization: `Bearer ${token}`, Accept: "application/json" };
  const init = {
    method, headers, credentials: "omit", cache: "no-store", redirect: "error", mode: "same-origin",
    referrerPolicy: "no-referrer", signal: options.signal,
  };
  if (method === "POST") {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body || {});
  }
  let response;
  try {
    response = await fetch(url, init);
  } catch (e) {
    if (e && e.name === "AbortError") throw e;
    throw new ApiError(0, "network", "The service could not be reached. Is it still running?");
  }
  let data = null;
  try {
    data = await response.json();
  } catch (e) {
    data = null;
  }
  if (!response.ok) {
    const word = (data && typeof data.error === "string" && data.error) || WORD_OF_STATUS[response.status] || "internal";
    const message = (data && typeof data.message === "string" && data.message) || word;
    const failure = new ApiError(response.status, word, message);
    if (failure.unauthorized && authFailure) authFailure();
    throw failure;
  }
  if (data === null || typeof data !== "object") throw new ApiError(response.status, "internal", "The service answered with something that is not JSON.");
  return data;
}

// --- the routes, in the order of ROUTES --------------------------------------------------------------------------
// A function marked (job) answers 202: it returns the job {job, op, project, state, result, error, started_at,
// ended_at}; hand job.job to pollJob. The other functions return what the operation returned.

/** GET /projects: {projects: [{id, name, config: {sha256, accepted}, message?, open_pending?, running_task?}]}. */
export function projects(options) {
  return send("GET", "/projects", options);
}

/** GET /projects/{p}/status: the requests with their tasks, the open decisions, the documents. */
export function status(p, options) {
  return send("GET", `/projects/${enc(p)}/status`, options);
}

/** GET /projects/{p}/pending: the open decisions, each with the actions it takes. */
export function pending(p, options) {
  return send("GET", `/projects/${enc(p)}/pending`, options);
}

/** GET /projects/{p}/pending/{id}: one decision with its body and payload. */
export function pendingItem(p, id, options) {
  return send("GET", `/projects/${enc(p)}/pending/${enc(id)}`, options);
}

/** POST /projects/{p}/pending/{id}/answer: {text, with_comments?}. */
export function answer(p, id, text, { withComments, signal } = {}) {
  return send("POST", `/projects/${enc(p)}/pending/${enc(id)}/answer`, { body: { text, with_comments: withComments }, signal });
}

/** POST /projects/{p}/pending/{id}/release (job). */
export function release(p, id, options) {
  return send("POST", `/projects/${enc(p)}/pending/${enc(id)}/release`, options);
}

/** POST /projects/{p}/pending/{id}/approve (job): {sha256}, the hash of the content the page showed. */
export function approve(p, id, sha256, options = {}) {
  return send("POST", `/projects/${enc(p)}/pending/${enc(id)}/approve`, { body: { sha256 }, signal: options.signal });
}

/** POST /projects/{p}/pending/{id}/reject: {note?}. */
export function reject(p, id, note, options = {}) {
  return send("POST", `/projects/${enc(p)}/pending/${enc(id)}/reject`, { body: { note }, signal: options.signal });
}

/** GET /projects/{p}/flows: the flow files of the checkout. */
export function flows(p, options) {
  return send("GET", `/projects/${enc(p)}/flows`, options);
}

/** POST /projects/{p}/requests: {text, flow?, title?}. */
export function request(p, text, { flow, title, signal } = {}) {
  return send("POST", `/projects/${enc(p)}/requests`, { body: { text, flow, title }, signal });
}

/** POST /projects/{p}/requests/{id}/route (job): {flow?}. */
export function route(p, id, { flow, signal } = {}) {
  return send("POST", `/projects/${enc(p)}/requests/${enc(id)}/route`, { body: { flow }, signal });
}

/** POST /projects/{p}/requests/{id}/cancel. */
export function cancel(p, id, options) {
  return send("POST", `/projects/${enc(p)}/requests/${enc(id)}/cancel`, options);
}

/** GET /projects/{p}/tasks/{id}: the task, its runs and its decisions. */
export function task(p, id, options) {
  return send("GET", `/projects/${enc(p)}/tasks/${enc(id)}`, options);
}

/** POST /projects/{p}/tasks/{id}/retry. */
export function retry(p, id, options) {
  return send("POST", `/projects/${enc(p)}/tasks/${enc(id)}/retry`, options);
}

/** POST /projects/{p}/tasks/{id}/files: hand a file to a task, {name, content_base64}. */
export function handOver(p, id, name, contentBase64, options = {}) {
  return send("POST", `/projects/${enc(p)}/tasks/${enc(id)}/files`, { body: { name, content_base64: contentBase64 }, signal: options.signal });
}

/** POST /projects/{p}/runs/{id}/verdict: {word}. */
export function verdict(p, id, word, options = {}) {
  return send("POST", `/projects/${enc(p)}/runs/${enc(id)}/verdict`, { body: { word }, signal: options.signal });
}

/** POST /projects/{p}/agents/{name}/mode: {mode}. Every route of an unaccepted project answers 412 first. */
export function setMode(p, name, mode, options = {}) {
  return send("POST", `/projects/${enc(p)}/agents/${enc(name)}/mode`, { body: { mode }, signal: options.signal });
}

/** GET /projects/{p}/progress?since=: the only route that takes a query. */
export function progress(p, { since, signal } = {}) {
  return send("GET", `/projects/${enc(p)}/progress`, { query: { since }, signal });
}

/** GET /projects/{p}/agents: {agents: [{name, pack, enabled, mode, acting_mode, max_runs_per_day, max_usd_per_day, runs_today, usd_today, queued, ...}]}. */
export function agents(p, options) {
  return send("GET", `/projects/${enc(p)}/agents`, options);
}

/** GET /projects/{p}/conversation?after=&conversation=: {conversation, messages: [{id, role, text, ...}]}, oldest first. */
export function conversation(p, { after, conversation: name, signal } = {}) {
  return send("GET", `/projects/${enc(p)}/conversation`, { query: { after, conversation: name }, signal });
}

/** GET /projects/{p}/skills: the skills in scope with their proof on each model, and the two checks of the proof. */
export function skills(p, options) {
  return send("GET", `/projects/${enc(p)}/skills`, options);
}

/** GET /projects/{p}/costs?since=: {since, rows, caps}; since is a day, YYYY-MM-DD. */
export function costs(p, { since, signal } = {}) {
  return send("GET", `/projects/${enc(p)}/costs`, { query: { since }, signal });
}

/** GET /projects/{p}/connections: the providers, the secrets found (never a value), the image. */
export function connections(p, options) {
  return send("GET", `/projects/${enc(p)}/connections`, options);
}

/** GET /projects/{p}/artifacts: {artifacts: [{path, owner, size, modified_at, bound}], truncated}. */
export function artifacts(p, options) {
  return send("GET", `/projects/${enc(p)}/artifacts`, options);
}

/** GET /projects/{p}/artifact?path=: {path, text, size, modified_at} of one file under docs/ (at most 512 bytes of path). */
export function artifact(p, path, { signal } = {}) {
  return send("GET", `/projects/${enc(p)}/artifact`, { query: { path }, signal });
}

/** POST /projects/{p}/conversation (job): one turn with the planning agent, {text}. */
export function say(p, text, options = {}) {
  return send("POST", `/projects/${enc(p)}/conversation`, { body: { text }, signal: options.signal });
}

/** POST /projects/{p}/sync (job): {dry_run?, take?, path?}. */
export function sync(p, { dryRun, take, path, signal } = {}) {
  return send("POST", `/projects/${enc(p)}/sync`, { body: { dry_run: dryRun, take, path }, signal });
}

/** POST /projects/{p}/dispatch (job). */
export function dispatch(p, options) {
  return send("POST", `/projects/${enc(p)}/dispatch`, options);
}

/** GET /jobs/{id}: a job again, with state "running", "done" or "failed". */
export function job(id, options) {
  return send("GET", `/jobs/${enc(id)}`, options);
}

// --- jobs ----------------------------------------------------------------------------------------------------------

function sleep(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal && signal.aborted) {
      reject(new DOMException("aborted", "AbortError"));
      return;
    }
    const timer = setTimeout(() => {
      if (signal) signal.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(new DOMException("aborted", "AbortError"));
    };
    if (signal) signal.addEventListener("abort", onAbort, { once: true });
  });
}

/**
 * Ask for a job every `every` milliseconds (at least 200) until its state is "done" or "failed", and return that last
 * job: job.result holds the operation's result when done, job.error the reason when failed. onUpdate is called with
 * each answer. An ApiError from the poll (a 404 for a job the service forgot, a lost connection) is thrown.
 */
export async function pollJob(id, every = 1000, { signal, onUpdate } = {}) {
  const wait = Math.max(200, Number(every) || 1000);
  for (;;) {
    const current = await job(id, { signal });
    if (onUpdate) onUpdate(current);
    if (current.state === "done" || current.state === "failed") return current;
    if (current.state !== "running") throw new ApiError(200, "internal", "The service answered with a job state this page does not know.");
    await sleep(wait, signal);
  }
}
