#!/usr/bin/env python3
"""Eval status of every skill, computed from a committed record and the skill folder's content hash.

Usage:
  python3 evals/eval_status.py status [--skill <name>]
  python3 evals/eval_status.py hash --skill <name>
  python3 evals/eval_status.py evidence [--skill <name> | --file <path>]
  python3 evals/eval_status.py gate --skill <name>
  python3 evals/eval_status.py inventory --write | --check
  python3 evals/eval_status.py measurement --kind grader|execution|infrastructure --cause "<why>"
                               [--skills <name>,...|all] [--models <id>,...|all] [--date YYYY-MM-DD]
  python3 evals/eval_status.py measurement --close --cause "<why>" [--date YYYY-MM-DD]
  python3 evals/eval_status.py bump --skill <name> [--class x|y|z] [--date YYYY-MM-DD]
  python3 evals/eval_status.py migrate-versions [--date YYYY-MM-DD]

The records of the first round, skills/<name>/evals/result.json, are history: nothing writes one any more
(the runner writes evidence, below), and the status of a skill is still read from them until the bands
replace it. A record was written by tooling, never by hand:

  {"skill", "content_sha256", "date", "iteration", "runs", "cases": [ids], "harness", "floor_harness",
   "models": {"strong", "floor"}, "grader", "threshold",
   "scores": {"strong_with", "strong_without", "floor_with", "floor_without"},
   "complete": true|false, "infra_failures": <n>,
   "gate": {"floor": bool, "strong": bool, "strong_delta": bool, "passed": bool},
   "measurement_version": <n>, "tolerance": <number>,   (optional: a record without them is of version 1)
   "environment": {"kind": "container", "definition_sha256", "image", "image_id"},   (required from version 3:
                                                 the container the runs executed in, written by the runner)
   "early_ends": {"<tier>": {"early_ends": <n>, "rate": <float>}},   (optional: records written before it lack it)
   "baseline": {"date", "iteration", "runs"}}   (optional: the without-skill scores were measured again, alone)

"early_ends" counts the attempts in which a model ended its turn early with no error; the runner retried them,
so they are not in the scores (see eval_run.py --help).

Gate: floor_with >= threshold, strong_with >= threshold, and strong_with >= strong_without - tolerance.
A record of measurement version 1 was written under the earlier rule (floor_with >= threshold and
strong_with >= strong_without) and its "gate" has no "strong" key; it is valid as a record and always stale.

Content hash: sha256 over the files of the skill folder (sorted relative paths and their bytes), leaving out
all of evals/ (the cases, the evidence, the version file, the old record), everything under scripts/tests/,
caches (__pycache__, .pytest_cache, *.pyc, .DS_Store) and the marker file an installer writes into a copied
skill folder (.installed-by-ai-workbench). A change to SKILL.md, a reference, an asset or a script changes it;
a case, an evidence file, a test and files outside the folder do not: none of them is read by a model that
uses the skill, and none is copied into an eval run. Each case has a hash of its own (`hash --skill <name>`
prints both): over the whole case object as it stands in the case file and the bytes of its fixture files,
with "workbench_files" as the list of paths, never as the content of those files.

Evidence. The eval runner writes one file per test event, skills/<name>/evals/evidence/lab-<test id>.jsonl
(the reliability model, section 1): a first line that describes the event and one line per run. Both have
closed keys: `evidence` below validates every file, and an unknown key or a value outside its form is an
error. A committed evidence file is written by tooling and never edited. The old records, result.json, stay
as the history of the first round; the status below still reads them until the bands replace it.

  The event line: {"record": "test", "skill", "test", "kind": "full"|"partial", "version", "content_sha256",
   "date", "models": {tier: model id}, "adapters": {tier: adapter}, "adapter_sha256": {adapter: sha256 of its
   run-prompt.sh}, "grader", "runs", "timeout_seconds", "retries", "measurement_version",
   "measurement_sha256", "image_digest", "image_platform", "grading_template_sha256", "tools": {name:
   version}, "cases": {case id: case hash}, "baseline": {case id: "run"|"reused"|"none"}, "web_cases": [ids],
   "counts": {model id: {"with"|"without": {"retries", "refusals", "timeouts", "pauses", "early_ends",
   "resumes"[, "invoked"]}}}, "extra_pass_env": [names], "complete": bool[, "gate": {"passed", "with",
   "baseline", "threshold", "tolerance"[, "note"]}][, "upstream": {model id: provider}]}
  A run line: {"record": "run", "skill", "version", "content_sha256", "model", "adapter", "kind", "test",
   "date", "measurement_version", "measurement_sha256", "case", "case_sha256", "variant": "with"|"without",
   "outcome": "graded"|"timeout", "score", "results": [0|1, ...][, "context_sha256"][, "platform"]
   [, "guard_failed": [positions]]}

A run line with "platform" is a run of a case of that platform's case file, skills/<name>/evals/platforms/
<platform>.json (eval_run.py --platform; the plan's decision 14c): it belongs to a partial test and to a run
with the skill. Such lines never enter the gate or a score: `status` shows, per platform and model, their mean
and their number of runs ("platforms" in a skill's row), counting the lines whose case is still in that file
with the same hash, at or above the measurement floor, of the current major version.

A model id in a line is an id of the gate file's "models" ({id: [aliases]}): an alias is written as its id,
anything else as "unknown", so that one model never falls into two rows and a private model name never enters
the repository. Without that key the known ids are the configured strong model, floor model and grader.

The eval gate is configured in evals/eval-gate.json, committed: {"strong_model", "strong_harness",
"floor_model", "floor_harness", "floor_pass_env": [variables], "strong_pass_env": [variables], "grader",
"threshold", "strong_tolerance", "measurement_version", "measurement_floor"}, once a measurement version is
closed "measurement_sha256", the optional "models" ({model id: [aliases]}, the ids an evidence line may
carry) and the optional keys that control a test event (below). It names the models, the adapters and the grader a gate run uses (eval_run.py takes
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

Control of a test event, all optional keys of the gate file (a key it lacks takes the default in brackets):
"runs" [3], the runs of every case; "timeout_seconds" [900], the limit of one model run; "retries" [2], how
often a run that timed out, was refused, failed in its adapter or ended early is made again inside the event;
"max_resumes" [3], how often `eval_run.py --resume` reruns one failed run before it is written as a timeout
with score 0; "total_jobs" [10], the model runs in progress at one time over every runner process of the
machine; "web_jobs" [{"strong": 2, "floor": 2}], the same for runs on the open network, per tier;
"web_cases", {skill: [case ids]}, the only cases that may set "allow_web" (with a gate file and no such key,
none may); "strong_web_pass_env", the variables a strong-model run of a web case receives in place of
"strong_pass_env" (a low-limit API key in place of the account's token). An event made with another number of
runs, another timeout or another number of retries than these writes no evidence (eval_run.py --help).

Status of a skill:
  draft      no record, or a record whose gate did not pass (on the configured threshold) or that is not complete
  evaluated  the record passed, is complete, is of the configured measurement version, strong model, grader
             and floor model, and its content_sha256 equals the current hash
  stale      the record passed and is complete, but under another measurement version, strong model, grader
             or floor model than the configured ones, or the skill folder changed since

Commands:
  status     prints {"skills": [{"skill", "status", "date", "scores", "reason"[, "platforms": {platform: {model id:
             {"mean", "runs"}}}]}], "counts",
             "gate": {"floor_model", "threshold", "strong_model", "grader", "strong_tolerance", "measurement_version"}}
             (the configured gate; null values without the file).
  hash       prints the content hash of one skill, its version and the hash of each of its cases (and of each case of
             its platforms' case files, "platform_cases").
  evidence   validates the evidence files: every skill's, one skill's (--skill) or one file (--file <path>,
             which may be in a run folder's scratch tree). Prints {"files", "problems": {path: [...]}};
             exit 1 when a file is not valid.
  gate       prints the gate of one skill computed from its lab evidence (the model's section 2, below):
             {"computed", "passed", "with", "baseline", "threshold", "tolerance", "version", "test", "cases",
             "pending", "note", "cause"}.
  inventory  regenerates the block between <!-- eval-status:begin --> and <!-- eval-status:end --> in
             docs/inventory.md (--write), or exits 1 when the block differs from what would be generated (--check).
  measurement  commits a change of a file the measurement fingerprint covers as one of the three kinds of the
             reliability model's section 8, and rewrites the gate file: --kind grader raises the measurement
             version and the floor; --kind execution raises the version and appends an epoch dated --date (today,
             UTC, by default) for the skills of --skills and the models of --models ("all" by default, the listed
             ids otherwise; a hosted model that changed under its id is entered this way, with --models <its id>);
             --kind infrastructure writes the new fingerprint alone, and refuses when it is unchanged. Each writes
             the fingerprint this checkout computes. No kind multiplies old evidence by a factor. --close writes the
             fingerprint of a measurement version that is still open, which closes it; a --kind change needs a
             closed version. Prints {"kind", "measurement_version", "measurement_floor", "measurement_sha256",
             "epoch", "decisions_entry"}: the entry is added to docs/decisions.md in the same commit.

  bump       raises a skill's metadata.version by one step of the class of its change (the reliability model's
             section 3): x, y or z raises that part of the version of the pull request's base (comparison_base:
             WB_BASE_REF, else the merge base with the default branch) and resets the lower parts, writes it into
             SKILL.md and appends one line to skills/<name>/evals/versions.jsonl: {"version", "content_sha256",
             "class", "date"[, "z_chars"]}, z_chars being the characters a Z change counts. Idempotent: run again,
             or with a higher class after more edits, it rewrites the one line this pull request adds. With no
             class it writes the first line of a skill that has none in the base, with the version of its
             frontmatter (X.Y.Z) and the hash of its content as it then is, class "new": run it again after the
             last edit. Prints the line.
  migrate-versions  writes the version file of every skill that has none: one line, the version read as X.Y.Z
             (a two-part 0.N is 0.N.0), the current content hash, class "new". It edits no SKILL.md.

The version rules the validator applies (scripts/validate.py, against the same base; version_findings): the
content hash equals the hash of the version file's last line, and metadata.version is X.Y.Z and that line's
version (a warning until the sweep that closes phase C, an error from it); the file is append-only, with at
most one line added; the class of the added line agrees with the diff (change_class): X for a difference in
side_effects, an item removed from outputs or updates, a changed line of the Confirmation gate or Stop rules
section or of the external-content line; Z only for lines of SKILL.md in Purpose or before the first heading
that change no number, path, code span or listed word, within 300 characters since the newest lab evidence;
Y for the rest. A declared X is never refused. Without a base (a skill built in a case folder) the last two
are skipped.

The measurement fingerprint: sha256 over the files of FINGERPRINT_FILES (the grading template, the measuring
module evals/measure.py and its constants evals/measurement.json, the executor, the staging module), every file
of evals/container/, and the run-prompt.sh and adapter.json of each eval adapter. scripts/validate.py fails when
it differs from a committed "measurement_sha256"; the runner computes it when an event starts, writes it into
every evidence line and writes no evidence when it differs.

The gate (the reliability model, section 2). Only a full test evaluates it, and the runner writes its result
into the event line when the test ends; `gate` computes it again from the lines. It is computed over the run
lines with the skill, of kind full, on the reference model (strong_model), of the X.Y version the newest full
test ran on and of the same epoch as that test, every current case being required and only lines of weight
above zero being counted: the case exists with the same hash, the measurement version is at or above the
floor, and the line's major version is the current one. A second full test of an unchanged X.Y adds its runs
to the first and replaces none; a full test closed as abandoned keeps its lines. The mean of those lines
passes when it is at the threshold or above and is not below the mean of the baselines in force by more than
the tolerance, both unrounded. A partial test never moves the gate, with one exception: a case added after
the newest full test is "pending", and is left out of the gate, until it has with-skill lines and a baseline
in force (eval_run.py --cases <id> --baseline); those lines then enter the gate. A case changed after the
newest full test makes the gate impossible to compute until a full test runs it. When a case of the gate has
no baseline in force (after an epoch that reaches the skill), the result the newest full test wrote stands,
with the note "baseline expired".
A baseline line is in force while three things are unchanged: the case (its hash), the reference model (no
epoch of it after the line's date: "epochs" of the gate file, [{"date", "models", "skills", "cause"}], where
models and skills are lists or "all"), and the measurement (its version at or above the floor). The skill's
version does not age it: a run without the skill never saw the skill.

Data goes to stdout as JSON, diagnostics to stderr. Standard library only.
Exit codes: 0 ok, 1 the inventory block is out of date (--check) or an evidence file is not valid, 2 usage error.
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
EVALS_REL = "evals"  # the cases, the evidence, the version file and the old record: outside the content hash
EVIDENCE_REL = os.path.join("evals", "evidence")
CACHE_DIRS = ("__pycache__", ".pytest_cache")
INSTALL_MARKER = ".installed-by-ai-workbench"  # what an installer writes into a skill folder it copied
BEGIN, END = "<!-- eval-status:begin -->", "<!-- eval-status:end -->"
INVENTORY_REL = os.path.join("docs", "inventory.md")
GATE_REL = os.path.join("evals", "eval-gate.json")
GATE_FIELDS = {"strong_model": str, "strong_harness": str, "floor_model": str, "floor_harness": str,
               "floor_pass_env": list, "strong_pass_env": list, "grader": str, "threshold": (int, float), "strong_tolerance": (int, float),
               "measurement_version": int, "measurement_floor": int}
GATE_OPTIONAL = {"measurement_sha256": str,  # absent while a measurement version is open
                 # Control of a test event (event_config below): absent keys take the defaults of EVENT_DEFAULTS.
                 "runs": int, "timeout_seconds": int, "retries": int, "max_resumes": int, "total_jobs": int,
                 "web_jobs": dict, "web_cases": dict, "strong_web_pass_env": list, "models": dict,
                 "epochs": list}  # [{"date", "models", "skills", "cause"}]: the model's section 8
# What an event uses when the gate file does not say: 3 runs per case (the plan's decision 1), 900 seconds per
# run, 2 retries inside the event, 3 resumptions of one run before it is written as a timeout, 10 runs at a
# time over every runner process of the machine, 2 runs on the open network at a time per tier.
EVENT_DEFAULTS = {"runs": 3, "timeout_seconds": 900, "retries": 2, "max_resumes": 3, "total_jobs": 10,
                  "web_jobs": {"strong": 2, "floor": 2}}
EVENT_RANGES = {"runs": (1, 10), "timeout_seconds": (30, 86400), "retries": (0, 5), "max_resumes": (0, 10), "total_jobs": (1, 64)}
TIERS = ("strong", "floor")
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
    return out or event_problems(cfg)


def whole(value, low, high):
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def event_problems(cfg):
    """Why the keys that control a test event are not valid; every one of them is optional."""
    out = []
    for key, (low, high) in EVENT_RANGES.items():
        if key in cfg and not whole(cfg[key], low, high):
            out.append(f"{key} must be a whole number from {low} to {high}")
    jobs = cfg.get("web_jobs")
    if "web_jobs" in cfg and not (isinstance(jobs, dict) and set(jobs) == set(TIERS) and all(whole(v, 1, 64) for v in jobs.values())):
        out.append("web_jobs must give a whole number, 1 or more, for \"strong\" and for \"floor\"")
    cases = cfg.get("web_cases")
    if "web_cases" in cfg and not (isinstance(cases, dict) and all(
            isinstance(k, str) and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", k) and isinstance(v, list) and v
            and all(isinstance(i, (int, str)) and not isinstance(i, bool) for i in v) for k, v in cases.items())):
        out.append("web_cases must map a skill name to the list of its case ids that may use the web")
    names = cfg.get("strong_web_pass_env")
    if "strong_web_pass_env" in cfg and not (isinstance(names, list) and all(
            isinstance(v, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v) for v in names)):
        out.append("strong_web_pass_env must list variable names")
    if "epochs" in cfg:
        out += [f"epochs[{i}] {why}" for i, entry in enumerate(cfg["epochs"] if isinstance(cfg["epochs"], list) else [None])
                for why in epoch_problems(entry)]
    models = cfg.get("models")
    if "models" in cfg:
        names = [n for k, v in models.items() for n in [k] + (v if isinstance(v, list) else [])] if isinstance(models, dict) else []
        if not (isinstance(models, dict) and models and all(isinstance(v, list) for v in models.values())
                and all(isinstance(n, str) and MODEL_RE.fullmatch(n) and n != "unknown" for n in names)):
            out.append("models must map each known model id to the list of its aliases")
        elif len(set(names)) != len(names):
            out.append("models names an id or an alias twice: one model is one id")
        else:
            for key in ("strong_model", "floor_model", "grader"):
                if cfg.get(key) not in names:
                    out.append(f"{key} {cfg.get(key)!r} is not in models: every configured model is a known one")
    return out


def event_config(cfg):
    """The values that control a test event: the gate file's, and EVENT_DEFAULTS for a key it does not carry.
    cfg is a loaded gate configuration ({} when there is none)."""
    out = {key: cfg.get(key, default) for key, default in EVENT_DEFAULTS.items()}
    out["web_jobs"] = dict(out["web_jobs"])
    return out


def web_case_allowed(cfg, skill, case_id):
    """True when the gate file lists the case among those that may use the web. Without a gate file there is no
    list, and nothing is refused; with one, a case it does not list never gets the open network."""
    if not cfg:
        return True
    return str(case_id) in {str(i) for i in (cfg.get("web_cases") or {}).get(skill, [])}


def evidence_refusal(root=ROOT):
    """Why nothing measured now may be written as evidence (eval_run.py asks it), or None when it may.

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

    Left out, because no model that uses the skill reads them: all of evals/ (the cases, the evidence, the
    version file, the old record), the tests of the skill's scripts (TESTS_REL), caches, and the marker file an
    installer writes into a copied skill folder. So a case, an evidence file or a test changes no hash, and a
    copy an installer made has the hash of its source.
    """
    files = []
    for dp, dns, fns in os.walk(skill_dir):
        top = dp == skill_dir
        dns[:] = sorted(d for d in dns if d not in CACHE_DIRS and not (top and d == EVALS_REL))
        for fn in fns:
            rel = os.path.relpath(os.path.join(dp, fn), skill_dir).replace(os.sep, "/")
            if rel.startswith(TESTS_REL + "/"):
                continue
            if fn == ".DS_Store" or fn.endswith(".pyc") or (top and fn == INSTALL_MARKER):
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


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _litter(name):
    return name in CACHE_DIRS or name == ".DS_Store" or name.endswith(".pyc")


def case_hash(skill_dir, case, top_allow_web=False):
    """sha256 over the whole case: the case object as it stands in the case file (its prompt, its assertions
    with their tags, grader_files, skills, setup, allow_web, workbench_files as the list of paths, its tags,
    every other key) and the bytes of its fixture files. A change to one case changes that case's hash only.
    top_allow_web is the file's own "allow_web", which applies to every case of the file."""
    obj = {**case, "allow_web": True} if top_allow_web and not case.get("allow_web") else case
    h = hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    for entry in case.get("files") or []:
        if not isinstance(entry, str):
            continue
        src, found = os.path.join(skill_dir, entry), []
        if os.path.isdir(src):
            for dp, dns, fns in os.walk(src):
                dns[:] = sorted(d for d in dns if not _litter(d))
                found += [os.path.join(dp, fn) for fn in fns if not _litter(fn)]
        elif os.path.isfile(src):
            found = [src]
        for path in sorted(found):
            rel = entry.strip("/") + "/" + os.path.relpath(path, src).replace(os.sep, "/") if os.path.isdir(src) else entry
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                data = b""  # a dangling link: its name still counts
            h.update(b"\0file\0" + rel.encode("utf-8") + b"\0" + str(len(data)).encode() + b"\0" + data)
    return h.hexdigest()


