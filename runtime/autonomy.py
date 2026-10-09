#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The five autonomy modes of an area agent, from the three facts under them, and the daily caps: the one module
that compares a mode word (decision D14 of the platform plan).

An area agent is an entry of "area_agents" in the project's configuration (runtime.json): a pack of skills, whether
it is enabled, its mode and two caps. The mode the person chose rests on three facts: whether the agent is enabled,
the checkpoints of its mode (every-phase, milestones, end) and whether a standing approval is in force for it. One
mapping (mode_of) turns the facts back into the mode the agent acts in now, so an agent set to
autonomous-with-policy whose approval expired acts as autonomous: its effects ask again.

  MODES, DEFAULT_MODE, CHECKPOINTS             MODES is also the order of autonomy, the least first
  narrows(old, new)                             whether a move from mode old to mode new is down that order
  agents(raw)                                   the checked "area_agents" ({} when absent; an absent cap is 0)
  facts(name, agents, standing, now)            {"enabled", "checkpoints", "standing"} of one agent
  mode_of(facts)                                the mode the agent acts in now
  state_checkpoints(agents)                     the value of the state file's "- Checkpoints:" line: the most careful
                                                among the enabled agents (every-phase when none is enabled)
  spend(runs, agent, reference_model, floor_model, per_run_usd)   a day's spend of one agent: runs on the reference
                                                model, dollars on the floor model (a floor run of unknown cost counts
                                                at per_run_usd)
  spend_split(runs, agent, floor_model, per_run_usd)   the one place the day's rule is written: {"usd_recorded",
                                                "usd_reserved", "runs_total", "runs_reference", "runs_without_cost"};
                                                spend reads it (usd_floor = usd_recorded + usd_reserved, exactly)
  may_start(name, agents, facts, spent, tier)   (True, "") or (False, why): stopped, or a cap reached
  review_action(task, pending, facts, proven, mandatory)   "release" or "hold": whether a mode releases a review
  covers(approval, policy_sha256, effect, executed_today, now)   (True, "") or (False, why): whether a standing
                                                approval covers one effect, inside every bound
  bounds_of(data, agent, effects)               a policy's bounds file, checked (docs/workbench/policies/<policy>.json);
                                                effects is the closed vocabulary of side effects, given by the caller

A mode never releases a question; it releases a review only when the run ended `done` and wrote something (never a
`draft_with_questions`, an `unclassified` reply, a `done` whose reason says no file changed, or a blocked change set),
the skill is proven, and the task is not a milestone of its mode nor a mandatory milestone. Releasing is not
approving. An effect is executed without asking only inside an approved policy (covers, limit L15).

Usage (a library): python3 runtime/autonomy.py --help

