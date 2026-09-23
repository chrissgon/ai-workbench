#!/usr/bin/env bash
# Install ai-workbench into Claude Code as a plugin.
#
# Usage: bash adapters/claude-code/install.sh [--dry-run] [--uninstall]
#
# Builds agents from the core, then symlinks this adapter folder into
# ~/.claude/skills/ai-workbench. Claude Code loads any folder under a skills directory
# that contains .claude-plugin/plugin.json as a plugin on the next session.
# Alternative for a single session: claude --plugin-dir "$(pwd)/adapters/claude-code"
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/ai-workbench"
DRY=0 UNINSTALL=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --help|-h) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$a'. See --help." >&2; exit 2 ;;
  esac
done
if [[ $UNINSTALL -eq 1 ]]; then
  [[ $DRY -eq 1 ]] && { echo "{\"would_remove\": \"$TARGET\"}"; exit 0; }
  [[ -L "$TARGET" ]] && rm "$TARGET"
  echo "{\"removed\": \"$TARGET\"}"; exit 0
fi
if [[ $DRY -eq 1 ]]; then
  python3 "$HERE/build.py" --dry-run >/dev/null
  echo "{\"would_link\": \"$TARGET\", \"to\": \"$HERE\"}"; exit 0
fi
python3 "$HERE/build.py" >/dev/null
mkdir -p "$(dirname "$TARGET")"
if [[ -e "$TARGET" && ! -L "$TARGET" ]]; then
  echo "Error: $TARGET exists and is not a symlink. Remove it manually or set CLAUDE_SKILLS_DIR." >&2; exit 1
fi
ln -sfn "$HERE" "$TARGET"
echo "{\"linked\": \"$TARGET\", \"to\": \"$HERE\", \"next\": \"restart the session; the plugin loads as ai-workbench@skills-dir\"}"
