#!/usr/bin/env python3
"""Lint a roadmap written from assets/roadmap-template.md against its PRD.

Usage: python3 lint_roadmap.py --file <roadmap.md> --prd <prd.md> [--json]

Checks:
  - required sections are present; the Method section has a "Method:" line
  - every must/should feature of the PRD appears in exactly one R- release
  - every later feature of the PRD appears in a release or under "Not planned"
  - release ids are unique; every R- has Includes:, Order:, Exit: and Depends on: lines
  - every feature in Includes: exists in the PRD; every F- in the Dependencies section points at a
    feature placed in the same or an earlier release
  - every OPEN has Blocks: and Recommended:
  - dates (YYYY-MM-DD, or a month name with a year) on R- lines without a Source: (warning)
  - effort words (story points, weeks, days, hours, sprint) on R- lines (error)

Prints JSON. Exit codes: 0 ok, 1 problems found, 2 usage error.
"""
import json
import re
import sys

SECTIONS = ["## Summary", "## Sources", "## Method", "## Dependencies", "## Releases", "## Now, next, later",
            "## Risks by release", "## Not planned", "## Assumptions", "## Open questions", "## Readiness"]
ID_RE = re.compile(r"^\s*-\s*((?:R|F|ASSUMPTION|OPEN)-\d+)\s*:", re.M)
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b")
EFFORT_RE = re.compile(r"\b(story points?|weeks?|days?|hours?|sprints?)\b", re.I)


def blocks_of(text, prefixes):
    out, cur = {}, None
    for ln in text.splitlines():
        m = ID_RE.match(ln)
        if m and m.group(1).startswith(prefixes):
            cur = m.group(1)
            out[cur] = [ln]
        elif cur and ln.startswith("  "):
            out[cur].append(ln)
        else:
            cur = None
    return {k: " ".join(v) for k, v in out.items()}


def section(text, title):
    m = re.search(r"^## " + re.escape(title) + r"\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^## ", rest, re.M)
    return rest[: n.start()] if n else rest


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        print(__doc__)
        return 0 if argv else 2
    as_json = "--json" in argv
    path = prd = None
    if "--file" in argv:
        path = argv[argv.index("--file") + 1]
    if "--prd" in argv:
        prd = argv[argv.index("--prd") + 1]
    if not path or not prd:
        print("Error: --file <roadmap.md> and --prd <prd.md> are required. See --help.", file=sys.stderr)
        return 2
    try:
        text = open(path, encoding="utf-8").read()
        prd_text = open(prd, encoding="utf-8").read()
    except OSError as e:
        print(f"Error: cannot read input: {e}", file=sys.stderr)
        return 2
    errors, warnings = [], []
    for s in SECTIONS:
        if s not in text:
            errors.append(f"missing section {s!r}")
    if "Method:" not in section(text, "Method"):
        errors.append("Method section has no 'Method:' line")
    prd_feats = {}
    for fid, body in blocks_of(prd_text, ("F-",)).items():
        pm = re.search(r"Priority:\s*(must|should|later)\b", body)
        prd_feats[fid] = pm.group(1) if pm else "unknown"
    if not prd_feats:
        errors.append("the PRD defines no F- features")
    releases = blocks_of(section(text, "Releases"), ("R-",))
    placed = {}
    order = list(releases)
    for rid, body in releases.items():
        for part in ("Includes:", "Order:", "Exit:", "Depends on:"):
            if part not in body:
                errors.append(f"{rid} lacks {part}")
        inc = re.search(r"Includes:\s*([^.]*)", body)
        for fid in re.findall(r"\bF-\d+\b", inc.group(1) if inc else ""):
            if fid not in prd_feats:
                errors.append(f"{rid} includes {fid}, which the PRD does not define")
            placed.setdefault(fid, []).append(rid)
        if DATE_RE.search(body) and "Source:" not in body:
            warnings.append(f"{rid} carries a date without a Source: line")
        if EFFORT_RE.search(body):
            errors.append(f"{rid} states effort or duration: {EFFORT_RE.search(body).group(0)!r}")
    not_planned = section(text, "Not planned")
    for fid, pr in prd_feats.items():
        n = len(placed.get(fid, []))
        if pr in ("must", "should") and n != 1:
            errors.append(f"{fid} ({pr}) is in {n} releases; must be exactly one")
        if pr == "later" and n == 0 and fid not in not_planned:
            errors.append(f"{fid} (later) is neither in a release nor under Not planned")
    rank = {rid: i for i, rid in enumerate(order)}
    deps = blocks_of(section(text, "Dependencies"), ("F-",))
    for fid, body in deps.items():
        m = re.search(r"Depends on:\s*([^.]*)", body)
        if not m:
            errors.append(f"{fid} in Dependencies has no 'Depends on:' line")
            continue
        for d in re.findall(r"\bF-\d+\b", m.group(1)):
            if d not in prd_feats:
                errors.append(f"{fid} depends on {d}, which the PRD does not define")
            elif fid in placed and d in placed:
                if rank[placed[d][0]] > rank[placed[fid][0]]:
                    errors.append(f"{fid} (in {placed[fid][0]}) depends on {d}, which ships later in {placed[d][0]}")
            elif fid in placed and d not in placed:
                errors.append(f"{fid} depends on {d}, which is in no release")
    for oid, body in blocks_of(text, ("OPEN-",)).items():
        for part in ("Blocks:", "Recommended:"):
            if part not in body:
                errors.append(f"{oid} lacks {part}")
    ok = not errors
    print(json.dumps({"ok": ok, "releases": order, "features": {k: v for k, v in placed.items()},
                      "unplaced": sorted(f for f in prd_feats if f not in placed), "errors": errors, "warnings": warnings},
                     indent=2 if as_json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
