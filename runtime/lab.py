#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The lab facade: the one file of runtime/ that talks to the lab (evals/eval_run.py).

The agent runtime runs a skill in the container the skill was proven in, through the same entry: the eval
container of evals/executor.py, started by the adapter's run-prompt.sh, with the skill staged by
scripts/stage_skills.py. This file imports the lab's runner as it is and calls its functions for everything
except the control of the loop: the pause on the account limit, the shared lock, the refusals, the early end,
the replacement of passed values, and the stopping of everything a run started are the lab's own code.

What is written again here, and nowhere else in runtime/, is the loop of one run: prepare a fresh folder, run,
classify how the attempt failed, make it again or stop (run_skill below). It mirrors the closure one_run of
evals/eval_run.py without its measurement: no variant, no baseline, no contamination check, no shared-passage
check, no grading, no evidence line. A parity test (runtime/tests/test_lab_parity.py) gives the same adapter
output to the lab and to this file and expects the same classification. In stage 5 of the platform plan the
loop moves into one function that the lab and the runtime both call, and it is deleted from this file.

Rule: no other module of runtime/ imports anything under evals/. They call the functions of this file.

Usage (a library; the terminal shell is runtime/cli.py):
  python3 runtime/lab.py --help        print this text
  python3 runtime/lab.py reference     print the reference model and its adapter, as JSON

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNNER = os.path.join(ROOT, "evals", "eval_run.py")
MODULE = "workbench_eval_run"

# The names of evals/eval_run.py this file may read. Anything else raises AttributeError (class Lab), and a
# test asserts that every name of FORBIDDEN does. Add a name here only with a line in the pull request that
# says why it is not measurement.
ALLOWED = (
    # where things are, and which executor is in use ("container" for every real run; a test sets "host")
    "ROOT", "EXECUTOR",
    # modules of the lab, loaded by path
    "load_executor", "load_status",
    # the adapter's data and what a run sees of the skills
    "adapter_eval", "harness_settings", "settings_in", "stage_run",
    # credentials by name, and the environment of a contained command
    "resolve_pass_env", "contained_env", "credential_label",
    # the fresh folder of a run, and its way back
    "new_run_root", "return_run", "return_all_runs",
    # running: the fixture commit, the adapter, the stopping of what was started
    "isolate_git", "run_failure", "probe_call", "stop_all_groups", "STOPPING",
    # what the host may read after a run, and what the run did to its folder
    "run_files", "readable", "file_index", "changes", "read_text", "run_ending",
    # passed values replaced in what a run leaves (redaction_values is read through the lab from evals/measure.py)
    "redact_folder", "redaction_values",
    # how an attempt failed (early_end is read through the lab from evals/measure.py)
    "account_limit", "provider_refusal", "auth_refusal", "early_end",
    # the control of the loop that is shared with every runner process of the machine
    "Slots", "start_pause", "wait_while_paused", "RETRY_KINDS", "RETRY_PAUSE", "KEPT_PREFIXES",
)
# Measurement: never read from here. The list is not complete (ALLOWED is what decides); it names what a
# maintainer is most likely to reach for.
FORBIDDEN = (
    "run", "main", "parse", "regrade", "routing", "check_cases_only",                       # the event runner
    "load_evals", "preflight", "case_files", "dependency_dirs", "workbench_files", "build_tree",  # case files
    "ablated_copy", "ablated_line_count",                                                   # variants
    "contamination", "mount_patterns",                                                      # the baseline's checks
    "shared_passage", "skill_passages", "passages_of", "words_of", "folder_text",
    "grade", "grading_call", "template_hash", "version_control", "shown_in",                # grading
    "facts_block", "grading_prompt", "read_grading", "grading_summary", "score", "gate_passes",
    "at_threshold", "within_tolerance", "failed_guards", "confirmed_guards", "guard_positions",
    "run_record_hash", "write_evidence", "evidence_file", "ledger_add", "ledger_read",      # evidence rows
    "scratch_reason", "later_test_id", "next_iteration", "find_event", "conditions_of", "agg", "exact_mean",
    "early_end_stats", "early_end_warning",
)
TIERS = {"strong": ("strong_model", "strong_harness", "strong_pass_env"),
         "floor": ("floor_model", "floor_harness", "floor_pass_env")}
RESPONSE_LIMIT = 2000000  # characters of a reply handed to the caller
EARLY_END_LIMIT = 200000  # characters of a reply the early-end rule reads: the lab's own limit


