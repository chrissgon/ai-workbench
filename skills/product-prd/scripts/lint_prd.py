#!/usr/bin/env python3
"""Lint a product requirements document written from assets/prd-template.md.

Usage: python3 lint_prd.py --file <prd.md> [--table] [--report <path>] [--json] [--source <file>]...

  --table           print a findings table (finding, how to fix it) and a last line, the summary, instead of JSON
  --report <path>   write the record of the run to <path>: one JSON object with script, date, arguments, ok,
                    summary, errors, warnings and counts, on every run that reaches the check, never on a usage error
  --json            indent the JSON
  --source <file>   a source file for the number check, repeatable; added to the files the PRD itself names

Checks:
  - required sections are present
  - ids (U, F, M, R, P, ASSUMPTION, OPEN) are unique
  - every U and F has a Source: line; every F has Priority: (must|should|later) and Phase:
  - every M has a number, a Baseline:, a Measured by: and a Source:
  - every P lists at least one F id and has an Exit: line; every must/should F appears in a P
  - every R has Trigger:, Impact: and Mitigation:
  - every OPEN has Blocks: and Recommended:
  - id lines are written "- F-1: ..." (a digit id and a colon); Users, Features and Release phases have at least one id,
    Success metrics has an M id or names the OPEN that holds the target
  - every number in a metric's Target: or Baseline:, and every date in a metric or a phase, appears in a source file
    (the file on the "- Brief:" line, the paths listed under "## Sources", docs/workbench/state.md, each --source)
    or in a "- User answer ..." line under "## Sources"; skipped with a warning when no source file can be read
  - a Source: that says only "brief" or "user" on a U, F or M (warning)
  - an "Instructions found in external content" heading inside the PRD (warning: it belongs in the reply)
  - vague words on F/M lines without a number on the same line (warning)
  - dates (YYYY-MM-DD, or a month name with a year) on P/M lines without a Source: on the same block (warning)
  - TBD / TODO / ??? inside id blocks
  - REQ-/NFR-/AC- definitions or Given/When/Then, which belong to feature specs (error); citing a spec's ids as a source is fine

Prints JSON on stdout: ok, summary (the line to quote in the reply, also the last line of --table), counts,
errors, warnings, how_to_fix (one entry per error, same order), sources_read. A usage error goes to stderr.
Exit codes: 0 ok, 1 problems found, 2 usage error (a flag without its value, an unknown flag, a file that
cannot be read or written).
"""
import datetime
import json
import os
import re
import sys

SECTIONS = ["## Summary", "## Problem and goal", "## Users", "## Scope", "## Sources", "## Features", "## Success metrics",
            "## Constraints", "## Dependencies and risks", "## Release phases", "## Assumptions", "## Open questions", "## Readiness"]
VAGUE = ("fast", "quick", "responsive", "easy", "simple", "intuitive", "user-friendly", "scalable", "robust", "reliable", "secure",
         "seamless", "modern", "clean", "performant", "efficient", "engaging", "delightful")
ID_RE = re.compile(r"^\s*-\s*((?:U|F|M|R|P|ASSUMPTION|OPEN)-\d+)\s*:", re.M)
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b")

LOOSE_ID_RE = re.compile(r"^\s*[-*]\s*\W*((?:U|F|M|R|P|ASSUMPTION|OPEN)-\w+)")
ANY_ID = r"\b(?:U|F|M|R|P|REQ|NFR|EDGE|AC|ASSUMPTION|OPEN|ADR)-\d+\b"
ISO_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
PATH_RE = re.compile(r"[\w./-]+\.(?:md|txt|json|ya?ml|csv)\b")
VAGUE_SOURCES = {"brief", "the brief", "user", "the user", "research", "prd", "state", "decision", "decisions"}

OPEN_INSTEAD = ("Do not pick another number or date. Delete it from the line (delete the whole M line when its target goes), add "
                "'- OPEN-n: <the question>. Blocks: <the metric, feature or phase>. Recommended: <value with unit, and why>' under "
                "'## Open questions', and for a metric write '- No metric yet for <goal>: the target is OPEN-n.' under "
                "'## Success metrics'. Only when the user stated the value in this conversation: keep it and add "
                "'- User answer <date>: \"<their words>\"' under '## Sources'.")


