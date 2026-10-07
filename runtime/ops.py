#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The operations layer of the task runtime: every operation a person or a scheduler can perform, once.

The terminal shell (runtime/cli.py), the conversation (runtime/chat.py) and later the local interface are shells over the
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
  sync(project[, dry_run][, take, path])   mirror the tasks with the project's task board (runtime/board.py) and
                                   the documents with its documents platform (runtime/documents.py): what a person
                                   edited there comes in, what the store and the project hold goes out; a dry run
                                   reads nothing and shows every write; take and path settle a document that was not
                                   taken
  answer(..., with_comments=True)  the comments saved from the board for the task, and from the platform for the
                                   documents its skill owns, enter the answer
  hand_over(project, task_id, file)   put a file of the person's in a task's file drop (runtime/drop.py): it enters
                                   that task's runs, and the prompt lists it

Operations of stage 4:
  deps(project)                    install the project's declared dependency sets by code, with no model
                                   (runtime/deps.py); a run whose copy holds versioned files gets each set that
                                   applies, after its base commit, and never brings it back

Operations of stage 6:
  progress(project[, since])       where the work stands and what happened in a period (runtime/progress.py),
                                   computed from the store's records; it calls no model
  approve_policy(project, file, agent[, sha256, expires, what])   a standing approval of a policy file, bound by
                                   its hash, with an expiry: without the hash a preview; with it, the approvals table
                                   gets the row (an earlier one of the same policy and agent is revoked) and the state
                                   file's ## Approvals its generated copy, the row the engagement gate reads
  revoke_policy(project, approval_id)   end a standing approval; its row leaves the state file
  standing(project, policy)        whether an active standing approval covers the policy now: a read
  set_mode(project, agent, mode)   set one area agent's autonomy mode in runtime.json (runtime/autonomy.py, the five
                                   modes); the person then accepts the new hash. accept_config rewrites the state
                                   file's Checkpoints line, a generated copy of the most careful enabled agent's mode
  route(project, request_id)       a request whose lines starting with "- " list several deliveries gets one router
                                   run per delivery and one plan of them all, chained in the order listed
                                   (runtime/plan.py, combine); a route to the brief skill plans one brief task, and
                                   the delivery is routed again after the brief is released; every task names its
                                   area agent
  dispatch(project[, budget_seconds])   the dispatcher's round (runtime/dispatcher.py decides): the handlers' ticks,
                                   the releases each agent's mode makes, the runs its mode and caps allow, one at a time
  poll(project)                    the short job: mirrors, expired approvals, the state file's generated lines, the
                                   releases a mode makes; it calls no model and starts no task
  handler_call(project, name, verb[, args])   one verb of a handler under runtime/handlers/, its JSON object
  pin(project)                     the pin of the dispatcher's two jobs: the accepted runtime.json's path and hash
  say(project, text)               one turn of the conversation with the planning agent (runtime/chat.py is its shell):
                                   a command, the answer to the router's question, or a new request with the memory
  release(project, pending_id)     also starts what a release starts: the brief's delivery routed again (its tasks
                                   wait in an acceptance), and, when the released task returned the product backlog,
                                   its todo tasks as sub-tasks inside the approved plan's limits (the others wait in
                                   an acceptance)

Code comes back as a change set (runtime/changeset.py, limits L9 and L11): a run of a code task (its skill is of a
code area, code_task) whose copy holds versioned files starts only when the project's tracked files have no
uncommitted change, from the project's files plus the newest unblocked change set of its request; what it did to
versioned files is kept in its run folder as one change set, never written into the project. A document task makes
no change set and is not held to clean tracked files; a versioned file it changed is listed in `kept`. The pending decision lists the change set, and a review whose change set is blocked
is not released: it is answered, or the request is cancelled.

