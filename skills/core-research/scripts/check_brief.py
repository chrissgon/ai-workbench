#!/usr/bin/env python3
"""Check a core-research brief against the rules of the skill's self-check step.

Deterministic checks only: it does not judge whether a source is true, only that the brief carries the
fields and markers the skill promises.

Usage:
  python3 check_brief.py --file <brief.md> [--today YYYY-MM-DD] [--recency-months <n>] [--report <path>]

  --file <path>          the brief to check (required)
  --today YYYY-MM-DD     the date the recency check counts from (default: today)
  --recency-months <n>   a source published more than this many months before --today needs an age flag
                         next to every claim that cites it (default: 12)
  --report <path>        also write the result as one JSON record to this path (the evidence convention)

What fails the check:
  - a header without `Status: draft | limited` or `Search capability: full | partial | none`; a capability
    below `full` without `Status: limited`
  - no source entry (a line `[n] ...`) when the capability is `full`; a limited brief may have none
  - a source line without URL, publisher (after an em dash), `Published <date | undated>`, `Accessed <date>`,
    `Tier 1|2|3` or `Quote:`; a placeholder URL
  - a bullet of "Answer in brief" or "Findings" with no citation, unless it says `not established` or
    `Nothing established`; a citation of a source no entry defines; a claim with one source and no
    `single-source` tag; a claim citing a source older than the recency threshold with no age flag
  - a bullet of "Contradictions" or "Implications" that holds a figure (a number other than a year) and no
    citation. "Unknowns" is never checked for figures: an unknown names what is missing, not a finding.
  - a directive in "Implications" (should, must, avoid, position around, do not)
  - in a limited brief with no source, an "Implications" bullet other than `none: ...`
  - a URL or a publication date outside "Sources" and "Method"
  - a capability below `full` without a query plan

Output: one JSON object on stdout with ok, summary, path, errors, warnings and counts. Diagnostics of a usage
error go to stderr. Exit codes: 0 no errors, 1 errors found, 2 usage error (nothing is checked).
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

SCRIPT = "check_brief.py"
SOURCE_RE = re.compile(r"^\[(\d+)\]\s")
CITATION_RE = re.compile(r"\[(\d+)")
CLAIM_SECTIONS = ("Answer in brief", "Findings")
# A figure without a citation is checked in these two sections only. "Unknowns" is left out on purpose: an
# unknown says what could not be established, and its numbers are part of the question, not a finding.
FIGURE_SECTIONS = ("Contradictions", "Implications")
IMPERATIVE_RE = re.compile(r"\b(should|must|avoid|position around|do not|don't)\b", re.I)
PLACEHOLDER_RE = re.compile(r"[<>{}]|\.\.\.|example\.(com|org)|/owner/repo|<pkg>")
URL_RE = re.compile(r"https?://\S+")
PUBLISHED_RE = re.compile(r"Published\s+(\d{4}-\d{2}-\d{2})")
FLAG_RE = re.compile(r"older than|stale|flagged", re.I)
NOT_ESTABLISHED_RE = re.compile(r"\bnot established\b|\bnothing established\b", re.I)
NONE_RE = re.compile(r"^-\s*none\b", re.I)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
URL_SECTIONS = ("Sources", "Method")
STATUS_VALUES = ("draft", "limited")
CAPABILITY_VALUES = ("full", "partial", "none")


def sections(lines):
    """Yield (heading, [lines]) for each level-2 section, plus the header as ''."""
    current = ""
    body = []
    for line in lines:
        if line.startswith("## "):
            yield current, body
            current = line[3:].strip()
            body = []
        else:
            body.append(line)
    yield current, body


def header_fields(lines):
    fields = {}
    for line in lines:
        if line.startswith("## "):
            break
        m = re.match(r"^-\s*([A-Za-z ]+):\s*(.*)$", line)
        if m:
            fields[m.group(1).strip().lower()] = m.group(2).strip()
    return fields


def months_between(old, today):
    return (today.year - old.year) * 12 + (today.month - old.month) - (1 if today.day < old.day else 0)


def holds_figure(line):
    """True when the line holds a number other than a year, once its citations are taken out."""
    text = CITATION_RE.sub("", line)
    text = re.sub(r"\]", "", text)
    text = YEAR_RE.sub("", text)
    return bool(re.search(r"\d", text))


def check(text, today, recency_months):
    errors = []
    warnings = []
    lines = text.splitlines()

    fields = header_fields(lines)
    status = fields.get("status", "").lower()
    capability = fields.get("search capability", "").lower().split("(")[0].strip()
    limited = capability in ("partial", "none")
    if status not in STATUS_VALUES:
        errors.append(f"header: Status must be one of {STATUS_VALUES}, found {status!r}")
    if capability not in CAPABILITY_VALUES:
        errors.append(f"header: Search capability must be one of {CAPABILITY_VALUES}, found {capability!r}")
    if limited and status != "limited":
        errors.append("header: a capability below 'full' requires Status: limited")

    source_lines = [l for l in lines if SOURCE_RE.match(l)]
    if not source_lines and not limited:
        errors.append("no source entries found (lines beginning with [n]); only a limited brief may have none")
    published = {}
    for line in source_lines:
        n = SOURCE_RE.match(line).group(1)
        if "http" not in line:
            errors.append(f"source [{n}]: no URL")
        if "—" not in line:
            errors.append(f"source [{n}]: no publisher (expected an em dash before it)")
        if not re.search(r"Published\s+\S", line):
            errors.append(f"source [{n}]: no publication date or 'undated'")
        if not re.search(r"Accessed\s+\S", line):
            errors.append(f"source [{n}]: no access date")
        if not re.search(r"Tier\s+[123]", line):
            errors.append(f"source [{n}]: no tier (Tier 1|2|3)")
        if "Quote:" not in line:
            errors.append(f"source [{n}]: no supporting quote")
        url = URL_RE.search(line)
        if url and PLACEHOLDER_RE.search(url.group(0)):
            errors.append(f"source [{n}]: URL is a placeholder, not an opened page: {url.group(0)}")
        m = PUBLISHED_RE.search(line)
        if m:
            published[n] = m.group(1)

    old = {}
    for n, iso in published.items():
        try:
            d = datetime.date.fromisoformat(iso)
        except ValueError:
            continue
        if months_between(d, today) > recency_months:
            old[n] = iso

    plan_seen = False
    claims = 0
    defined = {SOURCE_RE.match(l).group(1) for l in source_lines}
    for heading, body in sections(lines):
        bullets = [l.strip() for l in body if l.strip().startswith("- ")]
        if any(heading.startswith(s) for s in CLAIM_SECTIONS):
            for line in bullets:
                ids = CITATION_RE.findall(line)
                if not ids:
                    if NOT_ESTABLISHED_RE.search(line):
                        continue
                    errors.append(f"claim without a citation in '{heading}': {line[:80]}")
                    continue
                claims += 1
                for n in sorted(set(ids)):
                    if n not in defined:
                        errors.append(f"claim cites [{n}] but no source entry defines it in '{heading}'")
                if len(set(ids)) == 1 and "single-source" not in line:
                    errors.append(f"claim with one source is not tagged 'single-source' in '{heading}': {line[:80]}")
                for n in sorted(set(ids)):
                    if n in old and not FLAG_RE.search(line):
                        errors.append(
                            f"claim cites [{n}] (published {old[n]}, older than {recency_months} months) "
                            f"without an age flag: {line[:80]}"
                        )
        if any(heading.startswith(s) for s in FIGURE_SECTIONS):
            for line in bullets:
                if holds_figure(line) and not CITATION_RE.search(line):
                    errors.append(f"figure without a citation in '{heading}': {line[:80]}")
        if heading.startswith("Implications"):
            for line in bullets:
                if IMPERATIVE_RE.search(line):
                    errors.append(f"implication reads as a directive in '{heading}': {line[:80]}")
                if limited and not source_lines and not NONE_RE.match(line):
                    errors.append(
                        f"a limited brief with no source has no implication; write '- none: no finding to draw "
                        f"a consequence from' in '{heading}': {line[:80]}"
                    )
        if heading.startswith("Query plan") and any(l.strip() for l in body):
            plan_seen = True
        for line in body:
            if "Queries for you to run:" in line and line.split("Queries for you to run:", 1)[1].strip(" ."):
                plan_seen = True
            if heading not in URL_SECTIONS:
                for url in URL_RE.findall(line):
                    errors.append(f"URL outside Sources/Method in '{heading}': {url}")
                if PUBLISHED_RE.search(line):
                    errors.append(f"publication date outside Sources in '{heading}': {line.strip()[:80]}")

    if limited and not plan_seen:
        errors.append("degraded mode needs a query plan (a '## Query plan' section or 'Queries for you to run:')")

    counts = {"sources": len(source_lines), "cited_claims": claims}
    return errors, warnings, counts


def write_report(path, arguments, result):
    record = {"script": SCRIPT, "date": datetime.date.today().isoformat(), "arguments": arguments,
              "ok": result["ok"], "summary": result["summary"], "errors": result["errors"],
              "warnings": result["warnings"], "counts": result["counts"]}
    Path(path).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog=SCRIPT, description="Check a core-research brief against the rules of the skill's self-check step.",
        epilog="Exit codes: 0 no errors, 1 errors found, 2 usage error.")
    parser.add_argument("--file", required=True, metavar="<path>", help="the brief to check")
    parser.add_argument("--today", metavar="YYYY-MM-DD", default=None,
                        help="the date the recency check counts from (default: today)")
    parser.add_argument("--recency-months", type=int, default=12, metavar="<n>",
                        help="flag sources older than this many months (default: 12)")
    parser.add_argument("--report", metavar="<path>", default=None,
                        help="also write the result as one JSON record to this path")
    args = parser.parse_args(argv)

    if args.today is None:
        today = datetime.date.today()
    else:
        try:
            today = datetime.date.fromisoformat(args.today)
        except ValueError:
            print(f"Error: --today is not a date (YYYY-MM-DD): {args.today}", file=sys.stderr)
            return 2
    if args.recency_months < 0:
        print("Error: --recency-months must be 0 or more.", file=sys.stderr)
        return 2
    try:
        text = Path(args.file).read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
        print(f"Error: cannot read --file {args.file}: {e.strerror or e}", file=sys.stderr)
        return 2

    errors, warnings, counts = check(text, today, args.recency_months)
    ok = not errors
    n = len(errors)
    summary = (f"check_brief ok: 0 errors, {counts['sources']} sources" if ok
               else f"check_brief FAILED: {n} error{'s' if n != 1 else ''}")
    result = {"ok": ok, "summary": summary, "path": args.file, "errors": errors, "warnings": warnings,
              "counts": counts}
    print(json.dumps(result, ensure_ascii=False))
    if args.report:
        write_report(args.report, typed_arguments(sys.argv[1:] if argv is None else argv), result)
    return 0 if ok else 1


def typed_arguments(argv):
    """Every flag given except --report, with its value as typed (the last one when a flag is repeated)."""
    arguments = {}
    i = 0
    while i < len(argv):
        item = argv[i]
        if item.startswith("--") and "=" in item:
            flag, value = item.split("=", 1)
            i += 1
        elif item.startswith("--") and i + 1 < len(argv):
            flag, value = item, argv[i + 1]
            i += 2
        else:
            i += 1
            continue
        if flag != "--report":
            arguments[flag] = value
    return arguments


if __name__ == "__main__":
    sys.exit(main())
