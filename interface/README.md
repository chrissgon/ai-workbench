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
| `js/main.js` | The page: the token prompt, then the shared frame with the screen the hash names (`#/` is the City, `#/p/<id>` the Building, `#/p/<id>/floor/<agent>` the Floor, `#/p/<id>/lobby` the Lobby; the Control room `#/p/<id>/control`), and the reload: everything the page shows is read again (`js/data.js`, then each screen's own reads, given a stamp that moves) when the watcher says the store changed, after any write the page sent, and on return to a visible tab (see `js/watch.js`). |
| `js/watch.js` | The page's liveness, with no knowledge of the screens: `createWatcher` reads the change signal (`GET /versions`, one request for every project) every second while the document is visible, and asks for a reload when a number moved, once when the signal could not be read and once when it can again (a failed read is retried after 10 s), after 30 seconds with no reload as a safety net, and once on return to a visible tab; it keeps no timer and reads nothing while the document is hidden. It keeps time and reads only through what it is given, so a test drives it with a fake clock (`runtime/tests/test_interface_live.py`). `coalesce` makes the reload one at a time: a request made during a reload makes one more after it. |
| `js/router.js`, `js/format.js`, `js/model.js`, `js/floor-model.js`, `js/world-model.js` | Pure functions: the hash forms (a document of the desk is `/desk/<percent-encoded path>`), the display words and numbers, what the City shows worked out from the service's bodies (floors, windows, waiting rows, the tracking bar), and what the Building and the Floor show (each floor's state, plate and list row, the current task, the run block, the desk rows, the resolved lines). Tested under Node. |
| `js/data.js` | What the City reads: `projects`, then `status` and `agents` of each accepted project, and the running task's `task` body (a reload reads it again whatever its state; without `force` it is reused while the state is the same), and `versionKey`, the change signal of every project as one string. Reads only. |
| `js/api.js` | The client of the service: one function per route of `ROUTES` in `runtime/service.py`, named after the operation. `pollJob` asks for a running job every second (at least 200 ms) and asks nothing while the document is hidden: the first poll after the tab is visible again happens at once, then the period continues; an abort rejects at once, paused or not. `onWrite` registers the one function called after the service answered any POST, whatever it answered (the page reloads at once); `version` and `versions` read the change signal. |
| `js/markdown.js` | The one Markdown renderer: headings 1 to 4, paragraphs, bold, italic, inline and fenced code, lists, quotes, tables, rules and line breaks, built as DOM nodes. Raw HTML, comments and entities stay text; an image is its alt text and address as text; a link is its text and its address as text unless the address is a route of this page (`#/...`), then a plain anchor, so a click never leaves the page; the only attributes it sets are `class` and that `href`; it tries at most 500 bracket pairs in a paragraph. A document over 200,000 characters renders its first part and shows the rest as one plain block. Called by `js/markdown-view.js` (the rendered view with the "Plain text" toggle, used by the viewer and by both plan cards, one session choice for all), by the cards (question, acceptance and review bodies) and by the conversation (the planning agent's replies; the person's messages stay plain text). |
| `js/token.js`, `js/dom.js` | The token for this session; building elements (strings become text, a style or an event attribute is refused). |
| `js/frame/` | The shared frame of every scene screen: header (back, breadcrumbs, project switcher), KPI cards, waiting list, tracking bar, panel shell, sheet (a phone's lists), icons, `escape.js` (the order of the one Escape handler: a field, a dialog, a document, a menu, a selection, then up one level), `origin.js` (the tab and the decision an open document was opened from, else the Desk: the viewer's "Close", a phone's dialog and Escape all go to the hash it names), `command.js` (the terminal-command component: the sentence, the command the service gave in a code block that wraps whole, and a Copy button that uses the clipboard and, where the browser refuses it, selects the text; `isCommand` and `commandsIn` tell a command from a sentence and take the commands out of a sentence that names them). The command of a refusal is the `next` of the 412 body (`ApiError.next`), never read out of its sentence. |
| `js/scene/` | The scene engine: `engine.js` (one renderer, orthographic camera, picking, labels, tokens read at run time, the one world of the City, the Building, the Floor and the Lobby and its targets, the work-order tag moving), `loop.js` (the render scheduler: a frame only when asked, at most 30 a second while an ambient animation runs, none while hidden), `palette.js`, `kit.js`, `props.js`, `labels.js`, `cull.js`, `fit.js` (the fitted camera), `rig.js` (the isometric camera and a scene's bounds, shared by the engine and the picking test), `prototype-motion.js` (the prototype's own motion functions: the approach by frame, the working pose, the beacon), `camera.js` (the person's zoom and pan with limits, the pointer's mapping), `look.js` (the window colour, which outline lines show, what a `show` must do), `pick.js` (what the pointer is on: the meshes of the pickable objects, never a line), `outline.js` (the outline of a hovered object: the edges of its outer shell parts only), `pointer.js`, `tween.js` (the camera's goal followed each frame, retargetable), `world.js` and `tower.js` (the one persistent world: every building with its floors, each floor already holding its room; a screen only sets targets on it: the open building, the floor, the selection), and the builders it uses: `city.js` (ground, streets, the beacon), `building.js` (the room of one floor), with `furniture.js` (desk, chair, tray, sheet, table, cabinet, lamp, bookshelf, door), `figure.js` (the agent in its three poses and the typing motion) and `plates.js` (the compact floor card, the board, tag and door labels). |
| `js/views/` | One module per screen: `token-prompt.js`, `city.js` (the City), `lobby.js` with `lobby-*.js` (the Lobby: the conversation, the request form, the composer, the tab list, the cancel dialog, the room; `lobby-inbox.js`, `lobby-desk.js` and `lobby-agent.js` hand the Floor's Inbox, Desk and viewer, and Agent tab the planning agent: its decisions, its documents (those with `agent` "planning" or none) and its tasks; `lobby.js` itself builds the Floor's Tasks tab for the planning agent, whose tasks are those with `agent` "planning" or none), `building.js` (the Building: the cutaway, the floors list, the project's facts), `floor.js` (the Floor: the room and the panel with the tabs Agent, Inbox, Desk and Tasks) and the Control room: `control.js` (the panel, the tabs, the reads, the server-room scene), `control-skills.js`, `control-costs.js` and `control-connections.js` (one per tab), `control-scene.js` (the server-room builder), `control-model.js` (the pure part: chips, filters, the chart, the cost words and the scene's model, tested under Node) and `control-parts.js` (the loading line, the failed-read notice, the empty block); `placeholder.js` stays as the fallback of an unknown screen. |
| `js/floor/` | The Floor's panel and the decision cards, the only files that send a write: `cards.js` (effect, acceptance, question, review and plan cards, the request line and the cancel dialog), `inbox.js`, `agent-tab.js` (Stop agent and Supervise, the held reason of the current task, retry, hand a file over), `desk-tab.js`, `tasks-tab.js` with `tasks-model.js` (the Tasks tab: every task of the agent in groups by state, with Retry on a failed or blocked one, "Open in the Inbox" on one that waits, the paths a done task returned and its runs on expand; it reads `task` for its first twelve rows and for a row when expanded, and sends only Retry, through the client it is handed), `run-block.js` (the run block the Agent tab and the Tasks tab share), `viewer.js` (a document: Markdown drawn by `js/markdown.js` through `js/markdown-view.js`, with a "Plain text" toggle, or the text in a wrapped `pre`), `widgets.js`, and `actions.js`, the one object that names every write of the client; the cards and the tab are handed it, so a test can give them a fake client. |
| `js/cards/` | The decision cards the Lobby draws under a message: `plan.js` (the plan card: the table of tasks, the limits, the whole hash, "Approve this plan" sending exactly the hash it shows) and `plan-rows.js` (what it shows, worked out from the decision's payload). |
| `js/three.js` | The one place the 3D library is imported from (a relative re-export); the scene uses it. |
| `vendor/three/`, `vendor/<library>/` | The two third-party libraries, copied unchanged, each folder with a README that records the package, the exact version, the licence and the sha256 of every file. |

## The brand

The page's primary colour is the library's one token `--pui-theme`, set once at `:root` in `style.css` to the brand pair `light-dark(#6B4429, #C99A6E)` (a brown on a light ground, a lighter brown on a dark one); no other token of the library is set by the page. Everything that is "the theme" reads that token and nothing else: the tints derived from it (`--wb-ink-theme`, `--wb-tint-selected`, `--wb-tint-reserved`), the meters, the focus rings, the running dot, the outline buttons, and the scene, which reads the token through a probe element when it is built and when the colour scheme changes (`js/scene/palette.js`; the outline of a hovered or selected object copies `palette.T.theme`, so no scene file holds a colour of its own). To change the primary, change that one line. It is the only colour literal in the stylesheet, and `runtime/tests/test_interface_files.py` keeps it so.

The "working" light of a floor's windows is the library's amber (`--pui-warn`), not the brand brown. On a dark ground the two were looked at side by side in the served page (a working floor beside the selected floor's outline, and the amber dot of a waiting floor beside the brown dot of a running one): the brown `#C99A6E` and the amber `#F59E0B` are about 14 apart in CIEDE2000 and read as two colours at the size of a window, so the amber stays; the identity's alternative, a warm white `#FFE8C2` for the working light, is not used.

The favicon (`favicon.svg`) and the mark (`brand/openhora-mark.svg`) are the identity's drawings with their provenance metadata block removed and nothing else changed; a test records the hash of each file and the first path of each drawing, so a new drawing changes those two lines on purpose.

## How to open it

```
python3 runtime/service.py --project <dir>
```

It prints one JSON line with the page's `url` and the path of the `token_file`. Open the url in a browser, open the token
file in an editor or with `cat`, and paste its one line into the page. The page asks for it once per browser session: it
is kept in memory and in the tab's `sessionStorage` (which the browser drops when the tab closes), and the button "Forget
the token" clears both. Where the browser can mask a text field by CSS the field is such a text field, not a password field, so that the browser does not offer to save a token that changes at every start; elsewhere (Firefox) it is a password field. The service writes a new token at every start, so after a restart the page asks again. Then the
City appears: a project whose configuration is not accepted shows the service's message in a band under the header, with
the command to type in the terminal in the terminal-command component (a code block with Copy); a screen that had read the project
keeps what it read (the building, its floors, the cards, the bar, the floor's room and panel), dimmed by one class on the frame
(`is-unaccepted`), and the dim lifts when the next reload finds the configuration accepted; a screen that never read the project
shows the placeholder; choosing a building keeps its id
in the hash (`#/p/<id>`). The first screen is the City: an isometric plot with one building per project, the three KPI
cards, the waiting list, the project switcher and the tracking bar; choosing a building moves the camera in and opens the
project's screen: the Building, a cutaway with one floor for each area agent, one compact floor card at the scene's top right for the floor that is hovered or selected, and in the panel the project's facts and the floors list; choosing a floor moves the camera in and opens the Floor, the agent at its desk, with the panel's tabs Agent, Inbox, Desk and Tasks.

## The rules of these files

- **Nothing from another host.** No CDN, no font host, no analytics, no remote import. Every `src`, `href`, `import`,
  `url(` and `fetch` is a relative path inside this folder or a `/api/` path of the service.
- **No build step, no package.** There is no manifest and no tool to run: a file here is the file the browser gets.
- **The token lives in memory and in `sessionStorage`, nowhere else.** Never in a URL, a cookie or `localStorage`; the
  client sends it only as the `Authorization: Bearer` header and logs nothing.
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
and, when the service gave a command to get past it (`dispatch off`, `secret store`), the command component; the City's tooltip adds
"n held". The meters say what they count: "Reference-model runs today" (the runs cap, the reference model's runs) and "Floor-model spend
today" (the dollar cap, the floor model's spend, a run of unknown cost counted at the per-run limit), each with a tooltip sentence; the spend meter is one track with two segments, what was recorded in the theme colour and what is reserved for runs whose cost is not recorded yet in `--wb-tint-reserved`, with both numbers labelled ("$0.03 recorded · up to $0.50 reserved", from `usd_recorded` and `usd_reserved` of `agents`), and "Runs today: n" (`runs_total_today`, every model) is a plain line under the Agent tab's meters and in the caps line; the
KPI cards and the Control room's caps line use the same words (`format.js`). Stop agent and Supervise send the word of the button; the
runtime accepts a narrowing at once, so the page reloads with no refusal, and a wider mode is set in the terminal: the tab shows the service's `wider` commands, one per wider mode, with Copy. A held reason's command (`held.next`) is shown the same way; for `credential` it is a sentence with the commands that store the key, each with its own Copy. The Control room's
Connections tab shows each verdict the service made at its start that is not ok (`connections.service`), with the service's `start` command.

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
ground, the Fit button or the key 0 fit the whole scene, + and - and the arrow keys work with the focus on the scene. The pointer picks meshes only (`pick.js`) and the outline is the edges of the picked object's own meshes (`outline.js`: a building's slabs, bodies and roof, a rack's cabinet, a floor's slab and walls, the figure's parts): the tooltip, the click and the outline name one object. The floors of the Building have a plate each beside them on the desktop and the tablet, stacked; on the phone one compact floor card is pinned at the top right of the scene, and each row of the floors list is that same card (`floorCardNode`). The Building has no "Control room" label (the header button is its way there; the Lobby's room keeps its door label). The Lobby (WP-9.4: its room is the Floor's `room` scene with a door) and the Control room (WP-9.5) add a builder to `BUILDERS` of `engine.js`
and a module under `js/views/`, read more routes through `js/api.js`, and edit no vendored file.

The Control room's three tabs (WP-9.5) read `skills`, `costs`, `connections` and `agents` through `js/api.js`: all three on entering, then, whenever the page reloads, `costs` (cheap, and it feeds the room); the Skills and Connections tabs, about 0.8 s of server work each, are read again only when their data is older than 30 s (the open one on a reload, the safety net's included, the other when it is opened), so a runtime that writes every few seconds does not keep them busy; `costs` is read again when the Since date changes; they write nothing. Its small server-room scene (racks: the connection facts as LEDs; wall screen: the runs of the last seven days; console) registers itself as the scene kind `server` and is static.

## What the Floor sends

Only `js/floor/`, the Lobby's `views/lobby*.js` and `cards/` send a write, through `actions.js`: `answer`, `release`, `approve`, `reject`, `verdict`, `cancel`, `setMode`,
`retry` and `handOver` (with `pollJob` for a job). A card draws one button per word of its decision's `actions` and none for a
word it does not know; an effect or a plan is approved with the hash the card shows, read back from the page's own text at the
click, and a hash that is not the decision's is refused before any request; a blocked change set cannot send a release from
the page. A failure is written above the buttons of the control that sent it, the buttons are enabled again and what the
person typed stays; the card is read again, never changed by the page itself. `runtime/tests/test_interface_floor.py` builds
the cards and the Agent tab under a fake document and a fake client and checks what each button sends.

## How the service serves it

`python3 runtime/service.py --project <dir>` binds `127.0.0.1` only and serves this folder at `/`. A file is served when
all of these hold, and is a 404 otherwise:

- its real path (links resolved) is inside this folder, and no part of the path is empty, `.` or `..`, or starts with a dot;
- its extension is one the service knows (html, css, js, json, svg, images, fonts, glTF models, txt): an unknown extension
  is never served;
- it is a regular file of at most 16 MiB. There is no directory listing.

Every response carries `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`; an HTML or SVG document also
carries `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'` and `Referrer-Policy: no-referrer`. So a page
here loads nothing from another host (no CDN, no font service, no analytics), runs no inline script or style that the
policy does not allow, and cannot be put in a frame.

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
