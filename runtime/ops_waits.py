#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The derived waits in the operations layer: which task waits for which, worked out from the artifact contract.

A person adds requests in any order, on the page, in the terminal or on the task board. This part of the layer knows
what each task needs (the inputs its skill declares) and what each open task will write (the outputs of its skill),
and makes a task wait for the open task of another request that writes an input the project does not have yet
(runtime/plan.py, derive, is the pure rule). The wait is stored with its reason (the store's task_waits); a task with
an open wait stays `planned`, and the store gives it out to no one (providers/store/sqlite.py). The person's
override, "after request #n", is a request's own field and becomes the same kind of wait; "go ahead" on a plan's
task drops its derived waits and is recorded in the state file as the person's decision.

Functions (each takes the project's context, ops_core.context):
  rederive(ctx)                           recompute the waits of every task not yet started and bring the store to
                                          them; a request that is the only open one, with no override, has none to
                                          compute and costs no read of the skills
  for_plan(ctx, tasks, after, go_ahead)   the waits the tasks of a plan not created yet begin with: {"store": [the
                                          waits as request_add and plan_approve take them], "shown": [...], "missing",
                                          "cycles"}
  annotate(ctx, request, decision)        a plan decision with `waits`, `missing` and `cycles` in its payload and their
                                          lines in its body, before the person approves it
  approve_plan(ctx, item, go_ahead)       plan_approve with the waits and the go-ahead in the same transaction, the
                                          decision written to the state file, and the other tasks derived again
  go_ahead(ctx, task_id)                  the person's go-ahead on a task already created: its derived waits end, the
                                          decision is written to the state file; its new waiting_for
  waiting_for(ctx)                        {task id: [{"task_id", "request_id", "reason"}]}, the open waits, for `status`,
                                          `task` and the dispatcher's snapshot

It reaches no operation of ops.py. Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import datetime
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ops_core as core  # noqa: E402  (the shared names: read as core.<name>, never bound at import)
import path_rule  # noqa: E402
import plan  # noqa: E402
import state_merge  # noqa: E402

FINAL = ("done", "cancelled")
LIVE = ("planned", "ready")      # the states in which a task has not started and may still wait
NEW = "new"                      # the request name of a plan that is not created yet


def _exists(project: str):
    """exists(path) for plan.derive: whether the project has the file. A declared path with placeholders is a pattern
    (each placeholder one path segment); a path that ends in "/" is a folder with a file in it. A path that leaves the
    project is a file the project does not have."""
    def has(path: str) -> bool:
        parts = path.split("/")
        if path.startswith("/") or "\\" in path or ".." in parts:
            return False
        full = os.path.join(project, *[p for p in parts if p])
        if "<" in path:
            found = glob.glob(os.path.join(glob.escape(project), *[plan.PLACEHOLDER.sub("*", p) for p in parts if p]))
            return any(os.path.isfile(f) or (path.endswith("/") and os.path.isdir(f)) for f in found)
        if path.endswith("/"):
            return os.path.isdir(full) and any(files for _root, _dirs, files in os.walk(full))
        return os.path.isfile(full)
    return has


def _graph(rows: list) -> tuple:
    """(nodes, open requests, after_of) of the store's task rows: every task that is not final, the requests that are not
    done or cancelled, and each request's `after_request`."""
    nodes = [{"ref": t["id"], "request": t["parent_id"], "skill": t.get("skill"), "candidate": t["state"] in LIVE,
              "depends_on": list(t.get("depends_on") or [])}
             for t in rows if t["parent_id"] is not None and t["state"] not in FINAL]
    requests = [t for t in rows if t["parent_id"] is None]
    return (nodes, {t["id"] for t in requests if t["state"] not in FINAL},
            {t["id"]: t["after_request"] for t in requests if t.get("after_request")})


def rederive(ctx: dict) -> dict:
    """Recompute the waits of every planned or ready task from the open tasks of the project, the files it has and the
    requests' `after`, and bring the store to them (store.waits_sync); a task that gained a wait goes back to `planned`,
    one whose waits all ended becomes ready. Returns what the store changed ({} when there was nothing to derive)."""
    store = ctx["store"]
    rows = core._stored(ctx, store.tasks_list)
    live = [t["id"] for t in rows if t["parent_id"] is not None and t["state"] in LIVE]
    if not live:
        return {}
    waits = core._stored(ctx, store.waits_list, status="all")
    nodes, open_requests, after_of = _graph(rows)
    if len({n["request"] for n in nodes}) < 2 and not after_of and not any(w["status"] == "open" for w in waits):
        return {}  # one request alone: nothing it reads is written by another request's task
    skip = {w["task_id"] for w in waits if w["kind"] == "go_ahead"}
    got = plan.derive(nodes, plan.skill_facts(core.ROOT), _exists(ctx["cfg"]["project"]), after_of=after_of,
                      open_requests=open_requests, skip=skip)
    desired = [{"task_id": w["ref"], "awaited_id": w["awaited"], "kind": w["kind"], "path": w["path"],
                "reason": w["reason"]} for w in got["waits"]]
    return core._stored(ctx, store.waits_sync, desired, live)


def for_plan(ctx: dict, tasks: list, after, go_ahead=()) -> dict:
    """The waits the tasks of a plan begin with, derived against the open tasks of the project before the plan's tasks
    exist. tasks are the plan's tasks ({"key", "title", "skill", "depends_on"}); after is the request the plan's
    request is to run after, or None; go_ahead the keys the person told to go ahead (their waits are still derived:
    the store records them as dropped, and the state file says what they would have waited for).
    Returns {"store": [{"key", "kind", "awaited_id", "path", "reason"}], "shown": [{"task_key", "task_id", "reason"}],
    "missing": [{"task_key", "skill", "path", "owner", "sentence"}], "cycles": [{"task_key", "sentence"}]}."""
    store = ctx["store"]
    rows = core._stored(ctx, store.tasks_list)
    nodes, open_requests, after_of = _graph(rows)
    held = core._stored(ctx, store.waits_list)
    fixed = {}
    for w in held:
        theirs = [n["ref"] for n in nodes if n["request"] == w["awaited_id"]] if w["kind"] == "after" else [w["awaited_id"]]
        fixed.setdefault(w["task_id"], set()).update(theirs)
    ref = lambda key: (NEW, key)
    nodes += [{"ref": ref(t["key"]), "request": NEW, "skill": t["skill"], "candidate": True,
               "depends_on": [ref(d) for d in t.get("depends_on") or []]} for t in tasks]
    if after:
        after_of[NEW] = after
    got = plan.derive(nodes, plan.skill_facts(core.ROOT), _exists(ctx["cfg"]["project"]), after_of=after_of,
                      open_requests=open_requests, only={ref(t["key"]) for t in tasks}, fixed=fixed)
    return {"store": [{"key": w["ref"][1], "kind": w["kind"], "awaited_id": w["awaited"], "path": w["path"],
                       "reason": w["reason"]} for w in got["waits"]],
            "shown": [{"task_key": w["ref"][1], "task_id": w["awaited"] if w["kind"] == plan.WAIT_INPUT else None,
                       "reason": w["reason"]} for w in got["waits"]],
            "missing": [{"task_key": m["ref"][1], **{k: m[k] for k in ("skill", "path", "owner", "sentence")}}
                        for m in got["missing"]],
            "cycles": [{"task_key": c["ref"][1], "sentence": c["sentence"]} for c in got["cycles"]]}


def annotate(ctx: dict, request: dict, decision: dict) -> dict:
    """A plan decision (plan.build's {"kind", "title", "body", "payload"}) with `waits`, `missing` and `cycles` in its
    payload, and their lines in its body above the plan hash. The plan hash covers the tasks only: it does not move."""
    tasks = decision["payload"].get("tasks") or []
    got = for_plan(ctx, tasks, request.get("after_request"))
    keyed = {t["key"]: t["title"] for t in tasks}
    lines = plan.wait_lines([dict(w, ref=w["task_key"]) for w in got["shown"]],
                            [dict(m, ref=m["task_key"]) for m in got["missing"]],
                            [dict(c, ref=c["task_key"]) for c in got["cycles"]], keyed)
    body = decision["body"].split("\n")
    at = next((i for i, line in enumerate(body) if line.startswith("Plan hash: ")), len(body))
    return {**decision, "body": "\n".join(body[:at] + lines + body[at:]),
            "payload": {**decision["payload"], "waits": got["shown"], "missing": got["missing"],
                        "cycles": got["cycles"]}}


def approve_plan(ctx: dict, item: dict, go_ahead) -> dict:
    """Approve a plan decision: its tasks are created with the waits derived for them (and the go-ahead of the keys the
    person named, in the same transaction, so no task is ever ready for a moment before its wait exists), the go-ahead is
    written to the state file as the person's decision, and the waits of the other tasks are derived again (a task
    already there may now wait for one of the new ones). Returns plan_approve's result with "waits" (the shown ones) and,
    for a go-ahead, "state"."""
    store = ctx["store"]
    payload = item.get("payload") or {}
    request = core._stored(ctx, store.task_get, item["task_id"])
    keys = _keys(go_ahead, [t["key"] for t in payload.get("tasks") or []])
    got = for_plan(ctx, payload.get("tasks") or [], request.get("after_request"), keys)
    done = core._stored(ctx, store.plan_approve, item["id"], by="user", waits=got["store"], go_ahead=keys)
    out = {**done, "waits": got["shown"]}
    if keys:
        out["state"] = _record_go_ahead(ctx, done["tasks"], keys, got["shown"], payload.get("tasks") or [])
    rederive(ctx)
    return out


def _keys(go_ahead, known: list) -> list:
    """The task keys the person named, as a list: a list, or the comma-separated text a shell carries. A key the plan
    does not have is a refusal that names the keys it has."""
    if go_ahead is None:
        return []
    named = [k.strip() for k in (go_ahead.split(",") if isinstance(go_ahead, str) else go_ahead) if str(k).strip()]
    unknown = [k for k in named if k not in known]
    if unknown:
        raise core.OpsError(f"go ahead names {', '.join(unknown)}, which the plan does not have; its tasks are "
                            f"{', '.join(known)}", 2)
    return list(dict.fromkeys(named))


def _record_go_ahead(ctx: dict, created: list, keys: list, shown: list, tasks: list) -> dict:
    """The decision of a plan's go-ahead: one line for each task the person went ahead on, with what it did not wait for."""
    ids = {t["key"]: t["id"] for t in created}
    skills = {t["key"]: t["skill"] for t in tasks}
    return _record_decision(ctx, [(skills[k], ids[k], [w["reason"] for w in shown if w["task_key"] == k]) for k in keys])


def _record_decision(ctx: dict, decisions: list) -> dict:
    """One line of the state file's ## Decisions for each (skill, task id, reasons), written by code
    (state_merge.with_go_ahead): what the task did not wait for. {"written": True}, or {"written": False, "reason"}."""
    target = os.path.join(ctx["cfg"]["project"], *path_rule.STATE.split("/"))
    try:
        with open(target, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return {"written": False, "reason": "the project has no state file"}
    if os.path.islink(target):
        return {"written": False, "reason": "the state file is a link"}
    today = datetime.date.today().isoformat()
    try:
        for skill, task_id, reasons in decisions:
            text = state_merge.with_go_ahead(text, date=today, skill=skill, task_id=task_id, waited=reasons)
    except state_merge.Conflict as e:
        return {"written": False, "reason": str(e)}
    temporary = f"{target}.{os.getpid()}.tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(temporary, target)
    return {"written": True}


def go_ahead(ctx: dict, task_id: int) -> dict:
    """The person's go-ahead on a task that is already created and waits (the store's waits_go_ahead): its derived waits
    end and stay ended, an `after` override stays, and the decision is one line of the state file's ## Decisions
    (state_merge.with_go_ahead, as the plan's go-ahead writes it). Nothing is derived again for the task. Returns
    {"task_id", "state", "dropped": [the reasons], "waiting_for": [what still holds it], "decision": {"written", ...}}."""
    store = ctx["store"]
    done = core._stored(ctx, store.waits_go_ahead, task_id, by="user")
    task = core._stored(ctx, store.task_get, task_id)
    return {"task_id": task_id, "state": done["state"], "dropped": done["reasons"],
            "waiting_for": waiting_for(ctx).get(task_id, []),
            "decision": _record_decision(ctx, [(task["skill"], task_id, done["reasons"])])}


def waiting_for(ctx: dict) -> dict:
    """{task id: [{"task_id", "request_id", "reason"}]} of the open waits: task_id is the awaited task (None for an
    "after request #n" wait, which awaits a request), request_id the awaited request."""
    out = {}
    for w in core._stored(ctx, ctx["store"].waits_list):
        out.setdefault(w["task_id"], []).append(
            {"task_id": w["awaited_id"] if w["kind"] == plan.WAIT_INPUT else None, "request_id": w["request_id"],
             "reason": w["reason"]})
    return out


if __name__ == "__main__":
    print(__doc__.strip(), file=sys.stdout if sys.argv[1:] in (["--help"], ["-h"]) else sys.stderr)
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
