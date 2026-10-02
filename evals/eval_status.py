#!/usr/bin/env python3
"""Eval status of every skill, computed from a committed record and the skill folder's content hash.

Usage:
  python3 evals/eval_status.py status [--skill <name>]
  python3 evals/eval_status.py hash --skill <name>
  python3 evals/eval_status.py record --skill <name> --benchmark <path to benchmark.json> [--date YYYY-MM-DD]
  python3 evals/eval_status.py inventory --write | --check

A skill's eval result lives in skills/<name>/evals/result.json. It is written by tooling (the eval runner,
evals/eval_run.py, after a complete full run; or `record` here), never by hand:

  {"skill", "content_sha256", "date", "iteration", "runs", "cases": [ids], "harness", "floor_harness",
   "models": {"strong", "floor"}, "grader", "threshold",
   "scores": {"strong_with", "strong_without", "floor_with", "floor_without"},
   "complete": true|false, "infra_failures": <n>,
   "gate": {"floor": bool, "strong": bool, "strong_delta": bool, "passed": bool},
   "measurement_version": <n>, "tolerance": <number>,   (optional: a record without them is of version 1)
   "environment": {"kind": "container", "definition_sha256", "image", "image_id"},   (required from version 3:
                                                 the container the runs executed in, written by the runner)
   "early_ends": {"<tier>": {"early_ends": <n>, "rate": <float>}},   (optional: records written before it lack it)
   "baseline": {"date", "iteration", "runs"}}   (optional: the without-skill scores were measured again, alone,
                                                 by eval_run.py --only without --update-record)

"early_ends" counts the attempts in which a model ended its turn early with no error; the runner retried them,
so they are not in the scores (see eval_run.py --help).

Gate: floor_with >= threshold, strong_with >= threshold, and strong_with >= strong_without - tolerance.
A record of measurement version 1 was written under the earlier rule (floor_with >= threshold and
strong_with >= strong_without) and its "gate" has no "strong" key; it is valid as a record and always stale.

Content hash: sha256 over the files of the skill folder (sorted relative paths and their bytes), leaving out
evals/result.json, everything under scripts/tests/, __pycache__ folders, *.pyc and .DS_Store. A change to
SKILL.md, a reference, an asset, a script or an eval case changes it; files outside the folder do not. The
tests of a skill's scripts (skills/<name>/scripts/tests/) are left out because no model reads them: they are
not copied into an eval run, so adding, changing or removing one measures nothing differently.

The eval gate is configured in evals/eval-gate.json, committed: {"strong_model", "strong_harness",
"floor_model", "floor_harness", "floor_pass_env": [variables], "strong_pass_env": [variables], "grader",
"threshold", "strong_tolerance", "measurement_version", "measurement_floor"} and, once a measurement version is
closed, "measurement_sha256". It names the models, the adapters and the grader a gate run uses (eval_run.py takes
them as defaults) and what a record is judged against. "measurement_version" is a number raised by hand, in
the same commit, when a change alters what a run measures (the gate's rule, the environment runs execute in,
the grading template, what a model under test may do): every record of another version then reads stale. The
runner's own text is not hashed, so a change that measures the same thing stales nothing. The file sits
outside skills/, so changing it changes no content hash; the status below reacts instead. Without the file, a
record is judged on its own threshold, tolerance and version, and any model.

"measurement_floor" is the version below which lab evidence weighs nothing (the reliability model, section 8):
a whole number from 1 to the measurement version. "measurement_sha256" is the fingerprint of the files that
decide what a run measures, 64 hexadecimal characters. A gate file without it describes a measurement version
that is still open: files that decide what a run measures are still changing under that number, so nothing
measured meanwhile is written as evidence (evidence_refusal below; the runner and `record` both ask it).

Status of a skill:
  draft      no record, or a record whose gate did not pass (on the configured threshold) or that is not complete
  evaluated  the record passed, is complete, is of the configured measurement version, strong model, grader
             and floor model, and its content_sha256 equals the current hash
  stale      the record passed and is complete, but under another measurement version, strong model, grader
             or floor model than the configured ones, or the skill folder changed since

Commands:
  status     prints {"skills": [{"skill", "status", "date", "scores", "reason"}], "counts",
             "gate": {"floor_model", "threshold", "strong_model", "grader", "strong_tolerance", "measurement_version"}}
             (the configured gate; null values without the file).
  hash       prints the content hash of one skill.
  record     builds result.json from an existing benchmark.json (a run made before records existed, or with
             --no-record). Refused when the benchmark did not run every case of the skill, lacks one of the
             four variants (with and without the skill, strong and floor model) or lacks a score, and while
             the gate file carries no "measurement_sha256" (an open measurement version). It stores
             the CURRENT content hash unless the benchmark carries one: the caller answers for not having
             edited the skill since that run. The date is the benchmark's, else its file date, else --date.
  inventory  regenerates the block between <!-- eval-status:begin --> and <!-- eval-status:end --> in
             docs/inventory.md (--write), or exits 1 when the block differs from what would be generated (--check).

Data goes to stdout as JSON, diagnostics to stderr. Standard library only.
Exit codes: 0 ok, 1 the inventory block is out of date (--check) or a record was refused, 2 usage error.
"""
import datetime
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORD_REL = os.path.join("evals", "result.json")
TESTS_REL = "scripts/tests"  # the tests of a skill's scripts: outside the content hash and outside eval runs
BEGIN, END = "<!-- eval-status:begin -->", "<!-- eval-status:end -->"
INVENTORY_REL = os.path.join("docs", "inventory.md")
GATE_REL = os.path.join("evals", "eval-gate.json")
GATE_FIELDS = {"strong_model": str, "strong_harness": str, "floor_model": str, "floor_harness": str,
               "floor_pass_env": list, "strong_pass_env": list, "grader": str, "threshold": (int, float), "strong_tolerance": (int, float),
               "measurement_version": int, "measurement_floor": int}
