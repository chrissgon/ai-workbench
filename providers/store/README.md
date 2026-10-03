# Store providers

Implementations of the `store:runtime` class (`store` until 2026-10-02; the folder and `STORE_PROVIDER` keep that name): the durable state of the agent runtime (backlog R2). Interface: `providers/CONTRACT.md`. Selected with `STORE_PROVIDER=sqlite`; the runtime calls the store only through its CLI, so another implementation (a cloud database) can replace it without changing the runtime.

The decision behind it is in `docs/decisions.md` ("2026-09-28: An agent runtime as a new, tool-free layer; storage behind an interface"): a Markdown file does not take several agents writing at once, so state that agents write goes to a store. The first user is the `social-manager` agent (backlog PB7).

## SQLite (`sqlite.py`)

Standard library only (`sqlite3`); runs with `python3` or `uv run`. No credential: the database is a local file.

### Tables

| Table | What it holds | Written by |
|-------|---------------|------------|
| `schema_version` | one row per applied migration | `init` |
| `cursors` | where a trigger source left off, by name (for example the mailbox "since" time) | `cursor-set`, `cursor-clear` (the cursor is absent again) |
| `events` | triggers to handle (a notification e-mail, a calendar time), one per source and external id, with a status: `pending`, `claimed`, then `done`, `failed` or `to_inbox` | `event-add`, `event-next`, `event-done` |
| `runs` | one row per agent run (backlog R7): agent, triggering event, status, exit code, cost, tokens, duration, output folder, error | `run-start`, `run-end` |
| `inbox` | what waits for the user (backlog R5): kind, title, the payload as JSON and the approval hash the caller gave (`--payload-sha256`: the SHA-256 of what the person approves, in the sense of `contracts/environment.md`; it may be the hash of a file the payload only points to, and the store does not compare it with the payload), status `open`, then `approved`, `rejected` or `done`, and who decided when | `inbox-add`, `inbox-resolve` |
| `actions` | every outward action the runtime executed: kind, idempotency key (unique), target, payload hash, the provider's result | `action-add` |

`action-count --kind reply --since <start of day>` is how a daily limit is enforced; `actions` and `export` are the audit. `runs`, `inbox-list` and `actions` stop at `--limit` and then print `"truncated": true`; `inbox-list --id <id>` reads one item whatever its status, so an item past the limit can still be reached.

### Guarantees

- **Several writers.** WAL mode (readers never wait for the writer), a 10-second busy timeout, and every write in one `BEGIN IMMEDIATE` transaction: several agents and overlapping scheduler firings can write at once, and each verb's change is all or nothing. A write still blocked after 10 seconds fails with exit 1 and changes nothing.
- **One event per notification.** `event-add` is unique on source and external id; adding the same e-mail twice returns the first event with `"created": false`.
- **One claimant per event.** `event-next` claims inside one transaction and gives each event a fresh claim token; two overlapping ticks never receive the same event (tested with several processes). A claim older than `--reclaim-after-minutes` (default 60, at least 1) returns to pending on the next `event-next` for that source, for a run that crashed; an event already claimed 5 times whose claim expired again is not handed out a sixth time: it ends `failed` with a note, and `event-next` lists its id in `failed`. The old token is then refused by `event-done` (exit 1), so a late run cannot overwrite the new claimant's result. `event-done` with the same token and status twice is harmless (`"already": true`).
- **One open item per event and kind.** `inbox-add --event-id <id>` for an event that already has an open item of that kind returns that item with `"created": false` and adds nothing, so an event escalated twice makes one item.
- **Forward-only inbox.** `open` becomes `approved`, `rejected` or `done`; `approved` becomes `done`; nothing else. Who approved and who marked it done are kept separately.
- **One action per key.** `action-add` with a key already recorded returns the first action when kind, target and payload hash match, and fails with exit 1 when they differ.
- **External text is data.** Payloads may hold text written by other people (a comment in a notification e-mail). The store keeps the file's text exactly as given, only checks that it is UTF-8 JSON under the cap, and never interprets it. Every SQL statement is a constant with parameters.
- **Caps.** Payload and result files 64 KiB; notes, errors and cursor values 4 KiB; titles 1 KiB; external ids, targets and keys 512 bytes; names, kinds, sources, agents, triggers 128 bytes. Above a cap the verb exits 2 and stores nothing. Single-line fields refuse control characters.

### Where the database lives

Wherever `--db` or `STORE_SQLITE_PATH` points; the provider picks no default, so the runtime (or the user) decides per project. Put it outside every repository: it holds the agent's work data. `init` creates a missing folder 0700 and the file 0600, and resets the file (and its `-wal` and `-shm` files) to 0600 if it was loosened; `--check` warns when the file or its folder is readable by others.

### Usage

```sh
export STORE_SQLITE_PATH="$HOME/agent-state/social-manager.sqlite"
python3 providers/store/sqlite.py init
python3 providers/store/sqlite.py --check
python3 providers/store/sqlite.py event-add --source mailbox --external-id '<message id>' --payload-file event.json
python3 providers/store/sqlite.py event-next --source mailbox --limit 5
python3 providers/store/sqlite.py event-done --id 12 --token <claim token> --status done
python3 providers/store/sqlite.py run-start --agent social-manager --event-id 12 --trigger mailbox
python3 providers/store/sqlite.py run-end --run-id 7 --status ok --exit-code 0 --cost-usd 0.04 \
    --tokens 12000 --duration-ms 65000 --out-dir /path/to/run
python3 providers/store/sqlite.py action-count --kind reply --since 2026-09-29T00:00:00-03:00
python3 providers/store/sqlite.py export --format json --since 2026-09-28T00:00:00Z
```

`run-end` takes `null` for a number the run did not report (`timing.json` of an adapter has nulls when unknown). Every verb prints JSON; `--help` lists the verbs and their flags. Exit codes: 0 success, 1 store error (locked past the timeout, no such id, a lost claim, a conflicting key, a schema newer than the script), 2 usage error (including a value over its cap), 3 not configured (no database path, no database, or a schema that needs `init`).

### Schema changes

`init` applies the migrations the file does not have yet, in one transaction, and records each in `schema_version`; running it again changes nothing. Every other verb refuses a database whose version differs from the script's (exit 3 when older: run `init`; exit 1 when newer). A new migration is a new numbered entry in `MIGRATIONS` in `sqlite.py`, never an edit of an applied one.

### Backup

The database is one file plus its WAL. Copy it while no agent writes, or use SQLite's online backup, which is safe while others write:

```sh
sqlite3 "$STORE_SQLITE_PATH" ".backup '$HOME/agent-state/backup-$(date +%F).sqlite'"
```

Copying only the `.sqlite` file while a `-wal` file exists can miss the latest writes. `export --format json` is a readable dump, not a restorable backup.

### Tests

`uv run --with pytest==9.1.1 pytest providers/store/tests`: offline, one temporary database per test; the concurrency tests start several processes that claim events and add the same notification at once.
