// The plan card (handoff cards.md, "Plan card"): the approval point of a plan. It shows the exact thing approved ahead of its
// button: the table of the tasks, the limits, the whole plan hash and the plan as text. "Approve this plan" sends exactly
// {sha256: <the hash displayed>} (a job); "Reject" sends the note when one was typed. The card never changes by itself: after an
// action it asks its host to read again (`onChanged`) and the host draws what it got, a resolved line in place of the card. Text
// from the service goes in as text. A plan with no whole hash offers no approval.

import { h } from "../dom.js";
import * as format from "../format.js";
import { markdownView } from "../markdown-view.js";
import * as router from "../router.js";
import { COLUMNS, failureText, limitsLine, planHash, planText, stackedRow, taskRows } from "./plan-rows.js";

let counter = 0;

/**
 * A plan card. options: {api, project, item (a pending decision with payload and actions), now (Date), onChanged(): Promise,
 * signal, announce(text) (optional: a sentence for the live region)}. Returns {el, focus()}. `api` is the client module (`approve`, `reject`, `pollJob`), passed in so a test can stand in for it.
 */
export function createPlanCard({ api, project, item, now, onChanged, signal, announce }) {
  counter += 1;
  const titleId = `wb-plan-title-${counter}`;
  const shown = planHash(item);
  const actions = Array.isArray(item.actions) ? item.actions : [];
  const rows = taskRows(item);

  const kind = h("span", { class: "pui-badge pui-warn pui-soft", text: format.kindWord(item.kind) });
  const age = format.age(item.created_at, now);
  const meta = h("span", { class: "wb-card-meta" },
    `#${item.id} · `,
    item.task_id !== null && item.task_id !== undefined ? h("a", { class: "pui-link pui-theme", href: router.lobbyHash(project), text: `request #${item.task_id}` }) : null,
    item.task_id !== null && item.task_id !== undefined ? " · " : null,
    `${format.agentWord(item.agent)}${age ? ` · ${age === "now" ? "just now" : `${age} ago`}` : ""}`);
  if (item.created_at) meta.setAttribute("title", item.created_at);
  const title = h("h3", { class: "wb-card-title", id: titleId, tabindex: "-1", text: item.title || `Plan ${item.id}` });

  const table = h("table", { class: "pui-table wb-plan-table" },
    h("caption", { class: "wb-sr", text: "Tasks" }),
    h("thead", {}, h("tr", {}, COLUMNS.map((c) => h("th", { scope: "col", text: c })))),
    h("tbody", {}, rows.map((r) => h("tr", {},
      h("td", { class: "wb-cell-n", text: r.n }),
      h("td", { class: "wb-cell-task", text: r.task }),
      h("td", { class: "wb-cell-skill", text: r.skill }),
      h("td", { text: r.agent }),
      h("td", { text: r.after }),
      h("td", { text: r.milestone }),
      h("td", { text: r.web })))));
  const tableWrap = h("div", { class: "table-wrap wb-plan-wide", tabindex: "0", role: "region", "aria-label": "Plan tasks" }, table);
  // Below 640 px the table is replaced by one block per task (the design system's rule for a narrow screen).
  const stack = h("ol", { class: "wb-plan-stack", "aria-label": "Plan tasks" }, rows.map((r) => {
    const s = stackedRow(r);
    return h("li", { class: "wb-plan-stacked" }, h("strong", { text: s.head }),
      h("span", { class: "wb-plan-stacked-skill" }, h("code", { text: s.skill }), s.agent ? ` · ${s.agent}` : ""), h("span", { class: "wb-card-note", text: s.tail }));
  }));

  const limits = limitsLine(item);
  const hashBlock = shown
    ? h("div", { class: "wb-plan-hash-block" }, h("span", { class: "wb-card-label", text: "Plan hash" }), h("code", { class: "wb-plan-hash", text: shown }))
    : h("p", { class: "wb-card-note", text: "This plan carries no hash, so it cannot be approved from here." });
  const text = planText(item);
  const asText = text
    ? h("details", { class: "pui-accordion-item wb-plan-text" }, h("summary", { text: "Plan as text" }), h("div", { class: "wb-plan-body" }, markdownView(text, { name: "the plan", renderedLabel: "Plan as text", plainClass: "wb-plan-pre" })))
    : null;

  const noteId = `${titleId}-note`;
  const note = h("input", { class: "pui-input wb-lobby-field", id: noteId, type: "text", autocomplete: "off" });
  const noteGroup = h("label", { class: "pui-field-group", for: noteId }, h("span", { text: "Note (optional, used when you reject)" }), note);
  const error = h("div", { class: "notice error wb-card-error", role: "alert", hidden: true });
  const working = h("span", { class: "wb-lobby-working", hidden: true, text: "Working..." });
  const approve = actions.includes("approved") && shown
    ? h("button", { class: "pui-btn pui-theme pui-outline", type: "button", text: "Approve this plan" }) : null;
  const reject = actions.includes("rejected")
    ? h("button", { class: `pui-btn ${approve ? "pui-surface" : "pui-theme"} pui-outline`, type: "button", text: "Reject" }) : null;
  const buttons = [approve, reject].filter(Boolean);
  const row = buttons.length ? h("div", { class: "wb-card-buttons" }, ...buttons, working) : null;

  const el = h("article", { class: "pui-card wb-card wb-plan-card", "aria-labelledby": titleId },
    h("div", { class: "wb-card-head" }, kind, meta),
    h("div", { class: "pui-card-content wb-card-content" },
      title, tableWrap, stack, limits ? h("p", { class: "wb-card-note", text: limits }) : null, hashBlock, asText,
      reject ? noteGroup : null, error, row));

  let sending = false;

  function showError(message) {
    error.textContent = message;
    error.hidden = !message;
  }

  function lock(on, active, word) {
    sending = on;
    for (const button of buttons) {
      button.disabled = on;
      button.removeAttribute("aria-busy");
    }
    note.disabled = on;
    working.hidden = !(on && active === approve);
    if (on) {
      active.setAttribute("aria-busy", "true");
      active.dataset.word = active.textContent;
      active.textContent = word;
    } else if (active && active.dataset.word) {
      active.textContent = active.dataset.word;
    }
  }

  async function run(active, word, call, isJob) {
    if (sending) return;
    showError("");
    lock(true, active, word);
    try {
      const first = await call();
      if (isJob) {
        const done = await api.pollJob(first.job, 1000, { signal });
        if (done.state === "failed") {
          const failure = done.error || {};
          throw Object.assign(new Error(failure.message || "The job failed."), { status: failure.status || 500, word: failure.error || "internal" });
        }
      }
    } catch (e) {
      if (e && e.name === "AbortError") return;
      showError(failureText(e));
      lock(false, active);
      await onChanged();    // the card is read again: a decision resolved elsewhere becomes its resolved line
      return;
    }
    if (announce) announce(active === approve ? "Plan approved" : "Plan rejected");
    await onChanged();      // the host draws what it read: the resolved line in place of this card
    if (el.isConnected) lock(false, active);
  }

  if (approve) approve.addEventListener("click", () => run(approve, "Approving...", () => api.approve(project, item.id, shown), true));
  if (reject) {
    reject.addEventListener("click", () => run(reject, "Rejecting...", () => api.reject(project, item.id, note.value.trim() ? note.value : undefined), false));
  }

  return {
    el,
    focus() {
      title.focus({ preventScroll: false });
    },
  };
}
