#!/usr/bin/env python3
"""Generate Claude Code agents from the core.

Usage: python3 adapters/claude-code/build.py [--dry-run]

Reads ../../agents/<name>.md, merges overrides/<name>.yaml (flat key: value lines) into the
frontmatter, and writes agents/<name>.md inside this adapter. Output folder is ignored by git.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORE_AGENTS = os.path.normpath(os.path.join(HERE, "..", "..", "agents"))
OVERRIDES = os.path.join(HERE, "overrides")
OUT = os.path.join(HERE, "agents")


def read_overrides(name):
    p = os.path.join(OVERRIDES, f"{name}.yaml")
    if not os.path.isfile(p):
        return []
    lines = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            s = line.rstrip("\n")
            if s.strip() and not s.lstrip().startswith("#"):
                lines.append(s)
    return lines


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    dry = "--dry-run" in argv
    if not os.path.isdir(CORE_AGENTS):
        print(f"Error: core agents folder not found: {CORE_AGENTS}", file=sys.stderr)
        return 1
    os.makedirs(OUT, exist_ok=True)
    built = []
    for fn in sorted(os.listdir(CORE_AGENTS)):
        if not fn.endswith(".md"):
            continue
        name = fn[:-3]
        with open(os.path.join(CORE_AGENTS, fn), encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---\n"):
            print(f"Error: {fn} has no frontmatter", file=sys.stderr)
            return 1
        end = content.find("\n---", 4)
        fm, body = content[4:end], content[end + 4:]
        extra = read_overrides(name)
        merged = fm.rstrip("\n") + ("\n" + "\n".join(extra) if extra else "") + "\n"
        out = f"---\n{merged}---{body}"
        built.append({"agent": name, "overrides": len(extra), "path": f"adapters/claude-code/agents/{fn}"})
        if not dry:
            with open(os.path.join(OUT, fn), "w", encoding="utf-8") as f:
                f.write(out)
    import json
    print(json.dumps({"dry_run": dry, "built": built}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
