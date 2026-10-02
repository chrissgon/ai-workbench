#!/usr/bin/env python3
"""Run a skill's evals with and without the skill, on a strong and a floor model, and grade them.

Usage:
  python3 eval_run.py --skill <name>
                      [--harness <adapter>] [--model <strong-id>] [--floor-model <id>] [--floor-harness <adapter>]
                      [--grader <id>] [--case <id>]... [--threshold 0.8] [--record-anyway]
                      [--allow-contaminated] [--only without --update-record]
                      [--only with|without|ablated] [--tiers strong,floor] [--pass-env <VAR>]... [--floor-pass-env <VAR>]... [--ablate <text>]
                      [--runs 3] [--jobs 4] [--timeout 900] [--max-cost-usd <amount>] [--no-grade] [--no-record]
                      [--retries 2] [--early-end-rate 0.15]
                      [--dry-run] [--check-cases]

Defaults. --harness, --model, --floor-model, --floor-harness, --floor-pass-env and --threshold default to the
eval gate configuration, evals/eval-gate.json (strong_harness, strong_model, floor_model, floor_harness,
floor_pass_env, threshold), so `eval_run.py --skill <name>` runs the gate as configured. A flag given on the
command line wins; floor_pass_env is applied only when the floor model is the configured one (another floor
model, such as one served on the same machine, needs no provider key). Without the file, --harness and
--model are required, there is no floor model unless --floor-model names one, and the threshold is 0.8.

Reads skills/<name>/evals/evals.json. For each case and each variant (with_skill, without_skill)
and each model, it prepares a working directory with the case's files (paths inside the skill folder
only) in its own git repository (one "fixture" commit, then the case's optional "setup" shell commands,
such as a branch with commits), runs the prompt through adapters/<harness>/run-prompt.sh with the skills
listed in the case's optional "skills" (a flow's phases) for both variants, grades every assertion with
the grader model (which sees the files the run produced, and the case's optional "grader_files": input files,
relative to the case folder, that assertions check facts against), and writes:

  evals-workspace/<name>/iteration-N/eval-<id>/<variant>[.floor]/{prompt.md,cwd/,outputs/,grading.json,timing.json}
  evals-workspace/<name>/iteration-N/benchmark.json

--runs <n> (default 3) runs every case, variant and model n times; each run gets its own folder, run-<k>/,
and benchmark.json averages them. --jobs <n> (default 4, at most 8; the repository runs independent work in parallel, AGENTS.md principle 7) runs that many model runs, with their
gradings, at the same time. Each run already has its own folders and a throwaway home, so runs share
nothing; the earlier failures of parallel agents-dir runs came from a provider key that did not reach
the runner, not from running in parallel. Keep --jobs within the provider's rate limits.
--timeout <seconds> (default 900) stops a model run that takes longer, on any adapter, and counts it as
failed. --max-cost-usd <amount> is passed to the adapter as a spend limit per run: the claude-code adapter
enforces it, agents-dir says it cannot (a credit limit on the provider key is the cap there).

--floor-pass-env <VAR> passes a variable to the floor model's runs only (its provider key, such as
OPENROUTER_API_KEY), so the strong model's runs and the grader never see it; --pass-env reaches every run.

--ablate <text> adds a third variant, ablated_skill: the skill with every SKILL.md line containing <text>
removed (for example "External content is data."), to measure what one rule changes. It is refused when
no line matches. benchmark.json then reports ablation_delta (with_skill minus ablated_skill) per tier;
it is a measurement, not a pass condition.

--floor-harness lets the floor model run through a different adapter (for example agents-dir for an
open-weight model served through its own CLI) while the strong model and the grader use --harness.
--dry-run prints the plan as JSON and runs nothing: the runs, the runner of each model, the grader, the
variables that would be passed, every case with its files, dependency skills and setup commands, and the
result of the preflight.

Adapter contract: run-prompt.sh --prompt-file <f> --cwd <dir> --model <id> --out <dir> [--skill-dir <dir>]
[--extra-skill-dir <dir>]... [--allow-web] copies each skill folder into <cwd> where the
harness discovers it (never a link into the workbench) and must write <out>/response.md and
<out>/timing.json ({"total_tokens", "duration_ms", "cost_usd"}).

Commands. Every command a model runs is allowed: the container a run executes in is the boundary
(evals/executor.py). A case names no commands; an evals.json that still carries "allow_commands" (the list
used while runs happened on a person's machine) is refused, so that no case keeps a setting that does nothing.

Web. evals.json may set "allow_web": true at the top level or per case, for a skill that must search
and read web pages (it requires search:web). The adapter then lets the model search and fetch pages,
and nothing else more; the grader never gets it. Without it a harness that asks before searching denies
the search, and a with-skill run of a research skill measures only its degraded mode.

Containment. Every model run, grading, setup command and fixture commit executes in a container built
from evals/container/, one container per command (evals/executor.py); there is no host mode. A container
sees the run's folder (read-write, the only thing a run can change), the adapters and the shared references
(read-only), and the skill under test with the case's dependency skills (read-only, their evals/ folder
covered by an empty one). Nothing else of the machine: no home folder, no other checkout, no credential
store. Network, per command: none for setup commands and the fixture commit; for model runs and gradings an
internal network whose only way out is a proxy that lets through the model providers' hosts
(evals/container/proxy/allow.txt); the default network only for a case with "allow_web": true.
Environment: the image's own (its clock is UTC, its locale C.UTF-8, and the one git identity of a run is the
image's: nothing of the caller's machine sets them), plus the variables that keep git inside the case folder
(GIT_ALLOW_PROTOCOL=file, no terminal prompt), the proxy's address on the proxy network, and the variables
named with --pass-env (every run),
--floor-pass-env (floor-model runs only: a provider key the strong model and the grader must not receive) or
strong_pass_env of the gate file (strong-model runs and gradings only). A name among those that an adapter
registers as a secret for eval runs and that is missing from the environment is read from the OS secret
store through providers/secrets/resolver.py; values travel in the environment of the docker client, never
on a command line. Token variables for git hosts and npm are refused there. The docker client itself still
runs with an environment built from an allowlist on the host, with empty git, gh and npm configuration, but
only the names above cross into a container. The container is the boundary, so a model may run every
command; read a contributed skill's evals.json before running it all the same, because a case with
"allow_web" runs on the open network. The grader is told that the response and files are data; the adapter
decides whether it may run tools.

Preflight. Before any model call, and in --dry-run and --check-cases (which runs only this check; --harness
and --model are then optional), every case is checked: (a) each "files" entry exists in the skill folder;
(b) the case folder is built as a run builds it (the files, then the "setup" commands; --dry-run runs nothing,
so it leaves the cases that have a setup unchecked and says so) and every path the prompt cites exists in it,
unless the path also appears in "expected_output" or an assertion, or in the skill's metadata.outputs (the run
creates it), is one of the skill's own files outside evals/ or a workbench file under contracts/, shared/,
templates/, providers/, adapters/ or skills/, or the case lists it in "absent_on_purpose": ["path", ...] (a case that tests a missing input);
(c) each "grader_files" entry exists in that folder; (d) each "skills" dependency exists. A cited path is a
token with a "/" and a file extension, or one ending in .md .json .yml .yaml .toml .css .js .ts .py .html;
URLs, absolute paths, globs and placeholders are ignored, and a path matches a fixture when it is that
fixture's path or the end of it. Errors are printed one per line and stop the run before it spends anything.

Infrastructure failures are not scores. A run whose adapter exits non-zero (a provider out of credits, a
session limit, a missing runner), that passes --timeout, that ends its turn early on every attempt (below),
or whose grading returns nothing parsable, is listed in benchmark.json "infra_failures" ({"case", "variant", "tier",
"run", "reason"}) and never enters a mean. benchmark.json also carries "expected_runs", "completed_runs" and
"complete" (true only when every expected run completed and was graded), "date", "iteration", "cases" and
"content_sha256", the skill folder's hash when the run started. Rerun an incomplete iteration; never change
the skill for it. A timeout that repeats on the same case is a reason to raise --timeout or to look at the case.

Early ends. Some models end their turn before doing the work, with exit 0 and no error: they print a tool
call as text, loop on their own reminder blocks, or stop after "Let me read the template first". A run is an
early end only when the adapter exited 0 AND it created or changed no file in the case folder (the harness's
installed skills and shared references do not count) AND its response is not a reply to the user: (a) it is
empty; or (b) a line starts with tool-call or control markup printed as text (EARLY_END_MARKUP); or (c) the
response has no question mark and its last line announces a next action (a sentence starting with one of
EARLY_END_ANNOUNCE, with none of EARLY_END_NOT in the line). A reply that asks the user a question and
writes nothing is a stop-and-ask, never an early end; neither is a run that wrote a file and then stopped
before finishing: that one is graded as it is. An early-ended run is rerun in a fresh folder up to
--retries <n> times (default 2, 0 disables; each early attempt is kept in <run folder>/early-end-<j>/, the
last attempt stays in the run folder). One that early-ends on every attempt is an infrastructure failure
with reason "early_end". benchmark.json "early_ends" counts, per model tier, {"attempts", "early_ends",
"rate", "by_case"}; "early_end_warning" is a sentence, printed at the end, when a tier has at least 3 early
ends and either a rate above --early-end-rate (default 0.15) or all of them on one case: retries hid them
from the scores, so read the transcripts and decide between the skill, the case and the provider. The
warning never changes the exit code.

Record. After a complete run of every case, both variants and both models, without --case, --only, --tiers
that drops a model, --ablate or --no-grade, the result is written to skills/<name>/evals/result.json through
evals/eval_status.py (the same function as its `record` command) with the hash taken at the start, and the
skill's status (draft, evaluated, stale) is printed. A partial or incomplete run never writes it; a skill
folder that changed during the run is reported and not recorded. --no-record skips the record. A full run
whose floor model is not the configured one runs and is reported, but writes no record (it would read as
stale: evaluated on another floor model) unless --record-anyway is given.
No evidence while the measurement is open. While evals/eval-gate.json carries no "measurement_sha256" (the
fingerprint that closes a measurement version), and when the image was built for another CPU platform than
the one evidence is made on (evals/executor.py), runs execute and benchmark.json is written, but no record
is written or updated, whatever the options: the reason is printed.
--only without --update-record, when its run is complete and not contaminated, replaces scores.strong_without
and scores.floor_without of the existing record, recomputes its gate and adds "baseline": {"date", "iteration",
"runs"}. It needs a valid record whose content_sha256 is the skill's current hash and whose models and
threshold are the ones of this run and of the configuration; otherwise it changes nothing and says why. When
the recomputed gate fails, the record is still written and the skill reads draft.

Outside the repository. A model that runs inside the workbench finds it: it walks up from the case folder,
reads the instruction file and the skills, and a without-skill run then scores with the skill's help. So every
model run and every grading happens in a fresh folder under the system's temporary folder, <temp>/eval-<random>/
(case/ is the case folder, with the prompt file and the adapter's output beside it): no parent of it holds a
repository, an instruction file or a skills folder, and its path names neither the workbench nor the skill
(a temporary folder that would is replaced by /tmp or /var/tmp). Setup commands run there too. When the run
ends (also on a timeout, a failure or a stop) the folders are moved to where they have always been read,
<run folder>/cwd and <run folder>/outputs (grading/cwd and grading/out for a grading), and the temporary
folder is removed. The run's environment carries no path into the repository: PATH entries inside it and
allowlisted variables that point into it are dropped, TMPDIR is the temporary base, the git, gh and npm
configuration files sit in the temporary folder, and the adapter is started from there (a shell exports the
folder it came from as OLDPWD). Only a variable named with --pass-env is passed as it is.
Repository files. A case may list "workbench_files": files and folders of this repository copied into the
case folder at the same relative path (a skill's evals/ folder is left out; version control, eval workspaces
and eval cases are refused). It is for a skill whose job is the workbench itself, which needs the real
tooling to act on; such a case deliberately shows the model part of the repository.

Refusals. When the provider declines a without-skill run on policy grounds, the run scores 0 and is listed in
benchmark.json "baseline_refusals": the model alone could not do the task, which is what a baseline says. The
same refusal of a run that has the skill is an infrastructure failure, never a score.

Contamination. After each without-skill run the response and the adapter's stderr and raw output are searched
for the repository's absolute path (which includes the path of the skill under test). A hit means the model
reached the workbench anyway (a search from the filesystem root, a harness that loads user-level
configuration): it is listed in benchmark.json "contaminated" ({"case", "variant", "tier", "run", "evidence"}),
printed as a warning, and no record is written from that iteration unless --allow-contaminated.
Baseline only. --only without --update-record measures the without-skill variant alone, on both models, and
replaces the two baseline scores of an existing record (see Record).

Stopping. Every adapter call (a model run, a grading) and every setup command runs in its own session, one
process group per call. The group is ended (TERM, then KILL after a short wait) when the call passes its
timeout, when the call returns (so a browser or a server a run left behind stops with it), when this script
gets TERM, INT or HUP (it then exits with 128 plus the signal number, without writing benchmark.json), and on
every other way out. The adapters do the same for the runner they start, which they put in a session of its
own. A process that moves itself to yet another session escapes this.

Exit codes: 0 ok; 1 the iteration is incomplete (a run or a grading failed on infrastructure: rerun);
2 usage error or a preflight error in the cases; 3 the iteration is complete and the conditions are not met
(reported, not an error of the tool).
"""
import concurrent.futures
import datetime
import glob
import importlib.util
import json
import os
import re
import secrets
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
STATUS_SCRIPT = os.path.join(HERE, "eval_status.py")
EXECUTOR_SCRIPT = os.path.join(HERE, "executor.py")  # where a run's commands execute: a container
# "container" for every real run; the unit tests set "host" to drive stand-in adapters without docker.
EXECUTOR = "container"  # content hash and the per-skill record
GRADING_TEMPLATE = os.path.join(HERE, "grading-prompt.md")
SETUP_TIMEOUT = 300  # seconds per setup command


