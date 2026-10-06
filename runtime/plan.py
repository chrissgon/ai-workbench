#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The plan of a request: the tasks code builds from a route, which the person approves before any task exists.

The planning agent creates no task (limit L19): the router returns a route, or the person names a flow, and this
module turns it into the tasks of a plan, from the flow file (runtime/flow_files.py) or, for a route to one skill, a
plan of one task. The plan is shown to the person as a pending decision of kind `plan`; its tasks are created only
when the person approves it (runtime/ops.py, approve), and only the approved tasks, by their hash.

Functions:
  pack_skills(project_cfg, root)            the names of the skills in scope: the union of the packs of the enabled
                                            area agents of the project's configuration, else the pack `default`
  from_flow(flow, root, pack)               the tasks of a loaded flow file, as plan tasks
  from_skill(skill, title, root)            a plan of one task, with an empty text: its prompt is the plain request
  plan_hash(tasks)                          the sha256 of the tasks, the hash the person approves
  build(request, tasks, route, source, limits, past, flow=None)   the title, the body and the payload of the plan

A plan task is {"key", "skill", "title", "text", "depends_on": [keys], "milestone", "mandatory_milestone", "web"}:
milestone is true when the flow file says so or the skill's runtime manifest makes it a mandatory milestone; web is
whether the skill requires the web. No cost in money is written: the estimate counts runs.

Usage (a library; the shell is runtime/cli.py, verbs route, approve, reject): python3 runtime/plan.py --help

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import manifest  # noqa: E402  (the same folder)
import skill_meta  # noqa: E402

DEFAULT_PACK = "default"
SELECT_TIMEOUT = 60


class PlanError(Exception):
    """No plan can be built: a pack that does not resolve, a task whose skill is outside the pack."""


def pack_skills(project_cfg: dict, root: str) -> list:
    """The sorted names of the skills in scope. project_cfg is project_config.load() of the project (or its raw
    object). With `area_agents`, the union of the packs of the entries whose `enabled` is true; without it, the pack
    `default`. A pack is resolved by scripts/select_skills.py of the workbench checkout."""
    raw = project_cfg.get("raw", project_cfg) if isinstance(project_cfg, dict) else {}
    agents = raw.get("area_agents")
    if agents is None:
        packs = [DEFAULT_PACK]
    elif not isinstance(agents, dict) or not all(isinstance(a, dict) for a in agents.values()):
        raise PlanError("area_agents of the configuration is an object of agents, each an object")
    else:
        packs = sorted({a.get("pack") for a in agents.values() if a.get("enabled") is True})
        if not all(isinstance(p, str) and p for p in packs):
            raise PlanError("every enabled area agent names its pack")
    names = set()
    for pack in packs:
        try:
            done = subprocess.run([sys.executable, os.path.join(root, "scripts", "select_skills.py"), "--pack", pack],
                                  capture_output=True, text=True, timeout=SELECT_TIMEOUT, check=False)
        except (OSError, subprocess.SubprocessError) as e:
            raise PlanError(f"the pack {pack} could not be resolved: {type(e).__name__}") from None
        try:
            found = json.loads(done.stdout) if done.returncode == 0 else None
        except ValueError:
            found = None
        if not isinstance(found, list):
            reason = (done.stderr.strip().splitlines() or [f"exit {done.returncode}"])[-1]
            raise PlanError(f"the pack {pack} could not be resolved: {reason}")
        names.update(found)
    return sorted(names)


def _task_facts(skill: str, root: str) -> dict:
    meta = skill_meta.declared(os.path.join(root, "skills", skill))
    mandatory = False
    if os.path.isfile(manifest.path(root, skill)):
        mandatory = bool(manifest.load(root, skill).get("mandatory_milestone"))
    return {"mandatory_milestone": mandatory, "web": bool(meta["web"])}


