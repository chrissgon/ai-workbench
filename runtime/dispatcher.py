#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The dispatcher of the task runtime: what may start now, and what an autonomy mode releases, decided by one pure
function from a snapshot of the store.

decide(snapshot, review_action, may_start) -> {"release": [pending ids], "start": task id or None, "held": [...]}

  snapshot      {"running": <task or None>, "ready": [tasks, oldest first], "reviews": [{"pending", "task", "agent",
                "proven", "mandatory"}], "agents": {"<name>": {"facts", "spent", "entry"}}, "tier": {"<task id>":
                "strong" or "floor"}}, built by runtime/ops.py (dispatch, poll) from the store, the proof and the
                runtime manifests
  review_action runtime/autonomy.py's review_action(task, pending, facts, proven, mandatory): "release" or "hold"
  may_start     runtime/autonomy.py's may_start(name, agents, facts, spent, tier): (True, "") or (False, why)

Rules: (1) release holds every review the agent's mode releases; (2) while a task of the project runs, nothing
starts (one task at a time per project); (3) otherwise the ready tasks are walked oldest first: a task no enabled
area agent owns is held, a task whose agent may not start is held with the reason, and the first that may start is
started; (4) nothing else, and no state is changed here: runtime/ops.py applies the decision.

The two rule functions are passed in, so this file imports no sibling: the scheduler runs a copy of it alone (its
entry, stage 6). It reaches neither the store nor the lab facade.

Usage (a library; the shells are runtime/cli.py dispatch and poll): python3 runtime/dispatcher.py --help

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import sys

ONE_AT_A_TIME = "one task at a time per project"
NO_AGENT = "no area agent owns this task"


def decide(snapshot: dict, review_action, may_start) -> dict:
    """What a round does now: the reviews a mode releases, the task that starts (or None) and the tasks held, each
    with why. Pure: it reads the snapshot and calls the two rule functions, nothing else."""
    agents = snapshot.get("agents") or {}
    entries = {name: a.get("entry") for name, a in agents.items()}
    release = []
    for review in snapshot.get("reviews") or []:
        agent = agents.get(review.get("agent")) or {}
        facts = agent.get("facts") or {"enabled": False, "checkpoints": "every-phase", "standing": False}
        if review_action(review["task"], review["pending"], facts, bool(review.get("proven")),
                         bool(review.get("mandatory"))) == "release":
            release.append(review["pending"]["id"])
    running = snapshot.get("running")
    if running is not None:
        return {"release": release, "start": None, "held": [{"task_id": running["id"], "why": ONE_AT_A_TIME}]}
    held, start = [], None
    tiers = snapshot.get("tier") or {}
    for task in snapshot.get("ready") or []:
        name = task.get("agent")
        if name is None or name not in agents:
            held.append({"task_id": task["id"], "why": NO_AGENT})
            continue
        agent = agents[name]
        tier = tiers.get(task["id"], tiers.get(str(task["id"])))
        ok, why = may_start(name, entries, agent["facts"], agent["spent"], tier)
        if not ok:
            held.append({"task_id": task["id"], "why": why})
            continue
        start = task["id"]
        break
    return {"release": release, "start": start, "held": held}


if __name__ == "__main__":
    print(__doc__.strip(), file=sys.stdout if sys.argv[1:] in (["--help"], ["-h"]) else sys.stderr)
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
