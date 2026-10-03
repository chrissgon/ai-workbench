#!/usr/bin/env python3
"""Lint a feature specification written from assets/spec-template.md.

Usage: python3 lint_spec.py --file <spec.md> [--report <path>] [--heading "<English heading>=<heading in the spec>"]... [--json]

--report <path> writes the record of the run to <path>: one JSON object with script, date, arguments, ok,
  summary, errors, warnings and counts, on every run that reaches the check, never on a usage error.
--heading maps one of the template's section headings to the heading a spec written in another language
  uses, without "## " (for example --heading "Functional requirements=Requisitos funcionais"); repeat it per
  heading. The field labels (Source:, Covers:, Given, When, Then, Blocks:, Recommended:) stay as the template
  writes them.

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

Prints JSON on stdout: ok, summary (the line to quote in the reply), counts, errors, warnings and next (what to
do now); a usage error goes to stderr.
Exit codes: 0 ok, 1 problems found, 2 usage error (a flag without its value, an unknown flag or heading, a file
that cannot be read or written).
"""
import datetime
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


def parse_args(argv):
    """(values, None), or (None, a usage error). values maps a value flag to its value, --heading to the list of
    its values and a switch to True: the shape of the record's `arguments`."""
    values, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a in ("--file", "--report", "--heading"):
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                return None, f"Error: {a} needs a value. See --help."
            if a == "--heading":
                values.setdefault(a, []).append(argv[i + 1])
            else:
                values[a] = argv[i + 1]
            i += 2
        elif a == "--json":
            values[a] = True
            i += 1
        else:
            return None, f"Error: unknown option {a!r}. See --help."
    return values, None


def translate(text, headings):
    """The text with each translated `## ` heading written as the template's English one."""
    for pair in headings:
        english, _, translated = pair.partition("=")
        text = re.sub(r"^## " + re.escape(translated.strip()) + r"[ \t]*$", "## " + english.strip(), text, flags=re.M)
    return text


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
    path, as_json = values.get("--file"), "--json" in values
    if not path:
        print("Error: --file <spec.md> is required. See --help.", file=sys.stderr)
        return 2
    headings = values.get("--heading", [])
    known = [s[3:] for s in SECTIONS]
    bad = [h for h in headings if h.partition("=")[0].strip() not in known or not h.partition("=")[2].strip()]
    if bad:
        print(f"Error: --heading {bad[0]!r} is not '<English heading>=<translated heading>' with one of: "
              + ", ".join(known) + ". See --help.", file=sys.stderr)
        return 2
    try:
        text = translate(open(path, encoding="utf-8").read(), headings)
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
    summary = (f"lint_spec.py --file {path}: ok: {'true' if ok else 'false'}, {len(errors)} errors, {len(warnings)} warnings ("
               + ", ".join(f"{v} {k}" for k, v in counts.items()) + ")")
    if errors or warnings:
        nxt = ("Not done. 1) If you have not edited the file yet, copy every error and warning above into your reply first. "
               "2) Fix each one from a source, or move the item to an OPEN with Blocks: and Recommended:. Never invent a number or a source. "
               "3) Run this command again.")
    else:
        nxt = ("Lint passed. Quote the command and this `summary` line in the reply's `- Check:` line, then go to the next "
               "step.")
    result = {"ok": ok, "summary": summary, "counts": counts, "errors": errors, "warnings": warnings, "next": nxt}
    print(json.dumps(result, indent=2 if as_json else None))
    if "--report" in values:
        record = {"script": "lint_spec.py", "date": datetime.date.today().isoformat(),
                  "arguments": {k: v for k, v in values.items() if k != "--report"}, "ok": ok, "summary": summary,
                  "errors": errors, "warnings": warnings, "counts": counts}
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
