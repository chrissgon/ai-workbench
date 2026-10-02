#!/usr/bin/env bash
# Eval contract: run one prompt through Claude Code non-interactively, inside the eval container.
#
# Usage: run-prompt.sh --prompt-file <f> --cwd <dir> --model <id> --out <dir>
#                      [--allow-web] [--max-cost-usd <amount>]
#
# Writes <out>/response.md and <out>/timing.json. It installs nothing: the eval runner stages the
# skill under test and a case's dependency skills in <cwd>/.claude/skills/<name> before this script
# starts (the "eval" object of adapter.json names that folder; scripts/stage_skills.py copies them),
# so they are discoverable at project scope. Settings are limited to the project scope; the runner
# refuses a case folder that carries a name of adapter.json's "eval.settings" (.claude, .mcp.json or
# the project-instructions files CLAUDE.md and CLAUDE.local.md, from a fixture or a setup), since the
# project scope would apply its rules, hooks, servers or instructions.
# No MCP servers or claude.ai connectors are loaded (--strict-mcp-config, ENABLE_CLAUDEAI_MCP_SERVERS=false).
# It runs only inside the eval container (evals/executor.py; the image sets WB_EVAL_CONTAINER=1) and
# refuses to start anywhere else: the container is the boundary, so every tool is allowed
# (--dangerously-skip-permissions), which on a person's machine would let a model do anything.
# --allow-web leaves WebSearch and WebFetch available, for a case that must search the web; without it
# both are disallowed.
# --max-cost-usd becomes claude's --max-budget-usd: the run stops once it has spent that much.
# SLASH_COMMAND_TOOL_CHAR_BUDGET is raised (200000 unless set): the CLI lists skills to the model within a
# character budget, its own bundled skills first, and past the budget a project skill is listed by name
# only, with no description, so the model cannot tell when to use the skill under test.
# The CLI authenticates with CLAUDE_CODE_OAUTH_TOKEN (or ANTHROPIC_API_KEY) from the environment.
# Extra CLI flags: CLAUDE_EVAL_ARGS.
# The prompt reaches the CLI on standard input, not as an argument: a grading prompt with long files
# is larger than one argument may be.
# Stopping this script (TERM, INT, HUP) stops the CLI and everything it started.
set -euo pipefail
PROMPT="" CWD="" MODEL="" OUT="" WEB="" MAX_COST=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt-file) PROMPT="$2"; shift 2 ;;
    --cwd) CWD="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --allow-web) WEB=1; shift ;;
    --max-cost-usd)
      [[ "$2" =~ ^[0-9]+(\.[0-9]+)?$ ]] || { echo "Error: --max-cost-usd needs a number, e.g. 0.50." >&2; exit 2; }
      MAX_COST="$2"; shift 2 ;;
    --help|-h) sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
[[ -f "$PROMPT" && -d "$CWD" && -n "$MODEL" && -n "$OUT" ]] || { echo "Error: --prompt-file, --cwd, --model and --out are required. See --help." >&2; exit 2; }
[[ "${WB_EVAL_CONTAINER:-}" == "1" ]] || { echo "Error: this adapter allows a model every tool, so it runs only inside the container that evals/eval_run.py starts." >&2; exit 2; }
command -v claude >/dev/null || { echo "Error: 'claude' CLI not found on PATH." >&2; exit 1; }
mkdir -p "$OUT"
# The runner gets its own session, so everything it starts (model sessions, browsers) is one process group
# that can be stopped as a whole: when it exits, and when this script gets TERM, INT or HUP (a timeout or a
# stop of eval_run.py). Without it a stopped eval left model sessions working for minutes.
RUNNER_PID=""
stop_runner() {
  [[ -n "$RUNNER_PID" ]] || return 0
  kill -TERM -- "-$RUNNER_PID" 2>/dev/null || return 0
  for _ in 1 2 3 4 5 6 7 8 9 10; do kill -0 -- "-$RUNNER_PID" 2>/dev/null || return 0; sleep 0.2; done
  kill -KILL -- "-$RUNNER_PID" 2>/dev/null || true
}
# exec, so that the session leader is the background job itself and RUNNER_PID names its process group.
OWN_SESSION=(python3 -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])')
trap 'stop_runner; exit 143' TERM INT HUP
START=$(python3 -c 'import time; print(int(time.time()*1000))')
set +e
EXTRA=(--dangerously-skip-permissions)
[[ -n "$WEB" ]] || EXTRA+=(--disallowedTools "WebSearch,WebFetch")
[[ -n "$MAX_COST" ]] && EXTRA+=(--max-budget-usd "$MAX_COST")
# Connectors: https://code.claude.com/docs/en/mcp (read 2026-09-27): claude.ai connectors load when logged in
# with a claude.ai account unless ENABLE_CLAUDEAI_MCP_SERVERS=false, and `claude -p` loads project servers
# without asking unless --strict-mcp-config (checked in `claude --help`, 2.1.283).
( cd "$CWD" && export ENABLE_CLAUDEAI_MCP_SERVERS=false SLASH_COMMAND_TOOL_CHAR_BUDGET="${SLASH_COMMAND_TOOL_CHAR_BUDGET:-200000}" && exec "${OWN_SESSION[@]}" claude -p --model "$MODEL" --output-format json \
    --setting-sources project,local --strict-mcp-config ${CLAUDE_EVAL_ARGS:-} ${EXTRA[@]+"${EXTRA[@]}"} ) \
  < "$PROMPT" > "$OUT/raw.json" 2> "$OUT/stderr.log" &
RUNNER_PID=$!
wait "$RUNNER_PID"; RC=$?
stop_runner   # what the CLI left running (a browser, a server) stops with it
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
