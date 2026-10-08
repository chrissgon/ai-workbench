// The Building screen (handoff building.md): the cutaway of a project, one floor per area agent from the lobby up, one compact
// floor card at the scene's top right for the floor that is hovered or selected (name, state word, mode plate, runs and spend), and
// in the panel the project's facts and the floors list, the HTML twin of the scene, whose rows are the same card. It owns the scene engine for as long as the screen is
// shown. What the frame holds (header, KPI cards, tracking bar) is filled by the page; this fills the scene and the panel.
// It only reads: `artifacts` (for the sheets and drawers of each floor) and, for "Project state", one file under docs/.

import * as api from "../api.js";
import { fill, h } from "../dom.js";
import * as fm from "../floor-model.js";
import { createViewer } from "../floor/viewer.js";
import { chip } from "../floor/widgets.js";
import { arrowNav, keepFocus } from "../frame/arrows.js";
import { icon } from "../frame/icons.js";
import * as router from "../router.js";
import { NoWebGL } from "../scene/engine.js";
import { floorCardNode, plateNode } from "../scene/plates.js";
import { worldModel } from "../world-model.js";

export const PLATE_GAP_X = 14;
const STATE_PATH = "docs/workbench/state.md";
const ARTIFACTS_EVERY_MS = 20000;

