#!/usr/bin/env python3
"""Lint a product requirements document written from assets/prd-template.md.

Usage: python3 lint_prd.py --file <prd.md> [--json]

Checks:
  - required sections are present
  - ids (U, F, M, R, P, ASSUMPTION, OPEN) are unique
  - every U and F has a Source: line; every F has Priority: (must|should|later) and Phase:
  - every M has a number, a Baseline:, a Measured by: and a Source:
  - every P lists at least one F id and has an Exit: line; every must/should F appears in a P
  - every R has Trigger:, Impact: and Mitigation:
  - every OPEN has Blocks: and Recommended:
  - vague words on F/M lines without a number on the same line (warning)
  - dates (YYYY-MM-DD, or a month name with a year) on P/M lines without a Source: on the same block (warning)
  - TBD / TODO / ??? inside id blocks
  - REQ-/NFR-/AC- definitions or Given/When/Then, which belong to feature specs (error); citing a spec's ids as a source is fine

Prints JSON. Exit codes: 0 ok, 1 problems found, 2 usage error.
"""
import json
import re
import sys

SECTIONS = ["## Summary", "## Problem and goal", "## Users", "## Scope", "## Sources", "## Features", "## Success metrics",
            "## Constraints", "## Dependencies and risks", "## Release phases", "## Assumptions", "## Open questions", "## Readiness"]
VAGUE = ("fast", "quick", "responsive", "easy", "simple", "intuitive", "user-friendly", "scalable", "robust", "reliable", "secure",
         "seamless", "modern", "clean", "performant", "efficient", "engaging", "delightful")
ID_RE = re.compile(r"^\s*-\s*((?:U|F|M|R|P|ASSUMPTION|OPEN)-\d+)\s*:", re.M)
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b")


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        print(__doc__)
        return 0 if argv else 2
    path, as_json = None, "--json" in argv
    if "--file" in argv:
        i = argv.index("--file")
        path = argv[i + 1] if i + 1 < len(argv) else None
    if not path:
        print("Error: --file <prd.md> is required. See --help.", file=sys.stderr)
        return 2
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        print(f"Error: cannot read {path}: {e}", file=sys.stderr)
        return 2
    errors, warnings = [], []
    for s in SECTIONS:
        if s not in text:
            errors.append(f"missing section {s!r}")
    ids = ID_RE.findall(text)
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errors.append(f"duplicate ids: {sorted(dup)}")
    blocks, current = {}, None
    for ln in text.splitlines():
        m = ID_RE.match(ln)
        if m:
            current = m.group(1)
            blocks[current] = [ln]
        elif current and ln.startswith("  "):
            blocks[current].append(ln)
        else:
            current = None
    joined = {i: " ".join(b) for i, b in blocks.items()}
    # definitions of requirements or criteria (a "- REQ-1:" line), not citations of a spec's ids as a source
    if re.search(r"^\s*-\s*(REQ|NFR|AC)-\d+\s*:", text, re.M) or re.search(r"^\s*(Given|When|Then)\b", text, re.M):
        errors.append("defines REQ/NFR/AC items or Given/When/Then: requirements and acceptance criteria belong to feature specs")
    phased = set()
    for i, body in joined.items():
        if i.startswith(("U-", "F-")) and "Source:" not in body:
            errors.append(f"{i} has no Source: line")
        if i.startswith("F-"):
            pm = re.search(r"Priority:\s*(must|should|later)\b", body)
            if not pm:
                errors.append(f"{i} has no Priority: must|should|later")
            if "Phase:" not in body:
                errors.append(f"{i} has no Phase: line")
        if i.startswith("M-"):
            for part in ("Baseline:", "Measured by:", "Source:"):
                if part not in body:
                    errors.append(f"{i} lacks {part}")
            tm = re.search(r"Target:\s*([^.]*)", body)
            # an id inside the target ("Target: OPEN-2") is not a number
            if not tm or not re.search(r"\d", re.sub(r"\b(?:U|F|M|R|P|ASSUMPTION|OPEN)-\d+\b", "", tm.group(1))):
                errors.append(f"{i} has no numeric Target:")
        if i.startswith("P-"):
            feats = re.findall(r"\bF-\d+\b", body)
            if not feats:
                errors.append(f"{i} lists no F- feature")
            phased.update(feats)
            if "Exit:" not in body:
                errors.append(f"{i} has no Exit: line")
        if i.startswith("R-"):
            for part in ("Trigger:", "Impact:", "Mitigation:"):
                if part not in body:
                    errors.append(f"{i} lacks {part}")
        if i.startswith("OPEN-"):
            for part in ("Blocks:", "Recommended:"):
                if part not in body:
                    errors.append(f"{i} lacks {part}")
        if re.search(r"\b(TBD|TODO)\b|\?\?\?", body):
            errors.append(f"{i} contains TBD/TODO/???")
        if i.startswith(("F-", "M-")):
            for ln in blocks[i]:
                # digits inside ids (F-2, REQ-10) and source citations do not count as a number
                bare = re.sub(r"\b(?:U|F|M|R|P|REQ|NFR|EDGE|AC|ASSUMPTION|OPEN|T-[a-z]+|ADR)-\d+\b", "", ln)
                bare = re.sub(r"Source:.*$", "", bare)
                low = bare.lower()
                for w in VAGUE:
                    if re.search(r"\b" + re.escape(w) + r"\b", low) and not re.search(r"\d", bare):
                        warnings.append(f"{i}: vague word {w!r} without a number on the line: {ln.strip()[:90]}")
        if i.startswith(("P-", "M-")) and DATE_RE.search(body) and "Source:" not in body:
            warnings.append(f"{i} carries a date without a Source: line")
    for i, body in joined.items():
        if i.startswith("F-"):
            pm = re.search(r"Priority:\s*(must|should)\b", body)
            if pm and i not in phased:
                errors.append(f"{i} is {pm.group(1)} but appears in no P- phase")
    ok = not errors
    result = {"ok": ok, "counts": {k: sum(1 for i in blocks if i.startswith(k + "-")) for k in ("U", "F", "M", "R", "P", "ASSUMPTION", "OPEN")},
              "errors": errors, "warnings": warnings}
    print(json.dumps(result, indent=2 if as_json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
