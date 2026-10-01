#!/usr/bin/env python3
"""Lint a design handoff spec.

Usage: python3 lint_handoff.py --file <handoff.md> --flows <flows.md> --screen SCREEN-n
                               [--inventory <inventory.json> --library <stylesheet.css>]
                               [--report <handoff.lint.json>] [--json]

Checks:
  - required sections are present
  - every region of the SCREEN in the flows has a Components row (matched by its first two words)
    with a non-empty Content source
  - with --inventory and --library: every custom property the export defines or uses that the library
    stylesheet does not define, and every fixed colour, appears in the Tokens table (custom properties
    may be grouped with a wildcard such as `--ds-*-ink`)
  - every Tokens row has an Action
  - with --inventory: every true or false constant of the export's scripts (inventory `script_flags`, the
    candidates for preview-only switches) and every constant holding hard-coded data (`script_data`) is
    named somewhere in the spec
  - every Motion row has a Timing with a number in ms or s and a Reduced motion entry
  - every DEV-n has "Action:" with fix in code, back to design, or accepted
  - Acceptance names at least one width in px and a mode (light or dark)
  - no TBD or TODO; every OPEN has Blocks: and Recommended:

Prints JSON: ok, summary (the line the report quotes), counts, errors. --report also writes that result,
with the command's arguments and the date, to the given file, kept next to the spec as the evidence of the
last run. Exit codes: 0 ok, 1 problems found, 2 usage error.
"""
import datetime
import fnmatch
import json
import re
import sys

SECTIONS = ["Summary", "Sources", "Reference and shipping", "Tokens", "Components", "Layout", "Behaviour",
            "Motion", "Assets", "Deviations", "Acceptance", "Open questions", "Readiness"]


def section(text, title):
    m = re.search(r"^## " + re.escape(title) + r"\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^## ", rest, re.M)
    return rest[: n.start()] if n else rest


