#!/usr/bin/env python3
"""WCAG 2.x contrast ratios for colour pairs of a brand identity.

Usage:
  python3 contrast.py <<'EOF'
  {"pairs": [{"name": "headline on background", "fg": "#FFFFFF", "bg": "#000000", "use": "large"}]}
  EOF

"use" is "text" (needs 4.5:1 for AA), "large" (large text, 3:1) or "graphic" (non-text elements,
3:1). Colours are #RGB or #RRGGBB. Prints JSON with each pair's ratio (two decimals), the minimum
for its use, and pass or fail; exit 1 when any pair fails, 2 on bad input. The thresholds are the
WCAG 2 AA values (1.4.3 Contrast Minimum; 1.4.11 Non-text Contrast).
"""
import json
import re
import sys

MIN = {"text": 4.5, "large": 3.0, "graphic": 3.0}
HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def luminance(hex_colour):
    h = hex_colour[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    channels = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(fg, bg):
    a, b = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def fail(msg):
    print(f"contrast.py: {msg}", file=sys.stderr)
    sys.exit(2)


def main(argv):
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    try:
        data = json.load(sys.stdin)
    except ValueError:
        fail("stdin is not JSON")
    pairs = data.get("pairs") if isinstance(data, dict) else None
    if not isinstance(pairs, list) or not pairs:
        fail("expected {\"pairs\": [...]}")
    out, bad = [], 0
    for p in pairs:
        fg, bg, use = p.get("fg", ""), p.get("bg", ""), p.get("use", "text")
        if not (isinstance(fg, str) and HEX.match(fg) and isinstance(bg, str) and HEX.match(bg)):
            fail(f"pair {p.get('name')!r}: fg and bg must be #RGB or #RRGGBB")
        if use not in MIN:
            fail(f"pair {p.get('name')!r}: use must be one of {sorted(MIN)}")
        r = ratio(fg, bg)
        ok = r >= MIN[use]
        bad += not ok
        out.append({"name": p.get("name", ""), "fg": fg, "bg": bg, "use": use,
                    "ratio": round(r, 2), "minimum": MIN[use], "pass": ok})
    print(json.dumps({"pairs": out, "ok": bad == 0}, indent=2))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
