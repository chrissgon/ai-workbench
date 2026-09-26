#!/usr/bin/env python3
"""Run a skill's evals with and without the skill, on a strong and a floor model, and grade them.

Usage:
  python3 eval_run.py --skill <name> --harness <adapter> --model <strong-id>
                      [--floor-model <id>] [--floor-harness <adapter>] [--grader <id>] [--case <id>]... [--threshold 0.8]
                      [--only with|without] [--tiers strong,floor] [--no-grade] [--dry-run]

Reads skills/<name>/evals/evals.json. For each case and each variant (with_skill, without_skill)
and each model, it prepares a working directory with the case's files, runs the prompt through
adapters/<harness>/run-prompt.sh, grades every assertion with the grader model, and writes:

  evals-workspace/<name>/iteration-N/eval-<id>/<variant>[.floor]/{prompt.md,cwd/,outputs/,grading.json,timing.json}
  evals-workspace/<name>/iteration-N/benchmark.json

--floor-harness lets the floor model run through a different adapter (for example agents-dir for an
open-weight model served through its own CLI) while the strong model and the grader use --harness.

Adapter contract: run-prompt.sh --prompt-file <f> --cwd <dir> --model <id> --out <dir> [--skill-dir <dir>]
must write <out>/response.md and <out>/timing.json ({"total_tokens", "duration_ms", "cost_usd"}).

Exit codes: 0 ok, 1 a run or grading failed, 2 usage error, 3 conditions not met (reported, not an error of the tool).
"""
import json
import os
import re
import shutil
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
GRADING_TEMPLATE = os.path.join(HERE, "..", "assets", "grading-prompt.md")


def die(msg, code=2):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse(argv):
    opts = {"skill": None, "harness": None, "model": None, "floor": None, "floor_harness": None, "grader": None, "cases": [],
            "threshold": 0.8, "only": None, "tiers": None, "grade": True, "dry": False}
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
        elif a == "--no-grade": opts["grade"] = False; i += 1
        elif a == "--dry-run": opts["dry"] = True; i += 1
        elif a in ("--help", "-h"): print(__doc__); sys.exit(0)
        else: die(f"unknown option {a!r}. See --help.")
    for k in ("skill", "harness", "model"):
        if not opts[k]:
            die(f"--{k} is required.")
    if opts["only"] not in (None, "with", "without"):
        die("--only must be with or without.")
    opts["grader"] = opts["grader"] or opts["model"]
    return opts


def load_cases(skill):
    p = os.path.join(ROOT, "skills", skill, "evals", "evals.json")
    if not os.path.isfile(p):
        die(f"no evals at {os.path.relpath(p, ROOT)}", 2)
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("evals") or []


def next_iteration(ws):
    os.makedirs(ws, exist_ok=True)
    nums = [int(d.split("-")[1]) for d in os.listdir(ws) if re.match(r"^iteration-\d+$", d)]
    return os.path.join(ws, f"iteration-{max(nums, default=0) + 1}")


def run_prompt(runner, prompt_path, cwd, model, out, skill_dir):
    cmd = ["bash", runner, "--prompt-file", prompt_path, "--cwd", cwd, "--model", model, "--out", out]
    if skill_dir:
        cmd += ["--skill-dir", skill_dir]
    r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        with open(os.path.join(out, "error.log"), "w", encoding="utf-8") as f:
            f.write(r.stdout + "\n" + r.stderr)
        return False
    return True


def snapshot(cwd, before):
    files = {}
    for dp, _, fns in os.walk(cwd):
        # Match whole folder names: "/.git" as a substring would also skip ".github".
        if {".claude", ".agents", "node_modules", ".git"} & set(os.path.relpath(dp, cwd).split(os.sep)):
            continue
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, cwd)
            try:
                mtime = os.path.getmtime(p)
            except OSError:
                continue
            if rel not in before or before[rel] != mtime:
                files[rel] = mtime
    return files


def isolate_git(cwd):
    """Give the case its own repository, so git commands in a run stay inside it.

    Without one, `git add -A` or `git commit` from the case folder reaches the enclosing
    repository (the workbench itself) and commits whatever is uncommitted there.
    """
    if os.path.isdir(os.path.join(cwd, ".git")):
        return
    env = dict(os.environ, GIT_AUTHOR_NAME="eval", GIT_AUTHOR_EMAIL="eval@localhost",
               GIT_COMMITTER_NAME="eval", GIT_COMMITTER_EMAIL="eval@localhost")
    for args in (["init", "-q"], ["add", "-A"], ["-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", "fixture"]):
        subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)


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


