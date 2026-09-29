#!/usr/bin/env bash
# Eval contract: run one prompt through Claude Code non-interactively.
#
# Usage: run-prompt.sh --prompt-file <f> --cwd <dir> --model <id> --out <dir> [--skill-dir <dir>]
#                      [--extra-skill-dir <dir>]... [--allow-command <prefix>]... [--allow-web] [--max-cost-usd <amount>]
#
# Writes <out>/response.md and <out>/timing.json. --skill-dir (the skill under test) and each
# --extra-skill-dir (a case's dependencies, a flow's phases) are copied, never linked, into
# <cwd>/.claude/skills/<name>, so they are discoverable at project scope and a run cannot edit the
# workbench. Settings are limited to the project scope so user-level skills do not leak into a
# without-skill run; a case folder that already holds .claude/ or .mcp.json (from a fixture or a
# setup) is refused, since the project scope would apply its rules, hooks or servers.
# No MCP servers or claude.ai connectors are loaded (--strict-mcp-config, ENABLE_CLAUDEAI_MCP_SERVERS=false).
# Each --allow-command becomes a Bash(<prefix> *) rule in --allowedTools, and so does every script in
# the skill's scripts/ folder; any other command is denied (print mode cannot ask) and reported in
# raw.json's permission_denials. A prefix containing ( ) , or * is refused (it would add rules).
# acceptEdits still lets file commands (touch, mkdir) run inside --cwd.
# --allow-web adds WebSearch and WebFetch to --allowedTools, for a case that must search the web;
# without it print mode denies both.
# --max-cost-usd becomes claude's --max-budget-usd: the run stops once it has spent that much.
# Extra CLI flags: CLAUDE_EVAL_ARGS (default: --permission-mode acceptEdits).
# A proxy for floor models: pass ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN (eval_run.py --pass-env).
set -euo pipefail
PROMPT="" CWD="" MODEL="" OUT="" SKILL_DIR="" ALLOW="" MAX_COST=""
EXTRA_SKILLS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt-file) PROMPT="$2"; shift 2 ;;
    --cwd) CWD="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --skill-dir) SKILL_DIR="$2"; shift 2 ;;
    --extra-skill-dir) EXTRA_SKILLS+=("$2"); shift 2 ;;
    --allow-command)
      [[ "$2" == *[\(\),\*]* ]] && { echo "Error: --allow-command '$2' contains ( ) , or *, which would add permission rules." >&2; exit 2; }
      ALLOW="${ALLOW:+$ALLOW,}Bash($2 *)"; shift 2 ;;
    --allow-web) ALLOW="${ALLOW:+$ALLOW,}WebSearch,WebFetch"; shift ;;
    --max-cost-usd)
      [[ "$2" =~ ^[0-9]+(\.[0-9]+)?$ ]] || { echo "Error: --max-cost-usd needs a number, e.g. 0.50." >&2; exit 2; }
      MAX_COST="$2"; shift 2 ;;
    --help|-h) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
[[ -f "$PROMPT" && -d "$CWD" && -n "$MODEL" && -n "$OUT" ]] || { echo "Error: --prompt-file, --cwd, --model and --out are required. See --help." >&2; exit 2; }
command -v claude >/dev/null || { echo "Error: 'claude' CLI not found on PATH." >&2; exit 1; }
FOUND="$(find "$CWD" -path "$CWD/.git" -prune -o \( -name .claude -o -name .mcp.json \) -print -quit)"
[[ -z "$FOUND" ]] || { echo "Error: the case folder already holds ${FOUND#"$CWD"/}; a fixture or setup must not carry harness settings." >&2; exit 2; }
mkdir -p "$OUT"
install_skill() {
  local src dest
  src="$(cd "$1" && pwd)"; dest="$CWD/.claude/skills/$(basename "$src")"
  mkdir -p "$CWD/.claude/skills"
  rm -rf "${dest:?}"
  cp -RL "$src" "$dest"   # -L: a link inside the skill is copied as its content, never kept pointing back
  rm -rf "${dest:?}/evals"   # the cases, their fixtures and assertions: the model under test never reads them
}
[[ -n "$SKILL_DIR" ]] && install_skill "$SKILL_DIR"
for d in ${EXTRA_SKILLS[@]+"${EXTRA_SKILLS[@]}"}; do install_skill "$d"; done
# Skills link the workbench's shared references as ../../shared/references/<file>: copy them beside
# the installed skills so those links resolve inside the case folder too.
WORKBENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -d "$CWD/.claude/skills" && -d "$WORKBENCH/shared" ]]; then
  rm -rf "${CWD:?}/.claude/shared"
  cp -RL "$WORKBENCH/shared" "$CWD/.claude/shared"
