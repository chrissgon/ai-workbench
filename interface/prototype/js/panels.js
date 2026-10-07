// The side panels. Every function returns DOM nodes; `ctx` is main.js's small interface (data, state, go, ...).
import { h, toast, money, fmtTime, ago, meter, MODE_CLASS, STATE_LABEL } from "./dom.js";

export const AGENT_ORDER = ["planning", "business", "brand", "design", "engineering", "marketing"];
const AREA = { planning: "Lobby", business: "Business", brand: "Brand", design: "Design", engineering: "Engineering", marketing: "Marketing" };
export const areaName = (id) => AREA[id] || id;

export function statePill(state) {
  const cls = { working: "blue", running: "blue", waiting: "amber", done: "green", failed: "red" }[state] || "";
  return h("span", { class: "chip " + cls }, STATE_LABEL[state] || state);
}
export function modePlate(mode) { return h("span", { class: "chip " + (MODE_CLASS[mode] || "") }, mode); }

// ---------------------------------------------------------------- a pending decision as a card
export function pendingCard(p, ctx) {
  const card = h("article", { class: "pcard k-" + p.kind });
  card.append(
    h("div", { class: "row", style: "border:0;padding:0;margin:0" },
      h("span", { class: "chip " + ({ effect: "red", question: "amber", review: "blue", acceptance: "green", plan: "blue" }[p.kind] || "") }, p.kind),
      h("span", { class: "muted s" }, `#${p.id} - ${areaName(p.agent)} - ${ago(p.created_at, ctx.data.projects.now)}`)),
    h("h4", {}, p.title),
    h("div", { class: "body-text" }, p.body));
  if (p.plan) {
    card.append(
      h("table", { class: "plan-table" }, p.plan.tasks.map((t, i) => h("tr", {}, h("td", {}, String(i + 1)), h("td", {}, t.title), h("td", { class: "muted" }, t.skill)))),
      h("div", { class: "muted s" }, "Plan hash"), h("code", { class: "hash" }, p.plan.hash));
  }
  if (p.effect) {
    card.append(
      h("div", { class: "muted s", style: "margin-top:8px" }, `Exact content of the ${p.effect.kind} (what will be sent):`),
      h("pre", { class: "text" }, p.effect.content),
      h("div", { class: "muted s" }, "sha256 of that content"), h("code", { class: "hash" }, p.effect.sha256),
      h("div", { class: "muted s", style: "margin-top:6px" }, "An effect is approved with its hash. Nothing is sent before that."));
  }
  let input = null;
  if (p.actions.includes("answer")) {
    input = h("input", { type: "text", placeholder: p.kind === "question" ? "Your answer (the recommended one is marked)" : "Comments (optional)" });
    card.append(h("div", { style: "margin-top:8px" }, input));
  }
  const bar = h("div", { class: "actions" });
  const label = { approve: p.kind === "effect" ? "Approve this exact content" : "Approve", reject: "Reject", answer: "Send answer", release: "Release as draft" };
  for (const a of p.actions) {
    bar.append(h("button", {
      class: "btn" + (a === "approve" ? " primary" : a === "reject" ? " danger" : ""), type: "button",
      onclick: () => {
        let op = p.operation[a] || a;
        if (a === "answer" && input) op = op.replace(/<[^>]+>/, JSON.stringify(input.value || "..."));
        if (a === "approve" && p.effect) op = op.replace("<hash>", p.effect.sha256.slice(0, 12) + "...");
        toast("would call " + op);
      },
    }, label[a] || a));
  }
  card.append(bar);
  return card;
}

