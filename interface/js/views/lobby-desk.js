// The Lobby's Desk tab (handoff lobby.md, "Desk tab"): the Floor's desk table and viewer showing the documents of `artifacts` that
// belong to the planning agent: those with `agent` "planning" and those with no agent (no owner, or no single agent owns the skill:
// WP-9.4b, E-22). The page reads `artifacts` (every 5 seconds while the Desk is open, every 30 otherwise) and puts a path in the
// viewer only when the person clicks one; the viewer reads the file with `artifact` and shows it as text.

import * as api from "../api.js";
import { createDeskTab } from "../floor/desk-tab.js";
import { createViewer } from "../floor/viewer.js";
import { h } from "../dom.js";
import { PLANNING } from "../floor-model.js";
import { lobbyDocuments } from "./lobby-model.js";

const DOCS_OPEN_MS = 5000;
const DOCS_IDLE_MS = 30000;

/**
 * Create the Desk. env: {project, open(path) (the person chose a document), changed() (the documents were read)}. Returns {el, update({tab,
 * ready}), rows() (the planning agent's documents, or null while unread), focusRow(path)}.
 */
export function createLobbyDesk(env) {
  const { project } = env;
  const desk = createDeskTab({ project, agent: PLANNING, open: env.open });
  let documents = null;      // {rows, truncated} as read, or null
  let error = null;
  let at = 0;
  let reading = false;
  let disposed = false;

  async function read() {
    if (reading || disposed) return;
    reading = true;
    try {
      const body = await api.artifacts(project);
      documents = { rows: Array.isArray(body.artifacts) ? body.artifacts : [], truncated: Boolean(body.truncated) };
      error = null;
    } catch (e) {
      // a project that is not accepted yet: the page shows its waiting line; any other failure is shown by the table
      if (!(e && e.name === "ApiError" && e.status === 412)) error = (e && e.message) || "The documents could not be read.";
    }
    at = Date.now();
    reading = false;
    if (!disposed) {
      draw();
      env.changed();
    }
  }

  function draw() {
    const rows = documents ? lobbyDocuments(documents.rows) : [];
    desk.update({ documents: rows, truncated: Boolean(documents && documents.truncated), loading: documents === null && !error, error });
  }

  return {
    el: desk.el,
    /** tab: the selected tab id; ready: the project is read and accepted. */
    update({ tab, ready }) {
      if (ready) {
        const stale = Date.now() - at > (tab === "desk" ? DOCS_OPEN_MS : DOCS_IDLE_MS);
        if (at === 0 || stale) read();
      }
      draw();
    },
    rows() {
      return documents ? lobbyDocuments(documents.rows) : null;
    },
    focusRow(path) {
      desk.focusRow(path);
    },
    dispose() {
      disposed = true;
    },
  };
}

/**
 * The viewer of a document of the Desk. It takes the whole panel's place (`host` inside the panel), or on a phone a dialog. env: {frame,
 * panel (the element the host goes in), project, onClose()}. Returns {show(path) -> "inline" | "dialog" | null, dispose()}.
 */
export function createLobbyViewer(env) {
  const viewer = createViewer({ onClose: () => env.onClose() });
  const host = h("div", { class: "wb-viewer-host", hidden: true }, viewer.el);
  env.panel.append(host);
  const dialog = h("dialog", { class: "pui-modal wb-viewer-dialog", "aria-label": "Document" });
  dialog.addEventListener("close", () => {
    if (current !== null) env.onClose();
  });
  env.frame.el.append(dialog);
  const phone = window.matchMedia("(max-width: 639px)");
  let current = null;

  return {
    /** Show the document at `path`, or none for null. Returns where it is: "inline" (in the panel's place), "dialog" (a phone) or null. */
    show(path) {
      if (path === null || path === undefined) {
        if (current !== null) {
          viewer.close();
          current = null;
          if (dialog.open) dialog.close();
        }
        host.hidden = true;
        return null;
      }
      if (current !== path) {
        current = path;
        viewer.load(env.project, path).then(() => viewer.focus());
      }
      if (phone.matches) {
        if (viewer.el.parentNode !== dialog) dialog.append(viewer.el);
        if (!dialog.open) dialog.showModal();
        host.hidden = true;
        return "dialog";
      }
      if (viewer.el.parentNode !== host) host.append(viewer.el);
      host.hidden = false;
      return "inline";
    },
    dispose() {
      viewer.close();
      current = null;
      host.remove();
      dialog.remove();
    },
  };
}
