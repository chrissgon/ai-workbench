#!/usr/bin/env python3
"""Lint a market analysis for the mistakes models repeat: prices under Implications, price cells
that hold no price, and citations that are not source numbers.

Usage:
  python3 lint_market.py --file docs/business/market.md
         [--implications-heading "Implications for the next decisions"]
         [--alternatives-heading "Alternatives and competitors per offer"]
         [--price-column price] [--not-found-label "price not found"] [--sources-heading Sources]

Checks, each reported with the line number:
  implications_currency: a currency amount (a currency sign or code next to a number) in the
    implications section. Implications ask the next skill a question; they propose no price.
  price_cell: a cell of the price column, in any table under the alternatives heading, that holds
    no currency amount, does not start with 0 (free, doing nothing) and is not the not-found label.
  bad_citation: a bracketed citation outside the sources section that is not one source number
    ([3], [2b]) or one command label (M1): lists such as [2,3] or [8-13] and names such as [Acme] are
    reported; Markdown links [text](url), checkboxes and [...] in quotes are ignored.
Headings are matched by their text after "## " (the alternatives heading also matches "### "
subsections below it), case-insensitive; pass the translated text for an artifact not in English.
The price column is the first header cell that contains --price-column, case-insensitive.
Prints JSON to stdout; exit 1 when anything is reported, 2 on a bad argument or unreadable file.
"""
import argparse
import json
import re
import sys

CURRENCY = re.compile(
    r"(?:[€$£]|R\$|US\$|\b(?:EUR|USD|BRL|GBP)\b)\s?\d|\d[\d.,]*\s?(?:[€£]|\b(?:EUR|USD|BRL|GBP)\b)")
CITATION = re.compile(r"\[([^\]\n]+)\](?!\()")
GOOD_CITATION = re.compile(r"^(\d+[a-z]?|M\d+)$")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True)
    ap.add_argument("--implications-heading", default="Implications for the next decisions")
    ap.add_argument("--alternatives-heading", default="Alternatives and competitors per offer")
    ap.add_argument("--price-column", default="price")
    ap.add_argument("--not-found-label", default="price not found")
    ap.add_argument("--sources-heading", default="Sources")
    args = ap.parse_args()
    try:
        with open(args.file, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        print(f"lint_market.py: cannot read {args.file}: {exc}", file=sys.stderr)
        sys.exit(2)
    impl, alts, srcs = (h.strip().lower() for h in
                        (args.implications_heading, args.alternatives_heading, args.sources_heading))
    findings, section, price_col = [], "", None
    seen = {impl: False, alts: False}
    for n, line in enumerate(lines, 1):
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            section, price_col = m.group(1).strip().lower(), None
            if section in seen:
                seen[section] = True
            continue
        if re.match(r"^###\s", line):
            price_col = None
        if section == impl and CURRENCY.search(line):
            findings.append({"line": n, "check": "implications_currency", "text": line.strip()[:160]})
        if section == alts and line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if price_col is None:
                hits = [i for i, c in enumerate(cells) if args.price_column.lower() in c.lower()]
                price_col = hits[0] if hits else -1
            elif price_col >= 0 and not set("".join(cells)) <= set("-: ") and price_col < len(cells):
                cell = cells[price_col]
                if not (CURRENCY.search(cell) or re.match(r"0([.,]0+)?(\s|$|\()", cell)
                        or args.not_found_label.lower() in cell.lower()):
                    findings.append({"line": n, "check": "price_cell", "text": cell[:160]})
        if section != srcs:
            for tok in CITATION.findall(line):
                if tok.strip().lower() in ("", "x", "...", "\u2026") or GOOD_CITATION.match(tok.strip()):
                    continue
                hint = " (write one reference per bracket: [2][3])" if re.fullmatch(r"[\d\s,;\u2013-]+[a-z]?", tok) else ""
                findings.append({"line": n, "check": "bad_citation", "text": f"[{tok}]"[:160] + hint})
    missing = [h for h, found in seen.items() if not found]
    report = {"file": args.file, "missing_headings": missing, "findings": findings,
              "ok": not findings and not missing}
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