A task whose skill's runtime manifest names a gate (the pull-request skill) runs up to its confirmation gate: its
copy holds the request's change set as one commit on a branch over its base (the configuration's code.base), as the
skill was measured; its temporary folder comes back in its run folder; the payload it wrote there is recovered only
when it is the file its reply hashed (runtime/effects.py), and kept as <run folder>/payload.md. When it parsed,
agrees with the configuration and the change set is not blocked, the task waits on an `effect`: the effect document
(<run folder>/effect.json) and its hash. approve(project, pending_id, sha256) with that hash records the approval
(the store's approvals table), checks that nothing moved, and code makes the one commit and opens the pull request
through the code provider; reject cancels the task and sends nothing; answer sends it back with a comment. Any
other case opens a review whose body starts with the reason no effect was opened.

A task whose skill's runtime manifest sets mandatory_milestone is a milestone whatever its flow file says; the review
its run opens when it ends `done` says so and carries "mandatory_milestone": true in its payload.

With a documents platform, run_next reads it first (documents.pull) and runs nothing while a document the task's
skill declares was edited there and not taken; after the run, the documents it returned are written to it
(documents.push), and a failed write never fails the task. A document the mirror imported from the platform (a
person's edit) since a task's last run is named to that task's next run, when its skill reads it, in one line of
its prompt (EDITED_LINE): the content is the person's, not external content.

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

import ast
import contextlib
import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import sys
import shutil
import subprocess
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import autonomy  # noqa: E402  (the same folder, as scripts/runtime.py imports runtime_vote)
import board  # noqa: E402
import changeset  # noqa: E402
import deps as deps_sets  # noqa: E402  (the operation `deps` would hide the module: part 0, F.1, rule 5)
import dispatcher  # noqa: E402
import documents  # noqa: E402
import drop  # noqa: E402
import effects  # noqa: E402
import endings  # noqa: E402
import flow_files  # noqa: E402
import lab  # noqa: E402
import manifest  # noqa: E402
import path_rule  # noqa: E402
import plan  # noqa: E402
import progress as progress_calc  # noqa: E402  (the operation `progress` would hide the module: part 0, F.1, rule 5)
import proof as proof_rules  # noqa: E402  (the operation `proof` would hide the module: part 0, F.1, rule 5)
import project_config  # noqa: E402
import router  # noqa: E402
import skill_meta  # noqa: E402
import state_merge  # noqa: E402
import workcopy  # noqa: E402

STORE_CLASS = "store:runtime"
EFFECTS_DIR = "effects"  # <data_dir>/effects/<pending id>/: the files code hands the code provider
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
HANDED_LINE = "The user handed over these files for this task. They are in the project at:"
# One line per document the mirror imported from the platform since the task's last run (decision of 2026-10-06).
EDITED_LINE = "The person edited {path} on the platform since the last run; its content is theirs."
MANDATORY_LINE = ("This delivery is a mandatory milestone: the next task accepts it only with your approval written in "
                  "the document. Write it there, then release.")


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
    return {"cfg": cfg, "store": store, "conn": conn, "root": ROOT}


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


def task_prompt(request_text: str, task_text: str, answered, handed=None, edited=None) -> str:
    """The text of one run: the request in the person's words, the task's own text, and, on a run made after
    an answer, every earlier question of this task with its answer. It names no skill: the one skill staged
    for the run loads by its description, as in a lab run. An empty task text (a plan of one skill) leaves out
    the "For this task: " paragraph, so the prompt is the plain request. handed lists the relative paths of the
    files the person handed over to this task (the file drop): one paragraph after the task's text names them;
    absent or empty, the prompt is unchanged. edited lists the documents the mirror imported from the platform
    since the task's last run (runtime/documents.py, imported_since): one line each, EDITED_LINE, right before
    the answers, so that the person's edit is read as the person's word and not as external content. Only code
    gives it, never a run's text."""
    parts = [request_text.strip()]
    if (task_text or "").strip():
        parts += ["", "For this task: " + task_text.strip()]
    if handed:
        parts += ["", HANDED_LINE, *[f"- {rel}" for rel in handed]]
    if edited:
        parts += ["", *[EDITED_LINE.format(path=rel) for rel in edited]]
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


def _ending(result: dict, meta: dict, skill: str, gate_files=()) -> tuple:
    """(ending, why) of a completed run, from runtime/endings.py, with the skill's facts (manifest.ending_facts),
    the declared outputs without a placeholder that the copy held, unchanged, after the run, and the files found
    under the run's returned temporary folder (gate_files)."""
    cwd, changes = result["cwd"], result["changes"]
    written = [p for p in changes["created"] + changes["modified"] if skill_meta.matches(meta["outputs"], p)]
    after = set(changes["created"] + changes["modified"] + changes["unchanged"])
    fixed = [p for p in meta["outputs"] if "<" not in p and not p.endswith("/")]
    missing = [p for p in fixed if p not in after]
    texts = [(_read(os.path.join(cwd, *p.split("/"))) or "") if lab.readable(cwd, p) else "" for p in written]
    facts = dict(manifest.ending_facts(ROOT, skill), outputs_present=[p for p in fixed if p in set(changes["unchanged"])],
                 gate_files=list(gate_files))
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
        loaded = flow_files.load(flow, ROOT)
        # A skill whose manifest makes it a mandatory milestone is one whatever the flow file says.
        tasks = [{**t, "milestone": bool(t.get("milestone")) or plan.mandatory(t["skill"], ROOT)} for t in loaded["tasks"]]
    except flow_files.FlowError as e:
        raise OpsError(str(e), 2) from None
    except manifest.ManifestError as e:
        raise OpsError(str(e), 1) from None
    out = _stored(ctx, ctx["store"].request_add, title=_text(title or loaded["title"], "the title").replace("\n", " "),
                  text=_text(text, "the request's text"), flow=loaded["flow"], tasks=tasks)
    return {**out, "flow": loaded["flow"]}


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
    return _claim_and_run(ctx, tier)


def _claim_and_run(ctx: dict, tier=None, task_id=None) -> dict:
    """The body of run_next, shared with dispatch: holding the run lock, end what an interrupted run left, read the
    documents platform, claim the next ready task (or, with task_id, that task: task_claim), run it, write back the
    documents it returned. What it returns is what run_next returns."""
    store = ctx["store"]
    with _run_lock(ctx["cfg"]):
        # This process holds the project's run lock, so a task still `running` is what an interrupted run left.
        recovered = _stored(ctx, store.task_fail_running, "the run was interrupted before it ended; retry the task")
        pulled = None
        if documents.enabled(ctx["cfg"]):
            # Before the task is claimed, so that a refusal leaves no task running (decision D11).
            try:
                pulled = documents.pull(ctx)
            except documents.DocumentsError as e:
                return {"ran": None, "reason": "the documents platform could not be read", "detail": str(e),
                        "recovered": recovered["tasks"]}
            except store.StoreError as e:
                raise OpsError(str(e), e.code) from None
            nxt = _stored(ctx, store.task_peek_next)["task"] if task_id is None else _stored(ctx, store.task_get, task_id)
            if nxt is not None and nxt.get("skill"):
                try:
                    stopped = documents.blocked(ctx, skill_meta.declared(os.path.join(ROOT, "skills", nxt["skill"])))
                except skill_meta.SkillError:
                    stopped = []  # the run fails to start below, with its reason
                if stopped:
                    return {"ran": None, "reason": "a document was edited on the platform and was not taken",
                            "task": nxt["id"], "documents": stopped, "pulled": pulled, "recovered": recovered["tasks"]}
        claimed = _stored(ctx, store.task_claim_next) if task_id is None else _stored(ctx, store.task_claim, task_id)
        task = claimed["task"]
        if task is None:
            reason = "no task is ready" if task_id is None or claimed.get("reason") in (None, "not-ready") else \
                f"task {task_id} is {claimed['reason']}"
            out = {"ran": None, "reason": reason, "recovered": recovered["tasks"],
                   "pending": len(_stored(ctx, store.pending_list))}
            return {**out, "documents": pulled} if pulled is not None else out
        out = {**_run(ctx, task, tier), "recovered": recovered["tasks"]}
        if pulled is not None:
            out["documents"] = documents.merged(pulled, _push_after_run(ctx, out))
        return out


def _push_after_run(ctx: dict, out: dict) -> dict:
    """Write to the documents platform the documents a run returned. Never fails the task: a failure is listed."""
    rels = [r["path"] for r in out.get("returned") or [] if r.get("class") == "document"]
    if not rels:
        return documents.result()
    try:
        return documents.push(ctx, rels)
    except Exception as e:  # a failed push never fails the task; the next sync tries again
        return {**documents.result(), "failed": [{"path": rel, "reason": f"{type(e).__name__}: {e}"} for rel in rels]}


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
        handed = drop.files(cfg["project"], task["id"])
        refused = []
        if handed and routing["web"] and not drop.WEB_TASK_TAKES_DROP:
            refused = [{"path": rel, "reason": drop.WEB_REFUSAL} for _source, rel in handed]
            handed = []
        try:
            entered = workcopy.entering(cfg["project"], meta, web=routing["web"], cfg=cfg,
                                        settings_names=lab.settings_names(), prepared_dir=prepared_dir, handed=handed)
        except workcopy.CopyError as e:
            return fail("internal", f"the copy could not be built: {e}")
        files, base, out["left_out"] = entered["files"], entered["base"], entered["left_out"] + refused
        entered_rels = {rel for _source, rel in files}
        out["entered"] = {"kind": entered["kind"], "agents_md": entered["agents_md"], "files": len(files)}
        base_state = _read(os.path.join(cfg["project"], *path_rule.STATE.split("/")))
        request = _stored(ctx, store.task_get, task["parent_id"])
        request_text = request["text"]
        answered = [p for p in _stored(ctx, store.pending_list, "resolved", task["id"]) if p["resolution"] == "answered"]
        earlier = [r for r in _stored(ctx, store.task_runs_list, task["id"]) if r["id"] != run_id]
        edited = [rel for rel in documents.imported_since(cfg, earlier[-1]["started_at"] if earlier else None)
                  if rel in entered_rels and skill_meta.matches(meta["inputs"], rel)]
        prompt = task_prompt(request_text, task["text"], answered,
                             handed=[rel for _source, rel in handed if rel in entered_rels], edited=edited)
        code = None
        if entered.get("tracked") and code_task(meta):
            code = _code_state(ctx, task)
            if code.get("refused"):
                return fail("internal", code["refused"])
        current = (code or {}).get("current")
        gate = known.get("gate")
        if gate:
            refused = _gate_refusal(cfg, current)
            if refused:
                return fail("internal", refused)
        try:
            installed = _dependencies(cfg, entered, read=_reader(cfg, current))
        except deps_sets.DepsError as e:
            return fail("internal", f"dependencies: {e.reason}")

        def prepare(copy, root):
            if gate:
                # T23: a skill runs only up to its gate; a runtime mode in the skills with an external effect replaces this
                changeset.as_branch(current, copy, root, base=cfg["code"]["base"], head=_head(cfg, task),
                                    message=request["title"])
            elif current is not None:
                changeset.apply(current, copy)  # the earlier work of the request, as an uncommitted change
            for r in installed:
                deps_sets.place(r, copy)

        finish = (lambda copy, _root: [deps_sets.remove(copy, r["produces"]) for r in installed]) if installed else None
        if current is None and not installed and not gate:
            prepare = None
        with lab.session(), _key_in_environment(routing, key):
            result = lab.run_skill(skill, prompt, files, dest, web=routing["web"], tier=routing["tier"],
                                   prepare=prepare, finish=finish, tmp_in_run=bool(gate))
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
    bound = manifest.bound_among(known, left)
    made = _changeset_of(ctx, task, run_id, dest, result, entered, code, bound) if code is not None else None
    returned, kept, state_report = workcopy.returning(cfg["project"], result, base, base_state, skill, bound=bound,
                                                       versioned=(made or {}).get("versioned", ()),
                                                       tracked=entered.get("tracked") or () if code is None else ())
    gate_files = _tmp_files(result.get("tmp"))
    ending, why = _ending(result, meta, skill, [rel for rel, _size in gate_files])
    gate_found = _gate_payload(result, dest, gate_files) if known.get("gate") else None
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
    mandatory = ending == "done" and bool(known.get("mandatory_milestone"))
    if made is not None:
        body = body.rstrip("\n") + "\n\n" + made["text"]
    if mandatory:
        body = body.rstrip("\n") + "\n\n" + MANDATORY_LINE
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
    if made is not None:
        decision["payload"]["changeset"] = made["summary"]
    if gate_found is not None:
        decision["payload"]["gate"] = gate_found if ending == "gate" else {**gate_found, "recovered": False,
                                                                            "why": f"the run ended {ending}, not at its gate"}
    if ending == "gate" and gate_found is not None:
        decision = _effect_or_review(ctx, task, request, dest, decision, gate_found, made, code)
    if mandatory:
        decision["payload"]["mandatory_milestone"] = True
        if cut:  # the sentence stays at the end of a body that was cut
            tail = "\n\n" + MANDATORY_LINE
            room = store.BODY_MAX - len(tail.encode("utf-8"))
            decision["body"] = body.encode("utf-8")[:room].decode("utf-8", errors="ignore") + tail
    done = _stored(ctx, store.task_run_finish, run_id, task_state="waiting", pending=decision, **finish)
    out.update(status="ok", ending=ending, task_state="waiting", pending_id=done["pending_id"], returned=returned, kept=kept)
    return out


def _effect_or_review(ctx: dict, task: dict, request: dict, dest: str, decision: dict, gate_found: dict, made, code) -> dict:
    """The pending decision a run that stopped at its gate opens: an `effect` (the effect document's hash in
    payload_sha256) when the payload was recovered and parsed, its base and head are the configuration's, the
    configuration has code, and the change set it would commit is not blocked; else the review, its body starting
    with the reason. The classifier never guesses, and neither does this."""
    cfg = ctx["cfg"]
    parsed = None
    if gate_found.get("payload_file"):
        with open(gate_found["payload_file"], encoding="utf-8", errors="replace") as f:
            parsed = effects.parse_pull_request_payload(f.read())
    stored = (made or {}).get("summary") or {}
    reason, chosen = None, None
    if not gate_found.get("recovered"):
        reason = f"the payload was not recovered: {gate_found.get('why')}"
    elif parsed is None:
        reason = "the payload is not in the pull-request skill's form"
    elif not cfg.get("code"):
        reason = "the configuration has no code: no pull request can be opened"
    elif (parsed["base"], parsed["head"]) != (cfg["code"]["base"], _head(cfg, task)):
        reason = (f"the payload's base and head ({parsed['base']} ← {parsed['head']}) are not the configuration's "
                  f"({cfg['code']['base']} ← {_head(cfg, task)})")
    elif stored.get("blocked"):
        reason = "the change set is blocked"
    else:
        try:
            chosen = changeset.load(dest) if stored.get("file") else (code or {}).get("current")
        except changeset.ChangesetError as e:
            reason = f"the change set: {e.reason}"
        if reason is None and (chosen is None or chosen.get("blocked") or not (chosen["files"] or chosen["removed"])):
            reason = "there is no unblocked change set to open a pull request for"
    if reason is not None:
        cut = decision["body"].encode("utf-8")[:ctx["store"].BODY_MAX - 2048].decode("utf-8", errors="ignore")
        return {**decision, "body": f"No effect was opened: {reason}.\n\n{cut}",
                "payload": {**decision["payload"], "effect": {"opened": False, "why": reason}}}
    doc = effects.document(cfg["code"], request, parsed, chosen, _head(cfg, task), gate_found["payload_sha256"])
    path, digest = effects.write(dest, doc)
    payload = {**decision["payload"], "effect_file": path, "changeset_file": os.path.join(chosen["dir"], changeset.JSON_FILE),
               "changeset_dir": chosen["dir"], "payload_file": gate_found["payload_file"],
               "effect": {"opened": True, "repo": doc["repo"], "base": doc["base"], "head": doc["head"]}}
    return {"kind": "effect", "title": f"Pull request: {parsed['title']}"[:200], "body": effects.body(doc, digest),
            "payload": payload, "payload_sha256": digest}


def _vcs_provider(cfg: dict) -> str:
    """The code provider's script, found by its class (integration:vcs) through providers/resolve.py, with the
    implementation the configuration names (code.provider); never a path built here."""
    resolve = _load("workbench_provider_resolve", os.path.join(ROOT, "providers", "resolve.py"))
    try:
        return resolve.resolve("integration:vcs", root=ROOT, implementation=cfg["code"]["provider"])["path"]
    except (resolve.UnknownClass, resolve.Unresolved) as e:
        raise OpsError(f"the code provider does not resolve: {e}", 3) from None


def _approve_effect(ctx: dict, item: dict, sha256) -> dict:
    """approve() for an `effect`: the approval row, then, holding the run lock, the checks and the execution by code,
    then the effect is done and the state file gets the generated row."""
    store, cfg, pending_id = ctx["store"], ctx["cfg"], item["id"]
    if sha256 is None:
        raise OpsError(f"pending decision {pending_id} is an effect: approve it with --sha256 <the hash shown with it>", 2)
    if sha256 != item["payload_sha256"]:
        raise OpsError(f"the effect's hash is {item['payload_sha256']} and you typed {sha256}: nothing was approved", 1)
    if item["status"] != "open":
        raise OpsError(f"pending decision {pending_id} is {item['status']}, not open", 1)
    payload = item.get("payload") or {}
    if not cfg.get("code"):
        raise OpsError("the configuration has no code: no pull request can be opened", 3)
    try:
        with open(payload["effect_file"], "rb") as f:
            doc = json.loads(f.read().decode("ascii"))
    except (OSError, KeyError, ValueError) as e:
        raise OpsError(f"the effect document of pending decision {pending_id} cannot be read: {e}", 1) from None
    what = f"pull request {doc['head']} into {doc['base']} of {doc['repo']}: {doc['title']}"
    approval = _stored(ctx, store.approval_add, scope="action", what=" ".join(what.split())[:1000], by="user",
                       payload_sha256=sha256, pending_id=pending_id)
    with _run_lock(cfg):
        try:
            made = changeset.load(os.path.dirname(payload["changeset_dir"]))
            if made is None:
                raise effects.EffectError("deviation", "the change set is no longer in its run folder")
            paths = [f["path"] for f in made["files"]] + list(made["removed"])
            facts = {"versioned": changeset.versioned_in(cfg["project"], paths)}
            doc = effects.verify(payload["effect_file"], sha256, made, facts, cfg["protected_paths"])
            key_prefix = f"wb-{hashlib.sha256(cfg['store_db'].encode('utf-8')).hexdigest()[:12]}-p{pending_id}"
            result = effects.execute(doc, made["dir"], os.path.join(cfg["data_dir"], EFFECTS_DIR, str(pending_id)),
                                     _vcs_provider(cfg), key_prefix)
        except (effects.EffectError, changeset.ChangesetError) as e:
            raise OpsError(f"nothing was sent: {e.reason}; the effect stays open, and approving it again with the same "
                           f"hash tries again", 3 if getattr(e, "kind", "") == "not-configured" else 1) from None
        done = _stored(ctx, store.effect_done, pending_id, approval["id"], by="user", result=result)
    row = effects.approval_row(_stored(ctx, store.approval_get, approval["id"]), doc)
    return {**done, "approval_id": approval["id"], "commit": result["commit"], "pull_request": result["pull_request"],
            "replayed": result["replayed"], "state": _write_approval_row(cfg, row)}


def _write_approval_row(cfg: dict, row: list) -> dict:
    """The generated row in the state file's ## Approvals table (state_merge.write_generated), only when the file did
    not change between its read and the write (L12); otherwise it is written at the next write."""
    target = os.path.join(cfg["project"], *path_rule.STATE.split("/"))
    if not os.path.isfile(target) or os.path.islink(target):
        return {"written": False, "reason": "the project has no state file"}
    before = _sha256(target)
    try:
        text = state_merge.write_generated(_read(target), [row])
    except state_merge.Conflict as e:
        return {"written": False, "reason": str(e)}
    if _sha256(target) != before:
        return {"written": False, "reason": "the state file changed while the row was being written; it is written at the next write"}
    temporary = f"{target}.{os.getpid()}.tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(temporary, target)
    return {"written": True}


def _head(cfg: dict, task: dict) -> str:
    """The head branch of a request's pull request: <branch_prefix>request-<request id> (choice K10)."""
    return f"{cfg['code']['branch_prefix']}request-{task['parent_id']}"


def _gate_refusal(cfg: dict, current):
    """Why a task whose skill has a gate cannot start, or None: it needs the configuration's code (the base branch)
    and a change set of its request to show."""
    if not cfg.get("code"):
        return "the configuration has no code (provider, repo, base): a task with a confirmation gate needs it"
    if current is None or not (current.get("files") or current.get("removed")):
        return "there is no change to open a pull request for"
    return None


def _tmp_files(tmp) -> list:
    """[(relative path, bytes)] of the regular files under a run's returned temporary folder, no link followed."""
    out = []
    if not tmp or not os.path.isdir(tmp) or os.path.islink(tmp):
        return out
    for current, folders, files in os.walk(tmp):
        folders[:] = sorted(n for n in folders if not os.path.islink(os.path.join(current, n)))
        for name in sorted(files):
            path = os.path.join(current, name)
            if not os.path.islink(path) and os.path.isfile(path):
                out.append((os.path.relpath(path, tmp).replace(os.sep, "/"), os.path.getsize(path)))
    return out


def _gate_payload(result: dict, dest: str, tmp_files) -> dict:
    """The payload a gate run wrote, recovered (runtime/effects.py) and kept as <dest>/payload.md; everything else
    under the returned temporary folder is deleted, and only its names and sizes are kept. Returns {"recovered",
    "why", "payload_file", "payload_sha256", "parsed", "tmp_left"}."""
    found = effects.recover_payload(result.get("response") or "", result.get("tmp"), lab.readable)
    out = {"recovered": found["recovered"], "why": found.get("why"), "payload_file": None, "payload_sha256": None,
           "parsed": False, "tmp_left": [{"name": rel, "bytes": size} for rel, size in tmp_files]}
    if found["recovered"]:
        kept = os.path.join(dest, "payload.md")
        shutil.copyfile(found["file"], kept)
        out.update(payload_file=kept, payload_sha256=found["sha256"],
                   parsed=effects.parse_pull_request_payload(found["text"]) is not None)
    if result.get("tmp") and os.path.isdir(result["tmp"]) and not os.path.islink(result["tmp"]):
        shutil.rmtree(result["tmp"])
    return out


def _git(project: str, *args) -> "subprocess.CompletedProcess":
    """git in the project (the person's own repository, run by the host); never in a copy a run touched."""
    return subprocess.run(["git", "-C", project, *args], capture_output=True, text=True, timeout=120, check=False)


def _request_run_dirs(ctx: dict, request_id: int) -> list:
    """The run folders of the completed runs of a request's tasks, newest first."""
    runs = []
    for t in _stored(ctx, ctx["store"].tasks_list, request_id):
        if t["parent_id"] is not None:
            runs += [r for r in _stored(ctx, ctx["store"].task_runs_list, t["id"]) if r["status"] == "ok" and r["run_dir"]]
    return [r["run_dir"] for r in sorted(runs, key=lambda r: r["id"], reverse=True)]


def code_task(meta: dict) -> bool:
    """A code task: its skill is of a code area (workcopy.CODE_AREAS, the areas of the code-change flow's skills).
    Only a code task whose copy holds versioned files is held to clean tracked files and makes a change set
    (choice K4); a document task runs on a project whose tracked files carry uncommitted changes (a project
    initialised by core-project-init always has two), and a versioned file it changed is listed in `kept`."""
    return meta.get("area") in workcopy.CODE_AREAS


def _code_state(ctx: dict, task: dict) -> dict:
    """What a run whose copy holds versioned files starts from: {"project_commit", "current"}, or {"refused": why}.
    A change set is made against one commit of the project (choice K4): the run is refused while the project's
    tracked files have uncommitted changes, and when the request's current change set was made against another
    commit. The state file is left out of that check: it never travels in a change set (the path rule's class
    `state`), and code writes into it (an answer, an approval row) between the runs of a request."""
    project = ctx["cfg"]["project"]
    try:
        dirty = _git(project, "status", "--porcelain", "-z", "--untracked-files=no")
        head = _git(project, "rev-parse", "HEAD")
    except (OSError, subprocess.SubprocessError) as e:
        return {"refused": f"git could not be run in the project: {type(e).__name__}"}
    if dirty.returncode != 0 or head.returncode != 0:
        return {"refused": f"git failed in the project: {(dirty.stderr or head.stderr).strip()[:300]}"}
    if [entry for entry in dirty.stdout.split("\0") if entry and entry[3:] != path_rule.STATE]:
        return {"refused": "commit or stash the changes to tracked files first: a change set is made against a commit"}
    commit = head.stdout.strip()
    try:
        current = changeset.current(_request_run_dirs(ctx, task["parent_id"]))
    except changeset.ChangesetError as e:
        return {"refused": f"the request's change set: {e.reason}"}
    if current is not None and current.get("project_commit") != commit:
        return {"refused": f"the request's change set was made against the commit {current.get('project_commit')} and the "
                           f"project is at {commit}: cancel the request, or put the project back on that commit"}
    return {"project_commit": commit, "current": current}


def _reader(cfg: dict, current):
    """read(rel) of a dependency file as the next run sees it: the request's current change set's when it holds or
    removes the file, else the project's."""
    def read(rel):
        if current is not None:
            if rel in (current.get("removed") or []):
                return None
            for item in current.get("files") or []:
                if item["path"] == rel:
                    with open(os.path.join(current["dir"], "files", *rel.split("/")), "rb") as f:
                        return f.read()
        return _project_bytes(cfg["project"], rel)
    return read


EMPTY_CHANGESET = changeset.canonical_sha256([], [])


def _changeset_of(ctx: dict, task: dict, run_id: int, dest: str, result: dict, entered: dict, code: dict, bound) -> dict:
    """The change set a completed run left, stored in its run folder when it differs from the one it started from:
    {"summary" (for the pending decision's payload), "text" (for its body), "versioned" (the paths that never come
    back as loose files)}."""
    checks = {"readable": lab.readable, "scan": workcopy.scan, "settings": lab.carries_settings}
    facts = {"staged": list(result["staged"]) + [path_rule.DROP_DIR], "bound": list(bound)}
    try:
        made = changeset.compute(dest, result.get("base_commit"), entered["tracked"], facts, checks,
                                 protected=ctx["cfg"]["protected_paths"])
    except changeset.ChangesetError as e:
        why = f"the change set could not be computed: {e.reason.splitlines()[0] if e.reason else e.kind}"
        return {"summary": {"error": why}, "text": why[0].upper() + why[1:] + ".", "versioned": []}
    current = code.get("current")
    file = None
    if made["refused"] or made["sha256"] != (current["sha256"] if current else EMPTY_CHANGESET):
        made.update(request=task["parent_id"], task=task["id"], run=run_id, project_commit=code["project_commit"])
        file = changeset.store(dest, made)
    summary = {"file": file, "sha256": made["sha256"], "files": len(made["files"]), "removed": len(made["removed"]),
               "blocked": made["blocked"], "refused": made["refused"]}
    lines = [f"Change set: {len(made['files'])} file(s), {len(made['removed'])} removed"
             + (", blocked" if made["blocked"] else "") + (f", sha256 {made['sha256']}" if file else ", unchanged")]
    lines += [f"- {item['change']}: {item['path']}" + (" (executable)" if item["executable"] else "") for item in made["files"]]
    lines += [f"- removed: {rel}" for rel in made["removed"]]
    lines += [f"- refused: {item['path'] or '(the whole set)'}: {item['reason']}" for item in made["refused"]]
    return {"summary": summary, "text": "\n".join(lines), "versioned": made["versioned"]}


def _project_bytes(project: str, rel: str):
    """The bytes of a project's file at rel, or None when it is not a regular file inside the project."""
    path = os.path.join(project, *rel.split("/"))
    real = os.path.realpath(path)
    if os.path.islink(path) or not os.path.isfile(path) or not real.startswith(os.path.realpath(project) + os.sep):
        return None
    with open(path, "rb") as f:
        return f.read()


def _dependencies(cfg: dict, entered: dict, read=None) -> list:
    """The installed folders a run gets: for a run whose copy holds versioned files, each declared dependency set
    whose files are all there (read(rel), default the project's own file), installed or taken from the cache
    (runtime/deps.py). Empty for a run without versioned files. Raises deps.DepsError."""
    if not entered.get("tracked"):
        return []
    read = read or (lambda rel: _project_bytes(cfg["project"], rel))
    out = []
    for entry in cfg.get("dependencies") or []:
        files = deps_sets.files_for(entry, read)
        if files is not None:
            out.append(deps_sets.ensure(cfg["data_dir"], entry, files, lab.image()["digest"]))
    return out


def deps(project: str) -> dict:
    """Install every dependency set the project's configuration declares, by code, with no model: {"dependencies":
    [{"recipe", "file", "applies", and when it applies "key", "cached", "duration_ms"}]}. A set whose files are not
    all in the project does not apply and installs nothing. Holds the run lock, so no run starts meanwhile."""
    ctx = context(project)
    cfg, out = ctx["cfg"], []
    with _run_lock(cfg):
        for entry in cfg.get("dependencies") or []:
            files = deps_sets.files_for(entry, lambda rel: _project_bytes(cfg["project"], rel))
            row = {"recipe": entry["recipe"], "file": entry["file"], "applies": files is not None}
            if files is not None:
                try:
                    done = deps_sets.ensure(cfg["data_dir"], entry, files, lab.image()["digest"])
                except deps_sets.DepsError as e:
                    raise OpsError(f"dependencies: {e.reason}", 1) from None
                except lab.LabError as e:
                    raise OpsError(f"dependencies: {e.kind}: {e.reason}", 1) from None
                row.update(key=done["key"], cached=done["cached"], duration_ms=done["duration_ms"])
            out.append(row)
    return {"dependencies": out}


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
# An answer that is only one of these words would reach the resumed skill as its "yes": an effect is approved by hash.
APPROVAL_WORDS = re.compile(r"(?i)(yes|y|ok|okay|approved|approve|proceed|go)\.?")


def answer(project: str, pending_id: int, text: str, with_comments: bool = False) -> dict:
    """Answer a pending decision. The task becomes ready, and its next run is given the answer. The answer to a
    question is also written by code into the project's state file, as a decision of the user (L10), so that the
    next run finds it where the skills look for decisions; "state" says whether it was written. A failure there
    never undoes the answer: the store has it, and the next run's prompt carries it. With with_comments (the
    person's command, never a default), the open comments saved from the platform for the task, and for the
    documents its skill owns (its declared outputs), are appended under COMMENTS_LINE, one per line, oldest first,
    and marked used by this pending decision ("comments": their ids)."""
    ctx = context(project)
    said = _text(text, "the answer")
    if _stored(ctx, ctx["store"].pending_get, pending_id)["kind"] == "effect" and \
            APPROVAL_WORDS.fullmatch(said.strip()):
        raise OpsError(f"pending decision {pending_id} is an effect: an approval is given with approve --id {pending_id} "
                       "--sha256 <its hash>, never as an answer (the next run would read it as the skill's yes)", 2)
    used = []
    if with_comments:
        item = _stored(ctx, ctx["store"].pending_get, pending_id)
        saved = _stored(ctx, ctx["store"].comments_list, task_id=item["task_id"])
        skill = _stored(ctx, ctx["store"].task_get, item["task_id"])["skill"]
        if skill:
            try:
                owned = skill_meta.declared(os.path.join(ROOT, "skills", skill))["outputs"]
            except skill_meta.SkillError as e:
                raise OpsError(f"the comments of {skill}'s documents cannot be found: {e}", 1) from None
            saved += [c for c in _stored(ctx, ctx["store"].comments_list)
                      if c.get("document_path") and skill_meta.matches(owned, c["document_path"])]
            saved.sort(key=lambda c: c["id"])
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
    become ready. The delivery stays a draft: releasing is not approving. What a release starts (stage 6,
    _after_release) follows in the same call: the brief's delivery routed again (one run of the router, holding the
    run lock, so the release is refused while another run is in progress), the backlog's sub-tasks; its result is
    under "after"."""
    ctx = context(project)
    return _release(ctx, pending_id, by="user")


def _release(ctx: dict, pending_id: int, by: str) -> dict:
    """pending_resolve(released) and then _after_release, for the person (by "user") and for a mode ("mode:<mode>")."""
    item = _stored(ctx, ctx["store"].pending_get, pending_id)
    made = (item.get("payload") or {}).get("changeset") or {}
    if item["kind"] == "review" and made.get("blocked"):
        refused = "; ".join(f"{r['path'] or 'the whole set'}: {r['reason']}" for r in made.get("refused") or [])
        raise OpsError(f"pending decision {pending_id}: its change set is blocked ({refused}): answer with what to change, "
                       "or cancel the request", 1)
    task = _stored(ctx, ctx["store"].task_get, item["task_id"])
    lock = _run_lock(ctx["cfg"]) if item["kind"] == "review" and _brief_delivery(ctx, task) else contextlib.nullcontext()
    with lock:
        out = _stored(ctx, ctx["store"].pending_resolve, pending_id, resolution="released", by=by)
        after = _after_release(ctx, item)
    return {**out, "after": after} if after else out


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
    return {"accepted": sha256, "previous": previous, "path": cfg["path"], "checkpoints": _write_checkpoints(cfg)}


def _write_checkpoints(cfg: dict):
    """The state file's "- Checkpoints:" line rewritten from the area agents (autonomy.state_checkpoints): only its
    value changes, and only when the configuration has area agents and the file did not change between its read and
    the write (L12). Returns {"written", "value"}, or a text saying why nothing was written."""
    if cfg["raw"].get("area_agents") is None:
        return "no area agents are configured"
    target = os.path.join(cfg["project"], *path_rule.STATE.split("/"))
    if not os.path.isfile(target) or os.path.islink(target):
        return "the project has no state file"
    value = autonomy.state_checkpoints(cfg["area_agents"])
    before = _sha256(target)
    text, found = state_merge.with_checkpoints(_read(target), value)
    if not found:
        return "no line to write"
    if _sha256(target) != before:
        return "the state file changed while the line was being written; it is written at the next acceptance"
    temporary = f"{target}.{os.getpid()}.tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(temporary, target)
    return {"written": True, "value": value}


POLICY_EXPIRY_DAYS = 365  # a standing approval always has an expiry, at most this far ahead


def _policy_file(cfg: dict, file: str) -> tuple:
    """(relative path, absolute path) of a policy file: under docs/, a regular file whose real path is inside the
    project; else OpsError 2."""
    rel = (file or "").replace("\\", "/")
    parts = rel.split("/")
    if not rel or rel.startswith(("/", "~")) or any(p in ("", ".", "..") for p in parts) or parts[0] != "docs":
        raise OpsError(f"{file!r} is not a relative path under docs/ of the project", 2)
    target = os.path.join(cfg["project"], *parts)
    real = os.path.realpath(target)
    if not (real.startswith(cfg["project"] + os.sep)) or os.path.islink(target) or not os.path.isfile(real):
        raise OpsError(f"{rel} is not a regular file inside the project", 2)
    return rel, real


SIDE_EFFECTS_LINE = re.compile(r"^SIDE_EFFECTS = \(([^)]*)\)", re.M)


def _effect_words() -> tuple:
    """The closed vocabulary of side effects (contracts/environment.md), read from its one source in code, SIDE_EFFECTS
    of the checkout's scripts/validate.py, so the runtime keeps no copy of it."""
    found = SIDE_EFFECTS_LINE.search(_read(os.path.join(ROOT, "scripts", "validate.py")) or "")
    if not found:
        raise OpsError("the vocabulary of side effects (SIDE_EFFECTS of scripts/validate.py) cannot be read", 1)
    return tuple(word.strip().strip('"') for word in found.group(1).split(",") if word.strip())


def _policy_bounds(rel: str, real: str, agent: str) -> dict:
    """The bounds an approval of this file stores: a bounds file (.json) checked whole, else {"policy": <file name
    without extension>, "agent"} (a file a skill's own gate reads, such as an engagement policy); with "file", the
    path the approval binds."""
    if rel.endswith(".json"):
        try:
            with open(real, encoding="utf-8") as f:
                data = json.load(f)
            bounds = autonomy.bounds_of(data, agent, _effect_words())
        except (OSError, ValueError) as e:
            raise OpsError(f"{rel} is not a bounds file: {e}", 2) from None
    else:
        bounds = {"policy": os.path.splitext(os.path.basename(rel))[0], "agent": agent}
    return dict(bounds, file=rel)


def _standing_rows(ctx: dict) -> dict:
    """Write the standing rows of the state file from the store (state_merge.write_standing): one per policy file
    hash, the active approval else the newest expired one; only when the file did not change between its read and
    the write (L12). Returns {"state_rows", "superseded_rows"}, or {"written": false, "reason"}."""
    # T23: workaround 5, the copy a skill's gate reads until it reads the runtime's record
    cfg = ctx["cfg"]
    target = os.path.join(cfg["project"], *path_rule.STATE.split("/"))
    if not os.path.isfile(target) or os.path.islink(target):
        return {"written": False, "reason": "the project has no state file"}
    every = _stored(ctx, ctx["store"].approvals_list, scope="standing")
    chosen = {}
    for row in every:
        if row["status"] not in ("active", "expired"):
            continue
        held = chosen.get(row["policy_sha256"])
        rank = lambda r: (r["status"] == "active", r["id"])  # the active one, else the newest
        if held is None or rank(row) > rank(held):
            chosen[row["policy_sha256"]] = row
    rows = [["standing", f"{row['what']} (runtime #{row['id']})", f"policy:{row['policy_sha256']}",
             row["approved_at"][:10], (row["expires_at"] or "")[:10], row["status"]]
            for row in sorted(chosen.values(), key=lambda r: r["id"])]
    before = _sha256(target)
    try:
        text, written, superseded = state_merge.write_standing(
            _read(target), rows, {f"policy:{row['policy_sha256']}" for row in every if row["policy_sha256"]})
    except state_merge.Conflict as e:
        return {"written": False, "reason": str(e)}
    if _sha256(target) != before:
        return {"written": False, "reason": "the state file changed while the rows were being written; they are written at "
                                            "the next write"}
    temporary = f"{target}.{os.getpid()}.tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(temporary, target)
    return {"state_rows": written, "superseded_rows": superseded}


def approve_policy(project: str, file: str, agent: str, sha256: str | None = None, expires: str | None = None,
                   what: str | None = None) -> dict:
    """A standing approval of a policy file for one area agent (limits L15, L17; contracts/environment.md, rule 7).
    Without sha256: a preview ({"file", "agent", "policy", "bounds", "sha256", "next"}), nothing written. With it:
    refused unless it is the file's hash now and expires is a date YYYY-MM-DD after today and at most 365 days ahead;
    then, in one transaction, an active approval of the same policy and agent is revoked and the new row added, and
    the state file's generated standing rows are rewritten. Never granted by default, never without an expiry."""
    ctx = context(project)
    cfg = ctx["cfg"]
    if agent not in cfg["area_agents"]:
        raise OpsError(f"{agent!r} is not an agent of area_agents in {cfg['path']}", 2)
    rel, real = _policy_file(cfg, file)
    bounds = _policy_bounds(rel, real, agent)
    now_hash = _sha256(real)
    if sha256 is None:
        return {"file": rel, "agent": agent, "policy": bounds["policy"], "bounds": bounds, "sha256": now_hash,
                "next": f"approve-policy --file {rel} --agent {agent} --sha256 {now_hash} --expires <YYYY-MM-DD>"}
    if sha256 != now_hash:
        raise OpsError(f"{rel} has the hash {now_hash} now, not {sha256}: nothing was approved", 1)
    today = datetime.date.today()
    try:
        until = datetime.date.fromisoformat(str(expires)) if isinstance(expires, str) and len(expires) == 10 else None
    except ValueError:
        until = None
    if until is None or until <= today or until > today + datetime.timedelta(days=POLICY_EXPIRY_DAYS):
        raise OpsError(f"a standing approval needs --expires, a date YYYY-MM-DD after today and at most "
                       f"{POLICY_EXPIRY_DAYS} days ahead: nothing was approved", 1)
    row = _stored(ctx, ctx["store"].approval_standing_add, what=_text(what or bounds["policy"], "what"), by="user",
                  policy_sha256=now_hash, bounds=bounds, expires_at=f"{until.isoformat()}T23:59:59Z")
    return {**row, **_standing_rows(ctx)}


def revoke_policy(project: str, approval_id: int) -> dict:
    """End a standing approval: the row becomes revoked and its generated row leaves the state file."""
    ctx = context(project)
    item = _stored(ctx, ctx["store"].approval_get, approval_id)
    if item["scope"] != "standing" or item["status"] != "active":
        raise OpsError(f"approval {approval_id} is not an active standing approval", 2)
    row = _stored(ctx, ctx["store"].approval_revoke, approval_id, by="user")
    return {**row, **_standing_rows(ctx)}


def standing(project: str, policy: str) -> dict:
    """Whether an active standing approval covers a policy now: a read, it executes nothing. covered is true only
    when the row exists, its file hashes as approved, it has not expired and its agent acts in the mode
    autonomous-with-policy. executed_today counts today's actions of kind <policy> (the store's action_count)."""
    ctx = context(project)
    cfg = ctx["cfg"]
    now = datetime.datetime.now(datetime.timezone.utc)
    active = _stored(ctx, ctx["store"].approvals_list, status="active", scope="standing")
    found = [row for row in active if (row.get("bounds") or {}).get("policy") == policy]
    approval = found[-1] if found else None
    midnight = datetime.datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    executed = _stored(ctx, ctx["store"].action_count, kind=policy, since=midnight.isoformat())
    out = {"policy": policy, "covered": False, "why": "", "approval": None, "executed_today": executed, "mode": None}
    if approval is None:
        return {**out, "why": "no active standing approval names this policy"}
    agent = approval["bounds"].get("agent")
    out["approval"] = {key: approval.get(key) for key in ("id", "expires_at", "policy_sha256", "bounds")}
    out["approval"]["agent"] = agent
    out["mode"] = autonomy.mode_of(autonomy.facts(agent, cfg["area_agents"], active, now))
    rel = approval["bounds"].get("file")
    current = _sha256(os.path.join(cfg["project"], *rel.split("/"))) if rel else None
    if current != approval["policy_sha256"]:
        return {**out, "why": "the policy file changed since it was approved, or is gone"}
    if datetime.datetime.fromisoformat(approval["expires_at"].replace("Z", "+00:00")) <= now:
        return {**out, "why": "the approval expired"}
    if out["mode"] != autonomy.POLICY_MODE:
        return {**out, "why": f"the agent {agent} acts in the mode {out['mode']}, not {autonomy.POLICY_MODE}"}
    return {**out, "covered": True}


def set_mode(project: str, agent: str, mode: str) -> dict:
    """Set one area agent's autonomy mode: only area_agents.<agent>.mode of runtime.json changes (decision P1: the
    mode is the configuration's word). Every operation then refuses until the person accepts the new hash
    (accept-config), which also rewrites the state file's Checkpoints line. Returns {"agent", "mode",
    "config_sha256", "accepted": false, "next"}."""
    ctx = context(project)
    cfg = ctx["cfg"]
    if mode not in autonomy.MODES:
        raise OpsError(f"a mode is one of {', '.join(autonomy.MODES)}", 2)
    if agent not in cfg["area_agents"]:
        raise OpsError(f"{agent!r} is not an agent of area_agents in {cfg['path']}", 2)
    raw = json.loads(json.dumps(cfg["raw"]))
    raw["area_agents"][agent]["mode"] = mode
    temporary = f"{cfg['path']}.{os.getpid()}.tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        f.write(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
    os.replace(temporary, cfg["path"])
    new = _sha256(cfg["path"])
    return {"agent": agent, "mode": mode, "config_sha256": new, "accepted": False,
            "next": f"python3 runtime/cli.py accept-config --project {cfg['project']} --sha256 {new}"}


def status(project: str) -> dict:
    """{"config": {"path", "sha256"}, "requests": [{"id", "title", "flow", "state", "tasks": [{"id", "key",
    "skill", "state", "note"}]}], "pending": [...], "documents": [{"path", "status", "note", "on_platform"}],
    "board": {"left_out_final"} or None}: everything from the store's records. "left_out_final" is the number of
    tasks the board never mirrors because they were final when it was configured (runtime/board.py)."""
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
            "pending": [_listed(item) for item in _stored(ctx, ctx["store"].pending_list)],
            "documents": [{"path": d["path"], "status": d["status"], "note": d["note"], "on_platform": bool(d["remote_id"])}
                          for d in _stored(ctx, ctx["store"].documents_list)],
            "board": ({"left_out_final": len(_stored(ctx, lambda _conn: board.left_out(ctx, rows)))}
                      if board.enabled(ctx["cfg"]) else None)}


