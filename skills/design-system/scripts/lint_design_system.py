#!/usr/bin/env python3
"""Lint a design-system document written from assets/design-system-template.md.

Usage: python3 lint_design_system.py --file <design-system.md> [--library <token file>] [--json]

Checks:
  - required sections are present
  - every row of the Colour table has a light value, a dark value (or "same") and a source
  - every row of the Contrast table has two ratios and an AA result
  - the Type section states a typeface and a reading width, and every type role row has size, line height and weight
  - every row of the Components table has owner, variants, states, screens and source
  - no TBD / TODO / ??? anywhere
  - with --library: every custom property matching --pui-[a-z-]+ in the library file appears in the document

Prints JSON. Exit codes: 0 ok, 1 problems found, 2 usage error.
"""
import json
import re
import sys

SECTIONS = ["## Summary", "## Sources", "## Ownership", "## Colour", "## Contrast", "## Type", "## Space, radii, borders, elevation",
            "## Layout", "## Components", "## Design tool", "## Assumptions", "## Open questions", "## Readiness"]
COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}\b|rgba?\(|oklch\(|light-dark\(|\bsame\b|\bnone\b|\btransparent\b|\d+%")


def section(text, title):
    m = re.search(r"^## " + re.escape(title) + r"\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^## ", rest, re.M)
    return rest[: n.start()] if n else rest


def rows(sec):
    out = []
    for ln in sec.splitlines():
        if ln.startswith("|") and not re.match(r"^\|\s*-", ln) and not re.match(r"^\|\s*(Token|Text token|Role|Component)\s*\|", ln):
            out.append([c.strip() for c in ln.strip().strip("|").split("|")])
    return out


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        print(__doc__)
        return 0 if argv else 2
    as_json = "--json" in argv
    path = lib = None
    if "--file" in argv:
        path = argv[argv.index("--file") + 1]
    if "--library" in argv:
        lib = argv[argv.index("--library") + 1]
    if not path:
        print("Error: --file <design-system.md> is required. See --help.", file=sys.stderr)
        return 2
    try:
        text = open(path, encoding="utf-8").read()
        lib_text = open(lib, encoding="utf-8").read() if lib else ""
    except OSError as e:
        print(f"Error: cannot read input: {e}", file=sys.stderr)
        return 2
    errors = []
    for s in SECTIONS:
        if s not in text:
            errors.append(f"missing section {s!r}")
    if re.search(r"\b(TBD|TODO)\b|\?\?\?", text):
        errors.append("contains TBD/TODO/???")
    colour = rows(section(text, "Colour"))
    for r in colour:
        if len(r) < 5:
            errors.append(f"colour row {r[0] if r else '?'} has fewer than 5 cells"); continue
        if not COLOR_RE.search(r[1]) or not COLOR_RE.search(r[2]):
            errors.append(f"colour row {r[0]} lacks a light or dark value")
        if not r[4]:
            errors.append(f"colour row {r[0]} has no source")
    contrast = rows(section(text, "Contrast"))
    for r in contrast:
        if len(r) < 5 or not re.search(r"\d+(\.\d+)?:1", r[2]) or not re.search(r"\d+(\.\d+)?:1", r[3]) or not re.search(r"\b(pass|fail)\b", r[4], re.I):
            errors.append(f"contrast row {r[0] if r else '?'} needs two ratios and pass/fail")
    typ = section(text, "Type")
    if not re.search(r"Typeface:\s*\S", typ):
        errors.append("Type section has no 'Typeface:' line")
    if not re.search(r"Reading width:\s*\S", typ):
        errors.append("Type section has no 'Reading width:' line")
    for r in rows(typ):
        if len(r) < 5 or not re.search(r"\d", r[1]) or not re.search(r"\d", r[2]) or not r[3]:
            errors.append(f"type role row {r[0] if r else '?'} needs size, line height and weight")
    comps = rows(section(text, "Components"))
    for r in comps:
        if len(r) < 6 or any(not c for c in r[:6]):
            errors.append(f"component row {r[0] if r else '?'} needs owner, variants, states, screens and source")
    missing = []
    if lib_text:
        props = sorted(set(re.findall(r"--pui-[a-z][a-z0-9-]*", lib_text)))
        missing = [p for p in props if p not in text]
        if missing:
            errors.append(f"library custom properties absent from the document: {missing}")
    ok = not errors
    print(json.dumps({"ok": ok, "counts": {"colour": len(colour), "contrast": len(contrast), "components": len(comps)},
                      "errors": errors}, indent=2 if as_json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
