# Task-board providers

Implementations of the `integration:issue-tracker` class: the task board of the task runtime (`runtime/`), where a person sees and edits the tasks of a project. Interface: the class's row in `providers/CONTRACT.md` ("Verbs per class"): `--check`, `list`, `get`, `upsert`, `resolve`, each with `--config-file <f>`, a JSON file holding the project configuration's `task_board` object (`docs/workbench/runtime.json`).

The board owns only what a person edits on a task: its title, its text, its state and its comments. Everything else stays in the runtime's store and is shown on the item (`shown`), never read back. A provider never reads the store or anything under `runtime/`.

| Implementation | Where the board is | Select with |
|----------------|--------------------|-------------|
| `local.py` | a folder of Markdown files on the machine, one per item | `"task_board": {"provider": "local", "dir": "<absolute folder>"}` |

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

## Tests

`uv run --with pytest==9.1.1 pytest providers/issue-tracker/tests`: offline. `test_issue_tracker_contract.py` runs the contract on every implementation the resolver lists; a new implementation adds its harness to `tests/board_harness.py` (how a person changes the board without the provider) and nothing else.
