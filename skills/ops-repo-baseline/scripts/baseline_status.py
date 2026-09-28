#!/usr/bin/env python3
"""Report which parts of the repository security baseline a project already has. Reads only.

Usage: python3 baseline_status.py [--root DIR]

Prints one JSON object:
  ecosystems[]        package ecosystems found (for dependabot.yml): npm, pip, gomod, cargo, bundler,
                      composer, docker, github-actions; each with the folders that hold its manifests
                      (in a git repository, only files git sees: ignored folders are skipped)
  files               ci_workflows[], codeowners (path or null), dependabot (path or null),
                      security_policy (path or null), pre_commit_hook (path or null), secret_scan (path or
                      null), env_ignored (true when .gitignore ignores .env)
  workflows[]         per workflow: path, declares_permissions (a top-level permissions: key),
                      unpinned_actions (uses: lines not pinned to a 40-character commit)
  git                 is_repo, remotes[], hooks_path, commit_signing (commit.gpgsign), signing_format
                      (gpg.format), commits (count on HEAD, 0 when none)
  agents_md           true when AGENTS.md exists (its commands name the checks CI must run)
Exit codes: 0 ok, 2 usage error.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

MANIFESTS = {
    "npm": ("package.json",),
    "pip": ("pyproject.toml", "requirements.txt", "setup.py", "Pipfile"),
    "gomod": ("go.mod",),
    "cargo": ("Cargo.toml",),
    "bundler": ("Gemfile",),
    "composer": ("composer.json",),
    "docker": ("Dockerfile",),
}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "vendor", "dist", "build", ".next", ".nuxt", ".output", "target"}
USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)")
PINNED_RE = re.compile(r"@[0-9a-f]{40}$")


def git(root, *args):
    try:
        r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def first(root, *names):
    for name in names:
        if os.path.isfile(os.path.join(root, name)):
            return name
    return None


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    root = "."
    if argv:
        if len(argv) != 2 or argv[0] != "--root":
            print("error: usage: baseline_status.py [--root DIR]", file=sys.stderr)
            return 2
        root = argv[1]
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        print(f"error: {root} is not a folder", file=sys.stderr)
        return 2

    # In a git repository, the files git sees (tracked, or untracked and not ignored); otherwise a walk.
    listed = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if listed is not None:
        paths = [p for p in listed.split("\0") if p]
    else:
        paths = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".") or d == ".github"]
            paths += [os.path.relpath(os.path.join(dirpath, f), root).replace(os.sep, "/") for f in filenames]
    ecosystems = {}
    for rel in paths:
        parts = rel.split("/")
        if any(p in SKIP_DIRS for p in parts[:-1]):
            continue
        name, folder = parts[-1], "/" + "/".join(parts[:-1])
        for eco, names in MANIFESTS.items():
            if name in names or (eco == "pip" and name.startswith("requirements") and name.endswith(".txt")):
                ecosystems.setdefault(eco, []).append(folder)

    wf_dir = os.path.join(root, ".github", "workflows")
    workflows = []
    if os.path.isdir(wf_dir):
        for name in sorted(os.listdir(wf_dir)):
            if not name.endswith((".yml", ".yaml")):
                continue
            text = open(os.path.join(wf_dir, name), encoding="utf-8", errors="replace").read()
            unpinned = [m.group(1) for line in text.splitlines() if (m := USES_RE.match(line))
                        and not m.group(1).startswith("./") and not PINNED_RE.search(m.group(1))]
            workflows.append({"path": f".github/workflows/{name}",
                              "declares_permissions": bool(re.search(r"(?m)^permissions:", text)),
                              "unpinned_actions": unpinned})
    if workflows:
        ecosystems.setdefault("github-actions", ["/"])

    gitignore = os.path.join(root, ".gitignore")
    env_ignored = os.path.isfile(gitignore) and bool(
        re.search(r"(?m)^\s*/?\.env(\*|\.\*)?\s*$", open(gitignore, encoding="utf-8", errors="replace").read()))
    is_repo = git(root, "rev-parse", "--is-inside-work-tree") == "true"
    report = {
        "root": root,
        "ecosystems": [{"name": k, "folders": sorted(set(v))} for k, v in sorted(ecosystems.items())],
        "files": {
            "ci_workflows": [w["path"] for w in workflows],
            "codeowners": first(root, ".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"),
            "dependabot": first(root, ".github/dependabot.yml", ".github/dependabot.yaml"),
            "security_policy": first(root, "SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"),
            "pre_commit_hook": first(root, ".githooks/pre-commit"),
            "secret_scan": first(root, "scripts/secret-scan/secret_scan.py"),
            "env_ignored": env_ignored,
        },
        "workflows": workflows,
        "git": {
            "is_repo": is_repo,
            "remotes": (git(root, "remote") or "").split() if is_repo else [],
            "hooks_path": git(root, "config", "--get", "core.hooksPath") if is_repo else None,
            "commit_signing": git(root, "config", "--get", "commit.gpgsign") if is_repo else None,
            "signing_format": git(root, "config", "--get", "gpg.format") if is_repo else None,
            "commits": int(git(root, "rev-list", "--count", "HEAD") or 0) if is_repo else 0,
        },
        "agents_md": os.path.isfile(os.path.join(root, "AGENTS.md")),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
