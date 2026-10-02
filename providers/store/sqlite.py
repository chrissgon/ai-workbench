#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Store provider on SQLite: the agent runtime's durable state in one local database file.

Tables: cursors (where a trigger source left off), events (triggers to handle, deduplicated and
claimed atomically), runs (one row per agent run), inbox (what waits for the user) and actions
(outward actions the runtime executed, for daily limits and audit). The runtime calls this script
through its CLI, so another implementation of the `store:runtime` class can replace it (STORE_PROVIDER).

Concurrency: the database runs in WAL mode (readers never block the writer) with a 10-second busy
timeout, and every write is one BEGIN IMMEDIATE transaction, so several agents and overlapping
scheduler firings can write at once and each change is all or nothing. Claiming events happens
inside one such transaction: two processes never receive the same event.

Standard library only. Every SQL statement is a constant with ? parameters; no value is ever
formatted into SQL. Payloads may hold text written by other people (notification e-mails,
comments): the store keeps it exactly as given and never interprets it.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import secrets
import sqlite3
import stat
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA_VERSION = 1
BUSY_TIMEOUT_SECONDS = 10
PATH_ENV = "STORE_SQLITE_PATH"

# Caps, in UTF-8 bytes. Above a cap the verb stops with exit 2 and stores nothing.
PAYLOAD_MAX = 64 * 1024   # --payload-file, --result-file
NOTE_MAX = 4 * 1024       # --note, --error
VALUE_MAX = 4 * 1024      # cursor values
TITLE_MAX = 1024          # inbox titles
REF_MAX = 512             # external ids, targets, idempotency keys
LABEL_MAX = 128           # source, name, kind, agent, trigger, by
PATH_MAX = 4096           # --out-dir, --db

LIMITS = {"event-next": (1, 1, 100), "runs": (20, 1, 1000), "inbox-list": (100, 1, 1000),
          "actions": (1000, 1, 10000)}  # verb: (default, min, max) for --limit
RECLAIM_DEFAULT_MINUTES = 60
RECLAIM_MAX_MINUTES = 7 * 24 * 60

EVENT_DONE_STATUSES = ("done", "failed", "to_inbox")
RUN_END_STATUSES = ("ok", "failed", "timeout")
INBOX_STATUSES = ("open", "approved", "rejected", "done")
# inbox-resolve moves an item forward only: open -> approved | rejected | done, approved -> done.
INBOX_TRANSITIONS = {"open": ("approved", "rejected", "done"), "approved": ("done",)}

SHA256_RE = re.compile(r"[0-9a-f]{64}")
# Control characters. Single-line fields refuse all of them; notes and errors keep tab and newline.
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
CONTROL_MULTILINE_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_NOT_CONFIGURED = 0, 1, 2, 3

MIGRATIONS = {
    1: ("cursors, events, runs, inbox and actions", [
        """CREATE TABLE cursors (
            name TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL)""",
        """CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            external_id TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'claimed', 'done', 'failed', 'to_inbox')),
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            claimed_at TEXT,
            claim_token TEXT,
            finished_at TEXT,
            note TEXT,
            UNIQUE (source, external_id))""",
        "CREATE INDEX events_by_source_status ON events (source, status, id)",
        """CREATE TABLE runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent TEXT NOT NULL,
            event_id INTEGER REFERENCES events (id),
            trigger TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'running'
                CHECK (status IN ('running', 'ok', 'failed', 'timeout')),
            started_at TEXT NOT NULL,
            ended_at TEXT,
            exit_code INTEGER,
            cost_usd REAL,
            tokens INTEGER,
            duration_ms INTEGER,
            out_dir TEXT,
            error TEXT)""",
        "CREATE INDEX runs_by_agent ON runs (agent, id)",
        """CREATE TABLE inbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            event_id INTEGER REFERENCES events (id),
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'approved', 'rejected', 'done')),
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            resolved_by TEXT,
            resolve_note TEXT,
            done_at TEXT,
            done_by TEXT,
            done_note TEXT)""",
        "CREATE INDEX inbox_by_status ON inbox (status, id)",
        """CREATE TABLE actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            idempotency_key TEXT NOT NULL UNIQUE,
            target TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            result TEXT NOT NULL,
            created_at TEXT NOT NULL)""",
        "CREATE INDEX actions_by_kind_time ON actions (kind, created_at)",
    ]),
}