def die(msg, code=2):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def load_executor():
    """evals/executor.py as a module."""
    name = "workbench_eval_executor"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, EXECUTOR_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def load_status():
    """evals/eval_status.py as a module: the content hash and the record are defined there, once."""
    if not os.path.isfile(STATUS_SCRIPT):
        die("evals/eval_status.py is missing: run this script from a checkout of the workbench.")
    spec = importlib.util.spec_from_file_location("workbench_eval_status", STATUS_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse(argv):
    opts = {"skill": None, "harness": None, "model": None, "floor": None, "floor_harness": None, "grader": None, "cases": [],
            "threshold": None, "strong_pass_env": [], "record_anyway": False, "allow_contaminated": False, "update_record": False, "only": None, "tiers": None, "grade": True, "dry": False, "pass_env": [], "ablate": None, "floor_pass_env": [],
            "runs": 3, "jobs": 4, "timeout": 900, "max_cost": None, "record": True, "check_cases": False, "retries": 2,
            "early_rate": 0.15}
    i = 0
    while i < len(argv):
        a = argv[i]
        def val():
            if i + 1 >= len(argv):
                die(f"{a} needs a value.")
            return argv[i + 1]
        if a == "--skill": opts["skill"] = val(); i += 2
        elif a == "--harness": opts["harness"] = val(); i += 2
        elif a == "--model": opts["model"] = val(); i += 2
        elif a == "--floor-model": opts["floor"] = val(); i += 2
        elif a == "--floor-harness": opts["floor_harness"] = val(); i += 2
        elif a == "--grader": opts["grader"] = val(); i += 2
        elif a == "--case": opts["cases"].append(val()); i += 2
        elif a == "--threshold": opts["threshold"] = float(val()); i += 2
        elif a == "--only": opts["only"] = val(); i += 2
        elif a == "--tiers": opts["tiers"] = {t.strip() for t in val().split(",")}; i += 2
        elif a == "--pass-env": opts["pass_env"].append(val()); i += 2
        elif a == "--ablate": opts["ablate"] = val(); i += 2
        elif a == "--floor-pass-env": opts["floor_pass_env"].append(val()); i += 2
        elif a == "--runs": opts["runs"] = val(); i += 2
        elif a == "--jobs": opts["jobs"] = val(); i += 2
        elif a == "--timeout": opts["timeout"] = val(); i += 2
        elif a == "--max-cost-usd": opts["max_cost"] = val(); i += 2
        elif a == "--no-grade": opts["grade"] = False; i += 1
        elif a == "--no-record": opts["record"] = False; i += 1
        elif a == "--record-anyway": opts["record_anyway"] = True; i += 1
        elif a == "--allow-contaminated": opts["allow_contaminated"] = True; i += 1
        elif a == "--update-record": opts["update_record"] = True; i += 1
        elif a == "--retries": opts["retries"] = val(); i += 2
        elif a == "--early-end-rate": opts["early_rate"] = val(); i += 2
        elif a == "--dry-run": opts["dry"] = True; i += 1
        elif a == "--check-cases": opts["check_cases"] = True; i += 1
        elif a in ("--help", "-h"): print(__doc__); sys.exit(0)
        else: die(f"unknown option {a!r}. See --help.")
    # What the command line leaves out comes from the eval gate configuration (evals/eval-gate.json).
    gate = {} if opts["check_cases"] else load_status().load_gate(ROOT)
    opts["configured_floor"] = gate.get("floor_model")
    for key, field in (("harness", "strong_harness"), ("model", "strong_model"), ("floor", "floor_model"),
                       ("threshold", "threshold")):
        if opts[key] is None:
            opts[key] = gate.get(field)
    if opts["threshold"] is None:
        opts["threshold"] = 0.8
    opts["grader"] = opts["grader"] or gate.get("grader")
    opts["tolerance"], opts["measurement_version"] = gate.get("strong_tolerance") or 0, gate.get("measurement_version")
    if opts["floor"] and not opts["floor_harness"]:
        opts["floor_harness"] = gate.get("floor_harness")
    if opts["floor"] and opts["floor"] == gate.get("floor_model") and not opts["floor_pass_env"]:
        opts["floor_pass_env"] = list(gate.get("floor_pass_env") or [])
    # The strong runner's credential in a container (there is no login or keychain there): strong runs and gradings.
    opts["strong_pass_env"] = list(gate.get("strong_pass_env") or []) if opts["model"] == gate.get("strong_model") else []
    for k in ("skill",) if opts["check_cases"] else ("skill", "harness", "model"):
        if not opts[k]:
            die(f"--{k} is required" + (" (evals/eval-gate.json sets no default)." if k != "skill" else "."))
    if opts["only"] not in (None, "with", "without", "ablated"):
        die("--only must be with, without or ablated.")
    if opts["update_record"] and (opts["only"] != "without" or opts["cases"] or opts["tiers"] or opts["ablate"]
                                  or not opts["grade"] or not opts["record"]):
        die("--update-record goes with --only without, on every case and both models, graded: "
            "eval_run.py --skill <name> --only without --update-record.")
    if opts["only"] == "ablated" and not opts["ablate"]:
        die("--only ablated needs --ablate <text>.")
    if opts["ablate"] is not None and not opts["ablate"].strip():
        die("--ablate needs a non-empty text.")
    try:
        opts["runs"], opts["timeout"], opts["jobs"] = int(opts["runs"]), int(opts["timeout"]), int(opts["jobs"])
    except (TypeError, ValueError):
        die("--runs, --jobs and --timeout take whole numbers.")
    if not 1 <= opts["jobs"] <= 8:
        die("--jobs must be between 1 and 8.")
    if not 1 <= opts["runs"] <= 10:
        die("--runs must be between 1 and 10.")
    try:
        opts["retries"], opts["early_rate"] = int(opts["retries"]), float(opts["early_rate"])
    except (TypeError, ValueError):
        die("--retries takes a whole number and --early-end-rate a number such as 0.15.")
    if not 0 <= opts["retries"] <= 5:
        die("--retries must be between 0 and 5.")
    if not 0 <= opts["early_rate"] <= 1:
        die("--early-end-rate must be between 0 and 1.")
    if opts["timeout"] < 30:
        die("--timeout is in seconds and at least 30.")
    if opts["max_cost"] is not None and not re.fullmatch(r"\d+(\.\d+)?", opts["max_cost"]):
        die("--max-cost-usd takes a number, e.g. 0.50.")
    for name in opts["pass_env"] + opts["floor_pass_env"]:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            die(f"--pass-env {name!r} is not a variable name.")
        if name in TOKEN_VARS:
            die(f"--pass-env {name}: token variables for git hosts and npm never reach a model run.")
    opts["grader"] = opts["grader"] or opts["model"]
    return opts


def resolve_pass_env(names):
    """Fill a --pass-env variable missing from the environment from the workbench's secret resolver
    (providers/secrets/resolver.py: the OS secret store), so a key kept there reaches the runs
    without an export. The names come from the caller (the flags, and floor_pass_env and
    strong_pass_env of the gate file, their one home): each is checked against the secrets the
    adapters register in the "secrets" list of their adapter.json, and no name is taken from that
    registry. Only secrets whose registered readers include eval_run.py are filled; other names and
    values that are not found are left alone."""
    path = os.path.join(ROOT, "providers", "secrets", "resolver.py")
    missing = [n for n in names if not os.environ.get(n)]
    if not missing or not os.path.isfile(path):
        return []
    spec = importlib.util.spec_from_file_location("workbench_secret_resolver", path)
    resolver = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = resolver  # dataclasses look their module up here
    spec.loader.exec_module(resolver)
    # The core's registry holds the providers' credentials; a model provider's key is registered by the
    # adapter that reads it, and the resolver merges a manifest only when it is handed one.
    for manifest in sorted(glob.glob(os.path.join(ROOT, "adapters", "*", "adapter.json"))):
        try:
            resolver.register_file(manifest)
        except ValueError as e:
            die(f"the secrets list of {os.path.relpath(manifest, ROOT)} is not valid: {e}", 2)
    filled = []
    for name in missing:
        secret = resolver.REGISTRY.get(name)
        # Only a secret registered for eval runs is filled: a provider's credential never reaches a model.
        if secret is None or not any(r.startswith("evals/eval_run.py") for r in secret.readers):
            continue
        found = resolver.resolve(name)
        if found:
            os.environ[name] = found[0]
            filled.append(f"{name} ({found[1]})")
    return filled


def load_evals(skill):
    p = os.path.join(ROOT, "skills", skill, "evals", "evals.json")
    if not os.path.isfile(p):
        die(f"no evals at {os.path.relpath(p, ROOT)}", 2)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# Credentials in the environment would sign gh, npm or git hosts back in.
TOKEN_VARS = {"GH_TOKEN", "GITHUB_TOKEN", "VCS_GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN",
              "NPM_TOKEN", "NODE_AUTH_TOKEN"}
# The only variables a model run, a setup or the grader receives from the caller, besides --pass-env.
ENV_ALLOW = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "LANGUAGE", "TERM", "TMPDIR", "TZ",
             "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS", "REQUESTS_CA_BUNDLE"}


