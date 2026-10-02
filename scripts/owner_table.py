#!/usr/bin/env python3
"""Generate the table of owning skills in contracts/project-layout.md from the skills' frontmatter.

Usage:
  python3 scripts/owner_table.py            # rewrite the table in contracts/project-layout.md
  python3 scripts/owner_table.py --check    # exit 1 when the table in the file differs from the frontmatter
  python3 scripts/owner_table.py --print    # print the table and change nothing
  python3 scripts/owner_table.py --help

  --root <path>   the workbench checkout to read and write, instead of the one this script is in

The table has one row per artifact path: the skill whose `metadata.outputs` lists it (its owner) and the
skills whose `metadata.updates` lists it. Two paths are the same artifact when they are equal after every
placeholder (`<task>`) is replaced by a wildcard. The table sits between the lines `<!-- owner-table:begin -->`
and `<!-- owner-table:end -->`; nothing outside them is touched, and the block is never edited by hand.
A pull request that changes a skill's `inputs`, `outputs` or `updates` runs this script.

scripts/validate.py runs the same comparison as `--check` (rule contract-owner-table).

output: the table on stdout with --print; diagnostics on stderr.
exit codes: 0 ok (written, or up to date), 1 --check found a difference, 2 usage error or no markers.
Standard library only.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYOUT = "contracts/project-layout.md"
BEGIN, END = "<!-- owner-table:begin -->", "<!-- owner-table:end -->"
HEADER = ["| Artifact | Owning skill | Updated by |", "|----------|--------------|------------|"]
PLACEHOLDER_RE = re.compile(r"<[^<>]*>")
NONE = "-"


def artifact_key(path):
    """What makes two declared paths the same artifact: every placeholder read as a wildcard."""
    return PLACEHOLDER_RE.sub("*", str(path))


def rows(skills):
    """[(path, [owners], [updaters])] sorted by path. `skills` is a list of {name, outputs, updates}. A path
    only listed in `updates` still gets a row, with no owner, so that the table shows what the check reports."""
    spelled, owners, updaters = {}, {}, {}
    for field, index in (("outputs", owners), ("updates", updaters)):  # outputs first: the owner's spelling wins
        for s in sorted(skills, key=lambda s: s["name"]):
            for path in s.get(field) or []:
                if not isinstance(path, str):
                    continue
                key = artifact_key(path)
                spelled.setdefault(key, path)
                if s["name"] not in index.setdefault(key, []):
                    index[key].append(s["name"])
    return [(spelled[k], owners.get(k, []), updaters.get(k, [])) for k in sorted(spelled, key=lambda k: spelled[k])]


def table(skills):
    """The Markdown of the block between the markers, markers left out."""
    lines = list(HEADER)
    for path, owners, updaters in rows(skills):
        lines.append(f"| `{path}` | {', '.join(owners) or NONE} | {', '.join(updaters) or NONE} |")
    return "\n".join(lines) + "\n"


def split_block(text):
    """(before, block, after) around the markers, or None when the file has no pair of them."""
    start, end = text.find(BEGIN), text.find(END)
    if start == -1 or end == -1 or end < start:
        return None
    return text[:start + len(BEGIN)], text[start + len(BEGIN):end], text[end:]


def read_block(root=ROOT):
    """The block as the file holds it, or None when the file or its markers are missing."""
    path = os.path.join(root, LAYOUT)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        parts = split_block(f.read())
    return None if parts is None else parts[1]


def read_owners(root=ROOT):
    """{artifact key: [owner names]} as the committed table states them; {} when there is no table."""
    block, found = read_block(root), {}
    for line in (block or "").splitlines():
        m = re.match(r"\|\s*`([^`]+)`\s*\|([^|]*)\|", line)
        if m:
            names = [n.strip() for n in m.group(2).split(",") if n.strip() and n.strip() != NONE]
            found[artifact_key(m.group(1))] = names
    return found


def current(skills, root=ROOT):
    """True when the table in the file equals the one the frontmatter gives; None when there is no table."""
    block = read_block(root)
    return None if block is None else block.strip("\n") == table(skills).strip("\n")


def write(skills, root=ROOT):
    path = os.path.join(root, LAYOUT)
    with open(path, encoding="utf-8") as f:
        parts = split_block(f.read())
    if parts is None:
        raise ValueError(f"{LAYOUT} has no {BEGIN} ... {END} block")
    new = parts[0] + "\n" + table(skills) + parts[2]
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__.strip())
        return 0
    root, mode, i = ROOT, "write", 0
    while i < len(argv):
        a = argv[i]
        if a == "--root":
            if i + 1 >= len(argv):
                print("error: --root needs a path. See --help.", file=sys.stderr)
                return 2
            root, i = os.path.abspath(argv[i + 1]), i + 2
            continue
        if a not in ("--check", "--print"):
            print(f"error: unknown option {a!r}. See --help.", file=sys.stderr)
            return 2
        if mode != "write":
            print("error: give one of --check and --print. See --help.", file=sys.stderr)
            return 2
        mode, i = a[2:], i + 1
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import validate  # the one frontmatter parser
    skills = validate.declarations(root)
    if mode == "print":
        print(table(skills), end="")
        return 0
    if not os.path.isfile(os.path.join(root, LAYOUT)) or read_block(root) is None:
        print(f"error: {LAYOUT} is missing or has no {BEGIN} ... {END} block.", file=sys.stderr)
        return 2
    if mode == "check":
        if current(skills, root):
            return 0
        print(f"{LAYOUT}: the table of owning skills differs from the skills' frontmatter; "
              "run python3 scripts/owner_table.py", file=sys.stderr)
        return 1
    write(skills, root)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