HELP_EPILOG = f"""\
database:
  --db <path> on every verb, or {PATH_ENV}. Neither: exit 3. The file is
  created by init with mode 0600; a missing folder is created 0700. WAL
  mode, busy timeout {BUSY_TIMEOUT_SECONDS} s. Every verb except init needs a database at the
  current schema version (exit 3 otherwise: run init).

verbs:
  init            create the schema or migrate it to version {SCHEMA_VERSION}; idempotent
  cursor-get      --name <n>                                  -> {{name, value|null, updated_at}}
  cursor-set      --name <n> --value <v>
  event-add       --source <s> --external-id <id> --payload-file <json>
                  -> {{id, created}}; the same source and external id is one event
  event-next      --source <s> [--limit n] [--reclaim-after-minutes m]
                  claims up to n pending events (default 1): status claimed,
                  a claim token per event. Claims older than m minutes
                  (default {RECLAIM_DEFAULT_MINUTES}) return to pending first.
  event-done      --id <id> --token <claim token> --status done|failed|to_inbox [--note <t>]
                  exit 1 when the claim was lost (reclaimed, or finished)
  run-start       --agent <a> --event-id <id|none> --trigger <t>  -> {{run_id}}
  run-end         --run-id <id> --status ok|failed|timeout --exit-code <n|null>
                  --cost-usd <x|null> --tokens <n|null> --duration-ms <n|null>
                  --out-dir <path> [--error <text>]
  runs            [--limit n] [--agent <a>]                   newest first
  inbox-add       --kind <k> --title <t> --payload-file <json> --payload-sha256 <hex>
                  [--event-id <id>]                           -> {{id}}
  inbox-list      [--status open|approved|rejected|done|all] (default open) [--limit n]
  inbox-resolve   --id <id> --status approved|rejected|done --by <who> [--note <t>]
                  open -> approved|rejected|done, approved -> done; nothing else
  action-add      --kind <k> --idempotency-key <k> --target <urn> --payload-sha256 <hex>
                  --result-file <json>   -> {{id, created}}; a key is recorded once
  actions         --since <ISO-8601> [--kind <k>] [--limit n]
  action-count    --kind <k> --since <ISO-8601>              -> {{kind, since, count}}
  export          --format json [--since <ISO-8601>]         every table, for review

caps (UTF-8 bytes; above a cap: exit 2, nothing stored):
  payload and result files {PAYLOAD_MAX}; notes, errors and cursor values {NOTE_MAX};
  titles {TITLE_MAX}; external ids, targets, keys {REF_MAX}; labels {LABEL_MAX}.
  Payload and result files must be UTF-8 JSON. They are stored exactly as given.

output: JSON on stdout; diagnostics on stderr. Times are UTC, ISO-8601 with Z.
  A --since without an offset is local time.

exit codes: 0 success, 1 store error (database locked past the timeout, no
  such id, a lost claim, a conflicting key), 2 usage error, 3 not configured.

examples:
  python3 providers/store/sqlite.py init --db ~/agent-state/social.sqlite
  export {PATH_ENV}=~/agent-state/social.sqlite
  python3 providers/store/sqlite.py --check
  python3 providers/store/sqlite.py event-add --source mailbox --external-id '<id@mail>' \\
      --payload-file event.json
  python3 providers/store/sqlite.py event-next --source mailbox --limit 5
  python3 providers/store/sqlite.py action-count --kind reply --since 2026-09-29T00:00:00-03:00
"""


class StoreError(Exception):
    """An error with an exit code and a one-line message for stderr."""

    def __init__(self, message: str, code: int = EXIT_ERROR):
        super().__init__(message)
        self.code = code


def log(message: str) -> None:
    print(message, file=sys.stderr)


def emit(data) -> int:
    # ASCII escapes keep the output valid wherever stdout's encoding is not UTF-8.
    print(json.dumps(data, indent=2, ensure_ascii=True))
    return EXIT_OK


# --- time -----------------------------------------------------------------------


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    """Fixed-width UTC ISO-8601, so stored times compare correctly as text."""
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def since_arg(value: str | None, flag: str = "--since") -> str | None:
    """Parse ISO-8601; Z means UTC; a value without offset is local time."""
    if value is None:
        return None
    raw = value.strip()
    if raw.endswith(("Z", "z")):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        raise StoreError(f"{flag} is not an ISO-8601 time: {value!r}", EXIT_USAGE) from None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return iso(parsed)


# --- argument checks --------------------------------------------------------------


