#!/usr/bin/env python3
"""Lint a screen document against the flows and the design system.

Usage: python3 lint_screen.py --file <screen.md> --flows <flows.md> --design-system <design-system.md> --screen SCREEN-n [--json]

Checks:
  - required sections are present
  - every region listed in the SCREEN's "Regions:" in the flows has a row in the Layout table (matched by the
    first words of the region name, case-insensitive)
  - every state listed in the SCREEN's "States:" has a line under States
  - every text style named in the Layout table (text/… or site/…) exists in the design system's Type table
  - every token named in the Tokens and Spacing columns (word/word form) exists in the design system
  - no raw hex colour (#RRGGBB) or pixel value (NNpx) appears outside the Sources section
  - the Copy section has at least one line and every line without a messaging source is a [copy: …] placeholder
  - every OPEN has Blocks: and Recommended:

Prints JSON. Exit codes: 0 ok, 1 problems found, 2 usage error.
"""
import json
import re
import sys

SECTIONS = ["## Summary", "## Sources", "## Variants", "## Layout", "## Copy", "## States", "## Accessibility",
            "## Design tool", "## Findings for design-system", "## Open questions", "## Readiness"]


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
        if ln.startswith("|") and not re.match(r"^\|\s*-", ln) and not re.match(r"^\|\s*Region\s*\|", ln):
            out.append([c.strip() for c in ln.strip().strip("|").split("|")])
    return out


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        print(__doc__)
        return 0 if argv else 2
    as_json = "--json" in argv
    args = {}
    for flag in ("--file", "--flows", "--design-system", "--screen"):
        if flag in argv:
            args[flag] = argv[argv.index(flag) + 1]
    if len(args) < 4:
        print("Error: --file, --flows, --design-system and --screen are required. See --help.", file=sys.stderr)
        return 2
    try:
        text = open(args["--file"], encoding="utf-8").read()
        flows = open(args["--flows"], encoding="utf-8").read()
        ds = open(args["--design-system"], encoding="utf-8").read()
    except OSError as e:
        print(f"Error: cannot read input: {e}", file=sys.stderr)
        return 2
    errors = []
    for s in SECTIONS:
        if s not in text:
            errors.append(f"missing section {s!r}")
    sid = args["--screen"]
    m = re.search(r"^\s*-\s*" + re.escape(sid) + r":(.*?)(?=^\s*-\s*SCREEN-\d+:|^## )", flows, re.M | re.S)
    if not m:
        errors.append(f"{sid} not found in the flows")
        regions, states = [], []
    else:
        body = " ".join(m.group(1).split())
        rm = re.search(r"Regions:\s*(.*?)\.\s*States:", body)
        sm = re.search(r"States:\s*(.*?)\.\s*Breakpoints:", body)
        regions = [r.strip() for r in re.split(r",\s*(?![^()]*\))", rm.group(1))] if rm else []
        states = [s.strip() for s in re.split(r";\s*", sm.group(1))] if sm else []
    layout = rows(section(text, "Layout"))
    layout_names = " ".join(r[0].lower() for r in layout if r)
    for reg in regions:
        key = " ".join(re.sub(r"\(.*?\)", "", reg).split()[:2]).lower()
        if key and key not in layout_names:
            errors.append(f"region {reg!r} of {sid} has no Layout row (looked for {key!r})")
    states_sec = section(text, "States").lower()
    for st in states:
        key = " ".join(re.sub(r"\(.*?\)", "", st).split()[:2]).lower()
        if key and key not in states_sec:
            errors.append(f"state {st!r} of {sid} has no States line (looked for {key!r})")
    ds_type = section(ds, "Type")
    ds_styles = set(re.findall(r"\b(?:text|site)/[a-z0-9-]+", ds_type))
    ds_tokens = set(re.findall(r"\b(?:page|theme|success|error|warn|muted|surface|inverse|space|radius|border|layout|breakpoint|target|focus)/[a-z0-9-]+", ds))
    for r in layout:
        if len(r) < 7:
            errors.append(f"layout row {r[0] if r else '?'} has fewer than 7 cells"); continue
        for st in re.findall(r"\b(?:text|site)/[a-z0-9-]+", r[4]):
            if st not in ds_styles:
                errors.append(f"layout row {r[0]}: text style {st} is not in the design system")
        for tok in re.findall(r"\b(?:page|theme|success|error|warn|muted|surface|inverse|space|radius|border|layout|breakpoint|target|focus)/[a-z0-9-]+", r[5] + " " + r[6] + " " + r[1] + " " + r[2]):
            if tok not in ds_tokens:
                errors.append(f"layout row {r[0]}: token {tok} is not in the design system")
    body_wo_sources = re.sub(r"## Sources.*?(?=^## )", "", text, flags=re.S | re.M)
    raw = re.findall(r"#[0-9A-Fa-f]{6}\b|\b\d+\s?px\b", body_wo_sources)
    if raw:
        errors.append(f"raw values outside Sources: {sorted(set(raw))[:8]}")
    copy_lines = [ln for ln in section(text, "Copy").splitlines() if ln.strip().startswith("-")]
    if not copy_lines:
        errors.append("Copy section has no lines")
    for ln in copy_lines:
        if "[copy:" not in ln and "messaging" not in ln.lower() and "flows" not in ln.lower() and "spec" not in ln.lower():
            errors.append(f"copy line without a placeholder or a source: {ln.strip()[:80]}")
    for oid in re.findall(r"^\s*-\s*(OPEN-\d+)\s*:(.*)$", text, re.M):
        if "Blocks:" not in oid[1] or "Recommended:" not in oid[1]:
            errors.append(f"{oid[0]} lacks Blocks: or Recommended:")
    ok = not errors
    print(json.dumps({"ok": ok, "counts": {"regions_in_flows": len(regions), "layout_rows": len(layout), "states_in_flows": len(states)},
                      "errors": errors}, indent=2 if as_json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
