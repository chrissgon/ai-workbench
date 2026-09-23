#!/usr/bin/env python3
"""Detect a project's tooling facts and audit an AGENTS.md against them.

Usage:
  python3 audit_agents_md.py --root <dir> --detect
  python3 audit_agents_md.py --root <dir> --audit <path-to-AGENTS.md> [--baseline <path>]

--detect  prints JSON: manifests and scripts, Makefile targets, lint/format/type configs, test
          frameworks and folders, CI and deploy files, root documents, instruction-like files,
          and the existing AGENTS.md sections plus whether it has the workbench section.
--audit   checks every backticked command against package scripts, Makefile targets and
          binaries (PATH or node_modules/.bin), and every backticked path against the filesystem.
          With --baseline <path> (a copy of the previous AGENTS.md), also reports whether the
          workbench section is byte-identical. Exit 1 when the audit finds problems.

Exit codes: 0 ok, 1 audit problems, 2 usage error.
"""
import json
import os
import re
import sys

MANIFESTS = ("package.json", "pyproject.toml", "go.mod", "Cargo.toml", "composer.json", "Gemfile", "Makefile")
CONFIG_PATTERNS = {
    "lint": (r"^\.?eslint", r"^\.oxlintrc", r"^biome\.json", r"^ruff\.toml", r"^\.golangci", r"^\.rubocop", r"^\.stylelintrc"),
    "format": (r"^\.prettierrc", r"^\.oxfmtrc", r"^\.editorconfig", r"^rustfmt\.toml"),
    "types": (r"^tsconfig", r"^mypy\.ini", r"^pyrightconfig"),
    "tests": (r"^vitest\.config", r"^jest\.config", r"^playwright\.config", r"^pytest\.ini", r"^cypress\.config", r"^karma\.conf"),
    "commits": (r"^commitlint", r"^\.commitlintrc", r"^\.husky$", r"^lefthook", r"^\.pre-commit-config"),
    "ci_deploy": (r"^\.github$", r"^\.gitlab-ci\.yml", r"^netlify\.toml", r"^vercel\.json", r"^Dockerfile", r"^docker-compose", r"^fly\.toml", r"^render\.yaml"),
}
TEST_DIRS = ("test", "tests", "__tests__", "e2e", "spec", "cypress")
EXCLUDED_STEMS = {"README", "LICENSE", "CHANGELOG", "CONTRIBUTING", "CODE_OF_CONDUCT", "SECURITY", "AGENTS"}
INSTRUCTION_HEADINGS = ("always", "never", "rules", "hard rules", "communication", "do", "don't", "workflow")
RUNNERS = {"npm run", "npm", "bun run", "bun", "pnpm run", "pnpm", "yarn run", "yarn"}
START, END = "<!-- workbench:start -->", "<!-- workbench:end -->"


