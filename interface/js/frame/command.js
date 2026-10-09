// The "terminal command" component (A-18): everywhere the page says that something is done in the terminal, it shows the exact command
// the service gave, in a code block that wraps whole, with a Copy button and the sentence of what the command does. The command is the
// service's text, verbatim: nothing here builds one. Copy uses the clipboard when the browser allows it; when it does not, the text is
// selected so that the keyboard copies it.

import { h } from "../dom.js";

const RUNNERS = /^(python3 |uv run |\/)/;
// How the service writes the command that stores a credential. The service now names the secret store "openhora"; the old name "ai-workbench" is
// still accepted so that a service that has not changed its sentence is read as before. The old name goes with the compatibility stage, which
// ends with the next change of reference model (T23).
const STORE = /uv run --with \S+ keyring set (openhora|ai-workbench) \S+/g;
const BACK_AFTER_MS = 2000;

/** Whether a text of the service is a command (it starts with a runner) and not a sentence. */
export function isCommand(text) {
  return typeof text === "string" && RUNNERS.test(text.trim());
}

/**
 * The commands inside a sentence of the service (the credential's: "... KEY: uv run --with ... keyring set openhora|ai-workbench <user>; ..."):
 * {sentence, commands}. Each command is taken verbatim (without the full stop or the semicolon that ends it) and the sentence names it as
 * "(command below)"; a sentence with none comes back as it was.
 */
export function commandsIn(text) {
  const whole = typeof text === "string" ? text : "";
  const commands = [];
  const sentence = whole.replace(STORE, (found) => {
    const command = found.replace(/[.;,)]+$/, "");
    commands.push(command);
    return `(command below)${found.slice(command.length)}`;
  });
  return { sentence, commands };
}

/**
 * Copy a text: "copied" when the clipboard took it (or the old copy command did), "selected" when the text was only selected for the
 * keyboard. env: {clipboard (an object with writeText, or null), select() (selects the text and returns whether a copy command worked)}.
 */
export async function copyCommand(text, env) {
  if (env.clipboard && typeof env.clipboard.writeText === "function") {
    try {
      await env.clipboard.writeText(text);
      return "copied";
    } catch (e) {
      // refused (no permission, an insecure context): fall through to the selection
    }
  }
  return env.select() ? "copied" : "selected";
}

function selectNode(node) {
  try {
    const range = document.createRange();
    range.selectNodeContents(node);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    return typeof document.execCommand === "function" ? Boolean(document.execCommand("copy")) : false;
  } catch (e) {
    return false;
  }
}

/**
 * The component. spec: {command, sentence?}; env (for a test): {clipboard, select(), later(fn, ms)}. Returns the element, or null when there is no
 * command. Text goes in as text; a command or a sentence with markup in it is shown as it came.
 */
export function commandBlock(spec, env = null) {
  if (!spec || typeof spec.command !== "string" || !spec.command.trim()) return null;
  const code = h("code", { class: "wb-command-code", text: spec.command });
  const button = h("button", { class: "pui-btn pui-surface pui-outline wb-copy", type: "button", "aria-label": "Copy the command", text: "Copy" });
  const status = h("span", { class: "wb-copy-status wb-muted", role: "status", text: "" });
  const use = env || {
    clipboard: typeof navigator !== "undefined" && navigator.clipboard ? navigator.clipboard : null,
    select: () => selectNode(code),
    later: (fn, ms) => setTimeout(fn, ms),
  };
  if (env && !env.select) use.select = () => selectNode(code);
  button.addEventListener("click", async () => {
    const result = await copyCommand(spec.command, { clipboard: use.clipboard, select: () => use.select() });
    button.textContent = result === "copied" ? "Copied" : "Selected";
    status.textContent = result === "copied" ? "Copied to the clipboard." : "Selected: copy it with the keyboard.";
    use.later(() => {
      button.textContent = "Copy";
      status.textContent = "";
    }, BACK_AFTER_MS);
  });
  const row = h("div", { class: "wb-command-row" }, code, button);
  return h("div", { class: "wb-command-block" }, spec.sentence ? h("p", { class: "wb-command-sentence", text: spec.sentence }) : null, row, status);
}
