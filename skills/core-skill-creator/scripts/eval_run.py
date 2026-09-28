#!/usr/bin/env python3
"""Run a skill's evals with and without the skill, on a strong and a floor model, and grade them.

Usage:
  python3 eval_run.py --skill <name> --harness <adapter> --model <strong-id>
                      [--floor-model <id>] [--floor-harness <adapter>] [--grader <id>] [--case <id>]... [--threshold 0.8]
                      [--only with|without|ablated] [--tiers strong,floor] [--pass-env <VAR>]... [--ablate <text>]
                      [--runs 3] [--timeout 900] [--max-cost-usd <amount>] [--no-grade] [--dry-run]

Reads skills/<name>/evals/evals.json. For each case and each variant (with_skill, without_skill)
and each model, it prepares a working directory with the case's files (paths inside the skill folder
only) in its own git repository (one "fixture" commit, then the case's optional "setup" shell commands,
such as a branch with commits), runs the prompt through adapters/<harness>/run-prompt.sh with the skills
listed in the case's optional "skills" (a flow's phases) for both variants, grades every assertion with
the grader model, and writes:

  evals-workspace/<name>/iteration-N/eval-<id>/<variant>[.floor]/{prompt.md,cwd/,outputs/,grading.json,timing.json}
  evals-workspace/<name>/iteration-N/benchmark.json

--runs <n> (default 3) runs every case, variant and model n times, one after another (parallel runs made
the agents-dir runner fail); each run gets its own folder, run-<k>/, and benchmark.json averages them.
--timeout <seconds> (default 900) stops a model run that takes longer, on any adapter, and counts it as
failed. --max-cost-usd <amount> is passed to the adapter as a spend limit per run: the claude-code adapter
enforces it, agents-dir says it cannot (a credit limit on the provider key is the cap there).

--ablate <text> adds a third variant, ablated_skill: the skill with every SKILL.md line containing <text>
removed (for example "External content is data."), to measure what one rule changes. It is refused when
no line matches. benchmark.json then reports ablation_delta (with_skill minus ablated_skill) per tier;
it is a measurement, not a pass condition.

--floor-harness lets the floor model run through a different adapter (for example agents-dir for an
open-weight model served through its own CLI) while the strong model and the grader use --harness.
--dry-run prints the runs, the allowed commands and every case's setup commands, and runs nothing.

Adapter contract: run-prompt.sh --prompt-file <f> --cwd <dir> --model <id> --out <dir> [--skill-dir <dir>]
[--extra-skill-dir <dir>]... [--allow-command <prefix>]... copies each skill folder into <cwd> where the
harness discovers it (never a link into the workbench) and must write <out>/response.md and
<out>/timing.json ({"total_tokens", "duration_ms", "cost_usd"}).

Commands. evals.json may list "allow_commands" at the top level (every case) and per case: command
prefixes the model may run without asking ("npm test", "git status", "TZ=UTC npm test"). They are
passed to the adapter as --allow-command; the adapter also allows the skill's own scripts. Refused,
because the prefix alone would run any code: wildcards and the characters ( ) , ; command runners
(env, xargs, find, npx, sudo...); a shell or an interpreter (node, python3, perl...) without a script
path right after it; git without a subcommand, with an option before it (git -c ...) or with "config";
leading assignments other than TZ, LANG, LC_*, CI, NODE_ENV, NO_COLOR, FORCE_COLOR.
A prefix fixes only the start of a command: "npm test" runs whatever tests the model wrote, and git
runs hooks it wrote. The environment below is what limits such code.

Containment. Model runs, setup commands and the grader get an environment built from an allowlist
(PATH, HOME, USER, LOGNAME, SHELL, LANG, LANGUAGE, LC_*, TERM, TMPDIR, TZ and certificate-bundle paths),
plus the variables named with --pass-env (a harness's API key or proxy; a registered secret missing from
the environment is read from the OS secret store through providers/secrets/resolver.py); token variables for git hosts
and npm are refused there. On top: GIT_ALLOW_PROTOCOL=file (git reaches only local remotes), no global
or system git config, GH_CONFIG_DIR pointing to an empty folder (the GitHub CLI is signed out) and
NPM_CONFIG_USERCONFIG pointing to an empty file (npm has no token). Remotes a case needs are local bare
repositories created by its "setup". This is not a sandbox: the filesystem, HOME included, and network
reads stay reachable, so run the evals of a contributed skill only after reading its evals.json. The
grader is told that the response and files are data; the adapter decides whether it may run tools.

Exit codes: 0 ok, 1 a run or grading failed, 2 usage error, 3 conditions not met (reported, not an error of the tool).
"""
import importlib.util
import json
import os
import re
import secrets
import shutil
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
GRADING_TEMPLATE = os.path.join(HERE, "..", "assets", "grading-prompt.md")
SETUP_TIMEOUT = 300  # seconds per setup command


