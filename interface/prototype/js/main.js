// Boot, hash router, breadcrumbs, keyboard. Routes:
//   #/                          city
//   #/p/<project>               building
//   #/p/<project>/<floor>       floor (the Lobby is floor "planning")
//   #/control                   control room       #/p/<project>/planning/control   the same, entered from the Lobby door
import { load, store, project, floorDef } from "./data.js";
import { renderTop, renderTrack, closePanel, panelOpen, openTask, hideTip } from "./ui.js";
import * as city from "./city.js";
import * as building from "./building.js";
import * as floor from "./floor.js";
import * as control from "./control.js";

const view = document.getElementById("view");

function parse() {
  const parts = (location.hash || "#/").replace(/^#\/?/, "").split("/").filter(Boolean);
  if (parts[0] === "control") return { name: "control", from: null };
  if (parts[0] === "p" && project(parts[1])) {
    const p = project(parts[1]);
    if (parts[2] && parts[3] === "control") return { name: "control", from: p };
    if (parts[2] && store.ws.floors.some((f) => f.key === parts[2])) return { name: "floor", p, floor: parts[2] };
    return { name: "building", p };
  }
  return { name: "city" };
}

export const go = (hash) => { location.hash = hash; };

function parentOf(r) {
  if (r.name === "floor") return `#/p/${r.p.id}`;
  if (r.name === "building") return "#/";
  if (r.name === "control") return r.from ? `#/p/${r.from.id}/planning` : "#/";
  return null;
}

function draw() {
  hideTip();
  closePanel();
  const r = parse();
  const ctx = { go, taskPanel: (p, s) => openTask(p, s), project: r.p, floor: r.floor };
  const crumbs = [{ label: "City", href: "#/" }];
  if (r.name === "building" || r.name === "floor") crumbs.push({ label: r.p.name, href: `#/p/${r.p.id}` });
  if (r.name === "floor") crumbs.push({ label: floorDef(r.floor).label, href: `#/p/${r.p.id}/${r.floor}` });
  if (r.name === "control") {
    if (r.from) crumbs.push({ label: r.from.name, href: `#/p/${r.from.id}` }, { label: "Lobby", href: `#/p/${r.from.id}/planning` });
    crumbs.push({ label: "Control room" });
  }
  renderTop(crumbs, r.p || r.from || null);
  document.getElementById("controlbtn").style.display = r.name === "control" ? "none" : "";
  view.dataset.view = r.name;
  if (r.name === "city") city.render(view, ctx);
  else if (r.name === "building") building.render(view, ctx);
  else if (r.name === "floor") floor.render(view, ctx);
  else { control.render(view, ctx); renderTrack(null); }
}

addEventListener("hashchange", draw);
addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (panelOpen()) { closePanel(); return; }
  const up = parentOf(parse());
  if (up) go(up);
});

load().then(draw).catch((err) => {
  const el = document.getElementById("fatal");
  el.hidden = false;
  el.textContent = `Could not load the fake data: ${err.message}\nServe this folder over HTTP (python3 -m http.server 8787) instead of opening the file.`;
});