def text_arg(value: str | None, flag: str, cap: int, multiline: bool = False, required: bool = True) -> str | None:
    if value is None:
        if required:
            raise StoreError(f"{flag} is required", EXIT_USAGE)
        return None
    if not value.strip():
        raise StoreError(f"{flag} is empty", EXIT_USAGE)
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        raise StoreError(f"{flag} is not valid UTF-8", EXIT_USAGE) from None
    if size > cap:
        raise StoreError(f"{flag} is {size} bytes; the cap is {cap}", EXIT_USAGE)
    if (CONTROL_MULTILINE_RE if multiline else CONTROL_RE).search(value):
        raise StoreError(f"{flag} contains a control character", EXIT_USAGE)
    return value


def sha_arg(value: str) -> str:
    digest = (value or "").strip().lower()
    if not SHA256_RE.fullmatch(digest):
        raise StoreError("--payload-sha256 must be 64 hexadecimal characters (a SHA-256 digest)", EXIT_USAGE)
    return digest


def limit_arg(value: int | None, verb: str) -> int:
    default, low, high = LIMITS[verb]
    if value is None:
        return default
    if not low <= value <= high:
        raise StoreError(f"--limit must be between {low} and {high}", EXIT_USAGE)
    return value


def id_arg(value: str, flag: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise StoreError(f"{flag} must be a positive integer", EXIT_USAGE) from None
    if number < 1:
        raise StoreError(f"{flag} must be a positive integer", EXIT_USAGE)
    return number


def nullable_number(value: str, flag: str, kind: type) -> int | float | None:
    """A number, or the literal null (or none) when the caller does not know it."""
    if value is None:
        raise StoreError(f"{flag} is required (use null when unknown)", EXIT_USAGE)
    if value.strip().lower() in ("null", "none"):
        return None
    try:
        number = kind(value)
    except ValueError:
        raise StoreError(f"{flag} must be a number or null", EXIT_USAGE) from None
    if kind is float and not math.isfinite(number):
        raise StoreError(f"{flag} must be finite", EXIT_USAGE)
    if flag != "--exit-code" and number < 0:
        raise StoreError(f"{flag} must not be negative", EXIT_USAGE)
    return number


def reject_constant(name: str):
    raise ValueError(f"{name} is not valid JSON")


def json_file(path_arg: str | None, flag: str) -> str:
    """The file's text, exactly as given, after checking it is UTF-8 JSON under the payload cap."""
    if not path_arg:
        raise StoreError(f"{flag} is required", EXIT_USAGE)
    try:
        with open(path_arg, "rb") as f:
            data = f.read(PAYLOAD_MAX + 1)
    except OSError as exc:
        raise StoreError(f"{flag}: cannot read {path_arg}: {exc.strerror}", EXIT_USAGE) from None
    if len(data) > PAYLOAD_MAX:
        raise StoreError(f"{flag}: the file is over the cap of {PAYLOAD_MAX} bytes", EXIT_USAGE)
    try:
        text = data.decode("utf-8")
        json.loads(text, parse_constant=reject_constant)
    except (UnicodeDecodeError, ValueError) as exc:
        raise StoreError(f"{flag}: not UTF-8 JSON ({exc})", EXIT_USAGE) from None
    return text


# --- database ---------------------------------------------------------------------


def db_path(args) -> Path:
    value = getattr(args, "db", None) or os.environ.get(PATH_ENV)
    if not value:
        raise StoreError(f"no database: pass --db <path> or set {PATH_ENV}", EXIT_NOT_CONFIGURED)
    text_arg(value, "--db", PATH_MAX)
    if value.strip() == ":memory:" or value.startswith("file:"):
        raise StoreError("--db must be a file path", EXIT_USAGE)
    return Path(value).expanduser().resolve()


def connect(path: Path) -> sqlite3.Connection:
    # isolation_level=None: no implicit transactions; writes open BEGIN IMMEDIATE themselves.
    conn = sqlite3.connect(str(path), timeout=BUSY_TIMEOUT_SECONDS, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def write(conn: sqlite3.Connection):
    """One write transaction. BEGIN IMMEDIATE takes the write lock up front, so a read inside
    the transaction cannot be overtaken by another writer before its update."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def enable_wal(conn: sqlite3.Connection) -> str:
    """Switch to WAL (persistent in the file). The switch needs an exclusive lock and SQLite may
    answer "locked" at once instead of waiting, when another process is initialising the same
    file: retry until the busy timeout."""
    deadline = time.monotonic() + BUSY_TIMEOUT_SECONDS
    while True:
        try:
            return conn.execute("PRAGMA journal_mode = WAL").fetchone()[0]
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc) or time.monotonic() > deadline:
                raise
            time.sleep(0.05)


def schema_version(conn: sqlite3.Connection) -> int | None:
    found = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_version'").fetchone()
    if not found:
        return None
    return conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()[0]


def private_files(path: Path) -> None:
    """The database and its WAL and shared-memory files are readable by the user only. SQLite removes
    the WAL and shared-memory files when the last connection closes, so another process may delete one
    between the listing and the chmod: a file that is gone needs no mode."""
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        try:
            os.chmod(candidate, 0o600)
        except FileNotFoundError:
            pass


def open_ready(args) -> sqlite3.Connection:
    """A connection to an existing database at the current schema version."""
    path = db_path(args)
    if not path.is_file():
        raise StoreError(f"no database at {path}: run init first", EXIT_NOT_CONFIGURED)
    conn = connect(path)
    version = schema_version(conn)
    if version is None or version < SCHEMA_VERSION:
        raise StoreError(f"{path} is at schema version {version or 0}, this script needs {SCHEMA_VERSION}: "
                         "run init to migrate", EXIT_NOT_CONFIGURED)
    if version > SCHEMA_VERSION:
        raise StoreError(f"{path} is at schema version {version}, newer than this script ({SCHEMA_VERSION}): "
                         "update the workbench", EXIT_ERROR)
    return conn


def event_exists(conn: sqlite3.Connection, event_id: int | None) -> None:
    if event_id is not None and not conn.execute("SELECT 1 FROM events WHERE id = ?", (event_id,)).fetchone():
        raise StoreError(f"no event {event_id}", EXIT_ERROR)


def row_dict(row: sqlite3.Row, json_fields: tuple[str, ...] = (), drop: tuple[str, ...] = ()) -> dict:
    out = {key: row[key] for key in row.keys() if key not in drop}
    for key in json_fields:
        if out.get(key) is not None:
            out[key] = json.loads(out[key])
    return out


# --- verbs ------------------------------------------------------------------------


def cmd_check(args) -> int:
    path = db_path(args)
    if not path.is_file():
        raise StoreError(f"no database at {path}: run init first", EXIT_NOT_CONFIGURED)
    conn = open_ready(args)
    quick = conn.execute("PRAGMA quick_check").fetchone()[0]
    if quick != "ok":
        raise StoreError(f"{path} failed the integrity check: {quick}", EXIT_ERROR)
    journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
    file_mode = stat.S_IMODE(path.stat().st_mode)
    folder_mode = stat.S_IMODE(path.parent.stat().st_mode)
    if file_mode & 0o077:
        log(f"warning: {path} is mode {file_mode:04o}; run init or chmod 600 it")
    if folder_mode & 0o077:
        log(f"warning: {path.parent} is mode {folder_mode:04o}; others can list it (0700 recommended)")
    return emit({
        "ok": True, "db": str(path), "schema_version": SCHEMA_VERSION, "journal_mode": journal,
        "file_mode": f"{file_mode:04o}", "folder_mode": f"{folder_mode:04o}",
        "pending_events": conn.execute("SELECT COUNT(*) FROM events WHERE status = 'pending'").fetchone()[0],
        "open_inbox": conn.execute("SELECT COUNT(*) FROM inbox WHERE status = 'open'").fetchone()[0],
    })


def cmd_init(args) -> int:
    path = db_path(args)
    if not path.parent.exists():
        path.parent.mkdir(mode=0o700, parents=True)  # the umask of main() makes parents 0700 too
    created = not path.exists()
    conn = connect(path)
    private_files(path)
    journal = enable_wal(conn)
    applied = []
    with write(conn):
        conn.execute("CREATE TABLE IF NOT EXISTS schema_version ("
                     "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL, description TEXT NOT NULL)")
        current = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()[0]
        if current > SCHEMA_VERSION:
            raise StoreError(f"{path} is at schema version {current}, newer than this script ({SCHEMA_VERSION})")
        for version in sorted(MIGRATIONS):
            if version <= current:
                continue
            description, statements = MIGRATIONS[version]
            for statement in statements:
                conn.execute(statement)
            conn.execute("INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
                         (version, iso(utcnow()), description))
            applied.append(version)
    private_files(path)
    return emit({"db": str(path), "created": created, "schema_version": SCHEMA_VERSION,
                 "migrated_from": current, "applied": applied, "journal_mode": journal})


def cmd_cursor_get(args) -> int:
    name = text_arg(args.name, "--name", LABEL_MAX)
    conn = open_ready(args)
    row = conn.execute("SELECT name, value, updated_at FROM cursors WHERE name = ?", (name,)).fetchone()
    return emit(row_dict(row) if row else {"name": name, "value": None, "updated_at": None})


def cmd_cursor_set(args) -> int:
    name = text_arg(args.name, "--name", LABEL_MAX)
    value = text_arg(args.value, "--value", VALUE_MAX)
    conn = open_ready(args)
    now = iso(utcnow())
    with write(conn):
        conn.execute("INSERT INTO cursors (name, value, updated_at) VALUES (?, ?, ?) "
                     "ON CONFLICT (name) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                     (name, value, now))
    return emit({"name": name, "value": value, "updated_at": now})


def cmd_event_add(args) -> int:
    source = text_arg(args.source, "--source", LABEL_MAX)
    external_id = text_arg(args.external_id, "--external-id", REF_MAX)
    payload = json_file(args.payload_file, "--payload-file")
    conn = open_ready(args)
    with write(conn):
        cur = conn.execute(
            "INSERT INTO events (source, external_id, payload, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (source, external_id) DO NOTHING", (source, external_id, payload, iso(utcnow())))
        created = cur.rowcount == 1
        row = conn.execute("SELECT id, status FROM events WHERE source = ? AND external_id = ?",
                           (source, external_id)).fetchone()
    return emit({"id": row["id"], "created": created, "status": row["status"]})


def cmd_event_next(args) -> int:
    source = text_arg(args.source, "--source", LABEL_MAX)
    limit = limit_arg(args.limit, "event-next")
    minutes = args.reclaim_after_minutes
    if not 0 <= minutes <= RECLAIM_MAX_MINUTES:
        raise StoreError(f"--reclaim-after-minutes must be between 0 and {RECLAIM_MAX_MINUTES}", EXIT_USAGE)
    conn = open_ready(args)
    now = utcnow()
    claimed = []
    with write(conn):
        reclaimed = conn.execute(
            "UPDATE events SET status = 'pending', claim_token = NULL, claimed_at = NULL "
            "WHERE source = ? AND status = 'claimed' AND claimed_at < ?",
            (source, iso(now - timedelta(minutes=minutes)))).rowcount
        ids = [r["id"] for r in conn.execute(
            "SELECT id FROM events WHERE source = ? AND status = 'pending' ORDER BY id LIMIT ?", (source, limit))]
        for event_id in ids:
            conn.execute("UPDATE events SET status = 'claimed', claim_token = ?, claimed_at = ?, "
                         "attempts = attempts + 1 WHERE id = ? AND status = 'pending'",
                         (secrets.token_hex(16), iso(now), event_id))
            row = conn.execute("SELECT id, source, external_id, payload, attempts, created_at, claimed_at, "
                               "claim_token FROM events WHERE id = ?", (event_id,)).fetchone()
            claimed.append(row_dict(row, ("payload",)))
    return emit({"source": source, "events": claimed, "reclaimed": reclaimed})


def cmd_event_done(args) -> int:
    event_id = id_arg(args.id, "--id")
    token = text_arg(args.token, "--token", LABEL_MAX)
    note = text_arg(args.note, "--note", NOTE_MAX, multiline=True, required=False)
    conn = open_ready(args)
    now = iso(utcnow())
    with write(conn):
        updated = conn.execute(
            "UPDATE events SET status = ?, finished_at = ?, note = ? "
            "WHERE id = ? AND status = 'claimed' AND claim_token = ?",
            (args.status, now, note, event_id, token)).rowcount
        row = conn.execute("SELECT status, claim_token, finished_at FROM events WHERE id = ?", (event_id,)).fetchone()
    if row is None:
        raise StoreError(f"no event {event_id}")
    if not updated:
        if row["status"] == args.status and row["claim_token"] == token:
            return emit({"id": event_id, "status": row["status"], "finished_at": row["finished_at"],
                         "already": True})
        raise StoreError(f"event {event_id}: the claim was lost (status {row['status']}); it was reclaimed "
                         "after the timeout or finished with another token, so this result is not recorded")
    return emit({"id": event_id, "status": args.status, "finished_at": now, "already": False})


def cmd_run_start(args) -> int:
    agent = text_arg(args.agent, "--agent", LABEL_MAX)
    trigger = text_arg(args.trigger, "--trigger", LABEL_MAX)
    raw_event = text_arg(args.event_id, "--event-id", LABEL_MAX)
    event_id = None if raw_event.strip().lower() == "none" else id_arg(raw_event, "--event-id")
    conn = open_ready(args)
    now = iso(utcnow())
    with write(conn):
        event_exists(conn, event_id)
        run_id = conn.execute("INSERT INTO runs (agent, event_id, trigger, started_at) VALUES (?, ?, ?, ?)",
                              (agent, event_id, trigger, now)).lastrowid
    return emit({"run_id": run_id, "agent": agent, "event_id": event_id, "started_at": now})


def cmd_run_end(args) -> int:
    run_id = id_arg(args.run_id, "--run-id")
    exit_code = nullable_number(args.exit_code, "--exit-code", int)
    cost = nullable_number(args.cost_usd, "--cost-usd", float)
    tokens = nullable_number(args.tokens, "--tokens", int)
    duration = nullable_number(args.duration_ms, "--duration-ms", int)
    out_dir = text_arg(args.out_dir, "--out-dir", PATH_MAX)
    error = text_arg(args.error, "--error", NOTE_MAX, multiline=True, required=False)
    conn = open_ready(args)
    now = iso(utcnow())
    with write(conn):
        updated = conn.execute(
            "UPDATE runs SET status = ?, ended_at = ?, exit_code = ?, cost_usd = ?, tokens = ?, duration_ms = ?, "
            "out_dir = ?, error = ? WHERE id = ? AND status = 'running'",
            (args.status, now, exit_code, cost, tokens, duration, out_dir, error, run_id)).rowcount
        row = conn.execute("SELECT status FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise StoreError(f"no run {run_id}")
    if not updated:
        raise StoreError(f"run {run_id} already ended with status {row['status']}")
    return emit({"run_id": run_id, "status": args.status, "ended_at": now})


def cmd_runs(args) -> int:
    agent = text_arg(args.agent, "--agent", LABEL_MAX, required=False)
    limit = limit_arg(args.limit, "runs")
    conn = open_ready(args)
    rows = conn.execute("SELECT * FROM runs WHERE (? IS NULL OR agent = ?) ORDER BY id DESC LIMIT ?",
                        (agent, agent, limit)).fetchall()
    return emit({"runs": [row_dict(r) for r in rows]})


def cmd_inbox_add(args) -> int:
    kind = text_arg(args.kind, "--kind", LABEL_MAX)
    title = text_arg(args.title, "--title", TITLE_MAX)
    payload = json_file(args.payload_file, "--payload-file")
    digest = sha_arg(args.payload_sha256)
    event_id = id_arg(args.event_id, "--event-id") if args.event_id is not None else None
    conn = open_ready(args)
    now = iso(utcnow())
    with write(conn):
        event_exists(conn, event_id)
        item_id = conn.execute(
            "INSERT INTO inbox (kind, title, payload, payload_sha256, event_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)", (kind, title, payload, digest, event_id, now)).lastrowid
    return emit({"id": item_id, "status": "open", "created_at": now})


def cmd_inbox_list(args) -> int:
    limit = limit_arg(args.limit, "inbox-list")
    conn = open_ready(args)
    rows = conn.execute("SELECT * FROM inbox WHERE (? = 'all' OR status = ?) ORDER BY id LIMIT ?",
                        (args.status, args.status, limit)).fetchall()
    return emit({"status": args.status, "items": [row_dict(r, ("payload",)) for r in rows]})


def cmd_inbox_resolve(args) -> int:
    item_id = id_arg(args.id, "--id")
    by = text_arg(args.by, "--by", LABEL_MAX)
    note = text_arg(args.note, "--note", NOTE_MAX, multiline=True, required=False)
    conn = open_ready(args)
    now = iso(utcnow())
    with write(conn):
        row = conn.execute("SELECT status FROM inbox WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise StoreError(f"no inbox item {item_id}")
        current = row["status"]
        if args.status not in INBOX_TRANSITIONS.get(current, ()):
            raise StoreError(f"inbox item {item_id} is {current}; it cannot become {args.status} "
                             "(open -> approved|rejected|done, approved -> done)")
        if current == "open":
            conn.execute("UPDATE inbox SET status = ?, resolved_at = ?, resolved_by = ?, resolve_note = ? "
                         "WHERE id = ? AND status = 'open'", (args.status, now, by, note, item_id))
        if args.status == "done":
            conn.execute("UPDATE inbox SET status = 'done', done_at = ?, done_by = ?, done_note = ? WHERE id = ?",
                         (now, by, note, item_id))
    return emit({"id": item_id, "status": args.status, "previous": current, "at": now, "by": by})


def cmd_action_add(args) -> int:
    kind = text_arg(args.kind, "--kind", LABEL_MAX)
    key = text_arg(args.idempotency_key, "--idempotency-key", REF_MAX)
    target = text_arg(args.target, "--target", REF_MAX)
    digest = sha_arg(args.payload_sha256)
    result = json_file(args.result_file, "--result-file")
    conn = open_ready(args)
    with write(conn):
        created = conn.execute(
            "INSERT INTO actions (kind, idempotency_key, target, payload_sha256, result, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (idempotency_key) DO NOTHING",
            (kind, key, target, digest, result, iso(utcnow()))).rowcount == 1
        row = conn.execute("SELECT id, kind, target, payload_sha256, created_at FROM actions "
                           "WHERE idempotency_key = ?", (key,)).fetchone()
    if not created and (row["kind"], row["target"], row["payload_sha256"]) != (kind, target, digest):
        raise StoreError(f"idempotency key {key!r} is already recorded for a different action "
                         f"(action {row['id']}: {row['kind']} on {row['target']})")
    return emit({"id": row["id"], "created": created, "created_at": row["created_at"]})


def cmd_actions(args) -> int:
    since = since_arg(args.since)
    kind = text_arg(args.kind, "--kind", LABEL_MAX, required=False)
    limit = limit_arg(args.limit, "actions")
    conn = open_ready(args)
    rows = conn.execute("SELECT * FROM actions WHERE created_at >= ? AND (? IS NULL OR kind = ?) "
                        "ORDER BY id LIMIT ?", (since, kind, kind, limit)).fetchall()
    return emit({"since": since, "kind": kind, "actions": [row_dict(r, ("result",)) for r in rows]})


def cmd_action_count(args) -> int:
    kind = text_arg(args.kind, "--kind", LABEL_MAX)
    since = since_arg(args.since)
    conn = open_ready(args)
    count = conn.execute("SELECT COUNT(*) FROM actions WHERE kind = ? AND created_at >= ?",
                         (kind, since)).fetchone()[0]
    return emit({"kind": kind, "since": since, "count": count})


EXPORT_QUERIES = (
    # (table, query, JSON fields, dropped fields); ? is --since, or NULL for everything.
    ("cursors", "SELECT * FROM cursors WHERE ?1 IS NULL OR updated_at >= ?1 ORDER BY name", (), ()),
    ("events", "SELECT * FROM events WHERE ?1 IS NULL OR created_at >= ?1 OR claimed_at >= ?1 "
     "OR finished_at >= ?1 ORDER BY id", ("payload",), ("claim_token",)),
    ("runs", "SELECT * FROM runs WHERE ?1 IS NULL OR started_at >= ?1 OR ended_at >= ?1 ORDER BY id", (), ()),
    ("inbox", "SELECT * FROM inbox WHERE ?1 IS NULL OR created_at >= ?1 OR resolved_at >= ?1 OR done_at >= ?1 "
     "ORDER BY id", ("payload",), ()),
    ("actions", "SELECT * FROM actions WHERE ?1 IS NULL OR created_at >= ?1 ORDER BY id", ("result",), ()),
)


def cmd_export(args) -> int:
    since = since_arg(args.since)
    conn = open_ready(args)
    out = {"exported_at": iso(utcnow()), "db": str(db_path(args)), "schema_version": SCHEMA_VERSION,
           "since": since}
    conn.execute("BEGIN")  # one read snapshot for every table
    try:
        for table, query, json_fields, drop in EXPORT_QUERIES:
            out[table] = [row_dict(r, json_fields, drop) for r in conn.execute(query, (since,))]
    finally:
        conn.execute("COMMIT")
    return emit(out)


# --- entry point ------------------------------------------------------------------


VERBS = {
    "init": cmd_init, "cursor-get": cmd_cursor_get, "cursor-set": cmd_cursor_set,
    "event-add": cmd_event_add, "event-next": cmd_event_next, "event-done": cmd_event_done,
    "run-start": cmd_run_start, "run-end": cmd_run_end, "runs": cmd_runs,
    "inbox-add": cmd_inbox_add, "inbox-list": cmd_inbox_list, "inbox-resolve": cmd_inbox_resolve,
    "action-add": cmd_action_add, "actions": cmd_actions, "action-count": cmd_action_count,
    "export": cmd_export,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sqlite.py",
        description="Store provider on SQLite: cursors, events, runs, inbox and actions of the agent runtime "
        "in one local database file.",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--check", action="store_true",
                        help="verify the database is reachable and at the current schema version; changes nothing")
    parser.add_argument("--db", help=f"database file (default ${PATH_ENV})")
    common = argparse.ArgumentParser(add_help=False)
    # SUPPRESS keeps a --db given before the verb when none is given after it.
    common.add_argument("--db", default=argparse.SUPPRESS, help=f"database file (default ${PATH_ENV})")
    sub = parser.add_subparsers(dest="verb", metavar="verb")

    def verb(name: str, help_text: str) -> argparse.ArgumentParser:
        return sub.add_parser(name, parents=[common], help=help_text)

    verb("init", "create or migrate the schema (idempotent)")
    p = verb("cursor-get", "read a cursor")
    p.add_argument("--name")
    p = verb("cursor-set", "write a cursor")
    p.add_argument("--name")
    p.add_argument("--value")
    p = verb("event-add", "record a trigger once per source and external id")
    p.add_argument("--source")
    p.add_argument("--external-id")
    p.add_argument("--payload-file")
    p = verb("event-next", "claim pending events atomically")
    p.add_argument("--source")
    p.add_argument("--limit", type=int)
    p.add_argument("--reclaim-after-minutes", type=int, default=RECLAIM_DEFAULT_MINUTES)
    p = verb("event-done", "finish a claimed event")
    p.add_argument("--id")
    p.add_argument("--token")
    p.add_argument("--status", choices=EVENT_DONE_STATUSES, required=True)
    p.add_argument("--note")
    p = verb("run-start", "record the start of an agent run")
    p.add_argument("--agent")
    p.add_argument("--event-id")
    p.add_argument("--trigger")
    p = verb("run-end", "record the end of an agent run")
    p.add_argument("--run-id")
    p.add_argument("--status", choices=RUN_END_STATUSES, required=True)
    p.add_argument("--exit-code")
    p.add_argument("--cost-usd")
    p.add_argument("--tokens")
    p.add_argument("--duration-ms")
    p.add_argument("--out-dir")
    p.add_argument("--error")
    p = verb("runs", "list runs, newest first")
    p.add_argument("--limit", type=int)
    p.add_argument("--agent")
    p = verb("inbox-add", "put an item in the user's inbox")
    p.add_argument("--kind")
    p.add_argument("--title")
    p.add_argument("--payload-file")
    p.add_argument("--payload-sha256")
    p.add_argument("--event-id")
    p = verb("inbox-list", "list inbox items")
    p.add_argument("--status", choices=(*INBOX_STATUSES, "all"), default="open")
    p.add_argument("--limit", type=int)
    p = verb("inbox-resolve", "record the user's decision on an inbox item")
    p.add_argument("--id")
    p.add_argument("--status", choices=("approved", "rejected", "done"), required=True)
    p.add_argument("--by")
    p.add_argument("--note")
    p = verb("action-add", "record an outward action the runtime executed")
    p.add_argument("--kind")
    p.add_argument("--idempotency-key")
    p.add_argument("--target")
    p.add_argument("--payload-sha256")
    p.add_argument("--result-file")
    p = verb("actions", "list actions since a time")
    p.add_argument("--since", required=True)
    p.add_argument("--kind")
    p.add_argument("--limit", type=int)
    p = verb("action-count", "count actions of a kind since a time")
    p.add_argument("--kind")
    p.add_argument("--since", required=True)
    p = verb("export", "dump every table as JSON")
    p.add_argument("--format", choices=("json",), required=True)
    p.add_argument("--since")
    return parser


def main(argv: list[str] | None = None) -> int:
    os.umask(0o077)  # the database, its WAL files and a new folder are private to the user
    args = build_parser().parse_args(argv)
    try:
        if args.check:
            if args.verb:
                raise StoreError("--check takes no verb", EXIT_USAGE)
            return cmd_check(args)
        if not args.verb:
            raise StoreError("give a verb or --check; see --help", EXIT_USAGE)
        return VERBS[args.verb](args)
    except StoreError as exc:
        log(f"error: {exc}")
        return exc.code
    except sqlite3.Error as exc:
        log(f"error: database: {exc}")
        return EXIT_ERROR
    except OSError as exc:
        log(f"error: {exc.strerror or exc}: {exc.filename or ''}".rstrip(": "))
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
