// The sheet of a phone (OPEN-13): a `dialog.pui-modal` that holds a list (the tracking bar's steps, the waiting list). It
// is modal, closes with Escape or its button, and returns the focus to the control that opened it.

import { h } from "../dom.js";
import { icon } from "./icons.js";

/** Create a sheet host. Returns {el, open(title, body, opener)}. */
export function createSheet() {
  const heading = h("strong", { class: "wb-sheet-title", text: "" });
  const close = h("button", { class: "pui-btn pui-surface pui-outline wb-sheet-close", type: "button", "aria-label": "Close" }, icon("x", 16));
  const body = h("div", { class: "wb-sheet-body" });
  const card = h("div", { class: "pui-card wb-sheet-card" }, h("div", { class: "wb-sheet-head" }, heading, close), body);
  const el = h("dialog", { class: "pui-modal wb-sheet", "aria-label": "List" }, card);
  let opener = null;
  close.addEventListener("click", () => el.close());
  el.addEventListener("click", (event) => {
    if (event.target === el) el.close();
  });
  el.addEventListener("close", () => {
    if (opener && opener.isConnected) opener.focus();
    opener = null;
  });
  // A link inside the sheet goes somewhere else on this page: close first.
  body.addEventListener("click", (event) => {
    if (event.target.closest("a")) el.close();
  });
  return {
    el,
    open(title, content, from) {
      heading.textContent = title;
      el.setAttribute("aria-label", title);
      body.replaceChildren(content);
      opener = from || null;
      if (!el.open) el.showModal();
    },
    close() {
      if (el.open) el.close();
    },
  };
}
