#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The operations layer of the task runtime: every operation a person or a scheduler can perform, once.

The terminal shell (runtime/cli.py), and later the conversation and the local interface, are shells over the
functions of this file: a shell parses what the person typed, calls one function here and prints what it
returns. No shell reaches the store, the lab facade or a project's files by itself.

Every operation takes the project folder first, reads the project's configuration
(<project>/docs/workbench/runtime.json, runtime/project_config.py), refuses to act when that file names
another workbench checkout than the one this code runs from, opens the store (class store:runtime, through
providers/resolve.py) and returns a JSON-serialisable object. An operation that changes the store does it
through one function of the store, which is one transaction.

Operations of stage 1 of the platform plan:
  request(project, text, flow)     record a request and the tasks of the named flow file
  run_next(project[, tier])        run the next ready task: one skill, once, in the eval container, on a copy
                                   of what may enter by limits L1 to L6 (runtime/workcopy.py); bring back what
                                   it left by the path rule; open the pending decision the task then waits on
  pending(project[, pending_id])   what waits for the person
  answer(project, pending_id, text)   answer a pending decision: the task runs again with the answer
  release(project, pending_id)     release a delivery: the task is done, and what depended on it becomes ready
  retry(project, task_id)          make a failed or blocked task ready again
  cancel(project, request_id)      cancel a request and what is still open under it
  status(project)                  requests, tasks, pending decisions
  proof(project[, skill])          the model each skill in use would run on, by its proof (runtime/proof.py); no
                                   model is called
  verdict(project, run_id, word)   record the person's verdict (worked, corrected, failed) on the use of a run,
                                   with the existing recorder (scripts/evidence.py)
  accept_config(project, sha256)   record the hash of docs/workbench/runtime.json the person accepts; every
                                   other operation refuses a configuration whose hash is not the accepted one

Operations of stage 3:
  request(project, text)           without a flow: a request that waits for its route
  route(project, request_id[, flow])   one run of the router skill asked only for the route (runtime/router.py),
                                   or, with flow, the flow the person names; either way code builds the plan
                                   (runtime/plan.py) as a pending decision of kind `plan`; no task is created
  approve(project, pending_id[, sha256])   approve a plan (its tasks are created) or an acceptance
  reject(project, pending_id[, note])      reject a plan or an acceptance: the request is cancelled
  sync(project[, dry_run])         mirror the tasks with the project's task board (runtime/board.py): what a person
                                   edited there comes in, what the store holds goes out; a dry run reads nothing
                                   and shows every write
  answer(..., with_comments=True)  the comments saved from the board for the task enter the answer

Releasing is not approving: a released delivery stays a draft in the project's state file.

The pending decision a run opens: a `question` when the run wrote nothing and asks (ending `question`); a
`review` otherwise. A draft with open questions (ending `draft_with_questions`) opens a review: the person
releases it as it stands, its open questions left in it, or answers it, and the task runs again. A run that
stopped on a missing input that another skill writes (ending `blocked`) opens nothing: the task is `blocked`, with
the start of the reply as its note, until the person retries it.

Usage (a library; the shell is runtime/cli.py): python3 runtime/ops.py --help

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import contextlib
import datetime
import fcntl
import hashlib
import importlib.util
import os
import re
import sys
import shutil
import subprocess
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import board  # noqa: E402  (the same folder, as scripts/runtime.py imports runtime_vote)
import endings  # noqa: E402
import flow_files  # noqa: E402
import lab  # noqa: E402
import manifest  # noqa: E402
import path_rule  # noqa: E402
import plan  # noqa: E402
import proof as proof_rules  # noqa: E402  (the operation `proof` would hide the module: part 0, F.1, rule 5)
import project_config  # noqa: E402
import router  # noqa: E402
import skill_meta  # noqa: E402
import state_merge  # noqa: E402
import workcopy  # noqa: E402

STORE_CLASS = "store:runtime"
RUNS_DIR = "task-runs"
LOCK_NAME = "run.lock"
NOTE_LIMIT = 1000        # characters of a failure's reason kept on a task and on a run row
PREPARED_DIR = "prepared"  # <data_dir>/prepared/<run id>/: files written for one run before they enter its copy
USE_ID = re.compile(r"[0-9a-f]{8}")
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
# The recorder of uses and verdicts (scripts/evidence.py of the checkout, ROOT, when None; a test points it at a
# stand-in). The runtime records a use of every run and the person's verdict with it, and builds nothing of its own.
EVIDENCE = None
VERDICTS = ("worked", "corrected", "failed")
RECORDER_TIMEOUT = 60
# The one secret the runtime owns: its own key for the floor model's provider, with a spend cap set there. When it
# is not stored, a floor run uses the lab's key for the floor model (_floor_key).
FLOOR_KEY = "WB_RUNTIME_FLOOR_KEY"
TITLE_CHARS = 120  # a request's title taken from its first line, when the person gives none
ROUTE_KEPT = "a route-only run returns no file"


class OpsError(Exception):
    """An operation that was refused: a message for the person and an exit code (1 failed, 2 usage,
    3 not configured)."""

    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


