// The "New request" disclosure: a text area, the Flow select (the first option lets the planning agent route it, then one option per
// flow of `flows`, labelled by the flow's own title), an optional title and "Create request". It reports what was typed and chosen;
// that the request is sent without a flow and routed in a second call is the caller's (lobby-actions.js). Closed by default.

import { h } from "../dom.js";
import { AUTO_FLOW, FORM_HINT, flowOptions } from "./lobby-model.js";

/** Create the form. options: {onCreate({text, flow, title})}. Returns {el, setFlows(list), set(partial), markEmpty(), reset(), open(on), isOpen()}. */
export function createForm({ onCreate }) {
  const textId = "wb-new-text";
  const flowId = "wb-new-flow";
  const titleId = "wb-new-title";
  const text = h("textarea", { class: "pui-input wb-field", id: textId, rows: "3", autocomplete: "off" });
  const flow = h("select", { class: "pui-input wb-field", id: flowId }, h("option", { value: "", text: AUTO_FLOW }));
  const title = h("input", { class: "pui-input wb-field", id: titleId, type: "text", autocomplete: "off" });
  const create = h("button", { class: "pui-btn pui-theme pui-outline", type: "submit", text: "Create request" });
  const error = h("div", { class: "notice error wb-card-error", role: "alert", hidden: true });
  const busy = h("div", { class: "wb-busy", role: "status", hidden: true }, h("span", { class: "wb-ring", "aria-hidden": "true" }), h("span", { text: "Creating the request..." }));
  const body = h("form", { class: "wb-form-body" },
    h("label", { class: "pui-field-group", for: textId }, h("span", { text: "What do you want done?" }), text),
    h("label", { class: "pui-field-group", for: flowId }, h("span", { text: "Flow" }), flow),
    h("label", { class: "pui-field-group", for: titleId }, h("span", { text: "Title (optional)" }), title),
    error, busy,
    h("div", { class: "wb-form-row" }, create),
    h("p", { class: "wb-form-hint", text: FORM_HINT }));
  const summary = h("summary", { text: "New request" });
  const el = h("details", { class: "pui-accordion-item wb-new-request" }, summary, body);
  let creating = false;
  let state = { creating: false, error: "", disabled: false };

  body.addEventListener("submit", (event) => {
    event.preventDefault();
    if (creating) return;
    onCreate({ text: text.value, flow: flow.value, title: title.value });
  });

  return {
    el,
    /** The flows the service listed: the options after the first. A list that failed to load leaves the first alone. */
    setFlows(list) {
      const keep = flow.value;
      flow.replaceChildren(...flowOptions(list).map((o) => h("option", { value: o.value, text: o.label })));
      flow.value = [...flow.options].some((o) => o.value === keep) ? keep : "";
    },
    /** Merge a state into the form's: {creating, error, disabled}; a key left out keeps its value. */
    set(partial) {
      state = { ...state, ...partial };
      creating = Boolean(state.creating);
      for (const control of [text, flow, title, create]) control.disabled = creating || Boolean(state.disabled);
      create.textContent = creating ? "Creating..." : "Create request";
      if (creating) create.setAttribute("aria-busy", "true");
      else create.removeAttribute("aria-busy");
      busy.hidden = !creating;
      error.textContent = state.error || "";
      error.hidden = !state.error;
      if (creating) text.removeAttribute("aria-invalid");
    },
    /** Empty text is not sent: the field says so (aria-invalid) and takes the focus. */
    markEmpty() {
      text.setAttribute("aria-invalid", "true");
      text.focus();
    },
    reset() {
      text.value = "";
      title.value = "";
      flow.value = "";
    },
    open(on) {
      el.open = Boolean(on);
    },
    isOpen() {
      return el.open;
    },
  };
}
