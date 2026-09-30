#!/usr/bin/env bash
# Runtime contract (contracts/runtime.md): run one agent on one task with one model API call and no tools.
#
# Usage: run-agent.sh --agent-file <agents/name.md> --task-file <f> --project <dir> --model <id> --out <dir>
#                     [--skill-dir <dir>]... [--max-cost-usd <amount>] [--timeout-seconds <n>]
#
# --model anthropic/<model> calls the Anthropic Messages API (secret ANTHROPIC_API_KEY);
# --model openrouter/<vendor>/<model> calls OpenRouter (secret OPENROUTER_API_KEY).
# Everything happens in run_agent.py (standard library; see its --help for the prompt, costs and limits).
# With uv on PATH it runs through `uv run --script`, so the secret resolver can also read the OS secret
# store (its keyring package); without uv, python3 runs it and the key must be in the environment.
# Writes <out>/response.md, <out>/timing.json {total_tokens, duration_ms, cost_usd, exit_code},
# <out>/raw.json, <out>/request.json and <out>/stderr.log. Exit 0 when the model answered, 1 otherwise,
# 2 on usage errors.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v uv >/dev/null 2>&1; then
  exec uv run --quiet --no-project --script "$HERE/run_agent.py" "$@"
fi
exec python3 "$HERE/run_agent.py" "$@"
