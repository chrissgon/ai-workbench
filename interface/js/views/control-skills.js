// The Skills tab of the Control room (handoff control-room.md): the checks notice (when a check failed), the legend, the
// filters, the table of skills (a card per skill on a phone) and the two sentences of an open row. It shows what the
// `skills` operation returned: the band is its word, the score its number. The filters only narrow the rows on the page.

import { h } from "../dom.js";
import { icon } from "../frame/icons.js";
import * as model from "./control-model.js";
import { cell, chip, code, emptyBlock, failedCard, FAILED_TITLE, loadingCard, tableCard } from "./control-parts.js";

const PHONE = "(max-width: 639px)";

function chipCell(skill, tier) {
  const found = model.chipOf(skill, tier);
  if (!found) return "-";
  return [chip(found.className, found.band), ` ${found.score}`];
}

/** The tab. Returns {el, set(state), dispose()}; state: {status: "loading"|"ready"|"failed", data, error}. */
export function createSkillsTab() {
  const el = h("div", { class: "wb-tab-body" });
  const ui = { area: "", band: "", name: "", open: new Set() };
  let skills = [];
  let filters = null;     // built once, so that typing in the search field keeps its focus
  let results = null;
  let detailCounter = 0;
  const phone = window.matchMedia(PHONE);
  const onPhone = () => { if (filters) filters.box.open = !phone.matches; };
  phone.addEventListener("change", onPhone);

  function buildFilters() {
    const area = h("select", { class: "pui-input wb-field" });
    const band = h("select", { class: "pui-input wb-field" },
      h("option", { value: "", text: "All bands" }), model.BANDS.map((b) => h("option", { value: b, text: b })));
    const name = h("input", { class: "pui-input wb-field", type: "text", autocomplete: "off", spellcheck: "false" });
    const group = (label, control) => h("label", { class: "pui-field-group" }, h("span", { text: label }), control);
    const box = h("details", { class: "pui-accordion-item wb-filters" },
      h("summary", { text: "Filters" }),
      h("div", { class: "wb-filter-body" }, group("Area", area), group("Band", band), group("Search by name", name)));
    box.open = !phone.matches;
    area.addEventListener("change", () => { ui.area = area.value; renderResults(); });
    band.addEventListener("change", () => { ui.band = band.value; renderResults(); });
    name.addEventListener("input", () => { ui.name = name.value; renderResults(); });
    return { box, area, band, name };
  }

  function fillAreas() {
    const areas = model.areasOf(skills);
    if (ui.area && !areas.includes(ui.area)) ui.area = "";
    filters.area.replaceChildren(h("option", { value: "", text: "All areas" }), ...areas.map((a) => h("option", { value: a, text: a })));
    filters.area.value = ui.area;
  }

  function toggle(name, on, nodes) {
    if (on) ui.open.add(name); else ui.open.delete(name);
    nodes.button.setAttribute("aria-expanded", String(on));
    nodes.button.classList.toggle("is-open", on);
    nodes.detail.hidden = !on;
    nodes.row.classList.toggle("is-open", on);
  }

  function tableRow(skill) {
    detailCounter += 1;
    const id = `wb-skill-detail-${detailCounter}`;
    const open = ui.open.has(skill.name);
    const chevron = icon("chevron-down", 12);
    const button = h("button", { class: `wb-expander${open ? " is-open" : ""}`, type: "button", "aria-expanded": String(open), "aria-controls": id },
      chevron, code(skill.name));
    const row = h("tr", { class: open ? "is-open" : "" },
      cell("Skill", button), cell("Version", String(skill.version)), cell("Area", String(skill.area)),
      cell("Manifest", model.manifestText(skill)), cell("Runs here", String(skill.runs_here ?? "-")),
      cell("Reference model", chipCell(skill, "strong")), cell("Floor model", chipCell(skill, "floor")));
    const lines = model.detailLines(skill);
    const detail = h("tr", { class: "wb-detail-row", id, hidden: !open },
      h("td", { colspan: "7" }, h("div", { class: "wb-detail" }, lines.map((line) => h("span", { text: line })))));
    const nodes = { button, detail, row };
    button.addEventListener("click", () => toggle(skill.name, button.getAttribute("aria-expanded") !== "true", nodes));
    return [row, detail];
  }

  function card(skill) {
    const open = ui.open.has(skill.name);
    const lines = model.detailLines(skill);
    const rows = h("div", { class: "wb-card-rows" },
      h("div", { class: "wb-card-line" }, code(skill.name), h("span", { class: "wb-muted", text: `${skill.version} · ${skill.area}` })),
      h("span", { class: "wb-muted", text: `Manifest ${model.manifestText(skill)} · ${skill.runs_here ?? "-"} runs here` }),
      h("div", { class: "wb-card-tiers" },
        model.TIER_COLUMNS.flatMap(([tier]) => [
          h("span", { class: "wb-muted", text: tier === "strong" ? "Reference" : "Floor" }),
          h("span", {}, chipCell(skill, tier)),
        ])));
    const details = h("details", { class: "pui-accordion-item wb-skill-card", open },
      h("summary", {}, rows),
      h("div", { class: "wb-detail" }, lines.map((line) => h("span", { text: line }))));
    details.addEventListener("toggle", () => { if (details.open) ui.open.add(skill.name); else ui.open.delete(skill.name); });
    return details;
  }

  function renderResults() {
    const shown = model.filterSkills(skills, ui);
    if (!shown.length) {
      results.replaceChildren(emptyBlock("No skill matches these filters."));
      return;
    }
    const table = h("table", { class: "pui-table wb-table" },
      h("caption", { class: "wb-sr", text: "Skills in scope, with their band and score on the reference model and the floor model" }),
      h("thead", {}, h("tr", {}, ["Skill", "Version", "Area", "Manifest", "Runs here", "Reference model", "Floor model"].map((t) => h("th", { scope: "col", text: t })))),
      h("tbody", {}, shown.flatMap(tableRow)));
    results.replaceChildren(
      tableCard(table, "wb-skill-table"),
      h("div", { class: "wb-skill-cards" }, shown.map(card)));
  }

  function legend() {
    return h("div", { class: "wb-legend" },
      model.BANDS.map((b) => h("span", { class: `${model.bandClass(b)} wb-chip-legend`, text: b })),
      "band per model tier, with the score");
  }

  function notice(spec) {
    return h("div", { class: "wb-check-notice", role: "alert" },
      h("strong", { class: "wb-failed-title", text: spec.title }),
      h("span", { text: spec.sentence }),
      spec.lines.map((line) => h("span", { class: "wb-muted", text: line })));
  }

  function render(state) {
    if (state.status === "loading") {
      el.replaceChildren(loadingCard(model.LOADING));
      return;
    }
    if (state.status === "failed") {
      el.replaceChildren(failedCard(FAILED_TITLE, state.error));
      return;
    }
    skills = Array.isArray(state.data.skills) ? state.data.skills : [];
    const spec = model.checksNotice(state.data.checks);
    if (!skills.length) {
      el.replaceChildren(...[spec ? notice(spec) : null, emptyBlock("No skills are in scope of this project.")].filter(Boolean));
      return;
    }
    if (!filters) {
      filters = buildFilters();
      results = h("div", { class: "wb-results" });
    }
    fillAreas();
    renderResults();
    // the notice comes first: whether any skill runs as proven is decided by it (OPEN-26, recommended answer)
    el.replaceChildren(...[spec ? notice(spec) : null, legend(), filters.box, results].filter(Boolean));
  }

  return {
    el,
    set: render,
    dispose() {
      phone.removeEventListener("change", onPhone);
    },
  };
}
