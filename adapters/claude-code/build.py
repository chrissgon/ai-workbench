#!/usr/bin/env python3
"""Build an installable Claude Code plugin for one pack.

Usage: python3 adapters/claude-code/build.py [--pack <name>] [--prune] [--dry-run]
       python3 adapters/claude-code/build.py --clean [--dry-run]

Creates build/<pack>/ inside this adapter:
  .claude-plugin/plugin.json   copied from plugin.json
  skills/<name>                one symlink per selected skill into ../../skills
  shared/references            one symlink into ../../shared, so that a skill's
                               ../../shared/references/<file> resolves by the installed path
  agents/<name>.md             core agents merged with overrides/<name>.yaml

--prune   after the build, remove the builds of every other pack (install.sh does this: one pack
          is installed at a time, and an old build would keep skills the new pack dropped)
--clean   remove every build and exit (install.sh --uninstall does this)

The build folder is ignored by git; the adapter tracks no symlinks. Default pack: default.
Prints one JSON line. Exit codes: 0 ok, 2 usage error (unknown pack or option, a flag without its value).
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


def remove_builds(build_root, keep, dry):
    """Remove every entry of build/ except `keep`; returns the names removed. Links are unlinked, never followed."""
    removed = []
    if not os.path.isdir(build_root):
        return removed
    for name in sorted(os.listdir(build_root)):
        if name == keep:
            continue
        path = os.path.join(build_root, name)
        removed.append(name)
        if dry:
            continue
        if os.path.islink(path) or not os.path.isdir(path):
            os.unlink(path)
        else:
            shutil.rmtree(path)
    return removed


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    pack, dry = "default", "--dry-run" in argv
    known = ("--pack", "--prune", "--clean", "--dry-run")
    unknown = [a for i, a in enumerate(argv) if a not in known and not (i > 0 and argv[i - 1] == "--pack")]
    if unknown:
        print(f"Error: unknown option {unknown[0]!r}. See --help.", file=sys.stderr)
        return 2
    if "--clean" in argv:
        removed = remove_builds(os.path.join(HERE, "build"), None, dry)
        if not dry and os.path.isdir(os.path.join(HERE, "build")):
            os.rmdir(os.path.join(HERE, "build"))
        print(json.dumps({"dry_run": dry, "cleaned": removed}))
        return 0
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
    # resolve() accepts only a known pack name made of [a-z0-9-]; this check keeps the rmtree below
    # inside build/ even if that rule changes.
    build_root = os.path.realpath(os.path.join(HERE, "build"))
    out = os.path.join(HERE, "build", pack)
    if os.path.dirname(os.path.realpath(out)) != build_root or os.path.islink(out):
        print(f"Error: pack {pack!r} would build outside {build_root}.", file=sys.stderr)
        return 2
    if not dry:
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(os.path.join(out, ".claude-plugin"))
        os.makedirs(os.path.join(out, "skills"))
        os.makedirs(os.path.join(out, "agents"))
        shutil.copy(os.path.join(HERE, "plugin.json"), os.path.join(out, ".claude-plugin", "plugin.json"))
        for n in names:
            target = os.path.relpath(os.path.join(CORE_SKILLS, n), os.path.join(out, "skills"))
            os.symlink(target, os.path.join(out, "skills", n))
        os.makedirs(os.path.join(out, "shared"))
        os.symlink(os.path.relpath(os.path.join(ROOT, "shared", "references"), os.path.join(out, "shared")),
                   os.path.join(out, "shared", "references"))
        # The providers a skill may reach, so that the plugin carries what a skill needs of providers/:
        # a skill runs `python3 <workbench root>/providers/resolve.py --class <class>`.
        if os.path.isdir(os.path.join(ROOT, "providers")):
            os.symlink(os.path.relpath(os.path.join(ROOT, "providers"), out), os.path.join(out, "providers"))
    providers = ["providers"] if os.path.isdir(os.path.join(ROOT, "providers")) else []
    agents = build_agents(os.path.join(out, "agents"), dry)
    pruned = remove_builds(build_root, pack, dry) if "--prune" in argv else []
    print(json.dumps({"dry_run": dry, "pack": pack, "output": os.path.relpath(out, ROOT), "skills": len(names),
                      "shared": ["references"], "providers": providers, "agents": agents, "pruned": pruned}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
