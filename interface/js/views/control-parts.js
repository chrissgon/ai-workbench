// Small pieces the three tabs of the Control room share: the loading line, the failed-read notice, the empty block, a chip,
// a section heading. Everything from the service is put in as text.

import { h } from "../dom.js";

export const FAILED_TITLE = "The read failed";

/** The loading line: a static ring and the sentence, `aria-busy`. */
export function loadingCard(text) {
  return h("div", { class: "wb-loading", "aria-busy": "true" }, h("span", { class: "wb-ring", "aria-hidden": "true" }), text);
}

/** A notice with an error border: a title over the service's own message (text, in the monospace face, free to break anywhere). */
export function failedCard(title, message) {
  return h("div", { class: "wb-failed", role: "alert" },
    h("strong", { class: "wb-failed-title", text: title }),
    h("span", { class: "wb-failed-text", text: message }));
}

/** The dashed block that says a list is empty. */
export function emptyBlock(text) {
  return h("div", { class: "wb-empty-block", text });
}

/** A chip in the library's classes. */
export function chip(className, text) {
  return h("span", { class: `${className} wb-chip-s`, text });
}

/** A section heading above a table: small, spaced, upper-cased by the stylesheet. */
export function eyebrow(text) {
  return h("span", { class: "wb-eyebrow", text });
}

/** A value in the monospace face. */
export function code(text) {
  return h("code", { class: "wb-code", text });
}

/** A table cell with the label a phone prints before it when the table is stacked. */
export function cell(label, ...children) {
  return h("td", { "data-label": label }, ...children);
}

/**
 * Make `parent`'s children exactly `nodes`, in order, without removing and re-inserting a node that is already in place: a
 * focused field kept in the list keeps its focus (replaceChildren would drop it). New nodes are inserted before the node
 * that stands where they belong; nodes not in the list are removed.
 */
export function reconcile(parent, nodes) {
  nodes.forEach((node, i) => {
    const here = parent.children[i];
    if (here !== node) parent.insertBefore(node, here || null);
  });
  while (parent.children.length > nodes.length) parent.children[nodes.length].remove();
}

/** A card on the sunken ground that holds a table. */
export function tableCard(table, className = "") {
  return h("div", { class: `pui-card wb-sunken-card${className ? ` ${className}` : ""}` }, table);
}
