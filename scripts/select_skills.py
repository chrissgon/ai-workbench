#!/usr/bin/env python3
"""Resolve which skills a pack or filter selects.

Usage: python3 scripts/select_skills.py [--pack <name>] [--areas a,b] [--skills x,y] [--lines]

With no options, resolves packs/default.txt. Filters combine by intersection:
--pack narrows to the pack, --areas keeps only those metadata.area values, --skills keeps
only the listed names. Prints a JSON array to stdout (or one name per line with --lines).

Pack file format (packs/<name>.txt): one pattern per line, '#' comments;
  eng-*               glob on skill name
  area:engineering    every skill with that metadata.area
  !asst-*             exclusion, applied after inclusions
  biz-business-model  exact name

Exit codes: 0 ok, 2 usage error (unknown pack, bad option).
"""
import fnmatch
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from validate import load_yaml, split_frontmatter  # noqa: E402

SKILLS = os.path.join(ROOT, "skills")
PACKS = os.path.join(ROOT, "packs")


def all_skills():
    out = {}
    if not os.path.isdir(SKILLS):
        return out
    for d in sorted(os.listdir(SKILLS)):
        p = os.path.join(SKILLS, d, "SKILL.md")
        if not os.path.isfile(p):
            continue
        area = None
        fm_text, _ = split_frontmatter(p)
        if fm_text:
            try:
                area = ((load_yaml(fm_text) or {}).get("metadata") or {}).get("area")
            except Exception:  # noqa: BLE001
                area = None
        out[d] = area
    return out


def available_packs():
    return sorted(f[:-4] for f in os.listdir(PACKS) if f.endswith(".txt")) if os.path.isdir(PACKS) else []


def read_pack(name):
    # A pack name also names build folders (adapters/<harness>/build/<pack>), so only a known name
    # made of [a-z0-9-] is accepted: never a path.
    available = available_packs()
    if not re.fullmatch(r"[a-z0-9-]+", name or "") or name not in available:
        raise FileNotFoundError(f"pack {name!r} not found. Available: {available}")
    p = os.path.join(PACKS, f"{name}.txt")
    inc, exc = [], []
    with open(p, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            (exc if s.startswith("!") else inc).append(s.lstrip("!"))
    return inc, exc


def matches(pattern, name, area):
    if pattern.startswith("area:"):
        return area == pattern[5:]
    return fnmatch.fnmatchcase(name, pattern)


def resolve(pack=None, areas=None, skills=None):
    catalog = all_skills()
    selected = set(catalog)
    if pack:
        inc, exc = read_pack(pack)
        selected = {n for n in catalog if any(matches(p, n, catalog[n]) for p in inc)}
        selected -= {n for n in catalog if any(matches(p, n, catalog[n]) for p in exc)}
    if areas:
        selected &= {n for n in catalog if catalog[n] in areas}
    if skills:
        selected &= set(skills)
    return sorted(selected)


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    pack, areas, skills, lines = None, None, None, False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--pack", "--areas", "--skills"):
            if i + 1 >= len(argv):
                print(f"Error: {a} needs a value. See --help.", file=sys.stderr)
                return 2
            v = argv[i + 1]
            if a == "--pack":
                pack = v
            elif a == "--areas":
                areas = {x.strip() for x in v.split(",") if x.strip()}
            else:
                skills = {x.strip() for x in v.split(",") if x.strip()}
            i += 2
        elif a == "--lines":
            lines = True
            i += 1
        else:
            print(f"Error: unknown option {a!r}. See --help.", file=sys.stderr)
            return 2
    if pack is None and areas is None and skills is None:
        pack = "default"
    try:
        names = resolve(pack, areas, skills)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    print("\n".join(names) if lines else json.dumps(names))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
