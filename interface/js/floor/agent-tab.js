// The Floor's Agent tab (handoff floor.md): the agent's state row, the mode plate and "Set mode", the standing notice about
// the configuration, the result notice with the exact command the service gave, three meters, the current task with its runs,
// the other tasks with "Retry", and "Hand a file over". Each control sends exactly one request: `setMode` with the selected
// word, `retry` with no body, `handOver` with the file as the person chose it. The page decides nothing: the mode's words
// and its line are constants of one table, every other value is what an operation returned. The tab is built once and its
// parts are drawn again only when their data changed, so a poll never takes the keyboard focus or the typed choice away.

import { fill, h } from "../dom.js";
import * as format from "../format.js";
import { MODES, MODE_LINES, PIPS, meters, modeOption, runRows, stateRow, stateTone, taskWord } from "../floor-model.js";
import { pips } from "../scene/plates.js";
import { busyLine, chip, errorText, notice, ring } from "./widgets.js";

export const MAX_FILE_BYTES = 25 * 1024 * 1024;
const NAME = /^[A-Za-z0-9._-]{1,100}$/;
export const STANDING = "Setting a mode changes the project's configuration. Every action of this page then refuses until you accept the new configuration in the terminal.";

/** The base64 of some bytes (the body of a file handed over): chunked so a large file does not overflow the call stack. */
export function toBase64(bytes) {
  let text = "";
  for (let i = 0; i < bytes.length; i += 0x8000) text += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(text);
}

/** The refusal before sending, or "" when the file may be sent: over 25 MiB, or a name the service would refuse. */
export function fileRefusal(name, size) {
  if (size > MAX_FILE_BYTES) return "A file handed to a task is at most 25 MiB.";
  if (!NAME.test(name)) return "The file name may hold letters, digits, ., _ and -, at most 100 characters.";
  return "";
}

/** Keep the keyboard focus on the control with the same `data-key` after a part is drawn again. */
function redraw(container, render) {
  const active = document.activeElement;
  const key = active && container.contains(active) && active.getAttribute ? active.getAttribute("data-key") : null;
  render();
  if (!key || !container.querySelectorAll) return;
  const next = [...container.querySelectorAll("[data-key]")].find((n) => n.getAttribute("data-key") === key);
  if (next && next.focus) next.focus({ preventScroll: true });
}

/**
 * Create the Agent tab. env: {project, agent, api: {setMode, retry, handOver}, refresh(), now()}. Returns {el, update(view),
 * focusSelect()}; view is floor-model.floor(...) (found, notAccepted or loading).
 */
