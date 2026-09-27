#!/usr/bin/env bash
# Enable the workbench's versioned git hooks (.githooks/) in this clone.
#
# Usage: bash scripts/install-hooks.sh [--check | --uninstall] [--help]
#
# Options:
#   (none)       set the clone's core.hooksPath to .githooks
#   --check      report whether the hooks are enabled; exit 1 when they are not
#   --uninstall  unset core.hooksPath, only when it points to .githooks
#   --help       show this text
#
# Refuses (exit 1) when core.hooksPath already points somewhere else in this clone: another hook
# manager is in use, and replacing it is the user's decision.
# Prints JSON to stdout: {"hooks_path": "<value or null>", "enabled": true|false}.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE=install
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) MODE=check; shift ;;
    --uninstall) MODE=uninstall; shift ;;
    --help|-h) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done

current() { git -C "$ROOT" config --local --get core.hooksPath || true; }
report() {
  local p; p="$(current)"
  if [[ -n "$p" ]]; then printf '{"hooks_path": "%s", "enabled": %s}\n' "$p" "$([[ "$p" == .githooks ]] && echo true || echo false)"
  else printf '{"hooks_path": null, "enabled": false}\n'; fi
}

case "$MODE" in
  check)
    report
    [[ "$(current)" == .githooks ]] || exit 1
    ;;
  install)
    p="$(current)"
    if [[ -n "$p" && "$p" != .githooks ]]; then
      echo "Error: core.hooksPath is already '$p' in this clone. Ask the user before replacing it." >&2
      report; exit 1
    fi
    chmod +x "$ROOT"/.githooks/*
    git -C "$ROOT" config --local core.hooksPath .githooks
    report
    ;;
  uninstall)
    [[ "$(current)" == .githooks ]] && git -C "$ROOT" config --local --unset core.hooksPath
    report
    ;;
esac
