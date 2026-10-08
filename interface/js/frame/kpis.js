// F-3 the three KPI cards: open decisions, runs today and spend today, each labelled by what it counts. The meter is
// a display division (used over cap), hidden from the accessibility tree: the number is in the text.

import { h } from "../dom.js";
import * as format from "../format.js";
import { icon } from "./icons.js";

function card(label, iconName, tone, withMeter) {
  const figure = h("strong", { class: "wb-kpi-figure", text: "..." });
  const unit = h("span", { class: "wb-kpi-unit", text: "" });
  const meterFill = h("span", { class: "wb-meter-fill" });
  const body = [h("span", { class: "wb-kpi-label", text: label }), h("div", { class: "wb-kpi-row" }, figure, unit)];
  if (withMeter) body.push(h("span", { class: "wb-meter", "aria-hidden": "true" }, meterFill));
  const el = h("div", { class: "pui-card wb-kpi", role: "group", "aria-label": `${label}, loading` },
    h("span", { class: `wb-kpi-tile pui-soft pui-${tone}` }, icon(iconName, 16)),
    h("div", { class: "wb-kpi-body" }, body));
  return { el, figure, unit, meterFill, label };
}

export function createKpis() {
  const decisions = card("Open decisions", "inbox", "warn", false);
  const runs = card("Runs today", "activity", "theme", true);
  const spend = card("Spend today", "credit-card", "theme", true);
  const el = h("div", { class: "wb-kpis" }, decisions.el, runs.el, spend.el);

  function meter(c, fraction) {
    c.meterFill.style.setProperty("--wb-share", `${Math.round(fraction * 100)}%`);
    c.meterFill.classList.toggle("is-full", fraction >= 1);
  }

  return {
    el,
    /** sums: {decisions, runs, runsCap, usd, usdCap} or null (loading or failed); state: "loading", "error" or "ready". */
    update(sums, state = "ready") {
      if (!sums) {
        const text = state === "error" ? "-" : "...";
        for (const c of [decisions, runs, spend]) {
          c.figure.textContent = text;
          c.unit.textContent = "";
          c.el.removeAttribute("title");
          c.el.setAttribute("aria-label", `${c.label}, ${state === "error" ? "not available" : "loading"}`);
          meter(c, 0);
        }
        return;
      }
      decisions.figure.textContent = String(sums.decisions);
      decisions.unit.textContent = "waiting";
      decisions.el.title = "waiting for you";
      decisions.el.setAttribute("aria-label", `Open decisions ${sums.decisions} waiting for you`);
      runs.figure.textContent = String(sums.runs);
      runs.unit.textContent = `of ${sums.runsCap}`;
      runs.el.title = `of ${sums.runsCap} · reference model`;
      runs.el.setAttribute("aria-label", `Runs today ${sums.runs} of ${sums.runsCap}, reference model`);
      meter(runs, format.share(sums.runs, sums.runsCap));
      spend.figure.textContent = format.dollars(sums.usd);
      spend.unit.textContent = `of ${format.dollars(sums.usdCap)}`;
      spend.el.title = `of ${format.dollars(sums.usdCap)} cap · floor model dollars`;
      spend.el.setAttribute("aria-label", `Spend today ${format.dollars(sums.usd)} of ${format.dollars(sums.usdCap)} cap, floor model dollars`);
      meter(spend, format.share(sums.usd, sums.usdCap));
    },
  };
}
