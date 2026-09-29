#!/usr/bin/env python3
"""Check a brand profile before it is handed to the skills and agents that write in public.

Usage:
  python3 check_profile.py --file docs/brand/profile.md [--sources-heading Sources]
      [--samples-heading "Voice"] [--never-heading "Never expose"]

Headings are matched by their text after "## ", case-insensitive; pass the translated heading when
the artifact is not in English. Reports, as JSON on stdout:
  contact_data   lines that carry an e-mail address or a phone number (the profile is read by agents
                 that publish; contact data never belongs in it)
  undefined      references [n] used in the text with no entry under the sources heading
  unused         source entries never cited
  no_date        source entries without a date (YYYY-MM-DD or YYYY-MM or a year)
  never_empty    true when the never-expose section is missing or has no item
  samples_unmarked  true when the voice section quotes text (lines starting with ">") but never
                 says who wrote it (a line with "written by" or "not voice samples"); pass the
                 translated phrases with --author-marker when the artifact is not in English
Exit 1 when anything is reported, 2 on a bad argument or unreadable file.
"""
import argparse
import json
import re
import sys

REF = re.compile(r"\[(\d+)\]")
REF_GROUP = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)(?:\s*,[^\]]*)?\]")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
LINKS = re.compile(r"(https?://\S+|urn:[\w:.()-]+)")
DATE = re.compile(r"\b(19|20)\d{2}\b")
MARKERS = ["written by", "not voice samples"]


def sections(text):
    out, name, buf = {}, "", []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            out[name] = out.get(name, "") + "\n".join(buf)
            name, buf = m.group(1).strip().lower(), []
        else:
            buf.append(line)
    out[name] = out.get(name, "") + "\n".join(buf)
    return out


def cited(text):
    found = set()
    for m in REF_GROUP.finditer(text):
        found.update(n.strip() for n in m.group(1).split(","))
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True)
    ap.add_argument("--sources-heading", default="Sources")
    ap.add_argument("--samples-heading", default="Voice")
    ap.add_argument("--never-heading", default="Never expose")
    ap.add_argument("--author-marker", action="append", default=[],
                    help="extra phrase that says who wrote a sample; repeatable")
    args = ap.parse_args()
    try:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(f"check_profile.py: cannot read {args.file}: {exc}", file=sys.stderr)
        sys.exit(2)
    secs = sections(text)
    src_key = args.sources_heading.lower()
    if src_key not in secs:
        print(f"check_profile.py: no '## {args.sources_heading}' heading in {args.file}", file=sys.stderr)
        sys.exit(2)

    contact = []
    for no, line in enumerate(text.splitlines(), start=1):
        bare = LINKS.sub(" ", line)  # ids inside URLs and URNs are not phone numbers
        phones = [m for m in PHONE.finditer(bare) if 10 <= sum(c.isdigit() for c in m.group()) <= 15]
        if EMAIL.search(line) or phones:
            contact.append(no)

    entries = {}
    for line in secs[src_key].splitlines():
        m = re.match(r"^\s*\[(\d+)\]\s*(.*)$", line)
        if m:
            entries[m.group(1)] = m.group(2)
    body = "\n".join(v for k, v in secs.items() if k != src_key)
    used = cited(body)
    report = {
        "contact_data": [f"line {n}" for n in contact],
        "undefined": sorted(used - set(entries), key=int),
        "unused": sorted(set(entries) - used, key=int),
        "no_date": sorted((k for k, v in entries.items() if not DATE.search(v)), key=int),
    }
    never = secs.get(args.never_heading.lower())
    report["never_empty"] = never is None or not re.search(r"^\s*[-*]\s+\S", never, re.M)
    samples = secs.get(args.samples_heading.lower(), "")
    markers = [m.lower() for m in MARKERS + args.author_marker]
    quotes = re.search(r"^\s*>", samples, re.M)
    report["samples_unmarked"] = bool(quotes) and not any(m in samples.lower() for m in markers)
    report["ok"] = not (report["contact_data"] or report["undefined"] or report["unused"] or report["no_date"]
                        or report["never_empty"] or report["samples_unmarked"])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