// ---------------------------------------------------------------- floor panel
export function agentTab(p, a, ctx) {
  const root = h("div");
  root.append(
    h("div", { class: "sect" },
      h("div", { class: "row", style: "border:0;padding:0" }, h("span", { class: "dot " + a.state }), h("b", {}, statePill(a.state)), modePlate(a.mode),
        h("span", { class: "chip " + (a.enabled ? "green" : "") }, a.enabled ? "lights on" : "lights off"))),
    h("div", { class: "sect" }, h("h3", {}, "Current task"),
      a.task
        ? h("div", { class: "row" }, h("span", { class: "dot " + a.task.state }), h("div", { class: "grow" }, h("div", { class: "t" }, a.task.title),
            h("div", { class: "s" }, `task #${a.task.id} - skill `, h("span", { class: "mono" }, a.task.skill))), statePill(a.task.state))
        : h("div", { class: "muted" }, a.enabled ? "Nothing is running. The agent is idle." : "This agent is off: its mode is stopped, so no task starts.")),
    h("div", { class: "sect" }, h("h3", {}, "Use today against its caps"),
      h("div", { class: "s" }, `Runs: ${a.used_today.runs} of ${a.max_runs_per_day}`), meter(a.used_today.runs, a.max_runs_per_day),
      h("div", { class: "s" }, `Spend: ${money(a.used_today.usd)} of ${money(a.max_usd_per_day)}`), meter(a.used_today.usd, a.max_usd_per_day)),
    h("div", { class: "sect" }, h("h3", {}, "Skills this agent runs"), h("div", {}, a.skills.map((s) => h("span", { class: "chip mono", style: "margin:0 4px 4px 0" }, s)))),
    h("div", { class: "sect" }, h("h3", {}, "Mode"),
      h("div", { class: "muted" }, "Set with the operation set-mode. The page only shows it here."),
      h("div", { class: "actions" }, ["stopped", "supervised", "milestones", "autonomous"].map((m) =>
        h("button", { class: "btn", type: "button", onclick: () => toast(`would call set-mode ${a.id} ${m}`) }, m)))));
  if (a.id === "planning") root.append(h("div", { class: "sect" }, h("button", { class: "btn primary", type: "button", onclick: () => ctx.go("control") }, "Open the control room (door at the back of the lobby)")));
  return root;
}

export function inboxTab(p, a, ctx) {
  const items = ctx.pendingFor(p.id, a.id);
  if (!items.length) return h("div", { class: "muted" }, "The inbox on this desk is empty. Nothing waits for you here.");
  return h("div", {}, items.map((x) => pendingCard(x, ctx)));
}

export function docsTab(p, a, ctx) {
  const st = ctx.state, all = ctx.data.documents[p.id] || [];
  if (st.doc) {
    const d = all.find((x) => x.path === st.doc);
    const text = ctx.data["document-texts"][st.doc];
    return h("div", {},
      h("button", { class: "btn", type: "button", onclick: () => { st.doc = null; ctx.render(); } }, "Back to the list"),
      h("h3", { class: "mono", style: "margin:12px 0 2px;font-size:13px" }, st.doc),
      h("div", { class: "muted s" }, d ? `owner ${d.owner} - modified ${fmtTime(d.modified)}` : ""),
      h("pre", { class: "text" }, text ?? "(the prototype has no text for this file)"),
      h("div", { class: "muted s" }, "Shown as plain text. Never rendered as markup."));
  }
  const scoped = st.docScope !== "all" && a.id !== "planning";
  const list = all.filter((d) => !scoped || d.agent === a.id).sort((x, y) => y.modified.localeCompare(x.modified));
  return h("div", {},
    a.id !== "planning" && h("div", { class: "actions", style: "margin:0 0 10px" },
      h("button", { class: "btn" + (scoped ? " primary" : ""), type: "button", onclick: () => { st.docScope = "floor"; ctx.render(); } }, "This floor"),
      h("button", { class: "btn" + (!scoped ? " primary" : ""), type: "button", onclick: () => { st.docScope = "all"; ctx.render(); } }, "Whole project")),
    list.length ? list.map((d) => h("div", { class: "row click", onclick: () => { st.doc = d.path; ctx.render(); } },
      h("div", { class: "grow" }, h("div", { class: "t mono", style: "font-size:12px" }, d.path), h("div", { class: "s" }, `${d.owner} - ${fmtTime(d.modified)}`)),
      h("span", { class: "chip" }, areaName(d.agent))))
      : h("div", { class: "muted" }, "No documents under docs/ for this floor yet."));
}