def case_hashes(skill_dir, platform=None):
    """{case id as text: hash} of the skill's current cases, those of evals/evals.json or, with platform, those of
    that platform's case file (evals/platforms/<platform>.json); {} when there is no readable case file."""
    rel = ("platforms", platform + ".json") if platform else ("evals.json",)
    try:
        with open(os.path.join(skill_dir, "evals", *rel), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    cases = data.get("evals") if isinstance(data, dict) else None
    return {str(c.get("id")): case_hash(skill_dir, c, data.get("allow_web") is True)
            for c in cases or [] if isinstance(c, dict)}


def platform_names(skill_dir):
    """The platforms that have a case file for the skill (evals/platforms/<platform>.json): the plan's decision 14c."""
    folder = os.path.join(skill_dir, "evals", "platforms")
    if not os.path.isdir(folder):
        return []
    return sorted(n[:-len(".json")] for n in os.listdir(folder) if n.endswith(".json") and NAME_RE.fullmatch(n[:-len(".json")]))


def context_hash(dependency_dirs, references):
    """One hash over what a run was given besides the skill under test: the dependency skills the case
    installs (each by name and content hash) and the shared and platform references staged into the run
    (references: [(path relative to shared/references, file path)]). None when there is neither. A line that
    ran with another context than the current one counts as inherited evidence."""
    parts = [f"skill\0{os.path.basename(os.path.normpath(d))}\0{content_hash(d)}" for d in dependency_dirs]
    parts += [f"reference\0{rel}\0{file_sha256(path)}" for rel, path in references]
    if not parts:
        return None
    return hashlib.sha256("\n".join(sorted(parts)).encode("utf-8")).hexdigest()


def skill_version(skill_dir):
    """metadata.version of the skill as X.Y.Z, or None when it has none in a known form. A two-part version,
    the form every skill had before the version rules, is read as X.Y.0."""
    try:
        with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    m = re.search(r"^\s+version:\s*[\"']?([0-9]+(?:\.[0-9]+){1,2})[\"']?\s*(?:#.*)?$", text.split("\n---", 1)[0], re.M)
    if not m:
        return None
    parts = m.group(1).split(".")
    return ".".join(parts + ["0"] * (3 - len(parts)))


def known_models(cfg):
    """{model id: [aliases]} of a gate configuration: its "models", or, without that key, the configured
    strong model, floor model and grader with no alias."""
    if isinstance(cfg.get("models"), dict):
        return {k: list(v) for k, v in cfg["models"].items()}
    return {cfg[k]: [] for k in ("strong_model", "floor_model", "grader") if cfg.get(k)}


def model_id(cfg, name):
    """The id a model is written under in an evidence line: the listed id for a listed id or one of its
    aliases, "unknown" for anything else. Without a gate configuration there is no list: the name as given."""
    if not cfg:
        return name
    for listed, aliases in known_models(cfg).items():
        if name == listed or name in aliases:
            return listed
    return "unknown"


# The files that decide what a run measures (item B10 of the plan): the grading template, the measuring module
# and its constants, the executor, the staging module; with them every file of the image's definition
# (evals/container/) and the run-prompt.sh and adapter.json of each eval adapter (an adapter with a
# run-prompt.sh). Not in it: scripts/redact.py and shared/references/ (FR-I4), the rest of the runner
# (infrastructure), the gate file itself. scripts/validate.py compares the result with the committed
# "measurement_sha256", and the runner refuses to write evidence when they differ.
FINGERPRINT_FILES = ("evals/grading-prompt.md", "evals/measure.py", "evals/measurement.json", "evals/executor.py",
                     "scripts/stage_skills.py")
MEASURE_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "measure.py")


