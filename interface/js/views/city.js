// The City screen (handoff city.md): the isometric plot with one building per project, the HTML list of the same
// buildings, the waiting list. It owns the scene engine for as long as the screen is shown. What the frame holds (header,
// KPI cards, tracking bar) is filled by the page; this fills the scene and the City's own panels.

import { h } from "../dom.js";
import { icon } from "../frame/icons.js";
import * as model from "../model.js";
import * as router from "../router.js";
import { createEngine, NoWebGL } from "../scene/engine.js";

/** Create the City screen in `frame`. Returns {update(data), dispose()}. */
export function createCityView(frame) {
  let engine = null;
  let disposed = false;
  let flying = false;
  let shown = "";

  const listHeading = h("div", { class: "pui-card-header wb-buildings-head", text: "Projects" });
  const list = h("ul", { class: "pui-list pui-hoverable wb-building-list", "aria-label": "Projects" });
  const buildings = h("section", { class: "pui-card wb-buildings", id: "wb-scene-list", tabindex: "-1" }, listHeading, list);
  const empty = h("div", { class: "pui-card wb-empty-card", hidden: true },
    h("div", { class: "pui-card-content" }, h("p", { text: "The service has no project. Start it with --project <folder>." })));
  frame.main.append(buildings, frame.waitingCard.el, empty);

  function open(id) {
    if (disposed || flying) return;
    flying = true;
    const go = () => {
      flying = false;
      if (!disposed) window.location.hash = router.buildingHash(id);
    };
    if (engine) engine.flyTo(id).then(go);
    else go();
  }

  try {
    engine = createEngine(frame.sceneHost, {
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
  const observer = new ResizeObserver(() => { if (engine) engine.refit(); });
  observer.observe(frame.track.el);
  observer.observe(frame.waitingCard.el);
  observer.observe(frame.noticeBox);

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
      link.addEventListener("focus", () => engine && engine.highlight(b.id));
      link.addEventListener("blur", () => engine && engine.highlight(null));
      return h("li", { class: "pui-list-item wb-building-item" }, link);
    });
    list.replaceChildren(...rows);
  }

  return {
    /**
     * data: {city (model.city), selectedId, state: "loading", "error" (the first read failed) or "ready"}.
     */
    update({ city, selectedId, state }) {
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
      if (engine) engine.show("city", model.sceneModel(city.buildings, selectedId, state === "ready"), city.canvasLabel);
    },
    dispose() {
      disposed = true;
      observer.disconnect();
      if (engine) engine.dispose();
      buildings.remove();
      empty.remove();
      frame.waitingCard.el.remove();
      frame.sceneUnavailable(false);
    },
    /** For the page's checks: the engine's counters, or null without WebGL. */
    stats() {
      return engine ? engine.stats() : null;
    },
  };
}