def die(msg, code=2):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse(argv):
    opts = {"skill": None, "harness": None, "model": None, "floor": None, "floor_harness": None, "grader": None, "cases": [],
            "threshold": 0.8, "only": None, "tiers": None, "grade": True, "dry": False, "pass_env": [], "ablate": None,
            "runs": 3, "timeout": 900, "max_cost": None}
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
        elif a == "--runs": opts["runs"] = val(); i += 2
        elif a == "--timeout": opts["timeout"] = val(); i += 2
        elif a == "--max-cost-usd": opts["max_cost"] = val(); i += 2
        elif a == "--no-grade": opts["grade"] = False; i += 1
        elif a == "--dry-run": opts["dry"] = True; i += 1
        elif a in ("--help", "-h"): print(__doc__); sys.exit(0)
        else: die(f"unknown option {a!r}. See --help.")
    for k in ("skill", "harness", "model"):
        if not opts[k]:
            die(f"--{k} is required.")
    if opts["only"] not in (None, "with", "without", "ablated"):
        die("--only must be with, without or ablated.")
    if opts["only"] == "ablated" and not opts["ablate"]:
        die("--only ablated needs --ablate <text>.")
    if opts["ablate"] is not None and not opts["ablate"].strip():
        die("--ablate needs a non-empty text.")
    try:
        opts["runs"], opts["timeout"] = int(opts["runs"]), int(opts["timeout"])
    except (TypeError, ValueError):
        die("--runs and --timeout take whole numbers.")
    if not 1 <= opts["runs"] <= 10:
        die("--runs must be between 1 and 10.")
    if opts["timeout"] < 30:
        die("--timeout is in seconds and at least 30.")
    if opts["max_cost"] is not None and not re.fullmatch(r"\d+(\.\d+)?", opts["max_cost"]):
        die("--max-cost-usd takes a number, e.g. 0.50.")
    for name in opts["pass_env"]:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            die(f"--pass-env {name!r} is not a variable name.")
        if name in TOKEN_VARS:
            die(f"--pass-env {name}: token variables for git hosts and npm never reach a model run.")
    opts["grader"] = opts["grader"] or opts["model"]
    return opts


def resolve_pass_env(names):
    """Fill a --pass-env variable missing from the environment from the workbench's secret resolver
    (providers/secrets/resolver.py: the OS secret store), so a key kept there reaches the runs
    without an export. Only secrets whose registered readers include eval_run.py are filled;
    other names and values that are not found are left alone."""
    path = os.path.join(ROOT, "providers", "secrets", "resolver.py")
    missing = [n for n in names if not os.environ.get(n)]
    if not missing or not os.path.isfile(path):
        return []
    spec = importlib.util.spec_from_file_location("workbench_secret_resolver", path)
    resolver = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = resolver  # dataclasses look their module up here
    spec.loader.exec_module(resolver)
    filled = []
    for name in missing:
        secret = resolver.REGISTRY.get(name)
        # Only a secret registered for eval runs is filled: a provider's credential never reaches a model.
        if secret is None or not any(r.startswith("skills/core-skill-creator/scripts/eval_run.py") for r in secret.readers):
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


# Commands that run another command: allowing one of them allows everything.
RUNNERS = {"env", "xargs", "sudo", "doas", "su", "eval", "exec", "nohup", "time", "command", "nice", "timeout",
           "watch", "script", "osascript", "find", "npx", "bunx", "awk", "gawk", "mawk", "nawk", "ssh"}
RUNNER_SUBCOMMANDS = {("npm", "exec"), ("npm", "x"), ("pnpm", "exec"), ("pnpm", "dlx"), ("yarn", "exec"), ("yarn", "dlx")}
# Shells and interpreters are accepted only with a script path after them ("bash scripts/check.sh").
SHELLS = {"bash", "sh", "zsh", "dash", "fish", "ksh"}
INTERPRETERS = {"node", "nodejs", "deno", "bun", "python", "python2", "python3", "pypy", "pypy3", "ruby", "perl",
                "php", "lua", "Rscript", "pwsh", "powershell", "tclsh"}
