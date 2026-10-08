// Reading what the City needs from the service: the project list, and for each accepted project its status (which holds
// the requests with their tasks, each with its title and agent, and the open decisions, each with its agent) and its
// agents, then the `task` body of the one running task of the followed project's open request, for the time its run
// started. Everything is read; nothing is written. A project that answers 412 (its configuration is not accepted) is
// kept with the service's own message; a lost connection throws.

import * as api from "./api.js";
import { neededTasks, taskKey } from "./model.js";

/** A new snapshot holder: {projects, details, tasks, loaded}. */
export function emptySnapshot() {
  return { projects: [], details: {}, tasks: {}, loaded: false };
}

/**
 * One project's status and agents. A 412 (not accepted) is kept as the project's error with the service's text. Any other
 * refusal of one project (a 409, a 500) keeps what the last read held, when there is one, so one bad read does not
 * blank a building; the next poll reads again.
 */
async function readProject(project, before) {
  try {
    const [status, agents] = await Promise.all([api.status(project.id), api.agents(project.id)]);
    return { status, agents: Array.isArray(agents.agents) ? agents.agents : [] };
  } catch (e) {
    if (e && e.name === "ApiError" && e.status !== 0 && e.status !== 401) {
      const error = { status: e.status, word: e.word, message: e.message };
      if (e.status !== 412 && before && before.status) return { ...before, error };   // the data stays, the page says it is stale
      return { error };
    }
    throw e;
  }
}

/**
 * Read everything again and return the new snapshot. `previous` is the last one (its task bodies are reused while a task's
 * state is unchanged); `followed` is the id of the project the tracking bar follows.
 */
export async function refresh(previous, followed) {
  const listed = await api.projects();
  const projects = Array.isArray(listed.projects) ? listed.projects : [];
  const accepted = projects.filter((p) => p.config && p.config.accepted);
  const read = await Promise.all(accepted.map((p) => readProject(p, previous.details[p.id])));
  const details = {};
  accepted.forEach((p, i) => { details[p.id] = read[i]; });
  const wanted = neededTasks(projects, details, followed);
  const tasks = {};
  await Promise.all(wanted.map(async (w) => {
    const key = taskKey(w.project, w.id);
    const cached = previous.tasks[key];
    if (cached && cached.task && (w.state === undefined || cached.task.state === w.state)) {
      tasks[key] = cached;
      return;
    }
    try {
      tasks[key] = await api.task(w.project, w.id);
    } catch (e) {
      if (e && e.name === "ApiError" && e.status === 0) throw e;
      if (e && e.unauthorized) throw e;
      // a task that cannot be read leaves its agent and title unknown: the page falls back to the key and the project
    }
  }));
  return { projects, details, tasks, loaded: true };
}
