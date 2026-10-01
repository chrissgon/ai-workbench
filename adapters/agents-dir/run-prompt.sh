#!/usr/bin/env bash
# Eval contract for tools that read .agents/skills. Default runner: OpenCode (`opencode run`).
#
# Usage: run-prompt.sh --prompt-file <f> --cwd <dir> --model <id> --out <dir> [--skill-dir <dir>]
#                      [--extra-skill-dir <dir>]... [--allow-command <prefix>]... [--allow-web] [--max-cost-usd <amount>]
#
# Writes <out>/response.md and <out>/timing.json (tokens unknown: null). --skill-dir and each
# --extra-skill-dir are copied, never linked, into <cwd>/.agents/skills/<name>. A case folder that
# already holds .agents/, .opencode/ or opencode.json[c] (from a fixture or a setup) is refused.
# Override the command with RUN_PROMPT_CMD, a template with {prompt_file}, {model} and {cwd}, each
# replaced by a shell-quoted value, e.g. RUN_PROMPT_CMD='mytool --model {model} < {prompt_file}'.
# Flags verified against opencode 1.18.32 (run --help); re-check after upgrades.
# --allow-command is accepted but not enforced: the default runner approves every tool (--auto), so
# the only containment is the environment eval_run.py sets (an allowlist, git local only, gh and npm
# signed out). --allow-web turns on the default runner's web search (OPENCODE_ENABLE_EXA=1, verified with
# opencode 1.18.32: without it the model can only fetch URLs it guesses); page fetch is always on.
# A model id "ollama/<name>" runs a local model served by Ollama (http://127.0.0.1:11434, or
# RUN_PROMPT_OLLAMA_URL): the provider entry is written into the throwaway HOME, never into the case
# folder. Give the model a context that fits the runner's own prompt and the skill (see README.md).
# On macOS the throwaway HOME gets its own empty keychain (below), so a browser a model starts finds a default
# keychain there instead of showing the person a "Keychain Not Found" dialog; it is removed with that HOME.
# Stopping this script (TERM, INT, HUP) stops the runner and everything it started.
# Connectors and MCP servers: the throwaway HOME below hides the user's configuration and
# project configuration is refused, so none load; RUN_PROMPT_KEEP_HOME=1 loses that guarantee.
set -euo pipefail
PROMPT="" CWD="" MODEL="" OUT="" SKILL_DIR="" ALLOWED=0 WEB=0 CAPPED=0
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
    --allow-web) WEB=1; shift ;;
    --max-cost-usd) CAPPED=1; shift 2 ;;
    --help|-h) sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
