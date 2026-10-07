// A tiny DOM builder. Text always goes in as textContent, so nothing from the data is ever read as markup.
export function h(tag, props = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "style") el.setAttribute("style", v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
export const $ = (s, root = document) => root.querySelector(s);
export function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }

let toastTimer;
export function toast(text) {
  const t = $("#toast");
  t.textContent = text; t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 3800);
}
export const money = (n) => "$" + Number(n).toFixed(2);
export function fmtTime(iso) { return iso.replace("T", " ").slice(0, 16); }
export function ago(iso, nowIso) {
  const m = Math.max(0, Math.round((Date.parse(nowIso) - Date.parse(iso)) / 60000));
  if (m < 60) return m + " min ago";
  const hh = Math.round(m / 60);
  return hh < 48 ? hh + " h ago" : Math.round(hh / 24) + " d ago";
}
export const MODE_CLASS = { stopped: "", supervised: "line", milestones: "blue", autonomous: "solid", "autonomous-with-policy": "navy" };
export const STATE_LABEL = { working: "working", waiting: "waiting for you", idle: "idle", off: "off", running: "running", ready: "ready", done: "done", failed: "failed", blocked: "blocked" };
export function meter(used, cap) {
  const pct = cap > 0 ? Math.min(100, (used / cap) * 100) : 0;
  return h("div", { class: "meter" + (pct >= 80 ? " warn" : "") }, h("i", { style: `width:${pct}%` }));
}
