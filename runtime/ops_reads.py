#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The reads of the local interface and the signals of the local service: the change signal of the store (`version`),
the stop of the runs a process started, the agents with their day, the conversation's messages, the skills with their
proof, the costs, the connections, the service's start check and the project's artifacts.

A sibling of runtime/ops.py, which exposes each of them under its name; no shell imports this file. The names every
module of the layer shares are read as `core.<name>` (runtime/ops_core.py); an operation or a helper that stays in
runtime/ops.py is reached at call time through `_ops()`, never imported at module level, so that the two files do not
import each other. The conversation's name comes from runtime/ops_say.py, which imports nothing of this file.

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import datetime
import importlib
import os
import platform as platform_module
import stat as stat_module
import sys

import ops_core as core
import ops_say
import autonomy
import costs as costs_calc  # the operation `costs` would hide the module
import dispatcher
import lab
import manifest
import operations
import path_rule
import plan
import project_config
import proof as proof_rules  # the operation `proof` would hide the module
import router
import skill_meta

SERVICE_TEXT = 300  # characters of one verdict of service_check: an exception's text is bounded


def _ops():
    """runtime/ops.py, found at call time: the helpers of the dispatcher's round and the service's facts stay there."""
    return importlib.import_module("ops")


# --- stage 9: the local service --------------------------------------------------------------------------------------