def progress(project: str, since: str | None = None) -> dict:
    """Where the work stands and what happened in a period, from the store's records only (runtime/progress.py): no
    model is called and no number is estimated. since is None (the last 7 days), "<n>d" or "YYYY-MM-DD". Returns
    {"progress", "summary", "text"}. The effects counted are the approvals code executed (status `executed`)."""
    ctx = context(project)
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        start, end = progress_calc.window(since, now)
    except ValueError as e:
        raise OpsError(str(e), 2) from None
    tasks = _stored(ctx, ctx["store"].tasks_list)
    runs = [run for task in tasks for run in _stored(ctx, ctx["store"].task_runs_list, task["id"])]
    pending_rows = _stored(ctx, ctx["store"].pending_list, "all")
    executed = _stored(ctx, ctx["store"].approvals_list, status="executed")
    now_progress = progress_calc.progress([t for t in tasks if t["parent_id"] is None], tasks, pending_rows, now)
    period = progress_calc.summary(tasks, runs, pending_rows, executed, start, end)
    return {"progress": now_progress, "summary": period, "text": progress_calc.render(now_progress, period)}


# --- stage 3: the route, the plan, its approval ------------------------------------------------------------------


def _with_agents(cfg: dict, tasks: list) -> list:
    """The tasks of a plan the person named, each with its area agent (plan.agent_of) when area agents are
    configured; without them every agent is None (stages 1 to 4)."""
    skills = plan.agent_skills(cfg, ROOT)
    return [dict(t, agent=plan.agent_of(t["skill"], skills) if skills else None) for t in tasks]


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
                tasks = _with_agents(ctx["cfg"], plan.from_flow(loaded, ROOT, plan.pack_skills(ctx["cfg"], ROOT)))
                decision = _plan_pending(ctx, request, tasks, None, "named", loaded["flow"])
            except flow_files.FlowError as e:
                raise OpsError(str(e), 2) from None
            except (plan.PlanError, lab.LabError, ValueError) as e:
                raise OpsError(f"no plan can be built: {e}", 1) from None
            opened = _stored(ctx, store.plan_open, request_id, title=decision["title"], body=decision["body"],
                             payload=decision["payload"])
            return {"routed": True, "pending_id": opened["pending_id"], "source": "named", "flow": loaded["flow"],
                    "cancelled": opened["cancelled"], "recovered": recovered["tasks"]}
        try:
            parts = plan.split(request["text"])
        except ValueError as e:
            raise OpsError(str(e), 2) from None
        if len(parts["items"]) > 1:
            return {**_route_deliveries(ctx, request, parts), "recovered": recovered["tasks"]}
        return {**_route_run(ctx, request), "recovered": recovered["tasks"]}