GATE_OPTIONAL = {"measurement_sha256": str}  # absent while a measurement version is open
CONTAINER_VERSION = 3  # from this version on every run executes in the eval container, and a record names it
LEGACY_VERSION = 1  # a record with no "measurement_version": the gate had no threshold for the strong model
STATUSES = ("evaluated", "stale", "draft")
VARIANTS = {"strong_with": "with_skill", "strong_without": "without_skill",
            "floor_with": "with_skill.floor", "floor_without": "without_skill.floor"}
# Field name -> accepted types, for a record read from disk.
FIELDS = {"skill": str, "content_sha256": str, "date": str, "iteration": int, "runs": int, "cases": list,
          "harness": str, "floor_harness": str, "models": dict, "grader": str, "threshold": (int, float),
          "scores": dict, "complete": bool, "infra_failures": int, "gate": dict}


def die(msg, code=2):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def gate_problems(root=ROOT):
    """Why evals/eval-gate.json is not a valid configuration; an empty list when it is, or when there is none."""
    path = os.path.join(root, GATE_REL)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError) as e:
        return [f"not valid JSON: {e}"]
    if not isinstance(cfg, dict):
        return ["the configuration must be a JSON object"]
    out = [f"unknown field {k!r}" for k in cfg if k not in GATE_FIELDS and k not in GATE_OPTIONAL]
    for key, kind in GATE_FIELDS.items():
        if key not in cfg:
            out.append(f"missing field {key!r}")
        elif not isinstance(cfg[key], kind) or isinstance(cfg[key], bool) or cfg[key] == "":
            out.append(f"field {key!r} has the wrong type")
    for key in ("floor_pass_env", "strong_pass_env"):
        if not out and not all(isinstance(v, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v) for v in cfg[key]):
            out.append(f"{key} must list variable names")
    if not out and not 0 <= cfg["threshold"] <= 1:
        out.append("threshold must be between 0 and 1")
    if not out and not 0 <= cfg["strong_tolerance"] <= 1:
        out.append("strong_tolerance must be between 0 and 1")
    if not out and cfg["measurement_version"] <= LEGACY_VERSION:
        out.append(f"measurement_version must be above {LEGACY_VERSION}")
    if not out and (isinstance(cfg["measurement_floor"], bool) or not 1 <= cfg["measurement_floor"] <= cfg["measurement_version"]):
        out.append("measurement_floor must be a whole number from 1 to the measurement version")
    if not out and "measurement_sha256" in cfg and not (isinstance(cfg["measurement_sha256"], str)
                                                        and re.fullmatch(r"[0-9a-f]{64}", cfg["measurement_sha256"])):
        out.append("measurement_sha256 must be 64 hexadecimal characters")
    return out


