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
  run_next(project)                run the next ready task: one skill, once, in the eval container, on a copy
                                   of what may enter by limits L1 to L6 (runtime/workcopy.py); bring back what
                                   it left by the path rule; open the pending decision the task then waits on
  pending(project[, pending_id])   what waits for the person
  answer(project, pending_id, text)   answer a pending decision: the task runs again with the answer
  release(project, pending_id)     release a delivery: the task is done, and what depended on it becomes ready
  retry(project, task_id)          make a failed or blocked task ready again
  cancel(project, request_id)      cancel a request and what is still open under it
  status(project)                  requests, tasks, pending decisions
  accept_config(project, sha256)   record the hash of docs/workbench/runtime.json the person accepts; every
                                   other operation refuses a configuration whose hash is not the accepted one

Releasing is not approving: a released delivery stays a draft in the project's state file.

The pending decision a run opens: a `question` when the run wrote nothing and asks (ending `question`); a
`review` otherwise. A draft with open questions (ending `draft_with_questions`) opens a review: the person
releases it as it stands, its open questions left in it, or answers it, and the task runs again.

Usage (a library; the shell is runtime/cli.py): python3 runtime/ops.py --help

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import os
import re
import sys
import shutil
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import endings  # noqa: E402  (the same folder, as scripts/runtime.py imports runtime_vote)
import flow_files  # noqa: E402
import lab  # noqa: E402
import manifest  # noqa: E402
import path_rule  # noqa: E402
import project_config  # noqa: E402
import skill_meta  # noqa: E402
import state_merge  # noqa: E402
import workcopy  # noqa: E402

STORE_CLASS = "store:runtime"
RUNS_DIR = "task-runs"
LOCK_NAME = "run.lock"
NOTE_LIMIT = 1000        # characters of a failure's reason kept on a task and on a run row
PREPARED_DIR = "prepared"  # <data_dir>/prepared/<run id>/: files written for one run before they enter its copy
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


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


def _inside(project: str, rel: str) -> bool:
    """True when the project's path rel is, or would be, a regular file inside the project: no link on the way."""
    target = os.path.join(project, *rel.split("/"))
    folder = os.path.dirname(target)
    while not os.path.exists(folder):
        folder = os.path.dirname(folder)
    real = os.path.realpath(folder)
    return not os.path.islink(target) and (real == project or real.startswith(project + os.sep))


# --- what enters a run: runtime/workcopy.py (limits L1 to L6) --------------------------------------------------


def task_prompt(request_text: str, task_text: str, answered) -> str:
    """The text of one run: the request in the person's words, the task's own text, and, on a run made after
    an answer, every earlier question of this task with its answer. It names no skill: the one skill staged
    for the run loads by its description, as in a lab run."""
    parts = [request_text.strip(), "", "For this task: " + task_text.strip()]
    if answered:
        parts += ["", "In an earlier run of this task you stopped and asked the user. Your replies and the user's "
                      "answers are below, oldest first. Each answer is the user's decision: record it where the "
                      "skill says decisions are recorded, and do not ask it again."]
        for n, item in enumerate(answered, 1):
            parts += ["", f"--- your reply {n} ---", (item.get("body") or "").strip(), "",
                      f"--- the user's answer {n} ---", (item.get("answer") or "").strip()]
    return "\n".join(parts) + "\n"


# --- what comes back ---------------------------------------------------------------------------------------


def _write(target: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(target), exist_ok=True)
    temporary = f"{target}.{os.getpid()}.tmp"
    with open(temporary, "wb") as f:
        f.write(data)
    os.replace(temporary, target)


def bring_back(project: str, result: dict, base: dict, base_state, skill: str) -> tuple:
    """Bring back what a completed run left, by the path rule. Returns (returned, kept): returned lists
    {"path", "class"} of what was written into the project; kept lists {"path", "class", "reason"} of what
    stays in the run folder only. Nothing is deleted in the project, and a file that changed in the project
    since the copy was made is never overwritten."""
    cwd, changes = result["cwd"], result["changes"]
    facts = {"staged": result["staged"]}
    returned, kept = [], []
    for rel in sorted(changes["created"] + changes["modified"]):
        cls = path_rule.classify(rel, facts)
        keep = lambda reason: kept.append({"path": rel, "class": cls, "reason": reason})
        if cls == "ignored":
            continue
        if cls not in path_rule.RETURNED:
            keep("this class of path is not brought back yet")
            continue
        if not lab.readable(cwd, rel):
            keep("not a regular file inside the copy")
            continue
        target = os.path.join(project, *rel.split("/"))
        if not _inside(project, rel):
            keep("the project's path is a link or leaves the project")
            continue
        if (_sha256(target) if os.path.isfile(target) else None) != base.get(rel):
            keep("the project's file changed while the run was in progress")
            continue
        source = os.path.join(cwd, *rel.split("/"))
        if cls == "state":
            try:
                merged = state_merge.merge(base_state, _read(target) if os.path.isfile(target) else None,
                                           _read(source) or "", skill)
            except state_merge.Conflict as e:
                keep(str(e))
                continue
            _write(target, merged.encode("utf-8"))
        else:
            with open(source, "rb") as f:
                _write(target, f.read())
        returned.append({"path": rel, "class": cls})
    for rel in sorted(changes["deleted"]):
        if path_rule.classify(rel, facts) != "ignored":
            kept.append({"path": rel, "class": path_rule.classify(rel, facts),
                         "reason": "the run deleted it; the project's file is left as it is"})
    return returned, kept


