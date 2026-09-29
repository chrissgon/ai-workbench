#!/usr/bin/env python3
"""Lint an ICP or positioning artifact for the mistakes models repeat.

Usage:
  python3 lint_icp.py --file docs/business/icp.md --kind icp
         [--validation-heading "Validation plan"] [--status-words hypothesis,validated]
  python3 lint_icp.py --file docs/business/positioning.md --kind positioning
         [--claims-heading "What we can truly claim"] [--confirmed-column "confirmed by"]
  common: [--sources-heading Sources] [--free-headings Method,Assumptions,Unknowns]
          [--hypothetical "would you,will you,if we,if you had,would it,interested in"]

Checks, each reported with the line number:
  status: no "Status:" line containing one of --status-words (both kinds).
  hypothetical_question: a line in the validation section that asks a hypothetical buying question
    (one of the comma-separated --hypothetical phrases, case-insensitive) (kind icp).
  missing_criteria: the validation section has no line with "validated if" and no line with
    "rejected if" (pass translations with --validated-label and --rejected-label) (kind icp).
  unconfirmed_claim: a row under the claims heading whose confirmed column is empty or "-"
    (kind positioning).
  bad_citation: a bracketed citation that is not one source number ([3], [2b]) or command label (M1).
  uncited_figure: a bullet or table row with a percentage or a currency amount and no source number,
    command label or assumption label, outside the sources section and --free-headings.
Headings are matched by their text after "## ", case-insensitive; pass translated texts for an
artifact not in English. Prints JSON to stdout; exit 1 when anything is reported, 2 on a bad
argument or unreadable file.
"""
import argparse
import json
import re
import sys

CURRENCY = re.compile(
    r"(?:[€$£]|R\$|US\$|\b(?:EUR|USD|BRL|GBP)\b)\s?\d|\d[\d.,]*\s?(?:[€£]|\b(?:EUR|USD|BRL|GBP)\b)")
FIGURE = re.compile(r"\d+(?:[.,]\d+)?\s?%|" + CURRENCY.pattern)
CITATION = re.compile(r"\[([^\]\n]+)\](?!\()")
GOOD_CITATION = re.compile(r"^(\d+[a-z]?|M\d+)$")
CITED = re.compile(r"\[(\d+[a-z]?|M\d+)\]|\bM\d+\b|assumption:|\bassumed\b", re.I)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True)
    ap.add_argument("--kind", choices=["icp", "positioning"], required=True)
    ap.add_argument("--validation-heading", default="Validation plan")
    ap.add_argument("--validated-label", default="validated if")
    ap.add_argument("--rejected-label", default="rejected if")
    ap.add_argument("--status-words", default="hypothesis,validated")
    ap.add_argument("--claims-heading", default="What we can truly claim")
    ap.add_argument("--confirmed-column", default="confirmed by")
    ap.add_argument("--sources-heading", default="Sources")
    ap.add_argument("--free-headings", default="Method,Assumptions,Unknowns")
    ap.add_argument("--assumed-label", default="Assumption:")
    ap.add_argument("--hypothetical", default="would you,will you,if we,if you had,would it,interested in")
    args = ap.parse_args()
    try:
        with open(args.file, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        print(f"lint_icp.py: cannot read {args.file}: {exc}", file=sys.stderr)
        sys.exit(2)
    low = lambda t: t.strip().lower()
    val, claims, srcs = low(args.validation_heading), low(args.claims_heading), low(args.sources_heading)
    free = {low(h) for h in args.free_headings.split(",") if h.strip()} | {srcs}
    hypos = [low(h) for h in args.hypothetical.split(",") if h.strip()]
    statuses = [low(w) for w in args.status_words.split(",") if w.strip()]
    assumed = low(args.assumed_label)
    findings, section, conf_col = [], "", None
    seen_val, has_ok, has_no, status_ok = False, False, False, False
    for n, line in enumerate(lines, 1):
        l = line.lower()
        if re.search(r"status\s*:", l) and any(w in l for w in statuses):
            status_ok = True
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            section, conf_col = low(m.group(1)), None
            seen_val = seen_val or section == val
            continue
        if args.kind == "icp" and section == val:
            has_ok = has_ok or low(args.validated_label) in l
            has_no = has_no or low(args.rejected_label) in l
            if any(h in l for h in hypos):
                findings.append({"line": n, "check": "hypothetical_question", "text": line.strip()[:160]})
        if args.kind == "positioning" and section == claims and line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if conf_col is None:
                hits = [i for i, c in enumerate(cells) if low(args.confirmed_column) in c.lower()]
                conf_col = hits[0] if hits else -1
            elif conf_col >= 0 and not set("".join(cells)) <= set("-: ") and conf_col < len(cells):
                if cells[conf_col] in ("", "-", "—"):
                    findings.append({"line": n, "check": "unconfirmed_claim", "text": line.strip()[:160]})
        if section != srcs:
            for tok in CITATION.findall(line):
                if low(tok) in ("", "x", "...", "…") or GOOD_CITATION.match(tok.strip()):
                    continue
                findings.append({"line": n, "check": "bad_citation", "text": f"[{tok}]"[:160]})
        if (section not in free and section and line.lstrip().startswith(("-", "*", "|"))
                and FIGURE.search(line) and not CITED.search(line) and assumed not in l):
            findings.append({"line": n, "check": "uncited_figure", "text": line.strip()[:160]})
    if not status_ok:
        findings.append({"line": 0, "check": "status", "text": f"no Status line with one of {statuses}"})
    if args.kind == "icp" and not (seen_val and has_ok and has_no):
        findings.append({"line": 0, "check": "missing_criteria",
                         "text": f"'## {args.validation_heading}' with '{args.validated_label}' and '{args.rejected_label}' lines"})
    report = {"file": args.file, "kind": args.kind, "findings": findings, "ok": not findings}
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
