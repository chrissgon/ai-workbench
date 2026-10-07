// One project, for now a placeholder: the scene comes with the next packages. It shows the counts of the project's
// status (open decisions, requests by state) so the route and the client are exercised end to end.

import { h, fill } from "../dom.js";

/** Requests by state, as [[state, count], ...] in the order the states first appear. */
export function countByState(requests) {
  const counts = new Map();
  for (const item of Array.isArray(requests) ? requests : []) {
    const state = typeof item.state === "string" ? item.state : "unknown";
    counts.set(state, (counts.get(state) || 0) + 1);
  }
  return [...counts.entries()];
}

/** Draw the project panel. `entry` is the project's row of the list (or null), `state` the body of its status. */
export function showProject(root, { entry, state, error }) {
  const title = entry ? entry.name : "Project";
  const back = h("a", { href: "#/", text: "All projects" });
  const body = [];
  if (error) {
    body.push(h("p", { class: "notice error", role: "alert", text: error }));
  } else {
    const pending = Array.isArray(state.pending) ? state.pending.length : 0;
    const states = countByState(state.requests);
    body.push(
      h("p", { class: "muted", text: "The scene of this project comes with the next packages. These are its counts for now." }),
      h("p", {}, h("span", { class: "muted", text: "Open decisions: " }), String(pending)),
      states.length
        ? h("div", { class: "table-wrap" },
          h("table", { class: "pui-table" },
            h("thead", {}, h("tr", {}, h("th", { text: "Requests" }), h("th", { text: "Count" }))),
            h("tbody", {}, states.map(([name, count]) => h("tr", {}, h("td", { text: name }), h("td", { text: String(count) }))))))
        : h("p", { class: "muted", text: "No requests yet." }));
  }
  fill(root,
    h("p", {}, back),
    h("section", { class: "pui-card" },
      h("div", { class: "pui-card-header", text: title }),
      h("div", { class: "pui-card-content" }, body)));
}