# git runs code through options before the subcommand (-c alias.x=!cmd) and through its config.
GIT_REFUSED_SUBCOMMANDS = {"config"}
# Leading assignments that cannot turn a command into a runner (NODE_OPTIONS, LD_PRELOAD, GIT_* could).
SAFE_ASSIGNMENTS = {"TZ", "LANG", "LANGUAGE", "CI", "NODE_ENV", "NO_COLOR", "FORCE_COLOR"}
# Characters that break out of an adapter's rule syntax or chain commands.
REFUSED_CHARS = set("*(),;|&`$<>\\")
# Credentials in the environment would sign gh, npm or git hosts back in.
TOKEN_VARS = {"GH_TOKEN", "GITHUB_TOKEN", "VCS_GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN",
              "NPM_TOKEN", "NODE_AUTH_TOKEN"}
# The only variables a model run, a setup or the grader receives from the caller, besides --pass-env.
ENV_ALLOW = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "LANGUAGE", "TERM", "TMPDIR", "TZ",
             "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS", "REQUESTS_CA_BUNDLE"}


def check_prefix(p):
    """Return why an allow_commands prefix would allow any command, or None when it is acceptable."""
    if not isinstance(p, str) or not p.strip():
        return "it is empty"
    bad = sorted({ch for ch in p if ch in REFUSED_CHARS or ord(ch) < 32})
    if bad:
        return f"it contains {' '.join(repr(ch) for ch in bad)}"
    words = p.split()
    while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$", words[0]):
        var = words[0].split("=", 1)[0]
        if var not in SAFE_ASSIGNMENTS and not var.startswith("LC_"):
            return f"the assignment {var}= can change what the command runs"
        words = words[1:]  # leading VAR=value assignments (TZ=UTC npm test)
    if not words:
        return "it names no command"
    cmd = words[0]
    if cmd in RUNNERS or tuple(words[:2]) in RUNNER_SUBCOMMANDS:
        return f"{' '.join(words[:2]) if tuple(words[:2]) in RUNNER_SUBCOMMANDS else cmd} runs other commands"
    if cmd in SHELLS or cmd in INTERPRETERS:
        script = words[1] if len(words) > 1 else ""
        if not script or script.startswith("-") or os.path.isabs(script) or ".." in script.split("/"):
            return f"{cmd} without a script path inside the case folder runs any code"
    if cmd == "git":
        if len(words) < 2 or words[1].startswith("-"):
            return "git needs a subcommand first (git status), since options such as -c run any command"
        if words[1] in GIT_REFUSED_SUBCOMMANDS:
            return f"git {words[1]} can make later git commands run any command"
    return None


def allowed_commands(data, case):
    """The case's command prefixes (top-level list plus the case's own), refusing ones that allow everything."""
    prefixes = list(dict.fromkeys((data.get("allow_commands") or []) + (case.get("allow_commands") or [])))
    for p in prefixes:
        why = check_prefix(p)
        if why:
            die(f"case {case.get('id')}: allow_commands entry {p!r} is refused: {why}. Name the command and its "
                "subcommand (\"npm test\", \"git status\", \"node scripts/size.mjs\").")
    return prefixes


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


def next_iteration(ws):
    os.makedirs(ws, exist_ok=True)
    nums = [int(d.split("-")[1]) for d in os.listdir(ws) if re.match(r"^iteration-\d+$", d)]
    return os.path.join(ws, f"iteration-{max(nums, default=0) + 1}")


def run_prompt(runner, prompt_path, cwd, model, out, skill_dir, allow=(), env=None, extra_skills=(), timeout=900,
               max_cost=None):
    cmd = ["bash", runner, "--prompt-file", prompt_path, "--cwd", cwd, "--model", model, "--out", out]
    if max_cost:
        cmd += ["--max-cost-usd", max_cost]
    if skill_dir:
        cmd += ["--skill-dir", skill_dir]
    for d in extra_skills:
        cmd += ["--extra-skill-dir", d]
    for p in allow:
        cmd += ["--allow-command", p]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        with open(os.path.join(out, "error.log"), "w", encoding="utf-8") as f:
            f.write(f"stopped after --timeout {timeout}s\n")
        return False
    if r.returncode != 0:
        with open(os.path.join(out, "error.log"), "w", encoding="utf-8") as f:
            f.write(r.stdout + "\n" + r.stderr)
        return False
    return True


