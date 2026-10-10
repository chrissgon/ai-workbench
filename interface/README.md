# The local interface

The folder `runtime/service.py` serves: the static files of the page a person uses to work with the task runtime on
their own machine. It holds no rule of the work. Which words a pending decision takes, what a state leads to and what a
hash must equal are decided by the operations layer (`runtime/ops.py`) and the store; the page shows what an operation
returned and sends what the person typed or clicked.

## What is here

| Path | What |
|---|---|
| `index.html`, `style.css`, `favicon.svg` | The one page (its title is "openhora"), its rules and its icon, the simplified owl mark (the service also answers `/favicon.ico`, which browsers ask for by default, with the same file). No inline script, no inline style: every rule is in `style.css`, every script is a module. `style.css` derives the page's own tokens (`--wb-raised`, `--wb-ground`, `--wb-elev`, ...) from the library's, with no colour literal but one: the brand pair (see "The brand" below). |
| `icons/` | One clean SVG file per icon (from the Lucide set), drawn by a CSS mask in the colour of the text. |
| `brand/`, `js/brand.js` | `brand/openhora-mark.svg` is the full mark, a drawing with no script, link or embedded data. `js/brand.js` is the one module that names the file: `markImage(size)` builds an `<img>` of it with the alt text "openhora", sized by its own attributes (the page's policy forbids a style attribute), never from a markup string and never a `data:` address. The token prompt shows it at 48 px above the field with the text "openhora" beside it, and the frame's top bar at 20 px, between Back and the breadcrumbs. |
| `js/main.js` | The page: the token prompt, then the shared frame with the screen the hash names (`#/city` is the City, always; `#/` is the entry: the City, or, when the service holds exactly one project, that project's Building, by a rule that runs once, on the first read of the projects, and replaces the hash, so a reload on `#/city` stays on the City; `#/p/<id>` is the Building, `#/p/<id>/floor/<agent>` the Floor, `#/p/<id>/lobby` the Lobby; the Control room `#/p/<id>/control`), and the reload: everything the page shows is read again (`js/data.js`, then each screen's own reads, given a stamp that moves) when the watcher says the store changed, after any write the page sent, and on return to a visible tab (see `js/watch.js`). |
| `js/watch.js` | The page's liveness, with no knowledge of the screens: `createWatcher` reads the change signal (`GET /versions`, one request for every project) every second while the document is visible, and asks for a reload when a number moved, once when the signal could not be read and once when it can again (a failed read is retried after 10 s), after 30 seconds with no reload as a safety net, and once on return to a visible tab; it keeps no timer and reads nothing while the document is hidden. It keeps time and reads only through what it is given, so a test drives it with a fake clock (`runtime/tests/test_interface_live.py`). `coalesce` makes the reload one at a time: a request made during a reload makes one more after it. |
| `js/router.js`, `js/format.js`, `js/model.js`, `js/floor-model.js`, `js/world-model.js` | Pure functions: the hash forms (a document of the desk is `/desk/<percent-encoded path>`; a request's line in the Lobby is `/lobby/conversation/request/<n>`, the word `request` being a segment because a bare number after the tab is a decision; `entryHash` and `isHomeBuilding` are the one-project rules `main.js` applies), the display words and numbers, what the City shows worked out from the service's bodies (floors, windows, waiting rows, the tracking bar), and what the Building and the Floor show (each floor's state, plate and list row, the current task, the run block, the desk rows, the resolved lines). Tested under Node. |
| `js/data.js` | What the City reads: `projects`, then `status` and `agents` of each accepted project, and the running task's `task` body (a reload reads it again whatever its state; without `force` it is reused while the state is the same), and `versionKey`, the change signal of every project as one string. Reads only. |
| `js/api.js` | The client of the service: one function per route of `ROUTES` in `runtime/service.py`, named after the operation. `pollJob` asks for a running job every second (at least 200 ms) and asks nothing while the document is hidden: the first poll after the tab is visible again happens at once, then the period continues; an abort rejects at once, paused or not. `onWrite` registers the one function called after the service answered any POST, whatever it answered (the page reloads at once); `version` and `versions` read the change signal. `tokenFile` reads `GET /token-file` with no bearer header (A-39), so the prompt can show the command that reads the token file before the page has a token. |
| `js/markdown.js` | The one Markdown renderer: headings 1 to 4, paragraphs, bold, italic, inline and fenced code, lists, quotes, tables, rules and line breaks, built as DOM nodes. Raw HTML, comments and entities stay text; an image is its alt text and address as text; a link is its text and its address as text unless the address is a route of this page (`#/...`), then a plain anchor, so a click never leaves the page; the only attributes it sets are `class` and that `href`; it tries at most 500 bracket pairs in a paragraph. A document over 200,000 characters renders its first part and shows the rest as one plain block. Called by `js/markdown-view.js` (the rendered view with the "Plain text" toggle, used by the viewer and by both plan cards, one session choice for all), by the cards (question, acceptance and review bodies) and by the conversation (the planning agent's replies; the person's messages stay plain text). |
| `js/token.js`, `js/dom.js` | The token for this session; building elements (strings become text, a style or an event attribute is refused). |
| `js/mode.js` | The light/dark preference (D-2): the one module that sets the library's own attribute `data-pui-mode="light"` or `"dark"` on `<html>` (or removes it: the system decides) and keeps the choice under the one `localStorage` key `openhora-mode`, the exception to the storage rule below. `main.js` applies it before the first draw; the control that sets it is provisional, three chips (Light, Dark, System, the default) at the foot of the project switcher's listbox, until the design round decides its place. The scene reads its palette again when the attribute changes (`watchScheme` in `js/scene/palette.js`, which also listens to the system's scheme). The library's own `js/mode.js` keeps a cookie and is not loaded. The preference is applied when `main.js` runs, so a first paint in the system's scheme is possible before it applies. |
| `js/frame/` | The shared frame of every scene screen: header (back, breadcrumbs, project switcher), KPI cards, waiting list, tracking bar, panel shell, `drawer.js` (the phone's bottom sheet: see "The phone layout"), sheet (a phone's lists, a dialog), icons, `escape.js` (the order of the one Escape handler: a field, a dialog, a document, a menu, a selection, then up one level), `origin.js` (the tab and the decision an open document was opened from, else the Desk: the viewer's "Close", a phone's dialog and Escape all go to the hash it names), `command.js` (the terminal-command component: the sentence, the command the service gave in a code block that wraps whole, and a Copy button that uses the clipboard and, where the browser refuses it, selects the text; `isCommand` tells a command from a sentence; a spec may also give the Copy button its own accessible name, for a path). The command of a refusal is the `next` of the 412 body (`ApiError.next`), and the credential's commands are the fields `status.held[].commands` (`{name, command}`, `command` null when no username is registered): the page never reads a command out of a sentence (A-22). |
| `js/scene/` | The scene engine: `engine.js` (one renderer, orthographic camera, picking, labels, tokens read at run time, the one world of the City, the Building, the Floor and the Lobby and its targets, the work-order tag moving), `loop.js` (the render scheduler: a frame only when asked, at most 30 a second while an ambient animation runs, none while hidden), `palette.js`, `kit.js`, `props.js`, `labels.js`, `cull.js`, `fit.js` (the fitted camera), `rig.js` (the isometric camera and a scene's bounds, shared by the engine and the picking test), `prototype-motion.js` (the prototype's own motion functions: the approach by frame, the working pose, the beacon), `camera.js` (the person's zoom and pan with limits, the pointer's mapping), `look.js` (the window colour, which outline lines show, what a `show` must do), `pick.js` (what the pointer is on: the meshes of the pickable objects, never a line), `outline.js` (the outline of a hovered object: the edges of its outer shell parts only), `pointer.js`, `tween.js` (the camera's goal followed each frame, retargetable), `world.js` and `tower.js` (the one persistent world: every building with its floors, each floor already holding its room; a screen only sets targets on it: the open building, the floor, the selection), and the builders it uses: `city.js` (ground, streets, the beacon), `building.js` (the room of one floor), with `furniture.js` (desk, chair, tray, sheet, table, cabinet, lamp, bookshelf, door), `figure.js` (the agent in its three poses and the typing motion) and `plates.js` (the compact floor card, the board, tag and door labels). |
| `js/views/` | One module per screen: `token-prompt.js`, `city.js` (the City, with the "Add a project" and "Leave a project" controls of `city-projects.js` and its pure part `city-projects-model.js`: A-24), `lobby.js` with `lobby-*.js` (the Lobby: the conversation, the request form, the composer, the tab list, the cancel dialog, the room; `lobby-inbox.js`, `lobby-desk.js` and `lobby-agent.js` hand the Floor's Inbox, Desk and viewer, and Agent tab the planning agent: its decisions, every document of the project (the Lobby is the project's room; the Desk table has the agent of each row as a column after the owner skill, "—" when none) and its tasks; `lobby.js` itself builds the Floor's Tasks tab for the planning agent, whose tasks are those with `agent` "planning" or none), `building.js` (the Building: the cutaway, the floors list, the project's facts), `floor.js` (the Floor: the room and the panel with the tabs Agent, Inbox, Desk and Tasks) and the Control room: `control.js` (the panel, the tabs, the reads, the server-room scene), `control-skills.js`, `control-costs.js` and `control-connections.js` (one per tab), `control-scene.js` (the server-room builder), `control-model.js` (the pure part: chips, filters, the chart, the cost words and the scene's model, tested under Node) and `control-parts.js` (the loading line, the failed-read notice, the empty block); `placeholder.js` stays as the fallback of an unknown screen. |
| `js/floor/` | The Floor's panel and the decision cards, the only files that send a write: `cards.js` (effect, acceptance, question, review and plan cards, the request line and the cancel dialog), `inbox.js`, `agent-tab.js` (Stop agent and Supervise, the held reason of the current task with the commands the service gave, the current task and the other tasks with the actions of a Tasks-tab row, hand a file over), `task-actions.js` (the one source of those actions in both tabs: Retry, with the sentence the runtime stored for a blocked task beside it, "Open in the Inbox", "Go ahead" and "Drop the after"), `hand-file.js` (the size and name checks and the base64 of a file handed to a task), `desk-tab.js` (the size cell carries the kind: text, Markdown, image or other), `tasks-tab.js` with `tasks-model.js` (the Tasks tab: every task of the agent in groups by state, with Retry on a failed or blocked one, "Open in the Inbox" on one that waits for you, "Go ahead" and "Drop the after" and the reason on a planned one that waits for another task or request, the paths a done task returned and its runs on expand; it reads `task` for its first twelve rows and for a row when expanded, and sends only Retry and the go-aheads, through the client it is handed), `run-block.js` (the run block the Agent tab and the Tasks tab share), `viewer.js` (a document: Markdown drawn by `js/markdown.js` through `js/markdown-view.js`, with a "Plain text" toggle, or the text in a wrapped `pre`; an image as an `<img>` from a `blob:` URL of the bytes `artifactRaw` fetched with the bearer header; a type the page cannot show as one sentence with the path to copy), `widgets.js`, and `actions.js`, the one object that names every write of the client; the cards and the tab are handed it, so a test can give them a fake client. |
| `js/cards/` | The decision cards the Lobby draws under a message: `plan.js` (the plan card: the table of tasks, what the plan waits for, the limits, the whole hash, "Approve this plan" sending exactly the hash it shows and the keys ticked "Go ahead"), `plan-waits.js` (the block that lists `payload.waits`, `missing` and `cycles` and holds the "Go ahead" boxes; the Floor's plan card draws the same block) and `plan-rows.js` (what the card shows, worked out from the decision's payload). |
| `js/three.js` | The one place the 3D library is imported from (a relative re-export); the scene uses it. |
| `vendor/three/`, `vendor/<library>/` | The two third-party libraries, copied unchanged, each folder with a README that records the package, the exact version, the licence and the sha256 of every file. |
| `vendor/fonts/` | The brand typefaces (C-13): Inter 400 and 600 for text, JetBrains Mono 400 and 700 for code, hashes and commands, Space Grotesk 500 for the wordmark on the token prompt only, as woff2 latin subsets (about 105 KB), with their SIL OFL 1.1 licence texts (`LICENSE-<family>.txt`) and a README that records the sha256 of every file. `style.css` declares them with `@font-face` (`font-display: swap`) by relative paths and puts them first in the text and code stacks; `index.html` preloads nothing. |

## The brand

The page's primary colour is the library's one token `--pui-theme`, set once at `:root` in `style.css` to the brand pair `light-dark(#6B4429, #C99A6E)` (a brown on a light ground, a lighter brown on a dark one); no other token of the library is set by the page. Everything that is "the theme" reads that token and nothing else: the tints derived from it (`--wb-ink-theme`, `--wb-tint-selected`, `--wb-tint-reserved`), the meters, the focus rings, the running dot, the outline buttons, and the scene, which reads the token through a probe element when it is built and when the colour scheme changes (`js/scene/palette.js`; the outline of a hovered or selected object copies `palette.T.theme`, so no scene file holds a colour of its own). To change the primary, change that one line. It is the only colour literal in the stylesheet, and `runtime/tests/test_interface_files.py` keeps it so.

The "working" light of a floor's windows is the library's amber (`--pui-warn`), not the brand brown. On a dark ground the two were looked at side by side in the served page (a working floor beside the selected floor's outline, and the amber dot of a waiting floor beside the brown dot of a running one): the brown `#C99A6E` and the amber `#F59E0B` are about 14 apart in CIEDE2000 and read as two colours at the size of a window, so the amber stays; the identity's alternative, a warm white `#FFE8C2` for the working light, is not used.

The favicon (`favicon.svg`) and the mark (`brand/openhora-mark.svg`) are the identity's drawings with their provenance metadata block and the namespace declaration that only that block used removed, and nothing else changed; a test records the hash of each file and the first path of each drawing, so a new drawing changes those two lines on purpose.

## How to open it

```
python3 runtime/service.py --project <dir>
```

`--project` repeats: the service holds every project it is started with, one building each, and the set is fixed until it is started again. The page does not add or remove one and never opens a folder: the City's "Add a project" takes the folder's path and shows the line that starts the service again with it, with Copy (the head of the line is the service's own start line, `connections.service.start`; the folders of the other projects are the `folder` of each entry of `GET /projects`, which the service knows for every project, accepted or not (A-34)), and, when the person says the folder has no configuration, three numbered steps: the `core-project-init` line (with the autonomy they choose; it makes `state.md` only), then writing `docs/workbench/runtime.json` by hand (the service does not start without it), then the restart line; a path must be absolute (`~/` is refused, quoted it would name a folder called `~`), and a project's name never goes into a line except with every character outside letters, digits, space, `.`, `_` and `-` replaced; "Leave a project" shows the line without that project. Both are in the City's top right on a desktop (the list card is clipped until it has the keyboard focus) and the first part of the sheet on a phone.

It prints one JSON line with the page's `url` and the path of the `token_file`. Open the url in a browser. The prompt reads
`GET /token-file` (the one request the page sends without a token: no bearer header, and it never carries the token) and shows
two steps: "1 · Run this in a terminal", the command the service built for the browser's system, with the system's name beside
it and Copy ("Copied" for two seconds), and "2 · Paste the token", the field and Continue. The command puts the token on the
clipboard (`pbcopy` on macOS, `Set-Clipboard` on Windows) or prints it in the terminal (`cat` on Linux); the sentence under it
says so, and the token itself is never shown on the page. The page picks one of the strings the service gave and builds no command
and joins no path into one (`js/views/token-prompt.js` spells none); a path the service cannot write safely as a command, an older
service (404), an error and a system the page does not tell apart leave the earlier sentence ("the file whose path the service printed
when it started") and the one field. Or open the token file in an editor, and paste its one line into the page. The page asks for it once per browser session: it
is kept in memory and in the tab's `sessionStorage` (which the browser drops when the tab closes), and the button "Forget
the token" clears both. Where the browser can mask a text field by CSS the field is such a text field, not a password field, so that the browser does not offer to save a token that changes at every start; elsewhere (Firefox) it is a password field. The service writes a new token at every start, so after a restart the page asks again. Then the
City appears: a project whose configuration is not accepted shows the service's message in a band under the header, with
the command to type in the terminal in the terminal-command component (a code block with Copy); a screen that had read the project
keeps what it read (the building, its floors, the cards, the bar, the floor's room and panel), dimmed by one class on the frame
(`is-unaccepted`), and the dim lifts when the next reload finds the configuration accepted; choosing a building keeps its id
in the hash (`#/p/<id>`). The first screen of a service with several projects is the City (`#/city`): an isometric plot with one building per project, the three KPI
cards, the waiting list, the project switcher and the tracking bar; choosing a building moves the camera in and opens the
project's screen: the Building, a cutaway with one floor for each area agent, one compact floor card at the scene's top right for the floor that is hovered or selected, and in the panel the project's facts and the floors list; choosing a floor moves the camera in and opens the Floor, the agent at its desk, with the panel's tabs Agent, Inbox, Desk and Tasks.

A service with one project opens on that project's Building (C-1): the City is its crumb, reached by the "City" crumb (`#/city`), Back is disabled there, Escape does nothing, and the switcher's main button is a label (no cycling, no "1/1"). With several projects the crumb, Back and Escape from the Building lead to `#/city`. With no project at all the switcher's listbox still opens, with its foot alone ("No project", the colour-mode control and "Forget the token").

## The rules of these files

- **Nothing from another host.** No CDN, no font host, no analytics, no remote import. Every `src`, `href`, `import`,
  `url(` and `fetch` is a relative path inside this folder, a `/api/` path of the service or its one open path, `/token-file`. The typefaces are files of `vendor/fonts/`, named by `@font-face` in `style.css`.
- **No build step, no package.** There is no manifest and no tool to run: a file here is the file the browser gets.
- **The token lives in memory and in `sessionStorage`, nowhere else.** Never in a URL, a cookie or `localStorage`; the
  client sends it only as the `Authorization: Bearer` header and logs nothing. Browser storage has one exception that is not the
  token: `js/mode.js` keeps the light/dark preference, a word (`light`, `dark` or `system`), under the one `localStorage` key
  `openhora-mode`. It holds no project data and no token, and no other module touches `localStorage`; `runtime/tests/test_interface_files.py`
  and `test_interface_adj_b1.py` keep both.
- **Text is text.** What came from the service goes into the page with `textContent` or a text node; the page never builds
  markup from a string. The one place that reads Markdown is `js/markdown.js`: it builds elements with `createElement` and
  text nodes only, so a tag, a comment or a script inside a document or a reply is shown as typed.
- **No import map.** The service's policy (`default-src 'self'`) forbids an inline script, and an import map is one, so a
  module imports another by a relative path (the 3D library by `js/three.js`).
- **The styling library's images are blocked by the policy.** Perfect UI draws the mark of a checkbox, a radio and a
  select as an inline `data:` image, which `default-src 'self'` does not allow. A panel that needs one of these controls
  draws its mark in `style.css` or uses another element, until the service's policy is widened in a package of its own.

`runtime/tests/test_interface_files.py` keeps these rules: the routes the client calls are routes of the service, nothing
is loaded from another host, no inline script or forbidden call is in a page file, and every vendored file has the hash its
README records.

## The vendored libraries, and how to update one

Three.js (the 3D renderer) and Perfect UI (the panels' styling) are copied from their npm packages without an edit. To
update one: in a folder outside the repository run `npm pack <package>@<version>`, unpack the tarball, replace the
folder under `vendor/` with the package's files exactly as its README lists them, rewrite the version and the hashes in
that README (`shasum -a 256 <file>`), and run `pytest -q runtime/tests/test_interface_files.py`. A vendored file is never
edited by hand: a change to one fails that test.

## How the page stays current

The page is always current with the runtime (WP-9.13). While the tab is visible it asks the service for the change signal once a second
(`GET /api/v1/versions`: for each project a number that grows on every write to its store, whoever wrote it: this page, the dispatcher's
thread, the terminal). When a number moved it reloads everything it shows, so a change made anywhere is on the screen within about two
seconds (one second of waiting for the next read and the time the reads take). A reload is: `projects`, `status` and `agents` of each
accepted project and the followed request's running task (`js/data.js`, never from a cache), then each screen's own reads, which it
makes when the stamp it is given moves: the Floor the bodies of the agent's tasks and the documents, the Building the documents, the
Lobby the conversation (above its newest message), the bodies of the requests it shows, the documents and the planning agent's tasks,
the Control room `costs` and, when older than 30 s, the open tab; the Floor and the Lobby also the document that is open; the City, the frame and the scene are drawn from the snapshot. The scene's state (the
figure's pose, the lit windows, the beacon, the badges, the tracking bar) follows the same reload, because it is drawn from the same
data. After any write the page sends it reloads at once, when the answer returns (`api.onWrite`), and a job it started keeps its fast
poll; a button press is one reload: the screen's own call to read again after its write joins the reload the client already asked for
(`coalesce.join`), and the page's own write is not reloaded again by the next read of the signal, because a reload reads the signal before
its data and the watcher takes that as its baseline. A body whose read began before a later change is read again when it ends. A reload
that one project refused (not "not accepted") is read again after 10 seconds, not left to the safety net. With nothing changing, the page makes one small request a second, plus one full reload after 30 quiet seconds as a safety net;
while the tab is hidden it asks nothing, and when it is visible again it reloads once. A server push would save the second a poll waits;
the service sends one response per request and holds no connection (`contracts/runtime.md`, "The change signal"), so it is not built.

### Plates, chips, meters and held tasks

A floor's plate shows the chips done, running, queued and left (planned or blocked), each only when its count is not zero, and its
state word: `working`, `Off, mode is stopped`, `held: <reason>` for an agent that has a ready task the dispatcher held (the reason is
the service's, from `status.held`), `resting`, or `not accepted`. The Agent tab shows the sentence of the reason on the current task
and the commands the service gave to get past it (`held[].commands`, or the one command of `next` for `dispatch off`), each in the command component; the City's tooltip adds
"n held". The meters say what they count: "Reference-model runs today" (the runs cap, the reference model's runs) and "Floor-model spend
today" (the dollar cap, the floor model's spend, a run of unknown cost counted at the per-run limit), each with a tooltip sentence; the spend meter is one track with two segments, what was recorded in the theme colour and what is reserved for runs whose cost is not recorded yet in `--wb-tint-reserved`, with both numbers labelled ("$0.03 recorded · up to $0.50 reserved", from `usd_recorded` and `usd_reserved` of `agents`), and "Runs today: n" (`runs_total_today`, every model) is a plain line under the Agent tab's meters and in the caps line; the
KPI cards and the Control room's caps line use the same words (`format.js`). Stop agent and Supervise send the word of the button; the
runtime accepts a narrowing at once, so the page reloads with no refusal, and a wider mode is set in the terminal: the tab shows the service's `wider` commands, one per wider mode, with Copy. A held reason's commands are shown the same way: for `credential` one block for each missing key, named by it, with its own Copy, and "no username registered" in place of a command when the registry has none; the sentence (`held.next`) stays as text. The Control room's
Connections tab shows each verdict the service made at its start that is not ok (`connections.service`), with the service's `start` command.

### Waits, queued lines, and what a card hands over (A-23, A-25, A-26, A-29 to A-33)

- **What waits.** A task that waits for another keeps the state `planned`; `waiting_for` ([{task_id, request_id, reason}], `task_id` null for the person's own `after`) is what the page words: "waiting for #10, request #3" on the tracking bar's step and as one chip on the plate ("waiting for #10", or "2 waiting", its tooltip the reasons), under `left`, and one line with the reason on the Tasks tab's row and in the Agent tab. "Go ahead" (`POST /tasks/{id}/go-ahead`) drops a derived wait, "Drop the after" (`drop_after: true`) the person's own. A plan card lists `waits`, `missing` and `cycles` before approval, each task that waits for a task with a "Go ahead" box; the boxes ticked travel as `go_ahead: [task keys]` with the hash shown. The request form and `/new --after n` take "After request #".
- **The conversation during a run.** The composer says, in place and before Send, that a run is in progress (the running task of `status`, linked), keeps Send on, and a plain line is stored by the service with `queued` and shown with the word "queued" until its reply exists; the page reads the conversation again from the oldest queued line while one waits. A request made from the form during a run is shown as recorded, to be routed when the run ends. A question about the state is answered by the service in prose.
- **The unrecognised route.** The question whose payload `actions` are `choose-flow` and `cancel` has its sentence as body, "Show the agent's reply" (`payload.raw` as plain text), "Choose a flow" (the flow list, read once, then `route` with the flow) and "Cancel the request".
- **A request line (C-2, E-20).** Each request block of the Lobby's Conversation has an id (`wb-request-<n>`). The route `#/p/<id>/lobby/conversation/request/<n>` opens the Conversation, scrolls to that block and focuses its title, once per visit; the "Waiting for you" row of a plan decision opens that route (the plan card is under the request's message), so a plan is two clicks from the Building. A request that waits for its route has "Route it"; after a reload, which forgets the flow chosen in the form, the line carries a flow select beside it (the flows read once, "Let the planning agent route it" first): "Route it" sends `route` with the chosen flow, or with none (a model run). The page never changes a request's text.
- **A card that is done** puts its result on its own line under the chip and the title (the card wraps); an id (commit, pull request) is mono, a sentence is prose, and `kept: n files` with the run folder to copy comes from the payload.
- **A review hands a file over, in two steps (C-17).** "Hand a file over" on the review card sends to the review's task; for a task with the web the runtime's line (`task.drop.line`) stands above the control before the file is chosen; the Agent tab's "Hand a file over" does the same (the current task's body is used as it is, another target is read once). Choosing a file sends nothing: the chosen name and a button "Hand over to task #n" appear (`handOverStep` of `floor/hand-file.js`), and the button sends `handOver`; the button names the task the file goes to now, a refusal the page can know (over 25 MiB, a name the service would refuse) is said at the choice, and a failure leaves the file chosen so that the button can be pressed again.
- **The viewer's image.** The raw route is under `/api/`, so it needs the bearer header: the client returns a Blob (`artifactRaw`), the viewer shows it from a `blob:` URL it revokes when the file changes or the viewer closes, and "Open in a new tab" opens that URL for a png, jpeg or webp (never a svg: a svg is shown in the page as an image only, and a document of the service's origin made of it is a sandbox question nobody verified); bytes of any other type are "cannot show", whatever the list said. The service's policy allows `img-src 'self' blob:` and never `data:`; the library's checked box draws its mark with a `data:` image, so the page's own `.wb-checkbox` draws the checked state in `style.css` with tokens.

## What the scene does and does not do

The scene is drawn only when something changed (data, camera, hover, size) or while a state animates: a running project's
beacon (at most 30 frames a second), a decision's marker dropping in once, the camera moving in (the prototype's curve, about 1 s). It draws nothing
while the document is hidden, caps the pixel ratio at 2, stops its ambient animation under `prefers-reduced-motion`, and
without WebGL shows one line of text and leaves every panel and action working. Its colours are read from the page's CSS
custom properties when it is built and when the colour scheme changes. Nothing in it is decorative: no vehicles, people,
birds or weather. `canvas.wbStats()` (a function on the canvas element) returns the frames drawn so far, for a check.

The Building (the floors separate once when it opens, the figure of a working agent types, the work-order tag moves
to the next floor once) and the Floor (the camera moves into the room once, the typing, a waiting marker dropping in) follow
the same rules; the motions are the prototype's (WP-9.8). A reload that finds the same state, or only other words, does not build the scene
again (`canvas.wbStats()` has `builds` and `relabels`). Windows are warm when the floor's agent works and grey otherwise; no outline
line stands: a hovered or selected object has one. The wheel and a pinch zoom (up to 3 times), a drag pans, a double click on the
ground, the Fit button or the key 0 fit the whole scene, + and - and the arrow keys work with the focus on the scene. The pointer picks meshes only (`pick.js`) and the outline is the edges of the picked object's own meshes (`outline.js`: a building's slabs, bodies and roof, a rack's cabinet, a floor's slab and walls, the figure's parts): the tooltip, the click and the outline name one object. The floors of the Building have a plate each beside them on the desktop and the tablet, stacked; on the phone one compact floor card hangs at the bottom left of the scene, above the camera buttons (the free rectangle is fitted above it), and each row of the floors list is a plate (`plateNode`, `views/building.js`). The Building has no "Control room" label (the header button is its way there; the Lobby's room keeps its door label). The Lobby (WP-9.4: its room is the Floor's `room` scene with a door) and the Control room (WP-9.5) add a builder to `BUILDERS` of `engine.js`
and a module under `js/views/`, read more routes through `js/api.js`, and edit no vendored file.

The Control room's three tabs (WP-9.5) read `skills`, `costs`, `connections` and `agents` through `js/api.js`: all three on entering, then, whenever the page reloads, `costs` (cheap, and it feeds the room); the Skills and Connections tabs, about 0.8 s of server work each, are read again only when their data is older than 30 s (the open one on a reload, the safety net's included, the other when it is opened), so a runtime that writes every few seconds does not keep them busy; `costs` is read again when the Since date changes; they write nothing. Its small server-room scene (racks: the connection facts as LEDs; wall screen: the runs of the last seven days; console) registers itself as the scene kind `server` and is static.

## The phone layout

The layout has four width bands (`style.css`): the phone up to 639 px, docked from 640 to 899 px (the panel docks under the scene, 34 percent of the height), in-between from 900 to 1099 px, and the desktop from 1100 px. From 640 to 1099 px the panel is 340 px (360 px for the Lobby) and the labels of the door and the waiting button are hidden. The top bar's mark hides under 712 px. A few older width variables (card and plate widths, the Lobby's panel width, the Control room's wide panel) switch at 1023 px beside these bands.

Up to 639 px wide the page is one column: the scene fills the whole upper part of the page (no rule gives it a height; `runtime/tests/test_interface_phone_sheet.py` keeps that), the bottom bar (project switcher, "Waiting for you", breadcrumbs, the door) is the last rows of the frame in every state, and everything else floats over the scene, from the bottom up:

- **The bottom sheet** (`js/frame/drawer.js`, A-27). The panel of the Lobby, the Floor, the Building and the Control room, and the City's two lists (Projects and Waiting for you, one sheet), have a handle at their top and three positions: *collapsed* (the header line only, the City's two header lines; the scene whole), *half* (the default for a panel; the City opens collapsed) and *full* (the sheet covers the scene up to the top of the page; there is no top bar on a phone, the header is the bottom bar). The position is a class on the sheet (`is-collapsed`, `is-half`, `is-full`), never a style. It moves by a drag that starts on the handle or on a header line (pointer events: touch and mouse), by a tap on the handle (half to full, full to half, collapsed to half), and by the keyboard: the handle is a button named `Panel size, <position>`, Enter or Space cycles, the arrow keys move one position. A drag never starts on the sheet's scrolled body or on a button of a header, so the body's scroll and the drag do not meet. While a drag lasts the sheet's height is one custom property, `--wb-drawer-drag`, written through the CSSOM like `--wb-x`, `--wb-y` and `--wb-share`; it ends on the position nearest the height reached, and a deliberate drag of 24 px or more always moves one step. Above 639 px the handle is not drawn, the City's wrapper takes no box and the panels are placed as before.
- **The position is kept per screen, in the module's memory**, for as long as the page lives (the routes are hashes, so going to the Building and back restores it; a reload does not). The first request said `sessionStorage`; the rule above lets only `js/token.js` touch it, so the rule wins and nothing of a project or of the token is kept anywhere else.
- **The sheet tells the frame what it does** with one bubbling event, `wb-drawer` (detail `{position, covering, dragging, rising}`). At full on a phone `covering` is true (and false while a drag lasts, and when the viewport leaves the phone width): the frame hides the cards over the scene (`is-sheet-full` on the frame), makes the scene area `inert` (the camera buttons and the canvas leave the tab order) and pauses the scene as a hidden tab does (`engine.setPaused`, which also leaves the camera's fit alone while it lasts, so the person's zoom and pan are not re-clamped; the Control room, which draws its own scene, pauses that one itself). While a drag has the sheet taller than it was (`rising`) the cards are put away (`is-sheet-rising`), and a collapsed sheet shows its content as a drag raises it. A sheet that is taken down says it covers nothing, so a screen's `dispose` calls `drawer.destroy()` before it removes the panel.
- **The cards** (A-28). The KPI row (three tiles, 12 px text, one line each, the short labels and no unit; the sentence with the cap is in each tile's title and name) and the tracking bar are moved by the frame into one stack, `.wb-float`, just above the sheet, and moved back when the page grows past the breakpoint. The camera buttons and the Building's floor steps stand just above that stack, bottom left and bottom right; the Building's floor card hangs from a point above the camera buttons (`cornerBottom` of `cornerPosition` in `js/scene/labels.js`; the card's room is taken from the bottom of the fit). A notice stays at the top of the scene.
- **The camera frames the city (or the building, the floor, the room) in what the cards and the sheet leave.** `frame.insets` measures the stack and the sheet, and each screen's `ResizeObserver` refits the scene when they change size: moving the sheet moves the fit, the canvas itself never resizes.

## What the Floor sends

Only `js/floor/`, the Lobby's `views/lobby*.js` and `cards/` send a write, through `actions.js`: `answer`, `release`, `approve`, `reject`, `verdict`, `cancel`, `setMode`,
`retry` and `handOver` (with `pollJob` for a job). A card draws one button per word of its decision's `actions` and none for a
word it does not know; an effect or a plan is approved with the hash the card shows, read back from the page's own text at the
click, and a hash that is not the decision's is refused before any request; a blocked change set cannot send a release from
the page. A failure is written above the buttons of the control that sent it, the buttons are enabled again and what the
person typed stays; the card is read again, never changed by the page itself. The blocks that show what an approval sends are tab stops with a name (K-5): the effect card's content ("Exact content of the publish") and hash ("Hash of this content"), and the plan card's hash ("Plan hash") on the Floor and in the Lobby. `runtime/tests/test_interface_floor.py` builds
the cards and the Agent tab under a fake document and a fake client and checks what each button sends.

## How the service serves it

`python3 runtime/service.py --project <dir>` binds `127.0.0.1` only and serves this folder at `/`. A file is served when
all of these hold, and is a 404 otherwise:

- its real path (links resolved) is inside this folder, and no part of the path is empty, `.` or `..`, or starts with a dot;
- its extension is one the service knows (html, css, js, json, svg, images, fonts, glTF models, txt): an unknown extension
  is never served;
- it is a regular file of at most 16 MiB. There is no directory listing.

Every response carries `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`; an HTML or SVG document also
carries `Content-Security-Policy: default-src 'self'; img-src 'self' blob:; frame-ancestors 'none'` and `Referrer-Policy: no-referrer`. So a page
here loads nothing from another host (no CDN, no font service, no analytics), runs no inline script or style that the
policy does not allow, and cannot be put in a frame; its images are its own files or `blob:` URLs it built from bytes it
fetched itself (never `data:`).

The static files need no token and hold no data. Everything a page shows comes from `/api/v1/...`, which needs the
token: the person pastes it once per browser session from the token file the service prints the path of (never the token
itself), the page keeps it in memory only, and sends it as `Authorization: Bearer <token>`. It is never in a URL, a
cookie, a log line or the page's source. The service has no cross-origin header, so no other origin can read an answer.

## What a page must do with what it receives

- **Text is text.** A reply, a title, a comment and every field a model or another person wrote leaves the service as a
  JSON string; a page puts it in the document as text (`textContent`), never as markup.
- **A path is data.** Results carry host paths (a run folder, an effect's file). They are shown as text, never as a link
  to open.
- **A job is asked for again.** A route whose operation calls a model or a platform answers `202` with a job; the page asks
  `GET /api/v1/jobs/<n>` until its `state` is `done` or `failed`. The records are in the store; a job lives only in the
  service's memory.
- **A button for each word of `actions`, and for no other.** Whether a decision can be approved, rejected, answered or
  released is the operation's answer.

## What the approval of an effect is worth

An effect (a pull request prepared up to its confirmation gate) is approved from the page with the hash of the content the
page showed: the card draws the exact content and `payload_sha256`, and the click sends that hash, which the operations
layer compares with the effect's file before it executes anything. The guarantee is that the person's browser sent the hash
of the content it displayed. The token and the checks of `Host` and `Origin` keep a stranger and another page from sending
it; they cannot tell a click from a script that holds the token, which is the person's own machine and account. A chat
channel and the MCP channel never approve an effect: the service passes the channel `page` itself, and a request cannot name
one.

## Not here

`accept-config` is not a route: a configuration hash is accepted in the terminal only, so a page can never accept the
change that widens what an agent may do. `run-next` is not a route either: the dispatcher decides what runs.