[[ -f "$PROMPT" && -d "$CWD" && -n "$MODEL" && -n "$OUT" ]] || { echo "Error: --prompt-file, --cwd, --model and --out are required. See --help." >&2; exit 2; }
FOUND="$(find "$CWD" -path "$CWD/.git" -prune -o \( -name .agents -o -name .opencode -o -name opencode.json -o -name opencode.jsonc \) -print -quit)"
[[ -z "$FOUND" ]] || { echo "Error: the case folder already holds ${FOUND#"$CWD"/}; a fixture or setup must not carry harness settings." >&2; exit 2; }
mkdir -p "$OUT"
[[ $ALLOWED -eq 1 ]] && echo "note: --allow-command is not enforced by this runner; it approves every tool (see --help)." >&2
[[ $CAPPED -eq 1 ]] && echo "note: --max-cost-usd is not enforced by this runner (opencode has no spend limit); eval_run.py --timeout and a credit limit on the provider key are the caps." >&2
install_skill() {
  local src dest
  src="$(cd "$1" && pwd)"; dest="$CWD/.agents/skills/$(basename "$src")"
  mkdir -p "$CWD/.agents/skills"
  rm -rf "${dest:?}"
  cp -RL "$src" "$dest"   # -L: a link inside the skill is copied as its content, never kept pointing back
  rm -rf "${dest:?}/evals"   # the cases, their fixtures and assertions: the model under test never reads them
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
  [[ $WEB -eq 1 ]] && export OPENCODE_ENABLE_EXA=1
else
  echo "Error: no runner. Install opencode or set RUN_PROMPT_CMD (see --help)." >&2; exit 1
fi
START=$(python3 -c 'import time; print(int(time.time()*1000))')
# Isolation: the default runner loads skills and config from the user's home (its own and other tools').
# Run with a throwaway HOME so only the project-scoped skill in <cwd> is visible; provider keys still come
# from the environment. Set RUN_PROMPT_KEEP_HOME=1 to use the real home instead.
ISO_HOME=""
if [[ -z "${RUN_PROMPT_KEEP_HOME:-}" ]]; then ISO_HOME="$(mktemp -d)"; export HOME="$ISO_HOME" XDG_CONFIG_HOME="$ISO_HOME/.config" XDG_DATA_HOME="$ISO_HOME/.local/share"; fi
# macOS resolves the default keychain through HOME, and the throwaway HOME has none: a browser started in the
# run (Chrome looks up "Chrome Safe Storage") then shows a "Keychain Not Found" dialog on the person's screen,
# once per launch. Give the throwaway HOME an empty keychain of its own. Every call sets HOME to the throwaway
# home, so the person's keychains and default keychain are never read or changed; never with the real HOME.
# A failure is not fatal. RUN_PROMPT_OS and RUN_PROMPT_SECURITY exist for the tests.
throwaway_keychain() {
  local sec="${RUN_PROMPT_SECURITY:-/usr/bin/security}" k="$ISO_HOME/Library/Keychains/login.keychain-db"
  [[ -n "$ISO_HOME" && "${RUN_PROMPT_OS:-$(uname)}" == "Darwin" && -x "$sec" ]] || return 0
  mkdir -p "$ISO_HOME/Library/Keychains" "$ISO_HOME/Library/Preferences"
  # A keychain is unlocked when it is created, and set-keychain-settings without options removes its auto-lock;
  # unlock-keychain is not called: it answers "passphrase not correct" for a keychain made this way (checked on
  # macOS, 2026-10-01) although items can be added and read. Each step on its own: a later step still runs when one fails, and the note names what failed and why.
  local step msg failed=""
  for step in "create-keychain -p  $k" "default-keychain -s $k" "list-keychains -d user -s $k" "set-keychain-settings $k"; do
    case "$step" in
      create-keychain*) msg="$(HOME="$ISO_HOME" "$sec" create-keychain -p "" "$k" 2>&1)" ;;
      default-keychain*) msg="$(HOME="$ISO_HOME" "$sec" default-keychain -s "$k" 2>&1)" ;;
      list-keychains*) msg="$(HOME="$ISO_HOME" "$sec" list-keychains -d user -s "$k" 2>&1)" ;;
      set-keychain-settings*) msg="$(HOME="$ISO_HOME" "$sec" set-keychain-settings "$k" 2>&1)" ;;
    esac || failed="$failed ${step%% *} ($(printf '%s' "$msg" | tr '\n' ' ' | cut -c1-120));"
  done
  [[ -z "$failed" ]] || echo "note: the keychain of the throwaway HOME is incomplete, a browser started in this run may show a keychain dialog:$failed" >&2
}
throwaway_keychain
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
cleanup() { stop_runner; [[ -n "$ISO_HOME" ]] && rm -rf "$ISO_HOME"; return 0; }
trap cleanup EXIT
trap 'exit 143' TERM INT HUP
if [[ "$MODEL" == ollama/* && -z "${RUN_PROMPT_CMD:-}" ]]; then
  [[ "$MODEL" =~ ^ollama/[A-Za-z0-9._:/-]+$ ]] || { echo "Error: a local model id is ollama/<name> with letters, digits and . _ : / - only." >&2; exit 2; }
  [[ -n "$ISO_HOME" ]] || { echo "Error: a local model needs the throwaway HOME (unset RUN_PROMPT_KEEP_HOME)." >&2; exit 2; }
  mkdir -p "$XDG_CONFIG_HOME/opencode"
  python3 - "${MODEL#ollama/}" "${RUN_PROMPT_OLLAMA_URL:-http://127.0.0.1:11434/v1}" > "$XDG_CONFIG_HOME/opencode/opencode.json" <<'PY'
import json, sys
name, url = sys.argv[1], sys.argv[2]
print(json.dumps({"$schema": "https://opencode.ai/config.json", "provider": {"ollama": {
    "npm": "@ai-sdk/openai-compatible", "name": "Ollama (local)", "options": {"baseURL": url},
    "models": {name: {"name": name}}}}}))
PY
fi
# stdin closed: the runner otherwise waits on an inherited pipe that never ends
set +e
( cd "$CWD" && exec "${OWN_SESSION[@]}" "${RUN[@]}" ) < /dev/null > "$OUT/response.md" 2> "$OUT/stderr.log" &
RUNNER_PID=$!
wait "$RUNNER_PID"; RC=$?
set -e
cleanup   # what the runner left running (a browser, a server) stops with it; the keychain goes with the home
END=$(python3 -c 'import time; print(int(time.time()*1000))')
printf '{"total_tokens": null, "duration_ms": %d, "cost_usd": null, "exit_code": %d}\n' "$((END-START))" "$RC" > "$OUT/timing.json"
exit $RC
