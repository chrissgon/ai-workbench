// The token prompt: asks the person to paste the service's token once per browser session. The field is a text field that the
// stylesheet masks (`.wb-token-field`) where the browser can, not a password field: the token changes at every start, so the browser
// must not offer to save it.

import { h, fill } from "../dom.js";
import { markImage } from "../brand.js";
import { commandBlock } from "../frame/command.js";
import { looksLikeToken } from "../token.js";

// The sentence the prompt had before the service told it where the token file is, and keeps when it cannot say.
const FIRST_LINE = "The token is in the file whose path the service printed when it started (the \"token_file\" value of its first line); open that file and paste its one line here.";
const COPIES = "It copies the token to the clipboard. The token itself is never shown on this page.";
const PRINTS = "It prints the token in the terminal; the token itself is never shown on this page.";

// The systems the page tells apart. `key` is the entry of the service's `commands` for it: the page picks one of the strings the
// service built and joins nothing into it.
const SYSTEMS = {
  macos: { name: "macOS", key: "macos", sentence: COPIES },
  linux: { name: "Linux", key: "linux", sentence: PRINTS },
  windows: { name: "Windows", key: "powershell", sentence: COPIES },
};

/** The system a browser's platform string names ("macos", "linux" or "windows"), or null for any other (then the prompt keeps its sentence). */
export function systemOf(platform) {
  if (typeof platform !== "string") return null;
  if (/^win/i.test(platform)) return "windows";
  if (/^mac/i.test(platform)) return "macos";
  if (/^linux|^x11/i.test(platform)) return "linux";
  return null;
}

function browserPlatform() {
  if (typeof navigator === "undefined" || !navigator) return "";
  return String((navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || "");
}

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
 * `tokenFile` (optional) is an async function that reads the service's answer to GET /token-file ({token_file, commands}); when the
 * answer has a command for the browser's system (`platform`, default the browser's own) the prompt shows two steps, "1 · Run this in a
 * terminal" with the command and Copy, then "2 · Paste the token"; in every other case (no reader, an older service, an error, a path
 * with no safe command, a system not told apart) it keeps its sentence about the first line. `copyEnv` is for a test.
 */
export function showTokenPrompt(root, { message, onSubmit, tokenFile, platform, copyEnv }) {
  const field = h("input", {
    id: "token-field", class: "pui-input wb-token-field", type: masksText() ? "text" : "password", name: "service-token", autocomplete: "off",
    autocapitalize: "off", spellcheck: "false", required: true, "aria-describedby": "token-help",
  });
  const problem = h("p", { class: "notice error", role: "alert", hidden: true });
  const button = h("button", { class: "pui-btn pui-solid pui-theme", type: "submit", text: "Continue" });
  const fieldLabel = h("span", { text: "Access token" });
  const form = h("form", { class: "stack", autocomplete: "off" },
    h("label", { class: "pui-field-group", for: "token-field" },
      fieldLabel,
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

  // Where the person is told how to get the token: the two steps, or the sentence. Empty while the service's answer is awaited.
  const how = h("div", { class: "wb-token-how" });
  const fallback = () => {
    fieldLabel.textContent = "Access token";
    fieldLabel.removeAttribute("class");
    fill(how, h("p", { text: FIRST_LINE }));
  };
  const steps = (system, command) => {
    fieldLabel.textContent = "2 \u00b7 Paste the token";
    fieldLabel.setAttribute("class", "wb-token-label");
    fill(how,
      h("div", { class: "wb-token-head" },
        h("span", { class: "wb-token-label", text: "1 \u00b7 Run this in a terminal" }),
        h("span", { class: "wb-token-system", text: system.name })),
      commandBlock({ command, label: "Copy the command" }, copyEnv || null),
      h("small", { class: "wb-token-help", text: system.sentence }));
  };
  if (typeof tokenFile !== "function") {
    fallback();
  } else {
    const system = SYSTEMS[systemOf(platform === undefined ? browserPlatform() : platform)];
    Promise.resolve().then(() => tokenFile()).then((answer) => {
      const commands = answer && typeof answer === "object" && answer.commands && typeof answer.commands === "object" ? answer.commands : null;
      const command = system && commands ? commands[system.key] : null;
      if (typeof command === "string" && command.trim()) steps(system, command);
      else fallback();
    }).catch(fallback);
  }

  fill(root,
    h("section", { class: "pui-card" },
      h("div", { class: "pui-card-header", text: "Paste the openhora service token" }),
      h("div", { class: "pui-card-content" },
        h("div", { class: "wb-brand" }, markImage(48, ""), h("span", { class: "wb-wordmark", text: "openhora" })),
        message ? h("p", { class: "notice error", role: "alert", text: message }) : null,
        how,
        form)));
  field.focus();
}
