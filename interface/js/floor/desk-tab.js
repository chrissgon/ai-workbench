// The Floor's Desk tab (handoff floor.md): the agent's documents from `artifacts` as a table (path, owner skill, size with the kind beside it:
// text, Markdown, image or other, A-33, and modified; the Lobby's desk, which lists every document of the project, has the agent after the
// owner skill: `agentColumn`),
// a filter that works in the page over the rows already read (no request), a "bound" chip, and the states loading, empty,
// truncated and no match. A row opens the viewer by its hash. A path is text: it wraps after "/", "-" and "." and never
// inside a name. The desk draws what the operation returned; opening a file is a read.

import { fill, h } from "../dom.js";
import { arrowNav } from "../frame/arrows.js";
import { deskRows, pathParts } from "../floor-model.js";
import { busyLine, field } from "./widgets.js";

export const NONE_IN_PROJECT = "The project has no documents under docs/ yet.";
// Assumption (WP-9.5b): the handoff has no wording for an agent with none of its own. The Lobby's desk lists every document of the project (C-2).
export const NONE_OF_ITS_OWN = "No documents of this agent. Every document is on the Lobby's desk.";

/** A path as nodes with a `wbr` after each of "/", "-" and ".". */
export function pathNodes(path) {
  const out = [];
  for (const part of pathParts(path)) out.push(part, h("wbr"));
  out.pop();
  return out;
}

/** The date and the time of a "2026-10-03 09:05" as two parts that are never broken inside (the date keeps its hyphens). */
export function whenParts(text) {
  const [date, ...time] = String(text).split(" ");
  return time.length ? [h("span", { class: "wb-nowrap", text: date }), " ", h("span", { class: "wb-nowrap", text: time.join(" ") })] : [h("span", { class: "wb-nowrap", text: date })];
}

/**
 * Create the Desk. env: {project, agent, open(path), agentColumn (the Lobby's: an "Agent" column after the owner skill)}. Returns {el, update({documents, truncated, loading, error, elsewhere}),
 * filterText(), focusRow(path)}; documents are the agent's rows of `artifacts`; `elsewhere` (optional) is how many rows of the
 * project are not this agent's, so that an agent with none of its own is not told that the project has none.
 */
export function createDeskTab(env) {
  const el = h("div", { class: "wb-desk-tab" });
  const input = h("input", { class: "pui-input wb-field-input", type: "text", placeholder: "Path or owner skill", "data-key": "filter" });
  const filterField = field("Filter documents", input);
  const states = h("div", { class: "wb-desk-states" });
  const tableBox = h("div", { class: "pui-card wb-desk-card" });
  fill(el, filterField, states, tableBox);
  let last = { documents: [], truncated: false, loading: true, error: null, elsewhere: 0 };
  let shown = "";
  input.addEventListener("input", () => draw(true));

  function table(rows) {
    const body = h("tbody", {}, rows.map((r) => {
      const open = h("button", { class: "pui-btn pui-link wb-path-button", type: "button", "data-path": r.path, "aria-label": `Open ${r.path}` }, pathNodes(r.path));
      open.addEventListener("click", (event) => {
        event.stopPropagation();
        env.open(r.path);
      });
      const row = h("tr", { class: "wb-desk-row" },
        h("td", { "data-label": "Path", class: "wb-desk-path" }, open, r.bound ? h("span", { class: "pui-chip pui-muted pui-soft wb-chip-11", title: "bound to a decision" }, "bound", h("span", { class: "wb-sr", text: " to a decision" })) : null),
        h("td", { "data-label": "Owner skill", class: "mono wb-desk-owner", text: r.owner }),
        env.agentColumn ? h("td", { "data-label": "Agent", class: "mono wb-desk-agent", text: r.agent || "—" }) : null,
        h("td", { "data-label": "Size", class: "wb-nowrap" }, r.size, r.kind ? h("span", { class: "wb-desk-kind wb-muted", text: `${r.size ? " · " : ""}${r.kind}` }) : null),
        h("td", { "data-label": "Modified", class: "wb-desk-when" }, ...whenParts(r.modified)));
      row.addEventListener("click", () => env.open(r.path));
      return row;
    }));
    const node = h("table", { class: "pui-table pui-hoverable wb-desk-table" },
      h("thead", {}, h("tr", {}, (env.agentColumn ? ["Path", "Owner skill", "Agent", "Size", "Modified"] : ["Path", "Owner skill", "Size", "Modified"]).map((t) => h("th", { scope: "col", text: t })))), body);
    arrowNav(node, "button.wb-path-button");
    return node;
  }

  function draw(force = false) {
    const text = input.value;
    const rows = deskRows(last.documents, text);
    const key = JSON.stringify([rows, last.truncated, last.loading, last.error, last.documents.length, last.elsewhere]);
    if (!force && key === shown) return;
    shown = key;
    const active = document.activeElement;
    const path = active && tableBox.contains(active) && active.getAttribute ? active.getAttribute("data-path") : null;
    if (last.error) {
      fill(states, h("div", { class: "wb-state-block is-error", role: "alert" }, h("strong", { class: "wb-refusal-title", text: "The documents could not be read" }), h("span", { class: "mono", text: last.error })));
      fill(tableBox);
      tableBox.hidden = true;
      filterField.hidden = true;
      return;
    }
    if (last.loading) {
      fill(states, h("div", { class: "wb-state-block is-sunken" }, busyLine("Loading the floor...")));
      tableBox.hidden = true;
      filterField.hidden = true;
      return;
    }
    if (!last.documents.length && !last.truncated) {
      fill(states, h("div", { class: "wb-state-block is-dashed wb-muted", text: last.elsewhere > 0 ? NONE_OF_ITS_OWN : NONE_IN_PROJECT }));
      tableBox.hidden = true;
      filterField.hidden = true;
      return;
    }
    filterField.hidden = false;
    fill(states,
      last.truncated ? h("div", { class: "wb-state-block", role: "status", text: "Only the first 2000 files are listed" }) : null,
      !rows.length ? h("div", { class: "wb-state-block is-dashed wb-muted", role: "status", text: "No document matches the filter." }) : null);
    tableBox.hidden = !rows.length;
    fill(tableBox, rows.length ? h("div", { class: "table-wrap" }, table(rows)) : null);
    if (path) {
      const next = tableBox.querySelectorAll ? [...tableBox.querySelectorAll("button.wb-path-button")].find((b) => b.getAttribute("data-path") === path) : null;
      if (next) next.focus({ preventScroll: true });
    }
  }

  return {
    el,
    update(data) {
      last = data;
      draw();
    },
    filterText() {
      return input.value;
    },
    focusRow(path) {
      const rows = tableBox.querySelectorAll ? [...tableBox.querySelectorAll("button.wb-path-button")] : [];
      const found = rows.find((b) => b.getAttribute("data-path") === path);
      if (found) found.focus();
    },
  };
}
