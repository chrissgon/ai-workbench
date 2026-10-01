#!/usr/bin/env python3
"""Lint a design brief written for an AI design tool.

Usage: python3 lint_brief.py --file <brief.md> --type <screen|mockup|logo|presentation|animation|image>
                             --values <inline|loaded> [--messaging <messaging.md>]
                             [--flows <flows.md> --screen SCREEN-n] [--report <lint.json>] [--json]

--report <path> also writes the result to that file, with the command's own arguments ("file", "type",
"values", "screen", "messaging") and the date, so a reviewer can check the lint ran and what it checked.

Checks:
  - required sections are present
  - self-contained: no repository path (`docs/…`, not a site URL `/docs/…`) outside the header, Sources and Attachments
  - Content holds the labels the type profile requires (references/<type>.md)
  - values mode: inline needs at least 6 hex colours, 6 pixel values and two typefaces "<Face> for text|code|…"
    in Visual language; loaded needs the header line "Values: loaded: <name>" and at least one hex value
    (the brand colour restated)
  - with --messaging: every SECTION-n headline of the messaging artifact appears verbatim (screen briefs
    that carry the page's copy)
  - with --flows and --screen: every region and state of the SCREEN is named in Content (lists split outside
    parentheses, on semicolons when the list has one, otherwise on commas)
  - Creative direction names at least one "Direction <X>" (three unless the header says one was chosen)
  - Evaluation criteria has at least 5 `- CRIT-n:` lines; Deliverables has at least one line
  - Prompt has exactly one fenced block of at most 150 lines, and a "Direction:" slot when there are several
  - no TBD, TODO, lorem or {template placeholder} remains
  - every OPEN has Blocks: and Recommended:

Prints JSON. Exit codes: 0 ok, 1 problems found, 2 usage error.
"""
import datetime
import json
import re
import sys

SECTIONS = ["Summary", "Sources", "Subject", "Audience and voice", "Creative direction", "Visual language",
            "Content", "Constraints", "Deliverables", "Evaluation criteria", "Attachments", "Prompt",
            "Open questions", "Readiness"]
PATH_EXEMPT = {"Sources", "Attachments"}
PROFILE = {
    "screen": ["Regions", "States", "Breakpoints", "Motion"],
    "mockup": ["Scene", "Placement", "Sizes"],
    "logo": ["Name", "Variants", "Minimum size", "Clear space"],
    "presentation": ["Format", "Slides"],
    "animation": ["Duration", "Timeline", "Final state", "Reduced motion", "Output"],
    "image": ["Size", "Format", "Text"],
}


def section(text, title):
    m = re.search(r"^## " + re.escape(title) + r"\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^## ", rest, re.M)
    return rest[: n.start()] if n else rest


def fenced(sec):
    return re.findall(r"```[^\n]*\n(.*?)```", sec, re.S)


def norm(s):
    return " ".join(s.split())