def rows(sec):
    out = []
    lines = [ln for ln in sec.splitlines() if ln.startswith("|") and not re.match(r"^\|\s*-", ln)]
    for ln in lines[1:]:
        out.append([c.strip() for c in ln.strip().strip("|").split("|")])
    return out


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        print(__doc__)
        return 0 if argv else 2
    as_json = "--json" in argv
    try:
        args = {f: argv[argv.index(f) + 1] for f in
                ("--file", "--flows", "--screen", "--inventory", "--library", "--report") if f in argv}
    except IndexError:
        print("Error: every option needs a value. See --help.", file=sys.stderr)
        return 2
    if not all(k in args for k in ("--file", "--flows", "--screen")) or (("--inventory" in args) != ("--library" in args)):
        print("Error: --file, --flows and --screen are required; --inventory and --library go together.", file=sys.stderr)
        return 2
    try:
        text = open(args["--file"], encoding="utf-8").read()
        flows = open(args["--flows"], encoding="utf-8").read()
        inv = json.load(open(args["--inventory"])) if "--inventory" in args else None
        lib = open(args["--library"], encoding="utf-8").read() if "--library" in args else ""
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error: cannot read input: {e}", file=sys.stderr)
        return 2
    errors = []
    for s in SECTIONS:
        if not re.search(r"^## " + re.escape(s) + r"\s*$", text, re.M):
            errors.append(f"missing section '## {s}'")
    sid = args["--screen"]
    m = re.search(r"^\s*-\s*" + re.escape(sid) + r":(.*?)(?=^\s*-\s*(?:SCREEN|FLOW)-\d+:|^## )", flows, re.M | re.S)
    comps = rows(section(text, "Components"))
    names = " ".join(r[0].lower() for r in comps if r)
    if not m:
        errors.append(f"{sid} not found in the flows")
    else:
        body = " ".join(m.group(1).split())
        rm = re.search(r"Regions:\s*(.*?)\.\s*States:", body)
        for reg in ([r.strip() for r in re.split(r",\s*(?![^()]*\))", rm.group(1))] if rm else []):
            key = " ".join(re.sub(r"\(.*?\)", "", reg).split()[:2]).lower()
            if key and key not in names:
                errors.append(f"region {reg!r} of {sid} has no Components row (looked for {key!r})")
    for r in comps:
        if len(r) < 5 or not r[3] or r[3] in ("-", "—"):
            errors.append(f"Components row {r[0] if r else '?'} has no content source")
    toks = rows(section(text, "Tokens"))
    tok_text = " ".join(r[0] for r in toks if r).lower()
    tok_patterns = re.findall(r"--[a-z0-9*-]+", tok_text)
    for r in toks:
        if len(r) < 4 or not r[3]:
            errors.append(f"Tokens row {r[0] if r else '?'} has no Action")
    if inv is not None:
        libvars = set(re.findall(r"(--[a-z0-9-]+)\s*:", lib))
        invented = sorted(set(inv.get("custom_properties_defined", []) + inv.get("custom_properties_used", [])) - libvars)
        for v in invented:
            if not any(fnmatch.fnmatch(v, p) for p in tok_patterns):
                errors.append(f"custom property {v} is not in the library and has no Tokens row")
        for c in inv.get("fixed_colours", []):
            libcol = c.lower() in lib.lower()
            if not libcol and c.lower() not in tok_text:
                errors.append(f"fixed colour {c} is not in the library and has no Tokens row")
        for f in inv.get("script_flags", []) + inv.get("script_data", []):
            if f.get("name") and f["name"] not in text:
                errors.append(f"script constant {f['name']} ({f.get('script')}, line {f.get('line')}) is not named in "
                              "the spec: say under 'Reference and shipping' whether it is a preview-only switch or "
                              "placeholder data, or under Behaviour or Components what it is in the product")
    motion = rows(section(text, "Motion"))
    for r in motion:
        if len(r) < 5 or not r[4] or r[4] in ("-", "—"):
            errors.append(f"Motion row {r[0] if r else '?'} has no reduced-motion entry")
        if len(r) >= 3 and not re.search(r"\d\s?(ms|s)\b", r[2]):
            errors.append(f"Motion row {r[0]} has no timing in ms or s (read it from the export's scripts and styles)")
    devs = re.findall(r"^\s*-\s*(DEV-\d+):(.*)$", section(text, "Deviations"), re.M)
    for did, rest in devs:
        if not re.search(r"Action:\s*(fix in code|back to design|accepted)", rest):
            errors.append(f"{did} has no Action: fix in code | back to design | accepted")
    acc = section(text, "Acceptance")
    if not re.search(r"\b\d{3,4}\s?px\b|\b\d{3,4}\b", acc) or not re.search(r"\b(light|dark)\b", acc):
        errors.append("Acceptance must name at least one width and a mode")
    if re.search(r"\bTBD\b|\bTODO\b", text):
        errors.append("TBD or TODO left in the spec")
    for oid, rest in re.findall(r"^\s*-\s*(OPEN-\d+)\s*:(.*)$", text, re.M):
        if "Blocks:" not in rest or "Recommended:" not in rest:
            errors.append(f"{oid} lacks Blocks: or Recommended:")
    ok = not errors
    counts = {"components": len(comps), "tokens": len(toks), "motion": len(motion), "deviations": len(devs)}
    checked = "with inventory and library" if inv is not None else "without inventory (tokens not checked)"
    summary = (f"lint_handoff {'ok' if ok else 'FAILED'}: {len(errors)} errors; {counts['components']} components, "
               f"{counts['tokens']} tokens, {counts['motion']} motion rows, {counts['deviations']} deviations; {checked}")
    result = {"ok": ok, "summary": summary, "counts": counts, "errors": errors}
    if "--report" in args:
        record = {"date": datetime.date.today().isoformat(),
                  "arguments": {k: v for k, v in args.items() if k != "--report"}, **result}
        try:
            with open(args["--report"], "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
                f.write("\n")
        except OSError as e:
            print(f"Error: cannot write the report: {e}", file=sys.stderr)
            return 2
    print(json.dumps(result, indent=2 if as_json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