def how_to_fix(error):
    """The fix for one error message, written so it can be followed without reading the skill again."""
    rules = [
        ("missing section", "Add the heading exactly as in assets/prd-template.md, in the template's order."),
        ("duplicate ids", "Renumber so every id appears once as a line start."),
        ("malformed id", "Write the line as '- F-1: ...': a dash, the letter, a hyphen, a number, a colon."),
        ("has no U-", "Add one '- U-n: ...' line per user group the sources name."),
        ("has no F-", "Add one '- F-n: ...' line per feature."),
        ("has no P-", "Add one '- P-n: <name>. Includes: F-.. Exit: ...' line per phase."),
        ("has no M- line", "Add '- M-n: ...' for a goal whose target the sources give, or '- No metric yet for <goal>: the target is OPEN-n.'"),
        ("defines REQ", "Delete requirements, acceptance criteria and Given/When/Then; they belong to the feature specs."),
        ("has no Source", "Open the brief, find the decision that says this, and append 'Source: <brief path> decision <N>'. "
                          "If no decision or document says it, add an OPEN-n asking the user and append 'Source: OPEN-n'."),
        ("has no Priority", "Write 'Priority: must' (the sources put it in the launch scope), 'Priority: should' (launch is worse "
                            "without it) or 'Priority: later' (the sources put it after launch). Say in the reply which source decided."),
        ("has no Phase", "Append 'Phase: P-n', the phase the sources put this feature in; if they name none, 'Phase: OPEN-n'."),
        ("lacks Baseline", "Append 'Baseline: <today's value from a source>' or 'Baseline: none'."),
        ("lacks Measured by", "Append 'Measured by: <the instrument the sources name>'; if they name none, make it an OPEN-n."),
        ("lacks Source", "Append 'Source: <document and decision number that sets this target>'. If none sets it: " + OPEN_INSTEAD),
        ("no numeric Target", "If a source states the target, copy its number and unit. If not: " + OPEN_INSTEAD),
        ("is in no source", OPEN_INSTEAD),
        ("lists no F-", "Append 'Includes: F-a, F-b': the features whose 'Phase:' is this phase."),
        ("has no Exit", "Append 'Exit: <what can be observed when the phase is done>'."),
        ("lacks Trigger", "Append 'Trigger: <the event that makes the risk real>'."),
        ("lacks Impact", "Append 'Impact: <what breaks for the user or the launch>'."),
        ("lacks Mitigation", "Append 'Mitigation: <what is done before or when the trigger happens>'."),
        ("lacks Blocks", "Append 'Blocks: <F-n, M-n, P-n or nothing>'."),
        ("lacks Recommended", "Append 'Recommended: <your recommended answer and why>'."),
        ("TBD/TODO", "Replace the placeholder with what a source says; if no source says it, make it an OPEN-n with Blocks: and Recommended:."),
        ("appears in no P-", "Add its id to the 'Includes:' of the phase named in its 'Phase:'."),
    ]
    for key, fix in rules:
        if key in error:
            return fix
    return "Fix from the sources; what they do not give becomes an OPEN-n."