def refuse_allow_commands(data, cases):
    """Exit when the evals file or a case still lists "allow_commands": the field has no effect any more."""
    where = (["the top level"] if "allow_commands" in data else []) + \
            [f"case {c.get('id')}" for c in cases if "allow_commands" in c]
    if where:
        die(f"\"allow_commands\" is no longer used ({', '.join(where)}): every command runs, inside the eval "
            "container. Remove the field.")


def allow_web(data, case):
    """Whether the case may search and fetch web pages: "allow_web" at the top level or in the case."""
    for where, value in (("top level", data.get("allow_web")), (f"case {case.get('id')}", case.get("allow_web"))):
        if value is not None and not isinstance(value, bool):
            die(f"{where}: allow_web must be true or false, not {value!r}.")
    return bool(data.get("allow_web") or case.get("allow_web"))


def case_files(skill_dir, case):
    """The case's "files" entries as source paths, refusing any that reach outside the skill folder."""
    base = os.path.realpath(skill_dir)
    inside = lambda path: os.path.commonpath([base, os.path.realpath(path)]) == base
    out = []
    for rel in case.get("files") or []:
        parts = re.split(r"[\\/]", rel) if isinstance(rel, str) else [".."]
        if not isinstance(rel, str) or not rel or os.path.isabs(rel) or rel.startswith("~") or ".." in parts:
            die(f"case {case.get('id')}: files entry {rel!r} must be a relative path inside the skill folder, without '..'.")
        src = os.path.join(skill_dir, rel)
        if not inside(src):
            die(f"case {case.get('id')}: files entry {rel!r} resolves outside the skill folder.")
        for dp, dns, fns in os.walk(src) if os.path.isdir(src) else []:
            for n in dns + fns:
                p = os.path.join(dp, n)
                if os.path.islink(p) and not inside(p):
                    die(f"case {case.get('id')}: {os.path.relpath(p, skill_dir)} links outside the skill folder.")
        out.append(src)
    return out


def dependency_dirs(case):
    """Folders of the skills a case depends on (a flow's phases), installed by the adapter in both variants."""
    dirs = []
    for name in case.get("skills") or []:
        if not isinstance(name, str) or not re.match(r"^[a-z0-9-]+$", name):
            die(f"case {case.get('id')}: skills entry {name!r} is not a skill name.")
        src = os.path.join(ROOT, "skills", name)
        if not os.path.isdir(src):
            die(f"case {case.get('id')} depends on skill {name!r}, which does not exist under skills/.")
        dirs.append(src)
    return dirs


def workbench_files(case):
    """The case's "workbench_files" entries as (source path, path in the case folder): files and folders of
    this repository copied into the case at the same relative path, for a skill whose job is the workbench
    itself (it creates, validates or evaluates skills and needs the real tooling to act on). Refused: a path
    that leaves the repository, the repository root, version control, eval workspaces and any skill's eval
    cases (they hold expected outputs)."""
    base, out = os.path.realpath(ROOT), []
    for rel in case.get("workbench_files") or []:
        parts = [p for p in re.split(r"[\\/]", rel) if p] if isinstance(rel, str) else [".."]
        if not parts or os.path.isabs(rel) or rel.startswith("~") or ".." in parts:
            die(f"case {case.get('id')}: workbench_files entry {rel!r} must be a relative path inside the repository, without '..'.")
        src = os.path.realpath(os.path.join(ROOT, *parts))
        if os.path.commonpath([base, src]) != base or src == base or not os.path.exists(src):
            die(f"case {case.get('id')}: workbench_files entry {rel!r} is not a file or folder of the repository.")
        if parts[0] in (".git", "evals-workspace") or (parts[0] == "skills" and "evals" in parts[1:]):
            die(f"case {case.get('id')}: workbench_files entry {rel!r} is refused: version control, eval workspaces "
                "and a skill's eval cases never go into a case folder.")
        out.append((src, os.path.join(*parts)))
    return out


