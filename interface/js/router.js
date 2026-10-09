// The hash router: a pure parser and the builders of every link the frame draws. The hash forms are the flows' IA-4:
//   #/                                   the City
//   #/p/<id>                             a project's building
//   #/p/<id>/floor/<agent>[/<tab>[/<pending id>]]   an agent's floor (tab: agent, inbox, desk, tasks; the desk takes a document: /desk/<percent-encoded path>)
//   #/p/<id>/lobby[/<tab>[/<pending id>]]            the planning agent's floor (tab: conversation, inbox, desk, tasks, agent; the desk takes a document like a floor's)
//   #/p/<id>/control[/<tab>]             the control room (tab: skills, costs, connections)
// <id> is the 12-character id the service gives a project. An unknown hash is the City. Nothing here touches the document.

const ID = /^[0-9a-f]{12}$/;
const NAME = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;
const NUMBER = /^[0-9]{1,9}$/;
const WORD = /^[a-z]{1,16}$/;

export const CITY = Object.freeze({ screen: "city", project: null, agent: null, tab: null, pending: null });

/** The route a hash names: {screen, project, agent, tab, pending}. Anything that does not match is the City. */
export function parse(hash) {
  const text = typeof hash === "string" ? hash : "";
  const parts = text.replace(/^#\/?/, "").split("/");
  while (parts.length && parts[parts.length - 1] === "") parts.pop();
  if (parts.length < 2 || parts[0] !== "p" || !ID.test(parts[1])) return CITY;
  const project = parts[1];
  const rest = parts.slice(2);
  const route = { screen: "building", project, agent: null, tab: null, pending: null };
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
  return "#/";
}

/** The hash of a project's building. */
export function buildingHash(project) {
  return `#/p/${project}`;
}

/** The hash of an agent's floor, optionally on a tab and at a decision. */
export function floorHash(project, agent, tab, pending) {
  return `#/p/${project}/floor/${agent}` + (tab ? `/${tab}` : "") + (tab && pending !== undefined && pending !== null ? `/${pending}` : "");
}

/** The hash of a document in an agent's desk: the path is one percent-encoded segment. */
export function deskHash(project, agent, path) {
  return `#/p/${project}/floor/${agent}/desk` + (path ? `/${encodeURIComponent(path)}` : "");
}

/** The hash of the lobby, optionally on a tab and at a decision. */
export function lobbyHash(project, tab, pending) {
  return `#/p/${project}/lobby` + (tab ? `/${tab}` : "") + (tab && pending !== undefined && pending !== null ? `/${pending}` : "");
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