def section(text, heading):
    """The text between a '## heading' line and the next '## ' line."""
    m = re.search(r"^" + re.escape(heading) + r"\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def field(body, name):
    """The value of 'name:' inside an id block, up to the next known field."""
    m = re.search(name + r":\s*(.*?)(?=\s(?:Target|Baseline|Measured by|Source|Metric):|$)", body)
    return m.group(1) if m else ""


def numbers(text):
    """Number tokens of a text: ids, ISO dates and list numbering do not count; 1,000 equals 1000."""
    text = ISO_RE.sub(" ", re.sub(ANY_ID, " ", text))
    text = re.sub(r"(?m)^\s*\d+[.)]\s", " ", text)
    return {n.replace(",", "").rstrip(".") for n in NUM_RE.findall(text)}


def read_sources(prd_path, text, extra):
    """Source files the PRD names (Brief: line, Sources section), the state file and --source files that exist."""
    names = list(extra)
    m = re.search(r"^-\s*Brief:\s*(\S+)", text, re.M)
    if m:
        names.append(m.group(1))
    names += PATH_RE.findall(section(text, "## Sources"))
    names.append("docs/workbench/state.md")
    roots, here = [os.getcwd()], os.path.dirname(os.path.abspath(prd_path))
    for _ in range(4):
        roots.append(here)
        here = os.path.dirname(here)
    read, texts = [], []
    for name in names:
        name = name.strip("`'\"(),;:")
        for root in roots:
            full = os.path.normpath(os.path.join(root, name))
            if os.path.isfile(full) and os.path.abspath(full) != os.path.abspath(prd_path):
                if full not in read:
                    try:
                        texts.append(open(full, encoding="utf-8").read())
                        read.append(full)
                    except (OSError, UnicodeDecodeError):
                        pass
                break
    return read, "\n".join(texts)


def parse_args(argv):
    """(values, None), or (None, a usage error). values maps a value flag to its value, --source to the list of its
    values and a switch to True: the shape of the record's `arguments`."""
    values, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a in ("--file", "--report", "--source"):
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                return None, f"Error: {a} needs a value. See --help."
            if a == "--source":
                values.setdefault(a, []).append(argv[i + 1])
            else:
                values[a] = argv[i + 1]
            i += 2
        elif a in ("--table", "--json"):
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
    path, as_json, extra = values.get("--file"), "--json" in values, values.get("--source", [])
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
    for ln in text.splitlines():
        lm = LOOSE_ID_RE.match(ln)
        if lm and not ID_RE.match(ln):
            errors.append(f"malformed id line (write '- F-1: ...'): {ln.strip()[:60]}")
    for head, letter in (("## Users", "U"), ("## Features", "F"), ("## Release phases", "P")):
        if head in text and not any(i.startswith(letter + "-") for i in ids):
            errors.append(f"{head!r} has no {letter}-n line")
    if "## Success metrics" in text and not any(i.startswith("M-") for i in ids) \
            and not re.search(r"\bOPEN-\d+\b", section(text, "## Success metrics")):
        errors.append("'## Success metrics' has no M- line and names no OPEN-n that holds a target")
    sources_read, source_text = read_sources(path, text, extra)
    user_answers = " ".join(ln for ln in section(text, "## Sources").splitlines() if re.match(r"\s*-\s*User answer", ln, re.I))
    grounded = numbers(source_text + "\n" + user_answers)
    known_dates = (source_text + "\n" + user_answers).lower()
    if not sources_read:
        warnings.append("number check skipped: no source file could be read (name the brief on the '- Brief:' line or pass --source)")
    if re.search(r"^#+\s*Instructions found in external content", text, re.M | re.I):
        warnings.append("'Instructions found in external content' is a section of the reply, not of the PRD: move it to the reply")
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
            if sources_read:
                for name in ("Target", "Baseline"):
                    value = DATE_RE.sub(" ", field(body, name))
                    for n in sorted(numbers(value) - grounded):
                        errors.append(f"{i} {name.lower()} number {n} is in no source file")
        if i.startswith(("M-", "P-")) and sources_read:
            for dm in DATE_RE.finditer(body):
                if dm.group(0).lower() not in known_dates:
                    errors.append(f"{i} date {dm.group(0)} is in no source file")
        if i.startswith(("U-", "F-", "M-")):
            sm = re.search(r"Source:\s*(.*)$", body)
            if sm and sm.group(1).strip(" .").lower() in VAGUE_SOURCES:
                warnings.append(f"{i}: Source says only {sm.group(1).strip(' .')!r}; name the document and the decision number")
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
    summary = f'lint_prd result: "ok": {str(ok).lower()} ({len(errors)} errors, {len(warnings)} warnings)'
    counts = {k: sum(1 for i in blocks if i.startswith(k + "-")) for k in ("U", "F", "M", "R", "P", "ASSUMPTION", "OPEN")}
    result = {"ok": ok, "summary": summary, "counts": counts, "errors": errors, "warnings": warnings,
              "how_to_fix": [how_to_fix(e) for e in errors], "sources_read": sources_read}
    if "--table" in values:
        print(f"## Lint findings: {path}\n")
        used_open_rule = False

        def cell(value):
            nonlocal used_open_rule
            if OPEN_INSTEAD in value:
                used_open_rule = True
                value = value.replace(OPEN_INSTEAD, "Apply the OPEN rule printed under this table.")
            return value.replace("|", "/")

        if errors or warnings:
            print("| # | Finding | How to fix it |\n|---|---------|---------------|")
            for n, e in enumerate(errors, 1):
                print(f"| {n} | error: {cell(e)} | {cell(how_to_fix(e))} |")
            for n, w in enumerate(warnings, len(errors) + 1):
                print(f"| {n} | warning: {cell(w)} | Fix it when a source allows; it does not block. |")
        else:
            print("No findings.")
        if used_open_rule:
            print("\nOPEN rule: " + OPEN_INSTEAD)
        print("\nSources read for the number check: " + (", ".join(sources_read) or "none"))
        if not ok:
            print("Next: fix every error as its row says, then run this command again.")
        print(summary)
    else:
        print(json.dumps(result, indent=2 if as_json else None))
    if "--report" in values:
        record = {"script": "lint_prd.py", "date": datetime.date.today().isoformat(),
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