fi
if [[ -n "$SKILL_DIR" && -d "$SKILL_DIR/scripts" ]]; then
  # The skill's own scripts, by the path the model sees (relative to the case folder).
  REL=".claude/skills/$(basename "$SKILL_DIR")/scripts"
  for f in "$SKILL_DIR"/scripts/*; do
    [[ -f "$f" ]] || continue
    # Both the relative path and the absolute one: models write either.
    # A folder path with ( ) , or * would break the rule syntax: then only the relative path is allowed.
    ABS=""; [[ "$CWD" == *[\(\),\*]* ]] || ABS="$CWD/$REL/$(basename "$f")"
    for script in "$REL/$(basename "$f")" ${ABS:+"$ABS"}; do
      for runner in bash python3; do ALLOW="${ALLOW:+$ALLOW,}Bash($runner $script),Bash($runner $script *)"; done
    done
  done
fi
START=$(python3 -c 'import time; print(int(time.time()*1000))')
set +e
EXTRA=(); [[ -n "$ALLOW" ]] && EXTRA=(--allowedTools "$ALLOW")
[[ -n "$MAX_COST" ]] && EXTRA+=(--max-budget-usd "$MAX_COST")
# Connectors: https://code.claude.com/docs/en/mcp (read 2026-09-27): claude.ai connectors load when logged in
# with a claude.ai account unless ENABLE_CLAUDEAI_MCP_SERVERS=false, and `claude -p` loads project servers
# without asking unless --strict-mcp-config (checked in `claude --help`, 2.1.283).
( cd "$CWD" && ENABLE_CLAUDEAI_MCP_SERVERS=false claude -p "$(cat "$PROMPT")" --model "$MODEL" --output-format json \
    --setting-sources project,local --strict-mcp-config ${CLAUDE_EVAL_ARGS:---permission-mode acceptEdits} ${EXTRA[@]+"${EXTRA[@]}"} ) \
  < /dev/null > "$OUT/raw.json" 2> "$OUT/stderr.log"
RC=$?
set -e
END=$(python3 -c 'import time; print(int(time.time()*1000))')
python3 - "$OUT" "$START" "$END" "$RC" <<'PY'
import json, sys, os
out, start, end, rc = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
raw = open(os.path.join(out, "raw.json"), encoding="utf-8", errors="ignore").read()
text, tokens, cost, dur = raw, None, None, end - start
try:
    d = json.loads(raw)
    if isinstance(d, list):
        d = next((x for x in d if x.get("type") == "result"), d[-1] if d else {})
    text = d.get("result") or text
    u = d.get("usage") or {}
    if u:
        tokens = sum(int(u.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    cost = d.get("total_cost_usd")
    dur = d.get("duration_ms") or dur
except ValueError:
    pass
open(os.path.join(out, "response.md"), "w", encoding="utf-8").write(text if isinstance(text, str) else json.dumps(text))
json.dump({"total_tokens": tokens, "duration_ms": dur, "cost_usd": cost, "exit_code": rc}, open(os.path.join(out, "timing.json"), "w"))
sys.exit(0 if rc == 0 else 1)
PY
