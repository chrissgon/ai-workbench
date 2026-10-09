// The HTML labels over the canvas (handoff scene.md 6): elements in an overlay, placed from a projected 3D anchor.
// A position is written only through the CSS Object Model (`--wb-x` and `--wb-y`, read by a class as `translate`): the
// page forbids an inline style attribute and style text, and a CSSOM write is neither. Positions are worked out on
// demand (data, camera or size changed: one frame each while the camera moves, none while it is still); labels over the budget or
// overlapping are culled.

import { h } from "../dom.js";
import { cull, rankOf } from "./cull.js";
import { stackColumn } from "./plates.js";

/** The card of a building: a dot (theme when a task runs), the name, the decisions badge and a sub line. */
export function cityCard(spec) {
  const node = h("div", { class: `wb-label wb-label-card${spec.selected ? " is-selected" : ""}` });
  const row = h("div", { class: "wb-label-row" },
    h("span", { class: `wb-dot${spec.running ? " is-running" : ""}` }),
    h("strong", { class: "wb-label-name", text: spec.name }));
  if (!spec.accepted) row.append(h("span", { class: "pui-chip pui-warn pui-soft wb-chip-small", text: "Not accepted" }));
  else if (spec.decisions > 0) row.append(h("span", { class: "pui-badge pui-warn pui-soft pui-rounded-full", text: String(spec.decisions) }));
  node.append(row, h("div", { class: "wb-label-sub", text: spec.sub }));
  return node;
}

/** Create the nodes of a built scene's labels in `overlay`: [{spec, node, width, height}]. */
export function mountLabels(overlay, specs, { popped = new Set() } = {}) {
  const entries = specs.map((spec) => {
    const node = spec.make ? spec.make(spec) : cityCard(spec);
    if (popped.has(spec.id)) {
      node.classList.add("is-pop");
      node.addEventListener("animationend", () => node.classList.remove("is-pop"), { once: true });
    }
    overlay.appendChild(node);
    return { spec, node, width: node.offsetWidth, height: node.offsetHeight };
  });
  return entries;
}

/** The gap between two plates of the column, in pixels (the export's 5 px). */
export const PLATE_GAP = 5;
const PLATE_OFFSET = 14;

/** Put the plates of a building in one column to the right of it, none over another; compact when they do not fit. */
function placeColumn(plates, project, hidden, insets, size) {
  for (const { entry } of plates) entry.node.classList.toggle("is-culled", hidden);
  if (hidden || !plates.length || !size) return;
  const ins = { top: 0, bottom: 0, plateRight: 0, ...(insets || {}) };
  const points = plates.map(({ entry }) => project(entry.spec.anchor));
  const plateWidth = plates[0].entry.node.offsetWidth || 290;
  const edge = Math.max(...points.map((p) => p.x)) + PLATE_OFFSET;
  const x = Math.max(0, Math.min(edge, size.w - ins.plateRight - plateWidth));
  const top = ins.top;
  const bottom = size.h - ins.bottom;
  const measure = () => plates.map(({ entry }, i) => ({ want: points[i].y, height: entry.node.offsetHeight || 90 }));
  // a plate shortens as the free height shrinks: the whole plate, then the name row and the meters, then the name row alone
  for (const { entry } of plates) entry.node.classList.remove("is-compact", "is-tiny");
  let result = stackColumn(measure(), top, bottom, PLATE_GAP);
  if (!result.fits) {
    for (const { entry } of plates) entry.node.classList.add("is-compact");
    result = stackColumn(measure(), top, bottom, PLATE_GAP);
  }
  if (!result.fits) {
    for (const { entry } of plates) entry.node.classList.add("is-tiny");
    result = stackColumn(measure(), top, bottom, PLATE_GAP);
  }
  plates.forEach(({ entry }, i) => {
    entry.node.style.setProperty("--wb-x", `${x.toFixed(1)}px`);
    entry.node.style.setProperty("--wb-y", `${result.centres[i].toFixed(1)}px`);
  });
}

/**
 * Place the labels: project each anchor with the camera, write the position, and hide the ones the culling drops. `project(anchor)`
 * returns {x, y} in pixels of the scene area. `hidden` hides all. A label with `place: "column"` is a floor plate: the plates are
 * stacked beside the building and never culled. `insets` and `size` are the free rectangle's (placeColumn).
 */
export function placeLabels(entries, project, { hidden = false, insets = null, size = null } = {}) {
  const plates = [];
  const items = [];
  entries.forEach((entry, index) => {
    if (entry.spec.place === "column") {
      plates.push({ entry, index });
      return;
    }
    const p = project(entry.spec.anchor);
    entry.node.style.setProperty("--wb-x", `${p.x.toFixed(1)}px`);
    entry.node.style.setProperty("--wb-y", `${p.y.toFixed(1)}px`);
    items.push({
      id: index, rank: entry.spec.rank !== undefined ? entry.spec.rank : rankOf(entry.spec),
      rect: { left: p.x - entry.width / 2, right: p.x + entry.width / 2, top: p.y - entry.height, bottom: p.y },
    });
  });
  const kept = hidden ? new Set() : cull(items);
  for (const item of items) entries[item.id].node.classList.toggle("is-culled", !kept.has(item.id));
  placeColumn(plates, project, hidden, insets, size);
}

/**
 * The corner slot's position: the top right of the scene area, in pixels. Its right edge is the scene's own (`insets.cornerRight`, or
 * the panels' right inset when the page gives none) and its top is the free rectangle's: below the KPI row. On a phone the page gives
 * `cornerBottom` (the distance from the scene's bottom edge to the card's bottom edge) and `cornerLeft`: the card is then anchored at the
 * bottom, its bottom left corner at that point (`bottom: true` tells the engine to hang it from there).
 */
export function cornerPosition(size, insets) {
  const ins = { right: 0, top: 0, ...(insets || {}) };
  if (ins.cornerBottom !== undefined) return { x: ins.cornerLeft !== undefined ? ins.cornerLeft : 10, y: Math.max(0, size.h - ins.cornerBottom), bottom: true };
  const right = ins.cornerRight !== undefined ? ins.cornerRight : ins.right;
  return { x: Math.max(0, size.w - right), y: Math.max(0, ins.top) };
}

/**
 * The insets the camera fits the scene into: when the page pins a card in the corner (`cornerRight` is given: the phone's floor
 * card), the diorama is fitted below it, so the card sits over empty space and not over the back wall. `cornerHeight` is the card's
 * measured height in pixels (0 when there is none). A card anchored at the bottom (`cornerBottom`) takes its room from the bottom instead.
 */
export function fitInsets(insets, cornerHeight, gap = 8) {
  const ins = insets || {};
  if (!cornerHeight) return ins;
  if (ins.cornerBottom !== undefined) return { ...ins, bottom: ins.cornerBottom + cornerHeight + gap };
  if (ins.cornerRight === undefined) return ins;
  return { ...ins, top: (ins.top || 0) + cornerHeight + gap };
}