export function chatTab(p, ctx) {
  const msgs = ctx.chat(p.id);
  const log = h("div", { class: "msgs" });
  const draw = () => {
    log.replaceChildren(...msgs.map((m) => {
      const bubble = h("div", { class: "msg " + m.from }, h("div", { class: "who" }, (m.from === "person" ? "You" : "Planning agent") + " - " + ago(m.at, ctx.data.projects.now)), m.text);
      const out = h("div", { style: "display:flex;flex-direction:column;gap:6px" }, bubble);
      if (m.pending_id) { const pe = ctx.data.pending.pending.find((x) => x.id === m.pending_id); if (pe) out.append(pendingCard(pe, ctx)); }
      return out;
    }));
  };
  draw();
  const input = h("input", { type: "text", placeholder: "Say what you want, or answer a question" });
  const send = () => {
    const v = input.value.trim(); if (!v) return;
    toast("would call say --text " + JSON.stringify(v));
    msgs.push({ from: "person", at: ctx.data.projects.now, text: v }); input.value = ""; draw();
  };
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
  return h("div", {}, log, h("div", { class: "sendrow" }, input, h("button", { class: "btn primary", type: "button", onclick: send }, "Send")));
}

// ---------------------------------------------------------------- building panel
export function buildingPanel(p, ctx) {
  const pend = ctx.pendingFor(p.id);
  const root = h("div");
  root.append(
    h("dl", { class: "kv sect" },
      h("dt", {}, "Repository"), h("dd", { class: "mono" }, p.repo),
      h("dt", {}, "Owner"), h("dd", {}, p.owner),
      h("dt", {}, "Request"), h("dd", {}, `#${p.request_id} - ${ctx.data.chains[p.id].title}`),
      h("dt", {}, "Waiting for you"), h("dd", {}, `${pend.length} decision${pend.length === 1 ? "" : "s"}`),
      h("dt", {}, "Running now"), h("dd", {}, p.running_task_id ? `task #${p.running_task_id}` : "nothing")),
    h("div", { class: "sect" }, h("h3", {}, "Floors, top to bottom"),
      [...p.agents].reverse().map((a) => {
        const n = ctx.pendingFor(p.id, a.id).length;
        return h("div", { class: "row click", onclick: () => ctx.go("floor", { pid: p.id, agent: a.id }) },
          h("span", { class: "dot " + a.state }),
          h("div", { class: "grow" }, h("div", { class: "t" }, areaName(a.id)), h("div", { class: "s" }, `${a.used_today.runs}/${a.max_runs_per_day} runs - ${money(a.used_today.usd)} of ${money(a.max_usd_per_day)}`)),
          n > 0 && h("span", { class: "badge" }, String(n)), modePlate(a.mode));
      })));
  return root;
}

