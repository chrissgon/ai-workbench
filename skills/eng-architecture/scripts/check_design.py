#!/usr/bin/env python3
"""Check a design document against its specification and its ADRs.

Usage: python3 check_design.py --spec <spec.md> --design <design.md> [--adr-dir <dir>] [--json]

Checks:
  - every REQ-n, NFR-n, EDGE-n and AC-n id in the specification appears in the design
  - required design sections are present
  - every ADR referenced in the design (ADR-NNNN) exists in --adr-dir
  - every ADR file in --adr-dir has Status, Context, Options with at least two "### Option" entries,
    Decision and Consequences
  - the verification plan has at least one row per AC (an AC id inside the Verification plan section)

Prints JSON. Exit codes: 0 ok, 1 problems, 2 usage error.
"""
import glob
import json
import os
import re
import sys

DESIGN_SECTIONS = ["## Summary", "## Sources", "## Decisions", "## Components", "## Data or content model", "## Contracts",
                   "## Flows", "## Verification plan", "## Traceability"]
ADR_SECTIONS = ["## Context", "## Options", "## Decision", "## Consequences"]
ID_RE = re.compile(r"\b((?:REQ|NFR|EDGE|AC)-\d+)\b")

DEF_RE = re.compile(r"^\s*-\s*((?:REQ|NFR|EDGE|AC)-\d+)\s*(?:\([^)]*\))?:", re.M)


def defined_ids(spec_text):
    """Ids the specification defines (`- REQ-n:` lines); a definition line saying "withdrawn" is excluded.

    Ids that only appear as citations of another document (\"content-model spec REQ-10\") are not
    this specification's requirements and are not returned. Falls back to every id mentioned when
    the specification defines none in this form.
    """
    ids = set(DEF_RE.findall(spec_text))
    if not ids:
        return set(ID_RE.findall(spec_text))
    for line in spec_text.splitlines():
        m = DEF_RE.match(line)
        if m and "withdrawn" in line.lower():
            ids.discard(m.group(1))
    return ids



def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def section(text, heading):
    i = text.find(heading)
    if i == -1:
        return ""
    rest = text[i + len(heading):]
    m = re.search(r"^## ", rest, re.M)
    return rest[: m.start()] if m else rest


def main(argv):
    if not argv or "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0 if argv else 2
    spec = design = adr_dir = None
    as_json = "--json" in argv
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--spec": spec = argv[i + 1]; i += 2
        elif a == "--design": design = argv[i + 1]; i += 2
        elif a == "--adr-dir": adr_dir = argv[i + 1]; i += 2
        elif a == "--json": i += 1
        else:
            print(f"Error: unknown option {a!r}. See --help.", file=sys.stderr)
            return 2
    if not spec or not design or not os.path.isfile(spec) or not os.path.isfile(design):
        print("Error: --spec and --design must be existing files. See --help.", file=sys.stderr)
        return 2
    s, d = read(spec), read(design)
    errors, warnings = [], []
    spec_ids = sorted(defined_ids(s), key=lambda x: (x.split("-")[0], int(x.split("-")[1])))
    design_ids = set(ID_RE.findall(d))
    missing = [i for i in spec_ids if i not in design_ids]
    if missing:
        errors.append(f"ids from the spec not mentioned in the design: {missing}")
    for h in DESIGN_SECTIONS:
        if h not in d:
            errors.append(f"design lacks section {h!r}")
    plan = section(d, "## Verification plan")
    plan_acs = set(re.findall(r"\bAC-\d+\b", plan))
    spec_acs = [i for i in spec_ids if i.startswith("AC-")]
    unplanned = [a for a in spec_acs if a not in plan_acs]
    if unplanned:
        errors.append(f"acceptance criteria without a row in the verification plan: {unplanned}")
    referenced = sorted(set(re.findall(r"\bADR-(\d{4})\b", d)))
    adr_files = sorted(glob.glob(os.path.join(adr_dir, "*.md"))) if adr_dir and os.path.isdir(adr_dir) else []
    existing = {os.path.basename(f)[:4] for f in adr_files}
    for n in referenced:
        if n not in existing:
            errors.append(f"ADR-{n} referenced but no file {n}-*.md in {adr_dir or '(no --adr-dir)'}")
    adr_report = []
    for f in adr_files:
        t = read(f)
        probs = [h for h in ADR_SECTIONS if h not in t]
        if "- Status:" not in t:
            probs.append("Status line")
        n_opts = len(re.findall(r"^### Option", t, re.M))
        if n_opts < 2:
            probs.append(f"only {n_opts} option(s)")
        adr_report.append({"file": os.path.basename(f), "ok": not probs, "problems": probs})
        if probs:
            errors.append(f"{os.path.basename(f)}: {', '.join(probs)}")
    ok = not errors
    print(json.dumps({"ok": ok, "spec_ids": len(spec_ids), "covered": len(spec_ids) - len(missing), "adrs": adr_report,
                      "errors": errors, "warnings": warnings}, indent=2 if as_json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
