// The document viewer (handoff floor.md, "Document viewer"): a file under docs/ read with `artifact`. A Markdown document is
// drawn by the page's own renderer (markdown.js: nodes, never markup) with a "Plain text" toggle one click away, the choice kept
// for the page session; any other file, and the plain view, is the text in a wrapped `pre`. Its header names the path, the size
// and the modification time, and has "Close". It has the
// states loading, loaded and refused (the operation's own message, shown whole). It owns no layout: the Floor puts it where the
// panel was, a phone puts it in a dialog, and the Building's "Project state" link opens it in a dialog.

import * as api from "../api.js";
import { fill, h } from "../dom.js";
import { formatSize, formatWhen } from "../floor-model.js";
import { icon } from "../frame/icons.js";
import { markdownView } from "../markdown-view.js";
import { busyLine } from "./widgets.js";

const MARKDOWN_FILE = /\.(md|markdown)$/i;

/** The body of a loaded document: a Markdown file gets the rendered view, the plain `pre` and the toggle; any other file, the `pre`. */
function documentBody(doc, path) {
  const name = doc.path || path;
  if (MARKDOWN_FILE.test(name)) return markdownView(doc.text, { name, renderedLabel: `Document ${name}`, plainClass: "wb-viewer-text" });
  return [h("pre", { class: "wb-viewer-text", tabindex: "0", "aria-label": `Text of ${name}` }, String(doc.text))];
}

/** Create a viewer. Returns {el, load(project, path, {quiet}), close(), focus()}; onClose is called by "Close". `quiet`: read the file again without the loading line (the page reloaded: the text stays until the new one arrives). */
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
    async load(project, path, { quiet = false } = {}) {
      if (controller) controller.abort();
      controller = new AbortController();
      const mine = controller;
      if (!quiet) fill(el, head(path, ""), h("div", { class: "wb-viewer-body" }, busyLine("Loading the floor...")));
      try {
        const doc = await api.artifact(project, path, { signal: mine.signal });
        if (mine.signal.aborted) return;
        const line = `${formatSize(doc.size)}, modified ${formatWhen(doc.modified_at)}`;
        fill(el, head(doc.path || path, line), h("div", { class: "wb-viewer-body" }, documentBody(doc, path)));
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
