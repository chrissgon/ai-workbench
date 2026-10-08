// The Lobby panel's tab list (design system "Tabs"): Conversation, Inbox with a count, Desk, Agent. The URL names the tab, so a tab
// is a button that sets the hash; Left and Right move to the next tab, Home and End jump to the first and the last.

import { h } from "../dom.js";
import * as router from "../router.js";
import { TABS } from "./lobby-model.js";

/** Create the tab list. Returns {el, set({project, selected, counts}), panelId(id)}. */
export function createTabs() {
  const el = h("div", { class: "wb-lobby-tabs", role: "tablist", "aria-label": "Lobby" });
  const buttons = new Map();
  let project = null;
  const panelId = (id) => `wb-lobby-panel-${id}`;
  const tabId = (id) => `wb-lobby-tab-${id}`;

  for (const [id, label] of TABS) {
    const count = h("span", { class: "pui-badge pui-warn pui-soft pui-rounded-full wb-lobby-tab-count", hidden: true, text: "" });
    const button = h("button", { class: "wb-lobby-tab", type: "button", role: "tab", id: tabId(id), "aria-controls": panelId(id), tabindex: "-1" },
      h("span", { text: label }), count);
    button.addEventListener("click", () => {
      if (project) window.location.hash = router.lobbyHash(project, id);
    });
    buttons.set(id, { button, count, label });
    el.append(button);
  }
  el.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    const ids = TABS.map(([id]) => id);
    const at = ids.findIndex((id) => buttons.get(id).button === document.activeElement);
    let next = at < 0 ? 0 : at;
    if (event.key === "ArrowRight") next = (at + 1) % ids.length;
    else if (event.key === "ArrowLeft") next = (at - 1 + ids.length) % ids.length;
    else if (event.key === "Home") next = 0;
    else next = ids.length - 1;
    event.preventDefault();
    buttons.get(ids[next]).button.focus();
    if (project) window.location.hash = router.lobbyHash(project, ids[next]);
  });

  return {
    el,
    panelId,
    tabId,
    /** counts: {inbox: n}; a count of 0 is not drawn. */
    set({ project: id, selected, counts }) {
      project = id;
      for (const [name, { button, count, label }] of buttons) {
        const on = name === selected;
        button.setAttribute("aria-selected", on ? "true" : "false");
        button.tabIndex = on ? 0 : -1;
        button.classList.toggle("is-selected", on);
        const n = counts && counts[name] ? counts[name] : 0;
        count.hidden = n <= 0;
        count.textContent = String(n);
        button.setAttribute("aria-label", n > 0 ? `${label}, ${n} waiting` : label);
      }
    },
  };
}
