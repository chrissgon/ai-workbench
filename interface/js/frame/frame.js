// The shared frame of every scene screen (handoff README section 4): the header (back, breadcrumbs, project switcher), the
// KPI cards, the door to the control room, the waiting list or its button, the tracking bar, the panel slot, the scene
// container and, for a phone, the bottom bar. Built once; a screen fills it through the methods below. Every control has an
// accessible name and a keyboard path; no element carries a style attribute.

import { h } from "../dom.js";
import * as router from "../router.js";
import { commandBlock } from "./command.js";
import { EVENT as DRAWER_EVENT } from "./drawer.js";
import { createKpis } from "./kpis.js";
import { createNav } from "./header.js";
import { icon } from "./icons.js";
import { createEngine } from "../scene/engine.js";
import { escapeStep, isField } from "./escape.js";
import { current as documentOrigin } from "./origin.js";
import { createSheet } from "./sheet.js";
import { createSwitcher } from "./switcher.js";
import { createTrack } from "./track.js";
import { createWaitingCard, createWaitingMenu } from "./waiting.js";

/**
 * What a rectangle that lies over the scene takes from it: {side, amount} or null. A tall part (the KPI column, the panel) is fixed to the
 * left or the right, a wide one (the header, the KPI row, the tracking bar) to the top or the bottom; the side is the nearer one.
 */
export function obstacleInset(rect, scene) {
  if (!(rect.width > 0 && rect.height > 0)) return null;
  const left = Math.max(rect.left, scene.left);
  const right = Math.min(rect.right, scene.right);
  const top = Math.max(rect.top, scene.top);
  const bottom = Math.min(rect.bottom, scene.bottom);
  if (right <= left || bottom <= top) return null;   // it does not touch the scene
  const wide = rect.width / scene.width > rect.height / scene.height;
  if (wide) {
    const nearTop = rect.top + rect.height / 2 < scene.top + scene.height / 2;
    return nearTop ? { side: "top", amount: rect.bottom - scene.top + 12 } : { side: "bottom", amount: scene.bottom - rect.top + 16 };
  }
  const nearLeft = rect.left + rect.width / 2 < scene.left + scene.width / 2;
  return nearLeft ? { side: "left", amount: rect.right - scene.left + 16 } : { side: "right", amount: scene.right - rect.left + 16 };
}

const SCREEN_NAMES = { city: "City", building: "Building", floor: "Floor", lobby: "Lobby", control: "Control room" };
const ANNOUNCE_EVERY_MS = 2000;

