#!/usr/bin/env python3
"""Lint a UX flows document written from assets/flows-template.md against its PRD.

Usage: python3 lint_flows.py --file <flows.md> --prd <prd.md> [--phase P-n] [--report <lint.json>] [--json]

--report <path> also writes the result to that file, with the command's own arguments ("file", "prd",
"phase") and the date, so a reviewer can check the lint ran and what it checked.

Checks:
  - required sections are present; ids (IA, SCREEN, FLOW, ASSUMPTION, OPEN) are unique
  - every IA has Parent:, URL:, Filled by: and Source:
  - every SCREEN has Purpose:, Regions:, States:, Breakpoints: and Source:
  - screen-states: every SCREEN names at least one state called `empty` or `error` in States: (for a
    message such as an email or a notification, the error state is the delivery failure)
  - every FLOW has Actor: U-n, Trigger:, Steps:, End:, Failures:, Keyboard: and Source:, and its
    steps name at least one SCREEN- that exists
  - every SCREEN is named by at least one FLOW
  - every must/should feature of the PRD (in the given phase, when --phase is set) has a Coverage line
  - every Coverage line names FLOW-/SCREEN- ids that exist, or "no screen:" with a reason
  - every OPEN has Blocks: and Recommended:

Prints JSON. Exit codes: 0 ok, 1 problems found, 2 usage error.
"""
import datetime
import json
import re
import sys

SECTIONS = ["## Summary", "## Sources", "## Information architecture", "## Screens", "## Flows", "## Coverage",
            "## Assumptions", "## Open questions", "## Readiness"]
STATES_RE = re.compile(r"States:\s*(.*?)(?=\s*(?:Purpose|Regions|Breakpoints|Source):|$)")
ID_RE = re.compile(r"^\s*-\s*((?:IA|SCREEN|FLOW|ASSUMPTION|OPEN|F)-\d+)\s*:", re.M)


def blocks(text, prefixes):
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
    path = prd = phase = report = None
    for flag in ("--file", "--prd", "--phase", "--report"):
        if flag in argv:
            if argv.index(flag) + 1 >= len(argv):
                print(f"Error: {flag} needs a value.", file=sys.stderr)
                return 2
            val = argv[argv.index(flag) + 1]
            if flag == "--file": path = val
            elif flag == "--prd": prd = val
            elif flag == "--phase": phase = val
            else: report = val
    if not path or not prd:
        print("Error: --file <flows.md> and --prd <prd.md> are required. See --help.", file=sys.stderr)
        return 2
    try:
        text = open(path, encoding="utf-8").read()
        prd_text = open(prd, encoding="utf-8").read()
    except OSError as e:
        print(f"Error: cannot read input: {e}", file=sys.stderr)
        return 2
    errors = []
    for s in SECTIONS:
        if s not in text:
            errors.append(f"missing section {s!r}")
    ids = [i for i in ID_RE.findall(text) if not i.startswith("F-")]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errors.append(f"duplicate ids: {sorted(dup)}")
    ia = blocks(section(text, "Information architecture"), ("IA-",))
    screens = blocks(section(text, "Screens"), ("SCREEN-",))
    flows = blocks(section(text, "Flows"), ("FLOW-",))
    for i, b in ia.items():
        for part in ("Parent:", "URL:", "Filled by:", "Source:"):
            if part not in b:
                errors.append(f"{i} lacks {part}")
    for i, b in screens.items():
        for part in ("Purpose:", "Regions:", "States:", "Breakpoints:", "Source:"):
            if part not in b:
                errors.append(f"{i} lacks {part}")
        sm = STATES_RE.search(b)
        if sm and not re.search(r"\b(?:empty|error)\b", sm.group(1), re.I):
            errors.append(f"screen-states: {i} names no empty or error state in States: "
                          "(for a message, the error state is the delivery failure)")
    crossed = set()
    for i, b in flows.items():
        for part in ("Trigger:", "Steps:", "End:", "Failures:", "Keyboard:", "Source:"):
            if part not in b:
                errors.append(f"{i} lacks {part}")
        if not re.search(r"Actor:\s*U-\d+", b):
            errors.append(f"{i} lacks Actor: U-n")
        named = set(re.findall(r"\bSCREEN-\d+\b", b))
        if not named:
            errors.append(f"{i} names no SCREEN- in its steps")
        for s in named:
            if s not in screens:
                errors.append(f"{i} names {s}, which is not listed under Screens")
        crossed |= named
    for s in screens:
        if s not in crossed:
            errors.append(f"{s} is crossed by no flow")
    prd_feats = {}
    for fid, body in blocks(prd_text, ("F-",)).items():
        pm = re.search(r"Priority:\s*(must|should|later)\b", body)
        ph = re.search(r"Phase:\s*(P-\d+)", body)
        prd_feats[fid] = (pm.group(1) if pm else "unknown", ph.group(1) if ph else None)
    coverage = blocks(section(text, "Coverage"), ("F-",))
    for fid, (pr, ph) in prd_feats.items():
        if pr in ("must", "should") and (phase is None or ph == phase):
            if fid not in coverage:
                errors.append(f"{fid} ({pr}, {ph}) has no Coverage line")
    for fid, b in coverage.items():
        if fid not in prd_feats:
            errors.append(f"Coverage names {fid}, which the PRD does not define")
        refs = re.findall(r"\b(?:FLOW|SCREEN)-\d+\b", b)
        if not refs and "no screen:" not in b:
            errors.append(f"Coverage line for {fid} names no FLOW/SCREEN and gives no 'no screen:' reason")
        for r in refs:
            if r not in flows and r not in screens:
                errors.append(f"Coverage for {fid} names {r}, which does not exist")
    for i, b in blocks(text, ("OPEN-",)).items():
        for part in ("Blocks:", "Recommended:"):
            if part not in b:
                errors.append(f"{i} lacks {part}")
    ok = not errors
    result = {"ok": ok, "counts": {"IA": len(ia), "SCREEN": len(screens), "FLOW": len(flows),
              "covered": len(coverage)}, "errors": errors}
    if report:
        record = {"ok": ok, "date": datetime.date.today().isoformat(), "file": path, "prd": prd, "phase": phase,
                  "counts": result["counts"], "errors": errors}
        try:
            with open(report, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
                f.write("\n")
        except OSError as e:
            print(f"Error: cannot write the report: {e}", file=sys.stderr)
            return 2
    print(json.dumps(result, indent=2 if as_json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
