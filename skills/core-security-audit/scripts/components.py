#!/usr/bin/env python3
"""List the components a security audit must cover, and split them into slices.

Usage:
  python3 components.py --root <workbench root> [--slices 3]
  python3 components.py --skill <folder of one skill to vet>

Workbench mode lists every skill (with its area prefix), agent, agent override, provider class,
adapter, script, the git hooks and the CI workflows, each with its files. Skills are split into
slices by area prefix, balanced by file count; everything that is not a skill is its own last
slice. Skill mode lists the files of one skill folder, marking scripts and hidden files.

Prints JSON to stdout; diagnostics go to stderr. Exit 2 on a bad argument.
"""
import argparse
import json
import os
import sys

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "build"}
SCRIPT_EXT = (".py", ".sh", ".mjs", ".js", ".ts", ".rb", ".pl")


def files_under(base):
    out = []
    for dirpath, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.endswith("-workspace"))
        for f in sorted(files):
            out.append(os.path.relpath(os.path.join(dirpath, f), base))
    return out


def rel(root, path):
    return os.path.relpath(path, root)


def workbench(root, slices):
    comps = []
    sk = os.path.join(root, "skills")
    for name in sorted(os.listdir(sk)) if os.path.isdir(sk) else []:
        d = os.path.join(sk, name)
        if os.path.isfile(os.path.join(d, "SKILL.md")):
            fs = files_under(d)
            comps.append({"kind": "skill", "name": name, "prefix": name.split("-")[0],
                          "path": rel(root, d), "files": len(fs),
                          "scripts": [f for f in fs if f.endswith(SCRIPT_EXT)]})
    for kind, sub, pred in (
        ("agent", "agents", lambda p: p.endswith(".md") and os.path.basename(p) != "README.md"),
        ("script", "scripts", lambda p: p.endswith(SCRIPT_EXT) and os.sep + "tests" + os.sep not in os.sep + p),
        ("hook", ".githooks", lambda p: True),
        ("ci", os.path.join(".github", "workflows"), lambda p: True),
    ):
        base = os.path.join(root, sub)
        if os.path.isdir(base):
            for f in files_under(base):
                if pred(f):
                    comps.append({"kind": kind, "name": f, "path": rel(root, os.path.join(base, f)), "files": 1})
    for kind, sub in (("provider", "providers"), ("adapter", "adapters")):
        base = os.path.join(root, sub)
        for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            d = os.path.join(base, name)
            if os.path.isdir(d) and name not in SKIP_DIRS:
                comps.append({"kind": kind, "name": name, "path": rel(root, d), "files": len(files_under(d))})
                ov = os.path.join(d, "overrides")
                if kind == "adapter" and os.path.isdir(ov):
                    for f in files_under(ov):
                        if f.endswith((".yaml", ".yml", ".json")):
                            comps.append({"kind": "agent-override", "name": f"{name}/{f}",
                                          "path": rel(root, os.path.join(ov, f)), "files": 1})

    skills = [c for c in comps if c["kind"] == "skill"]
    by_prefix = {}
    for c in skills:
        by_prefix.setdefault(c["prefix"], []).append(c["name"])
    weight = {p: sum(c["files"] for c in skills if c["prefix"] == p) for p in by_prefix}
    n = max(1, slices - 1) if len(comps) > len(skills) else max(1, slices)
    buckets = [{"prefixes": [], "skills": [], "files": 0} for _ in range(min(n, max(1, len(by_prefix))))]
    for p in sorted(by_prefix, key=lambda p: (-weight[p], p)):
        b = min(buckets, key=lambda b: b["files"])
        b["prefixes"].append(p)
        b["skills"] += by_prefix[p]
        b["files"] += weight[p]
    out_slices = [{"id": chr(ord("A") + i), "components": b["skills"], "prefixes": sorted(b["prefixes"]),
                   "files": b["files"]} for i, b in enumerate(buckets)]
    rest = [c["path"] for c in comps if c["kind"] != "skill"]
    if rest:
        out_slices.append({"id": chr(ord("A") + len(out_slices)), "components": rest, "prefixes": [],
                           "files": sum(c["files"] for c in comps if c["kind"] != "skill")})
    counts = {}
    for c in comps:
        counts[c["kind"]] = counts.get(c["kind"], 0) + 1
    return {"mode": "workbench", "root": os.path.abspath(root), "counts": counts,
            "components": comps, "slices": out_slices}


def one_skill(folder):
    fs = files_under(folder)
    return {"mode": "skill", "root": os.path.abspath(folder),
            "has_skill_md": os.path.isfile(os.path.join(folder, "SKILL.md")),
            "files": fs,
            "scripts": [f for f in fs if f.endswith(SCRIPT_EXT)],
            "hidden": [f for f in fs if any(part.startswith(".") for part in f.split(os.sep))],
            "links": [f for f in fs if os.path.islink(os.path.join(folder, f))]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--root", help="workbench root to audit")
    g.add_argument("--skill", help="folder of one skill to vet before installing it")
    ap.add_argument("--slices", type=int, default=3, help="number of slices, the last one for non-skills (default 3)")
    a = ap.parse_args()
    path = a.root or a.skill
    if not os.path.isdir(path):
        print(f"not a folder: {path}", file=sys.stderr)
        return 2
    if a.slices < 1 or a.slices > 26:
        print("--slices must be between 1 and 26", file=sys.stderr)
        return 2
    json.dump(workbench(path, a.slices) if a.root else one_skill(path), sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