/** Create the frame in `root` and return its parts and methods. handlers: {onSelectProject(id), onSelectRequest(project, request), onForgetToken(), onRetry()}. */
export function createFrame(root, handlers) {
  const sheet = createSheet();
  const closeLists = () => {
    switcher.close();
    waitingMenu.close();
  };
  const switcher = createSwitcher({ onSelect: (id) => handlers.onSelectProject(id), onForgetToken: () => handlers.onForgetToken(), onOpen: () => waitingMenu.close() });
  const waitingMenu = createWaitingMenu({ onOpen: () => switcher.close(), onSheet: (title, body, opener) => sheet.open(title, body, opener) });
  const waitingCard = createWaitingCard();
  const nav = createNav();
  const kpis = createKpis();
  const track = createTrack({ onOpenSteps: (title, body, opener) => sheet.open(title, body, opener), onSelectRequest: (project, id) => handlers.onSelectRequest(project, id) });

  const skipPanel = h("a", { class: "wb-skip", href: "#wb-panel", text: "Skip to the panel" });
  const skipList = h("a", { class: "wb-skip", href: "#wb-scene-list", text: "Skip to the scene list" });
  const live = h("div", { class: "wb-sr", role: "status", "aria-live": "polite" });
  const heading = h("h1", { class: "wb-sr", tabindex: "-1", text: "City" });
  // A skip link moves the focus to its target by id. It never changes the hash: the hash is the router's, and a fragment
  // that is not a route would send the page back to the City.
  for (const link of [skipPanel, skipList]) {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const target = document.getElementById(link.getAttribute("href").slice(1)) || heading;
      target.focus();
    });
  }

  const door = h("button", { class: "pui-btn pui-surface pui-outline wb-door", type: "button", "aria-label": "Control room" },
    icon("server", 16), h("span", { class: "wb-door-label", text: "Control room" }));
  const actions = h("div", { class: "wb-actions" }, waitingMenu.el, door);
  const header = h("header", { class: "wb-header" }, nav.el, switcher.el);

  const sceneHost = h("div", { class: "wb-scene" });
  const fallback = h("p", { class: "wb-scene-fallback", hidden: true, text: "Your browser cannot draw the 3D scene; the panels have everything." });
  const sceneArea = h("div", { class: "wb-scene-area" }, sceneHost, fallback, kpis.el);

  const noticeBox = h("div", { class: "wb-notice-box", hidden: true });
  // On a phone the KPI row and the tracking bar float over the scene just above the bottom sheet (A-28): they are moved into this stack there, and
  // back to where they stand otherwise. Elsewhere the stack is empty and takes no box.
  const float = h("div", { class: "wb-float" });
  const main = h("main", { class: "wb-main" }, heading, noticeBox, float);
  const frame = h("div", { class: "wb-frame", "data-screen": "city" }, skipPanel, skipList, live, header, sceneArea, main, track.el, actions, sheet.el);
  root.replaceChildren(frame);

  let doorTarget = null;
  let shownRoute = null;
  let shownNotice = "null";
  door.addEventListener("click", () => {
    if (doorTarget) window.location.hash = doorTarget;
  });
  // Escape: the one handler (escape.js), in its order. The frame knows the route, what is open and where the Control room was opened from.
  let currentRoute = null;
  let currentHash = null;
  let controlFrom = null;
  const onKey = (event) => {
    if (event.key !== "Escape" || event.defaultPrevented || !currentRoute) return;
    const dialogs = [...document.querySelectorAll("dialog[open]")];
    const requestMenu = document.querySelector(".wb-req-menu:not([hidden])");
    const step = escapeStep({
      route: currentRoute, field: isField(document.activeElement), dialog: dialogs.length > 0,
      menu: switcher.isOpen() || waitingMenu.isOpen() || Boolean(requestMenu), selection: Boolean(world && world.hasSelection()), from: controlFrom, origin: documentOrigin(),
    });
    if (step.step === "none") return;
    event.preventDefault();
    if (step.step === "dialog") {
      const dialog = dialogs[dialogs.length - 1];
      const cancel = new Event("cancel", { cancelable: true });
      dialog.dispatchEvent(cancel);   // as the browser does: a dialog that refuses to be cancelled (a request in flight) stays
      if (!cancel.defaultPrevented) dialog.close();
    } else if (step.step === "menu") {
      closeLists();
      const chip = document.querySelector('.wb-req-chip[aria-expanded="true"]');
      if (chip) chip.click();
    } else if (step.step === "selection") {
      world.clearSelection();
    } else {
      window.location.hash = step.hash;
    }
  };
  document.addEventListener("keydown", onKey);

  // The live region: one sentence per change, at most one per two seconds.
  const queue = [];
  let announcing = null;
  function flush() {
    announcing = null;
    const next = queue.shift();
    if (!next) return;
    live.textContent = "";
    live.textContent = next;
    announcing = setTimeout(flush, ANNOUNCE_EVERY_MS);
  }

  const phone = window.matchMedia("(max-width: 639px)");

  function placeFloat() {
    if (phone.matches) float.append(kpis.el, track.el);
    else if (kpis.el.parentNode === float) {
      sceneArea.append(kpis.el);
      frame.insertBefore(track.el, actions);
    }
  }
  placeFloat();
  phone.addEventListener("change", placeFloat);

  // The bottom sheet (frame/drawer.js) says where it stands. At full on a phone it covers the scene: the cards over the scene go and the scene is paused.
  let covering = false;
  main.addEventListener(DRAWER_EVENT, (event) => {
    covering = Boolean(event.detail && event.detail.covering);
    frame.classList.toggle("is-sheet-full", covering);
    frame.classList.toggle("is-sheet-rising", Boolean(event.detail && event.detail.rising));   // a drag that has the sheet taller: the cards are put away while it lasts
    sceneArea.inert = covering;     // the camera buttons and the canvas leave the tab order while the sheet covers them
    if (world) world.setPaused(covering);
  });

  // The one scene of the City, the Building, the Floor and the Lobby (WP-9.11): it is made when the first of the screens asks for it, handed from one
  // to the next with its state (the building that is open, the floor, the camera) and taken down when the route leaves them all.
  let world = null;
  function releaseWorld() {
    if (!world) return;
    world.dispose();
    world = null;
  }

  return {
    el: frame, sceneHost, main, noticeBox, nav,
    /** Take the frame down: the listeners it put on the document go, so that entering the token again does not stack them. */
    destroy() {
      releaseWorld();
      document.removeEventListener("keydown", onKey);
      switcher.destroy();
      waitingMenu.destroy();
      clearTimeout(announcing);
      queue.length = 0;
      frame.remove();
    }, switcher, kpis, waitingCard, waitingMenu, track, sheet, heading, closeLists,
    /**
     * The world's engine for the City, the Building, the Floor or the Lobby screen: the one that is already drawing (its handlers become the screen's), else a new
     * one. It throws NoWebGL when the browser cannot draw the scene.
     */
    acquireWorld(options) {
      if (world) world.setOptions(options);
      else world = createEngine(sceneHost, options);
      if (covering) world.setPaused(true);
      return world;
    },
    /** Set the screen: route (router.parse), the project's name (or null), the agent's display name for a floor. */
    setScreen(route, { projectName, projectId, leaf }) {
      frame.dataset.screen = route.screen;
      heading.textContent = SCREEN_NAMES[route.screen] || "City";
      const hash = window.location.hash;
      if (hash !== currentHash) {
        // the Control room remembers the screen of the same project it was opened from (Escape goes back there)
        if (route.screen === "control" && currentRoute && currentRoute.screen !== "control" && currentRoute.project === route.project && currentRoute.screen !== "city") controlFrom = currentHash;
        else if (route.screen !== "control") controlFrom = null;
        currentHash = hash;
      }
      currentRoute = route;
      if (!["city", "building", "floor", "lobby"].includes(route.screen)) releaseWorld();   // the Control room draws its own scene
      const items = [{ label: "City", href: router.cityHash() }];
      if (route.screen !== "city" && projectName) {
        items.push({ label: projectName, href: router.buildingHash(route.project) });
        if (route.screen !== "building") items.push({ label: leaf || SCREEN_NAMES[route.screen] });
      }
      items[items.length - 1] = { label: items[items.length - 1].label };
      nav.set(items, router.parentHash(route));
      doorTarget = projectId ? router.controlHash(projectId) : null;
      door.disabled = !doorTarget;
      door.classList.toggle("is-selected", route.screen === "control");
      door.setAttribute("aria-current", route.screen === "control" ? "page" : "false");
      waitingMenu.el.hidden = route.screen === "city";
      const key = `${route.screen}|${route.project}|${route.agent}`;
      if (key !== shownRoute) closeLists();   // a poll redraws the same screen: an open list stays open
      shownRoute = key;
    },
    /** A band under the header: spec {kind: "error"|"info", text, mono?, retry?} or null. */
    notice(spec) {
      // Redrawn only when the notice changes: a poll that finds the same notice must not make a screen reader read an
      // alert again, nor take the focus from its "Try again" button.
      const key = JSON.stringify(spec);
      if (key === shownNotice) return;
      shownNotice = key;
      noticeBox.replaceChildren();
      noticeBox.hidden = !spec;
      if (!spec) return;
      const band = h("div", { class: `wb-notice${spec.kind === "error" ? " is-error" : ""}`, role: spec.kind === "error" ? "alert" : "status" });
      // The service's own sentence; the command it gave (`command`, the `next` of the refusal) is drawn with the component.
      const sentence = (text, command, mono) => (command
        ? commandBlock({ command, sentence: text })
        : h("p", { class: mono ? "wb-notice-text mono" : "wb-notice-text", text }));
      if (spec.lead) band.append(h("p", { class: "wb-notice-lead", text: spec.lead }));
      band.append(sentence(spec.text, spec.command, spec.mono));
      if (spec.retry) {
        const button = h("button", { class: "pui-btn pui-surface pui-outline", type: "button", text: "Try again" });
        button.addEventListener("click", () => handlers.onRetry());
        band.append(button);
      }
      for (const extra of spec.more || []) band.append(sentence(extra.text, extra.command, true));
      noticeBox.append(band);
    },
    /** Tell a screen reader: at most one sentence per two seconds. */
    announce(text) {
      if (!text || queue.includes(text)) return;
      queue.push(text);
      if (announcing === null) flush();
    },
    /** Show the one line that stands for the scene when WebGL is missing (or hide it). */
    sceneUnavailable(on) {
      fallback.hidden = !on;
      sceneHost.hidden = on;
      frame.classList.toggle("no-scene", on);
    },
    /**
     * The free rectangle for the scene, in pixels from the scene area's edges, measured from what is on the page now: every part of the page that
     * lies over the scene (the KPI cards, the header, the notice, the panel or the waiting card at the right, the tracking bar) takes the
     * side it is fixed to, so the scene's objects are fitted into what none of them covers. A part that does not touch the scene (the panel
     * docked below it on a narrow screen) takes nothing.
     */
    insets(rightEl) {
      const scene = sceneArea.getBoundingClientRect();
      if (phone.matches) {
        // The scene fills the whole upper part of the page; what lies over it is the notice at the top, and at the bottom the cards (the KPI row, the
        // tracking bar) and the sheet: the camera frames the city in what is left between them.
        const out = { left: 8, right: 8, top: 8, bottom: 8, pad: 1.02 };
        if (!noticeBox.hidden) out.top = Math.max(8, noticeBox.getBoundingClientRect().bottom - scene.top + 8);
        const covers = [float, ...main.querySelectorAll(".wb-drawer")].map((part) => part.getBoundingClientRect()).filter((rect) => rect.width > 0 && rect.height > 0);
        if (covers.length) out.bottom = Math.max(8, scene.bottom - Math.min(...covers.map((rect) => rect.top)) + 8);
        return out;
      }
      const out = { left: 16, right: 16, top: 16, bottom: 16, pad: 1.04 };
      const parts = [kpis.el, header, actions, noticeBox.hidden ? null : noticeBox, track.el, rightEl && !rightEl.hidden ? rightEl : null];
      for (const part of parts) {
        if (!part) continue;
        const take = obstacleInset(part.getBoundingClientRect(), scene);
        if (take) out[take.side] = Math.max(out[take.side], take.amount);
      }
      return out;
    },
    /** The width of a floor's plate in the stylesheet now (it narrows on a tablet). */
    plateWidth() {
      const value = parseFloat(getComputedStyle(frame).getPropertyValue("--wb-plate-w"));
      return Number.isFinite(value) && value > 0 ? value : 290;
    },
    /** Move the keyboard focus to the screen's first heading (a screen opened by keyboard). */
    focusHeading() {
      heading.focus({ preventScroll: true });
    },
    isPhone() {
      return phone.matches;
    },
  };
}