def split_list(s):
    """Split a Regions: or States: list outside parentheses: on semicolons when there is one (items may then
    hold commas), otherwise on commas, the separator the flows template writes."""
    outside = r"\s*(?![^()]*\))"
    sep = ";" if re.search(";" + outside, s) else ","
    return [it.strip() for it in re.split(sep + outside, s) if it.strip()]


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        print(__doc__)
        return 0 if argv else 2
    as_json = "--json" in argv
    args = {}
    for flag in ("--file", "--type", "--values", "--messaging", "--flows", "--screen", "--report"):
        if flag in argv:
            if argv.index(flag) + 1 >= len(argv):
                print(f"Error: {flag} needs a value.", file=sys.stderr)
                return 2
            args[flag] = argv[argv.index(flag) + 1]
    if "--file" not in args or args.get("--type") not in PROFILE or args.get("--values") not in ("inline", "loaded"):
        print("Error: --file, --type <" + "|".join(PROFILE) + "> and --values <inline|loaded> are required.",
              file=sys.stderr)
        return 2
    if ("--flows" in args) != ("--screen" in args):
        print("Error: --flows and --screen go together.", file=sys.stderr)
        return 2
    try:
        text = open(args["--file"], encoding="utf-8").read()
        msg = open(args["--messaging"], encoding="utf-8").read() if "--messaging" in args else None
        flows = open(args["--flows"], encoding="utf-8").read() if "--flows" in args else None
    except OSError as e:
        print(f"Error: cannot read input: {e}", file=sys.stderr)
        return 2
    errors = []
    for s in SECTIONS:
        if not re.search(r"^## " + re.escape(s) + r"\s*$", text, re.M):
            errors.append(f"missing section '## {s}'")
    for title in [s for s in SECTIONS if s not in PATH_EXEMPT]:
        for path in re.findall(r"(?<![/\w.-])docs/[\w./<>-]+", section(text, title)):
            errors.append(f"{title}: references a repository path ({path}); the tool cannot read it")
    content = section(text, "Content")
    for label in PROFILE[args["--type"]]:
        if not re.search(r"(\*\*|###\s*|^\s*-\s*)" + re.escape(label) + r"\b", content, re.M | re.I):
            errors.append(f"Content lacks the '{label}' part the {args['--type']} profile requires")
    visual = section(text, "Visual language")
    hexes = set(h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}\b", visual))
    if args["--values"] == "inline":
        pxs = re.findall(r"\b\d+(?:\.\d+)?\s?px\b", visual)
        if len(hexes) < 6:
            errors.append(f"Visual language names {len(hexes)} hex colours; inline mode needs at least 6")
        if len(pxs) < 6:
            errors.append(f"Visual language names {len(pxs)} pixel values; inline mode needs at least 6")
        faces = re.findall(r"\b([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)?) for (?:text|code|interface|headings|body)", visual)
        if len(set(faces)) < 2:
            errors.append("Visual language must name the typefaces as '<Face> for text' and '<Face> for code|headings'")
    else:
        if not re.search(r"^- Values:\s*loaded:\s*\S", text, re.M):
            errors.append("loaded mode needs the header line '- Values: loaded: <design system in the tool>'")
        if not hexes:
            errors.append("loaded mode still restates the brand colour as a hex value in Visual language")
    if msg is not None:
        brief_norm = norm(text)
        for sid, body in re.findall(r"^\s*-\s*(SECTION-\d+):(.*)$", msg, re.M):
            hm = re.search(r"Headline:\s*(.*?)\s*Body:", body)
            if hm and norm(hm.group(1)).rstrip(".") not in brief_norm:
                errors.append(f"{sid}: headline {hm.group(1)!r} is not in the brief verbatim")
    if flows is not None:
        sid = args["--screen"]
        m = re.search(r"^\s*-\s*" + re.escape(sid) + r":(.*?)(?=^\s*-\s*(?:SCREEN|FLOW)-\d+:|^## )", flows, re.M | re.S)
        if not m:
            errors.append(f"{sid} not found in the flows")
        else:
            body = norm(m.group(1))
            rm = re.search(r"Regions:\s*(.*?)\.\s*States:", body)
            sm = re.search(r"States:\s*(.*?)\.\s*Breakpoints:", body)
            regions = split_list(rm.group(1)) if rm else []
            states = split_list(sm.group(1)) if sm else []
            low = content.lower()
            for kind, items in (("region", regions), ("state", states)):
                for it in items:
                    key = " ".join(re.sub(r"\(.*?\)", "", it).split()[:2]).lower().strip(" .")
                    if key and key not in low:
                        errors.append(f"{kind} {it!r} of {sid} is not named in Content (looked for {key!r})")
    directions = re.findall(r"Direction [A-Z]\b", section(text, "Creative direction"))
    chosen = re.search(r"^- Direction:\s*chosen", text, re.M)
    if not directions:
        errors.append("Creative direction names no 'Direction <X>'")
    elif len(set(directions)) < 3 and not chosen:
        errors.append(f"Creative direction names {len(set(directions))} directions; three, unless '- Direction: chosen …' is in the header")
    crits = re.findall(r"^\s*-\s*CRIT-\d+:", section(text, "Evaluation criteria"), re.M)
    if len(crits) < 5:
        errors.append(f"Evaluation criteria has {len(crits)} CRIT lines; at least 5 expected")
    if not [ln for ln in section(text, "Deliverables").splitlines() if ln.strip().startswith("-")]:
        errors.append("Deliverables has no lines")
    prompts = fenced(section(text, "Prompt"))
    if len(prompts) != 1:
        errors.append(f"Prompt must have exactly one fenced block, found {len(prompts)}")
    else:
        n = len(prompts[0].strip().splitlines())
        if n > 150:
            errors.append(f"Prompt block has {n} lines; at most 150")
        if len(set(directions)) > 1 and "Direction:" not in prompts[0]:
            errors.append("Prompt has no 'Direction:' slot although the brief names several directions")
    body_wo_sources = re.sub(r"## Sources.*?(?=^## )", "", text, flags=re.S | re.M)
    body_wo_code = re.sub(r"```.*?```", "", body_wo_sources, flags=re.S)
    for marker in re.findall(r"\bTBD\b|\bTODO\b|\blorem\b|\{[^}\n]{1,80}\}", body_wo_code):
        if re.match(r"\{\s*[\w-]+\s*:", marker):
            continue
        errors.append(f"placeholder or marker left in the brief: {marker!r}")
    for oid, rest in re.findall(r"^\s*-\s*(OPEN-\d+)\s*(?:\([^)]*\))?:(.*)$", text, re.M):
        if "Blocks:" not in rest or "Recommended:" not in rest:
            errors.append(f"{oid} lacks Blocks: or Recommended:")
    ok = not errors
    result = {"ok": ok, "counts": {"hex_colours": len(hexes), "directions": len(set(directions)),
              "criteria": len(crits)}, "errors": errors}
    if "--report" in args:
        record = {"ok": ok, "date": datetime.date.today().isoformat(), "file": args["--file"],
                  "type": args["--type"], "values": args["--values"], "screen": args.get("--screen"),
                  "flows": args.get("--flows"), "messaging": args.get("--messaging"),
                  "counts": result["counts"], "errors": errors}
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
