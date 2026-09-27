#!/usr/bin/env bash
# Install ai-workbench skills into the cross-tool skills directory.
#
# Usage: bash adapters/agents-dir/install.sh [--pack <name>] [--project <dir>] [--copy] [--dry-run] [--uninstall]
#
# Default target is ~/.agents/skills (read by Codex, Cursor, Cline, OpenCode, OpenClaw and others).
# --pack <name>    which skills to install (packs/<name>.txt); default: default
# --project <dir>  target <dir>/.agents/skills instead of the user-level directory
# --copy           copy folders instead of symlinking (for filesystems without symlinks)
# Replaces or removes only what it made (its symlinks, or copies holding its marker file); a folder
# of the same name that is not its own is skipped and reported, and the run exits 1.
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
    --help|-h) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
names=()
selected="$(python3 "$ROOT/scripts/select_skills.py" --pack "$PACK" --lines)" || exit 2
while IFS= read -r n; do [[ -n "$n" ]] && names+=("$n"); done <<< "$selected"
list="[]"; [[ ${#names[@]} -gt 0 ]] && list="[$(printf '"%s",' "${names[@]}" | sed 's/,$//')]"
if [[ $DRY -eq 1 ]]; then
  printf '{"target": "%s", "pack": "%s", "mode": "%s", "uninstall": %s, "skills": %s}\n' "$TARGET" "$PACK" "$([[ $COPY -eq 1 ]] && echo copy || echo symlink)" "$UNINSTALL" "$list"
  exit 0
fi
mkdir -p "$TARGET"
# Only what this script made is replaced or removed: a symlink to this checkout's skill, or a copy
# holding the marker file written by --copy. Anything else with the same name is the user's; it is
# skipped and reported, never deleted.
MARK=".installed-by-ai-workbench"
ours() {
  if [[ -L "$1" ]]; then [[ "$(readlink -- "$1")" == "$2" ]]; return; fi
  [[ -d "$1" && -f "$1/$MARK" ]]
}
remove_ours() {
  if [[ -L "$1" ]]; then rm -f -- "$1"; elif [[ -d "$1" ]]; then rm -rf -- "${1:?}"; fi
}
done_count=0 skipped=()
for n in "${names[@]}"; do
  dest="$TARGET/$n" src="$SKILLS/$n"
  if [[ -e "$dest" || -L "$dest" ]] && ! ours "$dest" "$src"; then
    echo "Skipped $dest: it exists and this installer did not create it. Move it away and run again." >&2
    skipped+=("$n")
    continue
  fi
  [[ $UNINSTALL -eq 1 && ! -e "$dest" && ! -L "$dest" ]] && continue
  remove_ours "$dest"
  if [[ $UNINSTALL -eq 0 ]]; then
    if [[ $COPY -eq 1 ]]; then cp -R "$src" "$dest" && : > "$dest/$MARK"; else ln -s "$src" "$dest"; fi
  fi
  done_count=$((done_count + 1))
done
skip_list="[]"; [[ ${#skipped[@]} -gt 0 ]] && skip_list="[$(printf '"%s",' "${skipped[@]}" | sed 's/,$//')]"
printf '{"target": "%s", "pack": "%s", "%s": %s, "skipped": %s, "uninstall": %s}\n' "$TARGET" "$PACK" \
  "$([[ $UNINSTALL -eq 1 ]] && echo removed || echo installed)" "$done_count" "$skip_list" "$UNINSTALL"
[[ ${#skipped[@]} -eq 0 ]] || exit 1