class LabError(Exception):
    """The run could not be made at all: a kind ("config", "container", "copy") and a one-line reason.
    A run that was made and failed is not an error: run_skill returns it."""

    def __init__(self, kind: str, reason: str):
        super().__init__(reason)
        self.kind, self.reason = kind, reason


def load():
    """evals/eval_run.py as a module, loaded once by path, the way its own tests load it."""
    if MODULE not in sys.modules:
        if not os.path.isfile(RUNNER):
            raise LabError("config", "evals/eval_run.py is missing: the runtime runs from a checkout of the workbench")
        spec = importlib.util.spec_from_file_location(MODULE, RUNNER)
        module = importlib.util.module_from_spec(spec)
        sys.modules[MODULE] = module
        spec.loader.exec_module(module)
    return sys.modules[MODULE]


class Lab:
    """The lab's module, seen through the names of ALLOWED only."""

    def __getattr__(self, name):
        if name not in ALLOWED:
            raise AttributeError(f"runtime/lab.py may not use {name!r} of evals/eval_run.py: it is not in ALLOWED "
                                 "(what measures is never shared with the runtime)")
        return getattr(load(), name)


LAB = Lab()


def _lab_call(function, *args, **kwargs):
    """Call a function of the lab that ends the process on a configuration error (its die()): here that is an
    error of this run, never the end of the caller."""
    try:
        return function(*args, **kwargs)
    except SystemExit as e:
        raise LabError("config", "the lab refused its configuration (its message is on stderr, above); "
                                 f"exit code {e.code}") from None


def reference(tier: str = "strong") -> dict:
    """The model a tier runs on, its adapter, the variables that carry its credential (names only) and the
    control of a run, all from the gate file evals/eval-gate.json: {"tier", "model", "adapter", "pass_env",
    "timeout_seconds", "retries", "control"}."""
    if tier not in TIERS:
        raise LabError("config", f"tier must be one of {', '.join(TIERS)}")
    status = _lab_call(LAB.load_status)
    gate = status.load_gate(LAB.ROOT)
    control = status.event_config(gate)
    model_key, harness_key, env_key = TIERS[tier]
    if not gate.get(model_key) or not gate.get(harness_key):
        raise LabError("config", f"evals/eval-gate.json is missing or invalid, or names no {tier} model")
    return {"tier": tier, "model": gate[model_key], "adapter": gate[harness_key], "pass_env": list(gate.get(env_key) or []),
            "timeout_seconds": control["timeout_seconds"], "retries": control["retries"], "control": control}


def credential_missing(tier: str) -> list:
    """The variables of a tier's credential (its pass_env in the gate file) that are neither set nor found in the
    secret store, by the lab's own lookup (resolve_pass_env of evals/eval_run.py, the one run_skill uses). It
    tells whether a run of the tier would have its key; no value is returned or kept: the environment is put back
    as it was. An empty list for a tier whose gate file names no variable."""
    names = reference(tier)["pass_env"]
    before = {name: os.environ.get(name) for name in names}
    try:
        _lab_call(LAB.resolve_pass_env, names)
        return [name for name in names if not os.environ.get(name)]
    finally:
        for name, value in before.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def skill_identity(skill: str) -> dict:
    """{"version", "content_sha256"} of a skill of this checkout, as the lab computes them for an evidence line."""
    status = _lab_call(LAB.load_status)
    skill_dir = os.path.join(LAB.ROOT, "skills", skill)
    return {"version": status.skill_version(skill_dir), "content_sha256": status.content_hash(skill_dir)}


def settings_names() -> list:
    """Every name that carries a tool's settings at project level, from the adapters' own lists (the lab's
    harness_settings): a path with such a part never enters a run copy (limit L4)."""
    return sorted(_lab_call(LAB.harness_settings))


def measurement_problem():
    """Why the measurement files of this checkout are not the recorded ones (the status script's
    fingerprint_problem), or None when they are."""
    return _lab_call(LAB.load_status).fingerprint_problem(LAB.ROOT)


def image() -> dict:
    """{"name", "digest", "platform"} of the eval image on this machine. digest is None when the lab does not run in
    a container, or when the image is not on this machine. It only inspects, the way ensure() of evals/executor.py
    reads the id of the built image (its digest); it never calls ensure() and never builds."""
    if LAB.EXECUTOR != "container":
        return {"name": None, "digest": None, "platform": None}
    try:
        executor = LAB.load_executor()
        name, platform = executor.names()["image"], executor.image_platform()
        found = executor.docker("image", "inspect", "--format", "{{.Id}}", name, check=False)
    except Exception:  # no docker client, no daemon: the image cannot be seen, so it is not there
        return {"name": None, "digest": None, "platform": None}
    digest = found.stdout.strip() if found.returncode == 0 else ""
    return {"name": name, "digest": digest or None, "platform": platform}


