#!/usr/bin/env python3
"""Lint a core-research brief for the rules in SKILL.md step 9.

Deterministic checks only; it does not judge whether a source is true, only that
the brief carries the fields and markers the skill promises.

Usage:
  python3 check-brief.py <brief.md> [--today YYYY-MM-DD] [--recency-months N] [--json]

Exit codes: 0 no errors, 1 errors found, 2 usage error.
"""
import argparse
import datetime
import json
import re
import sys

SOURCE_RE = re.compile(r"^\[(\d+)\]\s")
CLAIM_SECTIONS = ("Answer in brief", "Findings")
IMPERATIVE_RE = re.compile(r"\b(should|must|avoid|position around|do not|don't)\b", re.I)
PLACEHOLDER_RE = re.compile(r"[<>{}]|\.\.\.|example\.(com|org)|/owner/repo|<pkg>")
URL_RE = re.compile(r"https?://\S+")
PUBLISHED_RE = re.compile(r"Published\s+(\d{4}-\d{2}-\d{2})")
FLAG_RE = re.compile(r"older than|stale|flagged", re.I)
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


def check(path, today, recency_months):
    errors = []
    warnings = []
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    fields = header_fields(lines)
    status = fields.get("status", "").lower()
    capability = fields.get("search capability", "").lower().split("(")[0].strip()
    if status not in STATUS_VALUES:
        errors.append(f"header: Status must be one of {STATUS_VALUES}, found {status!r}")
    if capability not in CAPABILITY_VALUES:
        errors.append(f"header: Search capability must be one of {CAPABILITY_VALUES}, found {capability!r}")
    if capability and capability != "full" and status != "limited":
        errors.append("header: a capability below 'full' requires Status: limited")

    source_lines = [l for l in lines if SOURCE_RE.match(l)]
    if not source_lines:
        errors.append("no source entries found (lines beginning with [n])")
    published = {}
    for line in source_lines:
        n = SOURCE_RE.match(line).group(1)
        if "http" not in line:
            errors.append(f"source [{n}]: no URL")
        if "\u2014" not in line:
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
    defined = {SOURCE_RE.match(l).group(1) for l in source_lines}
    for heading, body in sections(lines):
        in_claims = any(heading.startswith(s) for s in CLAIM_SECTIONS)
        if in_claims:
            for line in body:
                if not line.strip().startswith("- "):
                    continue
                ids = re.findall(r"\[(\d+)", line)
                if not ids:
                    errors.append(f"claim without a citation in '{heading}': {line.strip()[:80]}")
                    continue
                for n in set(ids):
                    if n not in defined:
                        errors.append(f"claim cites [{n}] but no source entry defines it in '{heading}'")
                if len(set(ids)) == 1 and "single-source" not in line:
                    errors.append(
                        f"claim with one source is not tagged 'single-source' in '{heading}': {line.strip()[:80]}"
                    )
                for n in set(ids):
                    if n in old and not FLAG_RE.search(line):
                        errors.append(
                            f"claim cites [{n}] (published {old[n]}, older than {recency_months} months) "
                            f"without an age flag: {line.strip()[:80]}"
                        )
        if heading.startswith("Implications"):
            for line in body:
                if line.strip().startswith("- ") and IMPERATIVE_RE.search(line):
                    errors.append(f"implication reads as a directive in '{heading}': {line.strip()[:80]}")
        if heading.startswith("Query plan") and any(l.strip() for l in body):
            plan_seen = True
        for line in body:
            if "Queries for you to run:" in line and line.split("Queries for you to run:", 1)[1].strip(" ."):
                plan_seen = True
            if heading not in URL_SECTIONS:
                for url in URL_RE.findall(line):
                    errors.append(f"URL outside Sources/Method in '{heading}': {url}")
                if "Published" in line and PUBLISHED_RE.search(line):
                    errors.append(f"publication date outside Sources in '{heading}': {line.strip()[:80]}")

    if capability in ("partial", "none") and not plan_seen:
        errors.append("degraded mode needs a query plan (a '## Query plan' section or 'Queries for you to run:')")

    return errors, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lint a core-research brief.")
    parser.add_argument("path", help="path to the brief markdown file")
    parser.add_argument("--today", default=datetime.date.today().isoformat(),
                        help="access date the recency check uses (default: today)")
    parser.add_argument("--recency-months", type=int, default=12,
                        help="flag sources older than this many months (default: 12)")
    parser.add_argument("--json", action="store_true", help="print JSON (default)")
    args = parser.parse_args(argv)

    try:
        today = datetime.date.fromisoformat(args.today)
    except ValueError:
        print(json.dumps({"ok": False, "errors": [f"--today is not a date: {args.today}"], "warnings": []}))
        return 2
    try:
        errors, warnings = check(args.path, today, args.recency_months)
    except FileNotFoundError:
        print(json.dumps({"ok": False, "errors": [f"file not found: {args.path}"], "warnings": []}))
        return 2

    print(json.dumps({"ok": not errors, "path": args.path, "errors": errors, "warnings": warnings}))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