def _router_call(ctx: dict, request: dict, text: str, *, reroute: bool = False) -> dict:
    """One run of the router skill on a request, asked only for the route, with text as the request's words. Returns
    {"out", "failed"} and, for a run that did not fail, "response", "body", "finish" (the arguments of
    route_run_finish), "common" (the payload keys every decision of the run carries) and "read" (router.read_route).
    A failed run is finished here; a run that did not fail is finished by the caller, with its decision."""
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
                     skill_sha256=identity["content_sha256"], web=False, reroute=reroute)["run_id"]
    dest = os.path.join(cfg["data_dir"], RUNS_DIR, str(run_id))
    out = {"routed": False, "request": request["id"], "source": "router", "run_id": run_id, "run_dir": dest,
           "status": "failed", "ending": None, "failure": None, "pending_id": None, "kind": None, "kept": [],
           "left_out": [], "entered": None, "routing": routing, "use": None}

    def fail(kind: str, reason: str, attempts: int = 0, digest=None, redactions=None) -> dict:
        _stored(ctx, store.route_run_finish, run_id, status="failed", failure=kind, attempts=attempts,
                image_digest=digest, run_dir=dest, error=_note(reason), redactions=redactions)
        out["failure"] = {"kind": kind, "reason": _note(reason)}
        return {"out": out, "failed": True}

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
        answered = [] if reroute else [p for p in _stored(ctx, store.pending_list, "resolved", request["id"])
                                       if p["kind"] == "question" and p["resolution"] == "answered"]
        prompt = task_prompt(text, router.ROUTE_TASK_TEXT, answered)
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
    loaded = timing.get("skills_loaded")
    number = lambda key, kind: timing.get(key) if isinstance(timing.get(key), kind) and not isinstance(timing.get(key), bool) else None
    finish = dict(status="ok", attempts=counts["attempts"], cost_usd=number("cost_usd", (int, float)),
                  tokens=number("total_tokens", int), duration_ms=number("duration_ms", int),
                  skill_loaded=(skill in loaded) if isinstance(loaded, list) else None,
                  image_digest=result["image_digest"], run_dir=dest, redactions=_count(counts.get("redactions")))
    common = {"run_dir": dest, "response_file": os.path.join(result["outputs"], "response.md"), "kept": out["kept"],
              "routing": routing, "use": out["use"], "body_masked": masked}
    return {"out": out, "failed": False, "response": result["response"], "body": body, "finish": finish,
            "common": common, "read": router.read_route(result["response"])}