def proof_inputs(skill: str) -> str:
    """A sha256 that changes when the proof of a skill may have changed. Over, in this order: the bytes of the gate
    file; of the skill's evals/versions.jsonl; of every file of the skill's evals/evidence/ in sorted name order,
    each preceded by its name; and the skill's content hash. It lives here because no other module of runtime/
    may name a path under evals/."""
    status = _lab_call(LAB.load_status)
    skill_dir = os.path.join(LAB.ROOT, "skills", skill)
    digest = hashlib.sha256()

    def add(path: str) -> None:
        try:
            with open(path, "rb") as f:
                digest.update(f.read())
        except OSError:
            digest.update(b"\0missing\0")

    add(os.path.join(LAB.ROOT, *status.GATE_REL.split("/")))
    add(os.path.join(skill_dir, "evals", "versions.jsonl"))
    evidence = os.path.join(skill_dir, "evals", "evidence")
    for name in sorted(os.listdir(evidence)) if os.path.isdir(evidence) else []:
        digest.update(b"\0" + name.encode("utf-8") + b"\0")
        add(os.path.join(evidence, name))
    digest.update(skill_identity(skill)["content_sha256"].encode("utf-8"))
    return digest.hexdigest()


def standing(skill: str) -> dict:
    """What the status script computes for one skill: {"skill", "version", "models": {model id: {"band", "cause",
    "score", "mean", "runs"}}, "tiers": {"strong": {"model", "adapter"}, "floor": {"model", "adapter"}},
    "web_cases": the gate file's web cases of the skill, "evidence_images": the sorted distinct image digests of
    the skill's lab events at or above the measurement floor}."""
    status = _lab_call(LAB.load_status)
    gate = status.load_gate(LAB.ROOT)
    row = _lab_call(status.all_status, LAB.ROOT, only=skill)["skills"][0]
    floor = gate.get("measurement_floor") or 0
    images = set()
    for event, _ in status.skill_evidence(os.path.join(LAB.ROOT, "skills", skill)):
        version = event.get("measurement_version")
        if isinstance(version, (int, float)) and version >= floor and event.get("image_digest"):
            images.add(event["image_digest"])
    return {"skill": skill, "version": row["version"],
            "models": {model: {k: found.get(k) for k in ("band", "cause", "score", "mean", "runs")}
                       for model, found in (row.get("models") or {}).items()},
            "tiers": {"strong": {"model": gate.get("strong_model"), "adapter": gate.get("strong_harness")},
                      "floor": {"model": gate.get("floor_model"), "adapter": gate.get("floor_harness")}},
            "web_cases": list((gate.get("web_cases") or {}).get(skill, [])),
            "evidence_images": sorted(images)}


def readable(cwd: str, rel: str) -> bool:
    """True when the host may read the path rel of what a run left in cwd: a regular file, no link, inside cwd."""
    return bool(LAB.readable(cwd, rel))


@contextlib.contextmanager
def session():
    """Leave nothing running: every process group and container a run started is ended on TERM, INT or HUP and
    on every way out, and the folders of a run in progress go back to its run folder. Wrap run_skill in it."""
    LAB.STOPPING.clear()

    def on_signal(signum, _frame):
        print(f"stopped by signal {signum}: ending the run that was started", file=sys.stderr)
        LAB.stop_all_groups()
        LAB.return_all_runs()
        os._exit(128 + signum)

    previous = {}
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            previous[sig] = signal.signal(sig, on_signal)
    try:
        yield
    finally:
        LAB.stop_all_groups(grace=2.0)
        LAB.return_all_runs()
        LAB.STOPPING.clear()
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def failure_kind(why, out_dir: str, refusal_markers, response: str, changed) -> tuple:
    """How one attempt failed, by the lab's own functions and in the lab's own order (one_run of
    evals/eval_run.py): (kind, detail). kind is "timeout", "refused", "auth", "adapter", "early_end", or None
    when the attempt is the run's result. why is what run_failure() returned; changed lists the files the run
    created, changed or deleted. The account limit is looked at before this, by the caller."""
    if why and why.startswith("timeout"):
        return "timeout", None
    if why:
        refusal = LAB.provider_refusal(out_dir, refusal_markers)
        if refusal:
            return "refused", refusal[:300]
        auth = LAB.auth_refusal(out_dir)
        if auth:
            return "auth", auth
        return "adapter", None
    detail = LAB.early_end(response[:EARLY_END_LIMIT], changed)
    return ("early_end", detail) if detail else (None, None)