def build_tree(cwd, sources, case=None):
    """Copy a case's files into its folder: a folder's content goes to the root, a file keeps only its name.
    Then the case's "workbench_files", each at its own relative path, without any skill's evals/ folder."""
    for src, rel in workbench_files(case) if case else []:
        dest = os.path.join(cwd, rel)
        if os.path.isdir(src):
            shutil.copytree(src, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns(
                "evals", "__pycache__", "*.pyc", ".DS_Store") if rel.split(os.sep)[0] == "skills" else shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy(src, dest)
    for src in sources:
        if os.path.isdir(src):
            shutil.copytree(src, cwd, dirs_exist_ok=True)
        elif os.path.isfile(src):
            shutil.copy(src, cwd)


PATH_EXTENSIONS = ("md", "json", "yml", "yaml", "toml", "css", "js", "ts", "py", "html")
TOKEN_RE = re.compile(r"[A-Za-z0-9_.~@/*<>{}\[\]$:+%#=?&-]+")
NOT_A_PATH = set("*<>{}[]$~%#=?&+")
BARE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]*[A-Za-z0-9_-]\.(?:" + "|".join(PATH_EXTENSIONS) + r")$")
FILE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+\.[A-Za-z][A-Za-z0-9]{0,4}$")
HOST_RE = re.compile(r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
# Product names that look like a file name ("Node.js", "Next.js"): a capitalized word and .js, no folder.
PRODUCT_RE = re.compile(r"^[A-Z][A-Za-z0-9]*\.(?:js|ts|py)$")


# Folders only the workbench has: a prompt that cites a file there (a contract, a shared reference) names the
# workbench, not an input of the case.
WORKBENCH_DIRS = ("contracts", "shared", "templates", "providers", "adapters", "skills")


def prompt_paths(prompt):
    """Paths a prompt cites: tokens with a "/" and a file extension, or ending in a known extension.

    URLs, absolute and home paths, globs, placeholders and host names are left out."""
    found = []
    for token in TOKEN_RE.findall(prompt or ""):
        if "://" in token:
            continue
        token = token.split(":")[0].rstrip(".,;")
        while token.startswith("./"):
            token = token[2:]
        parts = token.split("/")
        if (not token or NOT_A_PATH & set(token) or token.startswith(("/", "@", "www.")) or ".." in parts
                or "" in parts):
            continue
        if len(parts) == 1:
            if not BARE_NAME_RE.match(token) or PRODUCT_RE.match(token):
                continue
        elif not FILE_NAME_RE.match(parts[-1]) or (HOST_RE.match(parts[0]) and not parts[0].startswith(".")):
            continue
        if token not in found:
            found.append(token)
    return found


def tree_paths(cwd):
    """Every file and folder of a case folder, relative, with "/" separators; .git is left out."""
    out = set()
    for dp, dns, fns in os.walk(cwd):
        dns[:] = [d for d in dns if d != ".git"]
        for n in dns + fns:
            out.add(os.path.relpath(os.path.join(dp, n), cwd).replace(os.sep, "/"))
    return out


def declared_outputs(skill_dir):
    """Paths under metadata.outputs in the skill's frontmatter: a run creates them, so a prompt may name them."""
    try:
        with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as f:
            head = f.read().split("\n---", 1)[0]
    except OSError:
        return []
    m = re.search(r"^\s*outputs:\s*\[(.*?)\]", head, re.M | re.S)
    if m:
        return [x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()]
    m = re.search(r"^\s*outputs:\s*\n((?:\s*-\s.*\n?)+)", head, re.M)
    return [x.strip()[1:].strip().strip("\"'") for x in m.group(1).splitlines() if x.strip()] if m else []


def preflight(skill_dir, cases, sources, setup=True):
    """Check every case before a model sees it. Returns (errors, unchecked): one line per problem.

    setup=False (--dry-run) runs no setup command, so cases that have one are not checked against their folder."""
    errors, unchecked = [], []
    outputs = declared_outputs(skill_dir)
    # The skill's own files (scripts, references, assets) reach a run with the skill, not through the case.
    own = {p for p in tree_paths(skill_dir) if not p.startswith("evals/") and p != "evals"}
    known = lambda p: (p in own or any(t.endswith("/" + p) for t in own)
                       or (p.split("/")[0] in WORKBENCH_DIRS and os.path.exists(os.path.join(ROOT, p))))
    for c in cases:
        cid = c.get("id")
        err = lambda msg: errors.append(f"case {cid}: {msg}")
        for rel, src in zip(c.get("files") or [], sources[cid]):
            if not os.path.exists(src):
                err(f"files entry {rel!r} does not exist in the skill folder")
        for name in c.get("skills") or []:
            if not isinstance(name, str) or not os.path.isdir(os.path.join(ROOT, "skills", name)):
                err(f"skills entry {name!r} is not a skill under skills/")
        absent = c.get("absent_on_purpose") or []
        if not isinstance(absent, list) or not all(isinstance(p, str) for p in absent):
            err("absent_on_purpose must be a list of paths")
            absent = []
        if c.get("setup") and not setup:
            unchecked.append(f"case {cid}: has setup commands, which --dry-run does not run; prompt paths and "
                             "grader_files are checked by --check-cases and by a real run")
            continue
        tmp = tempfile.mkdtemp(prefix="eval-preflight-")
        try:
            cwd = os.path.join(tmp, "cwd")
            os.makedirs(cwd)
            build_tree(cwd, sources[cid], c)
            if c.get("setup"):
                quiet = {"root": tmp, "network": "none"}  # in the eval container, like the run's own setup
                isolate_git(cwd, contained_env(tmp), box=quiet)
                run_setup(cwd, c["setup"], contained_env(tmp), box=quiet)
            tree = tree_paths(cwd)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        present = lambda p: p in tree or any(t.endswith("/" + p) for t in tree)
        produced = " ".join([str(c.get("expected_output") or "")] + [str(a) for a in c.get("assertions") or []])
        for p in prompt_paths(c.get("prompt")):
            if (present(p) or p in absent or p in produced or known(p)
                    or any(o == p or o.endswith("/" + p) for o in outputs)):
                continue
            err(f"the prompt cites {p!r}, which is not in the case folder: ship it under \"files\" at that path, "
                "or list it in \"absent_on_purpose\" when the case tests a missing input")
        for p in c.get("grader_files") or []:
            if not isinstance(p, str) or p.strip("/") not in tree:
                err(f"grader_files entry {p!r} is not in the case folder, so the grader would see an empty file")
    return errors, unchecked


def repo_paths():
    """The repository's absolute path as given and with links resolved (on some systems /var is a link)."""
    return {ROOT, os.path.realpath(ROOT)}


def temp_base(names=()):
    """The folder run folders are created in: the system's temporary folder, or /tmp or /var/tmp when that one
    is inside the repository, under a folder that holds a repository, an instruction file or a skills folder,
    or has the repository's folder name or one of names (the skill under test) in its path."""
    words = [w.lower() for w in (os.path.basename(os.path.realpath(ROOT)), *names) if w]
    for base in (tempfile.gettempdir(), "/tmp", "/var/tmp"):
        real = os.path.realpath(base)
        if not os.path.isdir(real) or not os.access(real, os.W_OK):
            continue
        if any(real == root or real.startswith(root + os.sep) for root in repo_paths()) or any(w in real.lower() for w in words):
            continue
        parent, clean = real, True
        while clean:
            clean = not any(os.path.exists(os.path.join(parent, marker)) for marker in (".git", "AGENTS.md", "skills"))
            if os.path.dirname(parent) == parent:
                break
            parent = os.path.dirname(parent)
        if clean:
            return real
    die("no temporary folder outside the repository to run the cases in: set TMPDIR to one whose parents hold no "
        ".git, AGENTS.md or skills folder.", 1)


# Temporary run folders in use -> where their content goes back to, so a stop returns every one of them.
RUN_ROOTS, RUN_ROOTS_LOCK = {}, threading.Lock()


def new_run_root(dest, out_name="outputs", names=()):
    """A fresh folder outside the repository for one model run or grading: case/ (the working folder), out/
    (the adapter's output) and prompt.md. return_run() moves them to dest/cwd, dest/<out_name> and dest/prompt.md."""
    with RUN_ROOTS_LOCK:
        if STOPPING.is_set():
            raise RuntimeError("stopping: no new run is started")
        root = tempfile.mkdtemp(prefix="eval-", dir=temp_base(names))
        RUN_ROOTS[root] = (dest, out_name)
    os.makedirs(os.path.join(root, "case"))
    os.makedirs(os.path.join(root, "out"))
    return root


def return_run(root):
    """Move a temporary run folder's content into the workspace and remove it. Safe to call twice."""
    with RUN_ROOTS_LOCK:  # held for the move, so a stop waits for a move in progress instead of cutting it
        entry = RUN_ROOTS.pop(root, None)
        if entry is None:
            return
        dest, out_name = entry
        os.makedirs(dest, exist_ok=True)
        for name, final in (("case", "cwd"), ("out", out_name), ("prompt.md", "prompt.md")):
            src, target = os.path.join(root, name), os.path.join(dest, final)
            if not os.path.lexists(src):
                continue
            if os.path.isdir(target) and not os.path.islink(target):
                shutil.rmtree(target)
            elif os.path.lexists(target):
                os.remove(target)
            shutil.move(src, target)
        shutil.rmtree(root, ignore_errors=True)


def return_all_runs():
    for root in list(RUN_ROOTS):
        return_run(root)


# What a provider answers when it declines a request on policy grounds, as the adapters record it.
PROVIDER_REFUSALS = ("safeguards flagged this message",)


def provider_refusal(out_dir):
    """The provider's refusal message when the run ended because the provider declined the request, else None."""
    for name in ("response.md", "raw.json", "error.log"):
        text = read_text(os.path.join(out_dir, name), 200000)
        for marker in PROVIDER_REFUSALS:
            at = text.find(marker)
            if at != -1:
                return text[max(0, at - 80):at + 160].replace("\n", " ").strip()
    return None


def contamination(out_dir):
    """Evidence that a run reached the repository: its absolute path in the response or the adapter's output.
    Exact path strings only; None when there is none."""
    for name in ("response.md", "stderr.log", "raw.json"):
        text = read_text(os.path.join(out_dir, name), 5000000)
        for root in sorted(repo_paths(), key=len, reverse=True):
            at = text.find(root)
            if at != -1:
                line = text[max(text.rfind("\n", 0, at) + 1, at - 80):at + len(root) + 120].split("\n")[0]
                return f"{name}: {line.strip()[:300]}"
    return None


def contained_env(run_dir, pass_env=()):
    """Environment for a model run, a setup or the grader: an allowlist, git local only, gh and npm signed out."""
    contain = os.path.join(run_dir, ".contain")
    gh_dir = os.path.join(contain, "gh")
    os.makedirs(gh_dir, exist_ok=True)
    npmrc, gitconfig = os.path.join(contain, "npmrc"), os.path.join(contain, "gitconfig")
    for path in (npmrc, gitconfig):
        open(path, "w").close()
    env = {k: v for k, v in os.environ.items()
           if (k in ENV_ALLOW or k.startswith("LC_") or k in pass_env) and k not in TOKEN_VARS}
    # Nothing tells the run where the repository is: PATH entries inside it go, an allowlisted variable that
    # points into it goes, and TMPDIR is the base the run folders are made in. A --pass-env variable is the
    # caller's own choice and stays as it is.
    inside = lambda value: any(root in value for root in repo_paths())
    if "PATH" in env and "PATH" not in pass_env:
        env["PATH"] = os.pathsep.join(p for p in env["PATH"].split(os.pathsep) if not inside(p))
    for k in [k for k, v in env.items() if k not in pass_env and inside(v)]:
        del env[k]
    if "TMPDIR" not in pass_env:
        env["TMPDIR"] = temp_base()
    env.update(GIT_ALLOW_PROTOCOL="file", GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=gitconfig,
               GIT_AUTHOR_NAME="eval", GIT_AUTHOR_EMAIL="eval@localhost",
               GIT_COMMITTER_NAME="eval", GIT_COMMITTER_EMAIL="eval@localhost",
               GH_CONFIG_DIR=gh_dir, NPM_CONFIG_USERCONFIG=npmrc)
    return env


def ablated_line_count(skill_dir, text):
    """Lines of SKILL.md that --ablate removes; exits when there are none."""
    with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as f:
        count = sum(1 for line in f if text in line)
    if not count:
        die(f"--ablate: no line of SKILL.md contains {text!r}.")
    return count


def ablated_copy(skill_dir, text, dest_root):
    """Copy the skill without its evals/ and without every SKILL.md line containing text."""
    dest = os.path.join(dest_root, os.path.basename(skill_dir))
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(skill_dir, dest, ignore=shutil.ignore_patterns("evals"))
    path = os.path.join(dest, "SKILL.md")
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    kept = [line for line in lines if text not in line]
    if len(kept) == len(lines):
        die(f"--ablate: no line of SKILL.md contains {text!r}.")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(kept)
    return dest, len(lines) - len(kept)


def next_iteration(ws, claim=True):
    """The next iteration folder of a skill's workspace. With claim it is created here, atomically, so two
    runs of the same skill started together never share one; a dry run only names it."""
    os.makedirs(ws, exist_ok=True)
    while True:
        nums = [int(d.split("-")[1]) for d in os.listdir(ws) if re.match(r"^iteration-\d+$", d)]
        path = os.path.join(ws, f"iteration-{max(nums, default=0) + 1}")
        if not claim:
            return path
        try:
            os.mkdir(path)
            return path
        except FileExistsError:
            continue


# Process groups started and not yet ended, so that stopping this script stops every one of them.
GROUPS, GROUPS_LOCK, STOPPING = set(), threading.Lock(), threading.Event()
STOP_GRACE = 5.0  # seconds between TERM and KILL; an adapter needs about two to stop its own runner


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # only processes that already ended and wait to be reaped
        return False
    return True


def stop_group(pgid, proc=None, grace=STOP_GRACE):
    """End a process group: TERM, then KILL for what is still there after the grace period."""
    try:
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    deadline = time.monotonic() + grace
    if proc is not None:
        try:
            proc.wait(timeout=grace)  # reaps the leader, so the check below sees only what outlived it
        except subprocess.TimeoutExpired:
            pass
    while group_alive(pgid) and time.monotonic() < deadline:
        time.sleep(0.1)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def stop_all_groups(grace=STOP_GRACE):
    """End every group still registered; no new one starts afterwards."""
    STOPPING.set()
    with GROUPS_LOCK:
        pending, containers = list(GROUPS), list(CONTAINERS)
    for name in containers:  # first, so that the work stops; their docker clients end with them
        try:
            load_executor().remove(name)
        except Exception:  # stopping goes on whatever one removal does
            pass
    for pgid in pending:
        try:
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    deadline = time.monotonic() + grace
    while any(group_alive(p) for p in pending) and time.monotonic() < deadline:
        time.sleep(0.1)
    for pgid in pending:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


CONTAINERS = set()  # names of containers started and not yet ended; guarded by GROUPS_LOCK


def run_group(cmd, timeout, cwd=None, env=None, box=None):
    """subprocess.run for a command in a session of its own: its whole process group ends on a timeout
    (subprocess.TimeoutExpired is raised) and when the command returns, so nothing it started outlives it.

    box = {"root", "skills", "pass", "network"} runs the command in a container (evals/executor.py): root is
    the run's folder, the only thing it can change. The container is removed by name when the command
    returns, times out or the script is stopped, since ending the docker client does not end it."""
    container = None
    if box is not None and EXECUTOR == "container":
        executor = load_executor()
        cmd, container = executor.command(cmd, box["root"], cwd=cwd, env=env, skills=box.get("skills") or (),
                                          pass_names=box.get("pass") or (), network=box.get("network") or "none")
        cwd = None
    try:
        return _run_group(cmd, timeout, cwd, env, container)
    finally:
        if container:
            load_executor().remove(container, env=env)
            with GROUPS_LOCK:
                CONTAINERS.discard(container)


def _run_group(cmd, timeout, cwd, env, container):
    with GROUPS_LOCK:
        if STOPPING.is_set():
            raise subprocess.TimeoutExpired(cmd, 0)
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, start_new_session=True)
        GROUPS.add(proc.pid)
        if container:
            CONTAINERS.add(container)
    try:
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop_group(proc.pid, proc)
            proc.kill()
            proc.communicate()
            raise
        stop_group(proc.pid, grace=2.0)  # what the command left running in the background
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
    finally:
        with GROUPS_LOCK:
            GROUPS.discard(proc.pid)