def evidence_refusal(root=ROOT):
    """Why nothing measured now may be written as evidence, or None when it may.

    A gate file that carries no "measurement_sha256" describes a measurement version that is open: the
    files that decide what a run measures are still changing under its number, so a result written now
    could not be told from one made after the version is closed. A tree with no gate file (a case folder
    that builds a skill of its own) has no measurement to protect and is not refused."""
    path = os.path.join(root, GATE_REL)
    if not os.path.isfile(path):
        return None
    problems = gate_problems(root)
    if problems:
        return f"{GATE_REL} is not valid ({'; '.join(problems)})"
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    if "measurement_sha256" not in cfg:
        return (f"{GATE_REL} carries no measurement_sha256: measurement version {cfg['measurement_version']} is open, "
                "and nothing measured while it is open is written as evidence")
    return None


def load_gate(root=ROOT):
    """The eval gate configuration, or {} when the file is missing or invalid (validate.py reports an invalid one)."""
    path = os.path.join(root, GATE_REL)
    if not os.path.isfile(path) or gate_problems(root):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def skill_names(root=ROOT):
    base = os.path.join(root, "skills")
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base) if os.path.isfile(os.path.join(base, d, "SKILL.md")))


def content_hash(skill_dir):
    """sha256 over the skill folder: each file's relative path and bytes, in sorted path order.

    Left out: the record, caches and the tests of the skill's scripts (TESTS_REL), which no eval run copies.
    """
    files = []
    for dp, dns, fns in os.walk(skill_dir):
        dns[:] = sorted(d for d in dns if d != "__pycache__")
        for fn in fns:
            rel = os.path.relpath(os.path.join(dp, fn), skill_dir).replace(os.sep, "/")
            if rel.startswith(TESTS_REL + "/"):
                continue
            if fn == ".DS_Store" or fn.endswith(".pyc") or rel == RECORD_REL.replace(os.sep, "/"):
                continue
            files.append(rel)
    h = hashlib.sha256()
    for rel in sorted(files):
        try:
            with open(os.path.join(skill_dir, rel), "rb") as f:
                data = f.read()
        except OSError:
            data = b""  # a dangling link: its name still counts
        h.update(rel.encode("utf-8") + b"\0" + str(len(data)).encode() + b"\0" + data)
    return h.hexdigest()


def record_path(skill_dir):
    return os.path.join(skill_dir, RECORD_REL)


def record_problems(rec, skill):
    """Why a parsed result.json is not a valid record for the skill; an empty list when it is."""
    if not isinstance(rec, dict):
        return ["the record must be a JSON object"]
    out = []
    for key, kind in FIELDS.items():
        if key not in rec:
            out.append(f"missing field {key!r}")
        elif not isinstance(rec[key], kind) or (kind is int and isinstance(rec[key], bool)):
            out.append(f"field {key!r} has the wrong type")
    if out:
        return out
    if rec["skill"] != skill:
        out.append(f"skill {rec['skill']!r} must equal the folder name {skill!r}")
    base = rec.get("baseline")
    if base is not None and not (isinstance(base, dict) and isinstance(base.get("date"), str)
                                 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", base["date"])
                                 and all(isinstance(base.get(k), int) and not isinstance(base.get(k), bool)
                                         for k in ("iteration", "runs"))):
        out.append("baseline must be {\"date\": YYYY-MM-DD, \"iteration\": <n>, \"runs\": <n>}")
    early = rec.get("early_ends", {})
    if not isinstance(early, dict) or not all(
            isinstance(v, dict) and isinstance(v.get("early_ends"), int) and isinstance(v.get("rate"), (int, float))
            for v in early.values()):
        out.append("early_ends must map a tier to {\"early_ends\": <n>, \"rate\": <number>}")
    if not re.fullmatch(r"[0-9a-f]{64}", rec["content_sha256"]):
        out.append("content_sha256 must be 64 hexadecimal characters")
    try:
        datetime.date.fromisoformat(rec["date"])
    except ValueError:
        out.append("date must be YYYY-MM-DD")
    for key in ("strong", "floor"):
        if not isinstance(rec["models"].get(key), str):
            out.append(f"models.{key} must be a model id")
    for key in VARIANTS:
        if not isinstance(rec["scores"].get(key), (int, float)) or isinstance(rec["scores"].get(key), bool):
            out.append(f"scores.{key} must be a number")
    version, tolerance = rec.get("measurement_version", LEGACY_VERSION), rec.get("tolerance", 0)
    if not isinstance(version, int) or isinstance(version, bool) or version < LEGACY_VERSION:
        out.append("measurement_version must be a whole number, 1 or more")
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool):
        out.append("tolerance must be a number")
    if "environment" in rec and not isinstance(rec["environment"], dict):
        out.append("environment must be an object")
    elif isinstance(version, int) and version >= CONTAINER_VERSION and (rec.get("environment") or {}).get("kind") != "container":
        out.append(f"a record of measurement version {CONTAINER_VERSION} or above names the container it ran in (environment)")
    if out:
        return out
    for key in ("floor", "strong_delta", "passed") + (("strong",) if version > LEGACY_VERSION else ()):
        if not isinstance(rec["gate"].get(key), bool):
            out.append(f"gate.{key} must be true or false")
    if not out and rec["gate"] != gate(rec["scores"], rec["threshold"], tolerance, version):
        out.append("gate does not follow from scores and threshold (the record is written by tooling, never by hand)")
    return out


