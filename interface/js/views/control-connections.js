// The Connections tab of the Control room: the requirement classes the skills in scope need, the secrets by name (never a
// value, never a masked value or a length), the eval image and the platform. It shows what the `connections` operation
// returned. The Platform card shows `here` and `evidence` and the chip `same` gives; it states no consequence of a
// difference (the supervisor's decision: the runtime has none, so the page states none).

import { h } from "../dom.js";
import * as model from "./control-model.js";
import { cell, chip, code, eyebrow, failedCard, FAILED_TITLE, loadingCard, tableCard } from "./control-parts.js";

function classesTable(rows) {
  const head = ["Class", "Provider", "Status", "Needed by"];
  return h("table", { class: "pui-table wb-table wb-stackable" },
    h("caption", { class: "wb-sr", text: "Requirement classes the skills in scope need, and whether a provider was found" }),
    h("thead", {}, h("tr", {}, head.map((t) => h("th", { scope: "col", text: t })))),
    h("tbody", {}, rows.map((r) => h("tr", {},
      cell("Class", code(r.class)),
      h("td", { "data-label": "Provider", title: r.note || null, text: r.provider }),
      cell("Status", chip(`pui-chip ${r.found ? "pui-success" : "pui-error"} pui-soft`, r.status)),
      cell("Needed by", r.needed ? code(r.needed) : "-")))));
}

function secretsTable(rows) {
  const head = ["Name", "Status", "Where"];
  return h("table", { class: "pui-table wb-table wb-stackable" },
    h("caption", { class: "wb-sr", text: "Secrets by name: found or missing, and where; never a value" }),
    h("thead", {}, h("tr", {}, head.map((t) => h("th", { scope: "col", text: t })))),
    h("tbody", {}, rows.map((r) => h("tr", { "aria-label": model.secretName(r) },
      cell("Name", code(r.name)),
      cell("Status", chip(`pui-chip ${r.found ? "pui-success" : "pui-error"} pui-soft`, r.status)),
      cell("Where", r.where)))));
}

function imageCard(spec) {
  return h("div", { class: "pui-card wb-sunken-card wb-info-card" },
    eyebrow("Image"),
    h("div", { class: "wb-info-row" }, h("code", { class: "wb-code wb-strong", text: spec.name }), chip(`pui-chip ${spec.tone} pui-soft`, spec.chip)),
    h("span", { class: "wb-muted", text: spec.sentence }));
}

function platformCard(spec) {
  const lines = [
    h("span", { class: "wb-platform-line" }, "This machine: ", code(spec.here)),
    h("span", { class: "wb-platform-line" }, "Evidence: ", code(spec.evidence)),
  ];
  return h("div", { class: `pui-card wb-sunken-card wb-info-card${spec.differs ? " is-wide" : ""}` },
    eyebrow("Platform"),
    h("div", { class: "wb-info-row" }, h("span", { class: "wb-platform" }, lines), spec.chip ? chip(`pui-chip ${spec.tone} pui-soft`, spec.chip) : null));
}

/** The tab. Returns {el, set(state)}; state: {status: "loading"|"ready"|"failed", data, error}. */
export function createConnectionsTab() {
  const el = h("div", { class: "wb-tab-body" });
  return {
    el,
    set(state) {
      if (state.status === "loading") {
        el.replaceChildren(loadingCard(model.LOADING));
        return;
      }
      if (state.status === "failed") {
        el.replaceChildren(failedCard(FAILED_TITLE, state.error));
        return;
      }
      const data = state.data;
      const classes = model.classRows(data);
      const secrets = model.secretRows(data);
      const platform = model.platformCard(data);
      const note = typeof data.secrets_note === "string" && data.secrets_note ? data.secrets_note : null;
      el.replaceChildren(...[
        eyebrow("Requirement classes"),
        tableCard(classesTable(classes)),
        eyebrow("Secrets (names only, never a value)"),
        tableCard(secretsTable(secrets)),
        note ? h("p", { class: "wb-muted wb-note", text: note }) : null,
        h("div", { class: `wb-info-grid${platform.differs ? " is-stacked" : ""}` }, imageCard(model.imageCard(data)), platformCard(platform)),
      ].filter(Boolean));
    },
  };
}
