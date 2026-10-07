# Interface prototype: 3D isometric

A throwaway prototype of the local interface, built to compare with a 2D prototype. It is a gamified
screen: projects are office buildings, each area agent is a floor, and a floor has a desk with documents
and an inbox. The scene is a Three.js orthographic isometric camera over geometry built in code (boxes,
cylinders, flat colours, one soft light). HTML cards, panels and labels sit over the canvas.

## Open it

```
cd interface; python3 -m http.server 8788
```

then open `http://127.0.0.1:8788/prototype/`. A page opened from `file://` will not load the modules.
A view can be opened directly: `#northwind-shop`, `#northwind-shop/marketing`, `#control`.

Use: click a building to enter it, click a floor to enter it, click the sheets, the tray, the cabinet, the
agent or the blue door (lobby) on a floor. Escape or the back button goes up one level. The bottom bar is the
task chain of one request; a step opens the floor of its agent.

## What is fake

Everything. The data is in `data/*.json`: two fictional projects ("northwind-shop", "tinykv-docs"), one
person ("Demo Person"), `.example` hosts. No model is called, no file of a real project is read, and every
button only shows a toast saying which operation it would call. Nothing is loaded from another host: the
renderer is the vendored `../vendor/three.module.js` (see `../vendor/README.md`), reached by an import map.

## What each view maps to in the runtime's operations

| View or part | Runtime operation it would call or read | Data file |
|--------------|------------------------------------------|-----------|
| City: buildings, badges, KPI "Open decisions" | `status` (`pending`, `requests`), `pending` | `projects.json`, `pending.json` |
| City: running mark, KPI "Agents working" | `status` (a task in state running) | `projects.json` |
| KPI "Runs today", "Spend today" | the day's runs and spend per agent (`autonomy.spend`, caps of `runtime.json`) | `projects.json` |
| Building: floors, mode plate, lights, use against caps | the `agents` of `runtime.json` (`enabled`, `mode`, `max_runs_per_day`, `max_usd_per_day`) and `set-mode` | `projects.json` |
| Floor: agent at its desk, task title and skill | `status` (task `key`, `skill`, `state`) | `projects.json` |
| Floor: desk with documents | `status` (`documents`: path, status) and the files under `docs/` | `documents.json`, `document-texts.json` |
| Floor: inbox cards | `pending` (kind `plan`, `question`, `review`, `effect`, `acceptance`) and `answer`, `approve`, `reject`, `release` | `pending.json` |
| Effect card: exact content and sha256 | `pending --id` (the payload) and `approve --id --sha256` | `pending.json` |
| Lobby: conversation, plan card | `say`, `pending --id` for the plan | `chat.json`, `pending.json` |
| Control room: skills with a band per model | `proof` (the bands of each skill in use) | `control.json` |
| Control room: costs | the day's runs per agent | `control.json` |
| Control room: connections | the requirement classes, secrets by name, and the image (doctor) | `control.json` |
| Bottom bar: the task chain | `progress` (`requests`: steps and states) | `chains.json` |

## Files

- `index.html`, `style.css`: the page and its look (white and light grey, one blue accent)
- `js/scene.js`: the 3D world (camera, buildings and their opening, floors, furniture, picking, animation)
- `js/main.js`: view state, breadcrumbs, KPI cards, labels that follow 3D points, pointer and keyboard
- `js/panels.js`: the side panels (agent, inbox cards, documents, conversation, control room)
- `js/dom.js`: a DOM builder that only uses `textContent`, so no text from the data is read as markup
- `data/*.json`: the fake data
