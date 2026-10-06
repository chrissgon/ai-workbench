#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The mirror of tasks to and from the project's task board (class integration:issue-tracker).

The board is where a person sees the tasks and edits them. It owns what a person edits on an item: its title, its
text, its state and its comments. Everything else stays in the store and is only shown on the item ("shown"
fields, written by the runtime and never read back). Only code talks to the board: a run never sees it.

  pull(ctx)                   the board to the store. Each item whose version changed is read once: a title or a
                              text the person edited reaches the store (store.task_edit); a state the person set is
                              taken only when it is one of three moves (below), any other is refused and written back
                              by the next push; open comments are saved (store.comments_save) and change nothing by
                              themselves. An item no task knows becomes a request waiting for the person's
                              acceptance (store.request_from_board).
  push(ctx, dry_run=False)    the store to the board, oldest first: an item is written only when what would be
                              written changed since the last write; a title and a text are written only when the item
                              is created, never after (they are the person's). With dry_run, every write is printed
                              by the provider (upsert --dry-run) and nothing changes.

The three moves a person may make on the board:
  ready      on a task that is failed or blocked: it is retried (store.task_retry)
  cancelled  on a request that is not final: it is cancelled with what is open under it (store.request_cancel)
  done       on a task waiting on a review: the review is released (store.pending_resolve, by "board")

The bounds of the writes: they are the project configuration's task_board object, inside the file whose hash the
person accepted (every operation checks it). A provider other than `local` is written to only until the day its
`expires` names (UTC), included.

Usage (a library; the shell is runtime/cli.py sync): python3 runtime/board.py --help

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

CLASS = "integration:issue-tracker"
TIMEOUT = 120
STDERR_CHARS = 1000
SHOWN_CHARS = 300
NO_DEPENDENCIES = re.compile(r'^# dependencies = \[\]\s*$', re.M)
FINAL = ("done", "cancelled")


class BoardError(Exception):
    """A call to the task-board provider failed: kind is "not configured" (exit 3), "failed" or "bounds"."""

    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


def enabled(cfg: dict) -> bool:
    return cfg.get("task_board") is not None


def _resolver(root: str):
    name = "workbench_board_resolve"
    path = os.path.join(root, "providers", "resolve.py")
    module = sys.modules.get(name)
    if module is None or getattr(module, "__file__", None) != path:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


def provider_argv(cfg: dict, root: str) -> list:
    """The command that starts the implementation the configuration names: with this interpreter when its header
    declares `dependencies = []`, else with `uv run`."""
    resolve = _resolver(root)
    try:
        found = resolve.resolve(CLASS, root=root, implementation=cfg["task_board"]["provider"])
    except (resolve.UnknownClass, resolve.Unresolved) as e:
        raise BoardError("not configured", str(e)) from None
    try:
        with open(found["path"], encoding="utf-8") as f:
            header = f.read(4096)
    except OSError as e:
        raise BoardError("not configured", f"{found['path']}: {e.strerror}") from None
    if NO_DEPENDENCIES.search(header):
        return [sys.executable, found["path"]]
    return ["uv", "run", found["path"]]


def call(cfg: dict, root: str, verb: str, args: list, timeout: int = TIMEOUT) -> dict:
    """Run one verb of the provider with the task_board object in a temporary file of mode 0600 (deleted after),
    and return the one JSON object it prints."""
    argv = provider_argv(cfg, root)
    fd, config_file = tempfile.mkstemp(prefix="board-", suffix=".json")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg["task_board"], f)
        words = [verb] if verb else []
        try:
            done = subprocess.run(argv + words + ["--config-file", config_file] + list(args), capture_output=True,
                                  text=True, timeout=timeout, check=False)
        except (OSError, subprocess.SubprocessError) as e:
            raise BoardError("failed", f"the provider could not be run: {type(e).__name__}") from None
    finally:
        try:
            os.unlink(config_file)
        except OSError:
            pass
    if done.returncode == 3:
        raise BoardError("not configured", done.stderr.strip()[:STDERR_CHARS])
    if done.returncode != 0:
        raise BoardError("failed", done.stderr.strip()[:STDERR_CHARS])
    try:
        out = json.loads(done.stdout)
    except ValueError:
        raise BoardError("failed", "the provider did not print one JSON object") from None
    if not isinstance(out, dict):
        raise BoardError("failed", "the provider did not print one JSON object")
    return out


