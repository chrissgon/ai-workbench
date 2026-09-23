#!/usr/bin/env python3
"""Build an installable Claude Code plugin for one pack.

Usage: python3 adapters/claude-code/build.py [--pack <name>] [--dry-run]

Creates build/<pack>/ inside this adapter:
  .claude-plugin/plugin.json   copied from plugin.json
  skills/<name>                one symlink per selected skill into ../../skills
  agents/<name>.md             core agents merged with overrides/<name>.yaml

The build folder is ignored by git; the adapter tracks no symlinks. Default pack: default.
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from select_skills import resolve  # noqa: E402

CORE_AGENTS = os.path.join(ROOT, "agents")
CORE_SKILLS = os.path.join(ROOT, "skills")
OVERRIDES = os.path.join(HERE, "overrides")


def read_overrides(name):
    p = os.path.join(OVERRIDES, f"{name}.yaml")
    if not os.path.isfile(p):
        return []
    with open(p, encoding="utf-8") as f:
        return [l.rstrip("\n") for l in f if l.strip() and not l.lstrip().startswith("#")]


def build_agents(out_dir, dry):
    built = []
    if not os.path.isdir(CORE_AGENTS):
        return built
    for fn in sorted(os.listdir(CORE_AGENTS)):
        if not fn.endswith(".md"):
            continue
        with open(os.path.join(CORE_AGENTS, fn), encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---\n"):
            raise ValueError(f"{fn} has no frontmatter")
        end = content.find("\n---", 4)
        fm, body = content[4:end], content[end + 4:]
        extra = read_overrides(fn[:-3])
        merged = fm.rstrip("\n") + ("\n" + "\n".join(extra) if extra else "") + "\n"
        built.append({"agent": fn[:-3], "overrides": len(extra)})
        if not dry:
            with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as f:
                f.write(f"---\n{merged}---{body}")
    return built


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    pack, dry = "default", "--dry-run" in argv
    if "--pack" in argv:
        i = argv.index("--pack")
        if i + 1 >= len(argv):
            print("Error: --pack needs a value.", file=sys.stderr)
            return 2
        pack = argv[i + 1]
    try:
        names = resolve(pack=pack)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    out = os.path.join(HERE, "build", pack)
    if not dry:
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(os.path.join(out, ".claude-plugin"))
        os.makedirs(os.path.join(out, "skills"))
        os.makedirs(os.path.join(out, "agents"))
        shutil.copy(os.path.join(HERE, "plugin.json"), os.path.join(out, ".claude-plugin", "plugin.json"))
        for n in names:
            target = os.path.relpath(os.path.join(CORE_SKILLS, n), os.path.join(out, "skills"))
            os.symlink(target, os.path.join(out, "skills", n))
    agents = build_agents(os.path.join(out, "agents"), dry)
    print(json.dumps({"dry_run": dry, "pack": pack, "output": os.path.relpath(out, ROOT), "skills": len(names), "agents": agents}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
