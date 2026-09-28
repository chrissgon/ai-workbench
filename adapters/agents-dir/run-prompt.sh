#!/usr/bin/env bash
# Eval contract for tools that read .agents/skills. Default runner: OpenCode (`opencode run`).
#
# Usage: run-prompt.sh --prompt-file <f> --cwd <dir> --model <id> --out <dir> [--skill-dir <dir>]
#                      [--extra-skill-dir <dir>]... [--allow-command <prefix>]... [--allow-web]
#
# Writes <out>/response.md and <out>/timing.json (tokens unknown: null). --skill-dir and each
# --extra-skill-dir are copied, never linked, into <cwd>/.agents/skills/<name>. A case folder that
# already holds .agents/, .opencode/ or opencode.json[c] (from a fixture or a setup) is refused.
# Override the command with RUN_PROMPT_CMD, a template with {prompt_file}, {model} and {cwd}, each
# replaced by a shell-quoted value, e.g. RUN_PROMPT_CMD='mytool --model {model} < {prompt_file}'.
# Flags verified against opencode 1.18.32 (run --help); re-check after upgrades.
# --allow-command is accepted but not enforced: the default runner approves every tool (--auto), so
# the only containment is the environment eval_run.py sets (an allowlist, git local only, gh and npm
# signed out). --allow-web is accepted for the same reason: web tools are whatever the runner offers.
# Connectors and MCP servers: the throwaway HOME below hides the user's configuration and
# project configuration is refused, so none load; RUN_PROMPT_KEEP_HOME=1 loses that guarantee.
set -euo pipefail
PROMPT="" CWD="" MODEL="" OUT="" SKILL_DIR="" ALLOWED=0
EXTRA_SKILLS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt-file) PROMPT="$2"; shift 2 ;;
    --cwd) CWD="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --skill-dir) SKILL_DIR="$2"; shift 2 ;;
    --extra-skill-dir) EXTRA_SKILLS+=("$2"); shift 2 ;;
    --allow-command) ALLOWED=1; shift 2 ;;
    --allow-web) shift ;;
    --help|-h) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
[[ -f "$PROMPT" && -d "$CWD" && -n "$MODEL" && -n "$OUT" ]] || { echo "Error: --prompt-file, --cwd, --model and --out are required. See --help." >&2; exit 2; }
FOUND="$(find "$CWD" -path "$CWD/.git" -prune -o \( -name .agents -o -name .opencode -o -name opencode.json -o -name opencode.jsonc \) -print -quit)"
[[ -z "$FOUND" ]] || { echo "Error: the case folder already holds ${FOUND#"$CWD"/}; a fixture or setup must not carry harness settings." >&2; exit 2; }
mkdir -p "$OUT"
[[ $ALLOWED -eq 1 ]] && echo "note: --allow-command is not enforced by this runner; it approves every tool (see --help)." >&2
install_skill() {
  local src dest
  src="$(cd "$1" && pwd)"; dest="$CWD/.agents/skills/$(basename "$src")"
  mkdir -p "$CWD/.agents/skills"
  rm -rf "${dest:?}"
  cp -RL "$src" "$dest"   # -L: a link inside the skill is copied as its content, never kept pointing back
}
[[ -n "$SKILL_DIR" ]] && install_skill "$SKILL_DIR"
for d in ${EXTRA_SKILLS[@]+"${EXTRA_SKILLS[@]}"}; do install_skill "$d"; done
# Skills link the workbench's shared references as ../../shared/references/<file>: copy them beside
# the installed skills so those links resolve inside the case folder too.
WORKBENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -d "$CWD/.agents/skills" && -d "$WORKBENCH/shared" ]]; then
  rm -rf "${CWD:?}/.agents/shared"
  cp -RL "$WORKBENCH/shared" "$CWD/.agents/shared"
fi
if [[ -n "${RUN_PROMPT_CMD:-}" ]]; then
  # Values are shell-quoted so a model id or path cannot add commands to the template.
  CMD="${RUN_PROMPT_CMD//\{prompt_file\}/$(printf '%q' "$PROMPT")}"
  CMD="${CMD//\{model\}/$(printf '%q' "$MODEL")}"
  CMD="${CMD//\{cwd\}/$(printf '%q' "$CWD")}"
  RUN=(bash -c "$CMD")  # security-scan: allow shell-string -- the template is the operator's own RUN_PROMPT_CMD; every value put in it is shell-quoted above
elif command -v opencode >/dev/null; then
  # --pure: no external plugins; --auto: approve tool permissions inside the sandboxed cwd (override with OPENCODE_EVAL_ARGS)
  read -r -a ARGS <<< "${OPENCODE_EVAL_ARGS:---pure --auto}"
  RUN=(opencode run ${ARGS[@]+"${ARGS[@]}"} -m "$MODEL" "$(cat "$PROMPT")")
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
set +e; ( cd "$CWD" && "${RUN[@]}" ) < /dev/null > "$OUT/response.md" 2> "$OUT/stderr.log"; RC=$?; set -e
[[ -n "$ISO_HOME" ]] && rm -rf "$ISO_HOME"
END=$(python3 -c 'import time; print(int(time.time()*1000))')
printf '{"total_tokens": null, "duration_ms": %d, "cost_usd": null, "exit_code": %d}\n' "$((END-START))" "$RC" > "$OUT/timing.json"
exit $RC
