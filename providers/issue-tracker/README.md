# Task-board providers

Implementations of the `integration:issue-tracker` class: the task board of the task runtime (`runtime/`), where a person sees and edits the tasks of a project. Interface: the class's row in `providers/CONTRACT.md` ("Verbs per class"): `--check`, `list`, `get`, `upsert`, `resolve`, each with `--config-file <f>`, a JSON file holding the project configuration's `task_board` object (`docs/workbench/runtime.json`).

The board owns only what a person edits on a task: its title, its text, its state and its comments. Everything else stays in the runtime's store and is shown on the item (`shown`), never read back. A provider never reads the store or anything under `runtime/`.

| Implementation | Where the board is | Select with |
|----------------|--------------------|-------------|
| `local.py` | a folder of Markdown files on the machine, one per item | `"task_board": {"provider": "local", "dir": "<absolute folder>"}` |
| `notion.py` | a base (data source) of a Notion workspace, one row per item | `"task_board": {"provider": "notion", "base": "<data source id>", "expires": "YYYY-MM-DD", "fields": {}, "states": {}}` |

## Local (`local.py`)

Standard library only; runs on Python 3.9. No credential, no network. The board is the folder `dir`: `<dir>/<id>.md` per item, the id lowercase letters, digits and hyphens. An item the provider creates is `t<n>`; a file a person writes by hand in the folder is an item too, and one with no `State:` line is `requested`. The file:

```markdown
# <title>

State: <state>

<text, any Markdown>

## Comments

- <one comment per line>

## Runtime

- <key>: <value>
```

`version` is the sha256 of the file's bytes, so it changes with any edit. A write goes through a temporary file and `os.replace`, keeps every part the item file does not name (a person's title, text and comments survive a write of the state), and writes `## Runtime` from `shown`. The key of a creation is kept in `<dir>/.keys.json`, so the same key never creates twice; `resolve` records what a person found for a key. `list` skips every file whose name starts with a dot.

## Notion (`notion.py`)

Python 3.10 or newer, with `keyring` (its header): run with `uv run`, never with the system interpreter. The token is `NOTION_TOKEN`, read only through `providers/secrets/resolver.py` (stored with `uv run --with keyring==25.7.0 keyring set ai-workbench notion`): an internal integration with read content, update content, insert content and read comments, given only the base. Neither the base's identifier nor the token is ever written in this repository: they live in the project's `docs/workbench/runtime.json` and in the secret store.

- `base` is the identifier of the base's data source (in the app: the base's settings, "Manage data sources", "Copy data source ID"). API version 2026-03-11 queries rows and creates them on a data source, not on a database.
- `fields` maps `title`, `state` and `shown` to the names of the base's properties (defaults `Name`, `Status`, `Runtime`): a title, a status or select, and a text property. `--check` refuses (exit 3) a base that lacks one.
- `states` maps each of the nine task states to the option the base uses (default: the state's own word); two states on one option is a usage error. An option the map does not know is read as `null`; a row with no option is `requested`, as a local item with no `State:` line.
- The item's text is the body of the row's page, converted by `providers/documents/notion_blocks.py`, loaded by path: the only file this script loads from another class's folder (a test asserts it). `shown` is written to the shown property as `key: value` lines and never read back.
- `version` is the page's `last_edited_time`; `archived` is true when the page reports `in_trash`, `is_archived` or `archived` (the reference names all three across its pages). `list` takes rows from one paginated query; `get` adds the body at every depth and the open comments of the page.
- An `upsert` on an existing row reads it first and sends only the properties that differ, and replaces the body only when its text differs, so a write of a value already there changes nothing. A body is replaced by appending the new blocks first and deleting the old ones after, so a failure never leaves the row empty.
- At most one row per idempotency key: the key is pending in the ledger (`issue-tracker-notion.json` in the data folder, 0600; `INTEGRATION_ISSUE_TRACKER_NOTION_LEDGER` names another file) before the creation and done after it, scoped by the base. A 4xx other than 408 and 429 releases it; anything else keeps it pending until `resolve`. No verb retries: a 429 or a 5xx is exit 1 with the status (and `Retry-After`) on stderr.
- No redirect is followed. `INTEGRATION_ISSUE_TRACKER_NOTION_API_BASE` replaces the service's address for tests only, and only with a loopback URL (exit 2 otherwise); the secret store is then never read.

Choices made where the plan left one (the supervisor's rule: the smallest call table the verbs need): the board is read by one query of the data source, never per row; the type of the state property is read from the row (or, for a creation, from the data source), not configured; the body of a creation is appended after the row is created, so the creation itself carries properties only.

### Calls this provider makes

The one table of calls is `CALLS` at the top of `notion.py`; every row below is read from the public reference, none from memory.

| Method and path | Used for | Reference | Read on |
|---|---|---|---|
| `GET /v1/data_sources/{id}` | `--check`; the state property's type before a creation | https://developers.notion.com/reference/retrieve-a-data-source | 2026-10-06 |
| `POST /v1/data_sources/{id}/query` | `list` | https://developers.notion.com/reference/query-a-data-source | 2026-10-06 |
| `GET /v1/pages/{id}` | `get`; an `upsert` reads the row first and its version after | https://developers.notion.com/reference/retrieve-a-page | 2026-10-06 |
| `POST /v1/pages` | `upsert` without `--id`: a row, `parent` `{"type": "data_source_id", "data_source_id": <base>}` | https://developers.notion.com/reference/post-page | 2026-10-06 |
| `PATCH /v1/pages/{id}` | `upsert`: the properties that differ | https://developers.notion.com/reference/patch-page | 2026-10-06 |
| `GET /v1/blocks/{id}/children` | `get`, `upsert`: the body, at every depth (`has_children`) | https://developers.notion.com/reference/get-block-children | 2026-10-06 |
| `PATCH /v1/blocks/{id}/children` | `upsert`: the body, 100 children per call, a block's children under it in later calls | https://developers.notion.com/reference/patch-block-children | 2026-10-06 |
| `DELETE /v1/blocks/{id}` | `upsert`: the old body, after the new one is appended | https://developers.notion.com/reference/delete-a-block | 2026-10-06 |
| `GET /v1/comments?block_id={id}` | `get`: the open comments of the row's page | https://developers.notion.com/reference/list-comments | 2026-10-06 |
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

`uv run --with pytest==9.1.1 pytest providers/issue-tracker/tests`: offline. `test_issue_tracker_contract.py` runs the contract on every implementation the resolver lists; a new implementation adds its harness to `tests/board_harness.py` (how a person changes the board without the provider) and nothing else. The Notion harness plays the person on the stand-in service `providers/documents/tests/fake_notion.py` (127.0.0.1, a free port), shared with the documents class; `test_issue_tracker_notion.py` holds what is particular to `notion.py`.