def _checked(ctx: dict, read: dict) -> dict:
    """read_route() of a reply with "checked": router.check_route() against the flow files and the pack in scope."""
    return dict(read, checked=router.check_route(read, flow_files.names(ROOT), plan.pack_skills(ctx["cfg"], ROOT)))


def _combined(ctx: dict, request: dict, routed: list) -> dict:
    """plan.combine for these routed deliveries, with the flow files they name, the agents' packs, the gate file's
    limits and the past runs of their skills. Raises plan.PlanError, ValueError, flow_files.FlowError."""
    cfg = ctx["cfg"]
    flows = {}
    for entry in routed:
        flow = ((entry.get("route") or {}).get("checked") or {}).get("flow")
        if flow and flow not in flows:
            flows[flow] = flow_files.load(flow, ROOT)
    reference = lab.reference("strong")
    limits = {"one_task_at_a_time": True, "timeout_seconds": reference["timeout_seconds"],
              "retries": reference["retries"]}
    skills = plan.agent_skills(cfg, ROOT)
    pack = plan.pack_skills(cfg, ROOT)
    out = plan.combine(request, routed, flows, skills, ROOT, pack=pack, limits=limits, past=[])
    past = []
    for skill in dict.fromkeys(t["skill"] for t in out["tasks"]):
        past += _stored(ctx, ctx["store"].task_runs_of_skill, skill)
    return plan.combine(request, routed, flows, skills, ROOT, pack=pack, limits=limits, past=past) if past else out


def _route_run(ctx: dict, request: dict) -> dict:
    """One run of the router on a request of one delivery (stage 3's behaviour): a valid route becomes a plan (through
    plan.combine), a reply that asks a question, anything else a question that names the flow command."""
    store = ctx["store"]
    call = _router_call(ctx, request, request["text"])
    out = call["out"]
    if call["failed"]:
        return out
    read, body, finish, common = call["read"], call["body"], call["finish"], call["common"]
    why = read.get("why")
    if read["kind"] == "route":
        decision = None
        try:
            route_read = _checked(ctx, read)
            if route_read["checked"]["ok"]:
                built = _combined(ctx, request, [{"item": request["text"], "route": route_read, "reply": body}])["plan"]
                decision = {"kind": "plan", **built}
            else:
                why = route_read["checked"]["why"]
        except (flow_files.FlowError, plan.PlanError, ValueError) as e:
            decision, why = None, f"no plan can be built from the route: {e}"
        if decision is not None:
            decision["payload"] = {**decision["payload"], **common}
            done = _stored(ctx, store.route_run_finish, out["run_id"], ending="done", pending=decision, **finish)
            out.update(status="ok", ending="done", routed=True, kind="plan", pending_id=done["pending_id"])
            return out
    if read["kind"] == "question":
        decision = {"kind": "question", "title": "The router asks", "body": body,
                    "payload": {"ending": "question", **common}}
        ending = "question"
    else:
        decision = _not_recognised(store, request, body, why, common)
        ending = "unclassified"
    done = _stored(ctx, store.route_run_finish, out["run_id"], ending=ending, pending=decision, **finish)
    out.update(status="ok", ending=ending, kind="question", pending_id=done["pending_id"])
    return out


def _not_recognised(store, request: dict, body: str, why, common: dict) -> dict:
    note = (f"\n\nName the flow with: route --request {request['id']} --flow <name>; or answer, and the router "
            f"runs again.")
    return {"kind": "question", "title": "The route was not recognised",
            "body": body.encode("utf-8")[:store.BODY_MAX - len(note.encode("utf-8"))].decode("utf-8", errors="ignore") + note,
            "payload": {"ending": "unclassified", "why": why, **common}}


def _item_text(preamble: str, item: str) -> str:
    return f"{preamble}\n\n{item}" if preamble else item


def _route_deliveries(ctx: dict, request: dict, parts: dict) -> dict:
    """A request that lists several deliveries (decision P3): one router run per item, each with the text
    "<preamble>\n\n<item>"; then one plan of every routed delivery, chained in the order listed (plan.combine),
    opened with the last run. An item whose reply asks, names no valid route or cannot be planned goes to the plan's
    "unrouted" with the whole reply. When no item was routed, the last run opens one question with every reply."""
    store = ctx["store"]
    routed, runs, last = [], [], None
    items = parts["items"]
    for k, item in enumerate(items, 1):
        call = _router_call(ctx, request, _item_text(parts["preamble"], item))
        if call["failed"]:
            return {**call["out"], "deliveries": len(items), "runs": runs + [call["out"]["run_id"]]}
        read = call["read"]
        entry = {"item": item, "route": None, "reply": call["body"]}
        if read["kind"] == "route":
            entry["route"] = _checked(ctx, read)
            ending = "done" if entry["route"]["checked"]["ok"] else "unclassified"
        else:
            entry["route"] = None if read["kind"] == "question" else read
            ending = "question" if read["kind"] == "question" else "unclassified"
        routed.append(entry)
        runs.append(call["out"]["run_id"])
        if k < len(items):
            _stored(ctx, store.route_run_finish, call["out"]["run_id"], ending=ending, **call["finish"])
        else:
            last = (call, ending)
    call, ending = last
    out = call["out"]
    try:
        combined = _combined(ctx, request, routed)
        why = None
    except (flow_files.FlowError, plan.PlanError, ValueError) as e:
        combined, why = None, f"no plan can be built from the routes: {e}"
    if combined is not None and combined["plan"] is not None:
        decision = {"kind": "plan", **combined["plan"]}
        decision["payload"] = {**decision["payload"], **call["common"], "router_runs": runs}
        kind = "plan"
    else:
        replies = "\n\n".join(f"--- delivery {n}: {e['item']} ---\n{e['reply'].rstrip()}" for n, e in enumerate(routed, 1))
        decision = _not_recognised(store, request, (why or "No delivery of the request was routed.") + "\n\n" + replies,
                                   why or "no delivery was routed", {**call["common"], "router_runs": runs})
        decision["title"] = "No delivery was routed"
        kind = "question"
    done = _stored(ctx, store.route_run_finish, out["run_id"], ending=ending, pending=decision, **call["finish"])
    out.update(status="ok", ending=ending, routed=kind == "plan", kind=kind, pending_id=done["pending_id"],
               deliveries=len(items), runs=runs,
               unrouted=len(combined["unrouted"]) if combined is not None else len(items))
    return out


# --- stage 6: what follows a release: the brief's delivery routed again, the backlog's sub-tasks ------------------


def _approved_plan(ctx: dict, request_id: int):
    """The payload of the request's approved `plan` pending decision (the newest), or None: the one source of the
    plan's deliveries and limits after its approval."""
    found = [p for p in _stored(ctx, ctx["store"].pending_list, "resolved", request_id)
             if p["kind"] == "plan" and p["resolution"] == "approved"]
    return found[-1]["payload"] if found else None


def _brief_delivery(ctx: dict, task: dict):
    """(k, delivery, plan payload) when task is the brief after which a delivery of its approved plan is routed again,
    else None."""
    if task.get("parent_id") is None:
        return None
    approved = _approved_plan(ctx, task["parent_id"]) or {}
    for k, delivery in enumerate(approved.get("deliveries") or [], 1):
        if delivery.get("reroute_after") and delivery["reroute_after"] == task["key"]:
            return k, delivery, approved
    return None


def _after_release(ctx: dict, item: dict) -> dict:
    """What a release of a review starts, by the person or by a mode (WP-6.5): (a) the brief's delivery routed again,
    with the brief's path from the files the run returned (never from the reply); (b) the backlog's sub-tasks, when the
    task's skill owns the product backlog and the run returned it. Returns {"reroute": ..., "subtasks": ...}, each only
    when it applied. The caller holds the run lock when (a) applies."""
    out = {}
    if item["kind"] != "review":
        return out
    task = _stored(ctx, ctx["store"].task_get, item["task_id"])
    returned = [r.get("path") for r in (item.get("payload") or {}).get("returned") or [] if isinstance(r, dict)]
    found = _brief_delivery(ctx, task)
    if found is not None:
        out["reroute"] = _reroute(ctx, task, returned, *found)
    if task.get("skill") and task["skill"] == plan.owner_of(plan.BACKLOG, ROOT) and plan.BACKLOG in returned:
        out["subtasks"] = _backlog_subtasks(ctx, task)
    return out


