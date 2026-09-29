#!/usr/bin/env python3
"""Turn a LinkedIn profile export ("More > Save to PDF") into JSON, without the contact data.

Usage:
  python3 linkedin_export.py --text-file profile.txt [--today YYYY-MM-DD]
  uv run --with pypdf==5.1.0 python3 linkedin_export.py --file Profile.pdf [--today YYYY-MM-DD]

--file reads the PDF (needs pypdf, pinned as above); --text-file reads text already extracted from it.
Prints JSON to stdout:
  header_lines   the lines just before "Summary": name, headline and location, in that order
                 when the headline fits one line; check them against the PDF
  summary, top_skills, languages, certifications
  experience     one entry per role: company, title, start, end ("present" when current),
                 months (inclusive, computed), location, description
  education      lines of the Education section
  totals         first_start, months_since_first_start (to --today, default today),
                 years_and_months
  redacted       what was removed: the Contact section, e-mail addresses and phone numbers
The Contact section is dropped and every e-mail address and phone number anywhere is replaced by
[redacted]. Exit 0 ok, 1 when no role with dates is found, 2 on a bad argument or unreadable file.
Diagnostics go to stderr.
"""
import argparse
import json
import re
import sys
from datetime import date

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}
DATE_LINE = re.compile(
    r"^(?P<sm>[A-Za-z]+)\s+(?P<sy>\d{4})\s*-\s*(?:(?P<em>[A-Za-z]+)\s+(?P<ey>\d{4})|(?P<present>Present))"
    r"\s*(?:\(.*\))?\s*$")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
PHONE_MIN_DIGITS = 10  # year ranges such as "2020 - 2024" have 8
PAGE = re.compile(r"^Page \d+ of \d+$")
SIDEBAR = {"contact": "contact", "top skills": "top_skills", "languages": "languages",
           "certifications": "certifications", "honors-awards": "honors", "publications": "publications"}
MAIN = {"summary", "experience", "education"}


def clean(text):
    lines = []
    for raw in text.replace("\xa0", " ").splitlines():
        line = raw.strip()
        if not line or PAGE.match(line):
            continue
        lines.append(line)
    return lines


def redact(lines):
    counts = {"emails": 0, "phones": 0}
    out = []
    for line in lines:
        line, n = EMAIL.subn("[redacted]", line)
        counts["emails"] += n
        hits = [m for m in PHONE.finditer(line) if sum(c.isdigit() for c in m.group()) >= PHONE_MIN_DIGITS]
        for m in reversed(hits):
            line = line[:m.start()] + "[redacted]" + line[m.end():]
        counts["phones"] += len(hits)
        out.append(line)
    return out, counts


def months_between(start, end):
    return (end[0] - start[0]) * 12 + end[1] - start[1] + 1


def month_of(name, year):
    key = name.lower()
    if key not in MONTHS:
        raise ValueError(f"unknown month {name!r}")
    return (int(year), MONTHS[key])


def parse(text, today):
    lines = clean(text)
    # Split into sections by the headings LinkedIn prints on their own line.
    current, sections, order = "header", {"header": []}, ["header"]
    for line in lines:
        key = line.lower()
        if key in SIDEBAR or key in MAIN:
            current = SIDEBAR.get(key, key)
            sections.setdefault(current, [])
            order.append(current)
            continue
        sections.setdefault(current, []).append(line)
    dropped_contact = "contact" in sections
    sections.pop("contact", None)
    for key in list(sections):
        sections[key], _ = redact(sections[key])
    _, counts = redact([line for line in lines])

    # The name, headline and location sit at the end of the sidebar block, just before Summary.
    before = order[order.index("summary") - 1] if "summary" in order[1:] else order[-1]
    if before == "contact":
        before = "header"
    header_block = sections.get(before, [])
    header_lines = header_block[-3:]
    sections[before] = header_block[:-3]

    roles = []
    exp = sections.get("experience", [])
    idx = [i for i, line in enumerate(exp) if DATE_LINE.match(line)]
    for n, i in enumerate(idx):
        m = DATE_LINE.match(exp[i])
        start = month_of(m["sm"], m["sy"])
        end = (today.year, today.month) if m["present"] else month_of(m["em"], m["ey"])
        title = exp[i - 1] if i >= 1 else ""
        company = exp[i - 2] if i >= 2 else ""
        stop = idx[n + 1] - 2 if n + 1 < len(idx) else len(exp)
        body = exp[i + 1:stop]
        location = ""
        if body and len(body[0]) <= 40 and not body[0].endswith("."):
            location, body = body[0], body[1:]
        roles.append({
            "company": company, "title": title,
            "start": f"{start[0]:04d}-{start[1]:02d}",
            "end": "present" if m["present"] else f"{end[0]:04d}-{end[1]:02d}",
            "months": months_between(start, end), "location": location,
            "description": " ".join(body),
        })
    totals = {}
    if roles:
        first = min(r["start"] for r in roles)
        fy, fm = int(first[:4]), int(first[5:])
        months = (today.year - fy) * 12 + today.month - fm
        totals = {"first_start": first, "months_since_first_start": months,
                  "years_and_months": f"{months // 12} years {months % 12} months", "today": today.isoformat()}
    return {
        "header_lines": header_lines,
        "summary": " ".join(sections.get("summary", [])),
        "top_skills": sections.get("top_skills", []),
        "languages": sections.get("languages", []),
        "certifications": sections.get("certifications", []),
        "experience": roles,
        "education": sections.get("education", []),
        "totals": totals,
        "redacted": {"contact_section_dropped": dropped_contact, **counts},
    }


def read_pdf(path):
    try:
        import pypdf  # imported here so --text-file works without it
    except ImportError:
        print("linkedin_export.py: --file needs pypdf; run it with: uv run --with pypdf==5.1.0 python3 ...",
              file=sys.stderr)
        sys.exit(2)
    reader = pypdf.PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="the exported PDF")
    src.add_argument("--text-file", help="text already extracted from the export")
    ap.add_argument("--today", help="YYYY-MM-DD; default: today")
    args = ap.parse_args()
    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
    except ValueError:
        print("linkedin_export.py: --today must be YYYY-MM-DD", file=sys.stderr)
        sys.exit(2)
    try:
        if args.file:
            text = read_pdf(args.file)
        else:
            with open(args.text_file, encoding="utf-8") as fh:
                text = fh.read()
    except OSError as exc:
        print(f"linkedin_export.py: cannot read the export: {exc}", file=sys.stderr)
        sys.exit(2)
    try:
        result = parse(text, today)
    except ValueError as exc:
        print(f"linkedin_export.py: {exc}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["experience"]:
        print("linkedin_export.py: no role with dates found; is this a LinkedIn profile export?", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
