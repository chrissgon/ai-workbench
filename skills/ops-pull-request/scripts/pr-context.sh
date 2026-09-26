#!/usr/bin/env bash
# Collect what a pull request needs to be written, as JSON on stdout.
#
# Usage: bash pr-context.sh [--base <branch>] [--help]
#
# Prints: repository root, current branch, base branch (the remote's default, else main or
# master), the commits the branch adds, the files it changes, whether it is pushed, the pull
# request template (path and content, first found in the usual places), the last base commits
# (to read the commit convention), the lines of AGENTS.md or CONTRIBUTING.md about merging, and
# an open pull request for the branch when the GitHub CLI can tell.
set -euo pipefail
BASE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) BASE="$2"; shift 2 ;;
    --help|-h) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
BRANCH=$(git branch --show-current)
if [[ -z "$BASE" ]]; then
  BASE=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || true)
  [[ -z "$BASE" ]] && for b in main master; do git show-ref --verify --quiet "refs/heads/$b" && { BASE=$b; break; }; done
fi
TEMPLATE=""
for f in .github/pull_request_template.md .github/PULL_REQUEST_TEMPLATE.md PULL_REQUEST_TEMPLATE.md docs/pull_request_template.md; do
  [[ -f "$f" ]] && { TEMPLATE=$f; break; }
done
PUSHED=false
git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1 && PUSHED=true
OPEN_PR=""
command -v gh >/dev/null && OPEN_PR=$(gh pr list --head "$BRANCH" --json url --jq '.[0].url' 2>/dev/null || true)
python3 - "$ROOT" "$BRANCH" "$BASE" "$TEMPLATE" "$PUSHED" "$OPEN_PR" <<'PY'
import json, os, subprocess, sys
root, branch, base, template, pushed, open_pr = sys.argv[1:]
git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()
rules = []
for doc in ("AGENTS.md", "CONTRIBUTING.md"):
    if os.path.isfile(doc):
        rules += [f"{doc}: {l.strip()}" for l in open(doc, encoding="utf-8") if any(w in l.lower() for w in ("merge", "squash", "rebase", "commit"))]
print(json.dumps({
    "root": root,
    "branch": branch,
    "base": base,
    "commits": git("log", "--format=%h %s", f"{base}..HEAD").splitlines() if base else [],
    "files": git("diff", "--name-status", f"{base}...HEAD").splitlines() if base else [],
    "pushed": pushed == "true",
    "open_pull_request": open_pr or None,
    "template": {"path": template, "content": open(template, encoding="utf-8").read()} if template else None,
    "base_history": git("log", "--format=%s", "-8", base).splitlines() if base else [],
    "merge_rules": rules,
}, indent=2))
PY