def _set_aside(dest: str, prefix: str) -> str:
    """Keep what an attempt left in a folder of its own inside the run folder, and clear the run folder for the
    next attempt (the lab's set_aside)."""
    n = 1
    while os.path.exists(os.path.join(dest, f"{prefix}-{n}")):
        n += 1
    kept = os.path.join(dest, f"{prefix}-{n}")
    os.makedirs(kept)
    for item in os.listdir(dest):
        if not item.startswith(tuple(LAB.KEPT_PREFIXES)):
            shutil.move(os.path.join(dest, item), os.path.join(kept, item))
    return kept


PLATFORMS_CITED = "shared/references/platforms/"
# A platform's name, as scripts/stage_skills.py accepts it (its NAME_RE); the folder's README.md is not one.
PLATFORM_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def platforms_cited(skill_dir: str) -> list:
    """The platforms whose reference a run of the skill is given, for the lab's staging (a case's "platforms"):
    every platform with a reference (shared/references/platforms/<name>.md of the lab's root) when the skill's
    SKILL.md, or a file under its references/ folder, cites that folder; none otherwise. A lab case names the
    platform its run needs; the runtime does not know in advance which platform a run will be told, so it gives
    them all. They are staged beside the skill and, like it, never come back (runtime/path_rule.py, "staged")."""
    texts = [os.path.join(skill_dir, "SKILL.md")]
    for current, names, files in os.walk(os.path.join(skill_dir, "references")):
        names.sort()
        texts += [os.path.join(current, name) for name in sorted(files)]
    cites = False
    for path in texts:
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                cites = PLATFORMS_CITED in f.read()
        except OSError:
            continue
        if cites:
            break
    folder = os.path.join(LAB.ROOT, *PLATFORMS_CITED.rstrip("/").split("/"))
    if not cites or not os.path.isdir(folder):
        return []
    return sorted(name[:-3] for name in os.listdir(folder)
                  if name.endswith(".md") and PLATFORM_NAME.match(name[:-3]) and os.path.isfile(os.path.join(folder, name)))


def _copy_in(files, case_dir: str) -> None:
    """Copy the caller's files into the fresh folder of a run: regular files only, each at its relative path."""
    for src, rel in files:
        parts = rel.replace("\\", "/").split("/")
        if os.path.isabs(rel) or not rel or ".." in parts or parts[0] == ".git":
            raise LabError("copy", f"{rel!r} is not a relative path inside the copy")
        if os.path.islink(src) or not os.path.isfile(src):
            raise LabError("copy", f"{rel!r} is not a regular file: only regular files enter a run")
        target = os.path.join(case_dir, *parts)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(src, target)