def _reroute(ctx: dict, task: dict, returned: list, k: int, delivery: dict, approved: dict) -> dict:
    """Route delivery k again, once, with the line "The brief is at <path>." added. A route to a flow or a skill opens
    an `acceptance` of kind subtasks with its tasks (keys d<k>-..., the first ones after the brief); a second route to
    the brief skill, a reply that asks or names no valid route, a missing brief or a failed run opens an `acceptance`
    of kind deliveries that shows the reason and the router's whole reply: the delivery reaches the person, never a
    third run."""
    store = ctx["store"]
    request = _stored(ctx, store.task_get, task["parent_id"])
    briefs = [rel for rel in returned if rel and rel.startswith(plan.BRIEFS_DIR)]
    if not briefs:
        return _not_rerouted(ctx, request, k, delivery, "the brief task returned no file under " + plan.BRIEFS_DIR, "")
    parts = plan.split(request["text"])
    text = _item_text(parts["preamble"] if len(parts["items"]) > 1 else "", delivery["item"]) + \
        f"\n\nThe brief is at {briefs[0]}."
    call = _router_call(ctx, request, text, reroute=True)
    if call["failed"]:
        return _not_rerouted(ctx, request, k, delivery, f"the router's run failed: {call['out']['failure']['reason']}",
                             "", run_id=call["out"]["run_id"])
    read, body = call["read"], call["body"]
    why, tasks = None, None
    if read["kind"] != "route":
        why = "the router asked" if read["kind"] == "question" else read.get("why") or "no route"
    else:
        route_read = _checked(ctx, read)
        checked = route_read["checked"]
        if not checked["ok"]:
            why = checked["why"]
        elif checked.get("skill") == plan.BRIEF_SKILL:
            why = "the router named the brief again: a delivery is routed again once"
        else:
            try:
                flows = {checked["flow"]: flow_files.load(checked["flow"], ROOT)} if "flow" in checked else {}
                tasks = plan.delivery_tasks(dict(route_read, title=delivery["item"][:120]), k, flows, ROOT,
                                            plan.pack_skills(ctx["cfg"], ROOT), prefix=True)
                skills = plan.agent_skills(ctx["cfg"], ROOT)
                inside = {t["key"] for t in tasks}
                for t in tasks:
                    if not [d for d in t["depends_on"] if d in inside]:
                        t["depends_on"] = [task["key"]] + t["depends_on"]
                    t["agent"] = plan.agent_of(t["skill"], skills) if skills else None
            except (flow_files.FlowError, plan.PlanError, ValueError) as e:
                why, tasks = f"no task can be planned from the route: {e}", None
    finish = call["finish"]
    if tasks is None:
        decision = _not_rerouted_decision(request, k, delivery, why, body, call["common"])
        ending = "question" if read["kind"] == "question" else "unclassified"
    else:
        lines = [f"Delivery {k} ({delivery['item']}) was routed again after its brief ({briefs[0]}): {read['line']}.",
                 "Accept to add these tasks to request " + str(request["id"]) + ":", ""]
        lines += [f"- {t['key']}: {t['title']} ({t['skill']}, agent {t['agent'] or 'none'})" for t in tasks]
        decision = {"kind": "acceptance", "title": f"Accept the tasks of delivery {k}, routed after its brief",
                    "body": "\n".join(lines), "payload": {"what": "subtasks", "delivery": k, "brief": briefs[0],
                                                          "route": read["line"], "tasks": tasks, **call["common"]}}
        ending = "done"
    done = _stored(ctx, store.route_run_finish, call["out"]["run_id"], ending=ending, pending=decision, **finish)
    return {"delivery": k, "run_id": call["out"]["run_id"], "pending_id": done["pending_id"],
            "routed": tasks is not None, "why": why}


def _not_rerouted_decision(request: dict, k: int, delivery: dict, why: str, reply: str, common: dict) -> dict:
    body = (f"Delivery {k} of request {request['id']} ({delivery['item']}) was not planned after its brief: {why}. "
            "Accepting records that you read this; start a new request for this delivery when you want it.")
    if reply:
        body += "\n\nThe router's reply, whole:\n\n" + reply
    return {"kind": "acceptance", "title": f"Delivery {k} was not routed after its brief",
            "body": body, "payload": {"what": "deliveries", "delivery": k, "why": why, **common}}


def _not_rerouted(ctx: dict, request: dict, k: int, delivery: dict, why: str, reply: str, run_id=None) -> dict:
    decision = _not_rerouted_decision(request, k, delivery, why, reply, {})
    opened = _stored(ctx, ctx["store"].acceptance_open, task_id=request["id"], what="deliveries",
                     title=decision["title"], body=decision["body"], payload=decision["payload"])
    return {"delivery": k, "run_id": run_id, "pending_id": opened["pending_id"], "routed": False, "why": why}


def _backlog_subtasks(ctx: dict, task: dict) -> dict:
    """The product backlog's todo tasks as sub-tasks of the request, within the limits of its approved plan (read from
    that plan's payload and nowhere else): those inside are added at once (tasks_add), the others wait in one
    `acceptance` of kind subtasks. A task the request already has is not proposed again."""
    store, request_id = ctx["store"], task["parent_id"]
    approved = _approved_plan(ctx, request_id) or {}
    limits = approved.get("limits") or {}
    try:
        proposed = plan.backlog_tasks(os.path.join(ctx["cfg"]["project"], *plan.BACKLOG.split("/")), ROOT)
    except ValueError as e:
        return {"error": str(e)}
    rows = [t for t in _stored(ctx, store.tasks_list, request_id) if t["parent_id"] is not None]
    known = {t["key"] for t in rows if t.get("key")}
    planned = {t.get("key") for t in approved.get("tasks") or []}
    proposed = [p for p in proposed if p["key"] not in known]
    if not proposed:
        return {"created": [], "pending_id": None}
    skills = plan.agent_skills(ctx["cfg"], ROOT)
    for p in proposed:
        try:
            p["agent"] = plan.agent_of(p["skill"], skills) if skills else None
        except ValueError:
            p["agent"] = None  # no agent owns it: it waits, and the person can run it by hand
    chosen = plan.subtasks(limits, len([t for t in rows if t.get("key") not in planned]), proposed, known)
    created = _stored(ctx, store.tasks_add, request_id, chosen["create"])["tasks"] if chosen["create"] else []
    pending_id = None
    if chosen["ask"]:
        lines = [f"The product backlog proposes {len(chosen['ask'])} task(s) outside the approved plan's limits "
                 f"({limits.get('max_subtasks', 0)} sub-tasks of {', '.join(limits.get('subtask_skills') or []) or 'no skill'}):", ""]
        lines += [f"- {t['key']}: {t['title']}" + (f" (after {', '.join(t['depends_on'])})" if t["depends_on"] else "")
                  for t in chosen["ask"]]
        pending_id = _stored(ctx, store.acceptance_open, task_id=request_id, what="subtasks",
                             title=f"Accept {len(chosen['ask'])} sub-task(s) of request {request_id}",
                             body="\n".join(lines), payload={"tasks": chosen["ask"]})["pending_id"]
    return {"created": [t["id"] for t in created], "pending_id": pending_id}


def approve(project: str, pending_id: int, sha256: str | None = None) -> dict:
    """Approve a pending decision of kind `plan` (its tasks are created as the plan lists them, and those with no
    dependency are ready) or `acceptance` (the request written on the task board is kept, and waits for its route).
    With sha256, a plan is approved only when it is the plan's hash. An `effect` (stage 4) is approved only with
    its hash, and code then executes it: the one commit through the code provider, then the pull request; nothing is
    sent when anything moved since the gate, and a failure leaves it open, approved again with the same hash."""
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
    if item["kind"] == "effect":
        return _approve_effect(ctx, item, sha256)
    raise OpsError(f"pending decision {pending_id} is a {item['kind']}: approve takes a plan, an acceptance or an effect; "
                   "a question or a review is answered or released", 2)


def sync(project: str, dry_run: bool = False, take: str | None = None, path: str | None = None) -> dict:
    """Mirror the project's task board (runtime/board.py) and its documents (runtime/documents.py), holding the run
    lock. The board: pull (the board to the store; not on a dry run, which reads nothing), then push (the store to
    the board; with dry_run, every write the provider would make, and nothing changes). The documents, after the
    board: pull (the platform to the project; not on a dry run), then push of every project document a manifest
    entry mirrors. take ("page" or "project") with path settles a document that was not taken (documents.take),
    and does nothing else. Returns {"board": {"pulled", "created", "edited", "refused", "gone", "comments",
    "left_out_final", "pushed", "failed"[, "would"]} or None, "documents": {"imported", "not_taken", "conflicts", "rejected", "comments", "gone",
    "pushed", "failed"[, "would"]} or None}."""
    if take is not None and take not in ("page", "project"):
        raise OpsError("take is page or project", 2)
    if (take is None) != (path is None):
        raise OpsError("take and path go together", 2)
    ctx = context(project)
    out = {"board": None, "documents": None}
    with _run_lock(ctx["cfg"]):
        if take is not None:
            if not documents.enabled(ctx["cfg"]):
                raise OpsError("take settles a document of the documents platform, and none is configured", 3)
            out["documents"] = _documents(ctx, documents.take, ctx, path, take)
            return out
        if board.enabled(ctx["cfg"]):
            try:
                pulled = ({"pulled": [], "created": [], "edited": [], "refused": [], "gone": [], "comments": 0,
                           "left_out_final": len(board.left_out(ctx))} if dry_run else board.pull(ctx))
                out["board"] = {**pulled, **board.push(ctx, dry_run=dry_run)}
            except board.BoardError as e:
                raise OpsError(f"the task board: {e}", 3 if e.kind == "not configured" else 1) from None
            except ctx["store"].StoreError as e:
                raise OpsError(str(e), e.code) from None
        if documents.enabled(ctx["cfg"]):
            pulled = _documents(ctx, documents.pull, ctx, dry_run=dry_run)
            pushed = _documents(ctx, lambda: documents.push(ctx, documents.mirrored_paths(ctx), dry_run=dry_run))
            out["documents"] = documents.merged(pulled, pushed)
    return out


def _documents(ctx: dict, function, *args, **kwargs):
    """Call one function of runtime/documents.py; its refusal becomes this layer's."""
    try:
        return function(*args, **kwargs)
    except documents.DocumentsError as e:
        raise OpsError(f"the documents platform: {e}", 3 if e.kind == "not configured" else 1) from None
    except ctx["store"].StoreError as e:
        raise OpsError(str(e), e.code) from None


def hand_over(project: str, task_id: int, file: str) -> dict:
    """Put one file of the person's in a task's file drop, <project>/.workbench-local/drop/<task id>/ (runtime/drop.py):
    it enters the runs of that task only, and their prompt lists it. Holds the run lock, so no run of the task is in
    progress. Returns {"task", "path", "bytes", "sha256"}; refused (drop.DropError) with the reason."""
    ctx = context(project)
    with _run_lock(ctx["cfg"]):
        task = _stored(ctx, ctx["store"].task_get, task_id)
        if task["parent_id"] is None or not task.get("skill"):
            raise OpsError(f"{task_id} is a request: a file is handed to one of its tasks", 1)
        try:
            meta = skill_meta.declared(os.path.join(ROOT, "skills", task["skill"]))
        except skill_meta.SkillError as e:
            raise OpsError(str(e), 1) from None
        try:
            return drop.hand_over(ctx["cfg"]["project"], {**task, "web": meta["web"]}, os.path.abspath(file),
                                  drop.WEB_TASK_TAKES_DROP)
        except drop.DropError as e:
            raise OpsError(str(e), 1) from None


def reject(project: str, pending_id: int, note: str | None = None) -> dict:
    """Reject a pending decision of kind `plan` or `acceptance`: the request is cancelled, with what is open under
    it. A note is kept on a rejected plan. An `effect` rejected cancels its task, and nothing is sent."""
    ctx = context(project)
    item = _stored(ctx, ctx["store"].pending_get, pending_id)
    if item["kind"] == "plan":
        said = _text(note, "the note") if note is not None else None
        return _stored(ctx, ctx["store"].plan_reject, pending_id, by="user", note=said)
    if item["kind"] == "acceptance":
        return _stored(ctx, ctx["store"].acceptance_resolve, pending_id, resolution="rejected", by="user")
    if item["kind"] == "effect":
        said = _text(note, "the note") if note is not None else None
        return _stored(ctx, ctx["store"].pending_resolve, pending_id, resolution="rejected", by="user", answer=said)
    raise OpsError(f"pending decision {pending_id} is a {item['kind']}: reject takes a plan, an acceptance or an effect", 2)


# --- stage 6: the dispatcher's operations ----------------------------------------------------------------------------