Standard library only. Runs on Python 3.9. Pure: no store, no file, no clock of its own.
"""
from __future__ import annotations

import datetime
import fnmatch
import math
import re
import sys

# The modes in the order of how much an agent may do on its own, the least first: this order is data, and "narrowing" is
# a move down it. A narrowing widens nothing, so code may accept the configuration it changes (runtime/ops.py, set_mode);
# a move up never is accepted by code.
MODES = ("stopped", "supervised", "milestones", "autonomous", "autonomous-with-policy")
DEFAULT_MODE = "milestones"
CHECKPOINTS = {"stopped": "every-phase", "supervised": "every-phase", "milestones": "milestones", "autonomous": "end",
               "autonomous-with-policy": "end"}
CAREFUL_ORDER = ("every-phase", "milestones", "end")  # the most careful first
AGENT_KEYS = ("pack", "enabled", "mode", "max_runs_per_day", "max_usd_per_day")
POLICY_MODE = "autonomous-with-policy"
NO_CHANGE = "no file changed"  # the start of the classifier's reason for a `done` that wrote nothing (runtime/endings.py)
BOUNDS_KEYS = ("policy", "agent", "effects", "targets", "files", "max_per_day", "max_items_per_run")
POLICY_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def narrows(old: str, new: str) -> bool:
    """True when mode new is lower than mode old in the order of MODES: a move that lets the agent do less on its own.
    The same mode, or a higher one, is False. A word that is not a mode: ValueError."""
    for word in (old, new):
        if word not in MODES:
            raise ValueError(f"{word!r} is not one of {', '.join(MODES)}")
    return MODES.index(new) < MODES.index(old)


def agents(raw) -> dict:
    """The checked "area_agents" of a configuration: {name: {"pack", "enabled", "mode", "max_runs_per_day",
    "max_usd_per_day"}}. Absent: {}. Defaults: enabled true, mode milestones, both caps 0 (an absent cap is 0, never
    "no limit"). An unknown key, a mode outside MODES, a cap that is not a number of 0 or more: ValueError naming the
    agent and the key."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("area_agents is an object of agents")
    out = {}
    for name, entry in raw.items():
        if not isinstance(name, str) or not name:
            raise ValueError("an area agent has a name")
        if not isinstance(entry, dict):
            raise ValueError(f"area agent {name}: its entry is an object")
        unknown = sorted(set(entry) - set(AGENT_KEYS))
        if unknown:
            raise ValueError(f"area agent {name}: unknown key {unknown[0]} (known: {', '.join(AGENT_KEYS)})")
        pack = entry.get("pack")
        if not isinstance(pack, str) or not pack.strip():
            raise ValueError(f"area agent {name}: pack is the name of a pack of packs/")
        enabled = entry.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValueError(f"area agent {name}: enabled is true or false")
        mode = entry.get("mode", DEFAULT_MODE)
        if mode not in MODES:
            raise ValueError(f"area agent {name}: mode {mode!r} is not one of {', '.join(MODES)}")
        checked = {"pack": pack, "enabled": enabled, "mode": mode}
        for key, kind in (("max_runs_per_day", int), ("max_usd_per_day", float)):
            value = entry.get(key, 0)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or \
                    (kind is int and not isinstance(value, int)) or not math.isfinite(value) or value < 0:
                what = "a whole number" if kind is int else "a number"
                raise ValueError(f"area agent {name}: {key} is {what}, 0 or more")
            checked[key] = value
        out[name] = checked
    return out


def _moment(value):
    """A stored time (ISO-8601 text) or a datetime, as an aware UTC datetime; None when there is none."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime.datetime):
        moment = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        if len(text) == 10:
            text += "T23:59:59+00:00"  # a date alone holds until the end of that day, as the policy gate reads it
        moment = datetime.datetime.fromisoformat(text)
    return moment if moment.tzinfo else moment.replace(tzinfo=datetime.timezone.utc)


def facts(name: str, agents_checked: dict, standing, now) -> dict:
    """{"enabled", "checkpoints", "standing"} of one agent. standing is the active approvals of scope `standing`;
    it is true only when the agent's mode is autonomous-with-policy and one of them is this agent's
    (bounds["agent"]) and expires after now. An agent that is not configured is not enabled."""
    entry = agents_checked.get(name)
    if entry is None:
        return {"enabled": False, "checkpoints": CHECKPOINTS["stopped"], "standing": False}
    now = _moment(now)
    in_force = entry["mode"] == POLICY_MODE and any(
        row.get("status", "active") == "active" and (row.get("bounds") or {}).get("agent") == name
        and _moment(row.get("expires_at")) is not None and _moment(row.get("expires_at")) > now
        for row in standing or [])
    return {"enabled": bool(entry["enabled"]) and entry["mode"] != "stopped",
            "checkpoints": CHECKPOINTS[entry["mode"]], "standing": in_force}


def mode_of(f: dict) -> str:
    """The mode an agent acts in now, from its three facts: the one mapping."""
    if not f["enabled"]:
        return "stopped"
    if f["checkpoints"] == "every-phase":
        return "supervised"
    if f["checkpoints"] == "milestones":
        return "milestones"
    return POLICY_MODE if f["standing"] else "autonomous"


def state_checkpoints(agents_checked: dict) -> str:
    """The state file's Checkpoints value: the most careful checkpoints among the enabled agents; every-phase when
    no agent is enabled."""
    found = {CHECKPOINTS[a["mode"]] for a in agents_checked.values() if a["enabled"] and a["mode"] != "stopped"}
    for value in CAREFUL_ORDER:
        if value in found:
            return value
    return CAREFUL_ORDER[0]


def spend_split(runs, agent: str, floor_model: str, per_run_usd: float) -> dict:
    """A day's use of one agent, from the rows of runs_since(<the day's start>), the one place the rule is written:
    {"usd_recorded", "usd_reserved", "runs_total", "runs_reference", "runs_without_cost"}. A run on the floor model
    adds its recorded cost to usd_recorded, or per_run_usd to usd_reserved when the cost is unknown (and 1 to
    runs_without_cost); a run on any other model counts as a run on the reference model; runs_total is every run of
    the agent. Each of the two sums is rounded once, to 6 places; spend's usd_floor is their sum."""
    recorded = reserved = 0.0
    out = {"runs_total": 0, "runs_reference": 0, "runs_without_cost": 0}
    for run in runs:
        if run.get("agent") != agent:
            continue
        out["runs_total"] += 1
        if run.get("model") == floor_model:
            if run.get("cost_usd") is None:
                reserved += float(per_run_usd)
                out["runs_without_cost"] += 1
            else:
                recorded += float(run["cost_usd"])
        else:
            out["runs_reference"] += 1
    return {"usd_recorded": round(recorded, 6), "usd_reserved": round(reserved, 6), **out}