/** Create the Building in `frame`. env: {refresh()}. Returns {update({snapshot, route, now}), dispose(), stats()}. */
export function createBuildingView(frame, env) {
  let engine = null;
  let disposed = false;
  let last = null;
  let documents = null;
  let documentsAt = 0;
  let reading = false;
  let hover = null;
  let focusName = null;
  let shown = "";
  let listShown = "";
  let projectId = null;

  // --- the panel ---------------------------------------------------------------------------------------------------------------
  const title = h("strong", { class: "wb-panel-title", id: "wb-building-title", text: "" });
  const panelSub = h("span", { class: "wb-panel-sub", text: "Project · one floor per area agent" });
  const head = h("div", { class: "wb-panel-head" },
    h("span", { class: "wb-tile pui-soft pui-theme" }, icon("building-2", 18)), h("div", { class: "wb-panel-titles" }, title, panelSub));
  const factsBox = h("dl", { class: "wb-facts" });
  const stateLink = h("button", { class: "pui-btn pui-link wb-state-link", type: "button", text: "Project state" });
  const listHeading = h("h2", { class: "wb-list-heading", text: "Floors, top to bottom" });
  const list = h("ul", { class: "pui-list pui-hoverable wb-floor-list", "aria-label": "Floors, top to bottom" });
  const moreLine = h("p", { class: "wb-muted wb-more-line", hidden: true });
  const body = h("div", { class: "wb-panel-body wb-building-body" }, factsBox, h("div", {}, stateLink), h("section", { id: "wb-scene-list", tabindex: "-1", class: "wb-floor-section" }, listHeading, moreLine, list));
  const panel = h("section", { class: "pui-card wb-panel wb-panel-building", role: "region", "aria-labelledby": "wb-building-title", id: "wb-panel", tabindex: "-1" }, head, body);
  frame.main.append(panel);
  arrowNav(list, "a.wb-floor-row");

  // the project state file, in a dialog with the same viewer the Floor uses
  const stateDialog = h("dialog", { class: "pui-modal wb-viewer-dialog", "aria-label": "Project state" });
  const viewer = createViewer({ onClose: () => stateDialog.close() });
  stateDialog.append(viewer.el);
  stateDialog.addEventListener("close", () => {
    viewer.close();
    if (stateLink.isConnected) stateLink.focus();
  });
  stateDialog.addEventListener("click", (event) => {
    if (event.target === stateDialog) stateDialog.close();
  });
  frame.el.append(stateDialog);
  stateLink.addEventListener("click", () => {
    if (!projectId) return;
    stateDialog.showModal();
    viewer.load(projectId, STATE_PATH);
    viewer.focus();
  });

  // the phone's floor buttons and counter, over the scene
  const above = h("button", { class: "pui-btn pui-surface pui-outline wb-floor-step", type: "button", "aria-label": "Floor above" }, icon("chevron-down", 16));
  above.classList.add("is-above");
  const below = h("button", { class: "pui-btn pui-surface pui-outline wb-floor-step", type: "button", "aria-label": "Floor below" }, icon("chevron-down", 16));
  const counter = h("span", { class: "wb-floor-counter", "aria-live": "polite" });
  const steps = h("div", { class: "wb-floor-steps" }, above, counter, below);
  const sceneArea = frame.sceneHost.parentElement || frame.sceneHost;
  sceneArea.append(steps);

  // --- the scene -----------------------------------------------------------------------------------------------------------------
  function open(id) {
    if (disposed || !last) return;
    if (id === "door") {
      window.location.hash = router.controlHash(projectId);
      return;
    }
    const name = String(id).replace(/^floor:/, "");
    const view = fm.building(last.snapshot, projectId);
    const row = view && view.rows.find((r) => r.name === name);
    if (!row) return;
    // The floor goes on as the click lands: the other floors shrink while the camera closes on it, and the route changes in the same moment.
    if (engine) engine.flyTo(id);
    window.location.hash = row.link;
  }

  // `fromScene`: the scene itself is the one hovered (its own pick already drew the outline): the engine is not told again, or a hover of
  // the door (not a floor, so name is null here) would clear the outline the scene just drew.
  function highlightRow(name, fromScene = false, source = "pointer") {
    hover = name;
    for (const li of list.querySelectorAll ? list.querySelectorAll(".wb-floor-item") : []) {
      li.classList.toggle("is-hover", li.getAttribute("data-floor") === name);
    }
    if (engine && !fromScene) engine.highlight(name ? `floor:${name}` : null, source);
    drawCorner();
  }

  // The phone's floor card at the scene's top right: the floor the pointer or the focus is on (the phone shows one floor at a time).
  // Desktop and tablet keep the plates beside the floors (WP-9.10), so there is no card there. The same component as each row of the floors list.
  let cornerKey = "";
  function drawCorner() {
    if (!engine || !last) return;
    const view = fm.building(last.snapshot, projectId);
    let row = null;
    if (phone.matches && view && last.snapshot.loaded) {
      const wanted = hover || focusOf(view);
      row = view.rows.slice(0, 8).find((r) => r.name === wanted) || null;
    }
    const card = row ? fm.cardOf(row) : null;
    const key = JSON.stringify(card);
    if (key === cornerKey) return;
    cornerKey = key;
    engine.setCorner(card ? floorCardNode(card, { class: "is-corner", "aria-hidden": "true" }) : null);
  }

  try {
    engine = frame.acquireWorld({
      label: "Building, loading",
      getInsets: () => {
        const base = frame.insets(panel);
        if (frame.isPhone()) return { left: 4, right: 70, top: base.top, bottom: 40, pad: 0.98, cornerRight: 10 };
        return { ...base, right: base.right + frame.plateWidth() + PLATE_GAP_X, plateRight: base.right };
      },
      onOpen: open,
      onHover: (id) => highlightRow(id && String(id).startsWith("floor:") ? String(id).slice(6) : null, true),
      onUnavailable: () => frame.sceneUnavailable(true),
      onRestored: () => frame.sceneUnavailable(false),   // the context came back: the host is shown again
    });
    frame.sceneUnavailable(false);
  } catch (e) {
    if (!(e instanceof NoWebGL)) throw e;
    frame.sceneUnavailable(true);
  }
  const observer = new ResizeObserver(() => { if (engine) engine.refit(); });
  observer.observe(frame.track.el);
  observer.observe(frame.kpis.el);
  observer.observe(panel);
  observer.observe(frame.noticeBox);
  const phone = window.matchMedia("(max-width: 639px)");
  const onPhone = () => { shown = ""; redraw(); };
  phone.addEventListener("change", onPhone);

  // plates in the overlay are pointer targets: hovering one outlines its floor, a click opens it
  const overPlate = (event) => (event.target && event.target.closest ? event.target.closest(".wb-plate") : null);
  const onOver = (event) => {
    const plate = overPlate(event);
    if (plate) highlightRow(plate.getAttribute("data-floor"));
  };
  const onOut = (event) => {
    if (overPlate(event)) highlightRow(null);
  };
  const onClick = (event) => {
    const plate = overPlate(event);
    if (plate) open(`floor:${plate.getAttribute("data-floor")}`);
  };
  frame.sceneHost.addEventListener("pointerover", onOver);
  frame.sceneHost.addEventListener("pointerout", onOut);
  frame.sceneHost.addEventListener("click", onClick);

  // --- reading the documents ------------------------------------------------------------------------------------------------------
  async function readDocuments() {
    if (reading || disposed || !projectId) return;
    reading = true;
    try {
      const body = await api.artifacts(projectId);
      documents = Array.isArray(body.artifacts) ? body.artifacts : [];
      documentsAt = Date.now();
      shown = "";
      redraw();
    } catch (e) {
      documentsAt = Date.now();
      if (!documents) documents = [];
    }
    reading = false;
  }

  // the live region says when an agent starts working ("Engineering agent started working"), never on the first read
  const worked = new Map();
  function announceWork(view) {
    for (const row of view.rows) {
      const was = worked.get(row.name);
      if (was === false && row.state === "working") frame.announce(`${row.label} agent started working`);
      worked.set(row.name, row.state === "working");
    }
  }

  // --- drawing -------------------------------------------------------------------------------------------------------------------
  function factRow(label, value) {
    return [h("dt", { class: "wb-muted", text: label }), h("dd", {}, value)];
  }

  function drawFacts(view) {
    const f = view.facts;
    const running = f.running ? h("a", { class: "pui-link pui-theme", href: f.running.link, text: `task #${f.running.id}${f.running.title ? ` · ${f.running.title}` : ""}` }) : "Nothing is running";
    fill(factsBox,
      factRow("Configuration", chip(f.configuration, f.accepted ? "pui-success pui-soft" : "pui-warn pui-soft")),
      f.accepted ? factRow("Running now", running) : null,
      f.accepted ? factRow("Request", f.request ? `#${f.request.id} ${f.request.title}` : "No request is open") : null,
      f.accepted ? factRow("Waiting for you", format_decisions(f.waiting)) : null);
  }

  function format_decisions(n) {
    return `${n} decision${n === 1 ? "" : "s"}`;
  }

  function floorItem(row, view) {
    // the plate beside the floor, as it is: one component in two places (the phone's corner card is the compact one)
    const link = plateNode(fm.plateOf(row, view.tag ? view.tag.floor === row.name : false), { class: "wb-floor-row is-row", href: row.link, "aria-label": row.linkName }, "a");
    link.addEventListener("click", (event) => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
      event.preventDefault();
      open(`floor:${row.name}`);
    });
    link.addEventListener("pointerenter", () => highlightRow(row.name));
    link.addEventListener("pointerleave", () => highlightRow(null));
    link.addEventListener("focus", () => highlightRow(row.name, false, "keyboard"));
    link.addEventListener("blur", () => highlightRow(null, false, "keyboard"));
    return h("li", { class: "pui-list-item wb-floor-item", "data-floor": row.name }, link);
  }

  function drawList(view, loading) {
    let rows;
    if (loading) rows = [h("li", { class: "pui-list-item wb-empty", text: "Loading the floors..." })];
    else {
      rows = [...view.rows].reverse().map((row) => floorItem(row, view));
      if (view.none) rows.unshift(h("li", { class: "pui-list-item wb-empty", text: "This project has no area agents in its configuration." }));
    }
    keepFocus(list, () => list.replaceChildren(...rows));
    moreLine.hidden = !(view && view.more > 0);
    if (view && view.more > 0) moreLine.textContent = `+${view.more} more floor${view.more === 1 ? "" : "s"}`;
  }

  /** The floor drawn alone on a phone: the one the person chose, else the work order's, else the first with a decision, else the top. */
  function focusOf(view) {
    const names = view.rows.slice(0, 8).map((r) => r.name);
    if (focusName && names.includes(focusName)) return focusName;
    if (view.tag && names.includes(view.tag.floor)) return view.tag.floor;
    const waiting = [...view.rows].reverse().find((r) => r.decisions > 0 || r.state === "working");
    return (waiting || view.rows[view.rows.length - 1]).name;
  }

  function stepFloor(delta, view) {
    const names = view.rows.slice(0, 8).map((r) => r.name);
    const at = names.indexOf(focusOf(view));
    const next = Math.max(0, Math.min(names.length - 1, at + delta));
    focusName = names[next];
    shown = "";
    redraw();
  }

  function redraw() {
    if (disposed || !last) return;
    const { snapshot } = last;
    const view = fm.building(snapshot, projectId);
    const loading = !snapshot.loaded || !view;
    title.textContent = view ? view.name : "";
    steps.hidden = true;
    if (!loading) {
      title.textContent = view.name;
      drawFacts(view);
      const sig = JSON.stringify(view.rows.map((r) => [fm.plateOf(r, false), r.link, r.linkName]));
      if (sig !== listShown) {
        listShown = sig;
        drawList(view, false);
      }
    } else if (listShown !== "loading") {
      listShown = "loading";
      fill(factsBox);
      drawList(null, true);
    }
    if (!engine) return;
    let label = "Building, loading";
    let frameFloor = null;
    if (!loading) {
      const isPhone = phone.matches;
      frameFloor = isPhone ? focusOf(view) : null;
      label = fm.buildingLabel(view);
      if (isPhone) {
        const names = view.rows.slice(0, 8).map((r) => r.name);
        const at = names.indexOf(frameFloor);
        const row = view.rows.find((r) => r.name === frameFloor);
        steps.hidden = names.length < 2;
        above.disabled = at >= names.length - 1;
        below.disabled = at <= 0;
        counter.textContent = `${at + 1}/${names.length}`;
        counter.setAttribute("aria-label", `Floor ${at + 1} of ${names.length}, ${row ? row.label : ""}`);
        above.onclick = () => stepFloor(1, view);
        below.onclick = () => stepFloor(-1, view);
      }
    }
    const model = worldModel(snapshot, last.now, { selectedId: projectId, focus: projectId, frame: frameFloor, documents, ready: !loading });
    if (!loading) announceWork(view);
    drawCorner();
    const key = JSON.stringify([model, label]);
    if (key !== shown) {
      shown = key;
      engine.show("world", model, label);
    }
  }

  return {
    /** data: {snapshot, route, now}. */
    update(data) {
      last = data;
      projectId = data.route.project;
      if (documents === null || Date.now() - documentsAt > ARTIFACTS_EVERY_MS) readDocuments();
      redraw();
    },
    dispose() {
      disposed = true;
      observer.disconnect();
      phone.removeEventListener("change", onPhone);
      frame.sceneHost.removeEventListener("pointerover", onOver);
      frame.sceneHost.removeEventListener("pointerout", onOut);
      frame.sceneHost.removeEventListener("click", onClick);
      viewer.close();
      panel.remove();   // the scene is the frame's: the City takes it over (the building closes), or the frame takes it down
      stateDialog.remove();
      steps.remove();
      frame.sceneUnavailable(false);
    },
    /** For the page's checks: the engine's counters, or null without WebGL. */
    stats() {
      return engine ? engine.stats() : null;
    },
  };
}
