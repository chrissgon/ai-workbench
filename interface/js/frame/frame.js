// The shared frame of every scene screen (handoff README section 4): the header (back, breadcrumbs, project switcher), the
// KPI cards, the door to the control room, the waiting list or its button, the tracking bar, the panel slot, the scene
// container and, for a phone, the bottom bar. Built once; a screen fills it through the methods below. Every control has an
// accessible name and a keyboard path; no element carries a style attribute.

import { h } from "../dom.js";
import * as router from "../router.js";
import { createKpis } from "./kpis.js";
import { createNav } from "./header.js";
import { icon } from "./icons.js";
import { createSheet } from "./sheet.js";
import { createSwitcher } from "./switcher.js";
import { createTrack } from "./track.js";
import { createWaitingCard, createWaitingMenu } from "./waiting.js";

const SCREEN_NAMES = { city: "City", building: "Building", floor: "Floor", lobby: "Lobby", control: "Control room" };
const ANNOUNCE_EVERY_MS = 2000;

/** Create the frame in `root` and return its parts and methods. handlers: {onSelectProject(id), onForgetToken(), onRetry()}. */
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
  const track = createTrack({ onOpenSteps: (title, body, opener) => sheet.open(title, body, opener) });

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
  const main = h("main", { class: "wb-main" }, heading, noticeBox);
  const frame = h("div", { class: "wb-frame", "data-screen": "city" }, skipPanel, skipList, live, header, sceneArea, main, track.el, actions, sheet.el);
  root.replaceChildren(frame);

  let doorTarget = null;
  let shownRoute = null;
  let shownNotice = "null";
  door.addEventListener("click", () => {
    if (doorTarget) window.location.hash = doorTarget;
  });
  const onKey = (event) => {
    if (event.key === "Escape") closeLists();
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

  return {
    el: frame, sceneHost, main, noticeBox, nav,
    /** Take the frame down: the listeners it put on the document go, so that entering the token again does not stack them. */
    destroy() {
      document.removeEventListener("keydown", onKey);
      switcher.destroy();
      waitingMenu.destroy();
      clearTimeout(announcing);
      queue.length = 0;
      frame.remove();
    }, switcher, kpis, waitingCard, waitingMenu, track, sheet, heading, closeLists,
    /** Set the screen: route (router.parse), the project's name (or null), the agent's display name for a floor. */
    setScreen(route, { projectName, projectId, leaf }) {
      frame.dataset.screen = route.screen;
      heading.textContent = SCREEN_NAMES[route.screen] || "City";
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
      if (spec.lead) band.append(h("p", { class: "wb-notice-lead", text: spec.lead }));
      band.append(h("p", { class: spec.mono ? "wb-notice-text mono" : "wb-notice-text", text: spec.text }));
      if (spec.retry) {
        const button = h("button", { class: "pui-btn pui-surface pui-outline", type: "button", text: "Try again" });
        button.addEventListener("click", () => handlers.onRetry());
        band.append(button);
      }
      for (const extra of spec.more || []) band.append(h("p", { class: "wb-notice-text mono", text: extra }));
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
    /** The free rectangle for the scene, in pixels from the scene area's edges, measured from what is on the page now. */
    insets(rightEl) {
      const scene = sceneArea.getBoundingClientRect();
      const kpiRect = kpis.el.getBoundingClientRect();
      if (phone.matches) {
        return { left: 8, right: 8, top: Math.max(8, kpiRect.bottom - scene.top + 12), bottom: 6, pad: 1.02 };
      }
      const headerRect = header.getBoundingClientRect();
      const noticeRect = noticeBox.hidden ? null : noticeBox.getBoundingClientRect();
      const trackRect = track.el.getBoundingClientRect();
      const right = rightEl && !rightEl.hidden ? rightEl.getBoundingClientRect() : null;
      return {
        left: kpiRect.right - scene.left + 16,
        right: right && right.width > 0 ? scene.right - right.left + 16 : 16,
        top: Math.max(headerRect.bottom, noticeRect ? noticeRect.bottom : 0) - scene.top + 12,
        bottom: trackRect.height > 0 ? scene.bottom - trackRect.top + 16 : 16,
        pad: 1.04,
      };
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