def spend(runs, agent: str, reference_model: str, floor_model: str, per_run_usd: float) -> dict:
    """A day's spend of one agent, from the rows of runs_since(<the day's start>): {"runs_reference",
    "usd_floor", "runs_without_cost"}, read from spend_split: usd_floor is usd_recorded + usd_reserved, so a meter
    that shows the two adds up to it exactly. may_start compares it rounded to 6 places."""
    split = spend_split(runs, agent, floor_model, per_run_usd)
    return {"runs_reference": split["runs_reference"], "usd_floor": split["usd_recorded"] + split["usd_reserved"],
            "runs_without_cost": split["runs_without_cost"]}


def may_start(name: str, agents_checked: dict, f: dict, spent: dict, tier: str) -> tuple:
    """(True, "") or (False, why): "stopped"; "cap: runs per day" (tier strong at its cap); "cap: usd per day"
    (tier floor at its cap). An absent cap is 0, so nothing starts on that tier."""
    entry = agents_checked.get(name)
    if entry is None or not f["enabled"]:
        return False, "stopped"
    if tier == "strong" and spent["runs_reference"] >= entry["max_runs_per_day"]:
        return False, "cap: runs per day"
    if tier == "floor" and round(spent["usd_floor"], 6) >= entry["max_usd_per_day"]:
        return False, "cap: usd per day"
    if tier not in ("strong", "floor"):
        return False, f"unknown tier {tier!r}"
    return True, ""


def review_action(task: dict, pending: dict, f: dict, proven: bool, mandatory: bool) -> str:
    """"release" or "hold" for one open pending decision, the first rule that matches:
    1. not a review: hold (a question, a plan, an effect, an acceptance always reach the person);
    2. its run's ending is not `done` (a draft with questions, an unclassified reply, a gate): hold;
    3. a `done` whose reason says no file changed: hold;
    4. its change set is blocked: hold;
    5. the skill is not proven: hold;
    6. a mandatory milestone: hold, in every mode;
    7. the agent is not enabled, or its checkpoints are every-phase: hold;
    8. checkpoints milestones and the task is a milestone: hold;
    9. otherwise release."""
    if pending.get("kind") != "review":
        return "hold"
    payload = pending.get("payload") or {}
    if payload.get("ending") != "done":
        return "hold"
    if str(payload.get("why") or "").startswith(NO_CHANGE):
        return "hold"
    if (payload.get("changeset") or {}).get("blocked"):
        return "hold"
    if not proven or mandatory:
        return "hold"
    if not f["enabled"] or f["checkpoints"] == "every-phase":
        return "hold"
    if f["checkpoints"] == "milestones" and task.get("milestone"):
        return "hold"
    return "release"