export function createAgentTab(env) {
  const el = h("div", { class: "wb-agent-tab" });
  const stateBox = h("div", { class: "wb-state-box", role: "status" });
  const plateBox = h("div", { class: "wb-mode-row" });
  const formBox = h("div", { class: "wb-mode-form" });
  const standing = h("div", { class: "wb-notice-card", text: STANDING });
  const resultBox = h("div", { class: "wb-result-box" });
  const waitingLine = h("p", { class: "wb-empty-line", text: "Waiting for the configuration to be accepted." });
  const metersBox = h("div", { class: "wb-meters" });
  const currentBox = h("div", { class: "wb-section" });
  const othersBox = h("div", { class: "wb-section" });
  const handBox = h("div", { class: "wb-hand" });
  const body = h("div", { class: "wb-agent-body" }, waitingLine, metersBox, currentBox, othersBox, handBox);
  fill(el, stateBox, plateBox, formBox, standing, resultBox, body);

  const shown = {};
  const swap = (name, value, draw) => {
    const key = JSON.stringify(value);
    if (shown[name] === key) return;
    shown[name] = key;
    draw();
  };

  // --- Set mode ----------------------------------------------------------------------------------------------------------------
  const select = h("select", { class: "pui-input wb-select", "data-key": "mode" });
  for (const mode of MODES) select.append(h("option", { value: mode, text: modeOption(mode) }));
  const setButton = h("button", { class: "pui-btn pui-theme pui-outline wb-set-mode", type: "button", "data-key": "set-mode", text: "Set mode" });
  const formError = h("div", { class: "wb-form-error" });
  let userChoice = false;
  let lastMode = null;
  let setting = false;
  let modeResult = null;       // {mode, next}
  let sawUnaccepted = false;
  const selectLabel = h("label", { class: "pui-field-group wb-field" }, h("span", { class: "wb-field-label", text: "Set mode" }), select);
  fill(formBox, h("div", { class: "wb-mode-controls" }, selectLabel, setButton), formError);
  const syncTitle = () => select.setAttribute("title", modeOption(select.value));
  select.addEventListener("change", () => { userChoice = true; syncTitle(); });
  setButton.addEventListener("click", async () => {
    if (setting) return;
    setting = true;
    setButton.disabled = true;
    select.disabled = true;
    fill(setButton, ring(true), "Setting...");
    setButton.setAttribute("aria-busy", "true");
    fill(formError);
    try {
      const result = await env.api.setMode(env.project, env.agent, select.value);
      modeResult = { mode: result.mode, next: result.next };
      drawResult();
      env.refresh();
    } catch (e) {
      fill(formError, notice(errorText(e), "error"));
    }
    setting = false;
    setButton.disabled = false;
    select.disabled = false;
    setButton.removeAttribute("aria-busy");
    fill(setButton, "Set mode");
  });

  function drawResult() {
    fill(resultBox, modeResult ? h("div", { class: "wb-notice-card is-warn", role: "status" },
      h("strong", { text: `Mode set to ${modeResult.mode}. Nothing works on this page until you accept the new configuration.` }),
      h("code", { class: "wb-command", text: modeResult.next || "" })) : null);
  }

  function drawPlate(agent) {
    if (!agent || !agent.mode) {
      fill(plateBox);
      return;
    }
    const plate = h("span", { class: "pui-chip pui-muted pui-outline pui-rounded-full wb-mode-plate" }, h("span", { text: agent.mode }), pips(PIPS[agent.mode] || 0));
    const acting = agent.acting_mode && agent.acting_mode !== agent.mode
      ? h("span", { class: "pui-chip pui-muted pui-outline pui-rounded-full wb-mode-plate wb-acting-plate" }, h("span", { text: `acting as ${agent.acting_mode}` }), pips(PIPS[agent.acting_mode] || 0)) : null;
    fill(plateBox, plate, acting, h("span", { class: "wb-muted wb-mode-line", text: `${MODE_LINES[agent.mode] || ""}.` }));
  }

  // --- the other parts -----------------------------------------------------------------------------------------------------------
  function drawState(row, view) {
    if (!row) {
      fill(stateBox, busyLine("Loading the floor..."));
      return;
    }
    const content = [chip(row.chip, row.tone), h("span", { class: "wb-muted wb-state-line", text: row.line })];
    if (row.off) {
      const button = h("button", { class: "pui-btn pui-theme pui-outline wb-small-button", type: "button", text: "Set mode" });
      button.addEventListener("click", () => select.focus());
      content.push(button);
    }
    fill(stateBox, h("div", { class: "wb-state-row" }, content));
  }

  function meterCell(label, text, share, full, note) {
    const fillNode = h("span", { class: `wb-meter-fill${full ? " is-full" : ""}` });
    fillNode.style.setProperty("--wb-share", `${Math.round(share * 100)}%`);
    return h("div", { class: "wb-meter-cell", role: "group", "aria-label": `${label} ${text}` },
      h("span", { class: "wb-muted wb-meter-label", text: label }), h("strong", { class: "wb-meter-value", text }),
      share !== null ? h("span", { class: "wb-meter wb-meter-track", "aria-hidden": "true" }, fillNode) : null,
      note ? h("span", { class: "wb-note wb-muted", text: note }) : null);
  }

  function drawMeters(m) {
    fill(metersBox, meterCell("Runs today", m.runs.text, m.runs.share, m.runs.full), meterCell("Spend today", m.spend.text, m.spend.share, m.spend.full, m.spend.unknown),
      meterCell("Queued", m.queued.text, null, false));
  }

  function runBlock(run) {
    const rows = runRows(run);
    return h("dl", { class: "wb-run" }, rows.flatMap((r) => [
      h("dt", { class: "wb-muted", text: r.label }),
      h("dd", { class: r.kind === "code" || r.kind === "wrap" ? "mono" : null }, r.kind === "chip" ? chip(r.value, r.tone, "11") : r.value),
    ]));
  }

  function drawCurrent(view) {
    const task = view.current;
    if (!task) {
      fill(currentBox, view.tasks.length ? null : h("p", { class: "wb-empty-line", text: "This agent has no task yet." }));
      return;
    }
    const newest = view.runs[0] || null;
    const since = newest ? format.clock(newest.started_at) : "";
    fill(currentBox, h("div", { class: "wb-section-label", text: "Current task" }),
      h("div", { class: "pui-card wb-current" },
        h("div", { class: "wb-current-head" }, h("strong", { text: `#${task.id} ${task.title || task.key || ""}`.trim() }), chip(taskWord(task.state), stateTone(task.state))),
        h("div", { class: "wb-muted wb-current-sub" }, "skill ", h("code", { text: task.skill || "" }), since ? ` · since ${since}` : ""),
        view.runs.map(runBlock)));
  }

  const retrying = new Set();
  const retryError = new Map();
  function drawOthers(view) {
    if (!view.others.length) {
      fill(othersBox);
      return;
    }
    redraw(othersBox, () => fill(othersBox, h("div", { class: "wb-section-label", text: "Other tasks of this agent" }),
      view.others.map((t) => {
        const can = t.state === "failed" || t.state === "blocked";
        const busy = retrying.has(t.id);
        let button = null;
        if (can) {
          button = h("button", { class: "pui-btn pui-surface pui-outline wb-small-button", type: "button", "data-key": `retry-${t.id}`, "aria-label": `Retry task ${t.id}`, "aria-busy": busy ? "true" : null },
            busy ? ring(true) : null, busy ? "Retrying..." : "Retry");
          button.disabled = busy;
          button.addEventListener("click", () => retryTask(t.id));
        }
        return h("div", { class: "wb-other" },
          h("div", { class: "pui-list-item wb-other-row" }, h("span", { class: "wb-other-title", text: `#${t.id} ${t.title || t.key || ""}`.trim() }), chip(taskWord(t.state), stateTone(t.state)), button),
          retryError.has(t.id) ? notice(retryError.get(t.id), "error") : null);
      })));
  }

  async function retryTask(id) {
    if (retrying.has(id)) return;
    retrying.add(id);
    retryError.delete(id);
    shown.others = null;
    drawOthers(lastView);
    try {
      await env.api.retry(env.project, id);
      env.refresh();
    } catch (e) {
      retryError.set(id, errorText(e));
    }
    retrying.delete(id);
    shown.others = null;
    drawOthers(lastView);
    env.refresh();
  }

  // --- hand a file over ------------------------------------------------------------------------------------------------------------
  const fileInput = h("input", { class: "pui-input wb-file", type: "file", "data-key": "file" });
  const hint = h("small", { class: "wb-hint", text: "At most 25 MiB." });
  const handResult = h("div", { class: "wb-hand-result" });
  const handLabel = h("label", { class: "pui-field-group wb-field" }, h("span", { class: "wb-field-label", text: "Hand a file over" }), fileInput, hint);
  fill(handBox, handLabel, handResult);
  let target = null;
  fileInput.addEventListener("change", async () => {
    const file = fileInput.files && fileInput.files[0];
    if (!file || !target) return;
    const refusal = fileRefusal(file.name, file.size);
    if (refusal) {
      fill(handResult, notice(refusal, "error"));
      fileInput.value = "";
      return;
    }
    fileInput.disabled = true;
    fill(handResult, busyLine("Sending..."));
    try {
      const bytes = new Uint8Array(await file.arrayBuffer());
      const result = await env.api.handOver(env.project, target.id, file.name, toBase64(bytes));
      fill(handResult, h("p", { class: "wb-card-line", role: "status", text: `Handed over: ${result.path} (${result.bytes} bytes)` }));
      env.refresh();
    } catch (e) {
      fill(handResult, notice(errorText(e), "error"));
    }
    fileInput.disabled = false;
    fileInput.value = "";
  });

  function drawHand(view) {
    target = view.target;
    fileInput.disabled = !target;
    hint.textContent = target ? `To task #${target.id}. At most 25 MiB.` : "This agent has no task to hand a file to.";
  }

  let lastView = null;
  return {
    el,
    focusSelect() {
      select.focus();
    },
    /** view: floor-model.floor(...) with found true; {notAccepted: true, ...} draws the waiting line only; null while loading. */
    update(view) {
      lastView = view;
      if (view && view.notAccepted) sawUnaccepted = true;
      else if (view && sawUnaccepted && modeResult) {
        modeResult = null;
        sawUnaccepted = false;
      }
      drawResult();
      const unaccepted = !view || view.notAccepted;
      waitingLine.hidden = !(view && view.notAccepted);
      for (const node of [metersBox, currentBox, othersBox, handBox]) node.hidden = unaccepted;
      stateBox.hidden = false;
      plateBox.hidden = unaccepted;
      formBox.hidden = unaccepted;
      if (!view) {
        swap("state", "loading", () => drawState(null));
        return;
      }
      if (view.notAccepted) {
        swap("state", "unaccepted", () => fill(stateBox));
        return;
      }
      const row = stateRow(view.row.state, view.decisions.length, view.runningBody);
      swap("state", row, () => drawState(row, view));
      swap("plate", [view.agent.mode, view.agent.acting_mode], () => drawPlate(view.agent));
      if (!userChoice || lastMode !== view.agent.mode) {
        if (view.agent.mode && MODES.includes(view.agent.mode)) select.value = view.agent.mode;
        lastMode = view.agent.mode;
        userChoice = false;
        syncTitle();
      }
      swap("meters", meters(view.agent), () => drawMeters(meters(view.agent)));
      swap("current", [view.current, view.runs, view.tasks.length], () => drawCurrent(view));
      swap("others", [view.others.map((t) => [t.id, t.title, t.state]), [...retrying], [...retryError]], () => drawOthers(view));
      swap("hand", view.target ? view.target.id : null, () => drawHand(view));
    },
  };
}