DISPATCH_BUDGET = 2700     # seconds after which a round starts no new run (the worker's limit is 240 minutes)
HANDLER_TIMEOUT = 1800     # seconds a handler's verb may take
PER_RUN_USD = 0.5          # what a floor run of unknown cost counts at, when runtime.json names no max_cost_usd_per_run
# A run that failed so: the next run of the round would fail the same way, so the round stops.
STOPPING_FAILURES = ("auth", "settings")
STOPPING_REASONS = ("container:", "config:")  # a LabError of these kinds, recorded as an internal failure


def _midnight_utc() -> str:
    """The start of today, local time, as UTC ISO-8601: where a day's caps start counting."""
    local = datetime.datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    return local.astimezone(datetime.timezone.utc).isoformat()


def _snapshot(ctx: dict, key: dict) -> dict:
    """What dispatcher.decide reads, from the store, the proof (proof.route through _route) and the runtime manifests:
    the running task, the ready tasks oldest first with the tier each would run on, the open reviews with their
    agent, proof and mandatory flag, and each area agent's facts, a day's spend and its entry. A run of the router
    (its task is a request, so its agent is None) counts against the planning agent."""
    store, cfg = ctx["store"], ctx["cfg"]
    agents = cfg["area_agents"]
    now = datetime.datetime.now(datetime.timezone.utc)
    tasks = _stored(ctx, store.tasks_list)
    by_id = {t["id"]: t for t in tasks}
    standing_rows = _stored(ctx, store.approvals_list, status="active", scope="standing")
    runs = [dict(r, agent=plan.PLANNING) if r.get("agent") is None and r.get("skill") == router.ROUTER_SKILL else r
            for r in _stored(ctx, store.runs_since, _midnight_utc())]
    reference, floor = lab.reference("strong")["model"], lab.reference("floor")["model"]
    per_run = cfg["raw"].get("max_cost_usd_per_run", PER_RUN_USD)
    proofs = {}

    def routed(skill: str) -> dict:
        if skill not in proofs:
            proofs[skill] = _route(ctx, skill, skill_meta.declared(os.path.join(ROOT, "skills", skill)), None, key)
        return proofs[skill]

    out = {"running": next((t for t in tasks if t["state"] == "running"), None),
           "ready": [t for t in tasks if t["state"] == "ready" and t["parent_id"] is not None],
           "reviews": [], "agents": {}, "tier": {}}
    for name, entry in agents.items():
        facts = autonomy.facts(name, agents, standing_rows, now)
        out["agents"][name] = {"facts": facts, "entry": entry,
                               "spent": autonomy.spend(runs, name, reference, floor, per_run)}
    for item in _stored(ctx, store.pending_list):
        task = by_id.get(item["task_id"])
        if item["kind"] != "review" or task is None or not task.get("skill"):
            continue
        out["reviews"].append({"pending": item, "task": task, "agent": task.get("agent"),
                               "proven": bool(routed(task["skill"]).get("proven")),
                               "mandatory": plan.mandatory(task["skill"], ROOT)})
    for task in out["ready"]:
        if task.get("agent") in agents and task.get("skill"):
            out["tier"][task["id"]] = routed(task["skill"])["tier"]
    return out


def _mode_releases(ctx: dict, released: list, snapshot: dict, decided: dict, skip=None) -> list:
    """Apply the releases a decision lists, each as the mode of its agent (by "mode:<mode>"), with what a release starts
    (_after_release). A review skip(task) names is left for later (poll leaves the brief's release, which runs the
    router, to dispatch). When a release by a mode completes a request, one acceptance of kind deliveries lists every
    delivery a mode released in it (part 0, F.3). Returns [{"pending_id", "task_id", "by", ...}]."""
    reviews = {r["pending"]["id"]: r for r in snapshot["reviews"]}
    agents = snapshot["agents"]
    out = []
    for pending_id in decided["release"]:
        review = reviews[pending_id]
        if skip is not None and skip(review["task"]):
            continue
        by = "mode:" + autonomy.mode_of(agents[review["agent"]]["facts"])
        done = _release(ctx, pending_id, by=by)
        out.append({"pending_id": pending_id, "task_id": review["task"]["id"], "by": by,
                    **({"after": done["after"]} if done.get("after") else {})})
        released.append(pending_id)
        for request_id in done.get("completed") or []:
            out[-1]["acceptance"] = _deliveries_acceptance(ctx, request_id)
    return out


def _deliveries_acceptance(ctx: dict, request_id: int):
    """One acceptance of kind deliveries on a request a mode completed, listing every delivery a mode released in it;
    None when no delivery of it was released by a mode."""
    store = ctx["store"]
    tasks = {t["id"]: t for t in _stored(ctx, store.tasks_list, request_id) if t["parent_id"] is not None}
    by_mode = [p for p in _stored(ctx, store.pending_list, "resolved")
               if p["task_id"] in tasks and p["kind"] == "review" and p["resolution"] == "released"
               and str(p.get("resolved_by") or "").startswith("mode:")]
    if not by_mode:
        return None
    lines = [f"Request {request_id} is done, and an autonomy mode released these deliveries without you. Each stays a "
             "draft: read it, then accept (a note records what you think), or reject.", ""]
    lines += [f"- task {p['task_id']} ({tasks[p['task_id']]['skill']}): {tasks[p['task_id']]['title']}, released by "
              f"{p['resolved_by']}, pending decision {p['id']}" for p in by_mode]
    return _stored(ctx, store.acceptance_open, task_id=request_id, what="deliveries",
                   title=f"Accept the deliveries of request {request_id}", body="\n".join(lines),
                   payload={"released": [p["id"] for p in by_mode]})["pending_id"]


def _stops_the_round(ran: dict):
    """The reason a round stops after this run, or None: a failure the next run would repeat."""
    failure = ran.get("failure") or {}
    if failure.get("kind") in STOPPING_FAILURES:
        return f"a run failed ({failure['kind']}): the next run would fail the same way"
    if failure.get("kind") == "internal" and str(failure.get("reason") or "").startswith(STOPPING_REASONS):
        return f"a run could not reach the container ({failure['reason'][:200]}): the next run would fail the same way"
    return None


def dispatch(project: str, budget_seconds=None) -> dict:
    """The dispatcher (decision P5): one round. The handlers whose `dispatch` is true and whose agent is enabled get
    their tick; then, until nothing may start: the reviews each agent's mode releases are released (with what a release
    starts), and the oldest ready task whose agent may start (its mode, its daily caps on the tier its proof gives) runs,
    as run_next runs a task. No new run starts once budget_seconds (default DISPATCH_BUDGET) have passed, and a failure
    the next run would repeat stops the round. Returns {"handlers", "released", "ran", "held", "stopped"}."""
    started = time.monotonic()
    ctx = context(project)
    cfg = ctx["cfg"]
    budget = DISPATCH_BUDGET if budget_seconds is None else budget_seconds
    if not cfg["area_agents"]:
        return {"stopped": "no area agent is configured"}
    out = {"handlers": _ticks(ctx, project), "released": [], "ran": [], "held": [], "stopped": None}
    key = _floor_key()
    released, checked = [], {}
    while out["stopped"] is None:
        snapshot = _snapshot(ctx, key)
        decided = dispatcher.decide(snapshot, autonomy.review_action, autonomy.may_start)
        out["held"] = decided["held"]
        did = _mode_releases(ctx, released, snapshot, decided)
        out["released"] += did
        if decided["start"] is None:
            if did:
                continue  # a release may have made a task ready
            out["stopped"] = "nothing may start" if decided["held"] or snapshot["ready"] else "no task is ready"
            break
        if time.monotonic() - started > budget:
            out["stopped"] = f"the round's budget of {budget} s is spent: no new run starts"
            break
        if snapshot["tier"].get(decided["start"]) == "strong":
            if "credential" not in checked:
                checked["credential"] = _credential_stop()
            if checked["credential"]:
                out["stopped"] = checked["credential"]
                break
        try:
            ran = _claim_and_run(ctx, None, decided["start"])
        except OpsError as e:
            out["stopped"] = f"task {decided['start']} could not run: {e}"
            break
        if ran.get("ran") is None:
            out["stopped"] = ran.get("reason") or "nothing ran"
            break
        out["ran"].append({"task_id": ran["ran"], "run_id": ran["run_id"], "status": ran["status"],
                           "ending": ran["ending"], "model": (ran.get("routing") or {}).get("model")})
        out["stopped"] = _stops_the_round(ran)
    return out


PIN_NAME = "dispatch-pin.json"


def pin(project: str) -> dict:
    """The pin of the dispatcher's two jobs, <data_dir>/dispatch-pin.json (mode 0600): the path and the hash of the
    project's runtime.json, which must be the accepted one. The scheduler's entry (runtime/dispatcher.py) refuses to
    load anything when the file differs from it. Returns {"pin", "runtime_json", "next"}."""
    ctx = context(project)
    cfg = ctx["cfg"]
    pinned = {"runtime_json": {"path": cfg["path"], "sha256": cfg["sha256"]},
              "pinned_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    os.makedirs(cfg["data_dir"], mode=0o700, exist_ok=True)
    target = os.path.join(cfg["data_dir"], PIN_NAME)
    temporary = f"{target}.{os.getpid()}.tmp"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(pinned, indent=1) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)
    return {"pin": target, "runtime_json": pinned["runtime_json"],
            "next": f"dispatcher.py command-file --job poll|work --project {cfg['project']} --pin {target}, then schedule "
                    "each with the scheduler provider"}


def _credential_stop():
    """Why no run on the reference model can start from this process, or None: its credential is neither set nor
    found in the secret store (lab.credential_missing). Named with the interpreter, since a scheduled job's
    interpreter may not read the store (open point O1)."""
    missing = lab.credential_missing("strong")
    if not missing:
        return None
    return (f"the reference model's credential ({', '.join(missing)}) is neither set nor found in the secret store "
            f"from {sys.executable} (Python {sys.version.split()[0]}): no run starts. See contracts/runtime.md, "
            "\"The dispatcher's two jobs\"")


def _ticks(ctx: dict, project: str) -> dict:
    """The tick of every handler whose `dispatch` is true and whose agent is enabled; a failure is recorded, never
    raised."""
    out = {}
    agents = ctx["cfg"]["area_agents"]
    for name, entry in sorted((ctx["cfg"].get("handlers") or {}).items()):
        agent = agents.get(entry.get("agent")) or {}
        if not entry.get("dispatch") or not agent.get("enabled") or agent.get("mode") == "stopped":
            continue
        try:
            out[name] = handler_call(project, name, "tick")
        except OpsError as e:
            out[name] = {"error": str(e), "code": e.code}
    return out


def poll(project: str) -> dict:
    """The short job (decision P5): mirror the task board and the documents when the project has them (an error is
    recorded, not raised), expire the standing approvals past their expiry, rewrite the state file's generated lines
    (the Checkpoints line, the standing rows) when they changed, and release what each agent's mode releases. It calls
    no model and starts no task: the release of a brief, which runs the router, is left to dispatch. Returns {"synced",
    "expired", "released", "state"}."""
    ctx = context(project)
    cfg, store = ctx["cfg"], ctx["store"]
    synced = None
    if board.enabled(cfg) or documents.enabled(cfg):
        try:
            synced = sync(project)
        except OpsError as e:
            synced = {"error": str(e), "code": e.code}
    expired = _stored(ctx, store.approvals_expire, datetime.datetime.now(datetime.timezone.utc).isoformat())
    state = "unchanged"
    if expired:
        rows = _standing_rows(ctx)
        state = "written" if rows.get("state_rows") is not None else state
    if cfg["raw"].get("area_agents") is not None:
        target = os.path.join(cfg["project"], *path_rule.STATE.split("/"))
        current = _read(target) if os.path.isfile(target) and not os.path.islink(target) else None
        if current is not None:
            text, found = state_merge.with_checkpoints(current, autonomy.state_checkpoints(cfg["area_agents"]))
            if found and text != current and isinstance(_write_checkpoints(cfg), dict):
                state = "written"
    released = []
    if cfg["area_agents"]:
        snapshot = _snapshot(ctx, _floor_key())
        decided = dispatcher.decide(snapshot, autonomy.review_action, autonomy.may_start)
        released = _mode_releases(ctx, [], snapshot, decided, skip=lambda task: _brief_delivery(ctx, task) is not None)
    return {"synced": synced, "expired": expired, "released": released, "state": state}


