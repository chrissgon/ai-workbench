#!/usr/bin/env python3
"""Lint a feature specification written from assets/spec-template.md.

Usage: python3 lint_spec.py --file <spec.md> [--json]

Checks:
  - required sections are present
  - ids (REQ, NFR, EDGE, AC, ASSUMPTION, OPEN) are unique
  - every REQ and NFR has a Source: line
  - every REQ and NFR is covered by at least one AC (Covers: line)
  - every AC has Given, When, Then and Covers lines
  - vague words on REQ/NFR/AC lines without a number on the same line (warnings)
  - every NFR states a number outside its Source: text (no number, no NFR)
  - every OPEN has a Blocks: and a Recommended: entry
  - every EDGE line has an arrow (→ or ->) with behaviour after it
  - TBD / TODO / ??? inside requirements
  - every bullet in an id section is written `- <ID>-n: ...` (no empty `-` bullet, no bullet without its id)

Prints JSON: ok, counts, errors, warnings, `report` (the line to paste into the reply) and `next` (what to do now). Exit codes: 0 ok, 1 problems found, 2 usage error.
"""
import json
import re
import sys

SECTIONS = ["## Summary", "## Goal and users", "## Scope", "## Sources", "## Functional requirements", "## Non-functional requirements",
            "## Constraints", "## Edge cases", "## Acceptance criteria", "## Assumptions", "## Open questions", "## Readiness"]
VAGUE = ("fast", "quick", "responsive", "easy", "simple", "intuitive", "user-friendly", "scalable", "robust", "reliable", "secure",
         "gracefully", "seamless", "modern", "clean", "performant", "efficient")
# section heading -> the id prefix every top-level bullet in it carries
ID_SECTIONS = {"## Functional requirements": "REQ", "## Non-functional requirements": "NFR", "## Edge cases": "EDGE",
               "## Acceptance criteria": "AC", "## Assumptions": "ASSUMPTION", "## Open questions": "OPEN"}
