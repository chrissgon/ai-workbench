# The local interface

The folder `runtime/service.py` serves: the static files of the page a person uses to work with the task runtime on
their own machine. It holds no rule of the work. Which words a pending decision takes, what a state leads to and what a
hash must equal are decided by the operations layer (`runtime/ops.py`) and the store; the page shows what an operation
returned and sends what the person typed or clicked.

## What is here

| Path | What |
|---|---|
| `index.html`, `style.css`, `favicon.svg` | The one page, its rules and its icon. No inline script, no inline style: every rule is in `style.css`, every script is a module. `style.css` derives the page's own tokens (`--wb-raised`, `--wb-ground`, `--wb-elev`, ...) from the library's, with no colour literal. |
| `icons/` | One clean SVG file per icon (13, from the Lucide set), drawn by a CSS mask in the colour of the text. |
| `js/main.js` | The page: the token prompt, then the shared frame with the screen the hash names (`#/` is the City; the other screens are placeholders until their packages), and the poll (every 5 s while the document is visible, none while it is hidden). |
| `js/router.js`, `js/format.js`, `js/model.js` | Pure functions: the hash forms, the display words and numbers, and what the City shows worked out from the service's bodies (floors, windows, waiting rows, the tracking bar). Tested under Node. |
| `js/data.js` | What the City reads: `projects`, then `status` and `agents` of each accepted project, and the running task's `task` body. Reads only. |
| `js/api.js` | The client of the service: one function per route of `ROUTES` in `runtime/service.py`, named after the operation. |
| `js/token.js`, `js/dom.js` | The token for this session; building elements (strings become text, a style or an event attribute is refused). |
| `js/frame/` | The shared frame of every scene screen: header (back, breadcrumbs, project switcher), KPI cards, waiting list, tracking bar, panel shell, sheet (a phone's lists), icons. |
| `js/scene/` | The scene engine: `engine.js` (one renderer, orthographic camera, picking, labels, tokens read at run time), `loop.js` (the render scheduler: a frame only when asked, at most 30 a second while an ambient animation runs, none while hidden), `palette.js`, `kit.js`, `props.js`, `city.js` (the City's geometry), `labels.js`, `cull.js`, `fit.js`, `tween.js` (the camera move as a state machine). |
| `js/views/` | One module per screen: `token-prompt.js`, `city.js` (the City) and `placeholder.js` (the Building, Floor, Lobby and Control room until their packages). |
| `js/three.js` | The one place the 3D library is imported from (a relative re-export); the scene uses it. |
| `vendor/three/`, `vendor/<library>/` | The two third-party libraries, copied unchanged, each folder with a README that records the package, the exact version, the licence and the sha256 of every file. |

## How to open it

```
python3 runtime/service.py --project <dir>
```

It prints one JSON line with the page's `url` and the path of the `token_file`. Open the url in a browser, open the token
file in an editor or with `cat`, and paste its one line into the page. The page asks for it once per browser session: it
is kept in memory and in the tab's `sessionStorage` (which the browser drops when the tab closes), and the button "Forget
the token" clears both. The service writes a new token at every start, so after a restart the page asks again. Then the
City appears: a project whose configuration is not accepted shows the service's message (the command to type in the
terminal) in a band under the header; choosing a building keeps its id
in the hash (`#/p/<id>`). The first screen is the City: an isometric plot with one building per project, the three KPI
cards, the waiting list, the project switcher and the tracking bar; choosing a building moves the camera in and opens the
project's screen (a placeholder with the status counts until the Building screen is built).

## The rules of these files

- **Nothing from another host.** No CDN, no font host, no analytics, no remote import. Every `src`, `href`, `import`,
  `url(` and `fetch` is a relative path inside this folder or a `/api/` path of the service.
- **No build step, no package.** There is no manifest and no tool to run: a file here is the file the browser gets.
- **The token lives in memory and in `sessionStorage`, nowhere else.** Never in a URL, a cookie or `localStorage`; the
  client sends it only as the `Authorization: Bearer` header and logs nothing.
- **Text is text.** What came from the service goes into the page with `textContent` or a text node; the page never builds
  markup from a string.
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

## What the scene does and does not do

The scene is drawn only when something changed (data, camera, hover, size) or while a state animates: a running project's
beacon (at most 30 frames a second), a decision's marker dropping in once, the camera moving in (600 ms). It draws nothing
while the document is hidden, caps the pixel ratio at 2, stops its ambient animation under `prefers-reduced-motion`, and
without WebGL shows one line of text and leaves every panel and action working. Its colours are read from the page's CSS
custom properties when it is built and when the colour scheme changes. Nothing in it is decorative: no vehicles, people,
birds or weather. `canvas.wbStats()` (a function on the canvas element) returns the frames drawn so far, for a check.

The Building, the Floor, the Lobby and the Control room are WP-9.3b to WP-9.5. They add modules under `js/views/` and
`js/scene/` (a builder per scene kind, registered in `BUILDERS` of `engine.js`) and read more routes through `js/api.js`;
they edit no vendored file.

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
