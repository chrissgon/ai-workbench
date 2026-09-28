#!/usr/bin/env python3
"""Check the citations of a market analysis: every reference used is defined, and every source is complete.

Usage:
  python3 check_refs.py --file docs/business/market.md [--sources-heading Sources] [--method-heading Method]

Reads the Markdown file. References are [n] or [nb] (numbers, optional letter) and M<n> for
commands. Sources are the lines under the sources heading that start with [n]; commands are the
M<n> labels that appear under the method heading. Reports:
  undefined: references used in the text with no source entry (or M<n> absent from Method);
  unused: source entries never cited in the text;
  incomplete: source entries without an http(s) URL or without a quote ("...").
Headings are matched by their text after "## ", case-insensitive; pass the translated heading
when the artifact is not in English. Prints JSON to stdout; exit 1 when anything is reported,
2 on a bad argument or unreadable file.
"""
import argparse
import json
import re
import sys

REF = re.compile(r"\[(\d+[a-z]?)\]")
CMD = re.compile(r"\bM(\d+)\b")
QUOTE = re.compile(r"[\"“”]")


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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True)
    ap.add_argument("--sources-heading", default="Sources")
    ap.add_argument("--method-heading", default="Method")
    args = ap.parse_args()
    try:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(f"check_refs.py: cannot read {args.file}: {exc}", file=sys.stderr)
        sys.exit(2)
    secs = sections(text)
    src_key, meth_key = args.sources_heading.lower(), args.method_heading.lower()
    if src_key not in secs:
        print(f"check_refs.py: no '## {args.sources_heading}' heading in {args.file}", file=sys.stderr)
        sys.exit(2)
    sources = secs[src_key]
    method = secs.get(meth_key, "")
    body = "\n".join(v for k, v in secs.items() if k not in (src_key, meth_key))
    entries = {}
    for line in sources.splitlines():
        m = re.match(r"^\s*\[(\d+[a-z]?)\]\s*(.*)$", line)
        if m:
            entries[m.group(1)] = m.group(2)
    used = set(REF.findall(body))
    cmds_used = set(CMD.findall(body))
    cmds_defined = set(CMD.findall(method))
    key = lambda r: (int(re.match(r"\d+", r).group()), r)
    report = {
        "file": args.file,
        "sources": len(entries),
        "undefined": sorted(used - set(entries), key=key) + [f"M{n}" for n in sorted(cmds_used - cmds_defined, key=int)],
        "unused": sorted(set(entries) - used, key=key),
        "incomplete": [
            {"ref": r, "missing": [f for f, ok in (("url", "http" in e), ("quote", bool(QUOTE.search(e)))) if not ok]}
            for r, e in sorted(entries.items(), key=lambda kv: key(kv[0]))
            if "http" not in e or not QUOTE.search(e)
        ],
    }
    report["ok"] = not (report["undefined"] or report["unused"] or report["incomplete"])
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
