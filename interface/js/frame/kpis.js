// F-3 the three KPI cards: open decisions, runs today and spend today, each labelled by what it counts. The meter is
// a display division (used over cap), hidden from the accessibility tree: the number is in the text.

import { h } from "../dom.js";
import * as format from "../format.js";
import { icon } from "./icons.js";

// A card's label has a long and a short form: the tablet layout shows the short one ("Decisions", "Runs", "Spend"), the others the long one.
function card(label, iconName, tone, withMeter, short) {
  const figure = h("strong", { class: "wb-kpi-figure", text: "..." });
  const unit = h("span", { class: "wb-kpi-unit", text: "" });
  const meterFill = h("span", { class: "wb-meter-fill" });
  const reservedFill = h("span", { class: "wb-meter-reserved" });
  const note = h("span", { class: "wb-kpi-note wb-muted", text: "" });
  const track = h("span", { class: "wb-meter", "aria-hidden": "true" }, meterFill, reservedFill);
  const body = [h("span", { class: "wb-kpi-label" }, h("span", { class: "wb-kpi-long", text: label }), h("span", { class: "wb-kpi-short", text: short })), h("div", { class: "wb-kpi-row" }, figure, unit)];
  if (withMeter) body.push(track);
  if (withMeter && short === "Spend") body.push(note);       // both numbers of the day's spend, labelled, when something is reserved
  const el = h("div", { class: "pui-card wb-kpi", role: "group", "aria-label": `${label}, loading` },
    h("span", { class: `wb-kpi-tile pui-soft pui-${tone}` }, icon(iconName, 16)),
    h("div", { class: "wb-kpi-body" }, body));
  return { el, figure, unit, meterFill, reservedFill, track, note, label };
}

export function createKpis() {
  const decisions = card("Open decisions", "inbox", "warn", false, "Decisions");
  const runs = card(format.METER_WORDS.runs, "activity", "theme", true, "Runs");
  const spend = card(format.METER_WORDS.spend, "credit-card", "theme", true, "Spend");
  const el = h("div", { class: "wb-kpis" }, decisions.el, runs.el, spend.el);

  function meter(c, fraction, reserved = 0) {
    c.meterFill.style.setProperty("--wb-share", `${Math.round(fraction * 100)}%`);
    c.meterFill.classList.toggle("is-full", fraction + reserved >= 1);
    c.reservedFill.style.setProperty("--wb-share", `${Math.round(reserved * 100)}%`);
    c.track.classList.toggle("has-reserved", reserved > 0);
  }

  return {
    el,
    /** sums: {decisions, runs, runsCap, usd, usdCap, usdRecorded, usdReserved, runsTotal, inUse: {runs, spend}} or null (loading or failed); state: "loading", "error" or "ready". A card whose cap is not in use (A-38) is hidden. */
    update(sums, state = "ready") {
      if (!sums) {
        const text = state === "error" ? "-" : "...";
        for (const c of [decisions, runs, spend]) {
          c.el.hidden = false;                 // while the data is not there nothing is hidden: the cards read as loading
          c.figure.textContent = text;
          c.unit.textContent = "";
          c.el.removeAttribute("title");
          c.el.setAttribute("aria-label", `${c.label}, ${state === "error" ? "not available" : "loading"}`);
          meter(c, 0);
          c.note.textContent = "";
        }
        return;
      }
      const use = sums.inUse || { runs: true, spend: true };
      runs.el.hidden = use.runs === false;
      spend.el.hidden = use.spend === false;
      decisions.figure.textContent = String(sums.decisions);
      decisions.unit.textContent = "waiting";
      decisions.el.title = `${sums.decisions} open decision${sums.decisions === 1 ? "" : "s"} waiting for you`;
      decisions.el.setAttribute("aria-label", `Open decisions ${sums.decisions} waiting for you`);
      runs.figure.textContent = String(sums.runs);
      runs.unit.textContent = `of ${sums.runsCap}`;
      runs.el.title = `of ${sums.runsCap} · ${format.METER_TIPS.runs}${sums.runsTotal ? ` All runs today: ${sums.runsTotal}` : ""}`;
      runs.el.setAttribute("aria-label", `${format.METER_WORDS.runs} ${sums.runs} of ${sums.runsCap}`);
      meter(runs, format.share(sums.runs, sums.runsCap));
      spend.figure.textContent = format.dollars(sums.usd);
      spend.unit.textContent = `of ${format.dollars(sums.usdCap)}`;
      const reserved = format.count(sums.usdReserved);
      const recorded = sums.usdRecorded === undefined ? sums.usd - reserved : sums.usdRecorded;
      const note = reserved > 0 ? format.spendNote(recorded, reserved) : "";
      spend.note.textContent = note;
      spend.el.title = `of ${format.dollars(sums.usdCap)} cap · ${format.METER_TIPS.spend}`;
      spend.el.setAttribute("aria-label", `${format.METER_WORDS.spend} ${format.dollars(sums.usd)} of ${format.dollars(sums.usdCap)} cap${note ? `, ${note}` : ""}`);
      const recordedShare = format.share(recorded, sums.usdCap);
      meter(spend, recordedShare, Math.min(format.share(reserved, sums.usdCap), 1 - recordedShare));
    },
  };
}