ID_RE = re.compile(r"^\s*-\s*((?:REQ|NFR|EDGE|AC|ASSUMPTION|OPEN)-\d+)\s*:", re.M)


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        print(__doc__)
        return 0 if argv else 2
    path, as_json = None, "--json" in argv
    if "--file" in argv:
        i = argv.index("--file")
        path = argv[i + 1] if i + 1 < len(argv) else None
    if not path:
        print("Error: --file <spec.md> is required. See --help.", file=sys.stderr)
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
    # split into id blocks: from an id line to the next id line or blank-line-terminated block
    blocks = {}
    lines = text.splitlines()
    current = None
    for ln in lines:
        m = ID_RE.match(ln)
        if m:
            current = m.group(1)
            blocks[current] = [ln]
        elif current and (ln.startswith("  ") or ln.strip() == "" and False):
            blocks[current].append(ln)
        elif ln.strip() == "" or ln.startswith("#") or ln.startswith("- ") and not m:
            current = None
    # shape of the bullets: a weak writer leaves empty "-" lines and bullets without their id, which the id checks cannot see
    section, empty, unspaced = None, [], []
    for n, ln in enumerate(lines, 1):
        if ln.startswith("## "):
            section = ln.strip()
            continue
        if ln.strip() == "-":
            empty.append(n)
            continue
        prefix = ID_SECTIONS.get(section)
        if not prefix or not ln.startswith("-"):
            continue
        if re.match(rf"-\s*{prefix}-\d+\s*:", ln):
            if not ln.startswith("- "):
                unspaced.append(n)
        elif prefix == "EDGE" and not re.search(r"→|->", ln):
            continue  # a note without an arrow (a skipped category and why) is not an edge case
        elif not re.match(r"-\s*(none\b|categories skipped)", ln, re.I):
            errors.append(f"line {n} in {section!r} is not '- {prefix}-n: ...': give it the next {prefix} id, or delete it: {ln.strip()[:60]}")
    if empty:
        errors.append(f"empty bullet '-' on lines {empty}: delete those lines")
    if unspaced:
        errors.append(f"no space after the dash on lines {unspaced}: write '- REQ-1: ...', not '-REQ-1: ...'")
    reqs = [i for i in blocks if i.startswith(("REQ-", "NFR-"))]
    acs = [i for i in blocks if i.startswith("AC-")]
    covered = set()
    for ac in acs:
        body = "\n".join(blocks[ac])
        for part in ("Given", "When", "Then", "Covers:"):
            if part not in body:
                errors.append(f"{ac} lacks {part}")
        m = re.search(r"Covers:\s*(.+)", body)
        if m:
            covered.update(re.findall(r"(?:REQ|NFR)-\d+", m.group(1)))
    for r in reqs:
        body = "\n".join(blocks[r])
        if "Source:" not in body:
            errors.append(f"{r} has no Source: line")
        if r not in covered:
            errors.append(f"{r} is not covered by any AC")
    for i, body_lines in blocks.items():
        if i.startswith(("REQ-", "NFR-", "AC-")):
            for ln in body_lines:
                # digits inside ids (F-2, REQ-10) and source citations do not count as a number
                bare = re.sub(r"\b(?:U|F|M|R|P|REQ|NFR|EDGE|AC|ASSUMPTION|OPEN|T-[a-z]+|ADR)-\d+\b", "", ln)
                bare = re.sub(r"Source:.*$", "", bare)
                low = bare.lower()
                for w in VAGUE:
                    if re.search(r"\b" + re.escape(w) + r"\b", low) and not re.search(r"\d", bare):
                        warnings.append(f"{i}: vague word {w!r} without a number on the line: {ln.strip()[:90]}")
            if re.search(r"\b(TBD|TODO)\b|\?\?\?", "\n".join(body_lines)):
                errors.append(f"{i} contains TBD/TODO/???")
    for i, body_lines in blocks.items():
        if i.startswith("EDGE-"):
            joined = " ".join(body_lines)
            if not re.search(r"(→|->)\s*\S", joined):
                errors.append(f"{i} has no '→ expected behaviour'")
    for i, body_lines in blocks.items():
        if i.startswith("OPEN-"):
            for part in ("Blocks:", "Recommended:"):
                if part not in " ".join(body_lines):
                    errors.append(f"{i} has no {part} entry")
        if i.startswith("NFR-"):
            # ids and the Source: citation do not count: the requirement itself must carry the figure
            bare = re.sub(r"\b(?:REQ|NFR|EDGE|AC|ASSUMPTION|OPEN)-\d+\b", "", " ".join(body_lines))
            bare = re.sub(r"Source:.*$", "", bare)
            if not re.search(r"\d", bare):
                errors.append(f"{i} states no number: give the sourced figure, or move it to an OPEN with a Recommended value")
    ok = not errors
    counts = {k: sum(1 for i in blocks if i.startswith(k + "-")) for k in ("REQ", "NFR", "EDGE", "AC", "ASSUMPTION", "OPEN")}
    report = (f"lint_spec.py --file {path}: ok: {'true' if ok else 'false'}, {len(errors)} errors, {len(warnings)} warnings ("
              + ", ".join(f"{v} {k}" for k, v in counts.items()) + ")")
    if errors or warnings:
        nxt = ("Not done. 1) If you have not edited the file yet, copy every error and warning above into your reply first. "
               "2) Fix each one from a source, or move the item to an OPEN with Blocks: and Recommended:. Never invent a number or a source. "
               "3) Run this command again.")
    else:
        nxt = "Lint passed. Paste the `report` line into your reply as the `- Lint:` line, then go to the next step."
    result = {"ok": ok, "counts": counts, "errors": errors, "warnings": warnings, "report": report, "next": nxt}
    print(json.dumps(result, indent=2 if as_json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
