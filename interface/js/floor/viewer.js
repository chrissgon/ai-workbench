// The document viewer (handoff floor.md, "Document viewer"): a file under docs/ read with `artifact` and shown as plain text in
// a wrapped `pre`, never as markup. Its header names the path, the size and the modification time, and has "Close". It has the
// states loading, loaded and refused (the operation's own message, shown whole). It owns no layout: the Floor puts it where the
// panel was, a phone puts it in a dialog, and the Building's "Project state" link opens it in a dialog.

import * as api from "../api.js";
import { fill, h } from "../dom.js";
import { formatSize, formatWhen } from "../floor-model.js";
import { icon } from "../frame/icons.js";
import { busyLine } from "./widgets.js";

/** Create a viewer. Returns {el, load(project, path), close(), focus()}; onClose is called by "Close". */
export function createViewer({ onClose }) {
  const titleId = "wb-viewer-title";
  const el = h("div", { class: "pui-card wb-viewer", role: "region", "aria-labelledby": titleId });
  let controller = null;

  function head(path, line) {
    const close = h("button", { class: "pui-btn pui-surface pui-outline wb-small-button", type: "button", "data-key": "close", text: "Close" });
    close.addEventListener("click", () => onClose());
    return h("div", { class: "wb-viewer-head" },
      h("span", { class: "wb-tile pui-soft pui-theme wb-tile-small" }, icon("file-text", 16)),
      h("div", { class: "wb-viewer-titles" }, h("strong", { class: "wb-viewer-path mono", id: titleId, tabindex: "-1", text: path }), line ? h("span", { class: "wb-muted wb-viewer-line", text: line }) : null),
      close);
  }

  return {
    el,
    async load(project, path) {
      if (controller) controller.abort();
      controller = new AbortController();
      const mine = controller;
      fill(el, head(path, ""), h("div", { class: "wb-viewer-body" }, busyLine("Loading the floor...")));
      try {
        const doc = await api.artifact(project, path, { signal: mine.signal });
        if (mine.signal.aborted) return;
        const line = `${formatSize(doc.size)}, modified ${formatWhen(doc.modified_at)}`;
        fill(el, head(doc.path || path, line), h("div", { class: "wb-viewer-body" },
          h("pre", { class: "wb-viewer-text", tabindex: "0", "aria-label": `Text of ${doc.path || path}` }, String(doc.text))));
      } catch (e) {
        if (mine.signal.aborted || (e && e.name === "AbortError")) return;
        const message = e && e.name === "ApiError" && e.status === 0 ? "The service could not be reached. Is it still running?" : (e && e.message) || "The file could not be opened.";
        fill(el, head(path, ""), h("div", { class: "wb-viewer-body" },
          h("div", { class: "wb-refusal", role: "alert" }, h("strong", { class: "wb-refusal-title", text: "The file could not be opened" }), h("span", { class: "mono", text: message }))));
      }
    },
    close() {
      if (controller) controller.abort();
      controller = null;
    },
    focus() {
      const node = el.querySelector ? el.querySelector(`#${titleId}`) : null;
      if (node && node.focus) node.focus();
    },
  };
}