def _line(value) -> str:
    text = "" if value is None else str(value)
    return " ".join(text.split())[:SHOWN_CHARS]


def item_payload(task: dict, pending, create: bool = False) -> dict:
    """What the runtime writes to a task's item: {"state", "shown": {...}}, every shown value one line of text;
    with create (the item does not exist yet), also its title and text, which are never written again."""
    waiting = f"{pending['kind']} {pending['id']}" if pending else ""
    payload = {"state": task["state"], "shown": {
        "task": _line(task["id"]), "request": _line(task.get("parent_id")), "flow": _line(task.get("flow")),
        "key": _line(task.get("key")), "skill": _line(task.get("skill")),
        "depends_on": _line(", ".join(str(d) for d in task.get("depends_on") or [])),
        "milestone": "yes" if task.get("milestone") else "no", "waiting_for": waiting, "note": _line(task.get("note"))}}
    if create:
        payload["title"] = task["title"]
        payload["text"] = task["text"]
    return payload


def payload_hash(payload: dict) -> str:
    """The sha256 of what the runtime owns on an item (its state and shown fields): a title and a text, written
    once at creation, are left out, so that an unchanged task is never written again."""
    owned = {k: payload[k] for k in ("state", "shown")}
    return hashlib.sha256(json.dumps(owned, sort_keys=True).encode("utf-8")).hexdigest()


def _bounds_problem(cfg: dict, today=None):
    """Why a write to the board is not allowed now, or None: a provider other than local writes only until the day
    its expires names, included (UTC)."""
    board = cfg["task_board"]
    if board.get("provider") == "local":
        return None
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    try:
        expires = datetime.date.fromisoformat(str(board.get("expires")))
    except ValueError:
        return "task_board.expires is not a date"
    if today > expires:
        return (f"the bounds of writing to the task board expired on {expires.isoformat()}: change expires in "
                "docs/workbench/runtime.json and accept the new hash")
    return None


def _open_pending(ctx: dict, task_id: int):
    found = ctx["store"].pending_list(ctx["conn"], "open", task_id)
    return found[0] if found else None


def pull(ctx: dict) -> dict:
    """The board to the store (see the module's text). Returns {"pulled", "created", "edited", "refused", "gone"}."""
    cfg, store, conn, root = ctx["cfg"], ctx["store"], ctx["conn"], ctx["root"]
    out = {"pulled": [], "created": [], "edited": [], "refused": [], "gone": []}
    listed = {item["id"]: item for item in call(cfg, root, "list", []).get("items", [])}
    tasks = store.tasks_list(conn)
    known = {t["remote_id"]: t for t in tasks if t.get("remote_id")}
    for remote_id, task in known.items():
        item = listed.get(remote_id)
        if item is None or item.get("archived"):
            out["gone"].append(task["id"])
            continue
        if item.get("version") == task.get("remote_version"):
            continue
        try:
            got = call(cfg, root, "get", ["--id", remote_id])
        except BoardError as e:
            out["refused"].append({"task": task["id"], "reason": str(e)})
            continue
        out["pulled"].append(task["id"])
        written = task.get("remote_written_sha256")
        edit = {}
        if got.get("title") and got["title"] != task["title"]:
            edit["title"] = got["title"]
        if got.get("text") and got["text"] != task["text"]:
            edit["text"] = got["text"]
        if edit:
            try:
                store.task_edit(conn, task["id"], by="board", **edit)
                out["edited"].append(task["id"])
            except store.StoreError as e:
                out["refused"].append({"task": task["id"], "reason": str(e)})
        state = got.get("state")
        if state != task["state"]:
            reason = _take_state(ctx, task, state)
            if reason:
                out["refused"].append({"task": task["id"], "state": state, "reason": reason})
                written = None  # the next push writes the store's state back
        if got.get("comments"):
            store.comments_save(conn, got["comments"], provider=cfg["task_board"]["provider"], subject="task",
                                task_id=task["id"])
        store.task_remote_set(conn, task["id"], remote_id=remote_id, remote_version=got.get("version"),
                              written_sha256=written)
    for remote_id, item in listed.items():
        if remote_id in known or item.get("archived"):
            continue
        try:
            got = call(cfg, root, "get", ["--id", remote_id])
            title = got.get("title") or remote_id
            made = store.request_from_board(conn, title=title, text=got.get("text") or title, remote_id=remote_id,
                                            remote_version=got.get("version"), by="board")
        except (BoardError, store.StoreError) as e:
            out["refused"].append({"item": remote_id, "reason": str(e)})
            continue
        out["created"].append({"request": made["request"], "pending_id": made["pending_id"], "item": remote_id})
    return out