def version(project: str) -> dict:
    """The change signal of a project's store: {"version", "changed_at"}. "version" is a whole number that grows on every
    write transaction that changed a row (providers/store/sqlite.py, `change_counter`: the database file's header),
    whoever wrote it: this process, a loop's thread, the terminal. A page asks it every second and reads everything
    again when it moved. It is the cheapest read there is: the configuration file and its hash, then on the store four
    statements (two pragmas of the connection, one plain SELECT of the cursor that holds the accepted configuration's hash,
    the header) with no transaction and so no write lock; no migration is run (every other operation runs one at its
    start), and a configuration nobody accepted, or one that names another checkout, is refused as every operation refuses it. "changed_at" is the time the store's file
    was last written (UTC, as the store writes times). A project whose store does not exist yet gets it made, as every
    other operation does."""
    cfg = core._config_of(project)
    store = core.store_module()
    db = cfg["store_db"]
    if not os.path.isfile(db):
        core.context(project, check_config=False)
    conn = store.connect(db)
    try:
        accepted = store.cursor_peek(conn, project_config.ACCEPTED)      # a plain read: no write lock, no queue behind a writer
        number = store.change_counter(conn)
    except store.StoreError as e:
        raise core.OpsError(f"the store at {db}: {e}", e.code) from None
    except Exception as e:  # sqlite3.Error: the file is not a database, or is locked past the timeout
        raise core.OpsError(f"the store at {db}: {e}", 1) from None
    finally:
        conn.close()
    core._accepted(cfg, accepted)
    stamps = [os.stat(path).st_mtime for path in (db, db + "-wal") if os.path.exists(path)]
    changed = datetime.datetime.fromtimestamp(max(stamps), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return {"version": number, "changed_at": changed}


def stop_runs(project: str | None = None) -> dict:
    """End every run this process started, through the lab's own stop (lab.stop_runs): the container and the process
    group of each run are ended and the folders of a run in progress go back to its run folder. The local service
    calls it before it exits, because a run it started in a thread has no signal handler of its own. Process-wide:
    the project is accepted for the shape every operation has and read for nothing. Returns what lab.stop_runs
    returns."""
    return lab.stop_runs()


# --- stage 9: the reads of the local interface ---------------------------------------------------------------------


COST_DAYS = 30           # costs: the default window, in days
MESSAGES_PAGE = 500      # conversation: the most messages one call returns (the store's own maximum)
ARTIFACT_LIMIT = 2000    # artifacts: the most files one call lists
ARTIFACT_MAX_BYTES = 1024 * 1024  # artifact: the largest file whose text is returned
SECRET_RESOLVER = ("providers", "secrets", "resolver.py")
CONFIGURED_PROVIDER = {"integration:vcs": "code", "integration:issue-tracker": "task_board", "integration:documents": "documents"}


def agents(project: str) -> dict:
    """The area agents of the configuration with their use of today: {"agents": [{"name", "pack", "enabled", "mode",
    "acting_mode", "max_runs_per_day", "max_usd_per_day", "runs_today", "usd_today", "runs_without_cost", "usd_recorded", "usd_reserved",
    "runs_total_today", "queued", "held", "wider"}]}
    in the order of the configuration. mode is the configured one; acting_mode the one the agent acts in now
    (autonomy.mode_of: an agent set to autonomous-with-policy whose approval expired acts as autonomous). The day is
    counted as the caps count it (_agents_of_the_day): runs_today is the runs on the reference model, usd_today the
    dollars of the floor model's runs (a run of unknown cost counts at max_cost_usd_per_run, and runs_without_cost
    says how many), and a router run counts for the planning agent. queued is the number of ready tasks of the agent;
    held how many of them the last round held (status lists them with their reasons). usd_today is split into
    usd_recorded (the recorded costs of today's floor-model runs) and usd_reserved (max_cost_usd_per_run, else
    PER_RUN_USD, for each such run with no cost yet: what the cap counts); runs_today stays the reference model's
    runs and runs_total_today is every run of the agent today, whatever the model. wider lists, for every mode above
    the agent's own, the absolute set-mode command (the page offers it with Copy and builds none).
    A project without area_agents: {"agents": []}."""
    ctx = core.context(project)
    day = _ops()._agents_of_the_day(ctx)
    rows = core._stored(ctx, ctx["store"].tasks_list)
    ready = [t for t in rows if t["state"] == "ready" and t["parent_id"] is not None]
    held = _ops()._held_listed(ctx, rows)
    out = []
    for name, found in day.items():
        entry, spent = found["entry"], found["spent"]
        out.append({"name": name, "pack": entry["pack"], "enabled": entry["enabled"], "mode": entry["mode"],
                    "acting_mode": autonomy.mode_of(found["facts"]), "max_runs_per_day": entry["max_runs_per_day"],
                    "max_usd_per_day": entry["max_usd_per_day"], "runs_today": spent["runs_reference"],
                    "usd_today": spent["usd_floor"], "runs_without_cost": spent["runs_without_cost"],
                    **_spend_words(found["split"]),
                    "queued": sum(1 for t in ready if t.get("agent") == name),
                    "held": sum(1 for h in held if h["agent"] == name),
                    "wider": _wider(ctx["cfg"]["project"], name, entry["mode"])})
    return {"agents": out}


def _spend_words(split: dict) -> dict:
    """The day's spend in the words a meter shows, the same in `agents` and in the caps of `costs`: usd_recorded,
    usd_reserved (their sum is usd_today) and runs_total_today."""
    return {"usd_recorded": split["usd_recorded"], "usd_reserved": split["usd_reserved"],
            "runs_total_today": split["runs_total"]}


def _caps_use(used, name: str) -> dict:
    """The day's use of one agent in the words of `agents`, for the caps of `costs`; {} when the day could not be
    computed (the gate file is broken): costs then show the caps alone."""
    if not used or name not in used:
        return {}
    found = used[name]
    return {"runs_today": found["spent"]["runs_reference"], "usd_today": found["spent"]["usd_floor"],
            "runs_without_cost": found["spent"]["runs_without_cost"], **_spend_words(found["split"])}


def _wider(project: str, agent: str, mode: str) -> list:
    """[{"mode", "command"}] for every mode above this one in the order of autonomy.MODES, each the absolute `set-mode`
    command (a wider mode is accepted by the person in the terminal): the page shows it, it builds none."""
    above = autonomy.MODES[autonomy.MODES.index(mode) + 1:]
    return [{"mode": m, "command": core._command("set-mode", project, agent=agent, mode=m)} for m in above]


def conversation(project: str, conversation: str | None = ops_say.CONVERSATION, after: int | None = 0) -> dict:
    """The messages of a conversation whose id is above `after`, oldest first, at most MESSAGES_PAGE (the newest of
    them when more are waiting): {"conversation", "messages": [{"id", "role", "text", "task_id", "run_id",
    "created_at"}]}. There is one conversation per project and its name is CONVERSATION (an argument left out is the
    default). For an assistant message
    task_id is the request the turn made or answered. Reads nothing else."""
    ctx = core.context(project)
    conversation, after = ops_say.CONVERSATION if conversation is None else conversation, 0 if after is None else after
    if isinstance(after, bool) or not isinstance(after, int) or after < 0:
        raise core.OpsError("after is a message id: a whole number, 0 or more", 2)
    if not isinstance(conversation, str) or not conversation.strip():
        raise core.OpsError("the conversation's name is empty", 2)
    rows = core._stored(ctx, ctx["store"].messages_list, conversation, limit=MESSAGES_PAGE, after_id=after)
    keys = ("id", "role", "text", "task_id", "run_id", "created_at")
    return {"conversation": conversation, "messages": [{key: row[key] for key in keys} for row in rows]}


def _scope(ctx: dict) -> list:
    """The skills in scope of the project: the packs of its enabled agents, or the default pack without area_agents."""
    try:
        return plan.pack_skills(ctx["cfg"], core.ROOT)
    except plan.PlanError as e:
        raise core.OpsError(f"the skills in scope cannot be listed: {e}", 1) from None


def skills(project: str) -> dict:
    """The skills in scope of the project (_scope) with what is known of each, and the two checks of the proof:
    {"skills": [{"name", "version", "area", "manifest": true or false, "proof": [{"tier", "model", "adapter",
    "band", "cause", "score", "mean", "runs"}], "runs_here": <runs of it in this project's store>}], "checks":
    {"measurement": "ok" or why, "image": "ok" or why}}. The proof is the entry runtime/proof.py keeps (proof.row),
    one pair for the reference model and one for the floor model, never recomputed here. The measurement check is the
    status script's; the image check is made once for the machine: "ok" when the eval image is on it and is the image
    the evidence of every skill that has evidence was measured in, else the reason (a skill with no evidence has
    nothing to compare and is `needs a test` anyway). Calls no model and no provider, and starts no network call."""
    ctx = core.context(project)
    cfg = ctx["cfg"]
    out, evidence = [], {}
    for name in _scope(ctx):
        try:
            meta = skill_meta.declared(os.path.join(core.ROOT, "skills", name))
            entry = proof_rules.row(cfg, name)
        except (skill_meta.SkillError, lab.LabError, OSError, KeyError) as e:
            raise core.OpsError(f"the proof of {name} cannot be read: {e}", 1) from None
        evidence[name] = entry.get("evidence_images") or []
        out.append({"name": name, "version": meta["version"], "area": meta["area"],
                    "manifest": os.path.isfile(manifest.path(core.ROOT, name)),
                    "proof": [{key: pair.get(key) for key in ("tier", "model", "adapter", "band", "cause", "score", "mean", "runs")}
                              for pair in entry["pairs"]],
                    "runs_here": len(core._stored(ctx, ctx["store"].task_runs_of_skill, name))})
    try:
        problem, digest = lab.measurement_problem(), lab.image()["digest"]
    except lab.LabError as e:
        raise core.OpsError(f"the proof's checks cannot be made: {e}", 1) from None
    others = sorted(name for name, images in evidence.items() if images and digest not in images)
    if digest is None:
        image = "the eval image is not on this machine"
    elif others:
        image = f"the image on this machine is not the one the evidence of {len(others)} skill(s) was measured in"
    else:
        image = None
    return {"skills": out, "checks": {"measurement": problem or "ok", "image": image or "ok"}}


def costs(project: str, since: str | None = None) -> dict:
    """The runs of the project from the day `since` (YYYY-MM-DD; default the last COST_DAYS days) by day, agent, model
    and adapter: {"since", "rows": [{"day", "agent", "model", "adapter", "runs", "tokens", "recorded_usd",
    "recomputed_usd", "unknown_runs", "price"}], "caps": [{"agent", "max_runs_per_day", "max_usd_per_day", "runs_today", "usd_today", "runs_without_cost", "usd_recorded",
    "usd_reserved", "runs_total_today"}]} (the caps carry the day's use in the words of `agents`). The runs
    are read task by task (the store's runs_since has no token count and no run folder) and the token counts of a
    run from its own folder (runtime/costs.py, usage_of): a folder outside <data_dir>/task-runs/ is not read, and the
    run is unknown. recomputed_usd is computed from the prices of the configuration's model_prices (price says their
    source and date) and is None, never a guess, for a model with no price or a group with a run of unknown usage
    (unknown_runs counts them). A router run counts for the planning agent. The day is the local day."""
    ctx = core.context(project)
    cfg, store = ctx["cfg"], ctx["store"]
    if since is None:
        day = (datetime.date.today() - datetime.timedelta(days=COST_DAYS)).isoformat()
    else:
        try:
            day = datetime.date.fromisoformat(str(since)).isoformat()
        except ValueError:
            raise core.OpsError("since is a day: YYYY-MM-DD", 2) from None
    try:
        used = _ops()._agents_of_the_day(ctx)
    except (lab.LabError, core.OpsError, KeyError, ValueError, OSError):  # a broken gate file leaves the day's use out; costs read the store
        used = None
    folder = os.path.realpath(os.path.join(cfg["data_dir"], core.RUNS_DIR)) + os.sep
    runs = []
    for task in core._stored(ctx, store.tasks_list):
        for run in core._stored(ctx, store.task_runs_list, task["id"]):
            agent = task.get("agent")
            if agent is None and task["parent_id"] is None and run.get("skill") == router.ROUTER_SKILL:
                agent = plan.PLANNING
            where = run.get("run_dir")
            inside = isinstance(where, str) and os.path.realpath(where).startswith(folder)
            runs.append(dict(run, agent=agent, run_dir=where if inside else None))
    return {"since": day, "rows": costs_calc.summary(runs, cfg["model_prices"], since=day),
            "caps": [{"agent": name, "max_runs_per_day": entry["max_runs_per_day"],
                      "max_usd_per_day": entry["max_usd_per_day"], **_caps_use(used, name)}
                     for name, entry in cfg["area_agents"].items()]}


def _secret_rows() -> tuple:
    """([{"name", "found", "where"}], note): the secrets the core and the runtime register, found or not and where
    (resolver.report(): the environment or the secret store), then the variables the lab names for the two models'
    keys (lab.credential_missing). Never a value: the resolver's report holds none, and only its name, found and
    source are taken. note is None, or why a part could not be read."""
    notes, rows = [], []
    try:
        resolver = core._load("workbench_secret_resolver_runtime", os.path.join(core.ROOT, *SECRET_RESOLVER))
        resolver.register_file(os.path.join(core.ROOT, "runtime", "secrets.json"))
        rows = [{"name": r["name"], "found": bool(r["found"]), "where": r["source"] if r["found"] else None}
                for r in resolver.report()]
    except Exception as e:  # an interpreter the resolver does not run on, a bad registry
        sys.modules.pop("workbench_secret_resolver_runtime", None)
        notes.append(f"the secret resolver could not be used: {type(e).__name__}")
    have = {row["name"] for row in rows}
    try:
        for tier in ("strong", "floor"):
            names, missing = lab.reference(tier)["pass_env"], lab.credential_missing(tier)
            for name in names:
                if name not in have:
                    have.add(name)
                    rows.append({"name": name, "found": name not in missing,
                                 "where": None if name in missing else "environment or secret store"})
    except Exception as e:  # a gate file the facade refuses
        notes.append(f"the models' keys could not be looked up: {type(e).__name__}")
    return sorted(rows, key=lambda row: row["name"]), "; ".join(notes) or None


ARCHITECTURES = {"x86_64": "amd64", "amd64": "amd64", "arm64": "arm64", "aarch64": "arm64"}


def _image_platform_here(machine: str, system: str) -> str | None:
    """The platform the eval image runs as on a machine without emulation, in the os/arch form of the evidence
    (executor.IMAGE_PLATFORM, such as linux/arm64): the image is a Linux image, so the os is linux on a Linux host and
    on a host that runs containers in a Linux virtual machine of its own architecture (macOS, Windows); the arch is the
    machine's, normalised (x86_64 and amd64 are amd64, arm64 and aarch64 are arm64). None when the arch is not one of
    those or the system is not linux, darwin or win32: nothing is guessed."""
    arch = ARCHITECTURES.get((machine or "").strip().lower())
    if arch is None or not (system or "").startswith(("linux", "darwin", "win32")):
        return None
    return "linux/" + arch


def _platform_row(machine: str, system: str, evidence: str | None) -> dict:
    """The "platform" row of connections: see its docstring. same never compares an unknown value."""
    here = _image_platform_here(machine, system)
    return {"machine": machine or None, "evidence": evidence, "here": here,
            "same": (here == evidence) if here and evidence else None}


def connections(project: str) -> dict:
    """What the project's skills need from the machine and whether it is there, with no provider started and no
    network call: {"classes": [{"class", "provider", "found", "note", "skills"}], "secrets": [{"name", "found",
    "where"}], "secrets_note", "image": {"name", "present", "evidence": true, false or None}, "platform": {"machine",
    "evidence", "here", "same"}, "service": {"secret_store", "credential", "docker", "image", "dispatch", "problems",
    "start", "at"} or None}. classes: each requirement class the skills in scope declare, resolved by providers/resolve.py as the
    runtime resolves it (the implementation the configuration names for the code provider, the task board and the
    documents; else the environment, the platform default or the only implementation): provider is the
    implementation or None, found whether its file exists, note how it was chosen or why it was not. secrets: see
    _secret_rows; the names are the registry's, never a value. image: whether the eval image is on this machine and
    whether its digest is the one the evidence of the skills in scope was measured in (None when it is not
    present). platform: machine is the architecture of this machine as the system names it; evidence is the platform
    the lab evidence was made on; here is the platform the eval image runs as on this machine without emulation, in
    the evidence's os/arch form (see _image_platform_here); same is true when here equals evidence, false when both
    are known and differ, None when either is unknown. service: what the local service found at its start
    (service_check), null in any other process."""
    ctx = core.context(project)
    cfg = ctx["cfg"]
    needs, evidence = {}, set()
    for name in _scope(ctx):
        try:
            for cls in skill_meta.declared(os.path.join(core.ROOT, "skills", name))["requires"]:
                needs.setdefault(cls, []).append(name)
            evidence.update(proof_rules.row(cfg, name).get("evidence_images") or [])
        except (skill_meta.SkillError, lab.LabError, OSError, KeyError) as e:
            raise core.OpsError(f"the needs of {name} cannot be read: {e}", 1) from None
    resolve = core._load("workbench_provider_resolve", os.path.join(core.ROOT, "providers", "resolve.py"))
    classes = []
    for cls in sorted(needs):
        key = CONFIGURED_PROVIDER.get(cls)
        implementation = (cfg.get(key) or {}).get("provider") if key else None
        row = {"class": cls, "provider": None, "found": False, "note": None, "skills": sorted(needs[cls])}
        try:
            got = resolve.resolve(cls, root=core.ROOT, implementation=implementation)
        except (resolve.UnknownClass, resolve.Unresolved) as e:
            row["note"] = str(e)
        else:
            row.update(provider=got["implementation"], found=os.path.isfile(got["path"]),
                       note=f"chosen by {got['source']}" + (f" ({got['variable']})" if got.get("variable") else ""))
            if not row["found"]:
                row["note"] = "the provider's file is missing: " + row["note"]
        classes.append(row)
    secrets, note = _secret_rows()
    try:
        seen = lab.image()
    except lab.LabError as e:
        raise core.OpsError(f"the eval image cannot be looked up: {e}", 1) from None
    present = seen["digest"] is not None
    return {"classes": classes, "secrets": secrets, "secrets_note": note,
            "image": {"name": seen.get("name"), "present": present,
                      "evidence": (seen["digest"] in evidence) if present else None},
            "platform": _platform_row(platform_module.machine(), sys.platform, seen.get("evidence_platform")),
            "service": dict(_ops().SERVICE[os.path.realpath(cfg["project"])]) if os.path.realpath(cfg["project"]) in _ops().SERVICE else None}


def service_check(project: str, dispatch_every=None) -> dict:
    """What the local service checks for one project at its start, and remembers (SERVICE) for `connections`, `status`
    and `agents` while the process lives: {"secret_store", "credential", "docker", "image", "dispatch", "problems",
    "start", "at"}. Each verdict is "ok" or one sentence saying what is missing. secret_store and credential are the
    scheduler entry's check (dispatcher.inspect: can this interpreter read the secret store, is the reference model's
    credential set or in it), docker whether it is on PATH, image whether the eval image is on this machine,
    dispatch "every <n> s" or "off" (dispatch_every in seconds; 0 is off; None says the process is no service), problems
    the modules or the lab that did not load, start the command that starts the service with the secret store's
    library (uv run --with keyring==..., operations.service_line). It starts nothing and makes no network call."""
    ctx = core.context(project, check_config=False)
    found = dispatcher.inspect(_ops())
    seen = lab.image()
    if not seen.get("name"):
        image = "not looked at: the lab does not run in a container, or docker cannot be reached"
    elif not seen.get("digest"):
        image = f"the eval image {seen['name']} is not on this machine"
    else:
        image = "ok"
    bounded = lambda text: core.CONTROL.sub(" ", str(text))[:SERVICE_TEXT]  # noqa: E731  (an exception's text, bounded)
    problems = [bounded(f"{name}: {why}") for name, why in sorted(found["modules"].items()) if why != "ok"]
    if found["lab"] != "ok":
        problems.append(bounded(f"lab: {found['lab']}"))
    report = {"secret_store": bounded(found["secret_store"]), "credential": bounded(found["credential"]),
              "docker": "ok" if found["tools"].get("docker") else "docker is not on the PATH of this process",
              "image": image,
              "dispatch": ("not a service" if dispatch_every is None else
                           f"every {dispatch_every:g} s" if dispatch_every else "off"),
              "problems": problems, "start": operations.service_line(core.ROOT, [ctx["cfg"]["project"]], uv=True), "at": _ops()._now_iso()}
    if dispatch_every is not None:
        _ops().SERVICE[os.path.realpath(ctx["cfg"]["project"])] = dict(report)
    return report


def _owners() -> list:
    """[(skill, its declared outputs)] for every skill folder of the checkout that has a readable frontmatter."""
    folder, out = os.path.join(core.ROOT, "skills"), []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        try:
            out.append((name, skill_meta.declared(os.path.join(folder, name))["outputs"]))
        except (skill_meta.SkillError, OSError):
            continue
    return out


def artifacts(project: str) -> dict:
    """The files of the project under docs/ that the path rule calls a document or a machine file, sorted by path:
    {"artifacts": [{"path", "owner", "agent", "size", "modified_at", "bound"}], "truncated"}. owner is the skill whose
    declared outputs match the path (skill_meta.matches), or None. agent is the area agent whose pack holds the owner
    skill, as plan.agent_of decides it; None when there is no owner, the project has no area agents, or no one agent
    (or several) owns the skill. modified_at is ISO-8601 UTC. bound is true when a pending
    decision still open lists the file among those a run returned or kept for it, or when its skill's runtime
    manifest binds it to an approval by its hash. Never docs/workbench/runtime.json, a link, a folder the path rule
    drops, or a file outside docs/. At most ARTIFACT_LIMIT files; truncated says whether more were left out."""
    ctx = core.context(project)
    root = ctx["cfg"]["project"]
    base = os.path.join(root, "docs")
    owners = _owners()
    try:
        packs = plan.agent_skills(ctx["cfg"], core.ROOT)
    except plan.PlanError as e:
        raise core.OpsError(f"the agents of the packs cannot be told: {e}", 1) from None
    agent_by_owner = {}
    waiting = set()
    for item in core._stored(ctx, ctx["store"].pending_list):
        payload = item.get("payload") or {}
        for key in ("returned", "kept"):
            waiting.update(f["path"] for f in payload.get(key) or [] if isinstance(f, dict) and isinstance(f.get("path"), str))
    bound_by_owner = {}
    out, truncated = [], False
    if os.path.isdir(base) and not os.path.islink(base):
        for current, folders, files in os.walk(base, followlinks=False):
            folders[:] = sorted(d for d in folders if not os.path.islink(os.path.join(current, d)))
            for name in sorted(files):
                full = os.path.join(current, name)
                if os.path.islink(full) or not os.path.isfile(full):
                    continue
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                if path_rule.classify(rel) not in ("document", "machine"):
                    continue
                if len(out) >= ARTIFACT_LIMIT:
                    truncated = True
                    break
                owner = next((skill for skill, outputs in owners if skill_meta.matches(outputs, rel)), None)
                if owner not in bound_by_owner:
                    try:
                        bound_by_owner[owner] = manifest.load(core.ROOT, owner, whole=False) if owner else {}
                    except manifest.ManifestError:
                        bound_by_owner[owner] = {}
                if owner not in agent_by_owner:
                    try:
                        agent_by_owner[owner] = plan.agent_of(owner, packs) if owner and packs else None
                    except ValueError:
                        agent_by_owner[owner] = None
                found = os.lstat(full)
                out.append({"path": rel, "owner": owner, "agent": agent_by_owner[owner], "size": found.st_size, "modified_at": _utc(found.st_mtime),
                            "bound": rel in waiting or bool(manifest.bound_among(bound_by_owner[owner], [rel]))})
            if truncated:
                break
    return {"artifacts": sorted(out, key=lambda a: a["path"]), "truncated": truncated}


def _utc(timestamp: float) -> str:
    return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def artifact(project: str, path: str) -> dict:
    """The text of one file of the project under docs/, read-only: {"path", "text", "size", "modified_at"}. The path is
    relative to the project and normalised first (path_rule.normal: no "..", no absolute path). Refused (code 2)
    before anything is read: a path outside docs/, docs/workbench/runtime.json, a path the path rule drops or does
    not know, a path with a link on any part of it (the project's own folder excepted), a file that is not a regular
    file, over ARTIFACT_MAX_BYTES, or whose bytes are not UTF-8 text (a NUL is not text). A path that is not there is
    refused with code 1."""
    ctx = core.context(project)
    rel = path_rule.normal(path)
    if rel is None or not rel.startswith(path_rule.DOCS_DIR) or rel == path_rule.CONFIG:
        raise core.OpsError("an artifact is a file under docs/ of the project, other than the runtime's configuration", 2)
    if path_rule.classify(rel) not in ("state", "document", "machine"):
        raise core.OpsError(f"{rel} is not a file the interface reads", 2)
    here = ctx["cfg"]["project"]
    for part in rel.split("/"):
        here = os.path.join(here, part)
        if os.path.islink(here):
            raise core.OpsError(f"{rel} is or passes through a link: it is not read", 2)
    try:
        looked = os.lstat(here)
    except OSError:
        raise core.OpsError(f"there is no file {rel} in the project", 1) from None
    if not stat_module.S_ISREG(looked.st_mode):  # before any open: a pipe would block it
        raise core.OpsError(f"{rel} is not a regular file", 2)
    if looked.st_size > ARTIFACT_MAX_BYTES:
        raise core.OpsError(f"{rel} is {looked.st_size} bytes: over the {ARTIFACT_MAX_BYTES} the interface reads", 2)
    try:
        fd = os.open(here, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except OSError:
        raise core.OpsError(f"{rel} cannot be opened without following a link", 2) from None
    with os.fdopen(fd, "rb") as f:
        found = os.fstat(f.fileno())  # the file that was opened, not the one that was looked at
        if not stat_module.S_ISREG(found.st_mode):
            raise core.OpsError(f"{rel} is not a regular file", 2)
        data = f.read(ARTIFACT_MAX_BYTES + 1)
    if len(data) > ARTIFACT_MAX_BYTES:
        raise core.OpsError(f"{rel} is over the {ARTIFACT_MAX_BYTES} bytes the interface reads", 2)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise core.OpsError(f"{rel} is not UTF-8 text", 2) from None
    if "\x00" in text:
        raise core.OpsError(f"{rel} is not text", 2)
    return {"path": rel, "text": text, "size": len(data), "modified_at": _utc(found.st_mtime)}
