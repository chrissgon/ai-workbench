#!/usr/bin/env python3
"""Find the longest value a variable field of a template must fit (a page title, a section name).

Usage: python3 longest_value.py <value> [<value>...]
       printf '%s\\n' "Button" "Input Group" | python3 longest_value.py

Values come as arguments or, when there are none, one per line on stdin. Empty lines are ignored and
surrounding whitespace is trimmed. Prints JSON: {"count", "longest", "characters", "words", "runners_up"}
where "runners_up" holds the next two values by length. A tie keeps the first value in input order.

Exit codes: 0 ok, 2 usage error (no value given).
"""
import json
import sys


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    values = argv if argv else sys.stdin.read().splitlines()
    values = [v.strip() for v in values if v.strip()]
    if not values:
        print("Error: give the values as arguments or one per line on stdin. See --help.", file=sys.stderr)
        return 2
    ranked = sorted(values, key=len, reverse=True)  # stable: a tie keeps input order
    print(json.dumps({"count": len(values), "longest": ranked[0], "characters": len(ranked[0]),
                      "words": len(ranked[0].split()),
                      "runners_up": [{"value": v, "characters": len(v)} for v in ranked[1:3]]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
