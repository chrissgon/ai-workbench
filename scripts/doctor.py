#!/usr/bin/env python3
"""Report which environment requirement classes are satisfied.

Usage: python3 scripts/doctor.py [--harness <name>] [--json] [--strict]

Collects `metadata.requires` from every skill, then checks each class against:
  1. connectors declared by the chosen adapter in adapters/<harness>/connectors.json
     ({"classes": {"integration:issue-tracker": "mcp: atlassian"}})
  2. a native provider selected by <CLASS>_<SUBCLASS>_PROVIDER or <CLASS>_PROVIDER, whose
     script exists under providers/ and passes `--check`

Options:
  --harness <name>  include connectors declared by that adapter
  --json            machine-readable report on stdout
  --strict          exit 1 when any required class is missing
  --help            show this text

Exit codes: 0 ok, 1 missing classes with --strict, 2 usage error.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from validate import load_yaml, split_frontmatter  # noqa: E402

SKILLS = os.path.join(ROOT, "skills")
PROVIDERS = os.path.join(ROOT, "providers")
ADAPTERS = os.path.join(ROOT, "adapters")


def collect_requires():
    req = {}
    if not os.path.isdir(SKILLS):
        return req
    for d in sorted(os.listdir(SKILLS)):
        p = os.path.join(SKILLS, d, "SKILL.md")
        if not os.path.isfile(p):
            continue
        fm_text, _ = split_frontmatter(p)
        if fm_text is None:
            continue
        try:
            meta = (load_yaml(fm_text) or {}).get("metadata") or {}
        except Exception:  # noqa: BLE001
            continue
        for cls in meta.get("requires") or []:
            req.setdefault(cls, []).append(d)
    return req


def env_provider(cls):
    parts = cls.split(":")
    keys = ["_".join(parts).upper() + "_PROVIDER", parts[0].upper() + "_PROVIDER"]
    for k in keys:
        if os.environ.get(k):
            return k, os.environ[k]
    return None, None


def check_provider(cls, impl):
    script = os.path.join(PROVIDERS, cls.split(":")[0], f"{impl}.py")
    if not os.path.isfile(script):
        return "missing", f"{os.path.relpath(script, ROOT)} not found"
    runner = ["uv", "run", script] if _which("uv") else ["python3", script]
    try:
        r = subprocess.run(runner + ["--check"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return "missing", f"--check failed to run: {e}"
    if r.returncode == 0:
        return "provider", os.path.relpath(script, ROOT)
    return "missing", f"--check exit {r.returncode}: {(r.stderr or r.stdout).strip()[:200]}"


def _which(name):
    for p in os.environ.get("PATH", "").split(os.pathsep):
        if os.path.isfile(os.path.join(p, name)):
            return True
    return False


def load_connectors(harness):
    if not harness:
        return {}
    p = os.path.join(ADAPTERS, harness, "connectors.json")
    if not os.path.isfile(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return (json.load(f) or {}).get("classes") or {}


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    harness, as_json, strict = None, "--json" in argv, "--strict" in argv
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--harness":
            if i + 1 >= len(argv):
                print("Error: --harness needs a value, e.g. --harness claude-code", file=sys.stderr)
                return 2
            harness = argv[i + 1]
            i += 2
            continue
        if a not in ("--json", "--strict"):
            print(f"Error: unknown option {a!r}. See --help.", file=sys.stderr)
            return 2
        i += 1
    if harness and not os.path.isdir(os.path.join(ADAPTERS, harness)):
        print(f"Error: adapter {harness!r} not found under adapters/.", file=sys.stderr)
        return 2

    connectors = load_connectors(harness)
    report, missing = {}, 0
    for cls, skills in sorted(collect_requires().items()):
        if cls in connectors:
            status, detail = "connector", connectors[cls]
        else:
            var, impl = env_provider(cls)
            if impl:
                status, detail = check_provider(cls, impl)
                detail = f"{var}={impl}: {detail}"
            else:
                status, detail = "missing", "no connector declared and no <CLASS>_PROVIDER set"
        if status == "missing":
            missing += 1
        report[cls] = {"status": status, "detail": detail, "skills": skills}

    if as_json:
        print(json.dumps({"harness": harness, "classes": report, "missing": missing}, indent=2))
    else:
        for cls, r in report.items():
            print(f"{r['status']:<9} {cls:<28} {r['detail']}  <- {', '.join(r['skills'])}", file=sys.stderr)
        print(json.dumps({"harness": harness, "classes": len(report), "missing": missing}))
    return 1 if (strict and missing) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
