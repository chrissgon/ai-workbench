#!/usr/bin/env python3
"""Compute WCAG 2.x contrast ratios for text-on-background pairs, in one or two modes.

Usage:
  python3 contrast.py --pairs <pairs.json> [--json]
  python3 contrast.py --pair "<name>" "#RRGGBB" "#RRGGBB" [--large]

pairs.json is a list of objects: {"name": "...", "light": ["#text", "#background"], "dark": ["#text", "#background"], "large": false}
For each pair the script prints the ratio per mode and the AA result (4.5:1 for normal text, 3:1 for large text and interface elements).
Prints a Markdown table by default, JSON with --json. Exit codes: 0 ok, 2 usage error.
"""
import json
import sys


def channel(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def ratio(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def main(argv):
    if not argv or "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0 if argv else 2
    as_json = "--json" in argv
    pairs = []
    if "--pairs" in argv:
        path = argv[argv.index("--pairs") + 1]
        try:
            pairs = json.load(open(path, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error: cannot read {path}: {e}", file=sys.stderr)
            return 2
    elif "--pair" in argv:
        i = argv.index("--pair")
        pairs = [{"name": argv[i + 1], "light": [argv[i + 2], argv[i + 3]], "large": "--large" in argv}]
    else:
        print("Error: --pairs <file> or --pair <name> <text> <background> is required. See --help.", file=sys.stderr)
        return 2
    rows = []
    for p in pairs:
        threshold = 3.0 if p.get("large") else 4.5
        row = {"name": p["name"], "threshold": threshold}
        for mode in ("light", "dark"):
            if p.get(mode):
                r = ratio(p[mode][0], p[mode][1])
                row[mode] = round(r, 2)
                row[mode + "_pass"] = r >= threshold
        rows.append(row)
    if as_json:
        print(json.dumps(rows, indent=2))
    else:
        print("| Pair | Light ratio | Dark ratio | AA |")
        print("|------|-------------|------------|----|")
        for r in rows:
            l = f"{r['light']:.2f}:1" if "light" in r else "n/a"
            d = f"{r['dark']:.2f}:1" if "dark" in r else "n/a"
            ok = all(r.get(k, True) for k in ("light_pass", "dark_pass"))
            print(f"| {r['name']} | {l} | {d} | {'pass' if ok else 'fail'} (needs {r['threshold']}:1) |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
