#!/usr/bin/env python3
"""Lint a messaging document written from assets/messaging-template.md.

Usage: python3 lint_messaging.py --file <messaging.md> [--json]

Checks:
  - required sections are present
  - every PROOF has Evidence: and Source:
  - every SECTION has Purpose:, Proof:, Headline:, Body:, Demo: (or CTA:) and Source:, and its Proof: names existing PROOF ids
    (the first section may carry no proof)
  - every number (digits, with optional unit) in a Headline: or Body: also appears in some PROOF line
  - no word from the "Avoid:" list appears in any Headline: or Body:
  - every OPEN has Blocks: and Recommended:
  - no TBD / TODO / ???

Prints JSON. Exit codes: 0 ok, 1 problems found, 2 usage error.
"""
import json
import re
import sys

SECTIONS = ["## Summary", "## Sources", "## Audience", "## Promise", "## Voice", "## Proof points", "## Sections",
            "## Taglines", "## Words", "## Open questions", "## Readiness"]
ID_RE = re.compile(r"^\s*-\s*((?:PROOF|SECTION|OPEN)-\d+)\s*:", re.M)


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
    m = re.search(name + r"\s*(.*?)(?=\s(?:Purpose|Proof|Headline|Body|Demo|CTA|Source|Evidence):|$)", body)
    return m.group(1).strip() if m else ""


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        print(__doc__); return 0 if argv else 2
    as_json = "--json" in argv
    path = argv[argv.index("--file") + 1] if "--file" in argv else None
    if not path:
        print("Error: --file <messaging.md> is required. See --help.", file=sys.stderr); return 2
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        print(f"Error: cannot read {path}: {e}", file=sys.stderr); return 2
    errors = []
    for s in SECTIONS:
        if s not in text:
            errors.append(f"missing section {s!r}")
    if re.search(r"\b(TBD|TODO)\b|\?\?\?", text):
        errors.append("contains TBD/TODO/???")
    proofs = blocks(text, ("PROOF-",))
    for pid, b in proofs.items():
        for part in ("Evidence:", "Source:"):
            if part not in b:
                errors.append(f"{pid} lacks {part}")
    proof_text = " ".join(proofs.values())
    proof_numbers = set(re.findall(r"\d[\d,.]*", proof_text))
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
        refs = re.findall(r"\bPROOF-\d+\b", field(b, "Proof:"))
        if i > 0 and not refs:
            errors.append(f"{sid} carries no proof point")
        for r in refs:
            if r not in proofs:
                errors.append(f"{sid} cites {r}, which does not exist")
        copy = field(b, "Headline:") + " " + field(b, "Body:")
        for num in re.findall(r"\d[\d,.]*", copy):
            if num.rstrip(".,") not in {n.rstrip(".,") for n in proof_numbers}:
                errors.append(f"{sid}: number {num} in the copy is not in any PROOF")
        low = copy.lower()
        for w in avoid:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                errors.append(f"{sid}: avoided word {w!r} in the copy")
    for oid, b in blocks(text, ("OPEN-",)).items():
        for part in ("Blocks:", "Recommended:"):
            if part not in b:
                errors.append(f"{oid} lacks {part}")
    ok = not errors
    print(json.dumps({"ok": ok, "counts": {"proofs": len(proofs), "sections": len(sections)}, "errors": errors}, indent=2 if as_json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
