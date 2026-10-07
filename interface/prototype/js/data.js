// Loads the fake data once and derives the numbers the views share.
export const store = { ws: null, projects: [], documents: {}, chat: {}, control: null, now: null };

async function getJSON(name) {
  const res = await fetch(`data/${name}.json`);
  if (!res.ok) throw new Error(`data/${name}.json: ${res.status}`);
  return res.json();
}

export async function load() {
  const [ws, projects, documents, chat, control] = await Promise.all(
    ["workspace", "projects", "documents", "chat", "control"].map(getJSON));
  Object.assign(store, { ws, projects, documents, chat, control, now: new Date(ws.now) });
  return store;
}

export const project = (id) => store.projects.find((p) => p.id === id);
export const floorDef = (key) => store.ws.floors.find((f) => f.key === key);
export const agentOf = (p, key) => p.agents.find((a) => a.key === key);
export const pendingOf = (p, key) => p.pending.filter((x) => x.agent === key);
export const docsOf = (p, key) => (store.documents[p.id] || []).filter((d) => d.agent === key);

export function running(p) { return p.agents.some((a) => a.state === "working"); }

export function totals(p) {
  const list = p ? [p] : store.projects;
  return {
    open: list.reduce((n, q) => n + q.pending.length, 0),
    runs: list.reduce((n, q) => n + q.agents.reduce((m, a) => m + a.runs_today, 0), 0),
    runsCap: list.reduce((n, q) => n + q.agents.filter((a) => a.enabled).reduce((m, a) => m + a.max_runs_per_day, 0), 0),
    usd: list.reduce((n, q) => n + q.agents.reduce((m, a) => m + a.usd_today, 0), 0),
    cap: p ? p.agents.filter((a) => a.enabled).reduce((m, a) => m + a.max_usd_per_day, 0) : store.ws.daily_cost_cap_usd,
    working: list.reduce((n, q) => n + q.agents.filter((a) => a.state === "working").length, 0),
  };
}

export function relTime(iso) {
  const mins = Math.round((store.now - new Date(iso)) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const h = Math.round(mins / 60);
  if (h < 24) return `${h} h ago`;
  return `${Math.round(h / 24)} d ago`;
}

export const money = (n) => `$${n.toFixed(2)}`;

export function bandOf(skill, model = "reference") {
  const row = store.control.skills.find((s) => s.skill === skill);
  return row ? row.models[model] : null;
}