def run_failure(runner, prompt_path, cwd, model, out, skill_dir, env=None, extra_skills=(), timeout=900,
                max_cost=None, web=False, start_dir=None, box=None):
    """Run the adapter once. Returns None when it exited 0, else why it failed: an infrastructure failure,
    never a score (the adapter exits non-zero when the provider or the harness fails, not when the answer is poor)."""
    cmd = ["bash", runner, "--prompt-file", prompt_path, "--cwd", cwd, "--model", model, "--out", out]
    if max_cost:
        cmd += ["--max-cost-usd", max_cost]
    if skill_dir:
        cmd += ["--skill-dir", skill_dir]
    for d in extra_skills:
        cmd += ["--extra-skill-dir", d]
    if web:
        cmd += ["--allow-web"]
    try:
        # start_dir: the adapter's shell exports the folder it starts in as OLDPWD once it changes to <cwd>.
        r = run_group(cmd, timeout, cwd=start_dir, env=env, box=box)
    except subprocess.TimeoutExpired:
        with open(os.path.join(out, "error.log"), "w", encoding="utf-8") as f:
            f.write(f"stopped after --timeout {timeout}s\n")
        return f"timeout: stopped after {timeout}s"
    if r.returncode != 0:
        with open(os.path.join(out, "error.log"), "w", encoding="utf-8") as f:
            f.write(r.stdout + "\n" + r.stderr)
        last = [line.strip() for line in (r.stderr or r.stdout).splitlines() if line.strip()]
        return f"adapter exit {r.returncode}" + (f": {last[-1][:200]}" if last else "")
    return None


def run_prompt(*args, **kwargs):
    """True when the adapter ran the prompt; False when it failed (the reason is in <out>/error.log)."""
    return run_failure(*args, **kwargs) is None


def installed_skill_file(rel, names, cwd=None):
    """True for a file the adapter installed, wherever it put it: inside a copy of an installed skill
    (".../skills/<name>/...") or, with cwd, in the shared references copied beside the installed skills
    (".../shared/..." next to a ".../skills" folder that holds one of them)."""
    parts = rel.split(os.sep)
    if any(parts[i] == "skills" and parts[i + 1] in names for i in range(len(parts) - 2)):
        return True
    return cwd is not None and any(
        parts[i] == "shared" and any(os.path.isdir(os.path.join(cwd, *parts[:i], "skills", n)) for n in names)
        for i in range(len(parts) - 1))


# An early end: the model ended its turn before doing the work, with no error (see the module docstring).
# Markup of a tool call or a control block printed as text; it counts only at the start of a line, so a reply
# that quotes such markup inline to the user is left alone. Seen from a floor model: <skill_tool>, and loops
# of <system-reminder> blocks it wrote itself. "<\uff5ctool" is the model's own tool-call token.
EARLY_END_MARKUP = ("<skill_tool", "<tool_call", "<function_calls", "<invoke", "<system-reminder", "<|tool", "<\uff5ctool")
# How a last line announces a next action instead of ending the turn's work. Matched, in lower case, at the
# start of a sentence of the last line ("Let me update the file:", "Now I'll write the spec:").
EARLY_END_ANNOUNCE = ("let me", "i'll ", "i will ", "now i", "now let me", "now, let me", "first, i", "first, let me",
                      "first let me", "next, i", "next, let me", "i'm going to", "i am going to")
# A last line with one of these waits for the user ("Let me know which you prefer", "I'll wait for the brief",
# "If you approve it, I'll run it"): never an early end.
EARLY_END_NOT = ("let me know", "wait", "if you", "once you", "when you", "after you", "unless you")
PSEUDO_TAG_LINE_RE = re.compile(r"^<([A-Za-z_-]+)>.*</\1>$")
# A trailing line that is only a tag, such as a tool call the model printed as text and never ran
# (<read filePath="...">, </read>): skipped to reach the last line of prose.
TAG_ONLY_LINE_RE = re.compile(r"^</?[A-Za-z_][\w-]*(\s[^<>]*)?/?>$")


