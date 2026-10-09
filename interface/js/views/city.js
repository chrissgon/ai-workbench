// The City screen (handoff city.md): the isometric plot with one building per project, the HTML list of the same
// buildings, the waiting list. It owns the scene engine for as long as the screen is shown. What the frame holds (header,
// KPI cards, tracking bar) is filled by the page; this fills the scene and the City's own panels.

import * as api from "../api.js";
import { h } from "../dom.js";
import { arrowNav } from "../frame/arrows.js";
import { bindDrawer, createGrip } from "../frame/drawer.js";
import { icon } from "../frame/icons.js";
import * as model from "../model.js";
import * as router from "../router.js";
import { NoWebGL } from "../scene/engine.js";
import { worldModel } from "../world-model.js";
import { createProjectsPanel } from "./city-projects.js";
import { projectsOf, readableProject } from "./city-projects-model.js";

/** Create the City screen in `frame`. Returns {update(data), dispose()}. */
export function createCityView(frame) {
  let engine = null;
  let disposed = false;
  let shown = "";

  const listHeading = h("div", { class: "pui-card-header wb-buildings-head", text: "Projects" });
  const list = h("ul", { class: "pui-list pui-hoverable wb-building-list", "aria-label": "Projects" });
  // A-24: a project enters the service, or leaves it, by the person's hand in the terminal; the panel shows the restart line with Copy.
  let lastSnapshot = null;
  const projectsPanel = createProjectsPanel({
    readStart: async () => {
      const id = readableProject(lastSnapshot);
      if (id === null) return "";
      const got = await api.connections(id);
      return got && got.service && typeof got.service.start === "string" ? got.service.start : "";
    },
  });
  // The two controls stand outside the list card: on a desktop the list is clipped until it has the keyboard focus, so a control inside it could not be reached
  // with a pointer. On a desktop the box floats at the scene's right edge; on a phone it is the first part of the sheet, hidden while the sheet is collapsed.
  const addButton = h("button", { class: "pui-btn pui-surface pui-outline wb-small-button wb-add-project-button", type: "button", "data-key": "add-project", "aria-expanded": "false", text: "Add a project" });
  const leaveButton = h("button", { class: "pui-btn pui-surface pui-outline wb-small-button wb-leave-project-button", type: "button", "data-key": "leave-project", "aria-expanded": "false", text: "Leave a project" });
  const syncExpanded = () => {
    const open = projectsPanel.isOpen();
    addButton.setAttribute("aria-expanded", String(open));
    leaveButton.setAttribute("aria-expanded", String(open));
  };
  addButton.addEventListener("click", () => {
    projectsPanel.openAdd();
    syncExpanded();
  });
  leaveButton.addEventListener("click", () => {
    projectsPanel.openLeave();
    syncExpanded();
  });
  projectsPanel.el.addEventListener("click", () => setTimeout(syncExpanded, 0));
  const projectsBox = h("section", { class: "pui-card wb-city-projects", "aria-label": "Projects of the service" }, h("div", { class: "wb-city-projects-bar" }, addButton, leaveButton), projectsPanel.el);
  const buildings = h("section", { class: "pui-card wb-buildings", id: "wb-scene-list", tabindex: "-1" }, listHeading, list);
  const empty = h("div", { class: "pui-card wb-empty-card", hidden: true },
    h("div", { class: "pui-card-content" }, h("p", { text: "The service has no project. Start it with --project <folder>." })));
  // On a phone the two lists are one bottom sheet, collapsed to a header line each (A-27, A-28); elsewhere the wrapper takes no box and the
  // lists stand where they always did.
  const grip = createGrip();
  const sheet = h("div", { class: "pui-card wb-drawer wb-city-drawer" }, grip, projectsBox, h("div", { class: "wb-drawer-scroll" }, buildings, frame.waitingCard.el));
  const drawer = bindDrawer(sheet, { screen: "city", grip, handles: ".wb-buildings-head, .wb-wait-head" });
  frame.main.append(sheet, empty);
  arrowNav(list, "a.wb-building-link");   // SCREEN-2: arrows move between the buildings, Enter opens

  // A click: the building opens where it stands and the camera starts at once (the world's own targets), and the route changes in the same
  // moment, as the prototype's `go` does: the panels do not wait for the scene and the scene does not wait for them.
  function open(id) {
    if (disposed) return;
    if (engine) engine.flyTo(id);
    window.location.hash = router.buildingHash(id);
  }

  try {
    engine = frame.acquireWorld({
      label: "City, loading",
      getInsets: () => frame.insets(frame.waitingCard.el),
      onOpen: open,
      onUnavailable: () => frame.sceneUnavailable(true),
      onRestored: () => frame.sceneUnavailable(false),   // the context came back: the host is shown again
    });
    frame.sceneUnavailable(false);
  } catch (e) {
    if (!(e instanceof NoWebGL)) throw e;
    frame.sceneUnavailable(true);
  }
  // A panel that changes size changes the free rectangle: the scene is fitted again (one frame), never on a timer.
  // The project box ends above the "Waiting for you" card, whatever its height (a desktop: the box floats at the right edge, the card stands under it).
  const fitBox = () => projectsBox.style.setProperty("--wb-wait-h", `${frame.waitingCard.el.offsetHeight || 0}px`);
  const observer = new ResizeObserver(() => { if (engine) engine.refit(); });
  const boxObserver = new ResizeObserver(fitBox);
  boxObserver.observe(frame.waitingCard.el);
  observer.observe(frame.track.el);
  observer.observe(frame.kpis.el);
  observer.observe(frame.waitingCard.el);
  observer.observe(frame.noticeBox);
  observer.observe(sheet);

  function renderList(buildingsOf) {
    const rows = buildingsOf.map((b) => {
      const link = h("a", { class: "wb-building-link", href: router.buildingHash(b.id), "aria-label": model.linkNameOf(b) },
        h("span", { class: `wb-dot${b.runningTask !== null ? " is-running" : ""}` }),
        h("strong", { class: "wb-building-name", text: b.name }),
        b.accepted
          ? (b.decisions > 0 ? h("span", { class: "pui-badge pui-warn pui-soft pui-rounded-full", text: String(b.decisions) }) : null)
          : h("span", { class: "pui-chip pui-warn pui-soft wb-chip-small", text: "Not accepted" }),
        h("span", { class: "wb-building-sub", text: model.subOf(b) }),
        icon("chevron-right", 14));
      link.addEventListener("click", (event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
        event.preventDefault();
        open(b.id);
      });
      link.addEventListener("pointerenter", () => engine && engine.highlight(b.id));
      link.addEventListener("pointerleave", () => engine && engine.highlight(null));
      link.addEventListener("focus", () => engine && engine.highlight(b.id, "keyboard"));
      link.addEventListener("blur", () => engine && engine.highlight(null, "keyboard"));
      const leave = h("button", { class: "pui-btn pui-link wb-leave-project", type: "button", "data-key": `leave-${b.id}`, "aria-label": `Leave project ${b.name}`, text: "Leave" });
      leave.addEventListener("click", () => projectsPanel.openLeave(b.id));
      return h("li", { class: "pui-list-item wb-building-item" }, link, leave);
    });
    list.replaceChildren(...rows);
  }

  return {
    /**
     * data: {city (model.city), selectedId, state: "loading", "error" (the first read failed) or "ready", snapshot, now}.
     */
    update({ city, selectedId, state, snapshot, now }) {
      lastSnapshot = snapshot;
      fitBox();
      projectsPanel.setProjects(projectsOf(snapshot));
      const key = JSON.stringify([city.buildings.map((b) => [b.id, b.name, b.accepted, b.decisions, b.runningTask]), state]);
      if (key !== shown) {
        shown = key;
        if (state === "loading") list.replaceChildren(h("li", { class: "pui-list-item wb-empty", text: "Loading the projects..." }));
        else if (state === "error") list.replaceChildren(h("li", { class: "pui-list-item wb-empty", text: "The projects could not be read." }));
        else if (city.buildings.length === 0) list.replaceChildren(h("li", { class: "pui-list-item wb-empty", text: "The service has no project." }));
        else renderList(city.buildings);
      }
      // "No project" is said only when a read answered with an empty list, never while loading or after a failed first read.
      empty.hidden = !model.emptyCityVisible(state, city.buildings.length);
      frame.waitingCard.set(city.waiting, state);
      if (engine) engine.show("world", worldModel(snapshot, now, { selectedId: null, marked: selectedId, focus: null, ready: state === "ready" }), city.canvasLabel);
    },
    dispose() {
      disposed = true;
      observer.disconnect();
      boxObserver.disconnect();   // the scene is the frame's: the Building takes it over, or the frame takes it down
      drawer.destroy();   // before the sheet leaves the page: the frame hears that nothing covers the scene
      buildings.remove();
      projectsBox.remove();
      empty.remove();
      frame.waitingCard.el.remove();
      sheet.remove();
      frame.sceneUnavailable(false);
    },
    /** For the page's checks: the engine's counters, or null without WebGL. */
    stats() {
      return engine ? engine.stats() : null;
    },
  };
}