def _ending(result: dict, meta: dict) -> tuple:
    """(ending, why) of a completed run, from runtime/endings.py."""
    cwd, changes = result["cwd"], result["changes"]
    written = [p for p in changes["created"] + changes["modified"] if skill_meta.matches(meta["outputs"], p)]
    after = set(changes["created"] + changes["modified"] + changes["unchanged"])
    missing = [p for p in meta["outputs"] if "<" not in p and not p.endswith("/") and p not in after]
    texts = [(_read(os.path.join(cwd, *p.split("/"))) or "") if lab.readable(cwd, p) else "" for p in written]
    return endings.classify(result["response"], changes, written, missing, texts)


# --- the operations ----------------------------------------------------------------------------------------


def request(project: str, text: str, flow: str, title: str | None = None) -> dict:
    """Record a request and plan it from the flow file the person names (flows/<flow>.json). The tasks without
    a dependency are ready at once. Returns {"request", "flow", "state", "tasks": [{"id", "key", "skill",
    "state"}]}."""
    ctx = context(project)
    try:
        plan = flow_files.load(flow, ROOT)
    except flow_files.FlowError as e:
        raise OpsError(str(e), 2) from None
    out = _stored(ctx, ctx["store"].request_add, title=_text(title or plan["title"], "the title").replace("\n", " "),
                  text=_text(text, "the request's text"), flow=plan["flow"], tasks=plan["tasks"])
    return {**out, "flow": plan["flow"]}


