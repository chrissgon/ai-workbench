// The page: the token prompt, the project list and a project's placeholder, chosen by the hash (#/ or #/p/<id>).

import * as api from "./api.js";
import { fill, h } from "./dom.js";
import { clearToken, getToken, setToken } from "./token.js";
import { showProject } from "./views/project.js";
import { showProjects } from "./views/projects.js";
import { showTokenPrompt } from "./views/token-prompt.js";

const root = document.getElementById("app");
const forget = document.getElementById("forget-token");
const PROJECT_HASH = /^#\/p\/([0-9a-f]{12})$/;
let drawing = 0;   // a newer draw makes an older one stop
let pendingMessage = null;

function askForToken(message) {
  drawing += 1;
  forget.hidden = true;
  showTokenPrompt(root, {
    message: message || pendingMessage,
    onSubmit: async (pasted) => {
      setToken(pasted);
      pendingMessage = null;
      await draw();
    },
  });
  pendingMessage = null;
}

api.onAuthFailure(() => {
  clearToken();
  pendingMessage = "The service did not accept the token. It makes a new one every time it starts: paste the current one.";
  askForToken();
});

function failure(error) {
  if (error && error.name === "ApiError") return error.message;
  return "Something went wrong while drawing the page.";
}

async function draw() {
  if (!getToken()) {
    askForToken();
    return;
  }
  const mine = ++drawing;
  forget.hidden = false;
  fill(root, h("p", { class: "muted", text: "Loading..." }));
  const wanted = PROJECT_HASH.exec(window.location.hash);
  try {
    const listed = await api.projects();
    if (mine !== drawing) return;
    if (!wanted) {
      showProjects(root, listed, { onRefresh: draw });
      return;
    }
    const entry = (listed.projects || []).find((p) => p.id === wanted[1]) || null;
    if (!entry) {
      showProject(root, { entry: null, error: "The service has no such project." });
      return;
    }
    try {
      const state = await api.status(entry.id);
      if (mine !== drawing) return;
      showProject(root, { entry, state });
    } catch (e) {
      if (mine !== drawing || (e && e.unauthorized)) return;
      showProject(root, { entry, error: failure(e) });
    }
  } catch (e) {
    if (mine !== drawing || (e && e.unauthorized)) return;
    fill(root, h("p", { class: "notice error", role: "alert", text: failure(e) }));
  }
}

forget.addEventListener("click", () => {
  clearToken();
  askForToken();
});
window.addEventListener("hashchange", draw);
draw();
