// F-7 the panel shell: a card at the right of the scene (a section of the page on a phone) with a header (a tinted tile, a
// title and a line under it) and a body. A screen fills the body.

import { h } from "../dom.js";
import { icon } from "./icons.js";

let counter = 0;

/** A panel for a screen. spec: {title, subtitle, icon, tone, width}. Returns {el, body}. */
export function createPanel(spec) {
  counter += 1;
  const titleId = `wb-panel-title-${counter}`;
  const body = h("div", { class: "wb-panel-body" });
  const el = h("section", { class: `pui-card wb-panel wb-panel-${spec.width || "narrow"}`, role: "region", "aria-labelledby": titleId, id: "wb-panel", tabindex: "-1" },
    h("div", { class: "wb-panel-head" },
      h("span", { class: `wb-tile pui-soft pui-${spec.tone || "theme"}` }, icon(spec.icon || "building-2", 18)),
      h("div", { class: "wb-panel-titles" }, h("strong", { class: "wb-panel-title", id: titleId, text: spec.title }),
        h("span", { class: "wb-panel-sub", text: spec.subtitle || "" }))),
    body);
  return { el, body };
}