def early_end(response, changed):
    """Why a run that exited 0 is an early end, or None. Conservative: a run that wrote a file, or a reply
    that asks the user a question, is never one."""
    if changed:
        return None
    lines = [line.strip() for line in response.splitlines() if line.strip()]
    if not lines:
        return "empty response and no file written"
    for line in lines:
        hit = next((m for m in EARLY_END_MARKUP if line.lower().startswith(m)), None)
        if hit:
            return f"tool or control markup printed as text ({hit}) and no file written"
    if "?" in response:
        return None
    while len(lines) > 1 and (PSEUDO_TAG_LINE_RE.match(lines[-1]) or TAG_ONLY_LINE_RE.match(lines[-1])):
        lines.pop()  # a trailing note the model wrapped in a tag of its own
    last = lines[-1].lower().replace("\u2019", "'")
    if any(phrase in last for phrase in EARLY_END_NOT):
        return None
    for sentence in re.split(r"(?<=[.!:;])\s+", last):
        sentence = sentence.lstrip("-*>#_`0123456789.) ")
        if sentence.startswith(EARLY_END_ANNOUNCE):
            return "the last line announces a next action, no question was asked and no file written"
    return None


def early_end_stats(counts):
    """benchmark.json "early_ends" from {tier: {"attempts", "early_ends", "by_case"}}: adds the rate."""
    return {tier: {"attempts": c["attempts"], "early_ends": c["early_ends"],
                   "rate": round(c["early_ends"] / c["attempts"], 3) if c["attempts"] else 0.0,
                   "by_case": {str(k): n for k, n in c["by_case"].items() if n}}
            for tier, c in counts.items()}


def early_end_warning(stats, max_rate):
    """A sentence when a tier's early ends are frequent or all on one case (at least 3 either way), else None."""
    parts = []
    for tier, s in stats.items():
        one_case = list(s["by_case"]) if len(s["by_case"]) == 1 else []
        if s["early_ends"] < 3 or not (s["rate"] > max_rate or one_case):
            continue
        where = (f"All of them are on case {one_case[0]}: the skill or that case may trigger it; read its transcripts "
                 "before blaming the provider." if one_case else
                 f"They spread over cases {', '.join(s['by_case'])}: if they concentrate on one case, the skill or the "
                 "case may trigger it (read the transcripts); if they spread across cases, the provider or the model "
                 f"may be unreliable: consider another provider for this model, or another {tier} model.")
        parts.append(f"the {tier} model ended its turn early in {s['early_ends']} of {s['attempts']} attempts "
                     f"({s['rate']:.0%}): retries hid them from the scores. {where}")
    return " ".join(parts) or None


def snapshot(cwd, before, installed=()):
    files = {}
    names = set(installed)
    for dp, _, fns in os.walk(cwd):
        # Match whole folder names: "/.git" as a substring would also skip ".github".
        if {"node_modules", ".git"} & set(os.path.relpath(dp, cwd).split(os.sep)):
            continue
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, cwd)
            if installed_skill_file(rel, names, cwd):
                continue
            try:
                mtime = os.path.getmtime(p)
            except OSError:
                continue
            if rel not in before or before[rel] != mtime:
                files[rel] = mtime
    return files


def isolate_git(cwd, env, box=None):
    """Give the case its own repository, so git commands in a run stay inside it.

    Without one, `git add -A` or `git commit` from the case folder reaches the enclosing
    repository (the workbench itself) and commits whatever is uncommitted there. The contained
    environment also drops GIT_DIR and GIT_INDEX_FILE, which would point git at the workbench.
    """
    if os.path.isdir(os.path.join(cwd, ".git")):
        return
    for args in (["init", "-q"], ["add", "-A"], ["-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", "fixture"]):
        r = run_group(["git", *args], SETUP_TIMEOUT, cwd=cwd, env=env, box=box)
        if r.returncode != 0:
            raise subprocess.CalledProcessError(r.returncode, ["git", *args], r.stdout, r.stderr)


def run_setup(cwd, commands, env, box=None):
    """Run a case's setup commands in its folder (a branch, commits), after its repository exists, contained."""
    for command in commands:
        try:
            # security-scan: allow shell-string -- setup lines come from the skill's evals.json, are listed by --dry-run and run in the contained environment
            r = run_group(["bash", "-c", command], SETUP_TIMEOUT, cwd=cwd, env=env, box=box)
        except subprocess.TimeoutExpired:
            die(f"setup command timed out after {SETUP_TIMEOUT}s in {cwd}: {command}")
        if r.returncode != 0:
            die(f"setup command failed in {cwd}: {command}\n{r.stderr}")


def file_index(cwd):
    idx = {}
    for dp, _, fns in os.walk(cwd):
        for fn in fns:
            p = os.path.join(dp, fn)
            try:
                idx[os.path.relpath(p, cwd)] = os.path.getmtime(p)
            except OSError:
                pass
    return idx


def read_text(path, limit=4000):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read(limit)
    except OSError:
        return ""


# The grader sees each produced file up to this many characters. Plans and reports run to several
# thousand; at 3,000 an early run graded the end of a plan as missing, and at 20,000 an assertion about
# every source of a long research artifact failed as unproven.
FILE_LIMIT = 60000


def binary_stub(path):
    """What the grader is told about a file that is not text: its kind, its size and, for a PNG, its
    dimensions. None when the file reads as text. Bytes pasted as text told the grader nothing, and a
    few images made the grading prompt too long to pass to a harness."""
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
        size = os.path.getsize(path)
    except OSError:
        return None
    if head.startswith(b"\x89PNG\r\n\x1a\n") and len(head) >= 24:
        width, height = int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
        return f"[binary file: PNG image, {width}x{height} pixels, {size} bytes; its content is not shown]"
    kinds = ((b"\xff\xd8\xff", "JPEG image"), (b"GIF8", "GIF image"), (b"%PDF", "PDF document"), (b"PK\x03\x04", "zip archive"))
    for magic, kind in kinds:
        if head.startswith(magic):
            return f"[binary file: {kind}, {size} bytes; its content is not shown]"
    if b"\0" in head:
        return f"[binary file, {size} bytes; its content is not shown]"
    return None


def shown(path):
    stub = binary_stub(path)
    if stub:
        return stub
    text = read_text(path, FILE_LIMIT + 1)
    if len(text) > FILE_LIMIT:
        return text[:FILE_LIMIT] + f"\n[... truncated at {FILE_LIMIT} characters: the file continues ...]"
    return text


def grading_prompt(tpl, case, response, files_blob):
    """Fill the grading template in one pass, fencing the model's output with a marker it cannot predict.

    One pass: a response that contains "{files}" or "{assertions}" stays text instead of being replaced.
    """
    marker = secrets.token_hex(8)
    while marker in response or marker in files_blob:
        marker = secrets.token_hex(8)
    values = {"prompt": case["prompt"], "response": response, "files": files_blob, "marker": marker,
              "assertions": "\n".join(f"{i + 1}. {a}" for i, a in enumerate(case.get("assertions") or []))}
    return re.sub(r"\{(prompt|response|files|assertions|marker)\}", lambda m: values[m.group(1)], tpl)


