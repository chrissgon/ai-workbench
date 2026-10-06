# Documents provider (`integration:documents`)

The documents of the task runtime (`runtime/`), mirrored where the project keeps them: on the machine or on a platform. The runtime calls a provider of this class with the project configuration's `documents` object (`docs/workbench/runtime.json`); the verbs and what each prints are in `providers/CONTRACT.md`, "Verbs per class". A write replaces the whole document; it never merges.

| File | What it is |
|------|------------|
| `local.py` | The documents as Markdown files in a folder of the machine, outside the project (`dir`); comments are the `- ` lines of a side file `<path>.comments.md`. Standard library only, Python 3.9 |
| `notion.py` | The documents as pages of a Notion workspace under one parent page: `{"provider": "notion", "parent": "<page id>", "expires": "YYYY-MM-DD"}`. Python 3.10 or newer, with `keyring`: run with `uv run` |
| `notion_blocks.py` | A pure helper, not an implementation: Markdown to the blocks of a page and back (`round_trip`), the platform's side of the trip for an implementation that stores blocks |

The class is found by its folder; its row in `contracts/environment.md` (and `LISTED` of `providers/resolve.py`) comes with the router's first change of its routing table.

## Which documents a person may edit on a platform

A skill's runtime manifest (`skills/<name>/evals/runtime-manifest.json`) marks each document it writes `editable` or `read_only`. A type is `editable` only when it survives the trip: `tests/test_document_types.py` runs, for each `editable` entry, the skill's own checker on its fixture before and after `notion_blocks.round_trip` (or, with no checker, checks that no word is lost). A fixture is a case of `tests/fixtures/round-trip.json` or of `tests/fixtures/types/<skill>.json`, a document a lab run of the skill wrote on its own fictional fixture. A type that fails is set to `read_only` in its manifest; the converter is not changed to make it pass.

## Notion (`notion.py`)

The token is `NOTION_TOKEN`, read only through `providers/secrets/resolver.py` (stored with `uv run --with keyring==25.7.0 keyring set ai-workbench notion`): an internal integration with read content, update content, insert content and read comments, given only the parent page. Neither the parent's identifier nor the token is ever written in this repository: they live in the project's `docs/workbench/runtime.json` and in the secret store.

- A document is a page under `parent`, created by the first `write` without `--id` and titled by its project-relative path; its id is the page's identifier. An id that is not a page identifier names no document (exit 1).
- `write` converts with `notion_blocks.to_blocks` and replaces every child block of the page: the new blocks are appended first, at most 100 per call, each sent without its own children (a table keeps its rows), whose children are appended under it in later calls, so no request nests more than one level; then the old blocks are deleted. A failure never leaves the page empty.
- `read` lists the children at every depth and converts them with `notion_blocks.to_markdown`: it returns the round trip of what was written, not the same bytes (`expected` of the harness). `stat` retrieves the page object only.
- `version` is the page's `last_edited_time`; `archived` is true when the page reports `in_trash`, `is_archived` or `archived`. Comments are those the service lists for the page (the reference: unresolved comments only).
- At most one page per idempotency key: the key is pending in the ledger (`documents-notion.json` in the data folder, 0600; `INTEGRATION_DOCUMENTS_NOTION_LEDGER` names another file) before the creation and done after it, scoped by the parent. A 4xx other than 408 and 429 releases it; anything else keeps it pending until `resolve`. No verb retries: a 429 or a 5xx is exit 1 with the status (and `Retry-After`) on stderr.
- No redirect is followed. `INTEGRATION_DOCUMENTS_NOTION_API_BASE` replaces the service's address for tests only, and only with a loopback URL (exit 2 otherwise); the secret store is then never read.

Choices made where the plan left one (the smallest call table the verbs need): no request nests children (the reference allows two levels; one call per parent block costs calls, not endpoints); the new body before the old one is deleted; a creation carries the title only, and the body follows by appends.

### Calls this provider makes

