#!/usr/bin/env bash
# Eval contract for tools that read .agents/skills. Default runner: OpenCode (`opencode run`).
#
# Usage: run-prompt.sh --prompt-file <f> --cwd <dir> --model <id> --out <dir> [--skill-dir <dir>]
#
# Writes <out>/response.md and <out>/timing.json (tokens unknown: null). With --skill-dir the skill is
# symlinked into <cwd>/.agents/skills/<name>. Override the command with RUN_PROMPT_CMD, a template with
# {prompt_file}, {model} and {cwd}, e.g. RUN_PROMPT_CMD='mytool --model {model} < {prompt_file}'.
# Flags verified against opencode 1.18.32 (run --help); re-check after upgrades.
set -euo pipefail
PROMPT="" CWD="" MODEL="" OUT="" SKILL_DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt-file) PROMPT="$2"; shift 2 ;;
    --cwd) CWD="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --skill-dir) SKILL_DIR="$2"; shift 2 ;;
    --help|-h) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
[[ -f "$PROMPT" && -d "$CWD" && -n "$MODEL" && -n "$OUT" ]] || { echo "Error: --prompt-file, --cwd, --model and --out are required. See --help." >&2; exit 2; }
mkdir -p "$OUT"
if [[ -n "$SKILL_DIR" ]]; then
  mkdir -p "$CWD/.agents/skills"
  ln -sfn "$(cd "$SKILL_DIR" && pwd)" "$CWD/.agents/skills/$(basename "$SKILL_DIR")"
fi
if [[ -n "${RUN_PROMPT_CMD:-}" ]]; then
  CMD="${RUN_PROMPT_CMD//\{prompt_file\}/$PROMPT}"; CMD="${CMD//\{model\}/$MODEL}"; CMD="${CMD//\{cwd\}/$CWD}"
elif command -v opencode >/dev/null; then
  # --pure: no external plugins; --auto: approve tool permissions inside the sandboxed cwd (override with OPENCODE_EVAL_ARGS)
  CMD="opencode run ${OPENCODE_EVAL_ARGS:---pure --auto} -m \"$MODEL\" \"\$(cat \"$PROMPT\")\""
else
  echo "Error: no runner. Install opencode or set RUN_PROMPT_CMD (see --help)." >&2; exit 1
fi
START=$(python3 -c 'import time; print(int(time.time()*1000))')
# Isolation: the default runner loads skills and config from the user's home (its own and other tools').
# Run with a throwaway HOME so only the project-scoped skill in <cwd> is visible; provider keys still come
# from the environment. Set RUN_PROMPT_KEEP_HOME=1 to use the real home instead.
ISO_HOME=""
if [[ -z "${RUN_PROMPT_KEEP_HOME:-}" ]]; then ISO_HOME="$(mktemp -d)"; export HOME="$ISO_HOME" XDG_CONFIG_HOME="$ISO_HOME/.config" XDG_DATA_HOME="$ISO_HOME/.local/share"; fi
# stdin closed: the runner otherwise waits on an inherited pipe that never ends
set +e; ( cd "$CWD" && bash -c "$CMD" ) < /dev/null > "$OUT/response.md" 2> "$OUT/stderr.log"; RC=$?; set -e
[[ -n "$ISO_HOME" ]] && rm -rf "$ISO_HOME"
END=$(python3 -c 'import time; print(int(time.time()*1000))')
printf '{"total_tokens": null, "duration_ms": %d, "cost_usd": null, "exit_code": %d}\n' "$((END-START))" "$RC" > "$OUT/timing.json"
exit $RC