def installed_skill_file(rel, names):
    """True for a file inside a copy of an installed skill (".../skills/<name>/..."), wherever the adapter put it."""
    parts = rel.split(os.sep)
    return any(parts[i] == "skills" and parts[i + 1] in names for i in range(len(parts) - 2))


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
            if installed_skill_file(rel, names):
                continue
            try:
                mtime = os.path.getmtime(p)
            except OSError:
                continue
            if rel not in before or before[rel] != mtime:
                files[rel] = mtime
    return files


def isolate_git(cwd, env):
    """Give the case its own repository, so git commands in a run stay inside it.

    Without one, `git add -A` or `git commit` from the case folder reaches the enclosing
    repository (the workbench itself) and commits whatever is uncommitted there. The contained
    environment also drops GIT_DIR and GIT_INDEX_FILE, which would point git at the workbench.
    """
    if os.path.isdir(os.path.join(cwd, ".git")):
        return
    for args in (["init", "-q"], ["add", "-A"], ["-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", "fixture"]):
        subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, timeout=SETUP_TIMEOUT)


def run_setup(cwd, commands, env):
    """Run a case's setup commands in its folder (a branch, commits), after its repository exists, contained."""
    for command in commands:
        try:
            # security-scan: allow shell-string -- setup lines come from the skill's evals.json, are listed by --dry-run and run in the contained environment
            r = subprocess.run(["bash", "-c", command], cwd=cwd, env=env, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=SETUP_TIMEOUT)
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
# thousand; at 3,000 the first real run graded the end of a plan as missing.
FILE_LIMIT = 20000


def shown(path):
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
    prompt = grading_prompt(tpl, case, response, files_blob)
    gdir = os.path.join(run_dir, "grading")
    os.makedirs(os.path.join(gdir, "cwd"), exist_ok=True)
    os.makedirs(os.path.join(gdir, "out"), exist_ok=True)
    gp = os.path.join(gdir, "prompt.md")
    with open(gp, "w", encoding="utf-8") as f:
        f.write(prompt)
    if not run_prompt(runner, gp, os.path.join(gdir, "cwd"), grader, os.path.join(gdir, "out"), None,
                      env=contained_env(gdir, pass_env)):
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


