// The HTML of the Building's floor plates and of the other labels the building and room scenes add (handoff building.md "Floor plate",
// scene.md 6), and the pure arithmetic that stacks the plates in a column without overlap. A plate is a card at the right edge of its
// floor; when six or more would not fit the free height they all become the compact form (name row and meters). Every fact on a plate is
// also in the floors list: the plates are `aria-hidden`. The compact floor card (WP-9.8) is one component for the phone's card at the top
// right of the scene and for each row of the floors list; the plates stay on the desktop and the tablet (WP-9.10: the maintainer's
// change was for the phone only).

import { h } from "../dom.js";
import { METER_TIPS, METER_WORDS, costNote } from "../format.js";

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
 * A meter's track: the fill in the theme colour for `share` and, when something is reserved (`reservedShare` above zero), a second segment in the
 * reserved tint right after it, on the same line (A-20). Every meter of the page is made by this.
 */
export function trackNode(share, full, reservedShare = 0, extraClass = "") {
  const fill = h("span", { class: `wb-meter-fill${full ? " is-full" : ""}` });
  fill.style.setProperty("--wb-share", `${Math.round(share * 100)}%`);
  const track = h("span", { class: `wb-meter${reservedShare > 0 ? " has-reserved" : ""}${extraClass ? ` ${extraClass}` : ""}`, "aria-hidden": "true" }, fill);
  if (reservedShare > 0) {
    const reserved = h("span", { class: "wb-meter-reserved" });
    reserved.style.setProperty("--wb-share", `${Math.round(reservedShare * 100)}%`);
    track.append(reserved);
  }
  return track;
}

function meter(label, text, share, full, note, tip, reservedShare = 0) {
  return h("div", { class: "wb-plate-meter", title: tip || null },
    h("span", { class: "wb-plate-meter-text" }, label ? h("span", { class: "wb-muted", text: `${label} ` }) : null, h("span", { text })),
    trackNode(share, full, reservedShare),
    note ? h("span", { class: "wb-plate-note", text: note }) : null);
}

/** The chips of a plate (A-12), in this order and each only when its count is not zero: done, running, queued, left (planned or blocked). */
export function chipNodes(p) {
  const chips = [["done", p.done, "pui-success"], ["running", p.running, "pui-theme"], ["queued", p.queued, "pui-surface"], ["left", p.left, "pui-muted"]];
  return chips.filter(([, count]) => count > 0).map(([word, count, tone]) => h("span", { class: `pui-badge ${tone} pui-soft pui-rounded-full`, text: `${count} ${word}` }));
}

/**
 * A floor plate. p: {name, label, dot, decisions, word, done, running, left, queued, runsText, runsShare, usdText, usdShare,
 * unknown, mode, pips, acting, actingPips, selected, off}. Returns the element; the caller toggles `is-compact`. The same component is the plate
 * beside a floor (a `div`) and each row of the floors list (`tag` "a", `attrs` {class: "wb-floor-row is-row", href, aria-label}): one design, two places.
 */
export function plateNode(p, attrs = {}, tag = "div") {
  const row1 = h("div", { class: "wb-plate-row" },
    h("span", { class: `wb-dot is-${p.dot}` }),
    h("strong", { class: "wb-plate-name", text: p.label }),
    p.decisions > 0 ? h("span", { class: "pui-badge pui-warn pui-soft pui-rounded-full", text: String(p.decisions) }) : null,
    h("span", { class: "wb-plate-state", text: p.word }));
  const chips = h("div", { class: "wb-plate-chips" }, chipNodes(p), p.mode ? modePlate(p.mode, p.pips, p.acting, p.actingPips) : null);
  const meters = h("div", { class: "wb-plate-meters" },
    meter(METER_WORDS.runs, p.runsText, p.runsShare, p.runsShare >= 1, "", METER_TIPS.runs),
    meter(METER_WORDS.spend, p.usdText, p.usdRecordedShare !== undefined ? p.usdRecordedShare : p.usdShare, p.usdShare >= 1,
      costNote(p.usdNote, p.usdReserved, p.unknown), METER_TIPS.spend, p.usdReservedShare || 0));
  const node = h(tag, { ...attrs, class: `wb-plate${p.selected ? " is-selected" : ""}${p.off ? " is-off" : ""}${attrs.class ? ` ${attrs.class}` : ""}`, "data-floor": p.name }, row1, chips, meters);
  return node;
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

/**
 * Stack boxes in one column with no overlap. items: [{want, height}] (want is the wished centre, in pixels, from the
 * floor's own height on screen); the result is the centre of each, in the same order, kept inside [top, bottom] with
 * `gap` between neighbours. Order follows `want`. When the column cannot fit, `fits` is false and the result is still the
 * tightest packing from the top (the caller then asks for compact plates).
 */
export function stackColumn(items, top, bottom, gap) {
  const order = items.map((item, index) => ({ ...item, index })).sort((a, b) => a.want - b.want || a.index - b.index);
  const total = order.reduce((sum, item) => sum + item.height, 0) + gap * Math.max(0, order.length - 1);
  const room = bottom - top;
  const fits = total <= room;
  const tops = order.map((item) => item.want - item.height / 2);
  // push down so none overlaps the one above, then pull up so none passes the bottom
  for (let i = 0; i < order.length; i++) {
    const min = i === 0 ? top : tops[i - 1] + order[i - 1].height + gap;
    if (tops[i] < min) tops[i] = min;
  }
  if (fits) {
    for (let i = order.length - 1; i >= 0; i--) {
      const max = i === order.length - 1 ? bottom - order[i].height : tops[i + 1] - gap - order[i].height;
      if (tops[i] > max) tops[i] = max;
    }
  }
  const centres = new Array(items.length);
  order.forEach((item, i) => { centres[item.index] = tops[i] + item.height / 2; });
  return { centres, fits };
}