def from_flow(flow: dict, root: str, pack) -> list:
    """The tasks of a flow file (flow_files.load()) as plan tasks, in its order. A task whose skill is not in pack
    raises PlanError naming it."""
    outside = [t["skill"] for t in flow["tasks"] if t["skill"] not in list(pack)]
    if outside:
        raise PlanError(f"the flow {flow['flow']} names skills outside the pack in scope: {', '.join(outside)}")
    tasks = []
    for t in flow["tasks"]:
        try:
            facts = _task_facts(t["skill"], root)
        except (skill_meta.SkillError, manifest.ManifestError) as e:
            raise PlanError(str(e)) from None
        tasks.append({"key": t["key"], "skill": t["skill"], "title": t["title"], "text": t["text"],
                      "depends_on": list(t["depends_on"]), "milestone": bool(t["milestone"]) or facts["mandatory_milestone"],
                      **facts})
    return tasks


def from_skill(skill: str, title: str, root: str) -> list:
    """A plan of one task: the key is the skill's name, the text is empty (the run's prompt is the plain request),
    no dependency."""
    try:
        facts = _task_facts(skill, root)
    except (skill_meta.SkillError, manifest.ManifestError) as e:
        raise PlanError(str(e)) from None
    return [{"key": skill, "skill": skill, "title": title, "text": "", "depends_on": [],
             "milestone": facts["mandatory_milestone"], **facts}]


def plan_hash(tasks: list) -> str:
    """The sha256 of the tasks as JSON with sorted keys and no spaces: what the person approves."""
    return hashlib.sha256(json.dumps(tasks, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build(request: dict, tasks: list, route, source: str, limits: dict, past: list, flow=None) -> dict:
    """{"title", "body", "payload"} of the pending decision of kind `plan`. request is the request's row; route the
    route read from the router's reply (None for a flow the person named); source `router` or `named`; limits from
    the gate file; past the rows of task_runs of the plan's skills in this store."""
    if source not in ("router", "named"):
        raise PlanError("a plan's source is router or named")
    skills = list(dict.fromkeys(t["skill"] for t in tasks))
    estimate_past = []
    for skill in skills:
        runs = [r for r in past if r.get("skill") == skill]
        durations = [r["duration_ms"] for r in runs if isinstance(r.get("duration_ms"), int)]
        estimate_past.append({"skill": skill, "runs": len(runs),
                              "mean_duration_ms": round(sum(durations) / len(durations)) if durations else None})
    digest = plan_hash(tasks)
    payload = {"source": source, "route": route, "flow": flow, "tasks": tasks, "limits": limits,
               "estimate": {"tasks": len(tasks), "runs_at_least": len(tasks), "past": estimate_past},
               "plan_sha256": digest}
    keys = {t["key"]: n for n, t in enumerate(tasks, 1)}
    lines = [f"Plan for request {request['id']}: {request['title']}",
             f"Source: {'the router, ' + route['line'] if source == 'router' and route else 'the flow you named'}"
             + (f"; flow file flows/{flow}.json" if flow else ""), "",
             "| # | Task | Skill | After | Milestone | Web |", "|---|---|---|---|---|---|"]
    for n, t in enumerate(tasks, 1):
        after = ", ".join(str(keys[d]) for d in t["depends_on"]) or "-"
        lines.append(f"| {n} | {t['title']} | {t['skill']} | {after} | {'yes' if t['milestone'] else 'no'} | "
                     f"{'yes' if t['web'] else 'no'} |")
    lines += ["", f"One task at a time; each run at most {limits.get('timeout_seconds')} s, retried at most "
                  f"{limits.get('retries')} times. At least {len(tasks)} runs.",
              "Past runs of these skills here: " + "; ".join(
                  f"{p['skill']} {p['runs']}" + (f" (mean {p['mean_duration_ms']} ms)" if p["mean_duration_ms"] is not None else "")
                  for p in estimate_past) + ".",
              f"Plan hash: {digest}"]
    title = f"Plan: {flow or tasks[0]['skill']} ({len(tasks)} task{'s' if len(tasks) != 1 else ''})"
    return {"title": title, "body": "\n".join(lines), "payload": payload}


if __name__ == "__main__":
    print(__doc__.strip(), file=sys.stdout if sys.argv[1:] in (["--help"], ["-h"]) else sys.stderr)
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
