#!/usr/bin/env bash
# Scaffold a new skill from templates/.
#
# Usage: bash scripts/new-skill.sh --name <prefix-name> --kind capability|flow --area <area> [--dry-run]
#
# Options:
#   --name    skill name; prefix must be one of biz product brand design eng ops mkt ai core flow
#   --kind    capability or flow (flow- prefix requires kind flow)
#   --area    business product brand design engineering delivery marketing ai core
#   --dry-run print what would be created and exit
#   --help    show this text
#
# Examples:
#   bash scripts/new-skill.sh --name biz-business-model --kind capability --area business
#   bash scripts/new-skill.sh --name flow-new-product --kind flow --area core
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="" KIND="" AREA="" DRY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2 ;;
    --kind) KIND="$2"; shift 2 ;;
    --area) AREA="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --help|-h) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
[[ -z "$NAME" || -z "$KIND" || -z "$AREA" ]] && { echo "Error: --name, --kind and --area are required. See --help." >&2; exit 2; }
[[ "$NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || { echo "Error: name must be lowercase a-z0-9 with single hyphens. Received: '$NAME'" >&2; exit 2; }
PREFIX="${NAME%%-*}"
case "$PREFIX" in biz|product|brand|design|eng|ops|mkt|ai|core|flow) ;; *) echo "Error: prefix '$PREFIX' is not an area prefix (biz product brand design eng ops mkt ai core flow)." >&2; exit 2 ;; esac
case "$KIND" in capability|flow) ;; *) echo "Error: --kind must be capability or flow. Received: '$KIND'" >&2; exit 2 ;; esac
case "$AREA" in business|product|brand|design|engineering|delivery|marketing|ai|core) ;; *) echo "Error: --area must be one of business product brand design engineering delivery marketing ai core. Received: '$AREA'" >&2; exit 2 ;; esac
[[ "$PREFIX" == "flow" && "$KIND" != "flow" ]] && { echo "Error: flow- prefix requires --kind flow." >&2; exit 2; }
[[ "$PREFIX" != "flow" && "$KIND" == "flow" ]] && { echo "Error: --kind flow requires the flow- prefix." >&2; exit 2; }
DEST="$ROOT/skills/$NAME"
[[ -e "$DEST" ]] && { echo "Error: $DEST already exists." >&2; exit 1; }
TITLE="$(echo "${NAME#*-}" | tr "-" " " | awk '{print toupper(substr($0,1,1)) substr($0,2)}')"
if [[ $DRY -eq 1 ]]; then
  echo "{\"would_create\": \"skills/$NAME/SKILL.md\", \"kind\": \"$KIND\", \"area\": \"$AREA\", \"template\": \"templates/$KIND.SKILL.md\"}"
  exit 0
fi
mkdir -p "$DEST/evals"
sed -e "s/__NAME__/$NAME/g" -e "s/__AREA__/$AREA/g" -e "s/__TITLE__/$TITLE/g" "$ROOT/templates/$KIND.SKILL.md" > "$DEST/SKILL.md"
printf '{\n  "skill_name": "%s",\n  "evals": []\n}\n' "$NAME" > "$DEST/evals/evals.json"
echo "{\"created\": \"skills/$NAME/SKILL.md\", \"next\": \"fill the remaining __PLACEHOLDERS__, then run python3 scripts/validate.py\"}"
