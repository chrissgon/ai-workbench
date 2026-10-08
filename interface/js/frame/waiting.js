// F-4 "Waiting for you": the City's card, the header button and its menu on the other screens, and the list a phone sheet shows.
// A row is a link to the card where the decision is answered.

import { h } from "../dom.js";
import { arrowNav, keepFocus } from "./arrows.js";
import { icon } from "./icons.js";

/** The rows as a list of links. state: "ready", "loading" or "error"; rows: model.waitingRows. */
export function rowList(rows, state, { chevron = true } = {}) {
  if (state === "loading") return h("p", { class: "wb-empty", text: "Loading the projects..." });
  if (state === "error" && rows.length === 0) return h("p", { class: "wb-empty", text: "The decisions could not be read." });
  if (rows.length === 0) return h("p", { class: "wb-empty", text: "Nothing waits for you." });
  const list = h("ul", { class: "pui-list pui-hoverable wb-wait-list" }, rows.map((row) => h("li", { class: "pui-list-item wb-wait-item" },
    h("a", { class: `wb-wait-row${chevron ? "" : " no-chevron"}`, href: row.link, "aria-label": row.name },
      h("span", { class: "pui-badge pui-warn pui-soft wb-wait-kind", text: row.kind }),
      h("span", { class: "wb-wait-title", text: row.title }),
      h("span", { class: "wb-wait-where", text: row.where }),
      h("span", { class: "wb-wait-age", text: row.age }),
      chevron ? h("span", { class: "wb-wait-chev" }, icon("chevron-right", 14)) : null))));
  arrowNav(list, ".wb-wait-row");
  return list;
}

/** The card's header: a warn tile, the title, the count and "oldest first". */
function head(count) {
  return h("div", { class: "wb-wait-head" },
    h("span", { class: "wb-kpi-tile pui-soft pui-warn" }, icon("inbox", 16)),
    h("strong", { class: "wb-wait-heading", text: "Waiting for you" }),
    h("span", { class: "pui-badge pui-warn pui-soft pui-rounded-full", text: String(count) }),
    h("span", { class: "wb-wait-order", text: "oldest first" }));
}

/** The City's card. Returns {el, set(rows, state)}. */
export function createWaitingCard() {
  const body = h("div", { class: "wb-wait-body" });
  const el = h("section", { class: "pui-card wb-waiting", role: "region", "aria-label": "Waiting for you, loading", id: "wb-panel", tabindex: "-1" }, body);
  let shown = "";
  return {
    el,
    set(rows, state) {
      const key = JSON.stringify([rows, state]);
      if (key === shown) return;
      shown = key;
      el.setAttribute("aria-label", state === "loading" ? "Waiting for you, loading" : `Waiting for you, ${rows.length} decision${rows.length === 1 ? "" : "s"}`);
      keepFocus(body, () => body.replaceChildren(head(state === "loading" ? "..." : rows.length), rowList(rows, state)));
    },
  };
}

/** The header button of the other screens, with the menu it opens. Returns {el, set(rows, state), close(), button}. */
export function createWaitingMenu({ onOpen, onSheet }) {
  const count = h("span", { class: "pui-badge pui-warn pui-soft pui-rounded-full wb-wait-count", text: "..." });
  const button = h("button", { class: "pui-btn pui-surface pui-outline wb-wait-btn", type: "button", "aria-haspopup": "true", "aria-expanded": "false" },
    icon("inbox", 16), h("span", { class: "wb-wait-btn-label", text: "Waiting for you" }), count);
  const menu = h("div", { class: "pui-card wb-wait-menu", hidden: true, role: "region", "aria-label": "Waiting for you" });
  const el = h("div", { class: "wb-wait-menu-wrap" }, button, menu);
  let last = { rows: [], state: "loading" };
  let shownMenu = "";
  let open = false;
  const phone = window.matchMedia("(max-width: 639px)");

  function setOpen(next) {
    open = next;
    menu.hidden = !next;
    button.setAttribute("aria-expanded", String(next));
    if (next) onOpen();
  }
  button.addEventListener("click", () => {
    if (phone.matches) {
      onSheet("Waiting for you", rowList(last.rows, last.state), button);
      return;
    }
    setOpen(!open);
  });
  el.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && open) {
      event.stopPropagation();   // the page's one Escape handler must not go up as well
      setOpen(false);
      button.focus();
    }
  });
  const onPointerDown = (event) => {
    if (open && !el.contains(event.target)) setOpen(false);
  };
  document.addEventListener("pointerdown", onPointerDown);
  return {
    el, button,
    destroy() { document.removeEventListener("pointerdown", onPointerDown); },
    close() { if (open) setOpen(false); },
    isOpen: () => open,
    set(rows, state) {
      const key = JSON.stringify([rows, state]);
      if (key === shownMenu) return;
      shownMenu = key;
      last = { rows, state };
      count.textContent = state === "loading" ? "..." : String(rows.length);
      button.setAttribute("aria-label", state === "loading" ? "Waiting for you, loading" : `Waiting for you, ${rows.length} decision${rows.length === 1 ? "" : "s"}`);
      keepFocus(menu, () => menu.replaceChildren(rowList(rows, state, { chevron: false })));
    },
  };
}