def looks_like_instructions(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            head = f.read(6000)
    except OSError:
        return False
    first_heading = next((l for l in head.splitlines() if l.startswith("#")), "")
    if re.search(r"\binstructions?\b", first_heading, re.I):
        return True
    headings = [l.strip("# ").strip().lower() for l in head.splitlines() if l.startswith("## ")]
    return sum(1 for h in headings if h in INSTRUCTION_HEADINGS) >= 2


def package_scripts(root):
    p = os.path.join(root, "package.json")
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return {"name": data.get("name"), "description": data.get("description"), "scripts": data.get("scripts") or {},
            "packageManager": data.get("packageManager")}


def makefile_targets(root):
    p = os.path.join(root, "Makefile")
    if not os.path.isfile(p):
        return []
    with open(p, encoding="utf-8", errors="ignore") as f:
        return sorted({m.group(1) for m in re.finditer(r"^([A-Za-z0-9_.-]+):", f.read(), re.M)})


def lockfile(root):
    for fn, cmd in (("bun.lock", "bun install"), ("bun.lockb", "bun install"), ("pnpm-lock.yaml", "pnpm install"),
                    ("yarn.lock", "yarn install"), ("package-lock.json", "npm ci"), ("poetry.lock", "poetry install"),
                    ("uv.lock", "uv sync"), ("Cargo.lock", "cargo build"), ("go.sum", "go mod download")):
        if os.path.isfile(os.path.join(root, fn)):
            return {"file": fn, "install": cmd}
    return None


def detect(root):
    entries = sorted(os.listdir(root))
    configs = {k: [] for k in CONFIG_PATTERNS}
    for e in entries:
        for kind, pats in CONFIG_PATTERNS.items():
            if any(re.search(p, e) for p in pats):
                configs[kind].append(e)
    ci_files = []
    wf = os.path.join(root, ".github", "workflows")
    if os.path.isdir(wf):
        ci_files = [os.path.join(".github/workflows", f) for f in sorted(os.listdir(wf)) if f.endswith((".yml", ".yaml"))]
    root_docs, instruction_like = [], []
    for e in entries:
        if e.lower().endswith(".md") and os.path.isfile(os.path.join(root, e)):
            stem = e[:-3]
            if stem.upper() in EXCLUDED_STEMS or stem.upper().startswith("README"):
                continue
            if stem == stem.upper():
                (instruction_like if looks_like_instructions(os.path.join(root, e)) else root_docs).append(e)
    agents = os.path.join(root, "AGENTS.md")
    agents_info = {"exists": False, "sections": [], "has_workbench_section": False, "lines": 0}
    if os.path.isfile(agents):
        with open(agents, encoding="utf-8") as f:
            text = f.read()
        agents_info = {"exists": True, "sections": re.findall(r"^## (.+)$", text, re.M),
                       "has_workbench_section": START in text and END in text, "lines": text.count("\n") + 1}
    return {
        "root": os.path.abspath(root),
        "manifests": [m for m in MANIFESTS if os.path.isfile(os.path.join(root, m))],
        "package": package_scripts(root),
        "makefile_targets": makefile_targets(root),
        "lockfile": lockfile(root),
        "configs": configs,
        "ci_workflows": ci_files,
        "test_dirs": [d for d in TEST_DIRS if os.path.isdir(os.path.join(root, d))],
        "root_docs": root_docs,
        "instruction_like": instruction_like,
        "agents_md": agents_info,
    }


def known_binaries(root):
    bins = set()
    nb = os.path.join(root, "node_modules", ".bin")
    if os.path.isdir(nb):
        bins.update(os.listdir(nb))
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if os.path.isdir(d):
            try:
                bins.update(os.listdir(d))
            except OSError:
                pass
    return bins


def audit(root, agents_path, baseline):
    with open(agents_path, encoding="utf-8") as f:
        text = f.read()
    scripts = set((package_scripts(root).get("scripts") or {}).keys())
    targets = set(makefile_targets(root))
    bins = known_binaries(root)
    unknown_commands, missing_paths, checked = [], [], 0
    for span in re.findall(r"`([^`\n]+)`", text):
        s = span.strip()
        parts = s.split()
        if not parts:
            continue
        first = parts[0]
        if first in ("npm", "bun", "pnpm", "yarn"):
            rest = parts[1:]
            if rest and rest[0] == "run":
                rest = rest[1:]
            if rest and rest[0] in ("install", "ci", "i", "add", "test", "x", "exec", "dlx", "create", "prepare"):
                checked += 1
                continue
            if rest:
                checked += 1
                if rest[0] not in scripts:
                    unknown_commands.append(s)
            continue
        if first == "make":
            checked += 1
            if len(parts) > 1 and parts[1] not in targets:
                unknown_commands.append(s)
            continue
        if first in ("python", "python3", "node", "go", "cargo", "uv", "poetry", "docker", "git", "bash", "sh", "npx"):
            checked += 1
            continue
        if re.match(r"^[A-Za-z0-9_.-]+$", first) and len(parts) > 1 and first in bins:
            checked += 1
            continue
        if ("/" in s or s.endswith((".md", ".json", ".ts", ".js", ".yml", ".yaml", ".toml", ".css"))) and " " not in s and not s.startswith(("http", "{", "<", "pui-", "-", "@", ".")):
            target = s.split("#")[0].rstrip("/")
            if target and not os.path.exists(os.path.join(root, target)):
                missing_paths.append(s)
    section_state = "not checked"
    if baseline:
        with open(baseline, encoding="utf-8") as f:
            old = f.read()
        def section(t):
            return t[t.index(START): t.index(END) + len(END)] if START in t and END in t else None
        a, b = section(old), section(text)
        section_state = "unchanged" if a == b else ("missing" if b is None else "CHANGED")
    ok = not unknown_commands and not missing_paths and section_state != "CHANGED" and section_state != "missing"
    result = {"ok": ok, "commands_checked": checked, "unknown_commands": unknown_commands,
              "missing_paths": missing_paths, "workbench_section": section_state,
              "lines": text.count("\n") + 1}
    print(json.dumps(result, indent=2))
    return 0 if ok else 1


def main(argv):
    if not argv or "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0 if argv else 2
    root, mode, target, baseline = ".", None, None, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--root":
            root = argv[i + 1] if i + 1 < len(argv) else None
            i += 2
        elif a == "--detect":
            mode = "detect"
            i += 1
        elif a == "--audit":
            mode, target = "audit", (argv[i + 1] if i + 1 < len(argv) else None)
            i += 2
        elif a == "--baseline":
            baseline = argv[i + 1] if i + 1 < len(argv) else None
            i += 2
        else:
            print(f"Error: unknown option {a!r}. See --help.", file=sys.stderr)
            return 2
    if not root or not os.path.isdir(root):
        print(f"Error: --root {root!r} is not a directory.", file=sys.stderr)
        return 2
    if mode == "detect":
        print(json.dumps(detect(root), indent=2))
        return 0
    if mode == "audit":
        if not target or not os.path.isfile(target):
            print("Error: --audit needs the path to an existing AGENTS.md.", file=sys.stderr)
            return 2
        if baseline and not os.path.isfile(baseline):
            print(f"Error: --baseline {baseline!r} not found.", file=sys.stderr)
            return 2
        return audit(root, target, baseline)
    print("Error: pass --detect or --audit <file>. See --help.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