def _handler_verbs(path: str) -> tuple:
    """The words of a handler's VERBS constant, read with ast, without importing the file."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "VERBS" for t in node.targets):
            value = ast.literal_eval(node.value)
            if isinstance(value, (tuple, list)) and all(isinstance(v, str) for v in value):
                return tuple(value)
    return ()


def handler_call(project: str, name: str, verb: str, args=None) -> dict:
    """Start one verb of a handler (runtime/handlers/<name with underscores>.py of the checkout) with this interpreter
    and --project, and return the one JSON object it printed, with "exit_code". name is a key of the configuration's
    handlers; verb is a word of the file's VERBS; args is {flag: value}, passed as --flag value. Anything else: OpsError
    2. Output that is not one JSON object: OpsError 1, with the end of its stderr."""
    ctx = context(project)
    handlers = ctx["cfg"].get("handlers") or {}
    if name not in handlers:
        raise OpsError(f"{name!r} is not a handler of {ctx['cfg']['path']}", 2)
    path = os.path.join(ROOT, "runtime", "handlers", name.replace("-", "_") + ".py")
    if not os.path.isfile(path) or os.path.islink(path):
        raise OpsError(f"the handler {name} has no file runtime/handlers/{os.path.basename(path)} in this checkout", 2)
    try:
        verbs = _handler_verbs(path)
    except (OSError, SyntaxError, ValueError) as e:
        raise OpsError(f"the handler {name}'s verbs cannot be read: {type(e).__name__}", 2) from None
    if verb not in verbs:
        raise OpsError(f"the handler {name} has no verb {verb!r} (its verbs: {', '.join(verbs) or 'none'})", 2)
    flags = []
    for flag, value in sorted((args or {}).items()):
        if not isinstance(flag, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", flag) or flag == "project":
            raise OpsError(f"{flag!r} is not a flag a handler takes", 2)
        flags += [f"--{flag}", str(value)]
    try:
        done = subprocess.run([sys.executable, path, verb, "--project", ctx["cfg"]["project"], *flags],
                              capture_output=True, text=True, timeout=HANDLER_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        raise OpsError(f"the handler {name} {verb} ran over {HANDLER_TIMEOUT} s", 1) from None
    except OSError as e:
        raise OpsError(f"the handler {name} could not be started: {type(e).__name__}", 1) from None
    try:
        printed = json.loads(done.stdout)
    except ValueError:
        printed = None
    if not isinstance(printed, dict):
        raise OpsError(f"the handler {name} {verb} printed no JSON object (exit {done.returncode}): "
                       f"{done.stderr.strip()[-300:]}", 1)
    return {**printed, "exit_code": done.returncode}


# --- stage 6: the conversation with the planning agent ----------------------------------------------------------------

CONVERSATION = "project"  # one conversation per project until the local interface (stage 9)
MEMORY_TURNS = 6
MEMORY_CHARS = 4000
MEMORY_CUT = 600
MEMORY_HEAD = "Earlier in this conversation, oldest first:"
MEMORY_TAIL = "The request now:"
SAY_COMMANDS = ("/help", "/status", "/progress", "/pending", "/answer", "/release", "/approve", "/reject", "/retry",
                "/cancel", "/new")
SAY_HELP = """Commands, one per line; any other line is a request for the planning agent, or the answer to its question:
/help                      this text
/status                    requests, tasks and what waits for you
/progress [since]          where the work stands and what happened (since: 7d, <n>d or YYYY-MM-DD)
/pending [id]              what waits for you; with an id, that decision whole
/answer <id> <text>        answer a pending decision
/release <id>              release a delivery (it stays a draft)
/approve <id> [sha256]     approve a plan, an acceptance, or an effect with its hash
/reject <id> [note]        reject a plan, an acceptance or an effect
/retry <task id>           make a failed or blocked task ready again
/cancel <request id>       cancel a request
/new <text>                start a new request, whatever is open"""
PLAN_NEXT = "Approve with /approve {pending}"
ASK_NEXT = "Answer with a plain line, or start again with /new <text>"


def chat_memory(messages: list, settled: set) -> str:
    """The conversation's memory for the router (T23: workaround 2, the floor model's adapter takes the request as one
    argument, so the memory travels inside it, bounded): the plain lines and the router's replies after the newest
    reply whose request reached `planned`, `done` or `cancelled` (settled: those request ids); commands and their
    replies are left out. The newest MEMORY_TURNS, oldest first, each `<role>: <text>` on one line cut to MEMORY_CUT
    characters, the whole cut to MEMORY_CHARS by dropping the oldest. Empty when there is none: the first line of an
    exchange reaches the router plain."""
    # T23: workaround 2, the conversation's memory as a bounded text in the request
    start = 0
    for n, m in enumerate(messages):
        if m["role"] == "assistant" and m.get("task_id") in settled:
            start = n + 1
    kept = [m for m in messages[start:] if (m["role"] == "user" and not m["text"].startswith("/")) or
            (m["role"] == "assistant" and m.get("task_id") is not None)][-MEMORY_TURNS:]
    lines = [f"{m['role']}: {' '.join(m['text'].split())[:MEMORY_CUT]}" for m in kept]
    while lines and len("\n".join([MEMORY_HEAD, *lines])) > MEMORY_CHARS:
        lines.pop(0)
    return "\n".join([MEMORY_HEAD, *lines]) if lines else ""


def say(project: str, text: str) -> dict:
    """One turn of the conversation with the planning agent (decision D12), one more shell of this layer. The person's
    line is stored; a line that starts with "/" is one command of SAY_COMMANDS, which calls its operation once; a plain
    line answers the router's open question on the conversation's last request, or else is a new request routed with
    the conversation's memory in front of it (one or more runs of the router: a model call), refused when the planning
    agent may not start. The reply is stored too. A model's reply is shown, never executed. Returns {"reply",
    "request_id", "pending_id", "ran"}."""
    ctx = context(project)
    said = _text(text, "the line")
    store = ctx["store"]
    _stored(ctx, store.message_add, conversation=CONVERSATION, role="user", text=said)
    request_id, pending_id, ran, run_id = None, None, False, None
    if said.startswith("/"):
        reply, request_id, pending_id, ran, run_id = _say_command(project, ctx, said)
    else:
        last = _last_request(ctx)
        asked = _router_question(ctx, last)
        if asked is not None:
            reply, request_id, pending_id, ran, run_id = _say_route(project, ctx, said, answer_to=asked)
        else:
            reply, request_id, pending_id, ran, run_id = _say_route(project, ctx, said)
    _stored(ctx, store.message_add, conversation=CONVERSATION, role="assistant", text=reply or "(no reply)",
            task_id=request_id, run_id=run_id)
    return {"reply": reply, "request_id": request_id, "pending_id": pending_id, "ran": ran}


def _last_request(ctx: dict):
    """The request of the conversation's newest message that names one, or None."""
    for m in reversed(_stored(ctx, ctx["store"].messages_list, CONVERSATION, limit=500)):
        if m.get("task_id") is not None:
            return m["task_id"]
    return None


def _router_question(ctx: dict, request_id):
    """The newest open pending decision of the request, when it is a question on the request itself (the router
    asked); else None."""
    if request_id is None:
        return None
    request = _stored(ctx, ctx["store"].task_get, request_id)
    if request["parent_id"] is not None or request["state"] != "requested":
        return None
    open_items = _stored(ctx, ctx["store"].pending_list, "open", request_id)
    return open_items[-1]["id"] if open_items and open_items[-1]["kind"] == "question" else None


def _say_command(project: str, ctx: dict, said: str) -> tuple:
    """(reply, request_id, pending_id, ran, run_id) of a command line: each calls its operation once, and a line that
    is not one of SAY_COMMANDS with its arguments gets the help."""
    word, _, rest = said.partition(" ")
    rest = rest.strip()
    parts = rest.split(None, 1)
    number = lambda value: int(value) if value is not None and value.isdigit() else None
    first = number(parts[0]) if parts else None
    second = parts[1].strip() if len(parts) > 1 else None
    if word == "/new" and rest:
        return _say_route(project, ctx, rest)
    if word == "/progress":
        return progress(project, rest or None)["text"], None, None, False, None
    calls = {
        "/status": (lambda: status(project)) if not rest else None,
        "/pending": (lambda: pending(project, first)) if not rest or first is not None and len(parts) == 1 else None,
        "/answer": (lambda: answer(project, first, second)) if first is not None and second else None,
        "/release": (lambda: release(project, first)) if first is not None and len(parts) == 1 else None,
        "/approve": (lambda: approve(project, first, second)) if first is not None else None,
        "/reject": (lambda: reject(project, first, second)) if first is not None else None,
        "/retry": (lambda: retry(project, first)) if first is not None and len(parts) == 1 else None,
        "/cancel": (lambda: cancel(project, first)) if first is not None and len(parts) == 1 else None,
    }
    call = calls.get(word)
    if call is None:
        return SAY_HELP, None, None, False, None
    try:
        out = call()
    except OpsError as e:
        return f"error: {e}", None, None, False, None
    return json.dumps(out, ensure_ascii=False, indent=1, default=str), None, None, False, None


def _planning_may_start(ctx: dict) -> tuple:
    """Whether the planning agent may run the router now (autonomy.may_start, on the tier the router's proof gives,
    with the day's runs of the router counted against it)."""
    cfg, store = ctx["cfg"], ctx["store"]
    agents = cfg["area_agents"]
    meta = skill_meta.declared(os.path.join(ROOT, "skills", router.ROUTER_SKILL))
    tier = _route(ctx, router.ROUTER_SKILL, meta, None, _floor_key())["tier"]
    now = datetime.datetime.now(datetime.timezone.utc)
    standing_rows = _stored(ctx, store.approvals_list, status="active", scope="standing")
    runs = [dict(r, agent=plan.PLANNING) if r.get("agent") is None and r.get("skill") == router.ROUTER_SKILL else r
            for r in _stored(ctx, store.runs_since, _midnight_utc())]
    facts = autonomy.facts(plan.PLANNING, agents, standing_rows, now)
    spent = autonomy.spend(runs, plan.PLANNING, lab.reference("strong")["model"], lab.reference("floor")["model"],
                           cfg["raw"].get("max_cost_usd_per_run", PER_RUN_USD))
    ok, why = autonomy.may_start(plan.PLANNING, agents, facts, spent, tier)
    if not ok and plan.PLANNING not in agents:
        why = "no planning agent is configured (area_agents has no entry named planning)"
    return ok, why


def _say_route(project: str, ctx: dict, said: str, answer_to=None) -> tuple:
    """A plain line: the answer to the router's question (then the router runs again), or a new request with the
    memory in front of it. Either way the router runs only when the planning agent may start."""
    ok, why = _planning_may_start(ctx)
    if not ok:
        return f"The planning agent may not start now: {why}. Nothing was run.", None, None, False, None
    if answer_to is not None:
        request_id = _stored(ctx, ctx["store"].pending_get, answer_to)["task_id"]
        answer(project, answer_to, said)
    else:
        messages = _stored(ctx, ctx["store"].messages_list, CONVERSATION, limit=500)[:-1]  # not the line just stored
        settled = {t["id"] for t in _stored(ctx, ctx["store"].tasks_list)
                   if t["parent_id"] is None and t["state"] in ("planned", "done", "cancelled")}
        remembered = chat_memory(messages, settled)
        text = f"{remembered}\n\n{MEMORY_TAIL}\n{said}" if remembered else said
        request_id = request(project, text, title=said.split("\n", 1)[0][:TITLE_CHARS])["request"]
    routed = route(project, request_id)
    item = _stored(ctx, ctx["store"].pending_get, routed["pending_id"]) if routed.get("pending_id") else None
    if item is None:
        failure = (routed.get("failure") or {}).get("reason") or "the router's run failed"
        return f"The router could not run: {failure}", request_id, None, True, routed.get("run_id")
    if item["kind"] == "plan":
        payload = item["payload"]
        lines = [item["title"]]
        lines += [f"- {t['key']}: {t['title']} ({t['skill']})" for t in payload.get("tasks") or []]
        estimate = payload.get("estimate") or {}
        lines += [f"Estimate: {estimate.get('runs', estimate.get('runs_at_least'))} runs"
                  + (f" ({estimate['formula']})" if estimate.get("formula") else ""), ""]
        for n, u in enumerate(payload.get("unrouted") or [], 1):
            lines += [f"Not planned {n}: {u['item']}. The router's reply:", u["reply"].rstrip("\n"), ""]
        lines.append(PLAN_NEXT.format(pending=item["id"]))
        reply = "\n".join(lines)
    else:
        reply = item["body"].rstrip("\n") + "\n\n" + ASK_NEXT
    return reply, request_id, item["id"], True, routed.get("run_id")


if __name__ == "__main__":
    print(__doc__.strip())
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
