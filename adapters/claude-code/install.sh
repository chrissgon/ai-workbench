#!/usr/bin/env bash
# Install ai-workbench into Claude Code as a plugin.
#
# Usage: bash adapters/claude-code/install.sh [--pack <name>] [--dry-run] [--uninstall]
#
# Builds build/<pack>/ (a plugin folder with symlinked skills, the shared references beside them
# and generated agents), then symlinks it to ~/.claude/skills/ai-workbench (CLAUDE_SKILLS_DIR
# replaces ~/.claude/skills). Claude Code loads any folder under a skills directory that contains
# .claude-plugin/plugin.json as a plugin on the next session.
# Default pack: default (every area except optional ones). See packs/README.md.
# One pack is installed at a time: an install removes the builds of other packs, --uninstall
# removes the link and every build. A pack that selects no skill is reported and changes nothing.
# When the linked folder is not picked up, load the build for one session instead:
#   claude --plugin-dir adapters/claude-code/build/<pack>
# Exit codes: 0 ok, 1 the target exists and is not this installer's, 2 usage error.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
TARGET="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/ai-workbench"
PACK="default" DRY=0 UNINSTALL=0
need() { [[ $# -ge 2 ]] || { echo "Error: $1 needs a value. See --help." >&2; exit 2; }; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pack) need "$@"; PACK="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --help|-h) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Error: unknown option '$1'. See --help." >&2; exit 2 ;;
  esac
done
# One JSON line on stdout, built by a JSON writer so that a path holding a quote or a backslash
# stays valid JSON. Arguments: key=value (a string), key:=value (a number, true, false or null).
emit() {
  python3 - "$@" <<'PY'
import json, sys
out = {}
for arg in sys.argv[1:]:
    key, sep, value = arg.partition("=")
    out[key[:-1] if key.endswith(":") else key] = json.loads(value) if key.endswith(":") else value
print(json.dumps(out))
PY
}
# Only a link into this adapter's build folder is ours to replace or remove.
ours() { [[ -L "$TARGET" && "$(readlink -- "$TARGET")" == "$HERE/build/"* ]]; }
if [[ $UNINSTALL -eq 1 ]]; then
  [[ $DRY -eq 1 ]] && { emit "would_remove=$TARGET"; exit 0; }
  if ours; then
    rm -f -- "$TARGET"
    python3 "$HERE/build.py" --clean >/dev/null
    emit "removed=$TARGET"; exit 0
  fi
  [[ -e "$TARGET" || -L "$TARGET" ]] && { echo "Error: $TARGET was not created by this installer; left in place." >&2; exit 1; }
  python3 "$HERE/build.py" --clean >/dev/null
  emit "removed:=null"; exit 0
fi
selected="$(python3 "$ROOT/scripts/select_skills.py" --pack "$PACK" --lines)" || exit 2
if [[ -z "$selected" ]]; then
  echo "Pack '$PACK' selects no skill: nothing was built and nothing was changed at $TARGET." >&2
  emit "pack=$PACK" "linked:=null" "skills:=0"; exit 0
fi
BUILD="$HERE/build/$PACK"
if [[ $DRY -eq 1 ]]; then
  python3 "$HERE/build.py" --pack "$PACK" --prune --dry-run
  emit "would_link=$TARGET" "to=$BUILD"; exit 0
fi
if [[ -e "$TARGET" || -L "$TARGET" ]] && ! ours; then
  echo "Error: $TARGET exists and was not created by this installer. Move it away or set CLAUDE_SKILLS_DIR." >&2; exit 1
fi
python3 "$HERE/build.py" --pack "$PACK" --prune >/dev/null
mkdir -p "$(dirname "$TARGET")"
ln -sfn "$BUILD" "$TARGET"
emit "linked=$TARGET" "to=$BUILD" "pack=$PACK" \
  "next=restart the session; the plugin loads as ai-workbench@skills-dir" \
  "fallback=claude --plugin-dir $BUILD"
