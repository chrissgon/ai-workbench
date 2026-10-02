#!/usr/bin/env python3
"""Lint a messaging document written from assets/messaging-template.md.

Usage: python3 lint_messaging.py --file <messaging.md> [--report <path>] [--json]

Checks:
  - required sections are present
  - every PROOF has Evidence:, Method:, Date: (with a YYYY-MM-DD date) and Source:
  - every SECTION has Purpose:, Proof:, Headline:, Body:, Demo: (or CTA:) and Source:, and its Proof: names
    existing PROOF ids (the first section may carry no proof); every later section's Demo: describes something
    (not empty, not "none")
  - every number in a Headline:, a Body: or a tagline also appears in some PROOF: digits ("14", "2.9") and
    number words ("eight", "half", "twice"; a PROOF may carry the word or its digits)
  - no word from the "Avoid:" list appears in any Headline: or Body:
  - every OPEN has Blocks: and Recommended:
  - no TBD / TODO / ???

It cannot check that a Method: belongs to its number: that is checked by reading.

Options:
  --file <path>     the messaging document (required)
  --report <path>   also write the record of this run there, as one JSON object: script, date, arguments,
                    ok, summary, errors, counts
  --json            pretty-print the output (indented); the output is JSON either way

Prints one JSON line: ok, summary, counts (proofs, sections), errors.
Exit codes: 0 ok, 1 problems found, 2 usage error or unreadable file.
"""
import argparse
import datetime
import json
import re
import sys

SECTIONS = ["## Summary", "## Sources", "## Audience", "## Promise", "## Voice", "## Proof points", "## Sections",
            "## Taglines", "## Words", "## Open questions", "## Assumptions", "## Readiness"]
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
NUM_RE = re.compile(r"\d[\d,.]*")
WORDS = {"two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
         "ten": "10", "eleven": "11", "twelve": "12", "twenty": "20", "thirty": "30", "fifty": "50", "hundred": "100",
         "thousand": "1000", "half": None, "twice": None, "double": None, "triple": None}
WORD_RE = re.compile(r"\b(" + "|".join(WORDS) + r")\b", re.I)
ID_RE = re.compile(r"^\s*-\s*((?:PROOF|SECTION|OPEN)-\d+)\s*:", re.M)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"Error: {message}. See --help.", file=sys.stderr)
        sys.exit(2)


def parse(argv):
    p = Parser(prog="lint_messaging.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
               usage="python3 lint_messaging.py --file <messaging.md> [--report <path>] [--json]")
    p.add_argument("--file", required=True, metavar="<messaging.md>")
    p.add_argument("--report", metavar="<path>")
    p.add_argument("--json", action="store_true")
    return p.parse_args(argv)


def blocks(text, prefixes):
    out, cur = {}, None
    for ln in text.splitlines():
        m = ID_RE.match(ln)
        if m and m.group(1).startswith(prefixes):
            cur = m.group(1); out[cur] = [ln]
        elif cur and ln.startswith("  "):
            out[cur].append(ln)
        else:
            cur = None
    return {k: " ".join(v) for k, v in out.items()}


def field(body, name):
    m = re.search(name + r"\s*(.*?)(?=\s(?:Purpose|Proof|Headline|Body|Demo|CTA|Source|Evidence|Method|Date):|$)", body)
    return m.group(1).strip() if m else ""


def lint(text):
    """The problems of one messaging document, and the counts of its proofs and sections."""
    errors = []
    for s in SECTIONS:
        if s not in text:
            errors.append(f"missing section {s!r}")
    if re.search(r"\b(TBD|TODO)\b|\?\?\?", text):
        errors.append("contains TBD/TODO/???")
    proofs = blocks(text, ("PROOF-",))
    for pid, b in proofs.items():
        for part in ("Evidence:", "Method:", "Date:", "Source:"):
            if part not in b:
                errors.append(f"{pid} lacks {part}")
        if "Date:" in b and not DATE_RE.search(field(b, "Date:")):
            errors.append(f"{pid}: Date: carries no YYYY-MM-DD date")
    proof_text = " ".join(proofs.values())
    proof_numbers = {n.rstrip(".,") for n in NUM_RE.findall(DATE_RE.sub(" ", proof_text))}
    proof_words = {w.lower() for w in WORD_RE.findall(proof_text)}

    def unproven(copy):
        """Numbers of a piece of copy, as digits or as words, that no PROOF carries."""
        out = [n for n in NUM_RE.findall(copy) if n.rstrip(".,") not in proof_numbers]
        for w in WORD_RE.findall(copy):
            if w.lower() not in proof_words and WORDS[w.lower()] not in proof_numbers:
                out.append(w)
        return out
    avoid_m = re.search(r"^\s*-\s*Avoid:\s*(.*)$", text, re.M)
    avoid = [w.strip().strip('"').lower() for w in re.split(r",|;", avoid_m.group(1))] if avoid_m else []
    avoid = [w for w in avoid if w and not w.startswith("(")]
    sections = blocks(text, ("SECTION-",))
    for i, (sid, b) in enumerate(sections.items()):
        for part in ("Purpose:", "Headline:", "Body:", "Source:"):
            if part not in b:
                errors.append(f"{sid} lacks {part}")
        if "Demo:" not in b and "CTA:" not in b:
            errors.append(f"{sid} lacks Demo: or CTA:")
        demo = field(b, "Demo:").lower().strip(" .`*")
        if i > 0 and (not demo or re.match(r"(none|n/a|no demo|nothing)\b", demo)):
            errors.append(f"{sid}: Demo: must describe what the design shows; a section with nothing to show is merged into another")
        refs = re.findall(r"\bPROOF-\d+\b", field(b, "Proof:"))
        if i > 0 and not refs:
            errors.append(f"{sid} carries no proof point")
        for r in refs:
            if r not in proofs:
                errors.append(f"{sid} cites {r}, which does not exist")
        copy = field(b, "Headline:") + " " + field(b, "Body:")
        for num in unproven(copy):
            errors.append(f"{sid}: number {num} in the copy is not in any PROOF")
        low = copy.lower()
        for w in avoid:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                errors.append(f"{sid}: avoided word {w!r} in the copy")
    tag_m = re.search(r"^## Taglines\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    for num in unproven(tag_m.group(1)) if tag_m else []:
        errors.append(f"Taglines: number {num} is not in any PROOF")
    for oid, b in blocks(text, ("OPEN-",)).items():
        for part in ("Blocks:", "Recommended:"):
            if part not in b:
                errors.append(f"{oid} lacks {part}")
    return errors, {"proofs": len(proofs), "sections": len(sections)}


def main(argv):
    args = parse(argv)
    try:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"Error: cannot read {args.file}: {e}", file=sys.stderr)
        return 2
    errors, counts = lint(text)
    ok = not errors
    summary = (f"lint_messaging {'ok' if ok else 'FAILED'}: {len(errors)} errors, "
               f"{counts['proofs']} proofs, {counts['sections']} sections")
    if args.report:
        arguments = {"--file": args.file}
        if args.json:
            arguments["--json"] = True
        record = {"script": "lint_messaging.py", "date": datetime.date.today().isoformat(), "arguments": arguments,
                  "ok": ok, "summary": summary, "errors": errors, "counts": counts}
        try:
            with open(args.report, "w", encoding="utf-8") as f:
                f.write(json.dumps(record, indent=2) + "\n")
        except OSError as e:
            print(f"Error: cannot write {args.report}: {e}", file=sys.stderr)
            return 2
    print(json.dumps({"ok": ok, "summary": summary, "counts": counts, "errors": errors},
                     indent=2 if args.json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