def _load(name: str, path: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def store_module():
    """The store provider as a module, found by its class through providers/resolve.py, never by a path built
    here. Its functions are the contract (providers/store/sqlite.py, "the task runtime")."""
    resolve = _load("workbench_provider_resolve", os.path.join(ROOT, "providers", "resolve.py"))
    try:
        found = resolve.resolve(STORE_CLASS, root=ROOT)
    except (resolve.UnknownClass, resolve.Unresolved) as e:
        raise OpsError(f"the store does not resolve: {e}", 3) from None
    return _load("workbench_store_" + found["implementation"], found["path"])


def context(project: str, *, check_config: bool = True) -> dict:
    """What every operation starts from: {"cfg", "store", "conn"}. The store is created or migrated here
    (idempotent), so the first operation on a project needs no separate setup step. With check_config (every
    operation but accept_config), the configuration's hash must be the one the person accepted last."""
    try:
        cfg = project_config.load(project)
    except project_config.ConfigError as e:
        raise OpsError(str(e), 3) from None
    if cfg["workbench"] != os.path.realpath(ROOT):
        raise OpsError(f"{cfg['path']} names the workbench checkout {cfg['workbench']}, and this command runs from "
                       f"{os.path.realpath(ROOT)}: run it from the checkout the project names, or correct the file", 3)
    store = store_module()
    try:
        store.init_db(cfg["store_db"])
        conn = store.open_db(cfg["store_db"])
    except store.StoreError as e:
        raise OpsError(f"the store at {cfg['store_db']}: {e}", e.code) from None
    if check_config:
        try:
            accepted = store.cursor_get(conn, project_config.ACCEPTED)
        except store.StoreError as e:
            raise OpsError(f"the store at {cfg['store_db']}: {e}", e.code) from None
        if accepted != cfg["sha256"]:
            raise OpsError(f"the configuration {cfg['path']} has the hash {cfg['sha256']} and the accepted one is "
                           f"{accepted or 'none: no configuration was accepted yet'}. Read the file; when it is what you "
                           f"want, run: python3 runtime/cli.py accept-config --project {cfg['project']} --sha256 "
                           f"{cfg['sha256']}", 3)
    return {"cfg": cfg, "store": store, "conn": conn}


def _stored(ctx: dict, function, *args, **kwargs):
    """Call one function of the store; its refusal becomes this layer's."""
    try:
        return function(ctx["conn"], *args, **kwargs)
    except ctx["store"].StoreError as e:
        raise OpsError(str(e), e.code) from None


def _text(value, what: str) -> str:
    """Text the person typed: line ends as \\n, no other control character, not empty."""
    if not isinstance(value, str) or not value.strip():
        raise OpsError(f"{what} is empty", 2)
    return CONTROL.sub(" ", value.replace("\r\n", "\n").replace("\r", "\n")).strip()


def _note(value) -> str:
    """A reason on one record: control characters out, cut to NOTE_LIMIT characters."""
    return CONTROL.sub(" ", str(value or "")).strip()[:NOTE_LIMIT] or "no reason given"


def _sha256(path: str):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _read(path: str):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


# --- what enters a run: runtime/workcopy.py (limits L1 to L6) --------------------------------------------------


def task_prompt(request_text: str, task_text: str, answered, handed=None) -> str:
    """The text of one run: the request in the person's words, the task's own text, and, on a run made after
    an answer, every earlier question of this task with its answer. It names no skill: the one skill staged
    for the run loads by its description, as in a lab run. An empty task text (a plan of one skill) leaves out
    the "For this task: " paragraph, so the prompt is the plain request. handed (the file drop, a later package
    of stage 3) is accepted and not used yet."""
    parts = [request_text.strip()]
    if (task_text or "").strip():
        parts += ["", "For this task: " + task_text.strip()]
    if answered:
        parts += ["", "In an earlier run of this task you stopped and asked the user. Your replies and the user's "
                      "answers are below, oldest first. Each answer is the user's decision: record it where the "
                      "skill says decisions are recorded, and do not ask it again."]
        for n, item in enumerate(answered, 1):
            parts += ["", f"--- your reply {n} ---", (item.get("body") or "").strip(), "",
                      f"--- the user's answer {n} ---", (item.get("answer") or "").strip()]
    return "\n".join(parts) + "\n"


# --- what comes back: runtime/workcopy.py (limits L7, L8, L12, L14) -------------------------------------------


def _count(value):
    """A count the lab reported, or None when it reported none."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _ending(result: dict, meta: dict, skill: str) -> tuple:
    """(ending, why) of a completed run, from runtime/endings.py, with the skill's facts (manifest.ending_facts)
    and the declared outputs without a placeholder that the copy held, unchanged, after the run."""
    cwd, changes = result["cwd"], result["changes"]
    written = [p for p in changes["created"] + changes["modified"] if skill_meta.matches(meta["outputs"], p)]
    after = set(changes["created"] + changes["modified"] + changes["unchanged"])
    fixed = [p for p in meta["outputs"] if "<" not in p and not p.endswith("/")]
    missing = [p for p in fixed if p not in after]
    texts = [(_read(os.path.join(cwd, *p.split("/"))) or "") if lab.readable(cwd, p) else "" for p in written]
    facts = dict(manifest.ending_facts(ROOT, skill), outputs_present=[p for p in fixed if p in set(changes["unchanged"])])
    return endings.classify(result["response"], changes, written, missing, texts, facts=facts)


# --- a use and a verdict, with the existing recorder; the runtime's own key for the floor model ---------------


def _recorder() -> str:
    return EVIDENCE or os.path.join(ROOT, "scripts", "evidence.py")


def _record(args: list) -> "subprocess.CompletedProcess":
    return subprocess.run([sys.executable, _recorder(), "record", *args], capture_output=True, text=True,
                          timeout=RECORDER_TIMEOUT, check=False)


def _use_start(ctx: dict, run_id: int, skill: str, routing: dict):
    """Record the start of a use of the skill with the recorder, with the model and adapter of the routing (the
    gate file's ids, never a model's own account), and keep its id in the cursor use:<run id>. Returns the id, or
    None when the use could not be recorded: that never stops a run."""
    try:
        done = _record(["--start", "--skill-dir", os.path.join(ROOT, "skills", skill), "--project", ctx["cfg"]["project"],
                        "--model", routing["model"], "--adapter", routing["adapter"]])
    except (OSError, subprocess.SubprocessError) as e:
        print(f"the use of run {run_id} could not be recorded: {type(e).__name__}", file=sys.stderr)
        return None
    use = done.stdout.strip()
    if done.returncode != 0 or not USE_ID.fullmatch(use):
        print(f"the use of run {run_id} could not be recorded: {done.stderr.strip()[-500:]}", file=sys.stderr)
        return None
    _stored(ctx, ctx["store"].cursor_set, f"use:{run_id}", use)
    return use


def _own_key() -> tuple:
    """(value or None, reason or None): the runtime's own key for the floor model, through the secret resolver
    (providers/secrets/resolver.py) with the registry runtime/secrets.json. The value is never printed, logged,
    stored or put in a message."""
    try:
        resolver = _load("workbench_secret_resolver_runtime", os.path.join(ROOT, "providers", "secrets", "resolver.py"))
        resolver.register_file(os.path.join(ROOT, "runtime", "secrets.json"))
        found = resolver.resolve(FLOOR_KEY)
    except Exception as e:  # an interpreter the resolver does not run on, a missing store library, a bad registry
        sys.modules.pop("workbench_secret_resolver_runtime", None)
        return None, f"the secret resolver could not be used: {type(e).__name__}"
    if not found:
        return None, None
    return found[0], None


def _floor_key() -> dict:
    """The key a floor run would use: {"value", "source", "reason"}, in this order.
    source "runtime": the runtime's own key (_own_key), when it is stored and the floor tier passes exactly one
      variable, under which it travels (_key_in_environment). It wins: a person who wants a capped key of the
      runtime's own stores it.
    source "lab": no key of its own, and every variable the gate file names for the floor tier is set or found in
      the secret store, by the lab's own lookup (lab.credential_missing). value is None: the value stays the lab's,
      which run_skill passes as it does for a lab run.
    source None: neither, and reason says why; the run stays on the reference model.
    Only the source is shown, by name; the value is never printed, logged, stored or put in a message."""
    reasons = []
    value, reason = _own_key()
    if reason:
        reasons.append(reason)
    try:
        names = lab.reference("floor")["pass_env"]
        if value is not None:
            if len(names) == 1:
                return {"value": value, "source": "runtime", "reason": None}
            reasons.append(f"the floor tier passes {len(names)} variables; the runtime's own key travels under one")
        missing = lab.credential_missing("floor") if names else None
    except Exception as e:  # a gate file the facade refuses, a resolver that does not run on this interpreter
        reasons.append(f"the lab's key for the floor model could not be looked up: {type(e).__name__}")
        missing = None
    if missing == []:
        return {"value": None, "source": "lab", "reason": None}
    if value is None and not reason:
        reasons.append(f"the runtime's own key ({FLOOR_KEY}) is not stored")
    if not names:
        reasons.append("the gate file names no variable for the floor model's key")
    elif missing:
        reasons.append(f"the lab's key for the floor model ({', '.join(missing)}) is neither set nor in the secret store")
    return {"value": None, "source": None, "reason": "no key for the floor model: " + "; ".join(reasons)}


def _route(ctx: dict, skill: str, meta: dict, tier, key: dict) -> dict:
    """proof.route with the key _floor_key found; the routing names that key by its source ("runtime" or "lab")
    on a floor run, and None otherwise."""
    routing = proof_rules.route(ctx["cfg"], skill, meta, force=tier, floor_key=key["source"] is not None)
    if key["reason"] and routing["tier"] == "strong":
        routing["reasons"].append(key["reason"])
    routing["key"] = key["source"] if routing["tier"] == "floor" else None
    return routing


@contextlib.contextmanager
def _key_in_environment(routing: dict, key: dict):
    """Around a floor run on the runtime's own key: the variable the gate file names for the floor tier holds that
    key, and afterwards what was there before (the earlier value, or no variable). Nothing for a strong run, nor
    for a floor run on the lab's key, which the lab passes itself."""
    if routing["tier"] != "floor" or key["source"] != "runtime" or key["value"] is None:
        yield
        return
    name = lab.reference("floor")["pass_env"][0]
    before = os.environ.get(name)
    os.environ[name] = key["value"]
    try:
        yield
    finally:
        if before is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = before


# --- the operations ----------------------------------------------------------------------------------------


def request(project: str, text: str, flow: str | None = None, title: str | None = None) -> dict:
    """Record a request. With a flow, plan it from the flow file the person names (flows/<flow>.json): the tasks
    without a dependency are ready at once, and it returns {"request", "flow", "state", "tasks": [{"id", "key",
    "skill", "state"}]}. Without one, the request waits for its route (route()): {"request", "state": "requested",
    "next": "route"}; its title, when none is given, is the first line of the text, cut to TITLE_CHARS."""
    ctx = context(project)
    if flow is None:
        said = _text(text, "the request's text")
        out = _stored(ctx, ctx["store"].request_add, title=_text(title or said.split("\n", 1)[0][:TITLE_CHARS],
                                                                 "the title").replace("\n", " "), text=said)
        return {"request": out["request"], "state": out["state"], "next": "route"}
    try:
        plan = flow_files.load(flow, ROOT)
    except flow_files.FlowError as e:
        raise OpsError(str(e), 2) from None
    out = _stored(ctx, ctx["store"].request_add, title=_text(title or plan["title"], "the title").replace("\n", " "),
                  text=_text(text, "the request's text"), flow=plan["flow"], tasks=plan["tasks"])
    return {**out, "flow": plan["flow"]}


def run_next(project: str, tier: str | None = None) -> dict:
    """Run the next ready task of the project, if no task of it is running: one skill, once, on the model its
    proof gives (runtime/proof.py: the floor model only where the skill is reliable there and the proof holds on
    this checkout; the reference model otherwise). tier "strong" asks for the reference model; nothing can ask
    for the floor model. Returns {"ran": None, "reason"} when there is nothing to run, else {"ran": task id, "skill",
    "run_id", "run_dir", "status", "ending" or None, "failure" or None, "task_state", "pending_id" or None,
    "returned", "kept", "left_out", "entered": {"kind", "agents_md", "files"} or None, "routing": the
    choice of proof.route, with "key" (the key of a floor run by name: "runtime" or "lab"; None otherwise), or
    None}; "recovered" names the tasks an interrupted run had left running."""
    if tier not in (None, "strong"):
        raise OpsError("tier may only be \"strong\": the person can ask for the reference model, never for the floor model", 2)
    ctx = context(project)
    store = ctx["store"]
    with _run_lock(ctx["cfg"]):
        # This process holds the project's run lock, so a task still `running` is what an interrupted run left.
        recovered = _stored(ctx, store.task_fail_running, "the run was interrupted before it ended; retry the task")
        claimed = _stored(ctx, store.task_claim_next)
        task = claimed["task"]
        if task is None:
            return {"ran": None, "reason": "no task is ready", "recovered": recovered["tasks"],
                    "pending": len(_stored(ctx, store.pending_list))}
        return {**_run(ctx, task, tier), "recovered": recovered["tasks"]}


@contextlib.contextmanager
def _run_lock(cfg: dict):
    """The project's run lock (<data_dir>/run.lock), taken without waiting: a run of a task and a run of the router
    never overlap in one project. Closing the file releases it."""
    os.makedirs(cfg["data_dir"], mode=0o700, exist_ok=True)
    lock = os.open(os.path.join(cfg["data_dir"], LOCK_NAME), os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise OpsError("another run of this project is in progress: one task at a time per project", 1) from None
        yield
    finally:
        os.close(lock)


def _run(ctx: dict, task: dict, tier: str | None = None) -> dict:
    cfg, store, skill = ctx["cfg"], ctx["store"], task["skill"]
    try:
        meta = skill_meta.declared(os.path.join(ROOT, "skills", skill))
        known = manifest.load(ROOT, skill)  # a skill the runtime knows nothing of does not run
        key = _floor_key()
        routing = _route(ctx, skill, meta, tier, key)
        identity = lab.skill_identity(skill)
        run_id = _stored(ctx, store.task_run_start, task["id"], skill=skill, model=routing["model"],
                         adapter=routing["adapter"], skill_version=identity["version"],
                         skill_sha256=identity["content_sha256"], web=routing["web"])["run_id"]
    except (skill_meta.SkillError, manifest.ManifestError, lab.LabError, OpsError, OSError, KeyError) as e:
        _stored(ctx, store.task_fail_running, _note(f"the run could not start: {e}"))
        raise OpsError(f"task {task['id']} ({skill}) could not start: {e}", 1) from None
    dest = os.path.join(cfg["data_dir"], RUNS_DIR, str(run_id))
    out = {"ran": task["id"], "skill": skill, "run_id": run_id, "run_dir": dest, "status": "failed", "ending": None,
           "failure": None, "task_state": "failed", "pending_id": None, "returned": [], "kept": [], "left_out": [],
           "entered": None, "state": None, "routing": routing, "use": None}

    def fail(kind: str, reason: str, attempts: int = 0, digest=None, redactions=None) -> dict:
        _stored(ctx, store.task_run_finish, run_id, status="failed", failure=kind, task_state="failed",
                attempts=attempts, image_digest=digest, run_dir=dest, error=_note(reason), task_note=_note(reason),
                redactions=redactions)
        out["failure"] = {"kind": kind, "reason": _note(reason)}
        return out

    out["use"] = _use_start(ctx, run_id, skill, routing)  # one use per run, also for a run made after an answer
    # Outside the run folder: the facade sets aside whatever it finds there.
    prepared_dir = os.path.join(cfg["data_dir"], PREPARED_DIR, str(run_id))
    try:
        try:
            entered = workcopy.entering(cfg["project"], meta, web=routing["web"], cfg=cfg,
                                        settings_names=lab.settings_names(), prepared_dir=prepared_dir)
        except workcopy.CopyError as e:
            return fail("internal", f"the copy could not be built: {e}")
        files, base, out["left_out"] = entered["files"], entered["base"], entered["left_out"]
        out["entered"] = {"kind": entered["kind"], "agents_md": entered["agents_md"], "files": len(files)}
        base_state = _read(os.path.join(cfg["project"], *path_rule.STATE.split("/")))
        request_text = _stored(ctx, store.task_get, task["parent_id"])["text"]
        answered = [p for p in _stored(ctx, store.pending_list, "resolved", task["id"]) if p["resolution"] == "answered"]
        prompt = task_prompt(request_text, task["text"], answered)
        with lab.session(), _key_in_environment(routing, key):
            result = lab.run_skill(skill, prompt, files, dest, web=routing["web"], tier=routing["tier"])
    except lab.LabError as e:
        return fail("internal", f"{e.kind}: {e.reason}")
    except Exception as e:  # the task never stays `running`: the error is recorded, then shown
        traceback.print_exc()
        return fail("internal", f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(prepared_dir, ignore_errors=True)
    counts, timing = result["counts"], result["timing"]
    if result["status"] != "ok":
        failure = result["failure"]
        return fail(failure["kind"], failure["reason"], counts["attempts"], result["image_digest"],
                    _count(counts.get("redactions")))
    left = result["changes"]["created"] + result["changes"]["modified"]
    returned, kept, state_report = workcopy.returning(cfg["project"], result, base, base_state, skill,
                                                       bound=manifest.bound_among(known, left))
    ending, why = _ending(result, meta, skill)
    loaded = timing.get("skills_loaded")
    body, masked = workcopy.masked_reply(result["response"])
    if state_report is not None:
        out["state"] = {"accepted": len(state_report["accepted"]), "rejected": state_report["rejected"]}
    number = lambda key, kind: timing.get(key) if isinstance(timing.get(key), kind) and not isinstance(timing.get(key), bool) else None
    finish = dict(status="ok", ending=ending, attempts=counts["attempts"], cost_usd=number("cost_usd", (int, float)),
                  tokens=number("total_tokens", int), duration_ms=number("duration_ms", int),
                  skill_loaded=(skill in loaded) if isinstance(loaded, list) else None,
                  image_digest=result["image_digest"], run_dir=dest, redactions=_count(counts.get("redactions")))
    if ending == "blocked":
        # The skill stopped on a missing input that another skill writes: the task is blocked, with no pending
        # decision; the note is the start of the masked reply, and `retry` makes the task ready again.
        done = _stored(ctx, store.task_run_finish, run_id, task_state="blocked", task_note=_note(body), **finish)
        out.update(status="ok", ending=ending, task_state="blocked", pending_id=None, returned=returned, kept=kept)
        return out
    cut = len(body.encode("utf-8")) > store.BODY_MAX
    # A run that wrote nothing and asks opens a question, which is answered. A run that wrote a declared output
    # opens a review, a draft with open questions included: its body is the whole reply, so the person reads the
    # questions and either releases the draft as it stands (its open questions stay in it, its row stays a
    # draft) or answers it, and the next run is given the answer. A run that stopped at its confirmation gate
    # (ending `gate`) opens a review too until stage 4 of the platform plan turns it into an `effect`.
    decision = {"kind": "question" if ending == "question" else "review",
                "title": f"{skill}: {ending.replace('_', ' ')}",
                "body": body.encode("utf-8")[:store.BODY_MAX].decode("utf-8", errors="ignore") if cut else body,
                "payload": {"ending": ending, "why": why, "returned": returned, "kept": kept, "run_dir": dest,
                            "entered": out["entered"], "left_out": out["left_out"], "state": out["state"],
                            "routing": routing, "use": out["use"],
                            "response_file": os.path.join(result["outputs"], "response.md"), "body_cut": cut,
                            "body_masked": masked}}
    done = _stored(ctx, store.task_run_finish, run_id, task_state="waiting", pending=decision, **finish)
    out.update(status="ok", ending=ending, task_state="waiting", pending_id=done["pending_id"], returned=returned, kept=kept)
    return out


def _listed(item: dict) -> dict:
    """One pending decision as a list shows it; a plan also shows its tasks and the hash the person approves."""
    out = {key: item[key] for key in ("id", "kind", "title", "task_id", "created_at")}
    if item["kind"] == "plan":
        payload = item.get("payload") or {}
        out["plan"] = {"tasks": [{"key": t.get("key"), "skill": t.get("skill")} for t in payload.get("tasks") or []],
                       "plan_sha256": payload.get("plan_sha256")}
    return out


def pending(project: str, pending_id: int | None = None) -> dict:
    """What waits for the person. Without an id: {"pending": [{"id", "kind", "title", "task_id", "created_at"}]},
    oldest first, a plan with its tasks and its hash ("plan"). With one: that pending decision whole, with its body
    (the reply, or the plan's table) and its payload."""
    ctx = context(project)
    if pending_id is not None:
        return _stored(ctx, ctx["store"].pending_get, pending_id)
    return {"pending": [_listed(item) for item in _stored(ctx, ctx["store"].pending_list)]}


COMMENTS_LINE = "Comments left on the platform:"


def answer(project: str, pending_id: int, text: str, with_comments: bool = False) -> dict:
    """Answer a pending decision. The task becomes ready, and its next run is given the answer. The answer to a
    question is also written by code into the project's state file, as a decision of the user (L10), so that the
    next run finds it where the skills look for decisions; "state" says whether it was written. A failure there
    never undoes the answer: the store has it, and the next run's prompt carries it. With with_comments (the
    person's command, never a default), the open comments saved from the platform for the task are appended under
    COMMENTS_LINE, one per line, and marked used by this pending decision ("comments": their ids)."""
    ctx = context(project)
    said = _text(text, "the answer")
    used = []
    if with_comments:
        item = _stored(ctx, ctx["store"].pending_get, pending_id)
        saved = _stored(ctx, ctx["store"].comments_list, task_id=item["task_id"])
        if saved:
            lines = [f"- {c.get('author') or 'unknown'}: {' '.join(str(c['text']).split())}" for c in saved]
            said = "\n".join([said, "", COMMENTS_LINE, *lines])
            used = [c["id"] for c in saved]
    out = _stored(ctx, ctx["store"].pending_resolve, pending_id, resolution="answered", by="user", answer=said)
    if used:
        _stored(ctx, ctx["store"].comments_use, used, pending_id=pending_id)
        out = {**out, "comments": used}
    item = _stored(ctx, ctx["store"].pending_get, pending_id)
    if item["kind"] != "question":
        return out
    if _stored(ctx, ctx["store"].task_get, item["task_id"])["parent_id"] is None:
        # A question of the router, on a request: the answer is given to the router's next run (route()), and is not
        # recorded as a decision of a skill.
        return {**out, "state": {"written": False, "reason": "an answer to the router is given to its next run, "
                                                               "not recorded as a decision"}}
    target = os.path.join(ctx["cfg"]["project"], *path_rule.STATE.split("/"))
    current = _read(target) if os.path.isfile(target) and not os.path.islink(target) else None
    if current is None:
        return {**out, "state": {"written": False, "reason": "the project has no state file"}}
    skill = _stored(ctx, ctx["store"].task_get, item["task_id"])["skill"]
    try:
        text_after = state_merge.with_answer(current, date=datetime.date.today().isoformat(), skill=skill,
                                             pending_id=pending_id, answer=said)
    except state_merge.Conflict as e:
        return {**out, "state": {"written": False, "reason": str(e)}}
    temporary = f"{target}.{os.getpid()}.tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        f.write(text_after)
    os.replace(temporary, target)
    return {**out, "state": {"written": True}}


def release(project: str, pending_id: int) -> dict:
    """Release a delivery (a pending decision of kind review). The task is done; the tasks that depended on it
    become ready. The delivery stays a draft: releasing is not approving."""
    ctx = context(project)
    return _stored(ctx, ctx["store"].pending_resolve, pending_id, resolution="released", by="user")


def retry(project: str, task_id: int) -> dict:
    """Make a failed or blocked task ready again."""
    ctx = context(project)
    return _stored(ctx, ctx["store"].task_retry, task_id)


def cancel(project: str, request_id: int) -> dict:
    """Cancel a request, its tasks that are not done, and their open pending decisions."""
    ctx = context(project)
    return _stored(ctx, ctx["store"].request_cancel, request_id, by="user")


def proof(project: str, skill: str | None = None) -> dict:
    """The model each skill would run on now, by its proof, with the two checks and the bands: {"skills": {name:
    proof.route(...)}}, for the named skill or for every skill of the packs in use (manifest.skills_in_use). It
    calls no model; it refreshes the proof file <data_dir>/proof.json where its inputs changed."""
    ctx = context(project)
    names = [skill] if skill else manifest.skills_in_use(ROOT)
    key, out = _floor_key(), {}
    for name in names:
        try:
            meta = skill_meta.declared(os.path.join(ROOT, "skills", name))
            out[name] = _route(ctx, name, meta, None, key)
        except (skill_meta.SkillError, lab.LabError, OSError, KeyError) as e:
            raise OpsError(f"the proof of {name} cannot be read: {e}", 1) from None
    return {"skills": out}


def verdict(project: str, run_id: int, word: str) -> dict:
    """Record the person's verdict on the use of one run, with the recorder (scripts/evidence.py record --verdict):
    {"run_id", "use", "verdict"}. word is worked, corrected or failed. One verdict per run. The verdict is the
    person's: no code path calls this by itself, and nothing reads a verdict out of a model's reply."""
    if word not in VERDICTS:
        raise OpsError(f"a verdict is one of {', '.join(VERDICTS)}", 2)
    ctx = context(project)
    use = _stored(ctx, ctx["store"].cursor_get, f"use:{run_id}")
    if not use:
        raise OpsError(f"run {run_id} has no recorded use", 1)
    given = _stored(ctx, ctx["store"].cursor_get, f"verdict:{run_id}")
    if given:
        raise OpsError(f"run {run_id} already has the verdict {given}", 1)
    try:
        done = _record(["--verdict", word, "--use", use, "--project", ctx["cfg"]["project"]])
    except (OSError, subprocess.SubprocessError) as e:
        raise OpsError(f"the recorder could not be run: {type(e).__name__}", 1) from None
    if done.returncode != 0:
        lines = done.stderr.strip().splitlines()
        raise OpsError(lines[-1] if lines else f"the recorder exited {done.returncode}", 1)
    _stored(ctx, ctx["store"].cursor_set, f"verdict:{run_id}", word)
    return {"run_id": run_id, "use": use, "verdict": word}


def accept_config(project: str, sha256: str) -> dict:
    """Record the hash of the project's configuration that the person accepts, after reading the file. The only
    operation that writes it, and the only one that runs on a configuration that was not accepted. Returns
    {"accepted", "previous", "path"}."""
    ctx = context(project, check_config=False)
    cfg = ctx["cfg"]
    if sha256 != cfg["sha256"]:
        raise OpsError(f"the file's hash is {cfg['sha256']} and you typed {sha256}: nothing was accepted", 1)
    previous = _stored(ctx, ctx["store"].cursor_get, project_config.ACCEPTED)
    _stored(ctx, ctx["store"].cursor_set, project_config.ACCEPTED, sha256)
    return {"accepted": sha256, "previous": previous, "path": cfg["path"]}


def status(project: str) -> dict:
    """{"config": {"path", "sha256"}, "requests": [{"id", "title", "flow", "state", "tasks": [{"id", "key",
    "skill", "state", "note"}]}], "pending": [...]}: everything from the store's records."""
    ctx = context(project)
    rows = _stored(ctx, ctx["store"].tasks_list)
    comments = {}
    for c in _stored(ctx, ctx["store"].comments_list):
        if c.get("task_id") is not None:
            comments[c["task_id"]] = comments.get(c["task_id"], 0) + 1
    board_of = lambda t: {"on_board": bool(t.get("remote_id")), "open_comments": comments.get(t["id"], 0)}
    requests = [{**{key: r[key] for key in ("id", "title", "flow", "state")}, **board_of(r),
                 "tasks": [{**{key: t[key] for key in ("id", "key", "skill", "state", "note")}, **board_of(t)}
                           for t in rows if t["parent_id"] == r["id"]]}
                for r in rows if r["parent_id"] is None]
    return {"config": {"path": ctx["cfg"]["path"], "sha256": ctx["cfg"]["sha256"]}, "requests": requests,
            "pending": [_listed(item) for item in _stored(ctx, ctx["store"].pending_list)]}


# --- stage 3: the route, the plan, its approval ------------------------------------------------------------------


def _plan_pending(ctx: dict, request: dict, tasks: list, route_read, source: str, flow) -> dict:
    """The pending decision of kind `plan` for these tasks: plan.build with the limits of the gate file and the past
    runs of the plan's skills in this store."""
    reference = lab.reference("strong")
    limits = {"one_task_at_a_time": True, "timeout_seconds": reference["timeout_seconds"],
              "retries": reference["retries"]}
    past = []
    for skill in dict.fromkeys(t["skill"] for t in tasks):
        past += _stored(ctx, ctx["store"].task_runs_of_skill, skill)
    built = plan.build(request, tasks, route_read, source, limits, past, flow=flow)
    return {"kind": "plan", **built}


def route(project: str, request_id: int, flow: str | None = None) -> dict:
    """Plan a request that waits for its route. With flow, the flow the person names: its plan is opened at once,
    with no run (an open question of the router is cancelled). Without, one run of the router skill
    (router.ROUTER_SKILL), as it is, asked only for the route: the reply's route line is checked against the flow
    files and the pack in scope, and a valid route becomes a plan; a reply that asks becomes a question; anything
    else reaches the person whole. Nothing the router's run left comes back. No task is created before the person
    approves the plan (approve()). Returns {"routed": true or false, "pending_id", "source", ...}."""
    ctx = context(project)
    store = ctx["store"]
    with _run_lock(ctx["cfg"]):
        recovered = _stored(ctx, store.task_fail_running, "the run was interrupted before it ended; retry the task")
        request = _stored(ctx, store.task_get, request_id)
        if request["parent_id"] is not None:
            raise OpsError(f"task {request_id} is not a request: route the request it belongs to", 1)
        if request["state"] != "requested":
            raise OpsError(f"request {request_id} is {request['state']}: only a request that waits for its route is routed", 1)
        if flow is not None:
            try:
                loaded = flow_files.load(flow, ROOT)
                tasks = plan.from_flow(loaded, ROOT, plan.pack_skills(ctx["cfg"], ROOT))
                decision = _plan_pending(ctx, request, tasks, None, "named", loaded["flow"])
            except flow_files.FlowError as e:
                raise OpsError(str(e), 2) from None
            except (plan.PlanError, lab.LabError) as e:
                raise OpsError(f"no plan can be built: {e}", 1) from None
            opened = _stored(ctx, store.plan_open, request_id, title=decision["title"], body=decision["body"],
                             payload=decision["payload"])
            return {"routed": True, "pending_id": opened["pending_id"], "source": "named", "flow": loaded["flow"],
                    "cancelled": opened["cancelled"], "recovered": recovered["tasks"]}
        return {**_route_run(ctx, request), "recovered": recovered["tasks"]}


def _route_run(ctx: dict, request: dict) -> dict:
    cfg, store, skill = ctx["cfg"], ctx["store"], router.ROUTER_SKILL
    try:
        meta = skill_meta.declared(os.path.join(ROOT, "skills", skill))
        key = _floor_key()
        routing = _route(ctx, skill, meta, None, key)
        identity = lab.skill_identity(skill)
    except (skill_meta.SkillError, lab.LabError, OSError, KeyError) as e:
        raise OpsError(f"the router ({skill}) could not start: {e}", 1) from None
    run_id = _stored(ctx, store.route_run_start, request["id"], skill=skill, model=routing["model"],
                     adapter=routing["adapter"], skill_version=identity["version"],
                     skill_sha256=identity["content_sha256"], web=False)["run_id"]
    dest = os.path.join(cfg["data_dir"], RUNS_DIR, str(run_id))
    out = {"routed": False, "request": request["id"], "source": "router", "run_id": run_id, "run_dir": dest,
           "status": "failed", "ending": None, "failure": None, "pending_id": None, "kind": None, "kept": [],
           "left_out": [], "entered": None, "routing": routing, "use": None}

    def fail(kind: str, reason: str, attempts: int = 0, digest=None, redactions=None) -> dict:
        _stored(ctx, store.route_run_finish, run_id, status="failed", failure=kind, attempts=attempts,
                image_digest=digest, run_dir=dest, error=_note(reason), redactions=redactions)
        out["failure"] = {"kind": kind, "reason": _note(reason)}
        return out

    out["use"] = _use_start(ctx, run_id, skill, routing)
    prepared_dir = os.path.join(cfg["data_dir"], PREPARED_DIR, str(run_id))
    try:
        try:
            entered = workcopy.entering(cfg["project"], meta, web=False, cfg=cfg, settings_names=lab.settings_names(),
                                        prepared_dir=prepared_dir)
        except workcopy.CopyError as e:
            return fail("internal", f"the copy could not be built: {e}")
        out["left_out"] = entered["left_out"]
        out["entered"] = {"kind": entered["kind"], "agents_md": entered["agents_md"], "files": len(entered["files"])}
        answered = [p for p in _stored(ctx, store.pending_list, "resolved", request["id"])
                    if p["kind"] == "question" and p["resolution"] == "answered"]
        prompt = task_prompt(request["text"], router.ROUTE_TASK_TEXT, answered)
        with lab.session(), _key_in_environment(routing, key):
            result = lab.run_skill(skill, prompt, entered["files"], dest, web=False, tier=routing["tier"])
    except lab.LabError as e:
        return fail("internal", f"{e.kind}: {e.reason}")
    except Exception as e:  # the run row never stays `running`: the error is recorded, then shown
        traceback.print_exc()
        return fail("internal", f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(prepared_dir, ignore_errors=True)
    counts, timing = result["counts"], result["timing"]
    if result["status"] != "ok":
        failure = result["failure"]
        return fail(failure["kind"], failure["reason"], counts["attempts"], result["image_digest"],
                    _count(counts.get("redactions")))
    # Nothing a route-only run left comes back: the router's run sees only the router installed, so what it would
    # write (a line about a skill it finds missing) is wrong here by construction.
    facts = {"staged": result["staged"]}
    out["kept"] = [{"path": rel, "class": path_rule.classify(rel, facts), "reason": ROUTE_KEPT}
                   for rel in sorted(result["changes"]["created"] + result["changes"]["modified"])
                   if path_rule.classify(rel, facts) != "ignored"]
    body, masked = workcopy.masked_reply(result["response"])
    body = body.encode("utf-8")[:store.BODY_MAX].decode("utf-8", errors="ignore")
    read = router.read_route(result["response"])
    loaded = timing.get("skills_loaded")
    number = lambda key, kind: timing.get(key) if isinstance(timing.get(key), kind) and not isinstance(timing.get(key), bool) else None
    finish = dict(status="ok", attempts=counts["attempts"], cost_usd=number("cost_usd", (int, float)),
                  tokens=number("total_tokens", int), duration_ms=number("duration_ms", int),
                  skill_loaded=(skill in loaded) if isinstance(loaded, list) else None,
                  image_digest=result["image_digest"], run_dir=dest, redactions=_count(counts.get("redactions")))
    common = {"run_dir": dest, "response_file": os.path.join(result["outputs"], "response.md"), "kept": out["kept"],
              "routing": routing, "use": out["use"], "body_masked": masked}
    why = read.get("why")
    if read["kind"] == "route":
        try:
            checked = router.check_route(read, flow_files.names(ROOT), plan.pack_skills(cfg, ROOT))
            if checked["ok"] and "flow" in checked:
                loaded_flow = flow_files.load(checked["flow"], ROOT)
                tasks = plan.from_flow(loaded_flow, ROOT, plan.pack_skills(cfg, ROOT))
                decision = _plan_pending(ctx, request, tasks, read, "router", loaded_flow["flow"])
            elif checked["ok"]:
                tasks = plan.from_skill(checked["skill"], request["title"], ROOT)
                decision = _plan_pending(ctx, request, tasks, read, "router", None)
            else:
                decision, why = None, checked["why"]
        except (flow_files.FlowError, plan.PlanError) as e:
            decision, why = None, f"no plan can be built from the route: {e}"
        if decision is not None:
            decision["payload"] = {**decision["payload"], **common}
            done = _stored(ctx, store.route_run_finish, run_id, ending="done", pending=decision, **finish)
            out.update(status="ok", ending="done", routed=True, kind="plan", pending_id=done["pending_id"])
            return out
    if read["kind"] == "question":
        decision = {"kind": "question", "title": "The router asks", "body": body,
                    "payload": {"ending": "question", **common}}
        ending = "question"
    else:
        note = (f"\n\nName the flow with: route --request {request['id']} --flow <name>; or answer, and the router "
                f"runs again.")
        decision = {"kind": "question", "title": "The route was not recognised",
                    "body": body.encode("utf-8")[:store.BODY_MAX - len(note.encode("utf-8"))].decode("utf-8", errors="ignore") + note,
                    "payload": {"ending": "unclassified", "why": why, **common}}
        ending = "unclassified"
    done = _stored(ctx, store.route_run_finish, run_id, ending=ending, pending=decision, **finish)
    out.update(status="ok", ending=ending, kind="question", pending_id=done["pending_id"])
    return out


def approve(project: str, pending_id: int, sha256: str | None = None) -> dict:
    """Approve a pending decision of kind `plan` (its tasks are created as the plan lists them, and those with no
    dependency are ready) or `acceptance` (the request written on the task board is kept, and waits for its route).
    With sha256, a plan is approved only when it is the plan's hash. An `effect` is approved from stage 4."""
    ctx = context(project)
    item = _stored(ctx, ctx["store"].pending_get, pending_id)
    if item["kind"] == "plan":
        payload = item.get("payload") or {}
        stated = payload.get("plan_sha256")
        if plan.plan_hash(payload.get("tasks") or []) != stated:
            raise OpsError(f"pending decision {pending_id}: its tasks do not have the hash it states; nothing was approved", 1)
        if sha256 is not None and sha256 != stated:
            raise OpsError(f"the plan's hash is {stated} and you typed {sha256}: nothing was approved", 1)
        return {**_stored(ctx, ctx["store"].plan_approve, pending_id, by="user"), "plan_sha256": stated}
    if item["kind"] == "acceptance":
        return _stored(ctx, ctx["store"].acceptance_resolve, pending_id, resolution="accepted", by="user")
    raise OpsError(f"pending decision {pending_id} is a {item['kind']}: approve takes a plan or an acceptance (an effect "
                   "is approved from stage 4); a question or a review is answered or released", 2)


def sync(project: str, dry_run: bool = False, take: str | None = None, path: str | None = None) -> dict:
    """Mirror the project's task board (runtime/board.py), holding the run lock: pull (the board to the store; not
    on a dry run, which reads nothing), then push (the store to the board; with dry_run, every write the provider
    would make, and nothing changes). take and path settle a document both sides changed (the documents' part,
    a later package of stage 3). Returns {"board": {"pulled", "created", "edited", "refused", "gone", "pushed",
    "failed"[, "would"]} or None, "documents": None}."""
    if take is not None and take not in ("page", "project"):
        raise OpsError("take is page or project", 2)
    if (take is None) != (path is None):
        raise OpsError("take and path go together", 2)
    ctx = context(project)
    ctx["root"] = ROOT
    out = {"board": None, "documents": None}
    with _run_lock(ctx["cfg"]):
        if board.enabled(ctx["cfg"]):
            try:
                pulled = {"pulled": [], "created": [], "edited": [], "refused": [], "gone": []} if dry_run else board.pull(ctx)
                out["board"] = {**pulled, **board.push(ctx, dry_run=dry_run)}
            except board.BoardError as e:
                raise OpsError(f"the task board: {e}", 3 if e.kind == "not configured" else 1) from None
            except ctx["store"].StoreError as e:
                raise OpsError(str(e), e.code) from None
    return out


def reject(project: str, pending_id: int, note: str | None = None) -> dict:
    """Reject a pending decision of kind `plan` or `acceptance`: the request is cancelled, with what is open under
    it. A note is kept on a rejected plan."""
    ctx = context(project)
    item = _stored(ctx, ctx["store"].pending_get, pending_id)
    if item["kind"] == "plan":
        said = _text(note, "the note") if note is not None else None
        return _stored(ctx, ctx["store"].plan_reject, pending_id, by="user", note=said)
    if item["kind"] == "acceptance":
        return _stored(ctx, ctx["store"].acceptance_resolve, pending_id, resolution="rejected", by="user")
    raise OpsError(f"pending decision {pending_id} is a {item['kind']}: reject takes a plan or an acceptance", 2)


if __name__ == "__main__":
    print(__doc__.strip())
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
