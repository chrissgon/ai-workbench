#!/usr/bin/env python3
"""Lint a design brief written for an external design tool.

Usage: python3 lint_brief.py --file <brief.md> --messaging <messaging.md> [--json]

Checks:
  - required sections are present
  - the brief is self-contained: no `docs/` path is referenced outside the header, Sources and How to run
    (the external tool cannot follow a repository path)
  - Visual language carries values: at least 6 distinct hex colours and 6 pixel values, and names two typefaces
  - every SECTION-n of the messaging artifact appears in Page structure, and every headline of the messaging
    artifact appears verbatim in the brief
  - Components has at least one fenced code block
  - Evaluation criteria has at least 5 `- CRIT-n:` lines; Deliverables has at least one line
  - Prompt has one fenced block of at most 25 lines
  - no TBD, TODO, lorem or placeholder marker remains
  - every OPEN has Blocks: and Recommended:

Prints JSON. Exit codes: 0 ok, 1 problems found, 2 usage error.
"""
import json
import re
import sys

SECTIONS = ["## Summary", "## Sources", "## Product", "## Audience and voice", "## Creative direction",
            "## Visual language", "## Components", "## Page structure", "## Constraints", "## Deliverables",
            "## Evaluation criteria", "## How to run", "## Prompt", "## Open questions", "## Readiness"]
PATH_EXEMPT = {"Sources", "How to run"}


def section(text, title):
    m = re.search(r"^## " + re.escape(title) + r"\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^## ", rest, re.M)
    return rest[: n.start()] if n else rest


def fenced(sec):
    return re.findall(r"```[^\n]*\n(.*?)```", sec, re.S)


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        print(__doc__)
        return 0 if argv else 2
    as_json = "--json" in argv
    args = {}
    for flag in ("--file", "--messaging"):
        if flag in argv:
            args[flag] = argv[argv.index(flag) + 1]
    if len(args) < 2:
        print("Error: --file and --messaging are required. See --help.", file=sys.stderr)
        return 2
    try:
        text = open(args["--file"], encoding="utf-8").read()
        msg = open(args["--messaging"], encoding="utf-8").read()
    except OSError as e:
        print(f"Error: cannot read input: {e}", file=sys.stderr)
        return 2
    errors = []
    for s in SECTIONS:
        if s not in text:
            errors.append(f"missing section {s!r}")
    for title in [s[3:] for s in SECTIONS if s[3:] not in PATH_EXEMPT]:
        for path in re.findall(r"\bdocs/[\w./<>-]+", section(text, title)):
            errors.append(f"{title}: references a repository path ({path}); the tool cannot read it")
    visual = section(text, "Visual language")
    hexes = set(h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}\b", visual))
    pxs = re.findall(r"\b\d+(?:\.\d+)?\s?px\b", visual)
    if len(hexes) < 6:
        errors.append(f"Visual language names {len(hexes)} hex colours; at least 6 expected (write the values out)")
    if len(pxs) < 6:
        errors.append(f"Visual language names {len(pxs)} pixel values; at least 6 expected (write the values out)")
    faces = re.findall(r"\b([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)?) for (?:text|code|interface|headings)", visual)
    if len(set(faces)) < 2:
        errors.append("Visual language must name the typefaces in the form '<Face> for text' and '<Face> for code'")
    structure = section(text, "Page structure")
    msg_sections = re.findall(r"^\s*-\s*(SECTION-\d+):(.*)$", msg, re.M)
    if not msg_sections:
        errors.append("the messaging artifact has no SECTION-n lines")
    norm = lambda s: " ".join(s.split())
    brief_norm = norm(text)
    for sid, body in msg_sections:
        if sid not in structure:
            errors.append(f"{sid} of the messaging artifact is missing from Page structure")
        hm = re.search(r"Headline:\s*(.*?)\s*Body:", body)
        if hm and norm(hm.group(1)) not in brief_norm:
            errors.append(f"{sid}: headline {hm.group(1)!r} is not in the brief verbatim")
    if not fenced(section(text, "Components")):
        errors.append("Components has no fenced code block with real markup")
    crits = re.findall(r"^\s*-\s*CRIT-\d+:", section(text, "Evaluation criteria"), re.M)
    if len(crits) < 5:
        errors.append(f"Evaluation criteria has {len(crits)} CRIT lines; at least 5 expected")
    if not [ln for ln in section(text, "Deliverables").splitlines() if ln.strip().startswith("-")]:
        errors.append("Deliverables has no lines")
    prompts = fenced(section(text, "Prompt"))
    if len(prompts) != 1:
        errors.append(f"Prompt must have exactly one fenced block, found {len(prompts)}")
    elif len(prompts[0].strip().splitlines()) > 25:
        errors.append(f"Prompt block has {len(prompts[0].strip().splitlines())} lines; at most 25")
    body_wo_sources = re.sub(r"## Sources.*?(?=^## )", "", text, flags=re.S | re.M)
    for marker in re.findall(r"\bTBD\b|\bTODO\b|\blorem\b|\{[^}]{1,80}\}", body_wo_sources):
        if not re.match(r"\{\s*[\w-]+\s*:", marker):
            errors.append(f"placeholder or marker left in the brief: {marker!r}")
    for oid, rest in re.findall(r"^\s*-\s*(OPEN-\d+)\s*(?:\([^)]*\))?:(.*)$", text, re.M):
        if "Blocks:" not in rest or "Recommended:" not in rest:
            errors.append(f"{oid} lacks Blocks: or Recommended:")
    ok = not errors
    print(json.dumps({"ok": ok, "counts": {"sections_in_messaging": len(msg_sections), "hex_colours": len(hexes),
                      "criteria": len(crits)}, "errors": errors}, indent=2 if as_json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
