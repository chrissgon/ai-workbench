// The project list: what GET /api/v1/projects returned, as a plain list of cards.

import { h, fill } from "../dom.js";

function accepted(project) {
  return Boolean(project.config && project.config.accepted);
}

function card(project) {
  const ok = accepted(project);
  const facts = h("ul", { class: "facts" });
  if (ok) {
    facts.append(
      h("li", {}, h("span", { class: "muted", text: "Open decisions: " }), String(project.open_pending ?? 0)),
      h("li", {}, h("span", { class: "muted", text: "Running task: " }),
        project.running_task === null || project.running_task === undefined ? "none" : `#${project.running_task}`));
  }
  return h("li", {},
    h("article", { class: "pui-card project-card" },
      h("div", { class: "pui-card-header" },
        h("a", { class: "project-link", href: `#/p/${project.id}`, text: project.name })),
      h("div", { class: "pui-card-content" },
        h("div", { class: "row" },
          h("span", { class: `pui-chip pui-soft ${ok ? "pui-success" : "pui-warn"}`, text: ok ? "Accepted" : "Not accepted" })),
        project.message ? h("p", { class: "notice", text: project.message }) : null,
        facts)));
}

/** Draw the list from the body of GET /projects. */
export function showProjects(root, body, { onRefresh }) {
  const list = Array.isArray(body.projects) ? body.projects : [];
  const refresh = h("button", { class: "pui-btn pui-outline pui-surface", type: "button", text: "Refresh" });
  refresh.addEventListener("click", () => onRefresh());
  fill(root,
    h("div", { class: "row" }, h("h2", { text: "Projects" }), refresh),
    list.length
      ? h("ul", { class: "project-list" }, list.map(card))
      : h("p", { class: "muted", text: "The service has no project." }));
}