def run_next(project: str) -> dict:
    """Run the next ready task of the project, if no task of it is running: one skill, once, on the reference
    model. Returns {"ran": None, "reason"} when there is nothing to run, else {"ran": task id, "skill",
    "run_id", "run_dir", "status", "ending" or None, "failure" or None, "task_state", "pending_id" or None,
    "returned", "kept", "left_out", "entered": {"kind", "agents_md", "files"} or None}; "recovered" names the
    tasks an interrupted run had left running."""
    ctx = context(project)
    cfg, store = ctx["cfg"], ctx["store"]
    os.makedirs(cfg["data_dir"], mode=0o700, exist_ok=True)
    lock = os.open(os.path.join(cfg["data_dir"], LOCK_NAME), os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise OpsError("another run of this project is in progress: one task at a time per project", 1) from None
        # This process holds the project's run lock, so a task still `running` is what an interrupted run left.
        recovered = _stored(ctx, store.task_fail_running, "the run was interrupted before it ended; retry the task")
        claimed = _stored(ctx, store.task_claim_next)
        task = claimed["task"]
        if task is None:
            return {"ran": None, "reason": "no task is ready", "recovered": recovered["tasks"],
                    "pending": len(_stored(ctx, store.pending_list))}
        return {**_run(ctx, task), "recovered": recovered["tasks"]}
    finally:
        os.close(lock)  # closing the file releases the lock


def _run(ctx: dict, task: dict) -> dict:
    cfg, store, skill = ctx["cfg"], ctx["store"], task["skill"]
    try:
        meta = skill_meta.declared(os.path.join(ROOT, "skills", skill))
        known = manifest.load(ROOT, skill)  # a skill the runtime knows nothing of does not run
        ref, identity = lab.reference("strong"), lab.skill_identity(skill)
        run_id = _stored(ctx, store.task_run_start, task["id"], skill=skill, model=ref["model"], adapter=ref["adapter"],
                         skill_version=identity["version"], skill_sha256=identity["content_sha256"],
                         web=meta["web"])["run_id"]
    except (skill_meta.SkillError, manifest.ManifestError, lab.LabError, OpsError) as e:
        _stored(ctx, store.task_fail_running, _note(f"the run could not start: {e}"))
        raise OpsError(f"task {task['id']} ({skill}) could not start: {e}", 1) from None
    dest = os.path.join(cfg["data_dir"], RUNS_DIR, str(run_id))
    out = {"ran": task["id"], "skill": skill, "run_id": run_id, "run_dir": dest, "status": "failed", "ending": None,
           "failure": None, "task_state": "failed", "pending_id": None, "returned": [], "kept": [], "left_out": [],
           "entered": None}

    def fail(kind: str, reason: str, attempts: int = 0, digest=None) -> dict:
        _stored(ctx, store.task_run_finish, run_id, status="failed", failure=kind, task_state="failed",
                attempts=attempts, image_digest=digest, run_dir=dest, error=_note(reason), task_note=_note(reason))
        out["failure"] = {"kind": kind, "reason": _note(reason)}
        return out

    # Outside the run folder: the facade sets aside whatever it finds there.
    prepared_dir = os.path.join(cfg["data_dir"], PREPARED_DIR, str(run_id))
    try:
        try:
            entered = workcopy.entering(cfg["project"], meta, web=meta["web"], cfg=cfg,
                                        settings_names=lab.settings_names(), prepared_dir=prepared_dir)
        except workcopy.CopyError as e:
            return fail("internal", f"the copy could not be built: {e}")
        files, base, out["left_out"] = entered["files"], entered["base"], entered["left_out"]
        out["entered"] = {"kind": entered["kind"], "agents_md": entered["agents_md"], "files": len(files)}
        base_state = _read(os.path.join(cfg["project"], *path_rule.STATE.split("/")))
        request_text = _stored(ctx, store.task_get, task["parent_id"])["text"]
        answered = [p for p in _stored(ctx, store.pending_list, "resolved", task["id"]) if p["resolution"] == "answered"]
        prompt = task_prompt(request_text, task["text"], answered)
        with lab.session():
            result = lab.run_skill(skill, prompt, files, dest, web=meta["web"], tier="strong")
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
        return fail(failure["kind"], failure["reason"], counts["attempts"], result["image_digest"])
    returned, kept = bring_back(cfg["project"], result, base, base_state, skill)
    ending, why = _ending(result, meta)
    loaded = timing.get("skills_loaded")
    body = result["response"]
    cut = len(body.encode("utf-8")) > store.BODY_MAX
    # A run that wrote nothing and asks opens a question, which is answered. A run that wrote a declared output
    # opens a review, a draft with open questions included: its body is the whole reply, so the person reads the
    # questions and either releases the draft as it stands (its open questions stay in it, its row stays a
    # draft) or answers it, and the next run is given the answer.
    decision = {"kind": "question" if ending == "question" else "review",
                "title": f"{skill}: {ending.replace('_', ' ')}",
                "body": body.encode("utf-8")[:store.BODY_MAX].decode("utf-8", errors="ignore") if cut else body,
                "payload": {"ending": ending, "why": why, "returned": returned, "kept": kept, "run_dir": dest,
                            "entered": out["entered"], "left_out": out["left_out"],
                            "response_file": os.path.join(result["outputs"], "response.md"), "body_cut": cut}}
    number = lambda key, kind: timing.get(key) if isinstance(timing.get(key), kind) and not isinstance(timing.get(key), bool) else None
    done = _stored(ctx, store.task_run_finish, run_id, status="ok", ending=ending, task_state="waiting",
                   attempts=counts["attempts"], cost_usd=number("cost_usd", (int, float)), tokens=number("total_tokens", int),
                   duration_ms=number("duration_ms", int),
                   skill_loaded=(skill in loaded) if isinstance(loaded, list) else None,
                   image_digest=result["image_digest"], run_dir=dest, pending=decision)
    out.update(status="ok", ending=ending, task_state="waiting", pending_id=done["pending_id"], returned=returned, kept=kept)
    return out


def pending(project: str, pending_id: int | None = None) -> dict:
    """What waits for the person. Without an id: {"pending": [{"id", "kind", "title", "task_id", "created_at"}]},
    oldest first. With one: that pending decision whole, with its body (the reply) and its payload."""
    ctx = context(project)
    if pending_id is not None:
        return _stored(ctx, ctx["store"].pending_get, pending_id)
    return {"pending": [{key: item[key] for key in ("id", "kind", "title", "task_id", "created_at")}
                        for item in _stored(ctx, ctx["store"].pending_list)]}


def answer(project: str, pending_id: int, text: str) -> dict:
    """Answer a pending decision. The task becomes ready, and its next run is given the answer."""
    ctx = context(project)
    return _stored(ctx, ctx["store"].pending_resolve, pending_id, resolution="answered", by="user",
                   answer=_text(text, "the answer"))


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
    requests = [{**{key: r[key] for key in ("id", "title", "flow", "state")},
                 "tasks": [{key: t[key] for key in ("id", "key", "skill", "state", "note")}
                           for t in rows if t["parent_id"] == r["id"]]}
                for r in rows if r["parent_id"] is None]
    return {"config": {"path": ctx["cfg"]["path"], "sha256": ctx["cfg"]["sha256"]}, "requests": requests,
            "pending": [{key: item[key] for key in ("id", "kind", "title", "task_id", "created_at")}
                        for item in _stored(ctx, ctx["store"].pending_list)]}


if __name__ == "__main__":
    print(__doc__.strip())
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
