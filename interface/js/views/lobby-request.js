// A request's block in the Lobby's conversation: the request line (its id, title and state, "Cancel request", and "Route it" when
// the request waits for a route nobody is asking for), then the request's decisions: an open plan as the plan card, another open
// kind as a line that points at the Inbox (its card is the Floor's pattern), a decision no longer open as a resolved line. And the
// dialog that asks before a request is cancelled. Text from the service goes in as text.

import { createPlanCard } from "../cards/plan.js";
import { failureText } from "../cards/plan-rows.js";
import { h } from "../dom.js";
import * as format from "../format.js";
import * as router from "../router.js";
import { ago, requestLine, resolvedWord } from "./lobby-model.js";

/** The line of a decision that is no longer open: a chip with "<kind> <resolution>" and the title and age. */
function resolvedLine(item, now) {
  const good = item.status === "resolved" && item.resolution !== "rejected";
  const when = ago(item.resolved_at || item.created_at, now);
  return h("div", { class: "wb-resolved" },
    h("span", { class: `pui-chip pui-soft ${good ? "pui-success" : "pui-muted"} wb-chip-small`, text: resolvedWord(item) }),
    h("span", { class: "wb-resolved-text", text: `${item.title || ""}${when ? ` · ${when}` : ""}` }));
}

/** An open decision whose card is not the plan card: its kind, title and a link to the Inbox where its card is. */
function pointer(project, item, now) {
  const when = ago(item.created_at, now);
  return h("div", { class: "wb-resolved wb-pointer" },
    h("span", { class: "pui-badge pui-warn pui-soft", text: format.kindWord(item.kind) }),
    h("span", { class: "wb-resolved-text", text: `${item.title || ""}${when ? ` · ${when}` : ""}` }),
    h("a", { class: "pui-link pui-theme", href: router.lobbyHash(project, "inbox", item.id), text: "Open in the Inbox", "aria-label": `Open ${format.kindWord(item.kind)} ${item.id} in the Inbox` }));
}

/**
 * One request's block. options: {api, project, request (a row of status.requests), body (the `task` answer, or null while it is
 * read), open (open decisions on it in status), now, signal, onChanged(), onCancel(request), onRoute(request), announce(text)}.
 * Returns {el, focusCard(id)}.
 */
export function createBlock({ api, project, request, body, open, now, signal, onChanged, onCancel, onRoute, routing, announce }) {
  const line = requestLine(request, open);
  const cancel = line.cancellable
    ? h("button", { class: "pui-btn pui-link pui-error wb-cancel-link", type: "button", text: "Cancel request", "aria-label": `Cancel request ${request.id}` }) : null;
  const route = line.routable
    ? h("button", { class: "pui-btn pui-surface pui-outline wb-route-button", type: "button", text: routing ? "Routing..." : "Route it", disabled: Boolean(routing),
      "aria-label": `Route request ${request.id}` }) : null;
  const row = h("div", { class: "wb-request-line", role: "group", "aria-label": line.name },
    h("span", { class: "pui-badge pui-muted pui-soft pui-rounded-full", text: `#${request.id}` }),
    h("span", { class: "wb-request-title", text: `Request #${request.id}: ${line.title}` }),
    line.state ? h("span", { class: "pui-chip pui-muted pui-soft wb-chip-small", text: line.state }) : null,
    route, cancel);
  if (cancel) cancel.addEventListener("click", () => onCancel(request, cancel));
  if (route) route.addEventListener("click", () => onRoute(request));

  const cards = new Map();
  const decisions = [];
  const items = body && Array.isArray(body.pending) ? body.pending : [];
  for (const item of items) {
    if (item.status === "open") {
      if (item.kind === "plan") {
        const card = createPlanCard({ api, project, item, now, onChanged, signal, announce });
        cards.set(item.id, card);
        decisions.push(card.el);
      } else {
        decisions.push(pointer(project, item, now));
      }
    } else {
      decisions.push(resolvedLine(item, now));
    }
  }
  const el = h("div", { class: "wb-request-block" }, line.final ? null : row, ...decisions);
  return {
    el,
    focusCard(id) {
      const card = cards.get(id);
      if (card) card.focus();
    },
  };
}

/** The dialog "Cancel this request and what is still open under it?". Returns {el, open(request, countText, opener)}. */
export function createCancelDialog({ api, project, onChanged }) {
  const titleId = "wb-cancel-title";
  const heading = h("strong", { class: "wb-card-title", id: titleId, text: "Cancel this request and what is still open under it?" });
  const sub = h("span", { class: "wb-card-note", text: "" });
  const error = h("div", { class: "notice error wb-card-error", role: "alert", hidden: true });
  const keep = h("button", { class: "pui-btn pui-surface pui-outline", type: "button", text: "Keep it" });
  const confirm = h("button", { class: "pui-btn pui-error pui-outline", type: "button", text: "Cancel request" });
  const card = h("div", { class: "pui-card wb-dialog-card" },
    h("div", { class: "pui-card-content wb-dialog-content" }, heading, sub, error, h("div", { class: "wb-dialog-buttons" }, keep, confirm)));
  const el = h("dialog", { class: "pui-modal wb-dialog", "aria-labelledby": titleId }, card);
  let current = null;
  let busy = false;

  function setError(text) {
    error.textContent = text;
    error.hidden = !text;
  }
  keep.addEventListener("click", () => {
    if (!busy) el.close();
  });
  el.addEventListener("cancel", (event) => {
    if (busy) event.preventDefault();      // Escape keeps the request; while a cancel is in flight the dialog stays
  });
  confirm.addEventListener("click", async () => {
    if (busy || !current) return;
    busy = true;
    setError("");
    keep.disabled = true;
    confirm.disabled = true;
    confirm.setAttribute("aria-busy", "true");
    confirm.textContent = "Cancelling...";
    try {
      await api.cancel(project, current.id);
      busy = false;
      el.close();
      await onChanged();
    } catch (e) {
      busy = false;
      setError(failureText(e));
    }
    keep.disabled = false;
    confirm.disabled = false;
    confirm.removeAttribute("aria-busy");
    confirm.textContent = "Cancel request";
  });

  return {
    el,
    open(request, countText) {
      current = request;
      sub.textContent = `Request #${request.id}: ${request.title || ""} · ${countText}`;
      setError("");
      if (!el.open) el.showModal();
      keep.focus();
    },
  };
}