def grade(runner, grader, run_dir, case, response, changed_files, pass_env=()):
    with open(GRADING_TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    files_blob = "\n".join(f"### {p}\n{shown(os.path.join(run_dir, 'cwd', p))}" for p in sorted(changed_files)) or "(none)"
    inputs = [p for p in case.get("grader_files") or [] if p not in changed_files
              and not os.path.isabs(p) and ".." not in p.split("/")]
    if inputs:
        files_blob += "\n\nInput files of the case, as the model found them (not produced by it):\n" + "\n".join(
            f"### {p}\n{shown(os.path.join(run_dir, 'cwd', p))}" for p in inputs)
    prompt = grading_prompt(tpl, case, response, files_blob)
    gdir = os.path.join(run_dir, "grading")
    # The grader is a model too: it works outside the repository, and its folders come back to grading/.
    root = new_run_root(gdir, out_name="out")
    try:
        gp = os.path.join(root, "prompt.md")
        with open(gp, "w", encoding="utf-8") as f:
            f.write(prompt)
        ok = run_prompt(runner, gp, os.path.join(root, "case"), grader, os.path.join(root, "out"), None,
                        env=contained_env(root, pass_env), start_dir=root,
                        box={"root": root, "pass": pass_env, "network": "proxy"})
    finally:
        return_run(root)
    if not ok:
        return None
    raw = read_text(os.path.join(gdir, "out", "response.md"), 200000)
    m = re.search(r"\[\s*\{.*\}\s*\]", raw, re.S)
    if not m:
        return None
    try:
        results = json.loads(m.group(0))
    except ValueError:
        return None
    passed = sum(1 for r in results if r.get("passed") is True)
    return {"assertion_results": results, "summary": {"passed": passed, "failed": len(results) - passed,
            "total": len(results), "pass_rate": (passed / len(results)) if results else 0.0}}


def check_cases_only(o):
    """--check-cases: the preflight alone. Prints {"skill", "cases", "errors", "unchecked"}; exit 2 on errors."""
    skill_dir = os.path.join(ROOT, "skills", o["skill"])
    cases = load_evals(o["skill"]).get("evals") or []
    if o["cases"]:
        cases = [c for c in cases if str(c.get("id")) in o["cases"]]
    if not cases:
        die("no matching eval cases.")
    refuse_allow_commands(load_evals(o["skill"]), cases)
    # A case's setup commands run only in the eval container, which a real run starts; this static check
    # needs no container, so such a case is listed as unchecked here and checked before the first model call.
    errors, unchecked = preflight(skill_dir, cases, {c["id"]: case_files(skill_dir, c) for c in cases}, setup=False)
    for line in errors:
        print(f"PREFLIGHT {o['skill']} {line}", file=sys.stderr)
    print(json.dumps({"skill": o["skill"], "cases": len(cases), "errors": errors, "unchecked": unchecked}, indent=2))
    return 2 if errors else 0


def main(argv):
    """Run, and leave nothing running: every process group started is ended on a signal and on any way out."""
    STOPPING.clear()

    def on_signal(signum, _frame):
        print(f"stopped by signal {signum}: ending every run that was started", file=sys.stderr)
        stop_all_groups()
        return_all_runs()  # the case folders go back to the workspace, the temporary folders are removed
        os._exit(128 + signum)  # worker threads would otherwise go on to the next run or grading

    previous = {}
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            previous[sig] = signal.signal(sig, on_signal)
    try:
        return run(argv)
    finally:
        stop_all_groups(grace=2.0)
        return_all_runs()
        STOPPING.clear()
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def run(argv):
    o = parse(argv)
    if o["check_cases"]:
        return check_cases_only(o)
    secrets = o["pass_env"] + o["floor_pass_env"] + (o["strong_pass_env"] if EXECUTOR == "container" else [])
    for filled in ([] if o["dry"] else resolve_pass_env(secrets)):
        print(f"--pass-env {filled}", file=sys.stderr)
    unset = [n for n in secrets if not os.environ.get(n)]
    if unset and not o["dry"]:
        # A missing provider key makes some runners fail with an opaque error (opencode: "UnknownError")
        # on every run; stop before spending a whole iteration on it.
        die(f"{', '.join(unset)} is not set and was not found in the secret store. Export it, or run this "
            "script with the store's library available: uv run --with keyring==25.7.0 python3 "
            "evals/eval_run.py ...", 2)
    runner = os.path.join(ROOT, "adapters", o["harness"], "run-prompt.sh")
    if not os.path.isfile(runner):
        die(f"adapter {o['harness']!r} has no run-prompt.sh (see AGENTS.md, Adding an adapter).")
    floor_runner = runner
    if o["floor_harness"]:
        floor_runner = os.path.join(ROOT, "adapters", o["floor_harness"], "run-prompt.sh")
        if not os.path.isfile(floor_runner):
            die(f"adapter {o['floor_harness']!r} has no run-prompt.sh.")
    runner_for = {"strong": runner, "floor": floor_runner}
    skill_dir = os.path.join(ROOT, "skills", o["skill"])
    evals = load_evals(o["skill"])
    cases = evals.get("evals") or []
    if o["cases"]:
        cases = [c for c in cases if str(c.get("id")) in o["cases"]]
    if not cases:
        die("no matching eval cases.")
    variants = ["with_skill"] + (["ablated_skill"] if o["ablate"] else []) + ["without_skill"]
    if o["only"]:
        variants = [f"{o['only']}_skill"]
    models = [("strong", o["model"])] + ([("floor", o["floor"])] if o["floor"] else [])
    if o["tiers"]:
        models = [m for m in models if m[0] in o["tiers"]]
        if not models:
            die("--tiers selected no model.")
    refuse_allow_commands(evals, cases)
    web = {c["id"]: allow_web(evals, c) for c in cases}
    sources = {c["id"]: case_files(skill_dir, c) for c in cases}
    # Before anything is spent or written: a case that cites a file it does not ship measures nothing.
    problems, unchecked = preflight(skill_dir, cases, sources, setup=not o["dry"])
    for line in problems:
        print(f"PREFLIGHT {o['skill']} {line}", file=sys.stderr)
    if problems and not o["dry"]:
        die(f"{len(problems)} preflight error(s) in the cases (listed above); nothing was run.", 2)
    deps = {c["id"]: dependency_dirs(c) for c in cases}
    status = load_status()
    start_hash = status.content_hash(skill_dir)
    environment = None
    if EXECUTOR == "container" and not o["dry"]:
        try:  # the images, the internal network and the proxy: built and started once, before any run
            environment = load_executor().ensure()
        except Exception as e:
            die(f"the eval container is not available: {e}", 1)
    it_dir = next_iteration(os.path.join(ROOT, "evals-workspace", o["skill"]), claim=not o["dry"])
    ablated_dir, ablated_lines = None, 0
    if "ablated_skill" in variants:
        ablated_lines = ablated_line_count(skill_dir, o["ablate"])
        if not o["dry"]:
            ablated_dir, _ = ablated_copy(skill_dir, o["ablate"], os.path.join(it_dir, "ablated-skill"))
    plan = [{"case": c["id"], "variant": v, "model_tier": t, "model": m, "run": k, "allow_web": web[c["id"]]}
            for c in cases for v in variants for t, m in models for k in range(1, o["runs"] + 1)]
    if o["dry"]:
        print(json.dumps({"dry_run": True, "iteration_dir": os.path.relpath(it_dir, ROOT), "runner": os.path.relpath(runner, ROOT),
                          "floor_runner": os.path.relpath(floor_runner, ROOT), "grader": o["grader"], "pass_env": o["pass_env"],
                          "floor_pass_env": o["floor_pass_env"],
                          "cases": [{"case": c["id"], "files": c.get("files") or [], "skills": c.get("skills") or [],
                                     "setup": c.get("setup") or []} for c in cases],
                          "ablate": {"text": o["ablate"], "lines_removed": ablated_lines} if o["ablate"] else None,
                          "timeout": o["timeout"], "max_cost_usd": o["max_cost"],
                          "preflight": {"errors": problems, "unchecked": unchecked}, "runs": plan}, indent=2))
        return 2 if problems else 0

    def one_run(c, v, tier, model, k):
        """Prepare, run and grade one (case, variant, model, run).

        Returns (name, row or None, infrastructure failure or None, messages, {"attempts", "early_ends"})."""
        infra = lambda reason, **more: {"case": c["id"], "variant": v, "tier": tier, "run": k, "reason": reason, **more}
        name = v if tier == "strong" else f"{v}.floor"
        run_dir = os.path.join(it_dir, f"eval-{c['id']}", name, *([f"run-{k}"] if o["runs"] > 1 else []))
        cwd, out = os.path.join(run_dir, "cwd"), os.path.join(run_dir, "outputs")
        variant_dir = {"with_skill": skill_dir, "ablated_skill": ablated_dir}.get(v)
        installed = [os.path.basename(d) for d in deps[c["id"]]] + ([o["skill"]] if variant_dir else [])
        count, msgs = {"attempts": 0, "early_ends": 0, "contaminated": None}, []
        while True:
            count["attempts"] += 1
            # The run happens outside the repository; its folders come back to run_dir when it ends, however it ends.
            root = new_run_root(run_dir, names=(o["skill"],))
            case_dir, changed = os.path.join(root, "case"), {}
            try:
                build_tree(case_dir, sources[c["id"]], c)
                tier_env = o["pass_env"] + (o["floor_pass_env"] if tier == "floor" else o["strong_pass_env"])
                env = contained_env(root, tier_env)
                quiet = {"root": root, "network": "none"}  # setup and the fixture commit: no secret, no network
                isolate_git(case_dir, contained_env(root), box=quiet)
                run_setup(case_dir, c.get("setup") or [], contained_env(root), box=quiet)
                pp = os.path.join(root, "prompt.md")
                with open(pp, "w", encoding="utf-8") as f:
                    f.write(c["prompt"])
                before = file_index(case_dir)
                why = run_failure(runner_for[tier], pp, case_dir, model, os.path.join(root, "out"), variant_dir,
                                  env, deps[c["id"]], o["timeout"], o["max_cost"], web[c["id"]],
                                  start_dir=root,
                                  box={"root": root, "skills": [variant_dir] + list(deps[c["id"]]), "pass": tier_env,
                                       "network": "open" if web[c["id"]] else "proxy"})
                if not why:
                    changed = snapshot(case_dir, before, installed)
            finally:
                return_run(root)
            if v == "without_skill":
                count["contaminated"] = contamination(out) or count["contaminated"]
            refusal = provider_refusal(out) if why and v == "without_skill" else None
            if refusal:
                # The model alone could not do the task: a baseline of zero, not a missing score. A refusal
                # of a run that has the skill stays an infrastructure failure: it says nothing about the skill.
                count["refused"] = refusal
                row = {"case": c["id"], "run": k, "pass_rate": 0.0, "tokens": None, "duration_ms": None, "refused": True}
                return name, row, None, msgs + [f"REFUSED     case {c['id']} {name} run {k}: the provider declined the "
                                                "request; scored 0 for the baseline"], count
            if why:
                return name, None, infra(why), msgs + [f"RUN FAILED  case {c['id']} {name} run {k} ({why}): see "
                                                       f"{os.path.relpath(os.path.join(out, 'error.log'), ROOT)}"], count
            response = read_text(os.path.join(out, "response.md"), 200000)
            early = early_end(response, changed)
            if not early:
                break
            # The adapter exited 0 but the model ended its turn before doing the work: not the skill's score.
            count["early_ends"] += 1
            if count["attempts"] > o["retries"]:
                return name, None, infra("early_end", detail=early, attempts=count["attempts"]), msgs + [
                    f"RUN FAILED  case {c['id']} {name} run {k} (early_end on all {count['attempts']} attempt(s): {early})"], count
            kept = os.path.join(run_dir, f"early-end-{count['attempts']}")
            os.makedirs(kept)
            for entry in os.listdir(run_dir):
                if not entry.startswith("early-end-"):
                    shutil.move(os.path.join(run_dir, entry), os.path.join(kept, entry))
            msgs.append(f"EARLY END   case {c['id']} {name} run {k} attempt {count['attempts']} ({early}): retrying; "
                        f"kept in {os.path.relpath(kept, ROOT)}")
        timing = {}
        try:
            with open(os.path.join(out, "timing.json"), encoding="utf-8") as f:
                timing = json.load(f)
        except (OSError, ValueError):
            pass
        with open(os.path.join(run_dir, "timing.json"), "w", encoding="utf-8") as f:
            json.dump(timing, f)
        g, failed = None, None
        if o["grade"]:
            g = grade(runner, o["grader"], run_dir, c, response, changed, o["pass_env"] + o["strong_pass_env"])
            if g is None:
                failed = infra("grading failed: the grader returned no parsable result")
                msgs.append(f"GRADE FAILED case {c['id']} {name} run {k}")
            else:
                with open(os.path.join(run_dir, "grading.json"), "w", encoding="utf-8") as f:
                    json.dump(g, f, indent=2)
        row = {"case": c["id"], "run": k, "pass_rate": g["summary"]["pass_rate"] if g else None,
               "tokens": timing.get("total_tokens"), "duration_ms": timing.get("duration_ms")}
        return name, row, failed, msgs, count

    jobs = [(c, v, t, m, k) for c in cases for v in variants for t, m in models for k in range(1, o["runs"] + 1)]
    infra_failures = []
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=o["jobs"]) as pool:
        done = [pool.submit(one_run, *j) for j in jobs]
        for fut in concurrent.futures.as_completed(done):
            for msg in fut.result()[3]:
                print(msg, file=sys.stderr)
    early_counts = {t: {"attempts": 0, "early_ends": 0, "by_case": {}} for t, _ in models}
    contaminated, refusals = [], []
    for job, fut in zip(jobs, done):  # submission order, so benchmark.json does not depend on which run finished first
        name, row, failed, _, count = fut.result()
        tier_count = early_counts[job[2]]
        tier_count["attempts"] += count["attempts"]
        tier_count["early_ends"] += count["early_ends"]
        tier_count["by_case"][job[0]["id"]] = tier_count["by_case"].get(job[0]["id"], 0) + count["early_ends"]
        if count["contaminated"]:
            contaminated.append({"case": job[0]["id"], "variant": job[1], "tier": job[2], "run": job[4],
                                 "evidence": count["contaminated"]})
        if count.get("refused"):
            refusals.append({"case": job[0]["id"], "variant": job[1], "tier": job[2], "run": job[4],
                             "evidence": count["refused"][:300]})
        if failed:
            infra_failures.append(failed)
        if row is not None:
            results.setdefault(name, []).append(row)

    def agg(rows, key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return {"mean": round(statistics.mean(vals), 3), "stddev": round(statistics.pstdev(vals), 3), "n": len(vals)} if vals else None

    summary = {name: {"pass_rate": agg(rows, "pass_rate"), "tokens": agg(rows, "tokens"), "duration_ms": agg(rows, "duration_ms"), "cases": rows}
               for name, rows in results.items()}
    def mean(name):
        s = summary.get(name, {}).get("pass_rate")
        return s["mean"] if s else None
    conditions = {}
    if mean("with_skill") is not None and mean("without_skill") is not None:
        conditions["strong_delta"] = round(mean("with_skill") - mean("without_skill"), 3)
        conditions["strong_delta_ok"] = conditions["strong_delta"] >= -o["tolerance"]
        conditions["strong_pass_rate"] = mean("with_skill")
        conditions["strong_ok"] = mean("with_skill") >= o["threshold"]
    if o["floor"] and mean("with_skill.floor") is not None:
        conditions["floor_pass_rate"] = mean("with_skill.floor")
        conditions["floor_ok"] = mean("with_skill.floor") >= o["threshold"]
    for tier_suffix in ("", ".floor"):
        if mean("with_skill" + tier_suffix) is not None and mean("ablated_skill" + tier_suffix) is not None:
            key = "ablation_delta" + ("_floor" if tier_suffix else "")
            conditions[key] = round(mean("with_skill" + tier_suffix) - mean("ablated_skill" + tier_suffix), 3)
    bench = {"skill": o["skill"], "runs": o["runs"], "timeout": o["timeout"], "max_cost_usd": o["max_cost"], "harness": o["harness"], "floor_harness": o["floor_harness"] or o["harness"], "models": dict(models), "grader": o["grader"], "threshold": o["threshold"],
             "strong_tolerance": o["tolerance"], "measurement_version": o["measurement_version"],
             **({"environment": environment} if environment else {}),
             "ablate": {"text": o["ablate"], "lines_removed": ablated_lines} if o["ablate"] else None,
             "run_summary": summary, "conditions": conditions, "failures": len(infra_failures)}
    # A run counts as completed when it produced a response and, unless --no-grade, was graded.
    completed = sum(1 for rows in results.values() for r in rows if r["pass_rate"] is not None or not o["grade"])
    complete = o["grade"] and not infra_failures and completed == len(jobs)
    iteration = int(os.path.basename(it_dir).split("-")[1])
    bench.update({"date": datetime.date.today().isoformat(), "iteration": iteration, "cases": [c["id"] for c in cases],
                  "content_sha256": start_hash, "expected_runs": len(jobs), "completed_runs": completed,
                  "complete": complete, "infra_failures": infra_failures})
    bench["contaminated"] = contaminated
    bench["baseline_refusals"] = refusals
    bench["early_ends"] = early_end_stats(early_counts)
    bench["early_end_warning"] = early_end_warning(bench["early_ends"], o["early_rate"])
    with open(os.path.join(it_dir, "benchmark.json"), "w", encoding="utf-8") as f:
        json.dump(bench, f, indent=2)
    if infra_failures:
        print(f"INCOMPLETE: {len(infra_failures)} of {len(jobs)} runs failed on infrastructure and have no score "
              "(benchmark.json infra_failures). Rerun the iteration; do not change the skill for them.", file=sys.stderr)
    full = (o["grade"] and not o["cases"] and not o["only"] and not o["ablate"]
            and [t for t, _ in models] == ["strong", "floor"])
    if contaminated:
        print(f"CONTAMINATED: {len(contaminated)} without-skill run(s) show the repository's path in their output "
              "(benchmark.json contaminated): the model reached the workbench, so the baseline may be inflated. Read "
              "the evidence, close the way in, and rerun; --allow-contaminated records anyway.", file=sys.stderr)
    record = {"written": False, "reason": None}
    blocked = contaminated and not o["allow_contaminated"]
    refusal = status.evidence_refusal(ROOT)
    if not refusal and environment and environment.get("image_platform") != load_executor().IMAGE_PLATFORM:
        refusal = (f"the image was built for {environment.get('image_platform')}, and evidence is made on "
                   f"{load_executor().IMAGE_PLATFORM} only")
    if not o["record"]:
        record["reason"] = "--no-record"
    elif refusal:
        record["reason"] = refusal
    elif o["update_record"]:
        # The baseline alone: both without-skill scores of the existing record are replaced.
        if [t for t, _ in models] != ["strong", "floor"]:
            record["reason"] = "no floor model: the baseline is measured on both models"
        elif not complete:
            record["reason"] = "incomplete iteration"
        elif blocked:
            record["reason"] = f"{len(contaminated)} contaminated without-skill run(s); see benchmark.json"
        elif status.content_hash(skill_dir) != start_hash:
            record["reason"] = "the skill folder changed during the run: rerun the evals on the current content"
        else:
            try:
                updated = status.update_baseline(skill_dir, bench, iteration, bench["date"], status.load_gate(ROOT))
                status.write_record(skill_dir, updated)
                state = status.skill_status(skill_dir)
                record = {"written": True, "path": os.path.relpath(status.record_path(skill_dir), ROOT),
                          "status": state["status"], "updated": "baseline",
                          "scores": {k: updated["scores"][k] for k in ("strong_without", "floor_without")}}
                if not updated["gate"]["passed"]:
                    print(f"RECORD {o['skill']}: with the new baseline the gate no longer passes ({state['reason']}); "
                          "the record is written and the skill reads draft.", file=sys.stderr)
            except ValueError as e:
                record["reason"] = f"record not updated: {e}"
    elif not full:
        record["reason"] = "partial run: a record needs every case, both variants, both models, grading and no --ablate"
    elif o["configured_floor"] and o["floor"] != o["configured_floor"] and not o["record_anyway"]:
        record["reason"] = (f"the floor model {o['floor']} is not the configured one ({o['configured_floor']}), so the "
                            "record would read as stale; pass --record-anyway to write it")
    elif not complete:
        record["reason"] = "incomplete iteration"
    elif blocked:
        record["reason"] = f"{len(contaminated)} contaminated without-skill run(s); see benchmark.json"
    elif status.content_hash(skill_dir) != start_hash:
        record["reason"] = "the skill folder changed during the run: rerun the evals on the current content"
    else:
        try:
            status.write_record(skill_dir, status.build_record(skill_dir, bench, iteration, bench["date"], start_hash))
            record = {"written": True, "path": os.path.relpath(status.record_path(skill_dir), ROOT),
                      "status": status.skill_status(skill_dir)["status"]}
        except ValueError as e:
            record["reason"] = str(e)
    print(f"RECORD {o['skill']}: " + (f"{record['path']} written, status {record['status']}. Then run: python3 "
          "evals/eval_status.py inventory --write" if record["written"] else f"not written ({record['reason']})"),
          file=sys.stderr)
    if bench["early_end_warning"]:
        print(f"WARNING early ends: {bench['early_end_warning']}", file=sys.stderr)
    print(json.dumps({"iteration_dir": os.path.relpath(it_dir, ROOT), "conditions": conditions,
                      "failures": len(infra_failures), "complete": complete, "expected_runs": len(jobs),
                      "completed_runs": completed, "record": record, "contaminated": len(contaminated),
                      "early_ends": {t: {"early_ends": s["early_ends"], "attempts": s["attempts"], "rate": s["rate"]}
                                     for t, s in bench["early_ends"].items()},
                      "early_end_warning": bench["early_end_warning"]}))
    if infra_failures:
        return 1
    if conditions and not all(v for k, v in conditions.items() if k.endswith("_ok")):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
