// Where an open document goes back to (A-19). The hash names the document and the room, never the tab it was opened from, so the
// screens that show a document (the Floor and the Lobby) tell this module every route they draw, and this module keeps one fact:
// the document was opened from the room's Inbox (a card's "Open" link), or from anywhere else (a Desk row, a sheet of the room, a
// hash typed in the bar), which all go back to the Desk. "Close" and Escape both read it, so they cannot disagree. Memory only.

import * as router from "../router.js";

let previous = null;   // the last route told: {screen, project, agent, tab, path (a boolean)}
let origin = null;     // "inbox" while the open document came from the same room's Inbox, else null

/** Tell the module the route a screen is drawing. Called on every draw: the same route again changes nothing. */
export function track(route) {
  const here = { screen: route.screen, project: route.project, agent: route.agent || null, tab: route.tab || null, path: Boolean(route.path) };
  const sameRoom = previous !== null && previous.screen === here.screen && previous.project === here.project && previous.agent === here.agent;
  if (!here.path || !sameRoom) origin = null;
  else if (!previous.path) origin = previous.tab === "inbox" ? "inbox" : null;   // the document just opened: from the route before it
  // else a document was already open in this room (a poll, or one document replaced by another): the origin stays
  previous = here;
}

/** A screen that was told routes is taken down: what it knew is forgotten, so a later deep link is a direct entry. */
export function reset() {
  previous = null;
  origin = null;
}

/** "inbox" when the document now open was opened from the Inbox, else null (the Desk). */
export function current() {
  return origin;
}

/** The hash that closes the document of `route`: the Inbox it was opened from, else the Desk of the same room. */
export function closeHash(route, from) {
  const tab = from === "inbox" ? "inbox" : "desk";
  return route.screen === "lobby" ? router.lobbyHash(route.project, tab) : router.floorHash(route.project, route.agent, tab);
}

/** Close the document of `route`: the same hash Escape goes to. */
export function close(route) {
  window.location.hash = closeHash(route, origin);
}