def _take_state(ctx: dict, task: dict, state):
    """Take a state a person set on the board when it is one of the three moves; else the reason it is refused."""
    store, conn = ctx["store"], ctx["conn"]
    try:
        if state == "ready" and task["state"] in ("failed", "blocked"):
            store.task_retry(conn, task["id"])
            return None
        if state == "cancelled" and task.get("parent_id") is None and task["state"] not in FINAL:
            store.request_cancel(conn, task["id"], by="board")
            return None
        if state == "done" and task["state"] == "waiting":
            pending = _open_pending(ctx, task["id"])
            if pending and pending["kind"] == "review":
                store.pending_resolve(conn, pending["id"], resolution="released", by="board")
                return None
    except store.StoreError as e:
        return str(e)
    return (f"the board moved task {task['id']} from {task['state']} to {state}: only ready (a failed or blocked "
            "task), cancelled (a request) and done (a task waiting on a review) are taken from the board")


def _key(cfg: dict, task_id: int, digest: str) -> str:
    store_hash = hashlib.sha256(cfg["store_db"].encode("utf-8")).hexdigest()[:12]
    return f"task:{store_hash}:{task_id}:{digest[:16]}"


def push(ctx: dict, dry_run: bool = False) -> dict:
    """The store to the board (see the module's text). Returns {"pushed", "failed"}, and with dry_run "would":
    what the provider printed for each write it would make."""
    cfg, store, conn, root = ctx["cfg"], ctx["store"], ctx["conn"], ctx["root"]
    out = {"pushed": [], "failed": []}
    if dry_run:
        out["would"] = []
    bounds = None if dry_run else _bounds_problem(cfg)
    for task in store.tasks_list(conn):
        exists = bool(task.get("remote_id"))
        payload = item_payload(task, _open_pending(ctx, task["id"]), create=not exists)
        digest = payload_hash(payload)
        if exists and digest == task.get("remote_written_sha256"):
            continue
        if bounds:
            out["failed"].append({"task": task["id"], "reason": bounds})
            continue
        fd, item_file = tempfile.mkstemp(prefix="item-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            args = (["--id", task["remote_id"]] if exists else []) + [
                "--item-file", item_file, "--idempotency-key", _key(cfg, task["id"], digest),
                "--dry-run" if dry_run else "--confirmed"]
            done = call(cfg, root, "upsert", args)
        except BoardError as e:
            out["failed"].append({"task": task["id"], "reason": str(e)})
            continue
        finally:
            try:
                os.unlink(item_file)
            except OSError:
                pass
        if dry_run:
            out["would"].append({"task": task["id"], **done})
            continue
        try:
            store.task_remote_set(conn, task["id"], remote_id=done["id"], remote_version=done.get("version"),
                                  written_sha256=digest)
        except (KeyError, store.StoreError) as e:
            out["failed"].append({"task": task["id"], "reason": f"written, and not recorded: {e}"})
            continue
        out["pushed"].append(task["id"])
    return out


if __name__ == "__main__":
    print(__doc__.strip(), file=sys.stdout if sys.argv[1:] in (["--help"], ["-h"]) else sys.stderr)
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