def load_measure():
    """evals/measure.py as a module, loaded on first use: the gate's comparison lives there. A command that
    compares nothing (status, hash, evidence, inventory) runs without it."""
    import importlib.util
    name = "workbench_eval_measure"
    if name not in sys.modules:
        if not os.path.isfile(MEASURE_SCRIPT):
            die("evals/measure.py is missing: run this script from a checkout of the workbench.")
        spec = importlib.util.spec_from_file_location(name, MEASURE_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[name] = module
    return sys.modules[name]


def measurement_fingerprint(root=ROOT):
    """sha256 over the files that decide what a run measures (sorted relative paths and their bytes). The
    runner computes it when an event starts and writes it into every evidence line."""
    paths = [os.path.join(root, *rel.split("/")) for rel in FINGERPRINT_FILES]
    for dp, dns, fns in os.walk(os.path.join(root, "evals", "container")):
        dns[:] = sorted(d for d in dns if d not in CACHE_DIRS)
        paths += [os.path.join(dp, fn) for fn in fns if not _litter(fn)]
    adapters = os.path.join(root, "adapters")
    for name in sorted(os.listdir(adapters)) if os.path.isdir(adapters) else []:
        if os.path.isfile(os.path.join(adapters, name, "run-prompt.sh")):  # an eval adapter
            paths += [os.path.join(adapters, name, "run-prompt.sh"), os.path.join(adapters, name, "adapter.json")]
    h = hashlib.sha256()
    for path in sorted(p for p in paths if os.path.isfile(p)):
        with open(path, "rb") as f:
            data = f.read()
        h.update(os.path.relpath(path, root).replace(os.sep, "/").encode("utf-8") + b"\0" + str(len(data)).encode() + b"\0" + data)
    return h.hexdigest()


def fingerprint_problem(root=ROOT):
    """Why the committed measurement fingerprint is not the one of this checkout, or None when they agree or when
    there is none to compare (no gate file, or a measurement version still open)."""
    cfg = load_gate(root)
    committed = cfg.get("measurement_sha256")
    if not committed:
        return None
    current = measurement_fingerprint(root)
    if current == committed:
        return None
    return (f"the measurement fingerprint of this checkout ({current[:12]}...) differs from the committed one "
            f"({committed[:12]}...) in {GATE_REL}: a file that decides what a run measures changed. Commit the change "
            "as one of the three kinds of the reliability model's section 8: python3 evals/eval_status.py measurement "
            "--kind grader|execution|infrastructure --cause \"<why>\"")


MEASUREMENT_KINDS = ("grader", "execution", "infrastructure")
KIND_TEXT = {
    "grader": "grader side: what the grader is shown, the grading rules or the scoring changed. The measurement "
              "version and the floor are raised: every lab line below the floor weighs nothing, and every skill needs "
              "a full test",
    "execution": "execution side: the image, an adapter, the runner's prompt or tools, the executor, the staging, or a "
                 "hosted model under its id changed. The measurement version is raised and an epoch is entered: for "
                 "the skills and models it reaches, earlier lab lines are inherited evidence and the baselines expire",
    "infrastructure": "infrastructure: locks, resumption, retries, pacing or reports changed in a file the "
                      "fingerprint covers. No version is raised; the new fingerprint is committed with the reason",
}


def format_gate(cfg):
    """The gate file's text: two spaces of indentation, a list of plain values on one line, an object or a list of
    objects over several lines."""
    def value(v, indent):
        pad = " " * indent
        if isinstance(v, dict) and v:
            return "{\n" + ",\n".join(f"{pad}  {json.dumps(k)}: {value(x, indent + 2)}" for k, x in v.items()) + "\n" + pad + "}"
        if isinstance(v, list) and any(isinstance(x, (dict, list)) for x in v):
            return "[\n" + ",\n".join(f"{pad}  {value(x, indent + 2)}" for x in v) + "\n" + pad + "]"
        return json.dumps(v, ensure_ascii=False)
    return value(cfg, 0) + "\n"


def measurement_change(root, kind=None, cause=None, skills="all", models="all", date=None, close=False):
    """Commit a change of a file the fingerprint covers as one of the three kinds of the model's section 8, or
    (close=True) close an open measurement version by writing its fingerprint. Returns (the new gate
    configuration, what to print). Raises ValueError with the reason when it cannot."""
    path = os.path.join(root, GATE_REL)
    if not os.path.isfile(path):
        raise ValueError(f"{GATE_REL} does not exist")
    problems = gate_problems(root)
    if problems:
        raise ValueError(f"{GATE_REL} is not valid: {'; '.join(problems)}")
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    date = date or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    if not _date(date):
        raise ValueError("--date must be YYYY-MM-DD")
    if not (isinstance(cause, str) and cause.strip() and "\n" not in cause):
        raise ValueError("--cause takes one line that says what changed and why")
    current, old = measurement_fingerprint(root), cfg["measurement_version"]
    new = dict(cfg)
    if close:
        if cfg.get("measurement_sha256"):
            raise ValueError(f"measurement version {old} is closed already: a later change is committed with --kind")
        new["measurement_sha256"] = current
        title = f"measurement version {old} closed"
        lines = [f"- Measurement version {old}, floor {cfg['measurement_floor']}: nothing measured while it was open is evidence; "
                 "from this commit on the runner writes evidence under it."]
        epoch = None
    else:
        if kind not in MEASUREMENT_KINDS:
            raise ValueError("--kind is grader, execution or infrastructure")
        if not cfg.get("measurement_sha256"):
            raise ValueError(f"measurement version {old} is open (no measurement_sha256): a change made while it is open "
                             "belongs to it. Close it with --close when its last change is in")
        if kind == "infrastructure" and current == cfg["measurement_sha256"]:
            raise ValueError("the fingerprint is unchanged: no file that decides what a run measures changed")
        epoch = None
        if kind == "grader":
            new.update(measurement_version=old + 1, measurement_floor=old + 1)
        elif kind == "execution":
            names = skill_names(root)
            if skills != "all":
                unknown = [s for s in skills if s not in names]
                if unknown or not skills:
                    raise ValueError(f"--skills names no skill of this tree: {', '.join(unknown) or '(none)'}")
            if models != "all":
                ids = [model_id(cfg, m) for m in models]
                if not models or "unknown" in ids:
                    raise ValueError("--models names a model the gate file does not list (models)")
                models = sorted(set(ids))
            epoch = {"date": date, "models": models, "skills": sorted(set(skills)) if skills != "all" else "all", "cause": cause}
            new.update(measurement_version=old + 1, epochs=list(cfg.get("epochs") or []) + [epoch])
        new["measurement_sha256"] = current
        title = f"measurement change, {kind}" + (f" (measurement version {old} to {new['measurement_version']})"
                                                  if new["measurement_version"] != old else "")
        lines = [f"- Kind: {KIND_TEXT[kind]}."]
        if kind == "grader":
            lines.append(f"- Measurement version and floor: {new['measurement_version']}.")
        if epoch:
            lines.append(f"- Epoch {epoch['date']}: skills {epoch['skills'] if epoch['skills'] == 'all' else ', '.join(epoch['skills'])}; "
                         f"models {epoch['models'] if epoch['models'] == 'all' else ', '.join(epoch['models'])}.")
    lines += [f"- Fingerprint: `{current}`.",
              "- Written by `python3 evals/eval_status.py measurement "
              + ("--close" if close else f"--kind {kind}") + "`."]
    entry = f"## {date}: {title}\n\n{cause.strip()}\n\n" + "\n".join(lines) + "\n"
    out = {"kind": "close" if close else kind, "measurement_version": new["measurement_version"],
           "measurement_floor": new["measurement_floor"], "measurement_sha256": current, "epoch": epoch,
           "decisions_entry": entry}
    return new, out


def new_test_id(now=None):
    """The id of a test event: the UTC time it started and eight random hexadecimal characters, so two events
    never share a file and ids sort by time."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y%m%dT%H%M%SZ") + "-" + os.urandom(4).hex()


# --- evidence: the closed forms of an event line and of a run line -------------------------------------

HEX64_RE = re.compile(r"[0-9a-f]{64}")
TEST_ID_RE = re.compile(r"\d{8}T\d{6}Z-[0-9a-f]{8}")
VERSION_RE = re.compile(r"\d+\.\d+\.\d+")
NAME_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
CASE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@-]{0,199}")
VARIABLE_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
TOOL_RE = re.compile(r"[A-Za-z0-9 ._()/+:,-]{1,80}")
KINDS, VARIANT_NAMES, OUTCOMES, BASELINES = ("full", "partial"), ("with", "without"), ("graded", "timeout"), ("run", "reused", "none")
COUNT_KEYS = ("retries", "refusals", "timeouts", "pauses", "early_ends", "resumes")
EVENT_REQUIRED = ("record", "skill", "test", "kind", "version", "content_sha256", "date", "models", "adapters",
                  "adapter_sha256", "grader", "runs", "timeout_seconds", "retries", "measurement_version",
                  "measurement_sha256", "image_digest", "image_platform", "grading_template_sha256", "tools", "cases",
                  "baseline", "web_cases", "counts", "extra_pass_env", "complete")
EVENT_OPTIONAL = ("gate", "upstream")
RUN_REQUIRED = ("record", "skill", "version", "content_sha256", "model", "adapter", "kind", "test", "date",
                "measurement_version", "measurement_sha256", "case", "case_sha256", "variant", "outcome", "score", "results")
RUN_OPTIONAL = ("context_sha256", "platform", "guard_failed")
GATE_KEYS = ("passed", "with", "baseline", "threshold", "tolerance")


def _is(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _number(value, low=0, high=1):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and low <= value <= high


def _count(value, low=0):
    return isinstance(value, int) and not isinstance(value, bool) and value >= low


def _model(value, models):
    return value == "unknown" or (_is(MODEL_RE, value) and (models is None or value in models))


def _case_id(value):
    return _count(value) or _is(CASE_ID_RE, value)


def _keys(line, required, optional):
    out = [f"unknown key {k!r}" for k in line if k not in required and k not in optional]
    return out + [f"missing key {k!r}" for k in required if k not in line]


def event_line_problems(line, models=None):
    """Why an event line is outside its form; models is the set of known model ids, None when there is no list."""
    out = _keys(line, EVENT_REQUIRED, EVENT_OPTIONAL)
    if out:
        return out
    bad = lambda key, form: out.append(f"{key} must be {form}")
    if line["record"] != "test":
        bad("record", "\"test\"")
    if not _is(NAME_RE, line["skill"]):
        bad("skill", "a skill name")
    if not _is(TEST_ID_RE, line["test"]):
        bad("test", "a test id (YYYYMMDDTHHMMSSZ-8 hex)")
    if line["kind"] not in KINDS:
        bad("kind", "full or partial")
    if not _is(VERSION_RE, line["version"]):
        bad("version", "X.Y.Z")
    for key in ("content_sha256", "measurement_sha256", "grading_template_sha256"):
        if not _is(HEX64_RE, line[key]):
            bad(key, "64 hexadecimal characters")
    if not _date(line["date"]):
        bad("date", "YYYY-MM-DD")
    tiers = line["models"]
    if not (isinstance(tiers, dict) and tiers and "strong" in tiers and set(tiers) <= set(TIERS)
            and all(_model(v, models) for v in tiers.values())):
        bad("models", "{\"strong\": model id[, \"floor\": model id]}, each a listed id or \"unknown\"")
        tiers = {}
    if not (isinstance(line["adapters"], dict) and set(line["adapters"]) == set(tiers or line["adapters"])
            and all(_is(NAME_RE, v) for v in line["adapters"].values())):
        bad("adapters", "an adapter's folder name for each tier of models")
    hashes = line["adapter_sha256"]
    if not (isinstance(hashes, dict) and all(_is(NAME_RE, k) and _is(HEX64_RE, v) for k, v in hashes.items())
            and (not isinstance(line["adapters"], dict) or set(hashes) == set(line["adapters"].values()))):
        bad("adapter_sha256", "the sha256 of the run-prompt.sh of each adapter named in adapters")
    if not _model(line["grader"], models):
        bad("grader", "a listed model id or \"unknown\"")
    for key, low in (("runs", 1), ("timeout_seconds", 1), ("retries", 0), ("measurement_version", 1)):
        if not _count(line[key], low):
            bad(key, f"a whole number, {low} or more")
    if not (isinstance(line["image_digest"], str) and re.fullmatch(r"sha256:[0-9a-f]{64}", line["image_digest"])):
        bad("image_digest", "sha256:<64 hexadecimal characters>")
    if not (isinstance(line["image_platform"], str) and re.fullmatch(r"linux/[a-z0-9]+(/[a-z0-9]+)?", line["image_platform"])):
        bad("image_platform", "a platform such as linux/arm64")
    if not (isinstance(line["tools"], dict) and all(_is(NAME_RE, k) and _is(TOOL_RE, v) for k, v in line["tools"].items())):
        bad("tools", "{tool name: its version line}")
    cases = line["cases"]
    if not (isinstance(cases, dict) and cases and all(_is(CASE_ID_RE, k) and _is(HEX64_RE, v) for k, v in cases.items())):
        bad("cases", "{case id: the case's hash}, at least one")
        cases = {}
    if not (isinstance(line["baseline"], dict) and set(line["baseline"]) == set(cases or line["baseline"])
            and all(v in BASELINES for v in line["baseline"].values())):
        bad("baseline", "run, reused or none for each case of cases")
    if not (isinstance(line["web_cases"], list) and all(_case_id(v) and str(v) in (cases or {str(v): 1}) for v in line["web_cases"])):
        bad("web_cases", "a list of ids of cases")
    counts = line["counts"]
    ok = isinstance(counts, dict) and all(_model(model, models) and isinstance(by, dict) and by and set(by) <= set(VARIANT_NAMES)
                                          for model, by in counts.items())
    for by in counts.values() if ok else []:
        for variant, c in by.items():
            allowed = COUNT_KEYS + (("invoked",) if variant == "with" else ())
            ok = ok and isinstance(c, dict) and set(COUNT_KEYS) <= set(c) and set(c) <= set(allowed) and all(_count(v) for v in c.values())
    if not ok:
        bad("counts", "{model id: {\"with\"|\"without\": {" + ", ".join(COUNT_KEYS) + "[, invoked]: whole numbers}}}")
    if not (isinstance(line["extra_pass_env"], list) and all(_is(VARIABLE_RE, v) for v in line["extra_pass_env"])):
        bad("extra_pass_env", "a list of variable names")
    if not isinstance(line["complete"], bool):
        bad("complete", "true or false")
    if "gate" in line:
        g = line["gate"]
        if line["kind"] != "full":
            out.append("gate belongs to a full test only: a partial test never evaluates the gate")
        elif not (isinstance(g, dict) and set(GATE_KEYS) <= set(g) and set(g) <= set(GATE_KEYS + ("note",))
                  and isinstance(g["passed"], bool) and _number(g["with"]) and (g["baseline"] is None or _number(g["baseline"]))
                  and _number(g["threshold"]) and _number(g["tolerance"]) and g.get("note", "baseline expired") == "baseline expired"):
            bad("gate", "{\"passed\": bool, \"with\": mean, \"baseline\": mean or null, \"threshold\", \"tolerance\"[, \"note\": \"baseline expired\"]}")
        elif line["complete"] is not True:
            out.append("gate is written by a complete full test only: an event closed as abandoned evaluates no gate")
    elif line["kind"] == "full" and line["complete"] is True:
        out.append("a complete full test carries its gate")
    if "upstream" in line and not (isinstance(line["upstream"], dict) and all(
            _model(k, models) and _is(TOOL_RE, v) for k, v in line["upstream"].items())):
        bad("upstream", "{model id: the upstream provider its responses name}")
    return out


def run_line_problems(line, event=None, models=None):
    """Why a run line is outside its form, or disagrees with the event line of its file."""
    out = _keys(line, RUN_REQUIRED, RUN_OPTIONAL)
    if out:
        return out
    bad = lambda key, form: out.append(f"{key} must be {form}")
    if line["record"] != "run":
        bad("record", "\"run\"")
    if not _is(NAME_RE, line["skill"]):
        bad("skill", "a skill name")
    if not _is(VERSION_RE, line["version"]):
        bad("version", "X.Y.Z")
    for key in ("content_sha256", "measurement_sha256", "case_sha256") + (("context_sha256",) if "context_sha256" in line else ()):
        if not _is(HEX64_RE, line[key]):
            bad(key, "64 hexadecimal characters")
    if not _model(line["model"], models):
        bad("model", "an id of the gate file's model list, or \"unknown\"")
    if not _is(NAME_RE, line["adapter"]):
        bad("adapter", "an adapter's folder name")
    if line["kind"] not in KINDS:
        bad("kind", "full or partial")
    if not _is(TEST_ID_RE, line["test"]):
        bad("test", "a test id")
    if not _date(line["date"]):
        bad("date", "YYYY-MM-DD")
    if not _count(line["measurement_version"], 1):
        bad("measurement_version", "a whole number, 1 or more")
    if not _case_id(line["case"]):
        bad("case", "a case id")
    if line["variant"] not in VARIANT_NAMES:
        bad("variant", "with or without")
    if line["outcome"] not in OUTCOMES:
        bad("outcome", "graded or timeout")
    results = line["results"]
    if not (isinstance(results, list) and results and all(r in (0, 1) and not isinstance(r, bool) for r in results)):
        bad("results", "a list of 0 and 1, one per assertion")
        results = None
    if not _number(line["score"]):
        bad("score", "a number from 0 to 1")
    elif results and abs(line["score"] - sum(results) / len(results)) > 1e-9:
        out.append("score must be the share of results that are 1")
    if results and line["outcome"] == "timeout" and any(results):
        out.append("a timeout has score 0 and results all 0")
    if "platform" in line and not _is(NAME_RE, line["platform"]):
        bad("platform", "a platform name")
    elif "platform" in line and (line["kind"] != "partial" or line["variant"] != "with"):
        out.append("a line of a platform's case runs in a partial test, with the skill only")
    if "guard_failed" in line:
        failed = line["guard_failed"]
        if not (isinstance(failed, list) and failed and all(_count(v, 1) for v in failed) and len(set(failed)) == len(failed)
                and (results is None or all(v <= len(results) and results[v - 1] == 0 for v in failed))):
            bad("guard_failed", "a list of positions of assertions whose result is 0")
        elif line["variant"] != "with":
            out.append("guard_failed belongs to a with-skill run only")
    if event and not out:
        for key in ("skill", "test", "kind", "version", "content_sha256", "measurement_version", "measurement_sha256"):
            if line[key] != event.get(key):
                out.append(f"{key} differs from the event line of the file")
        if isinstance(event.get("models"), dict) and line["model"] not in event["models"].values():
            out.append("model is not one of the event's models")
        if isinstance(event.get("adapters"), dict) and line["adapter"] not in event["adapters"].values():
            out.append("adapter is not one of the event's adapters")
        if isinstance(event.get("cases"), dict) and event["cases"].get(str(line["case"])) != line["case_sha256"]:
            out.append("case and case_sha256 are not a case of the event line")
    return out


def read_evidence_file(path):
    """(event line or None, run lines, problems) of one evidence file, each line parsed and not yet judged."""
    problems, lines = [], []
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read().split("\n")
    except (OSError, UnicodeDecodeError) as e:
        return None, [], [f"cannot be read: {e}"]
    if raw and raw[-1] == "":
        raw.pop()
    for n, text in enumerate(raw, 1):
        try:
            obj = json.loads(text)
        except ValueError:
            problems.append(f"line {n}: not valid JSON")
            continue
        if not isinstance(obj, dict):
            problems.append(f"line {n}: must be a JSON object")
            continue
        lines.append((n, obj))
    if not lines:
        return None, [], problems or ["the file is empty: an evidence file has an event line"]
    return lines[0][1], lines[1:], problems


def evidence_file_problems(path, root=ROOT, skill=None):
    """Why one lab evidence file is not valid; an empty list when it is. skill is the folder the file belongs
    to; by default it is read from a path .../skills/<name>/evals/evidence/<file>."""
    name = os.path.basename(path)
    parts = os.path.normpath(os.path.abspath(path)).split(os.sep)
    if skill is None and len(parts) >= 5 and parts[-3:-1] == ["evals", "evidence"] and parts[-5] == "skills":
        skill = parts[-4]
    m = re.fullmatch(r"lab-(" + TEST_ID_RE.pattern + r")\.jsonl", name)
    if not m:
        return [f"the name must be lab-<test id>.jsonl, not {name}"]
    cfg = load_gate(root)
    models = set(known_models(cfg)) if cfg else None
    event, runs, problems = read_evidence_file(path)
    if event is None:
        return problems
    first = event_line_problems(event, models)
    problems += [f"line 1: {p}" for p in first]
    if not first:
        if event["test"] != m.group(1):
            problems.append("line 1: test differs from the file's name")
        if skill is not None and event["skill"] != skill:
            problems.append(f"line 1: skill must be the folder's name, {skill}")
    for n, line in runs:
        problems += [f"line {n}: {p}" for p in run_line_problems(line, None if first else event, models)]
    return problems


def evidence_files(skill_dir):
    """The lab evidence files of a skill, oldest first (a test id starts with its time)."""
    folder = os.path.join(skill_dir, EVIDENCE_REL)
    if not os.path.isdir(folder):
        return []
    return [os.path.join(folder, n) for n in sorted(os.listdir(folder)) if n.startswith("lab-") and n.endswith(".jsonl")]


def evidence_problems(root=ROOT, only=None):
    """{relative path: [problems]} for the evidence folders of every skill, or of one. A file whose name is
    neither lab-<test id>.jsonl nor field-<id>.jsonl is a problem: nothing else belongs in that folder."""
    found, checked = {}, 0
    for name in [only] if only else skill_names(root):
        folder = os.path.join(root, "skills", name, EVIDENCE_REL)
        for entry in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            rel = os.path.relpath(os.path.join(folder, entry), root)
            if re.fullmatch(r"field-[0-9a-f]{12}\.jsonl", entry):
                continue  # contributed field evidence: its own importer validates it
            checked += 1
            problems = evidence_file_problems(os.path.join(folder, entry), root, name)
            if problems:
                found[rel] = problems
    return found, checked


def skill_evidence(skill_dir):
    """[(event line, run lines)] of a skill's lab evidence files, oldest first. A file whose first line is not an
    event line is left out (`evidence` reports it); so is a run line that lacks a key the rules below read."""
    found = []
    for path in evidence_files(skill_dir):
        event, runs, _ = read_evidence_file(path)
        if not isinstance(event, dict) or event.get("record") != "test" or not isinstance(event.get("test"), str):
            continue
        found.append((event, [line for _, line in runs if all(k in line for k in RUN_REQUIRED)]))
    return found


def base_lines(runs):
    """The run lines of the cases of evals/evals.json: a line of a platform's case ("platform") enters neither the
    gate nor the score (the plan's decision 14c)."""
    return [line for line in runs if "platform" not in line]


def platform_results(skill_dir, cfg, events=None):
    """{platform: {model id: {"mean", "runs"}}} of the lines of the platforms' cases with the skill: a mean and a
    number of runs, never a score (decision 14c). A line counts when its case is still in that platform's case
    file with the same hash, its measurement version is at or above the floor and its major version is the
    skill's current one."""
    floor, version = cfg.get("measurement_floor", 1), skill_version(skill_dir)
    major = version.split(".")[0] if version else None
    hashes = {name: case_hashes(skill_dir, name) for name in platform_names(skill_dir)}
    scores = {}
    for _, runs in skill_evidence(skill_dir) if events is None else events:
        for line in runs:
            name = line.get("platform")
            if (name is None or line["variant"] != "with" or hashes.get(name, {}).get(str(line["case"])) != line["case_sha256"]
                    or line["measurement_version"] < floor or str(line["version"]).split(".")[0] != major):
                continue
            scores.setdefault(name, {}).setdefault(line["model"], []).append(line["score"])
    return {name: {model: {"mean": sum(v) / len(v), "runs": len(v)} for model, v in sorted(by.items())}
            for name, by in sorted(scores.items())}


def epoch_problems(entry):
    """Why one entry of the gate file's "epochs" is outside its form: {"date": YYYY-MM-DD, "models": "all" or a
    list of model ids, "skills": "all" or a list of skill names, "cause": a sentence}."""
    if not isinstance(entry, dict) or set(entry) != {"date", "models", "skills", "cause"}:
        return ["must be {\"date\", \"models\", \"skills\", \"cause\"}"]
    out = [] if _date(entry["date"]) else ["date must be YYYY-MM-DD"]
    for key, pattern in (("models", MODEL_RE), ("skills", NAME_RE)):
        value = entry[key]
        if not (value == "all" or (isinstance(value, list) and value and all(_is(pattern, v) for v in value))):
            out.append(f"{key} must be \"all\" or a list of names")
    if not (isinstance(entry["cause"], str) and entry["cause"].strip() and "\n" not in entry["cause"]):
        out.append("cause must be one line of text")
    return out


def epochs(cfg):
    """The epochs of a gate configuration: [{"date", "models", "skills", "cause"}]; models and skills are lists or
    "all". The key is optional: without it there is none."""
    return [e for e in cfg.get("epochs") or [] if isinstance(e, dict) and _date(e.get("date"))]


def reaches(epoch, skill, model):
    applies = lambda value, name: value == "all" or (isinstance(value, list) and name in value)
    return applies(epoch.get("skills"), skill) and applies(epoch.get("models"), model)


def epoch_after(cfg, skill, model, date, until=None):
    """True when an epoch that reaches the skill on that model is dated after `date` (and not after `until`)."""
    return any(reaches(e, skill, model) and e["date"] > date and (until is None or e["date"] <= until) for e in epochs(cfg))


def reference_model(cfg):
    """The id the reference model's lines carry: the configured strong model, as the model list writes it."""
    return model_id(cfg, cfg["strong_model"]) if cfg.get("strong_model") else None


def baseline_lines(skill_dir, cfg, events=None):
    """{case id: [baseline lines in force]}: lines without the skill, on the reference model, of the case's current
    hash, at or above the measurement floor, with no epoch of that model after their date."""
    skill = os.path.basename(os.path.normpath(skill_dir))
    current, ref, floor = case_hashes(skill_dir), reference_model(cfg), cfg.get("measurement_floor", 1)
    found = {}
    for _, runs in skill_evidence(skill_dir) if events is None else events:
        for line in base_lines(runs):
            cid = str(line["case"])
            if (line["variant"] == "without" and (ref is None or line["model"] == ref) and current.get(cid) == line["case_sha256"]
                    and line["measurement_version"] >= floor and not epoch_after(cfg, skill, line["model"], line["date"])):
                found.setdefault(cid, []).append(line)
    return found


def gate_of(skill_dir, cfg, extra=()):
    """The gate of a skill from its lab evidence and the events in extra (the event the runner is ending, whose
    file is not in the skill yet), by the rule of the model's section 2 (see the module's help)."""
    skill = os.path.basename(os.path.normpath(skill_dir))
    events = sorted(((e, base_lines(runs)) for e, runs in skill_evidence(skill_dir) + list(extra)), key=lambda e: e[0]["test"])
    current, version = case_hashes(skill_dir), skill_version(skill_dir)
    ref, floor = reference_model(cfg), cfg.get("measurement_floor", 1)
    threshold, tolerance = cfg.get("threshold", 0.8), cfg.get("strong_tolerance", 0)
    out = {"computed": False, "passed": None, "with": None, "baseline": None, "threshold": threshold, "tolerance": tolerance,
           "version": None, "test": None, "cases": [], "pending": [], "note": None, "cause": None}
    major = version.split(".")[0] if version else None
    full = [e for e in events if e[0].get("kind") == "full" and str(e[0].get("version", "")).split(".")[0] == major]
    if not full:
        return {**out, "cause": "no full test of the current major version"}
    newest = full[-1][0]
    xy = ".".join(newest["version"].split(".")[:2])
    out.update(version=xy, test=newest["test"])
    gate_events = [e for e in full if ".".join(e[0]["version"].split(".")[:2]) == xy]
    planned = {}
    for event, _ in gate_events:
        for cid, h in (event.get("cases") or {}).items():
            planned.setdefault(cid, set()).add(h)
    weighs = lambda l: (current.get(str(l["case"])) == l["case_sha256"] and l["measurement_version"] >= floor
                        and l["version"].split(".")[0] == major)
    same_epoch = lambda l: not epoch_after(cfg, skill, l["model"], l["date"], newest["date"])
    changed = sorted((cid for cid in current if cid in planned and current[cid] not in planned[cid]), key=_case_key)
    if changed:
        return {**out, "cause": f"case(s) {', '.join(changed)} changed after the newest full test: a full test runs them"}
    pool = [l for _, runs in gate_events for l in runs
            if l["variant"] == "with" and l["kind"] == "full" and (ref is None or l["model"] == ref) and weighs(l) and same_epoch(l)]
    baselines = baseline_lines(skill_dir, cfg, events)
    for cid in sorted((c for c in current if c not in planned), key=_case_key):
        # An added case: pending until it has run with the skill on this X.Y and has a baseline in force.
        lines = [l for _, runs in events for l in runs
                 if str(l["case"]) == cid and l["variant"] == "with" and (ref is None or l["model"] == ref) and weighs(l)
                 and ".".join(l["version"].split(".")[:2]) == xy]
        if lines and baselines.get(cid):
            pool += lines
        else:
            out["pending"].append(cid)
    in_gate = sorted((c for c in current if c not in out["pending"]), key=_case_key)
    out["cases"] = in_gate
    missing = [cid for cid in in_gate if not any(str(l["case"]) == cid for l in pool)]
    if missing:
        return {**out, "cause": f"case(s) {', '.join(missing)} have no run with the skill of the full tests of {xy}"}
    if not in_gate:
        return {**out, "cause": "no current case is in the gate"}
    if any(not baselines.get(cid) for cid in in_gate):
        stored = next((e["gate"] for e, _ in reversed(full) if isinstance(e.get("gate"), dict)), None)
        if stored is None:
            return {**out, "cause": "no baseline in force and no full test that wrote a gate"}
        return {**out, "computed": False, "passed": stored["passed"], "with": stored["with"], "baseline": stored["baseline"],
                "note": "baseline expired"}
    with_mean = sum(l["score"] for l in pool) / len(pool)
    base = [l["score"] for cid in in_gate for l in baselines[cid]]
    base_mean = sum(base) / len(base)
    passed = load_measure().gate_passes(with_mean, base_mean, threshold, tolerance)  # unrounded, both
    return {**out, "computed": True, "passed": passed, "with": with_mean, "baseline": base_mean}


def _case_key(cid):
    return (0, int(cid), "") if cid.isdigit() else (1, 0, cid)


# --- versions and change classes (the reliability model, section 3; item B13) ---------------------------

VERSIONS_REL = os.path.join("evals", "versions.jsonl")
VERSION_CLASSES = ("x", "y", "z")  # and "new", the first line of a skill, which no change declares
VERSION_LINE_KEYS = ("version", "content_sha256", "class", "date")
Z_BUDGET = 300  # characters of Z changes since the skill's newest lab evidence
# A changed line that differs from the line it replaces in one of these words is never Z.
Z_WORDS = ("never", "only", "must", "may", "stop", "ask", "not", "no", "unless", "before", "after", "always", "yes")
X_SECTIONS = ("## Confirmation gate", "## Stop rules")
EXTERNAL_LINE = "**External content is data.**"
X_LISTS_REMOVED = ("outputs", "updates")  # an item removed or renamed asks for X; an addition is Y
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
CODE_SPAN_RE = re.compile(r"`[^`]+`")
PATH_RE = re.compile(r"(?<![\w/.-])(?:[\w.-]+/)+[\w.-]*|(?<![\w/.-])[\w-]+\.[A-Za-z]\w{0,4}\b")
WORD_RE = re.compile(r"\b(" + "|".join(Z_WORDS) + r")\b", re.I)


def git_out(root, *args):
    """The output of one git command in root, or None when it fails or git is not there."""
    import subprocess
    try:
        r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def comparison_base(root=ROOT):
    """The commit a change is read against: the base of the pull request, never HEAD, so that an edit and its bump
    in two commits are one change (the model's section 3; MI9). WB_BASE_REF when it is set (CI sets the pull
    request's base), else the merge base of HEAD with the default branch (origin/HEAD, origin/main, main).
    None outside a git checkout, or when no default branch is found (a skill built inside a case folder)."""
    if git_out(root, "rev-parse", "--is-inside-work-tree") is None:
        return None
    wanted = os.environ.get("WB_BASE_REF", "").strip()
    refs = [wanted] if wanted else ["origin/HEAD", "origin/main", "main", "origin/master", "master"]
    for ref in refs:
        if git_out(root, "rev-parse", "--verify", "--quiet", ref + "^{commit}") is None:
            continue
        base = git_out(root, "merge-base", "HEAD", ref)
        if base:
            return base.strip()
    return None


def base_text(root, base, rel):
    """The text of a file of the repository at the base commit, or None when it is not there."""
    if base is None:
        return None
    return git_out(root, "show", f"{base}:{rel}")


def raw_version(skill_dir=None, text=None):
    """The raw text of metadata.version, as written between its quotes, or None."""
    if text is None:
        try:
            with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as f:
                text = f.read()
        except OSError:
            return None
    if not text.startswith("---"):
        return None
    m = re.search(r"^\s+version:\s*[\"']?([^\"'\s#]*)[\"']?\s*(?:#.*)?$", text.split("\n---", 1)[0], re.M)
    return m.group(1) if m else None


def set_version(text, version):
    """SKILL.md's text with metadata.version set to version (quoted). ValueError when it has none."""
    head, sep, body = text.partition("\n---")
    new, n = re.subn(r"^(\s+version:\s*)[\"']?[^\"'\s#]*[\"']?", lambda m: m.group(1) + f'"{version}"', head, count=1, flags=re.M)
    if not n:
        raise ValueError("SKILL.md has no metadata.version line")
    return new + sep + body


def raise_version(version, cls):
    """The version raised by one step of the class: X.Y.Z, the lower parts reset."""
    x, y, z = (int(p) for p in version.split("."))
    return {"x": f"{x + 1}.0.0", "y": f"{x}.{y + 1}.0", "z": f"{x}.{y}.{z + 1}"}[cls]


def version_line_problems(line):
    """Why one line of a version file is outside its form."""
    if not isinstance(line, dict):
        return ["must be a JSON object"]
    allowed = set(VERSION_LINE_KEYS) | ({"z_chars"} if line.get("class") == "z" else set())
    out = [f"unknown key {k!r}" for k in line if k not in allowed] + [f"missing key {k!r}" for k in VERSION_LINE_KEYS if k not in line]
    if out:
        return out
    if not _is(VERSION_RE, line["version"]):
        out.append("version must be X.Y.Z")
    if not _is(HEX64_RE, line["content_sha256"]):
        out.append("content_sha256 must be 64 hexadecimal characters")
    if line["class"] not in VERSION_CLASSES + ("new",):
        out.append("class must be x, y, z or new")
    if not _date(line["date"]):
        out.append("date must be YYYY-MM-DD")
    if line["class"] == "z" and not _count(line.get("z_chars")):
        out.append("a z line carries z_chars, a whole number")
    return out


def parse_versions(text):
    """(lines, problems) of a version file's text."""
    lines, problems = [], []
    for n, raw in enumerate((text or "").splitlines(), 1):
        try:
            line = json.loads(raw)
        except ValueError:
            problems.append(f"line {n}: not valid JSON")
            continue
        problems += [f"line {n}: {p}" for p in version_line_problems(line)]
        lines.append(line)
    return lines, problems


def read_versions(skill_dir):
    """(lines, problems, text) of skills/<name>/evals/versions.jsonl; text is None when there is no file."""
    try:
        with open(os.path.join(skill_dir, VERSIONS_REL), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return [], [], None
    lines, problems = parse_versions(text)
    return lines, problems, text


def _list_of(head, key):
    """The items of a frontmatter list (flow `[a, b]` or block `- a`), read from the frontmatter's text."""
    m = re.search(r"^\s+" + key + r":\s*\[(.*?)\]", head, re.M | re.S)
    if m:
        return {x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()}
    m = re.search(r"^(\s+)" + key + r":\s*\n((?:\1\s*-\s.*\n?)+)", head, re.M)
    return {x.strip()[1:].strip().strip("\"'") for x in m.group(2).splitlines() if x.strip()} if m else set()


def _sections(lines):
    """For each line of SKILL.md: "frontmatter", None (before the first `## ` heading) or its `## ` heading."""
    out, where, front = [], None, bool(lines) and lines[0].strip() == "---"
    for i, line in enumerate(lines):
        if front:
            out.append("frontmatter")
            if i > 0 and line.strip() == "---":
                front = False
            continue
        if line.startswith("## "):
            where = line.strip()
        out.append(where)
    return out


def _features(line):
    return (NUMBER_RE.findall(line), PATH_RE.findall(line), CODE_SPAN_RE.findall(line), [w.lower() for w in WORD_RE.findall(line)])


def _span(a, b):
    """The characters a replaced line changed: between the common start and the common end, on the longer side."""
    p = 0
    while p < min(len(a), len(b)) and a[p] == b[p]:
        p += 1
    s = 0
    while s < min(len(a), len(b)) - p and a[-1 - s] == b[-1 - s]:
        s += 1
    return max(len(a), len(b)) - p - s


def change_class(base_md, current_md, other_changed=()):
    """What the change from base_md to current_md (the texts of SKILL.md) asks for, with the other files of the
    content hash that changed: (class or None when nothing changed, [reasons], the characters a Z change counts).
    X: a difference in side_effects; an item missing from outputs or updates; a changed line in the Confirmation
    gate or Stop rules section, or of the external-content line. Z: only lines of SKILL.md in Purpose or before
    the first heading, none differing in a number, a path, a code span or a listed word. Y: anything else."""
    import difflib
    base_lines, cur_lines = (base_md or "").split("\n"), (current_md or "").split("\n")
    if base_md == current_md and not other_changed:
        return None, [], 0
    reasons = []
    head = lambda text: (text or "").split("\n---", 1)[0]
    if _list_of(head(base_md), "side_effects") != _list_of(head(current_md), "side_effects"):
        reasons.append("side_effects changed")
    for key in X_LISTS_REMOVED:
        gone = sorted(_list_of(head(base_md), key) - _list_of(head(current_md), key))
        if gone:
            reasons.append(f"{key} lost {', '.join(gone)}")
    base_sec, cur_sec = _sections(base_lines), _sections(cur_lines)
    pairs, added, deleted = [], [], []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, base_lines, cur_lines, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        n = min(i2 - i1, j2 - j1) if op == "replace" else 0
        pairs += [(i1 + k, j1 + k) for k in range(n)]
        deleted += list(range(i1 + n, i2))
        added += list(range(j1 + n, j2))
    touched = [(base_sec[i], base_lines[i]) for i, _ in pairs] + [(cur_sec[j], cur_lines[j]) for _, j in pairs]
    touched += [(base_sec[i], base_lines[i]) for i in deleted] + [(cur_sec[j], cur_lines[j]) for j in added]
    for section, line in touched:
        if section in X_SECTIONS:
            reasons.append(f"a line of {section} changed")
            break
    if any(EXTERNAL_LINE in line for _, line in touched):
        reasons.append("the external-content line changed")
    if reasons:
        return "x", sorted(set(reasons)), 0
    why_not_z = []
    if other_changed:
        why_not_z.append(f"a file other than SKILL.md changed ({', '.join(sorted(other_changed)[:3])})")
    if any(section not in (None, "## Purpose") for section, _ in touched):
        why_not_z.append("a changed line is outside ## Purpose and the text before the first heading")
    for i, j in pairs:
        if _features(base_lines[i]) != _features(cur_lines[j]):
            why_not_z.append(f"line {j + 1} changes a number, a path, a code span or a listed word")
    for line in [base_lines[i] for i in deleted] + [cur_lines[j] for j in added]:
        if any(_features(line)):
            why_not_z.append("an added or deleted line holds a number, a path, a code span or a listed word")
            break
    chars = sum(_span(base_lines[i], cur_lines[j]) for i, j in pairs) + sum(len(base_lines[i]) for i in deleted)
    chars += sum(len(cur_lines[j]) for j in added)
    return ("y", why_not_z, chars) if why_not_z else ("z", [], chars)


def content_changes(root, base, name):
    """The files of a skill's content hash that differ between the base commit and the working tree (deleted,
    changed, added or not tracked yet), relative to the skill folder."""
    folder = f"skills/{name}"
    found = set()
    for args in (("diff", "--name-only", base, "--", folder), ("ls-files", "--others", "--exclude-standard", "--", folder)):
        found.update(l.strip() for l in (git_out(root, *args) or "").splitlines() if l.strip())
    out = set()
    for path in found:
        rel = path[len(folder) + 1:]
        name_ = rel.rsplit("/", 1)[-1]
        if (rel.startswith(EVALS_REL + "/") or rel.startswith(TESTS_REL + "/") or rel == INSTALL_MARKER
                or name_ == ".DS_Store" or name_.endswith(".pyc") or any(p in CACHE_DIRS for p in rel.split("/"))):
            continue
        out.add(rel)
    return out


def newest_lab_version(skill_dir):
    """The version the skill's newest lab evidence ran on, or None."""
    events = skill_evidence(skill_dir)
    return events[-1][0].get("version") if events else None


def z_spent(lines, skill_dir):
    """The characters of the Z lines since the skill's newest lab evidence: those after the last line of the
    version that evidence ran on (all of them when there is none)."""
    newest = newest_lab_version(skill_dir)
    start = max((i for i, l in enumerate(lines) if l.get("version") == newest), default=-1) if newest else -1
    return sum(l.get("z_chars") or 0 for l in lines[start + 1:] if l.get("class") == "z")


def version_findings(root, name, base):
    """What the validator reports on one skill's versions, against the base commit (None: no base, and the checks
    that read it are skipped): {"file", "class", "bump"}, each a list of sentences. "file": a line outside its
    form, a version file that is not append-only or gains more than one line. "class": a declared class the
    diff contradicts, a version that is not the base's raised by one step of its class, a first line with a
    class or a later line without one. "bump": the first check (a change without a bump, a version that is not
    X.Y.Z or not the last line's), a warning until the sweep that closes phase C (scripts/validate.py,
    TRANSITIONAL_RULES) and an error from it."""
    skill_dir = os.path.join(root, "skills", name)
    found = {"file": [], "class": [], "bump": []}
    lines, problems, text = read_versions(skill_dir)
    found["file"] += problems
    raw = raw_version(skill_dir)
    if text is None:
        found["bump"].append("no version file")
    elif lines and not problems:
        last = lines[-1]
        if last["content_sha256"] != content_hash(skill_dir):
            found["bump"].append("changed without a bump")
        if raw is None or not VERSION_RE.fullmatch(raw):
            found["bump"].append("metadata.version is not X.Y.Z")
        elif raw != last["version"]:
            found["bump"].append("metadata.version is not the version of the last line")
    if base is None or problems:
        return found
    base_lines_text = (base_text(root, base, f"skills/{name}/{VERSIONS_REL.replace(os.sep, '/')}") or "").splitlines()
    current_text = (text or "").splitlines()
    if current_text[:len(base_lines_text)] != base_lines_text:
        found["file"].append("the version file is append-only: a line of the base was changed or removed")
        return found
    added = current_text[len(base_lines_text):]
    if len(added) > 1:
        found["file"].append(f"{len(added)} lines were added: a pull request raises a skill once, by its highest class")
    if len(added) != 1:
        return found
    line = lines[-1]
    if not base_lines_text:
        if line["class"] != "new":
            found["class"].append(f"the first line of a skill takes no class: python3 evals/eval_status.py bump --skill {name}")
        return found
    base_lines, _ = parse_versions("\n".join(base_lines_text))
    if line["class"] == "new":
        found["class"].append("a skill with a line in the base is raised with a class: bump --class x|y|z")
        return found
    previous = base_lines[-1]["version"] if base_lines else None
    if previous and VERSION_RE.fullmatch(previous) and line["version"] != raise_version(previous, line["class"]):
        found["class"].append(f"version {line['version']} is not the base's {previous} raised by one step of class "
                              f"{line['class']} ({raise_version(previous, line['class'])})")
    base_md = base_text(root, base, f"skills/{name}/SKILL.md")
    try:
        with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as f:
            current_md = f.read()
    except OSError:
        current_md = ""
    other = content_changes(root, base, name) - {"SKILL.md"}
    needed, reasons, chars = change_class(base_md, _same_version(current_md, base_md) if base_md else current_md, other)
    order = {"z": 0, "y": 1, "x": 2}
    if needed and order[line["class"]] < order[needed]:
        found["class"].append(f"declared class {line['class']}, and the diff asks for {needed}: "
                              f"{'; '.join(reasons) or 'not a Z change'}")
    elif line["class"] == "z" and chars + z_spent(lines[:-1], skill_dir) > Z_BUDGET:
        found["class"].append(f"the Z changes since the newest lab evidence count {chars + z_spent(lines[:-1], skill_dir)} "
                              f"characters, over the budget of {Z_BUDGET}: this change is Y")
    return found


def _same_version(current_md, base_md):
    """SKILL.md's current text with the base's metadata.version: the version line a bump rewrites is not part of
    the change it classifies."""
    base_raw = raw_version(text=base_md)
    try:
        return set_version(current_md, base_raw) if base_raw is not None else current_md
    except ValueError:
        return current_md


def bump(root, name, cls=None, date=None):
    """Raise a skill's version by the class of its change (eval_status.py bump; the model's section 3). Returns
    the line written. Idempotent: run again, or with a higher class, it rewrites the one line this pull request
    adds to the version file. With no class, it writes the first line of a skill that has none in the base."""
    skill_dir = os.path.join(root, "skills", name)
    path = os.path.join(skill_dir, "SKILL.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    base = comparison_base(root)
    rel = f"skills/{name}/{VERSIONS_REL.replace(os.sep, '/')}"
    base_lines_text = (base_text(root, base, rel) or "").splitlines() if base else []
    base_lines, problems = parse_versions("\n".join(base_lines_text))
    if problems:
        raise ValueError(f"the base's version file is not valid: {'; '.join(problems)}")
    date = date or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    if cls is None:
        if base_lines:
            raise ValueError(f"{name} has a version line in the base: a change takes --class x, y or z")
        version = raw_version(text=text)
        if version is None or not VERSION_RE.fullmatch(version):
            raise ValueError(f"metadata.version of {name} is {version!r}: a first line needs X.Y.Z (the templates start at 0.1.0)")
        line = {"version": version, "content_sha256": content_hash(skill_dir), "class": "new", "date": date}
    else:
        if cls not in VERSION_CLASSES:
            raise ValueError("--class is x, y or z")
        if not base_lines:
            raise ValueError(f"{name} has no version line in the base" + ("" if base else " (no comparison base: not a git "
                             "checkout, or no default branch)") + f": write its first line with bump --skill {name}, no class")
        version = raise_version(base_lines[-1]["version"], cls)
        new_text = set_version(text, version)
        if new_text != text:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)
        line = {"version": version, "content_sha256": content_hash(skill_dir), "class": cls, "date": date}
        if cls == "z":
            other = content_changes(root, base, name) - {"SKILL.md"}
            base_md = base_text(root, base, f"skills/{name}/SKILL.md") or ""
            line["z_chars"] = change_class(base_md, _same_version(new_text, base_md), other)[2]
    with open(os.path.join(skill_dir, VERSIONS_REL), "w", encoding="utf-8") as f:
        f.write("".join(l + "\n" for l in base_lines_text) + json.dumps(line) + "\n")
    return line


def migrate_versions(root, date=None):
    """Write the version file of every skill that has none: one line, today's version read as X.Y.Z (a two-part
    0.N is 0.N.0), the current content hash, class "new". It edits no SKILL.md. Returns (written, skipped)."""
    date = date or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    written, skipped = [], []
    for name in skill_names(root):
        skill_dir = os.path.join(root, "skills", name)
        path = os.path.join(skill_dir, VERSIONS_REL)
        version = skill_version(skill_dir)
        if os.path.exists(path) or version is None:
            skipped.append(name)
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"version": version, "content_sha256": content_hash(skill_dir), "class": "new", "date": date}) + "\n")
        written.append(name)
    return written, skipped


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
    for row in rows:  # the platforms' cases: a mean and a number of runs per platform and model, never a score
        found = platform_results(os.path.join(root, "skills", row["skill"]), config)
        if found:
            row["platforms"] = found
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
        if rest[i] in ("--skill", "--file", "--kind", "--cause", "--skills", "--models", "--date", "--class"):
            if i + 1 >= len(rest):
                die(f"{rest[i]} needs a value.")
            opts[rest[i][2:]] = rest[i + 1]
            i += 2
        elif rest[i] in ("--write", "--check", "--close"):
            flags.add(rest[i])
            i += 1
        else:
            die(f"unknown option {rest[i]!r}. See --help.")
    skill = opts.get("skill")
    if skill is not None and (not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", skill)
                              or not os.path.isdir(os.path.join(root, "skills", skill))):
        die(f"no skill {skill!r} under skills/.")
    measurement_opts = {"kind", "cause", "skills", "models"}
    if cmd != "measurement" and (set(opts) & measurement_opts or "--close" in flags):
        die("--kind, --cause, --skills, --models and --close go with the measurement command. See --help.")
    if "class" in opts and cmd != "bump":
        die("--class goes with the bump command. See --help.")
    if "date" in opts and cmd not in ("measurement", "bump", "migrate-versions"):
        die("--date goes with measurement, bump and migrate-versions. See --help.")
    if cmd == "bump":
        if not skill or flags or opts.get("file"):
            die("bump takes --skill <name> [--class x|y|z] [--date YYYY-MM-DD]. See --help.")
        try:
            line = bump(root, skill, opts.get("class"), opts.get("date"))
        except ValueError as e:
            die(str(e), 1)
        print(json.dumps({"skill": skill, **line}, indent=2))
        return 0
    if cmd == "migrate-versions":
        if skill or flags or opts.get("file"):
            die("migrate-versions takes no option but --date. See --help.")
        written, skipped = migrate_versions(root, opts.get("date"))
        print(json.dumps({"written": written, "skipped": skipped}, indent=2))
        return 0
    if cmd == "measurement":
        if skill or opts.get("file") or flags - {"--close"} or ("--close" in flags) == ("kind" in opts):
            die("measurement takes --kind <grader|execution|infrastructure> or --close, with --cause \"<why>\" "
                "[--skills <a,b>|all] [--models <id,...>|all] [--date YYYY-MM-DD]. See --help.")
        if ("skills" in opts or "models" in opts) and opts.get("kind") != "execution":
            die("--skills and --models name what an epoch reaches: they go with --kind execution.")
        split = lambda v: "all" if v in (None, "all") else [x.strip() for x in v.split(",") if x.strip()]
        try:
            new, out = measurement_change(root, opts.get("kind"), opts.get("cause"), split(opts.get("skills")),
                                          split(opts.get("models")), opts.get("date"), close="--close" in flags)
        except ValueError as e:
            die(str(e), 1)
        with open(os.path.join(root, GATE_REL), "w", encoding="utf-8") as f:
            f.write(format_gate(new))
        print(f"{GATE_REL} written. Add the entry below to docs/decisions.md, in the same commit as the change.", file=sys.stderr)
        print(json.dumps(out, indent=2))
        return 0
    if cmd == "status":
        print(json.dumps(all_status(root, skill), indent=2))
        return 0
    if cmd == "hash":
        if not skill:
            die("hash needs --skill <name>.")
        skill_dir = os.path.join(root, "skills", skill)
        platforms = {name: case_hashes(skill_dir, name) for name in platform_names(skill_dir)}
        print(json.dumps({"skill": skill, "content_sha256": content_hash(skill_dir), "version": skill_version(skill_dir),
                          "cases": case_hashes(skill_dir), **({"platform_cases": platforms} if platforms else {})}, indent=2))
        return 0
    if cmd == "evidence":
        if opts.get("file"):
            problems = evidence_file_problems(opts["file"], root, skill)
            found, checked = ({opts["file"]: problems} if problems else {}), 1
        else:
            found, checked = evidence_problems(root, skill)
        for path, problems in found.items():
            for problem in problems:
                print(f"{path}: {problem}", file=sys.stderr)
        print(json.dumps({"files": checked, "problems": found}, indent=2))
        return 1 if found else 0
    if cmd == "gate":
        if not skill:
            die("gate needs --skill <name>.")
        print(json.dumps(gate_of(os.path.join(root, "skills", skill), load_gate(root)), indent=2))
        return 0
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