def load_record(skill_dir):
    """Return (record, problems). (None, []) when the skill has no record."""
    path = record_path(skill_dir)
    if not os.path.isfile(path):
        return None, []
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
    except (OSError, ValueError) as e:
        return None, [f"not valid JSON: {e}"]
    problems = record_problems(rec, os.path.basename(os.path.normpath(skill_dir)))
    return (None, problems) if problems else (rec, [])


def gate(scores, threshold, tolerance=0, version=LEGACY_VERSION + 1):
    """Both models at the threshold with the skill, and the skill does not lower the strong model by more
    than the tolerance. version 1 is the earlier rule, kept to read the records written under it."""
    floor = scores["floor_with"] >= threshold
    delta = scores["strong_with"] >= scores["strong_without"] - tolerance
    if version <= LEGACY_VERSION:
        return {"floor": floor, "strong_delta": delta, "passed": floor and delta}
    strong = scores["strong_with"] >= threshold
    return {"floor": floor, "strong": strong, "strong_delta": delta, "passed": floor and strong and delta}


def case_ids(skill_dir):
    with open(os.path.join(skill_dir, "evals", "evals.json"), encoding="utf-8") as f:
        return [c.get("id") for c in json.load(f).get("evals") or []]


def build_record(skill_dir, bench, iteration, date, content_sha256=None):
    """A record from a benchmark.json. Raises ValueError, naming every reason, when the benchmark is partial."""
    skill = os.path.basename(os.path.normpath(skill_dir))
    why = []
    if bench.get("skill") != skill:
        why.append(f"the benchmark is of skill {bench.get('skill')!r}, not {skill!r}")
    summary = bench.get("run_summary") or {}
    try:
        wanted = case_ids(skill_dir)
    except (OSError, ValueError) as e:
        raise ValueError(f"cannot read the skill's evals.json: {e}") from e
    runs = bench.get("runs") or 1
    scores, completed = {}, 0
    for key, name in VARIANTS.items():
        rows = (summary.get(name) or {}).get("cases") or []
        rate = (summary.get(name) or {}).get("pass_rate") or {}
        if name not in summary:
            why.append(f"variant {name} did not run")
            continue
        graded = [r for r in rows if r.get("pass_rate") is not None]
        missing = [c for c in wanted if c not in {r.get("case") for r in graded}]
        if missing:
            why.append(f"variant {name} has no graded run of case(s) {', '.join(str(c) for c in missing)}")
        if rate.get("mean") is None:
            why.append(f"variant {name} has no score")
        else:
            scores[key] = rate["mean"]
        completed += len([r for r in graded if r.get("case") in wanted])
    for key in ("strong", "floor"):
        if not isinstance((bench.get("models") or {}).get(key), str):
            why.append(f"the benchmark names no {key} model")
    if not wanted:
        why.append("the skill has no eval cases")
    if why:
        raise ValueError("; ".join(why))
    expected = len(wanted) * len(VARIANTS) * runs
    infra = bench.get("infra_failures")
    infra = len(infra) if isinstance(infra, list) else max(expected - completed, 0)
    threshold = bench.get("threshold", 0.8)
    tolerance, version = bench.get("strong_tolerance") or 0, bench.get("measurement_version") or LEGACY_VERSION + 1
    extra = {"environment": bench["environment"]} if isinstance(bench.get("environment"), dict) else {}
    early = bench.get("early_ends")
    early = {"early_ends": {t: {"early_ends": v.get("early_ends", 0), "rate": v.get("rate", 0.0)}
                            for t, v in early.items() if isinstance(v, dict)}} if isinstance(early, dict) else {}
    return {**early, "skill": skill, "content_sha256": content_sha256 or bench.get("content_sha256") or content_hash(skill_dir),
            "date": date, "iteration": iteration, "runs": runs, "cases": wanted,
            "harness": bench.get("harness") or "", "floor_harness": bench.get("floor_harness") or bench.get("harness") or "",
            "models": {"strong": bench["models"]["strong"], "floor": bench["models"]["floor"]},
            "grader": bench.get("grader") or bench["models"]["strong"], "threshold": threshold, "scores": scores,
            "complete": bool(bench.get("complete", True)) and completed >= expected and infra == 0,
            "infra_failures": infra, "measurement_version": version, "tolerance": tolerance, **extra,
            "gate": gate(scores, threshold, tolerance, version)}


