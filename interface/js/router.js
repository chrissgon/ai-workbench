// The hash router: a pure parser and the builders of every link the frame draws. The hash forms are the flows' IA-4:
//   #/city                               the City (always)
//   #/                                   the entry: the City, or the Building of the one project of a service that holds one (main.js replaces it, on entry only)
//   #/p/<id>                             a project's building
//   #/p/<id>/floor/<agent>[/<tab>[/<pending id>]]   an agent's floor (tab: agent, inbox, desk, tasks; the desk takes a document: /desk/<percent-encoded path>)
//   #/p/<id>/lobby[/<tab>[/<pending id>]]            the planning agent's floor (tab: conversation, inbox, desk, tasks, agent; the desk takes a document like a floor's)
//   #/p/<id>/lobby/conversation/request/<n>          the Conversation at request n's line (a bare number after the tab is a decision, so the word `request` is a segment)
//   #/p/<id>/control[/<tab>]             the control room (tab: skills, costs, connections)
// <id> is the 12-character id the service gives a project. An unknown hash is the City. Nothing here touches the document.

const ID = /^[0-9a-f]{12}$/;
const NAME = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;
const NUMBER = /^[0-9]{1,9}$/;
const WORD = /^[a-z]{1,16}$/;

export const CITY = Object.freeze({ screen: "city", project: null, agent: null, tab: null, pending: null, request: null });

/** The route a hash names: {screen, project, agent, tab, pending, request}. `#/city`, `#/` and anything that does not match is the City. */
export function parse(hash) {
  const text = typeof hash === "string" ? hash : "";
  const parts = text.replace(/^#\/?/, "").split("/");
  while (parts.length && parts[parts.length - 1] === "") parts.pop();
  if (parts.length < 2 || parts[0] !== "p" || !ID.test(parts[1])) return CITY;
  const project = parts[1];
  const rest = parts.slice(2);
  const route = { screen: "building", project, agent: null, tab: null, pending: null, request: null };
  if (rest.length === 0) return route;
  const [head, ...tail] = rest;
  if (head === "floor") {
    if (!tail.length || !NAME.test(tail[0])) return { ...route };
    route.screen = "floor";
    route.agent = tail[0];
    return finish(route, tail.slice(1));
  }
  if (head === "lobby") {
    route.screen = "lobby";
    return finish(route, tail);
  }
  if (head === "control") {
    route.screen = "control";
    return finish(route, tail);
  }
  return route;
}

function finish(route, tail) {
  route.path = null;
  if (tail.length && WORD.test(tail[0])) route.tab = tail[0];
  if (tail.length > 1 && NUMBER.test(tail[1])) route.pending = Number(tail[1]);
  if (route.screen === "lobby" && route.tab === "conversation" && tail[1] === "request" && tail.length === 3 && NUMBER.test(tail[2])) route.request = Number(tail[2]);
  if (route.tab === "desk" && tail.length > 1) {
    // a document: the percent-encoded path of a file under docs/ (never a slash, so it is one segment)
    try {
      const path = decodeURIComponent(tail[1]);
      if (path && path.length <= 512) route.path = path;
    } catch (e) {
      route.path = null;
    }
  }
  return route;
}

/** The hash of the City. */
export function cityHash() {
  return "#/city";
}

/**
 * Where the entry hash goes (C-1): the hash of the Building of the one project, when the page was opened on `#/` (or on nothing) and the
 * service holds exactly one project; else null. `#/city` and every other hash are left alone, so a reload on the City stays there.
 */
export function entryHash(hash, projectIds) {
  const text = typeof hash === "string" ? hash : "";
  if (text.replace(/^#\/?/, "") !== "") return null;
  return Array.isArray(projectIds) && projectIds.length === 1 ? buildingHash(projectIds[0]) : null;
}

/** True when `route` is the Building of the only project of the service: its home, where Back is disabled and Escape does nothing. */
export function isHomeBuilding(route, projectIds) {
  return Boolean(route) && route.screen === "building" && Array.isArray(projectIds) && projectIds.length === 1 && projectIds[0] === route.project;
}

/** The hash of a project's building. */
export function buildingHash(project) {
  return `#/p/${project}`;
}

/** The hash of an agent's floor, optionally on a tab and at a decision. */
export function floorHash(project, agent, tab, pending) {
  return `#/p/${project}/floor/${agent}` + (tab ? `/${tab}` : "") + (tab && pending !== undefined && pending !== null ? `/${pending}` : "");
}

/** Where an agent's floor is: the Lobby for the planning agent (or none), the agent's floor for any other. */
export function agentHash(project, agent) {
  return !agent || agent === "planning" ? lobbyHash(project) : floorHash(project, agent);
}

/** The hash of a document in an agent's desk: the path is one percent-encoded segment. */
export function deskHash(project, agent, path) {
  return `#/p/${project}/floor/${agent}/desk` + (path ? `/${encodeURIComponent(path)}` : "");
}

/** The hash of the lobby, optionally on a tab and at a decision. */
export function lobbyHash(project, tab, pending) {
  return `#/p/${project}/lobby` + (tab ? `/${tab}` : "") + (tab && pending !== undefined && pending !== null ? `/${pending}` : "");
}

/** The hash of the Conversation at the line of request `id` (the Lobby scrolls to it and focuses its title). */
export function requestHash(project, id) {
  return `#/p/${project}/lobby/conversation/request/${id}`;
}

/** The hash of a document in the Lobby's desk: the path is one percent-encoded segment. */
export function lobbyDeskHash(project, path) {
  return `#/p/${project}/lobby/desk` + (path ? `/${encodeURIComponent(path)}` : "");
}

/** The hash of the control room. */
export function controlHash(project, tab) {
  return `#/p/${project}/control` + (tab ? `/${tab}` : "");
}

/** The route one level up: a floor, the lobby and the control room go to the building; a building to the City. */
export function parentHash(route) {
  if (route.screen === "city") return null;
  if (route.screen === "building") return cityHash();
  return buildingHash(route.project);
}
