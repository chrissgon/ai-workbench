#!/usr/bin/env python3
"""Lint a design-system document written from assets/design-system-template.md.

Usage: python3 lint_design_system.py --file <design-system.md> [--library <token file> [--prefix <p>]]
                                     [--flows <flows.md>] [--report <design-system.lint.json>] [--json]

Checks:
  - required sections are present
  - every row of the Colour table has a light value, a dark value (or "same") and a source
  - every row of the Contrast table has two ratios and an AA result, and each ratio is the one the Colour
    table's values give: the text and the background of a row are found by the token names of the Colour
    table (a backticked property, the name in parentheses after it, or a name such as theme/ink) or by hex
    values written in the cell, and a stated ratio more than 0.05 away from the computed one is an error. A
    row whose colours cannot be found, or whose values are not hex, is not recomputed: it is a warning
  - the Type section states a typeface and a reading width, and every type role row has size, line height and weight
  - every row of the Components table has owner, variants, states, screens and source
  - no TBD / TODO / ??? anywhere
  - with --library: every custom property of the library's prefix (--<prefix>-*) in the library file appears
    in the document. The prefix is --prefix, or, without it, the prefix most custom properties defined in the
    library file share (`ui` when most are `--ui-*`; in a document that lists tokens without defining them,
    the prefix most of the listed properties share); the output names the prefix it used. When the library
    file lists a property in a table row with its values (`| --ui-bg | #FFFFFF | #000000 | ... |`), the row of
    the document that names the property must carry the same values
  - with --flows: every row of the Components table cites at least one SCREEN-n, and every SCREEN-n the
    document cites exists in the flows file

Prints JSON on stdout: ok, summary (the line a reply quotes), counts, errors, warnings, and library_prefix
with --library. --report <path> also writes the record of the evidence convention to that file (script,
date, arguments, ok, summary, errors, warnings, counts), kept next to the document as the evidence of the
last run. Usage errors, an unknown flag among them, go to stderr and write no report.
Exit codes: 0 ok, 1 problems found, 2 usage error.
"""
import datetime
import json
import re
import sys

SECTIONS = ["## Summary", "## Sources", "## Ownership", "## Colour", "## Contrast", "## Type", "## Space, radii, borders, elevation",
            "## Layout", "## Components", "## Design tool", "## Assumptions", "## Open questions", "## Readiness"]
COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}\b|rgba?\(|oklch\(|light-dark\(|\bsame\b|\bnone\b|\btransparent\b|\d+%")
HEX_RE = re.compile(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b")
RATIO_RE = re.compile(r"(\d+(?:\.\d+)?):1")
TOLERANCE = 0.05
VALUE_FLAGS = ("--file", "--library", "--prefix", "--flows", "--report")
SWITCHES = ("--json",)


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
        if ln.startswith("|") and not re.match(r"^\|\s*-", ln) and not re.match(r"^\|\s*(Token|Text token|Role|Component)\s*\|", ln):
            out.append([c.strip() for c in ln.strip().strip("|").split("|")])
    return out


def luminance(hex_colour):
    h = hex_colour[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    channels = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(fg, bg):
    a, b = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def token_names(cell):
    """The names a Colour row is known by: each backticked part, each name in parentheses, the bare cell."""
    names = set(re.findall(r"`([^`]+)`", cell)) | set(re.findall(r"\(([^()]+)\)", cell))
    bare = re.sub(r"\([^()]*\)", "", cell).replace("`", "").strip()
    if bare:
        names.add(bare)
    return {n.strip() for n in names if n.strip()}


def colour_values(colour_rows):
    """{name: (light hex or None, dark hex or None)} from the Colour table."""
    values = {}
    for r in colour_rows:
        if len(r) < 3:
            continue
        light = HEX_RE.search(r[1])
        dark = light if re.search(r"\bsame\b", r[2]) else HEX_RE.search(r[2])
        pair = (light.group(0) if light else None, dark.group(0) if dark else None)
        for name in token_names(r[0]):
            values[name] = pair
    return values


def resolve(cell, values):
    """The (light, dark) colours a Contrast cell names, or None: hex values written in the cell win, else the
    longest Colour-table name found in it as a whole word."""
    hexes = HEX_RE.findall(cell)
    if hexes:
        return (hexes[0], hexes[1] if len(hexes) > 1 else hexes[0])
    plain = cell.replace("`", "")
    for name in sorted(values, key=len, reverse=True):
        if re.search(r"(?<![\w/-])" + re.escape(name) + r"(?![\w/-])", plain):
            return values[name]
    return None


def check_contrast(contrast_rows, values):
    """(errors, warnings, recomputed) for the Contrast table against the Colour table's values."""
    errors, warnings, recomputed = [], [], 0
    for r in contrast_rows:
        name = r[0] if r else "?"
        if len(r) < 5 or not RATIO_RE.search(r[2]) or not RATIO_RE.search(r[3]) or not re.search(r"\b(pass|fail)\b", r[4], re.I):
            errors.append(f"contrast row {name} needs two ratios and pass/fail")
            continue
        fg, bg = resolve(r[0], values), resolve(r[1], values)
        if fg is None or bg is None:
            warnings.append(f"contrast row {name}: not recomputed, its colours are not in the Colour table")
            continue
        checked = False
        for mode, i, cell in (("light", 0, r[2]), ("dark", 1, r[3])):
            if not fg[i] or not bg[i]:
                warnings.append(f"contrast row {name}: {mode} ratio not recomputed, a value is not hex")
                continue
            stated = float(RATIO_RE.search(cell).group(1))
            computed = ratio(fg[i], bg[i])
            checked = True
            if abs(stated - computed) > TOLERANCE:
                errors.append(f"contrast row {name}: {mode} ratio is {stated:.2f}:1 in the document; "
                              f"{fg[i]} on {bg[i]} gives {computed:.2f}:1")
        recomputed += checked
    return errors, warnings, recomputed


def parse(argv):
    """The flags given, as {flag: value or True}, and None; or None and the message of a usage error."""
    args, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a in VALUE_FLAGS:
            if i + 1 >= len(argv):
                return None, f"{a} needs a value"
            args[a] = argv[i + 1]
            i += 2
        elif a in SWITCHES:
            args[a] = True
            i += 1
        else:
            return None, f"unknown argument {a!r}"
    if "--file" not in args:
        return None, "--file <design-system.md> is required"
    if "--prefix" in args and not re.fullmatch(r"[a-z][a-z0-9]*", args["--prefix"].strip("-")):
        return None, "--prefix must be lowercase letters and digits, e.g. ui"
    return args, None


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    args, problem = parse(argv)
    if problem:
        print(f"Error: {problem}. See --help.", file=sys.stderr)
        return 2
    lib, flows = args.get("--library"), args.get("--flows")
    prefix = args.get("--prefix", "").strip("-")
    try:
        text = open(args["--file"], encoding="utf-8").read()
        lib_text = open(lib, encoding="utf-8").read() if lib else ""
        flows_text = open(flows, encoding="utf-8").read() if flows else ""
    except OSError as e:
        print(f"Error: cannot read input: {e}", file=sys.stderr)
        return 2
    errors = []
    for s in SECTIONS:
        if s not in text:
            errors.append(f"missing section {s!r}")
    if re.search(r"\b(TBD|TODO)\b|\?\?\?", text):
        errors.append("contains TBD/TODO/???")
    colour = rows(section(text, "Colour"))
    for r in colour:
        if len(r) < 5:
            errors.append(f"colour row {r[0] if r else '?'} has fewer than 5 cells"); continue
        if not COLOR_RE.search(r[1]) or not COLOR_RE.search(r[2]):
            errors.append(f"colour row {r[0]} lacks a light or dark value")
        if not r[4]:
            errors.append(f"colour row {r[0]} has no source")
    contrast = rows(section(text, "Contrast"))
    contrast_errors, warnings, recomputed = check_contrast(contrast, colour_values(colour))
    errors += contrast_errors
    typ = section(text, "Type")
    if not re.search(r"Typeface:\s*\S", typ):
        errors.append("Type section has no 'Typeface:' line")
    if not re.search(r"Reading width:\s*\S", typ):
        errors.append("Type section has no 'Reading width:' line")
    for r in rows(typ):
        if len(r) < 5 or not re.search(r"\d", r[1]) or not re.search(r"\d|\b(normal|auto)\b", r[2]) or not r[3]:
            errors.append(f"type role row {r[0] if r else '?'} needs size, line height and weight")
    comps = rows(section(text, "Components"))
    for r in comps:
        if len(r) < 6 or any(not c for c in r[:6]):
            errors.append(f"component row {r[0] if r else '?'} needs owner, variants, states, screens and source")
    missing = []
    if lib_text:
        if not prefix:
            defined = (re.findall(r"--([a-z][a-z0-9]*)-[a-z0-9-]+\s*:", lib_text)  # a stylesheet
                       or re.findall(r"(?<![\w-])--([a-z][a-z0-9]*)-[a-z0-9-]+", lib_text))  # a token document
            prefix = max(sorted(set(defined)), key=defined.count) if defined else ""
        props = sorted(set(re.findall(rf"--{prefix}-[a-z][a-z0-9-]*", lib_text))) if prefix else []
        if not props:
            errors.append("--library: no prefixed custom properties found in the library file; pass --prefix")
        missing = [p for p in props if p not in text]
        if missing:
            errors.append(f"library custom properties absent from the document: {missing}")
        # Values: a library table row "| `--p-name` | v1 | v2 | ..." must be mirrored verbatim.
        value_re = re.compile(r"#[0-9A-Fa-f]{3,8}\b|\b\d+(?:\.\d+)?(?:px|rem|em|%)")
        doc_lines = text.splitlines()
        for ln in lib_text.splitlines():
            cells = [c.strip() for c in ln.strip().strip("|").split("|")] if ln.lstrip().startswith("|") else []
            m = re.fullmatch(rf"`?(--{prefix}-[a-z][a-z0-9-]*)`?", cells[0]) if prefix and len(cells) > 1 else None
            if not m or m.group(1) in missing:
                continue
            want = []
            for c in cells[1:3]:  # the light and dark cells, or the single value cell
                v = value_re.fullmatch(c)
                if not v:
                    break
                want.append(c.lower())
            if not want:
                continue
            tok = m.group(1)
            named = [dl.lower() for dl in doc_lines if re.search(re.escape(tok) + r"(?![a-z0-9-])", dl)]
            if not any(all(w in dl for w in want) for dl in named):
                errors.append(f"library value changed or absent: no line naming {tok} carries {' and '.join(cells[1:1 + len(want)])}")
    if flows:
        known = set(re.findall(r"\bSCREEN-\d+\b", flows_text))
        if not known:
            errors.append("--flows: the flows file names no SCREEN-n")
        for r in comps:
            if len(r) >= 5 and not re.search(r"\bSCREEN-\d+\b", r[4]):
                errors.append(f"component row {r[0]} cites no SCREEN-n in its Screens cell")
        unknown = sorted(set(re.findall(r"\bSCREEN-\d+\b", text)) - known)
        if known and unknown:
            errors.append(f"screens cited that the flows file does not have: {unknown}")
    if not comps:
        errors.append("Components table has no rows")
    ok = not errors
    counts = {"colour": len(colour), "contrast": len(contrast), "contrast_recomputed": recomputed,
              "components": len(comps)}
    summary = (f"lint_design_system {'ok' if ok else 'FAILED'}: {len(errors)} errors, {len(warnings)} warnings; "
               f"{counts['colour']} colour rows, {counts['contrast']} contrast rows ({recomputed} recomputed), "
               f"{counts['components']} components"
               + (f"; library prefix --{prefix}-" if lib_text else "; no library")
               + ("; flows checked" if flows else "; flows not checked"))
    if "--report" in args:
        record = {"script": "lint_design_system.py", "date": datetime.date.today().isoformat(),
                  "arguments": {k: v for k, v in args.items() if k != "--report"},
                  "ok": ok, "summary": summary, "errors": errors, "warnings": warnings, "counts": counts}
        try:
            with open(args["--report"], "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
                f.write("\n")
        except OSError as e:
            print(f"Error: cannot write the report: {e}", file=sys.stderr)
            return 2
    result = {"ok": ok, "summary": summary, **({"library_prefix": prefix} if lib_text else {}), "counts": counts,
              "errors": errors, "warnings": warnings}
    print(json.dumps(result, indent=2 if args.get("--json") else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
