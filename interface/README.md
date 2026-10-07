# The local interface

The folder `runtime/service.py` serves: the static files of the page a person uses to work with the task runtime on
their own machine. It holds no rule of the work. Which words a pending decision takes, what a state leads to and what a
hash must equal are decided by the operations layer (`runtime/ops.py`) and the store; the page shows what an operation
returned and sends what the person typed or clicked.

Today the folder holds only this file. The pages come with the next packages of stage 9 (the scene, then the views); they
are plain files in this folder, ES modules and a stylesheet, with the libraries they use vendored under `vendor/`, each
with its version, its licence text and its sha256 written beside it. There is no build step and no package to install.

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
