// The composer at the bottom of the Lobby's conversation: the message field, "Send", the hint, the busy line while a turn runs, the line
// that says a run is in progress (A-23: Send stays on; a plain line is stored and routed when the run ends, a question about the state is answered now) and
// the notice when a turn was not sent or failed. It holds no rule: it reports the text the person typed (Enter sends, Shift+Enter
// makes a new line) and draws the state it is given. A line that starts with "/" is sent unchanged; the page builds no prompt.

import { h } from "../dom.js";
import { icon } from "../frame/icons.js";
import { AFTER_HINT, HINT, RUN_LINE, SENDING_TEXT } from "./lobby-model.js";

/** Create the composer. options: {onSend(text)}. Returns {el, set(state), focus(), text(), clear()}. */
export function createComposer({ onSend }) {
  const busy = h("div", { class: "wb-lobby-busy", role: "status", "aria-busy": "true", hidden: true }, h("span", { class: "wb-lobby-ring", "aria-hidden": "true" }), h("span", { text: SENDING_TEXT }));
  const noticeTitle = h("strong", { class: "wb-lobby-notice-title", text: "" });
  const noticeText = h("span", { text: "" });
  const notice = h("div", { class: "wb-lobby-notice-card", role: "alert", hidden: true }, noticeTitle, noticeText);
  const runLink = h("a", { class: "pui-link pui-theme wb-lobby-run-link", href: "#/", hidden: true, text: "" });
  const runLine = h("p", { class: "wb-lobby-run", id: "wb-say-run", role: "status", hidden: true }, h("span", { text: RUN_LINE }), " ", runLink);
  const field = h("textarea", { class: "pui-input wb-lobby-field", id: "wb-say", rows: "1", placeholder: "Describe what you want done", autocomplete: "off" });
  const group = h("label", { class: "pui-field-group wb-composer-field", for: "wb-say" }, h("span", { text: "Message to the planning agent" }), field);
  const sendIcon = icon("send", 14);
  const word = document.createTextNode("Send");
  const button = h("button", { class: "pui-btn pui-theme pui-outline wb-send", type: "submit" }, sendIcon, word);
  const form = h("form", { class: "wb-composer" }, group, button);
  const hint = h("p", { class: "wb-lobby-hint", id: "wb-say-hint", text: HINT });
  const hintMore = h("p", { class: "wb-lobby-hint wb-lobby-hint-more", id: "wb-say-hint-more", text: AFTER_HINT });
  field.setAttribute("aria-describedby", "wb-say-hint");
  const el = h("div", { class: "wb-composer-wrap" }, busy, runLine, notice, form, hint, hintMore);
  let sending = false;

  function submit() {
    if (sending || field.disabled) return;
    onSend(field.value);
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submit();
  });
  field.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing && !event.ctrlKey && !event.metaKey && !event.altKey) {
      event.preventDefault();
      submit();
    }
  });

  return {
    el,
    /**
     * state: {sending, notice: {title, text} | null, disabled: bool (the project is not accepted), running: {text, href} | null (a run is in progress:
     * the task it names and where to read it; the line shows, Send stays on)}.
     */
    set({ sending: on, notice: shown, disabled, running = null }) {
      runLine.hidden = !running || Boolean(disabled);
      runLink.hidden = !running || !running.text;
      runLink.textContent = running && running.text ? running.text : "";
      if (running && running.href) runLink.setAttribute("href", running.href);
      sending = Boolean(on);
      busy.hidden = !sending;
      el.classList.toggle("is-sending", sending);
      field.disabled = sending || Boolean(disabled);
      button.disabled = sending || Boolean(disabled);
      if (sending) button.setAttribute("aria-busy", "true");
      else button.removeAttribute("aria-busy");
      sendIcon.hidden = sending;
      word.data = sending ? "Sending..." : "Send";
      notice.hidden = !shown;
      noticeTitle.textContent = shown ? shown.title : "";
      noticeText.textContent = shown ? shown.text : "";
    },
    focus() {
      field.focus();
    },
    text() {
      return field.value;
    },
    clear() {
      field.value = "";
    },
  };
}
