// The HTML of the floor card and of the other labels the building and room scenes add (handoff building.md, scene.md 6). The
// floor card is one compact component: the Building shows it at the scene's top right for the floor that is hovered or selected, and
// the floors list uses it for each row (WP-9.8: there is no plate beside each floor any more).

import { h } from "../dom.js";

/** The mode's pips: four 5 px squares, as many filled as the mode counts. */
export function pips(count) {
  const node = h("span", { class: "wb-pips", "aria-hidden": "true" });
  for (let i = 0; i < 4; i++) node.append(h("span", { class: `wb-pip${i < count ? " is-on" : ""}` }));
  return node;
}

/** The mode plate: the mode word and its pips; a second small plate "acting as <mode>" when it differs. */
export function modePlate(mode, pipCount, acting, actingPips) {
  const wrap = h("span", { class: "wb-mode-wrap" });
  wrap.append(h("span", { class: "pui-chip pui-muted pui-outline pui-rounded-full wb-mode-plate" }, h("span", { text: mode }), pips(pipCount)));
  if (acting && acting !== mode) {
    wrap.append(h("span", { class: "pui-chip pui-muted pui-outline pui-rounded-full wb-mode-plate wb-acting-plate" }, h("span", { text: `acting as ${acting}` }), pips(actingPips)));
  }
  return wrap;
}

/**
 * The compact floor card (WP-9.8): one component for the card at the scene's top right and for every row of the floors list, so
 * the two never differ. c: cardOf(row). Returns the element: the name row (state dot, name, decisions badge), the state word
 * with the mode plate, and one line of runs and spend. `tag` is "div" for the corner card and "a" for a list row (attrs: href, aria-label).
 */
export function floorCardNode(c, attrs = {}, tag = "div") {
  const head = h("span", { class: "wb-fc-head" },
    h("span", { class: `wb-dot is-${c.dot}` }),
    h("strong", { class: "wb-fc-name", text: c.label }),
    c.decisions > 0 ? h("span", { class: "pui-badge pui-warn pui-soft pui-rounded-full", text: String(c.decisions) }) : null);
  const status = h("span", { class: "wb-fc-status" },
    h("span", { class: "wb-fc-state", text: c.word }),
    c.mode ? modePlate(c.mode, c.pips, c.acting, c.actingPips) : null);
  const klass = `wb-floor-card${c.off ? " is-off" : ""}${attrs.class ? ` ${attrs.class}` : ""}`;
  return h(tag, { ...attrs, class: klass, "data-floor": c.name }, head, status, c.runsLine ? h("span", { class: "wb-fc-runs", text: c.runsLine }) : null);
}

/** The work-order tag's label: "#14". */
export function tagNode(spec) {
  return h("div", { class: "wb-label wb-label-tag", text: spec.text });
}

/** The board label above the room's wall board: the state dot, the title, and a mono line. */
export function boardNode(spec) {
  return h("div", { class: "wb-label wb-label-board" },
    h("div", { class: "wb-label-row" }, h("span", { class: `wb-dot is-${spec.dot}` }), h("strong", { class: "wb-label-name", text: spec.title })),
    ...spec.lines.map((line) => h("div", { class: "wb-label-sub mono", text: line })));
}

/** The door's label in the Lobby. */
export function doorNode(spec) {
  return h("div", { class: "wb-label wb-label-door" }, h("span", { class: "pui-btn pui-theme pui-soft wb-door-tag", text: spec.text }));
}