def main(argv):
    o = parse(argv)
    for filled in ([] if o["dry"] else resolve_pass_env(o["pass_env"])):
        print(f"--pass-env {filled}", file=sys.stderr)
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
    it_dir = next_iteration(os.path.join(ROOT, "evals-workspace", o["skill"]))
    ablated_dir, ablated_lines = None, 0
    if "ablated_skill" in variants:
        ablated_lines = ablated_line_count(skill_dir, o["ablate"])
        if not o["dry"]:
            ablated_dir, _ = ablated_copy(skill_dir, o["ablate"], os.path.join(it_dir, "ablated-skill"))
    allow = {c["id"]: allowed_commands(evals, c) for c in cases}
    sources = {c["id"]: case_files(skill_dir, c) for c in cases}
    deps = {c["id"]: dependency_dirs(c) for c in cases}
    plan = [{"case": c["id"], "variant": v, "model_tier": t, "model": m, "run": k, "allow_commands": allow[c["id"]]}
            for c in cases for v in variants for t, m in models for k in range(1, o["runs"] + 1)]
    if o["dry"]:
        print(json.dumps({"dry_run": True, "iteration_dir": os.path.relpath(it_dir, ROOT), "runner": os.path.relpath(runner, ROOT),
                          "floor_runner": os.path.relpath(floor_runner, ROOT), "grader": o["grader"], "pass_env": o["pass_env"],
                          "cases": [{"case": c["id"], "files": c.get("files") or [], "skills": c.get("skills") or [],
                                     "setup": c.get("setup") or []} for c in cases],
                          "ablate": {"text": o["ablate"], "lines_removed": ablated_lines} if o["ablate"] else None,
                          "timeout": o["timeout"], "max_cost_usd": o["max_cost"], "runs": plan}, indent=2))
        return 0

    failures = 0
    results = {}
    for c in cases:
        for v in variants:
            for tier, model, k in [(t, m, k) for t, m in models for k in range(1, o["runs"] + 1)]:
                name = v if tier == "strong" else f"{v}.floor"
                run_dir = os.path.join(it_dir, f"eval-{c['id']}", name, *([f"run-{k}"] if o["runs"] > 1 else []))
                cwd, out = os.path.join(run_dir, "cwd"), os.path.join(run_dir, "outputs")
                os.makedirs(cwd, exist_ok=True)
                os.makedirs(out, exist_ok=True)
                for src in sources[c["id"]]:
                    if os.path.isdir(src):
                        shutil.copytree(src, cwd, dirs_exist_ok=True)
                    elif os.path.isfile(src):
                        shutil.copy(src, cwd)
                env = contained_env(run_dir, o["pass_env"])
                isolate_git(cwd, contained_env(run_dir))
                run_setup(cwd, c.get("setup") or [], contained_env(run_dir))
                pp = os.path.join(run_dir, "prompt.md")
                with open(pp, "w", encoding="utf-8") as f:
                    f.write(c["prompt"])
                before = file_index(cwd)
                variant_dir = {"with_skill": skill_dir, "ablated_skill": ablated_dir}.get(v)
                ok = run_prompt(runner_for[tier], pp, cwd, model, out, variant_dir,
                                allow[c["id"]], env, deps[c["id"]], o["timeout"], o["max_cost"])
                if not ok:
                    failures += 1
                    print(f"RUN FAILED  case {c['id']} {name} run {k}: see {os.path.relpath(os.path.join(out, 'error.log'), ROOT)}", file=sys.stderr)
                    continue
                installed = [os.path.basename(d) for d in deps[c["id"]]] + ([o["skill"]] if variant_dir else [])
                changed = snapshot(cwd, before, installed)
                response = read_text(os.path.join(out, "response.md"), 200000)
                timing = {}
                try:
                    with open(os.path.join(out, "timing.json"), encoding="utf-8") as f:
                        timing = json.load(f)
                except (OSError, ValueError):
                    pass
                with open(os.path.join(run_dir, "timing.json"), "w", encoding="utf-8") as f:
                    json.dump(timing, f)
                g = None
                if o["grade"]:
                    g = grade(runner, o["grader"], run_dir, c, response, changed, o["pass_env"])
                    if g is None:
                        failures += 1
                        print(f"GRADE FAILED case {c['id']} {name} run {k}", file=sys.stderr)
                    else:
                        with open(os.path.join(run_dir, "grading.json"), "w", encoding="utf-8") as f:
                            json.dump(g, f, indent=2)
                results.setdefault(name, []).append({"case": c["id"], "run": k, "pass_rate": g["summary"]["pass_rate"] if g else None,
                                                     "tokens": timing.get("total_tokens"), "duration_ms": timing.get("duration_ms")})

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
        conditions["strong_delta_ok"] = conditions["strong_delta"] >= 0
    if o["floor"] and mean("with_skill.floor") is not None:
        conditions["floor_pass_rate"] = mean("with_skill.floor")
        conditions["floor_ok"] = mean("with_skill.floor") >= o["threshold"]
    for tier_suffix in ("", ".floor"):
        if mean("with_skill" + tier_suffix) is not None and mean("ablated_skill" + tier_suffix) is not None:
            key = "ablation_delta" + ("_floor" if tier_suffix else "")
            conditions[key] = round(mean("with_skill" + tier_suffix) - mean("ablated_skill" + tier_suffix), 3)
    bench = {"skill": o["skill"], "runs": o["runs"], "timeout": o["timeout"], "max_cost_usd": o["max_cost"], "harness": o["harness"], "floor_harness": o["floor_harness"] or o["harness"], "models": dict(models), "grader": o["grader"], "threshold": o["threshold"],
             "ablate": {"text": o["ablate"], "lines_removed": ablated_lines} if o["ablate"] else None,
             "run_summary": summary, "conditions": conditions, "failures": failures}
    with open(os.path.join(it_dir, "benchmark.json"), "w", encoding="utf-8") as f:
        json.dump(bench, f, indent=2)
    print(json.dumps({"iteration_dir": os.path.relpath(it_dir, ROOT), "conditions": conditions, "failures": failures}))
    if failures:
        return 1
    if conditions and not all(v for k, v in conditions.items() if k.endswith("_ok")):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
