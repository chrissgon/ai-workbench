#!/usr/bin/env python3
"""Keep the generated copies of shared files identical to their one source.

A skill is installed on its own, so a script two skills use cannot be imported from a common place: each
skill carries a copy. The source of every such script is shared/scripts/, with its tests; the copies are
generated from it, byte for byte, and never edited by hand. The manifest shared/scripts/copies.json says
which file is copied where.

Usage:
  python3 scripts/sync_copies.py                    # write every adopted copy again from its source
  python3 scripts/sync_copies.py --check            # exit 1 and name each adopted copy that differs
  python3 scripts/sync_copies.py --adopt <copy>...  # write these copies and mark them adopted
  python3 scripts/sync_copies.py --list             # the manifest as JSON, each copy with its state
  python3 scripts/sync_copies.py --destinations     # the path of every copy, one per line
  python3 scripts/sync_copies.py --help

  --root <path>   the workbench checkout to work in, instead of the one this script is in

The manifest:
  {"copies": [
    {"source": "shared/scripts/rank.py",
     "to": [{"path": "skills/<skill>/scripts/rank.py", "adopted": false}]},
    {"source": "contracts/environment.md", "between": ["<begin marker>", "<end marker>"], "header": "# Title\\n",
     "to": [{"path": "skills/<skill>/references/<name>.md", "adopted": false}]}
  ]}
An entry without "between" copies the whole source file. With "between", the copy is the "header" (optional),
an empty line, and the lines of the source between the two marker lines: a table that a contract holds and a
skill needs a copy of.

Adopted. A copy listed with "adopted": false is one that still differs from its source, or does not exist
yet, because the change that adopts it has not been made: --check and the plain write leave it alone, and
scripts/validate.py lists it as a warning. --adopt <copy> writes it from the source and sets the flag; it is
what the pull request that changes that skill runs, once. From then on a hand edit of the copy fails
--check, which the validator and the pre-commit hook run. A change of behaviour is made in the source and
followed by a plain write.

output: a JSON summary on stdout (--list: the manifest with states; --destinations: plain lines);
diagnostics on stderr.
exit codes: 0 ok, 1 --check found a difference, 2 usage error or a manifest that cannot be used.
Standard library only.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = "shared/scripts/copies.json"


class ManifestError(ValueError):
    """The manifest is missing, is not valid, or names a file that cannot be used."""


def _relative(path, what):
    if not isinstance(path, str) or not path or os.path.isabs(path) or ".." in path.split("/") or "\\" in path:
        raise ManifestError(f"{what} must be a path relative to the repository root, without '..': {path!r}")
    return path


def load_manifest(root=ROOT):
    """The entries of the manifest, checked: [{"source", "between", "header", "to": [{"path", "adopted"}]}]."""
    path = os.path.join(root, MANIFEST)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except OSError as e:
        raise ManifestError(f"{MANIFEST} cannot be read: {e}")
    except ValueError as e:
        raise ManifestError(f"{MANIFEST} is not valid JSON: {e}")
    copies = data.get("copies") if isinstance(data, dict) else None
    if not isinstance(copies, list):
        raise ManifestError(f"{MANIFEST} must be an object with a list \"copies\"")
    seen, entries = {}, []
    for n, entry in enumerate(copies, 1):
        if not isinstance(entry, dict) or set(entry) - {"source", "between", "header", "to"}:
            raise ManifestError(f"{MANIFEST}, entry {n}: an entry has source, to, and optionally between and header")
        source = _relative(entry.get("source"), f"entry {n}: source")
        between, header = entry.get("between"), entry.get("header", "")
        if between is not None and not (isinstance(between, list) and len(between) == 2
                                        and all(isinstance(m, str) and m.strip() for m in between)):
            raise ManifestError(f"{MANIFEST}, entry {n}: between is a list of two marker lines")
        if not isinstance(header, str) or (header and between is None):
            raise ManifestError(f"{MANIFEST}, entry {n}: header is a text, and goes with between")
        to = entry.get("to")
        if not isinstance(to, list) or not to:
            raise ManifestError(f"{MANIFEST}, entry {n}: to is a non-empty list of copies")
        for copy in to:
            if not isinstance(copy, dict) or set(copy) != {"path", "adopted"} or not isinstance(copy["adopted"], bool):
                raise ManifestError(f"{MANIFEST}, entry {n}: a copy is {{\"path\": ..., \"adopted\": true|false}}")
            dest = _relative(copy["path"], f"entry {n}: a copy's path")
            if dest in seen or dest == source or dest == MANIFEST:
                raise ManifestError(f"{MANIFEST}, entry {n}: {dest} is listed twice, or is a source")
            seen[dest] = source
        entries.append({"source": source, "between": between, "header": header, "to": to})
    for dest in seen:
        if dest in {e["source"] for e in entries}:
            raise ManifestError(f"{MANIFEST}: {dest} is a copy and a source")
    return entries


def expected(entry, root=ROOT):
    """The bytes every copy of an entry must hold."""
    path = os.path.join(root, entry["source"])
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        raise ManifestError(f"the source {entry['source']} cannot be read: {e}")
    if entry["between"] is None:
        return data
    begin, end = entry["between"]
    lines = data.decode("utf-8").split("\n")
    try:
        start = lines.index(begin)
        stop = lines.index(end, start + 1)
    except ValueError:
        raise ManifestError(f"the source {entry['source']} has no lines {begin!r} ... {end!r}")
    block = "\n".join(lines[start + 1:stop]).strip("\n")
    header = entry["header"].strip("\n")
    return ((header + "\n\n" if header else "") + block + "\n").encode("utf-8")


def states(root=ROOT):
    """[{"source", "path", "adopted", "state"}] for every copy; state is identical, differs or missing."""
    rows = []
    for entry in load_manifest(root):
        want = expected(entry, root)
        for copy in entry["to"]:
            path = os.path.join(root, copy["path"])
            if not os.path.isfile(path):
                state = "missing"
            else:
                with open(path, "rb") as f:
                    state = "identical" if f.read() == want else "differs"
            rows.append({"source": entry["source"], "path": copy["path"], "adopted": copy["adopted"], "state": state})
    return rows


def check(root=ROOT):
    """The adopted copies that are not identical to their source: [{"source", "path", "state"}]."""
    return [r for r in states(root) if r["adopted"] and r["state"] != "identical"]


def write(root=ROOT, only=None):
    """Write the adopted copies (or the copies named in `only`, adopted or not) from their source. Returns the
    paths whose bytes changed."""
    changed = []
    for entry in load_manifest(root):
        want = expected(entry, root)
        for copy in entry["to"]:
            if (copy["path"] not in only) if only is not None else (not copy["adopted"]):
                continue
            path = os.path.join(root, copy["path"])
            have = None
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    have = f.read()
            if have != want:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as f:
                    f.write(want)
                changed.append(copy["path"])
    return changed


def adopt(paths, root=ROOT):
    """Write the named copies and set their flag in the manifest. Returns the paths whose bytes changed."""
    entries = load_manifest(root)
    known = {copy["path"] for entry in entries for copy in entry["to"]}
    unknown = [p for p in paths if p not in known]
    if unknown:
        raise ManifestError(f"not a copy listed in {MANIFEST}: {', '.join(unknown)}")
    changed = write(root, only=set(paths))
    for entry in entries:
        for copy in entry["to"]:
            if copy["path"] in paths:
                copy["adopted"] = True
    save_manifest(entries, root)
    return changed


def save_manifest(entries, root=ROOT):
    out = []
    for entry in entries:
        row = {"source": entry["source"]}
        if entry["between"] is not None:
            row["between"] = entry["between"]
            if entry["header"]:
                row["header"] = entry["header"]
        row["to"] = entry["to"]
        out.append(row)
    with open(os.path.join(root, MANIFEST), "w", encoding="utf-8") as f:
        f.write(json.dumps({"copies": out}, indent=1, ensure_ascii=False) + "\n")


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__.strip())
        return 0
    root, mode, paths, i = ROOT, None, [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--root":
            if i + 1 >= len(argv):
                print("error: --root needs a path. See --help.", file=sys.stderr)
                return 2
            root, i = os.path.abspath(argv[i + 1]), i + 2
            continue
        if a in ("--check", "--adopt", "--list", "--destinations"):
            if mode:
                print("error: give one of --check, --adopt, --list and --destinations. See --help.", file=sys.stderr)
                return 2
            mode = a[2:]
        elif a.startswith("-") or mode != "adopt":
            print(f"error: unknown argument {a!r}. See --help.", file=sys.stderr)
            return 2
        else:
            paths.append(a.replace(os.sep, "/"))
        i += 1
    if mode == "adopt" and not paths:
        print("error: --adopt needs at least one copy, as the manifest lists it. See --help.", file=sys.stderr)
        return 2
    try:
        if mode == "list":
            print(json.dumps({"manifest": MANIFEST, "copies": states(root)}, indent=1))
        elif mode == "destinations":
            print("\n".join(r["path"] for r in states(root)))
        elif mode == "check":
            found = check(root)
            for r in found:
                print(f"{r['path']}: {r['state']}; it is a generated copy of {r['source']}: change the source, then "
                      "run python3 scripts/sync_copies.py", file=sys.stderr)
            print(json.dumps({"checked": sum(r["adopted"] for r in states(root)), "different": len(found),
                              "ok": not found}))
            return 1 if found else 0
        elif mode == "adopt":
            print(json.dumps({"adopted": paths, "written": adopt(paths, root)}))
        else:
            print(json.dumps({"written": write(root)}))
    except ManifestError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