// ---------------------------------------------------------------- control room
const PALETTE = ["#2d6cff", "#7fa5ff", "#b9ccf5", "#1f2f55", "#9aa5b5", "#d3d9e2"];
export function controlPanel(ctx) {
  const c = ctx.data.control, st = ctx.state, tab = st.ctlTab || "skills";
  const root = h("div");
  if (tab === "skills") {
    const q = (st.skillFilter || "").toLowerCase();
    const filter = h("input", { type: "text", placeholder: "Filter skills", value: st.skillFilter || "" });
    filter.addEventListener("input", () => { st.skillFilter = filter.value; fill(); });
    const tbody = h("tbody");
    const fill = () => {
      const f = (st.skillFilter || "").toLowerCase();
      tbody.replaceChildren(...c.skills.filter((s) => s.skill.includes(f)).map((s) => h("tr", {},
        h("td", { class: "mono" }, s.skill), ...["reference", "floor"].map((m) => h("td", { title: s[m].cause }, bandChip(s[m].band), h("span", { class: "muted s", style: "margin-left:6px" }, s[m].score ? s[m].score.toFixed(2) : ""))))));
    };
    fill();
    root.append(h("div", { class: "muted s", style: "margin-bottom:8px" }, "The band of each skill on each model, computed from recorded evidence. The score is the pessimistic score."),
      filter, h("table", { class: "t", style: "margin-top:8px" }, h("thead", {}, h("tr", {}, h("th", {}, "Skill"), ...c.models.map((m) => h("th", {}, m.label)))), tbody));
  } else if (tab === "costs") {
    const days = c.costs.days, agents = c.costs.agents;
    const totals = days.map((_, i) => agents.reduce((s, a) => s + c.costs.usd[a][i], 0));
    const max = Math.max(...totals) * 1.15;
    root.append(h("div", { class: "muted s", style: "margin-bottom:6px" }, "Spend by day and agent (USD). The daily cap of the machine is " + money(ctx.data.projects.daily_cap_usd) + "."),
      h("div", { class: "bars" }, days.map((d, i) => h("div", { class: "col", title: d },
        agents.map((a, k) => h("div", { class: "seg", title: `${areaName(a)} ${money(c.costs.usd[a][i])}`, style: `height:${(c.costs.usd[a][i] / max) * 100}%;background:${PALETTE[k % PALETTE.length]}` })),
        h("div", { class: "tot", style: `bottom:calc(${(totals[i] / max) * 100}% + 2px)` }, money(totals[i]))))),
      h("div", { class: "bars-x" }, days.map((d) => h("span", {}, d.slice(5)))),
      h("div", { class: "legend" }, agents.map((a, k) => h("span", {}, h("i", { style: `background:${PALETTE[k % PALETTE.length]}` }), areaName(a)))),
      h("div", { class: "sect", style: "margin-top:16px" }, h("h3", {}, "Today by agent"), h("table", { class: "t" }, h("thead", {}, h("tr", {}, h("th", {}, "Agent"), h("th", {}, "Today"), h("th", {}, "7 days"))),
        h("tbody", {}, agents.map((a) => h("tr", {}, h("td", {}, areaName(a)), h("td", {}, money(c.costs.usd[a][days.length - 1])), h("td", {}, money(c.costs.usd[a].reduce((x, y) => x + y, 0)))))))));
  } else {
    const cn = c.connections;
    root.append(
      h("div", { class: "sect" }, h("h3", {}, "Container image"), h("div", { class: "row" }, h("span", { class: "dot " + (cn.image.present ? "done" : "failed") }),
        h("div", { class: "grow" }, h("div", { class: "t mono" }, cn.image.name), h("div", { class: "s" }, cn.image.note)), h("span", { class: "chip " + (cn.image.present ? "green" : "red") }, cn.image.present ? "present" : "missing"))),
      h("div", { class: "sect" }, h("h3", {}, "Requirement classes"), cn.classes.map((k) => h("div", { class: "row" }, h("span", { class: "dot " + (k.found ? "done" : "failed") }),
        h("div", { class: "grow" }, h("div", { class: "t mono" }, k.class), h("div", { class: "s" }, k.provider ? "provider: " + k.provider : "no provider found")), h("span", { class: "chip " + (k.found ? "green" : "red") }, k.found ? "found" : "missing")))),
      h("div", { class: "sect" }, h("h3", {}, "Secrets, by name (a value is never shown)"), cn.secrets.map((k) => h("div", { class: "row" }, h("span", { class: "dot " + (k.found ? "done" : "failed") }),
        h("div", { class: "grow" }, h("div", { class: "t mono" }, k.name), h("div", { class: "s" }, k.purpose)), h("span", { class: "chip " + (k.found ? "green" : "red") }, k.found ? "found" : "missing")))));
  }
  return root;
}
function bandChip(b) { return h("span", { class: "chip " + ({ reliable: "green", watch: "amber", "needs a test": "red" }[b] || "") }, b); }
