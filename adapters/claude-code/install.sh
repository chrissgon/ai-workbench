#!/usr/bin/env bash
# Install ai-workbench into Claude Code as a plugin.
#
# Usage: bash adapters/claude-code/install.sh [--pack <name>] [--dry-run] [--uninstall]
#
# Builds build/<pack>/ (a plugin folder with symlinked skills and generated agents), then
# symlinks it to ~/.claude/skills/ai-workbench. Claude Code loads any folder under a skills
# directory that contains .claude-plugin/plugin.json as a plugin on the next session.
# Default pack: default (every area except optional ones). See packs/README.md.
# For one session only: claude --plugin-dir adapters/claude-code/build/<pack>
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/ai-workbench"
PACK="default" DRY=0 UNINSTALL=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pack) PACK="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --help|-h) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
if [[ $UNINSTALL -eq 1 ]]; then
  [[ $DRY -eq 1 ]] && { echo "{\"would_remove\": \"$TARGET\"}"; exit 0; }
  # Only a link into this adapter's build folder is ours to remove.
  if [[ -L "$TARGET" && "$(readlink -- "$TARGET")" == "$HERE/build/"* ]]; then
    rm -f -- "$TARGET"; echo "{\"removed\": \"$TARGET\"}"; exit 0
  fi
  [[ -e "$TARGET" || -L "$TARGET" ]] && { echo "Error: $TARGET was not created by this installer; left in place." >&2; exit 1; }
  echo "{\"removed\": null}"; exit 0
fi
BUILD="$HERE/build/$PACK"
if [[ $DRY -eq 1 ]]; then
  python3 "$HERE/build.py" --pack "$PACK" --dry-run
  echo "{\"would_link\": \"$TARGET\", \"to\": \"$BUILD\"}"; exit 0
fi
python3 "$HERE/build.py" --pack "$PACK" >/dev/null
mkdir -p "$(dirname "$TARGET")"
if [[ -e "$TARGET" || -L "$TARGET" ]] && [[ ! -L "$TARGET" || "$(readlink -- "$TARGET")" != "$HERE/build/"* ]]; then
  echo "Error: $TARGET exists and was not created by this installer. Move it away or set CLAUDE_SKILLS_DIR." >&2; exit 1
fi
ln -sfn "$BUILD" "$TARGET"
echo "{\"linked\": \"$TARGET\", \"to\": \"$BUILD\", \"pack\": \"$PACK\", \"next\": \"restart the session; the plugin loads as ai-workbench@skills-dir\"}"
