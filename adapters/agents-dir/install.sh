#!/usr/bin/env bash
# Install ai-workbench skills into the cross-tool skills directory.
#
# Usage: bash adapters/agents-dir/install.sh [--pack <name>] [--project <dir>] [--copy] [--dry-run] [--uninstall]
#
# Default target is ~/.agents/skills (read by Codex, Cursor, Cline, OpenCode, OpenClaw and others).
# --pack <name>    which skills to install (packs/<name>.txt); default: default
# --project <dir>  target <dir>/.agents/skills instead of the user-level directory
# --copy           copy folders instead of symlinking (for filesystems without symlinks)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SKILLS="$ROOT/skills"
TARGET="$HOME/.agents/skills"
PACK="default" DRY=0 UNINSTALL=0 COPY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pack) PACK="$2"; shift 2 ;;
    --project) TARGET="$2/.agents/skills"; shift 2 ;;
    --copy) COPY=1; shift ;;
    --dry-run) DRY=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --help|-h) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
names=()
while IFS= read -r n; do [[ -n "$n" ]] && names+=("$n"); done < <(python3 "$ROOT/scripts/select_skills.py" --pack "$PACK" --lines)
list="[]"; [[ ${#names[@]} -gt 0 ]] && list="[$(printf '"%s",' "${names[@]}" | sed 's/,$//')]"
if [[ $DRY -eq 1 ]]; then
  printf '{"target": "%s", "pack": "%s", "mode": "%s", "uninstall": %s, "skills": %s}\n' "$TARGET" "$PACK" "$([[ $COPY -eq 1 ]] && echo copy || echo symlink)" "$UNINSTALL" "$list"
  exit 0
fi
mkdir -p "$TARGET"
for n in "${names[@]}"; do
  dest="$TARGET/$n"
  if [[ $UNINSTALL -eq 1 ]]; then
    [[ -L "$dest" || -d "$dest" ]] && rm -rf "$dest"
    continue
  fi
  if [[ $COPY -eq 1 ]]; then rm -rf "$dest"; cp -R "$SKILLS/$n" "$dest"; else ln -sfn "$SKILLS/$n" "$dest"; fi
done
printf '{"target": "%s", "pack": "%s", "installed": %s, "uninstall": %s}\n' "$TARGET" "$PACK" "${#names[@]}" "$UNINSTALL"
