// F-6 the tracking bar and its "Now on" card. Desktop and phone have their own markup (the phone's is a row that opens
// a list of the steps in a sheet); CSS shows one of them.

import { h } from "../dom.js";
import { keepFocus } from "./arrows.js";
import { icon } from "./icons.js";

// Node states (the design system's state table): the class of the icon and its glyph. `failed` and `blocked` use the x,
// `cancelled` the minus (OPEN-14, only icons the design tool's bundle holds).
const NODE = {
  done: ["pui-success pui-soft", "check"], waiting: ["pui-warn pui-soft", "circle-alert"], running: ["pui-theme pui-outline is-running", "activity"],
  ready: ["pui-muted pui-outline", "clock"], requested: ["pui-muted pui-outline", "clock"], planned: ["pui-muted pui-outline", "clock"],
  failed: ["pui-error pui-soft", "x"], blocked: ["pui-error pui-outline", "x"], cancelled: ["pui-muted pui-outline", "minus"],
};

function nodeIcon(state, size) {
  const [cls, glyph] = NODE[state] || NODE.ready;
  return h("span", { class: `pui-checkpoint-icon ${cls}`, "aria-hidden": "true" }, icon(glyph, size));
}

function badge(request) {
  return h("span", { class: "pui-badge pui-muted pui-soft pui-rounded-full wb-req-id", text: `#${request.id}` });
}

export function createTrack({ onOpenSteps }) {
  const desktop = h("div", { class: "wb-track-desktop" });
  const phone = h("div", { class: "wb-track-phone" });
  const el = h("section", { class: "pui-card wb-track", role: "region", "aria-label": "Tracking bar" }, desktop, phone);

  function stepsList(model, size, vertical = false) {
    return h("ol", { class: `pui-timeline${vertical ? "" : " pui-group-row"} wb-steps`, "aria-label": `Request ${model.request.id}, ${model.request.title}, ${model.doneCount} of ${model.total} steps done` },
      model.steps.map((s) => h("li", { class: "pui-checkpoint wb-step" },
        nodeIcon(s.state, size),
        h("a", { class: "wb-step-text", href: s.link, "aria-label": s.name },
          h("strong", { class: "wb-step-title", text: s.title }), h("span", { class: "wb-step-sub", text: s.sub })))));
  }

  function nowCard(model) {
    if (!model.now) {
      return h("div", { class: "wb-now" },
        h("span", { class: "wb-now-where", text: "Nothing is running" }),
        h("strong", { class: "wb-now-title", text: model.request.title || `Request ${model.request.id}` }),
        h("span", { class: "wb-now-sub", text: `request #${model.request.id} · ${model.request.state}` }));
    }
    const now = model.now;
    return h("div", { class: "wb-now" },
      h("span", { class: "wb-now-where", text: now.where }),
      h("a", { class: "wb-now-title", href: now.link, text: now.title }),
      h("div", { class: "wb-now-row" },
        h("span", { class: `pui-chip pui-soft ${now.running ? "pui-theme" : "pui-warn"} wb-chip-small`, text: now.state }),
        h("span", { class: "wb-now-sub", text: now.sub })));
  }

  function draw(model, state) {
    if (state === "loading" || !model) {
      const text = state === "loading" ? "Loading the request..." : "No request is open";
      desktop.replaceChildren(h("div", { class: "wb-track-left" }, h("p", { class: "wb-empty", text })));
      phone.replaceChildren(h("p", { class: "wb-empty", text }));
      return;
    }
    const r = model.request;
    const countText = `${model.doneCount} of ${model.total} steps done`;
    desktop.replaceChildren(
      h("div", { class: "wb-track-left" },
        h("div", { class: "wb-track-head" }, badge(r), h("strong", { class: "wb-track-title", text: r.title || `Request ${r.id}` }),
          h("span", { class: "wb-track-project", text: r.project }), h("span", { class: "wb-track-count", text: countText })),
        model.steps.length ? stepsList(model, 13) : h("p", { class: "wb-empty", text: `Request ${r.id} has no steps yet (${r.state}).` })),
      nowCard(model));
    const current = model.now;
    const open = h("button", { class: "pui-btn pui-link wb-track-open", type: "button", "aria-label": `Steps of request ${r.id}, ${countText}. Open the list` },
      h("span", { class: "wb-dots", "aria-hidden": "true" }, model.steps.map((s) => nodeIcon(s.state, 12))),
      h("span", { class: "wb-track-now-text" },
        h("strong", { text: current ? current.title : (r.title || `Request ${r.id}`) }),
        h("span", { class: "wb-step-sub", text: current ? `${current.where.replace(/^Now on |^Waiting on /, "")} · ${current.state.toLowerCase()}` : r.state })));
    open.addEventListener("click", () => onOpenSteps(`Request ${r.id}, ${r.title || ""}`, model.steps.length ? stepsList(model, 13, true) : h("p", { class: "wb-empty", text: "No steps yet." }), open));
    phone.replaceChildren(
      h("div", { class: "wb-track-head" }, badge(r), h("strong", { class: "wb-track-title", text: r.title || `Request ${r.id}` }),
        h("span", { class: "wb-track-count", text: `${model.doneCount} of ${model.total} done` })),
      open);
  }

  let shown = "";
  return {
    el,
    /** model: model.tracking(...) or null; state: "ready", "loading" or "empty"; stale: dim it (the last data after a failed read). */
    set(model, state, stale = false) {
      el.classList.toggle("is-stale", stale);
      const key = JSON.stringify([model, state]);
      if (key === shown) return;
      shown = key;
      keepFocus(el, () => draw(model, state));
    },
  };
}
