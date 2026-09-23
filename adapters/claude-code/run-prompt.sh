#!/usr/bin/env bash
# Eval contract: run one prompt through Claude Code non-interactively.
#
# Usage: run-prompt.sh --prompt-file <f> --cwd <dir> --model <id> --out <dir> [--skill-dir <dir>]
#
# Writes <out>/response.md and <out>/timing.json. With --skill-dir, the skill is symlinked into
# <cwd>/.claude/skills/<name> so it is discoverable at project scope. Settings are limited to the
# project scope so user-level skills do not leak into a without-skill run; verify on first use by
# searching the transcript for the skill name.
# Extra CLI flags: CLAUDE_EVAL_ARGS (default: --permission-mode acceptEdits).
# A proxy for floor models: set ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN in the environment.
set -euo pipefail
PROMPT="" CWD="" MODEL="" OUT="" SKILL_DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt-file) PROMPT="$2"; shift 2 ;;
    --cwd) CWD="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --skill-dir) SKILL_DIR="$2"; shift 2 ;;
    --help|-h) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
[[ -f "$PROMPT" && -d "$CWD" && -n "$MODEL" && -n "$OUT" ]] || { echo "Error: --prompt-file, --cwd, --model and --out are required. See --help." >&2; exit 2; }
command -v claude >/dev/null || { echo "Error: 'claude' CLI not found on PATH." >&2; exit 1; }
mkdir -p "$OUT"
if [[ -n "$SKILL_DIR" ]]; then
  mkdir -p "$CWD/.claude/skills"
  ln -sfn "$(cd "$SKILL_DIR" && pwd)" "$CWD/.claude/skills/$(basename "$SKILL_DIR")"
fi
START=$(python3 -c 'import time; print(int(time.time()*1000))')
set +e
( cd "$CWD" && claude -p "$(cat "$PROMPT")" --model "$MODEL" --output-format json --setting-sources project,local ${CLAUDE_EVAL_ARGS:---permission-mode acceptEdits} ) > "$OUT/raw.json" 2> "$OUT/stderr.log"
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