def update_baseline(skill_dir, bench, iteration, date, config=None):
    """The skill's record with its two without-skill scores replaced by a benchmark of that variant alone.

    Raises ValueError, naming every reason, when there is no valid record, when the record is not of the
    skill's current content, of the benchmark's models and of the configured models and threshold, or when
    the benchmark lacks a graded run of a case. The caller checks that the run was complete and clean."""
    skill = os.path.basename(os.path.normpath(skill_dir))
    rec, problems = load_record(skill_dir)
    if problems:
        raise ValueError("the existing record is invalid: " + "; ".join(problems))
    if rec is None:
        raise ValueError("the skill has no record to update: run the full evals first")
    config, why = config or {}, []
    if bench.get("skill") != skill:
        why.append(f"the benchmark is of skill {bench.get('skill')!r}, not {skill!r}")
    if rec["content_sha256"] != content_hash(skill_dir):
        why.append("the record is of another content of the skill (stale): run the full evals")
    if bench.get("content_sha256") and bench["content_sha256"] != rec["content_sha256"]:
        why.append("the benchmark was run on another content of the skill")
    models = bench.get("models") or {}
    for key in ("strong", "floor"):
        if models.get(key) != rec["models"][key]:
            why.append(f"the record's {key} model is {rec['models'][key]}, this run's is {models.get(key)}")
        if config.get(f"{key}_model") and rec["models"][key] != config[f"{key}_model"]:
            why.append(f"the record's {key} model is {rec['models'][key]}, the configured one is {config[f'{key}_model']}")
    for name, value in (("this run's", bench.get("threshold")), ("the configured one", config.get("threshold"))):
        if value is not None and value != rec["threshold"]:
            why.append(f"the record's threshold is {rec['threshold']}, {name} is {value}")
    version = rec.get("measurement_version", LEGACY_VERSION)
    for name, value in (("this run's", bench.get("measurement_version")), ("the configured one", config.get("measurement_version"))):
        if value is not None and value != version:
            why.append(f"the record's measurement version is {version}, {name} is {value}: run the full evals")
    summary, wanted, scores = bench.get("run_summary") or {}, case_ids(skill_dir), {}
    for key in ("strong_without", "floor_without"):
        entry = summary.get(VARIANTS[key]) or {}
        graded = {r.get("case") for r in entry.get("cases") or [] if r.get("pass_rate") is not None}
        missing = [c for c in wanted if c not in graded]
        if missing or (entry.get("pass_rate") or {}).get("mean") is None:
            why.append(f"variant {VARIANTS[key]} has no graded run of case(s) {', '.join(str(c) for c in missing) or 'any'}")
        else:
            scores[key] = entry["pass_rate"]["mean"]
    if why:
        raise ValueError("; ".join(why))
    rec["scores"].update(scores)
    rec["gate"] = gate(rec["scores"], rec["threshold"], rec.get("tolerance", 0), version)
    rec["baseline"] = {"date": date, "iteration": iteration, "runs": bench.get("runs") or 1}
    return rec