def run_skill(skill: str, prompt: str, files, dest: str, *, web: bool = False, tier: str = "strong",
              model: str | None = None, adapter: str | None = None, pass_env=None,
              timeout: int | None = None, retries: int | None = None) -> dict:
    """Run one skill once on one task text, in the eval container, on a fresh copy.

    skill    a folder name under skills/ of this checkout: it is staged where the adapter's tool finds skills,
             without its evals/ and scripts/tests/, with the shared references it cites, as in a lab run, and,
             when it cites the platforms' folder, the reference of every platform (platforms_cited())
    prompt   the task text, written to prompt.md
    files    [(absolute source path, path relative to the copy)]: what the run sees of the project. The caller
             decides the list; this function copies regular files and nothing else
    dest     the run folder (absolute). When the run ends, however it ends: <dest>/cwd is the copy as the run
             left it, <dest>/outputs the adapter's output (response.md, timing.json, raw.json, stderr.log),
             <dest>/prompt.md the task text; what an attempt that was made again left is in <dest>/failed-<n>/,
             <dest>/early-end-<n>/ or <dest>/paused-<n>/
    web      True runs on the open network and lets the model search and fetch pages (the adapter's --allow-web)
    tier     "strong" (the reference model) or "floor": the model, its adapter and the names of the variables
             that carry its credential come from evals/eval-gate.json. model, adapter and pass_env replace them
             (a test's stand-in); timeout (seconds) and retries default to the gate file's too

    Returns {"status": "ok" | "failed", "failure": None | {"kind", "reason", "detail"}, "response", "changes":
    {"created", "modified", "deleted", "unchanged"} or None, "staged": [paths the runtime put in the copy],
    "run_dir", "cwd", "outputs", "timing": {...}, "counts": {"attempts", "timeouts", "refusals",
    "adapter_failures", "early_ends", "pauses", "redactions"}, "tier", "model", "adapter", "web",
    "image_digest", "image_platform"}. failure kinds: "timeout", "refused", "auth", "adapter", "early_end"
    (each after the gate file's retries, "auth" at once), "settings" (the copy carries a tool's settings) and
    "stopped". Raises LabError when no run could be made (configuration, container, a file that may not enter).
    Call it inside `with session():`."""
    ref = reference(tier)
    model, adapter = model or ref["model"], adapter or ref["adapter"]
    pass_env = list(ref["pass_env"] if pass_env is None else pass_env)
    timeout = ref["timeout_seconds"] if timeout is None else timeout
    retries = ref["retries"] if retries is None else retries
    control = ref["control"]
    skill_dir = os.path.join(LAB.ROOT, "skills", skill)
    if not os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
        raise LabError("config", f"no skill {skill!r} under skills/ of {LAB.ROOT}")
    if not os.path.isabs(dest):
        raise LabError("config", "dest must be an absolute path")
    eval_cfg = _lab_call(LAB.adapter_eval, adapter)
    runner = os.path.join(LAB.ROOT, "adapters", adapter, "run-prompt.sh")
    if not os.path.isfile(runner):
        raise LabError("config", f"adapter {adapter!r} has no run-prompt.sh")
    _lab_call(LAB.resolve_pass_env, pass_env)
    unset = [name for name in pass_env if not os.environ.get(name)]
    if unset:
        raise LabError("config", f"{', '.join(unset)} is not set and was not found in the secret store. Export it, or "
                                 "start the command with the store's library available: uv run --with keyring==25.7.0 "
                                 "python3 runtime/cli.py ...")
    environment = {}
    if LAB.EXECUTOR == "container":
        try:
            executor = LAB.load_executor()
            # Lab evidence is bound to one built image, and a rebuilt one is another image: the runtime never
            # builds it. ensure() would, so the image is looked for first.
            if executor.docker("image", "inspect", executor.names()["image"], check=False).returncode != 0:
                raise LabError("container", "the eval image of this checkout is not on this machine, and the runtime "
                                            "never builds it: the maintainer loads the archived image (docker load), "
                                            "or builds it with python3 evals/executor.py ensure")
            environment = executor.ensure()  # the networks and the egress proxy, started once before the run
        except LabError:
            raise
        except Exception as e:
            raise LabError("container", f"the eval container is not available: {e}") from None
    settings = _lab_call(LAB.harness_settings)
    values = LAB.redaction_values(pass_env)
    probe = lambda: LAB.probe_call(runner, model, pass_env)
    counts = {"attempts": 0, "timeouts": 0, "refusals": 0, "adapter_failures": 0, "early_ends": 0, "pauses": 0,
              "redactions": 0}
    cwd, out = os.path.join(dest, "cwd"), os.path.join(dest, "outputs")
    os.makedirs(dest, exist_ok=True)
    if any(not item.startswith(tuple(LAB.KEPT_PREFIXES)) for item in os.listdir(dest)):
        _set_aside(dest, "before-resume")  # what an earlier call left in this run folder
    result = {"status": "failed", "failure": None, "response": "", "changes": None, "staged": [], "run_dir": dest,
              "cwd": cwd, "outputs": out, "timing": {}, "counts": counts, "tier": tier, "model": model,
              "adapter": adapter, "web": bool(web), "image_digest": environment.get("image_digest"),
              "image_platform": environment.get("image_platform")}

    def failed(kind, reason, detail=None):
        result["failure"] = {"kind": kind, "reason": reason, "detail": detail}
        result["response"] = LAB.read_text(os.path.join(out, "response.md"), RESPONSE_LIMIT)
        return result

    while True:
        try:
            LAB.wait_while_paused(adapter, probe)
            counts["attempts"] += 1
            with LAB.Slots(control, tier, bool(web)):
                root = LAB.new_run_root(dest, names=(skill,))
                case_dir, out_tmp = os.path.join(root, "case"), os.path.join(root, "out")
                why, delta, staged, carried = None, None, [], None
                try:
                    _copy_in(files, case_dir)
                    quiet = {"root": root, "network": "none"}  # the fixture commit: no secret, no network
                    LAB.isolate_git(case_dir, LAB.contained_env(root), box=quiet)
                    carried = LAB.settings_in(case_dir, settings)
                    if carried:
                        why = f"the copy holds {carried}: a tool's settings never enter a run"
                    else:
                        case = {"platforms": platforms_cited(skill_dir)}
                        staged, _ = _lab_call(LAB.stage_run, case_dir, eval_cfg, skill_dir, [], case, None)
                        prompt_path = os.path.join(root, "prompt.md")
                        with open(prompt_path, "w", encoding="utf-8") as f:
                            f.write(prompt)
                        before = LAB.file_index(case_dir, staged)
                        why = LAB.run_failure(runner, prompt_path, case_dir, model, out_tmp,
                                              LAB.contained_env(root, pass_env), timeout, None, bool(web),
                                              start_dir=root,
                                              box={"root": root, "runner": runner, "pass": pass_env,
                                                   "network": "open" if web else "proxy"})
                        # Before anything is read or stored: each passed value is replaced by a marker, by exact value.
                        counts["redactions"] += LAB.redact_folder(case_dir, values, staged) + LAB.redact_folder(out_tmp, values)
                        if not why:
                            delta = LAB.changes(case_dir, before, staged)
                finally:
                    # Also when the run failed or was stopped: what it left goes to the run folder without the values.
                    counts["redactions"] += LAB.redact_folder(case_dir, values, staged) + LAB.redact_folder(out_tmp, values)
                    LAB.return_run(root)
        except LabError:
            raise
        except (RuntimeError, OSError, subprocess.SubprocessError) as e:
            if LAB.STOPPING.is_set():
                return failed("stopped", "stopped before the run ended")
            raise LabError("container", f"the run could not be prepared or started: {type(e).__name__}: {e}") from None
        result["staged"] = staged
        if carried:
            return failed("settings", why)
        if LAB.STOPPING.is_set():
            return failed("stopped", why or "stopped before the run was read")
        if why and LAB.account_limit(out, eval_cfg["account_limit"]):
            # The account is exhausted: no result of the run. Everything on the account waits, and the run starts
            # again from its beginning afterwards: never retried into the limit, never counted as a timeout.
            counts["attempts"] -= 1
            counts["pauses"] += 1
            LAB.start_pause(adapter, f"task run {os.path.basename(dest)}")
            _set_aside(dest, "paused")
            continue
        response = LAB.read_text(os.path.join(out, "response.md"), RESPONSE_LIMIT)
        changed = (delta["created"] + delta["modified"] + delta["deleted"]) if delta else []
        kind, detail = failure_kind(why, out, eval_cfg["refusal_markers"], response, changed)
        if kind is None:
            break
        if kind == "auth":  # never retried: every later run with that key would meet the same refusal
            return failed("auth", f"the provider refused the key ({detail}) passed in "
                                  f"{LAB.credential_label(adapter, pass_env)}", detail)
        counts[LAB.RETRY_KINDS[kind]] += 1
        if counts["attempts"] > retries:
            reason = {"early_end": f"the model ended its turn early on all {counts['attempts']} attempt(s): {detail}",
                      "refused": "refused: the provider declined the request"}.get(kind, why)
            return failed(kind, reason, detail)
        _set_aside(dest, "early-end" if kind == "early_end" else "failed")
        if kind == "adapter":  # a provider that is overloaded or limits the rate: not at once
            time.sleep(LAB.RETRY_PAUSE * counts["attempts"])
    timing = {}
    try:
        with open(os.path.join(out, "timing.json"), encoding="utf-8") as f:
            timing = json.load(f)
    except (OSError, ValueError):
        pass
    if not isinstance(timing, dict):
        timing = {}
    timing.update(LAB.run_ending(out))  # the stop reason and the turn count, beside the reply
    result.update(status="ok", failure=None, response=response, changes=delta, timing=timing)
    return result


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["reference"]:
        ref = reference()
        print(json.dumps({key: ref[key] for key in ("tier", "model", "adapter", "pass_env", "timeout_seconds", "retries")}, indent=1))
        return 0
    print(__doc__.strip(), file=sys.stdout if argv in (["--help"], ["-h"]) else sys.stderr)
    return 0 if argv in (["--help"], ["-h"]) else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except LabError as e:
        print(f"error: {e.reason}", file=sys.stderr)
        sys.exit(3 if e.kind == "config" else 1)
