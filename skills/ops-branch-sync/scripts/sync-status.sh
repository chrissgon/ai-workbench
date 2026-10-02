#!/usr/bin/env bash
# Report how a branch stands against the remote copy of its base, as JSON on stdout.
#
# Usage: bash sync-status.sh [--base <branch>] [--remote <name>] [--no-fetch] [--help]
#
# Fetches the remote (unless --no-fetch), then prints: the branch, the base, whether the local
# base is behind the remote base (a stale local base makes every comparison wrong), how many
# commits the branch is ahead of and behind the remote base, whether the branch is pushed and has
# an open pull request, uncommitted changes to tracked files, untracked files, files in conflict (during a merge), and which
# dependency manifests and lockfiles the base changed since the branch left it (reinstall after
# the sync when this list is not empty).
#
# A --base that is not a valid branch name (git check-ref-format --branch), or a --remote that is
# not a plain remote name, is refused with exit 2 before any git call uses it, so neither can be
# read as an option. The open pull request is asked of the code host's command-line tool only
# when it is installed.
set -euo pipefail
BASE=""; REMOTE=origin; FETCH=true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) [[ $# -ge 2 ]] || { echo "Error: --base needs a value. See --help." >&2; exit 2; }; BASE="$2"; shift 2 ;;
    --remote) [[ $# -ge 2 ]] || { echo "Error: --remote needs a value. See --help." >&2; exit 2; }; REMOTE="$2"; shift 2 ;;
    --no-fetch) FETCH=false; shift ;;
    --help|-h) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
valid_branch() { [[ -n "$1" && "$1" != -* ]] && git check-ref-format --branch "$1" >/dev/null 2>&1; }
if [[ -n "$BASE" ]] && ! valid_branch "$BASE"; then
  echo "Error: --base '$BASE' is not a branch name. See --help." >&2
  exit 2
fi
if ! [[ "$REMOTE" =~ ^[A-Za-z0-9_][A-Za-z0-9._-]*$ ]]; then
  echo "Error: --remote '$REMOTE' is not a remote name. See --help." >&2
  exit 2
fi
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
BRANCH=$(git branch --show-current)
FETCHED=false
if $FETCH && git remote get-url "$REMOTE" >/dev/null 2>&1; then
  git fetch --quiet --end-of-options "$REMOTE" && FETCHED=true
fi
if [[ -z "$BASE" ]]; then
  BASE=$(git symbolic-ref --quiet --short "refs/remotes/$REMOTE/HEAD" 2>/dev/null | sed "s#^$REMOTE/##" || true)
  [[ -z "$BASE" ]] && for b in main master; do
    git show-ref --verify --quiet "refs/remotes/$REMOTE/$b" && { BASE=$b; break; }
    git show-ref --verify --quiet "refs/heads/$b" && { BASE=$b; break; }
  done
  if [[ -n "$BASE" ]] && ! valid_branch "$BASE"; then BASE=""; fi
fi
OPEN_PR=""
command -v gh >/dev/null && OPEN_PR=$(gh pr list --head "$BRANCH" --json url --jq '.[0].url' 2>/dev/null || true)
python3 - "$ROOT" "$BRANCH" "$BASE" "$REMOTE" "$FETCHED" "$OPEN_PR" <<'PY'
import json, re, subprocess, sys
root, branch, base, remote, fetched, open_pr = sys.argv[1:]
def git(*a):
    r = subprocess.run(["git", *a], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""
remote_base = f"{remote}/{base}" if git("rev-parse", "--verify", "--quiet", f"refs/remotes/{remote}/{base}") else ""
target = remote_base or base
count = lambda rng: int(git("rev-list", "--count", rng) or 0)
local_base_behind = count(f"{base}..{remote_base}") if remote_base and git("rev-parse", "--verify", "--quiet", f"refs/heads/{base}") else 0
merge_base = git("merge-base", "HEAD", target)
MANIFESTS = re.compile(r"(^|/)(package\.json|bun\.lockb?|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|"
                       r"requirements[^/]*\.txt|poetry\.lock|uv\.lock|pyproject\.toml|Gemfile(\.lock)?|"
                       r"go\.(mod|sum)|Cargo\.(toml|lock)|composer\.(json|lock))$")
base_changed = git("diff", "--name-only", f"{merge_base}..{target}").splitlines() if merge_base else []
print(json.dumps({
    "root": root,
    "branch": branch,
    "base": base,
    "compared_with": target,
    "fetched": fetched == "true",
    "local_base_behind_remote": local_base_behind,
    "ahead": count(f"{target}..HEAD"),
    "behind": count(f"HEAD..{target}"),
    "pushed": bool(git("ls-remote", "--heads", remote, branch)),
    "open_pull_request": open_pr or None,
    "merging": bool(git("rev-parse", "--verify", "--quiet", "MERGE_HEAD")),
    "conflicted": git("diff", "--name-only", "--diff-filter=U").splitlines(),
    "uncommitted": [l for l in git("status", "--porcelain").splitlines() if not l.startswith("??")],
    "untracked": [l[3:] for l in git("status", "--porcelain").splitlines() if l.startswith("??")],
    "base_changed_dependencies": [f for f in base_changed if MANIFESTS.search(f)],
}, indent=2))
PY
