# Workbench local interface, 2D isometric prototype

A throwaway prototype of the gamified local interface, drawn as a flat isometric scene with inline SVG and CSS only.
No library, no build step, nothing loaded from another host, no model call. Every name and number is fake.

## Open it

```
cd interface/prototype; python3 -m http.server 8787
```

Then open `http://127.0.0.1:8787/`. It must be served over HTTP, because the page loads its data with `fetch`.
Routes (the address after `#`): `#/` city, `#/p/northwind-shop` building, `#/p/northwind-shop/marketing` floor,
`#/p/northwind-shop/planning` Lobby, `#/control` control room.

## How to use it

- City: click a building (or its row in the list) to enter it. Hover for a summary. Click the van to see the run it carries.
- Building: a cross-section, Lobby at the bottom. A lit window row is an enabled agent, a dark floor is a disabled one, a blue
  flicker is an agent working, a bubble with "!" is an agent waiting for you. Click a floor.
- Floor: the agent at its desk, the task on the wall board, the documents on the desk (click a sheet, or a row in the Desk
  card, to read the file as plain text), the inbox tray (click it to jump to the Inbox card). The Lobby has a conversation and
  a door to the control room.
- Buttons never act: they show a toast such as `would call approve(project='northwind-shop', pending_id=22, sha256='...')`.
- Escape closes the side panel, then goes back one level. The bar at the bottom is the task chain of one request; click a step.

## What is fake

Everything under `data/`: `workspace.json` (floors, modes, the daily cap), `projects.json` (agents, caps, usage, pending
decisions, the request and its tasks), `documents.json` (the artifacts and their text), `chat.json`, `control.json`
(bands, costs, connections). The effect card shows a real sha256 of the exact content next to it. The clock is fixed at the
time in `workspace.json`. Nothing is read from a project and nothing is written.

## What each view maps to in the runtime

| View | Operation (runtime/operations.py, runtime/ops.py) |
|------|---------------------------------------------------|
| KPI cards | `progress` (runs, spend against `daily_cost_cap_usd`), `pending` (open decisions) |
| City, building badges, "Waiting for you" | `status` (`requests`, `pending`) |
| Floor cards: mode, enabled, caps | `area_agents` of `runtime.json`, `set_mode`, `dispatch` |
| Desk documents | `status.documents`, the project's `docs/` files |
| Inbox buttons | `approve`, `reject`, `release`, `answer`, by pending kind (`plan`, `question`, `review`, `effect`, `acceptance`) |
| Conversation | `say` |
| Tracking bar | `status.requests[].tasks` |
| Control room: bands | `proof`; costs: the store's runs; connections: `scripts/doctor.py` and the secrets resolver (names only) |
