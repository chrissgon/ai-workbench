#!/usr/bin/env bash
# Runtime contract (contracts/runtime.md): run one agent on one task through Claude Code, read only.
#
# Usage: run-agent.sh --agent-file <agents/name.md> --task-file <f> --project <dir> --model <id> --out <dir>
#                     [--skill-dir <dir>]... [--max-cost-usd <amount>] [--timeout-seconds <n>]
#
# The run happens in a fresh folder <out>/cwd: the skills are copied (never linked) into
# <out>/cwd/.claude/skills/<name>, the workbench's shared references beside them, and the agent's body
# (without its frontmatter) is appended to the system prompt. The model gets only reading tools
# (--tools Read,Glob,Grep): it cannot write, run commands or fetch pages; it reads --project through
# --add-dir and answers. No connectors or MCP servers are loaded (ENABLE_CLAUDEAI_MCP_SERVERS=false,
# --strict-mcp-config) and only the run folder's settings apply (--setting-sources project,local).
# --max-cost-usd becomes --max-budget-usd; --timeout-seconds (default 600) stops the run.
# Writes <out>/response.md, <out>/timing.json {total_tokens, duration_ms, cost_usd, exit_code},
# <out>/raw.json and <out>/stderr.log. Exit 0 when the model answered, 1 otherwise, 2 on usage errors.
set -euo pipefail
AGENT="" TASK="" PROJECT="" MODEL="" OUT="" MAX_COST="" TIMEOUT=600
SKILLS=()
need() { [[ $# -ge 2 ]] || { echo "Error: $1 needs a value. See --help." >&2; exit 2; }; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent-file) need "$@"; AGENT="$2"; shift 2 ;;
    --task-file) need "$@"; TASK="$2"; shift 2 ;;
    --project) need "$@"; PROJECT="$2"; shift 2 ;;
    --model) need "$@"; MODEL="$2"; shift 2 ;;
    --out) need "$@"; OUT="$2"; shift 2 ;;
    --skill-dir) need "$@"; SKILLS+=("$2"); shift 2 ;;
    --max-cost-usd)
      need "$@"
      [[ "$2" =~ ^[0-9]+(\.[0-9]+)?$ ]] || { echo "Error: --max-cost-usd needs a number, e.g. 0.50." >&2; exit 2; }
      MAX_COST="$2"; shift 2 ;;
    --timeout-seconds)
      need "$@"
      [[ "$2" =~ ^[0-9]+$ && "$2" -ge 30 && "$2" -le 3600 ]] || { echo "Error: --timeout-seconds takes 30 to 3600." >&2; exit 2; }
      TIMEOUT="$2"; shift 2 ;;
    --help|-h) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
[[ -f "$AGENT" && -f "$TASK" && -d "$PROJECT" && -n "$MODEL" && -n "$OUT" ]] || {
  echo "Error: --agent-file, --task-file, --project, --model and --out are required. See --help." >&2; exit 2; }
command -v claude >/dev/null || { echo "Error: 'claude' CLI not found on PATH." >&2; exit 1; }
mkdir -p "$OUT"
[[ ! -e "$OUT/cwd" ]] || { echo "Error: $OUT/cwd already exists; every run gets a new --out." >&2; exit 2; }
CWD="$OUT/cwd"
mkdir -p "$CWD/.claude/skills"
chmod 700 "$OUT" "$CWD"
for d in ${SKILLS[@]+"${SKILLS[@]}"}; do
  src="$(cd "$d" && pwd)"; dest="$CWD/.claude/skills/$(basename "$src")"
  cp -RL "$src" "$dest"
  rm -rf "${dest:?}/evals"   # test cases and fixtures never reach the model
done
WORKBENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ -d "$WORKBENCH/shared" ]] && cp -RL "$WORKBENCH/shared" "$CWD/.claude/shared"
# The agent body without its YAML frontmatter.
BODY="$(awk 'NR==1 && /^---$/ {fm=1; next} fm && /^---$/ {fm=0; next} !fm' "$AGENT")"
PROJECT_ABS="$(cd "$PROJECT" && pwd)"
EXTRA=(); [[ -n "$MAX_COST" ]] && EXTRA+=(--max-budget-usd "$MAX_COST")
START=$(python3 -c 'import time; print(int(time.time()*1000))')
set +e
( cd "$CWD" && ENABLE_CLAUDEAI_MCP_SERVERS=false python3 - "$TIMEOUT" claude -p "$(cat "$TASK")" --model "$MODEL" \
    --output-format json --setting-sources project,local --strict-mcp-config --tools Read,Glob,Grep \
    --add-dir "$PROJECT_ABS" --append-system-prompt "$BODY" ${EXTRA[@]+"${EXTRA[@]}"} <<'PY'
import subprocess, sys
timeout, cmd = int(sys.argv[1]), sys.argv[2:]
try:
    sys.exit(subprocess.run(cmd, stdin=subprocess.DEVNULL, timeout=timeout).returncode)
except subprocess.TimeoutExpired:
    print(f"timeout after {timeout} s", file=sys.stderr)
    sys.exit(124)
PY
) > "$OUT/raw.json" 2> "$OUT/stderr.log"
RC=$?
set -e
END=$(python3 -c 'import time; print(int(time.time()*1000))')
python3 - "$OUT" "$START" "$END" "$RC" <<'PY'
import json, sys, os
out, start, end, rc = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
raw = open(os.path.join(out, "raw.json"), encoding="utf-8", errors="ignore").read()
text, tokens, cost, dur = "", None, None, end - start
try:
    d = json.loads(raw)
    if isinstance(d, list):
        d = next((x for x in d if x.get("type") == "result"), d[-1] if d else {})
    text = d.get("result") or ""
    u = d.get("usage") or {}
    if u:
        tokens = sum(int(u.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    cost = d.get("total_cost_usd")
    dur = d.get("duration_ms") or dur
except ValueError:
    pass
open(os.path.join(out, "response.md"), "w", encoding="utf-8").write(text if isinstance(text, str) else json.dumps(text))
json.dump({"total_tokens": tokens, "duration_ms": dur, "cost_usd": cost, "exit_code": rc}, open(os.path.join(out, "timing.json"), "w"))
sys.exit(0 if rc == 0 and text else 1)
PY