def write_record(skill_dir, record):
    path = record_path(skill_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    return path


def skill_status(skill_dir, config=None):
    """{"skill", "status", "date", "scores", "iteration", "reason"} for one skill folder.

    config is the eval gate configuration; by default the one of the repository the skill folder is in."""
    skill = os.path.basename(os.path.normpath(skill_dir))
    if config is None:
        config = load_gate(os.path.dirname(os.path.dirname(os.path.normpath(os.path.abspath(skill_dir)))))
    rec, problems = load_record(skill_dir)
    row = {"skill": skill, "status": "draft", "date": None, "scores": None, "iteration": None, "reason": "no eval record"}
    if problems:
        row["reason"] = "invalid record: " + "; ".join(problems)
        return row
    if rec is None:
        return row
    row.update(date=rec["date"], scores=rec["scores"], iteration=rec["iteration"])
    # The record is judged against the configured gate, not the one it was run under.
    threshold = config.get("threshold", rec["threshold"])
    tolerance = config.get("strong_tolerance", rec.get("tolerance", 0))
    version = rec.get("measurement_version", LEGACY_VERSION)
    s, g = rec["scores"], gate(rec["scores"], threshold, tolerance)
    if not rec["complete"]:
        row["reason"] = f"the recorded run is incomplete ({rec['infra_failures']} infrastructure failure(s)): rerun the evals"
    elif not g["passed"]:
        parts = ([] if g["floor"] else [f"floor {s['floor_with']} is below {threshold}"]) + \
                ([] if g["strong"] else [f"strong {s['strong_with']} is below {threshold}"]) + \
                ([] if g["strong_delta"] else [f"strong with the skill {s['strong_with']} is below without it {s['strong_without']}"
                                               + (f" by more than {tolerance}" if tolerance else "")])
        row["reason"] = "the gate did not pass: " + "; ".join(parts)
    elif config.get("measurement_version") and version != config["measurement_version"]:
        row.update(status="stale", reason=f"measured under version {version} of the measurement, the configured one is "
                                          f"{config['measurement_version']}; rerun the evals")
    elif config.get("strong_model") and rec["models"]["strong"] != config["strong_model"]:
        row.update(status="stale", reason=f"evaluated on another strong model ({rec['models']['strong']}); rerun the evals")
    elif config.get("grader") and rec["grader"] != config["grader"]:
        row.update(status="stale", reason=f"graded by another model ({rec['grader']}); rerun the evals")
    elif config.get("floor_model") and rec["models"]["floor"] != config["floor_model"]:
        row.update(status="stale", reason=f"evaluated on another floor model ({rec['models']['floor']}); rerun the evals")
    elif rec["content_sha256"] != content_hash(skill_dir):
        row.update(status="stale", reason="the skill folder changed since the recorded run: rerun the evals")
    else:
        row.update(status="evaluated", reason="the gate passed on the current content")
    return row


def all_status(root=ROOT, only=None):
    names = [only] if only else skill_names(root)
    config = load_gate(root)
    rows = [skill_status(os.path.join(root, "skills", n), config) for n in names]
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
    return {"skills": rows, "counts": counts,
            "gate": {k: config.get(k) for k in ("floor_model", "threshold", "strong_model", "grader", "strong_tolerance",
                                                "measurement_version")}}


def inventory_block(root=ROOT):
    """The generated lines that go between the markers."""
    data = all_status(root)
    num = lambda v: "—" if v is None else f"{v:.2f}"
    lines = ["| Skill | Status | Strong with | Strong without | Floor with | Date | Iteration |",
             "|-------|--------|-------------|----------------|------------|------|-----------|"]
    for r in data["skills"]:
        s = r["scores"] or {}
        lines.append(f"| {r['skill']} | {r['status']} | {num(s.get('strong_with'))} | {num(s.get('strong_without'))} | "
                     f"{num(s.get('floor_with'))} | {r['date'] or '—'} | {r['iteration'] if r['iteration'] is not None else '—'} |")
    c = data["counts"]
    lines += ["", f"Counts: {c['evaluated']} evaluated, {c['stale']} stale, {c['draft']} draft, {len(data['skills'])} skills."]
    return "\n".join(lines)


def inventory_text(root=ROOT):
    """Return (current text, text with the block regenerated). Raises ValueError when the markers are missing."""
    path = os.path.join(root, INVENTORY_REL)
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        raise ValueError(f"cannot read {INVENTORY_REL}: {e}") from e
    a, b = text.find(BEGIN), text.find(END)
    if a == -1 or b == -1 or b < a:
        raise ValueError(f"{INVENTORY_REL} lacks the markers {BEGIN} and {END}")
    return text, text[:a + len(BEGIN)] + "\n" + inventory_block(root) + "\n" + text[b:]


def inventory_current(root=ROOT):
    text, new = inventory_text(root)
    return text == new


def cmd_record(root, skill, bench_path, date):
    skill_dir = os.path.join(root, "skills", skill)
    refusal = evidence_refusal(root)
    if refusal:
        die(f"record refused: {refusal}.", 1)
    try:
        with open(bench_path, encoding="utf-8") as f:
            bench = json.load(f)
    except (OSError, ValueError) as e:
        die(f"cannot read the benchmark: {e}")
    m = re.search(r"iteration-(\d+)", os.path.abspath(bench_path))
    iteration = bench.get("iteration") or (int(m.group(1)) if m else 0)
    date = date or bench.get("date") or datetime.date.fromtimestamp(os.path.getmtime(bench_path)).isoformat()
    try:
        rec = build_record(skill_dir, bench, iteration, date)
    except ValueError as e:
        die(f"record refused: {e}", 1)
    if not bench.get("content_sha256"):
        print(f"The benchmark carries no content hash: recording the CURRENT hash of skills/{skill} "
              f"({rec['content_sha256'][:12]}). This is only true if the skill was not edited since that run.", file=sys.stderr)
    elif rec["content_sha256"] != content_hash(skill_dir):
        print(f"skills/{skill} changed since the benchmark's run: the record will read as stale.", file=sys.stderr)
    path = write_record(skill_dir, rec)
    print(f"wrote {os.path.relpath(path, root)}; run: python3 evals/eval_status.py inventory --write", file=sys.stderr)
    print(json.dumps({"record": rec, "status": skill_status(skill_dir)}, indent=2))
    return 0


def main(argv, root=None):
    root = root or ROOT
    if not argv or argv[0] in ("--help", "-h"):
        print(__doc__)
        return 0 if argv else 2
    cmd, rest = argv[0], argv[1:]
    if "--help" in rest or "-h" in rest:
        print(__doc__)
        return 0
    opts, flags, i = {}, set(), 0
    while i < len(rest):
        if rest[i] in ("--skill", "--benchmark", "--date"):
            if i + 1 >= len(rest):
                die(f"{rest[i]} needs a value.")
            opts[rest[i][2:]] = rest[i + 1]
            i += 2
        elif rest[i] in ("--write", "--check"):
            flags.add(rest[i])
            i += 1
        else:
            die(f"unknown option {rest[i]!r}. See --help.")
    skill = opts.get("skill")
    if skill is not None and (not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", skill)
                              or not os.path.isdir(os.path.join(root, "skills", skill))):
        die(f"no skill {skill!r} under skills/.")
    if cmd == "status":
        print(json.dumps(all_status(root, skill), indent=2))
        return 0
    if cmd == "hash":
        if not skill:
            die("hash needs --skill <name>.")
        print(content_hash(os.path.join(root, "skills", skill)))
        return 0
    if cmd == "record":
        if not skill or not opts.get("benchmark"):
            die("record needs --skill <name> and --benchmark <path>.")
        if opts.get("date"):
            try:
                datetime.date.fromisoformat(opts["date"])
            except ValueError:
                die("--date must be YYYY-MM-DD.")
        return cmd_record(root, skill, opts["benchmark"], opts.get("date"))
    if cmd == "inventory":
        if len(flags) != 1:
            die("inventory needs exactly one of --write or --check.")
        try:
            text, new = inventory_text(root)
        except ValueError as e:
            die(str(e), 1)
        if "--check" in flags:
            if text != new:
                print(f"{INVENTORY_REL}: the eval-status block is out of date; run python3 evals/eval_status.py inventory --write",
                      file=sys.stderr)
            print(json.dumps({"current": text == new}))
            return 0 if text == new else 1
        if text != new:
            with open(os.path.join(root, INVENTORY_REL), "w", encoding="utf-8") as f:
                f.write(new)
        print(json.dumps({"written": text != new, "counts": all_status(root)["counts"]}))
        return 0
    die(f"unknown command {cmd!r}. See --help.")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