def grade(runner, grader, run_dir, case, response, changed_files):
    with open(GRADING_TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    files_blob = "\n".join(f"### {p}\n{shown(os.path.join(run_dir, 'cwd', p))}" for p in sorted(changed_files)) or "(none)"
    assertions = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(case.get("assertions") or []))
    prompt = tpl.replace("{prompt}", case["prompt"]).replace("{response}", response).replace("{files}", files_blob).replace("{assertions}", assertions)
    gdir = os.path.join(run_dir, "grading")
    os.makedirs(os.path.join(gdir, "cwd"), exist_ok=True)
    os.makedirs(os.path.join(gdir, "out"), exist_ok=True)
    gp = os.path.join(gdir, "prompt.md")
    with open(gp, "w", encoding="utf-8") as f:
        f.write(prompt)
    if not run_prompt(runner, gp, os.path.join(gdir, "cwd"), grader, os.path.join(gdir, "out"), None):
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
    cases = load_cases(o["skill"])
    if o["cases"]:
        cases = [c for c in cases if str(c.get("id")) in o["cases"]]
    if not cases:
        die("no matching eval cases.")
    variants = ["with_skill", "without_skill"] if o["only"] is None else [f"{o['only']}_skill"]
    models = [("strong", o["model"])] + ([("floor", o["floor"])] if o["floor"] else [])
    if o["tiers"]:
        models = [m for m in models if m[0] in o["tiers"]]
        if not models:
            die("--tiers selected no model.")
    it_dir = next_iteration(os.path.join(ROOT, "evals-workspace", o["skill"]))
    plan = [{"case": c["id"], "variant": v, "model_tier": t, "model": m} for c in cases for v in variants for t, m in models]
    if o["dry"]:
        print(json.dumps({"dry_run": True, "iteration_dir": os.path.relpath(it_dir, ROOT), "runner": os.path.relpath(runner, ROOT), "floor_runner": os.path.relpath(floor_runner, ROOT),
                          "grader": o["grader"], "runs": plan}, indent=2))
        return 0

    failures = 0
    results = {}
    for c in cases:
        for v in variants:
            for tier, model in models:
                name = v if tier == "strong" else f"{v}.floor"
                run_dir = os.path.join(it_dir, f"eval-{c['id']}", name)
                cwd, out = os.path.join(run_dir, "cwd"), os.path.join(run_dir, "outputs")
                os.makedirs(cwd, exist_ok=True)
                os.makedirs(out, exist_ok=True)
                for rel in c.get("files") or []:
                    src = os.path.join(skill_dir, rel)
                    if os.path.isdir(src):
                        shutil.copytree(src, cwd, dirs_exist_ok=True)
                    elif os.path.isfile(src):
                        shutil.copy(src, cwd)
                isolate_git(cwd)
                pp = os.path.join(run_dir, "prompt.md")
                with open(pp, "w", encoding="utf-8") as f:
                    f.write(c["prompt"])
                before = file_index(cwd)
                ok = run_prompt(runner_for[tier], pp, cwd, model, out, skill_dir if v == "with_skill" else None)
                if not ok:
                    failures += 1
                    print(f"RUN FAILED  case {c['id']} {name}: see {os.path.relpath(os.path.join(out, 'error.log'), ROOT)}", file=sys.stderr)
                    continue
                changed = snapshot(cwd, before)
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
                    g = grade(runner, o["grader"], run_dir, c, response, changed)
                    if g is None:
                        failures += 1
                        print(f"GRADE FAILED case {c['id']} {name}", file=sys.stderr)
                    else:
                        with open(os.path.join(run_dir, "grading.json"), "w", encoding="utf-8") as f:
                            json.dump(g, f, indent=2)
                results.setdefault(name, []).append({"case": c["id"], "pass_rate": g["summary"]["pass_rate"] if g else None,
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
    bench = {"skill": o["skill"], "harness": o["harness"], "floor_harness": o["floor_harness"] or o["harness"], "models": dict(models), "grader": o["grader"], "threshold": o["threshold"],
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
