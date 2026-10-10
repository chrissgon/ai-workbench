// The light/dark preference (D-2): the one module that sets the library's own attribute on the root element (`data-pui-mode="light"` or
// `"dark"`) or removes it (the system decides), and the one that keeps the choice, under the single key `openhora-mode` of `localStorage`.
// It is a preference, no project data and no token: the interface's storage rule (README, "The rules of these files") names this module
// beside `token.js` for that one key. The library's own helper (`vendor/perfectui/js/mode.js`) keeps a cookie and is not loaded.
// Storage can be absent or blocked (a private window, cleared site data): then the choice shows for the session and is not kept.
// Everything takes the storage and the root as arguments, so a test runs it with stand-ins.

export const KEY = "openhora-mode";
export const ATTRIBUTE = "data-pui-mode";
export const MODES = Object.freeze(["light", "dark", "system"]);

const storageOf = () => {
  try {
    return window.localStorage;
  } catch (e) {
    return null;     // the accessor itself can throw
  }
};
const rootOf = () => (typeof document === "undefined" ? null : document.documentElement || null);

/** The stored choice: "light", "dark" or "system" (also when nothing is stored, the word is not a mode, or the storage refuses). */
export function readMode(storage = storageOf()) {
  try {
    const value = storage ? storage.getItem(KEY) : null;
    return MODES.includes(value) ? value : "system";
  } catch (e) {
    return "system";
  }
}

/** Put the choice on the root element: the attribute for light and dark, none for system. Returns the mode applied. */
export function applyMode(mode, root = rootOf()) {
  const chosen = MODES.includes(mode) ? mode : "system";
  if (!root) return chosen;       // no document (a test, a worker): nothing to set
  if (chosen === "system") root.removeAttribute(ATTRIBUTE);
  else root.setAttribute(ATTRIBUTE, chosen);
  return chosen;
}

/** The mode the root element shows now. */
export function currentMode(root = rootOf()) {
  const value = root ? root.getAttribute(ATTRIBUTE) : null;
  return value === "light" || value === "dark" ? value : "system";
}

/** Read the stored choice and apply it (the page does this once, before its first draw). Returns the mode. */
export function initMode({ storage = storageOf(), root = rootOf() } = {}) {
  return applyMode(readMode(storage), root);
}

/** Apply a choice and keep it. A word that is not a mode is "system". Returns the mode. */
export function setMode(mode, { storage = storageOf(), root = rootOf() } = {}) {
  const chosen = applyMode(mode, root);
  try {
    if (storage) storage.setItem(KEY, chosen);
  } catch (e) {
    // not kept: the choice stays for this session
  }
  return chosen;
}
