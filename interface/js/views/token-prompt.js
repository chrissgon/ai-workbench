// The token prompt: asks the person to paste the service's token once per browser session. The field is a text field that the
// stylesheet masks (`.wb-token-field`) where the browser can, not a password field: the token changes at every start, so the browser
// must not offer to save it.

import { h, fill } from "../dom.js";
import { looksLikeToken } from "../token.js";

/**
 * True when the browser can mask a text field by CSS (WebKit and Blink can; Firefox cannot). Where it cannot, the field is a password field:
 * the browser may then offer to save the token, which is the lesser failure next to showing it in clear. That the masked text field stops the
 * browser's offer rests on how browsers behave, not on a test.
 */
function masksText() {
  return typeof CSS !== "undefined" && typeof CSS.supports === "function" && CSS.supports("-webkit-text-security", "disc");
}

/**
 * Draw the prompt in `root`. onSubmit(token) is called with the pasted text when it has the shape of a token and
 * resolves when the page has tried it; `message` is shown above the field (why the prompt is here again).
 */
export function showTokenPrompt(root, { message, onSubmit }) {
  const field = h("input", {
    id: "token-field", class: "pui-input wb-token-field", type: masksText() ? "text" : "password", name: "service-token", autocomplete: "off",
    autocapitalize: "off", spellcheck: "false", required: true, "aria-describedby": "token-help",
  });
  const problem = h("p", { class: "notice error", role: "alert", hidden: true });
  const button = h("button", { class: "pui-btn pui-solid pui-theme", type: "submit", text: "Continue" });
  const form = h("form", { class: "stack", autocomplete: "off" },
    h("label", { class: "pui-field-group", for: "token-field" },
      h("span", { text: "Access token" }),
      field,
      h("small", { id: "token-help", text: "It is kept in this browser tab until you close it, and sent only to this service." })));
  form.append(problem, h("div", { class: "row" }, button));

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const pasted = field.value.trim();
    problem.hidden = true;
    if (!looksLikeToken(pasted)) {
      problem.textContent = "That does not look like the token: it is one line of 32 or more characters, with no spaces.";
      problem.hidden = false;
      return;
    }
    button.disabled = true;
    field.value = "";
    try {
      await onSubmit(pasted);
    } finally {
      button.disabled = false;
    }
  });

  fill(root,
    h("section", { class: "pui-card" },
      h("div", { class: "pui-card-header", text: "Paste the service token" }),
      h("div", { class: "pui-card-content" },
        message ? h("p", { class: "notice error", role: "alert", text: message }) : null,
        h("p", { text: "The token is in the file whose path the service printed when it started (the \"token_file\" value of its first line); open that file and paste its one line here." }),
        form)));
  field.focus();
}
