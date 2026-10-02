#!/usr/bin/env python3
"""WCAG 2.x contrast ratios for colour pairs, in one mode or in a light and a dark mode.

Usage:
  python3 contrast.py <<'EOF'
  {"pairs": [{"name": "headline on background", "fg": "#FFFFFF", "bg": "#000000", "use": "large"}]}
  EOF
  python3 contrast.py --pairs <pairs.json> [--json]
  python3 contrast.py --pair "<name>" "#RRGGBB" "#RRGGBB" [--large | --use text|large|graphic] [--json]

A pair is one of:
  {"name": "...", "fg": "#text", "bg": "#background", "use": "text"}
  {"name": "...", "light": ["#text", "#background"], "dark": ["#text", "#background"], "use": "text"}
"use" is "text" (needs 4.5:1 for AA), "large" (large text, 3:1) or "graphic" (non-text and interface
elements, 3:1); the default is "text", and "large": true is read as "use": "large". A pair with modes
gives "light", "dark" or both. Colours are #RGB or #RRGGBB.

Input and output:
  standard input   {"pairs": [...]}; prints JSON
  --pairs <file>   a JSON file holding a list of pairs, or {"pairs": [...]}; prints a Markdown table
  --pair           one pair on the command line, in one mode; prints a Markdown table
  --json           with --pairs or --pair: print the JSON instead of the table
The JSON is {"pairs": [...], "ok": true|false}. A pair with fg and bg gives {"name", "fg", "bg", "use",
"ratio", "minimum", "pass"}; a pair with modes gives {"name", "use", "minimum", "light": {"fg", "bg",
"ratio", "pass"}, "dark": {...}, "pass"}. Ratios have two decimals. The table is printed also when a
pair fails.

Exit codes: 0 every pair passes; 1 at least one pair fails; 2 on bad input: a colour that is not
#RGB or #RRGGBB, an unknown use, an unknown flag, a flag without its value, a file that cannot be read.
The thresholds are the WCAG 2 AA values (1.4.3 Contrast Minimum; 1.4.11 Non-text Contrast).
Standard library only; no network.
"""
import json
import re
import sys

MIN = {"text": 4.5, "large": 3.0, "graphic": 3.0}
HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
MODES = ("light", "dark")


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


def colours(name, fg, bg):
    if not (isinstance(fg, str) and HEX.match(fg) and isinstance(bg, str) and HEX.match(bg)):
        fail(f"pair {name!r}: fg and bg must be #RGB or #RRGGBB")
    return fg, bg


def measure(pair):
    """One pair's result (see the module docstring for the two shapes)."""
    if not isinstance(pair, dict):
        fail("a pair must be an object")
    name = pair.get("name", "")
    use = pair.get("use", "large" if pair.get("large") is True else "text")
    if use not in MIN:
        fail(f"pair {name!r}: use must be one of {sorted(MIN)}")
    if any(mode in pair for mode in MODES):
        out = {"name": name, "use": use, "minimum": MIN[use]}
        for mode in MODES:
            if pair.get(mode) is None:
                continue
            value = pair[mode]
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                fail(f"pair {name!r}: {mode} must be [\"#text\", \"#background\"]")
            fg, bg = colours(name, value[0], value[1])
            r = ratio(fg, bg)
            out[mode] = {"fg": fg, "bg": bg, "ratio": round(r, 2), "pass": r >= MIN[use]}
        if not any(mode in out for mode in MODES):
            fail(f"pair {name!r}: give light, dark or both")
        out["pass"] = all(out[mode]["pass"] for mode in MODES if mode in out)
        return out
    fg, bg = colours(name, pair.get("fg", ""), pair.get("bg", ""))
    r = ratio(fg, bg)
    return {"name": name, "fg": fg, "bg": bg, "use": use, "ratio": round(r, 2), "minimum": MIN[use],
            "pass": r >= MIN[use]}


def table(rows):
    lines = ["| Pair | Light ratio | Dark ratio | AA |", "|------|-------------|------------|----|"]
    for r in rows:
        light = r["light"]["ratio"] if "light" in r else r.get("ratio")
        dark = r["dark"]["ratio"] if "dark" in r else None
        cells = [f"{v:.2f}:1" if v is not None else "n/a" for v in (light, dark)]
        lines.append(f"| {r['name']} | {cells[0]} | {cells[1]} | {'pass' if r['pass'] else 'fail'} "
                     f"(needs {r['minimum']}:1) |")
    return "\n".join(lines)


def read_pairs(data, where):
    pairs = data.get("pairs") if isinstance(data, dict) else data
    if not isinstance(pairs, list) or not pairs:
        fail(f"{where}: expected a non-empty list of pairs, or {{\"pairs\": [...]}}")
    return pairs


def parse(argv):
    """(pairs or None for standard input, as_json). Every flag is checked: an unknown one, or one without its
    value, is a usage error."""
    pairs, as_json, large, use, source, i = None, False, False, None, None, 0
    while i < len(argv):
        a = argv[i]
        if a == "--json":
            as_json = True
        elif a == "--large":
            large = True
        elif a == "--use":
            if i + 1 >= len(argv):
                fail("--use needs a value: text, large or graphic. See --help.")
            use, i = argv[i + 1], i + 1
        elif a == "--pairs":
            if i + 1 >= len(argv) or source:
                fail("--pairs needs a file, and is given once and without --pair. See --help.")
            source, i = ("pairs", argv[i + 1]), i + 1
        elif a == "--pair":
            if i + 3 >= len(argv) or source:
                fail("--pair needs a name, a text colour and a background colour, and is given once and "
                     "without --pairs. See --help.")
            source, i = ("pair", argv[i + 1:i + 4]), i + 3
        else:
            fail(f"unknown argument {a!r}. See --help.")
        i += 1
    if source is None:
        if as_json or large or use:
            fail("--json, --large and --use go with --pairs or --pair. See --help.")
        return None, True
    if source[0] == "pairs":
        if large or use:
            fail("--large and --use go with --pair; in a file each pair carries its own use. See --help.")
        try:
            with open(source[1], encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as e:
            fail(f"cannot read {source[1]}: {e}")
        return read_pairs(data, source[1]), as_json
    if large and use:
        fail("give --large or --use, not both. See --help.")
    name, fg, bg = source[1]
    return [{"name": name, "light": [fg, bg], "use": use or ("large" if large else "text")}], as_json


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0
    pairs, as_json = parse(argv)
    if pairs is None:
        if sys.stdin.isatty():
            fail("no pairs: pass {\"pairs\": [...]} on standard input, or --pairs <file>, or --pair. See --help.")
        try:
            data = json.load(sys.stdin)
        except ValueError:
            fail("stdin is not JSON")
        if not isinstance(data, dict):
            fail("expected {\"pairs\": [...]}")
        pairs = read_pairs(data, "stdin")
    rows = [measure(p) for p in pairs]
    ok = all(r["pass"] for r in rows)
    print(json.dumps({"pairs": rows, "ok": ok}, indent=2) if as_json else table(rows))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
