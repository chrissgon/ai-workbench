// The HTML labels over the canvas (handoff scene.md 6): elements in an overlay, placed from a projected 3D anchor.
// A position is written only through the CSS Object Model (`--wb-x` and `--wb-y`, read by a class as `translate`): the
// page forbids an inline style attribute and style text, and a CSSOM write is neither. Positions are worked out on
// demand (data, camera or size changed), never every frame; labels over the budget or overlapping are culled.

import { h } from "../dom.js";
import { cull, rankOf } from "./cull.js";

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
    const node = cityCard(spec);
    if (popped.has(spec.id)) {
      node.classList.add("is-pop");
      node.addEventListener("animationend", () => node.classList.remove("is-pop"), { once: true });
    }
    overlay.appendChild(node);
    return { spec, node, width: node.offsetWidth, height: node.offsetHeight };
  });
  return entries;
}

/**
 * Place the labels: project each anchor with the camera, write the position, and hide the ones the culling drops.
 * `project(anchor)` returns {x, y} in pixels of the scene area. `hidden` hides all (a camera move).
 */
export function placeLabels(entries, project, { hidden = false } = {}) {
  const items = entries.map((entry, index) => {
    const p = project(entry.spec.anchor);
    entry.node.style.setProperty("--wb-x", `${p.x.toFixed(1)}px`);
    entry.node.style.setProperty("--wb-y", `${p.y.toFixed(1)}px`);
    return {
      id: index, rank: rankOf(entry.spec),
      rect: { left: p.x - entry.width / 2, right: p.x + entry.width / 2, top: p.y - entry.height, bottom: p.y },
    };
  });
  const kept = hidden ? new Set() : cull(items);
  entries.forEach((entry, index) => entry.node.classList.toggle("is-culled", !kept.has(index)));
}
