#!/usr/bin/env python3
"""Lint a roadmap written from assets/roadmap-template.md against its PRD.

Usage: python3 lint_roadmap.py --file <roadmap.md> --prd <prd.md> [--report <path>] [--json]

--report <path> writes the record of the run to <path>: one JSON object with script, date, arguments, ok,
  summary, errors, warnings and counts, on every run that reaches the check, never on a usage error.

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

  - an OPEN that blocks an R- or F- id while the Readiness section does not say "no" (error)

Prints JSON on stdout. The "summary" field is one line to quote in the reply, for example
"lint_roadmap.py --file docs/product/roadmap.md --prd docs/product/prd.md: ok: true, 0 errors, 0 warnings".
A usage error goes to stderr.
Exit codes: 0 ok, 1 problems found, 2 usage error (a flag without its value, an unknown flag, a file that
cannot be read or written).
"""
import datetime
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


def parse_args(argv):
    """(values, None), or (None, a usage error). values maps each flag given to its value, a switch to True."""
    values, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a in ("--file", "--prd", "--report"):
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                return None, f"Error: {a} needs a value. See --help."
            values[a] = argv[i + 1]
            i += 2
        elif a == "--json":
            values[a] = True
            i += 1
        else:
            return None, f"Error: unknown option {a!r}. See --help."
    return values, None


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    values, problem = parse_args(argv)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    as_json, path, prd = "--json" in values, values.get("--file"), values.get("--prd")
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
    readiness = section(text, "Readiness")
    for oid, body in blocks_of(section(text, "Open questions"), ("OPEN-",)).items():
        for part in ("Blocks:", "Recommended:"):
            if part not in body:
                errors.append(f"{oid} lacks {part}")
        bm = re.search(r"Blocks:\s*([^.]*)", body)
        if bm and re.search(r"\b[RF]-\d+\b", bm.group(1)) and not re.search(r":\s*no\b", readiness):
            errors.append(f"{oid} blocks {bm.group(1).strip()} but the Readiness section does not say 'no, because {oid} blocks ...'")
    ok = not errors
    summary = (f"lint_roadmap.py --file {path} --prd {prd}: ok: {'true' if ok else 'false'}, "
               f"{len(errors)} errors, {len(warnings)} warnings")
    unplaced = sorted(f for f in prd_feats if f not in placed)
    print(json.dumps({"ok": ok, "summary": summary, "releases": order, "features": {k: v for k, v in placed.items()},
                      "unplaced": unplaced, "errors": errors, "warnings": warnings},
                     indent=2 if as_json else None))
    if "--report" in values:
        record = {"script": "lint_roadmap.py", "date": datetime.date.today().isoformat(),
                  "arguments": {k: v for k, v in values.items() if k != "--report"}, "ok": ok, "summary": summary,
                  "errors": errors, "warnings": warnings,
                  "counts": {"releases": len(order), "features": len(prd_feats), "placed": len(placed),
                             "unplaced": len(unplaced)}}
        try:
            with open(values["--report"], "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
                f.write("\n")
        except OSError as e:
            print(f"Error: cannot write the report {values['--report']}: {e}", file=sys.stderr)
            return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