def _path_matches(path: str, pattern: str) -> bool:
    """A path against a glob, part by part, so `*` never crosses `/`."""
    parts, globs = path.split("/"), pattern.split("/")
    return len(parts) == len(globs) and all(fnmatch.fnmatchcase(p, g) for p, g in zip(parts, globs))


def covers(approval: dict, policy_sha256: str, effect: dict, executed_today: int, now) -> tuple:
    """(True, "") when a standing approval covers one effect now, else (False, why). Every bound must hold: the
    approval is active and not past its expiry; it was given to the bounds file as it is now (its hash); the effect's
    kind is in bounds["effects"], its target in bounds["targets"], every path of its files matches a glob of
    bounds["files"]; its number of items is at most bounds["max_items_per_run"]; fewer than bounds["max_per_day"]
    were executed today. effect is {"kind", "target", "files", "items"}."""
    bounds = approval.get("bounds") or {}
    if approval.get("status") != "active":
        return False, f"the approval is {approval.get('status')}, not active"
    expires = _moment(approval.get("expires_at"))
    if expires is None or expires <= _moment(now):
        return False, "the approval expired"
    if approval.get("policy_sha256") != policy_sha256:
        return False, "the bounds file changed since it was approved"
    if effect.get("kind") not in (bounds.get("effects") or []):
        return False, f"the effect {effect.get('kind')!r} is not in the policy's effects"
    if effect.get("target") not in (bounds.get("targets") or []):
        return False, f"the target {effect.get('target')!r} is not in the policy's targets"
    for path in effect.get("files") or []:
        if not any(_path_matches(path, glob) for glob in bounds.get("files") or []):
            return False, f"the file {path} is outside the policy's files"
    items, most = effect.get("items"), bounds.get("max_items_per_run")
    if not isinstance(items, int) or not isinstance(most, int) or items > most:
        return False, f"{items} items is over the policy's {most} per run"
    per_day = bounds.get("max_per_day")
    if not isinstance(per_day, int) or executed_today >= per_day:
        return False, f"{executed_today} executed today is at the policy's {per_day} per day"
    return True, ""


def bounds_of(data, agent: str, effects) -> dict:
    """A policy's bounds file, checked: {"policy", "agent", "effects", "targets", "files", "max_per_day",
    "max_items_per_run"}, every key present and no other; "agent" equal to agent; its effects words of effects (the
    closed vocabulary of contracts/environment.md, which the caller reads from its one source in code);
    targets and files lists of texts; the two maxima whole numbers of 1 or more. ValueError names the key."""
    if not isinstance(data, dict):
        raise ValueError("a bounds file holds one JSON object")
    unknown = sorted(set(data) - set(BOUNDS_KEYS))
    if unknown:
        raise ValueError(f"unknown key {unknown[0]} (known: {', '.join(BOUNDS_KEYS)})")
    missing = [key for key in BOUNDS_KEYS if key not in data]
    if missing:
        raise ValueError(f"missing key {missing[0]}")
    if not isinstance(data["policy"], str) or not POLICY_NAME.fullmatch(data["policy"]):
        raise ValueError("policy is lowercase words joined by hyphens")
    if data["agent"] != agent:
        raise ValueError(f"agent is {data['agent']!r}, not {agent!r}")
    if not isinstance(data["effects"], list) or not data["effects"] or any(e not in effects for e in data["effects"]):
        raise ValueError(f"effects is a list of {', '.join(effects)}")
    for key in ("targets", "files"):
        if not isinstance(data[key], list) or not data[key] or not all(isinstance(v, str) and v.strip() for v in data[key]):
            raise ValueError(f"{key} is a non-empty list of texts")
    for key in ("max_per_day", "max_items_per_run"):
        value = data[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{key} is a whole number, 1 or more")
    return dict(data)


if __name__ == "__main__":
    print(__doc__.strip())
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