The one table of calls is `CALLS` at the top of `notion.py`; every row below is read from the public reference, none from memory.

| Method and path | Used for | Reference | Read on |
|---|---|---|---|
| `GET /v1/pages/{id}` | `--check` (the parent), `stat`, `read`; the version after a `write` | https://developers.notion.com/reference/retrieve-a-page | 2026-10-06 |
| `POST /v1/pages` | `write` without `--id`: a page, `parent` `{"type": "page_id", "page_id": <parent>}`, the `title` property only | https://developers.notion.com/reference/post-page | 2026-10-06 |
| `GET /v1/blocks/{id}/children` | `read`: the blocks at every depth (`has_children`); `write`: the old top-level blocks | https://developers.notion.com/reference/get-block-children | 2026-10-06 |
| `PATCH /v1/blocks/{id}/children` | `write`: 100 children per call, a block's children under it in later calls | https://developers.notion.com/reference/patch-block-children | 2026-10-06 |
| `DELETE /v1/blocks/{id}` | `write`: each old top-level block, after the new ones are appended | https://developers.notion.com/reference/delete-a-block | 2026-10-06 |
| `GET /v1/comments?block_id={id}` | `read`: the open comments of the page | https://developers.notion.com/reference/list-comments | 2026-10-06 |
| (every call) | Headers of every call: `Authorization: Bearer <token>`, `Notion-Version: 2026-03-11` | https://developers.notion.com/reference/versioning | 2026-10-06 |
| (every call) | Pagination: `page_size` 100 (the maximum), `start_cursor` from `next_cursor` while `has_more` | https://developers.notion.com/reference/intro | 2026-10-06 |
| (every call) | Limits: 100 children per append, two levels of nesting per request, 2,000 characters per text object, 1,000 block elements and 500 KB per request; 429 `rate_limited` with `Retry-After`; 180 requests a minute (600 on Business and Enterprise plans) | https://developers.notion.com/reference/request-limits | 2026-10-06 |
| (every call) | Errors: 401 a token the service rejects (exit 3), 403/404 an object missing or not shared with the integration, 409, 429, 5xx | https://developers.notion.com/reference/status-codes | 2026-10-06 |

## Measured on the live service

The ten measurements of the platform plan (stage 3, WP-3.10, step 4), made by the maintainer on a scratch page and a scratch base of his own workspace, with the token in the secret store. Each row is written as observed: the command, what it printed with identifiers removed, the date. Until a row is measured, the code follows the public reference and the stand-in service of the tests decides what the reference leaves open (`tests/fake_notion.py` of the documents class says what).

| # | What is not known | Observed | Date |
|---|---|---|---|
| N1 | Which field of a page says it changed, and how fine it is | not measured yet | |
| N2 | Whether the runtime's own write moves that field, and to what | not measured yet | |
| N3 | Whether a comment moves that field | not measured yet | |
| N4 | Whether replacing a page's content deletes its open comments, and whether a comment on one block is listed with the page's | not measured yet | |
| N5 | Whether resolved comments are listed | not measured yet | |
| N6 | The limits: child blocks per call, nesting depth per call, calls per second, and what too many requests answers | not measured yet | |
| N7 | Whether the live service returns the block shapes `notion_blocks.py` writes | not measured yet | |
| N8 | How an item deleted or archived by a person is reported | not measured yet | |
| N9 | Whether the rows of a base can be asked for "changed since" in one call | not measured yet | |
| N10 | What the service answers when the integration was not given the page | not measured yet | |

## Tests

`uv run --with pytest==9.1.1 pytest -q providers/documents/tests`: the contract on every implementation (`documents_harness.py` plays the person for each), what is particular to `local.py` and to `notion.py`, the trip of each editable type, and the converter. `fake_notion.py` is the stand-in service on 127.0.0.1 that the Notion harnesses of both classes use: it serves exactly the calls of the two tables above and refuses what the reference says the service refuses.
