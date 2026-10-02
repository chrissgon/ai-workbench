#!/usr/bin/env python3
"""Eval stand-in of an issue-tracker provider: no network, no account. Records every ticket it creates in wb/calls.log.

Usage:
  python3 tracker.py --check
  python3 tracker.py list --project <key>
  python3 tracker.py create --project <key> --title <text> --body-file <path> [--label <text>]...
                     --idempotency-key <key> [--dry-run]

--check prints whether the tracker can be reached. list prints the project's open tickets as JSON.
create creates one ticket and prints its key and link; with --dry-run it prints the ticket it would create
and creates nothing. Exit 0 ok, 2 usage error.
"""
import json
import sys
from pathlib import Path

WB = Path(__file__).resolve().parents[2]
args = sys.argv[1:]


def value(flag):
    if flag not in args or args.index(flag) + 1 >= len(args):
        print(f"error: {flag} needs a value", file=sys.stderr)
        sys.exit(2)
    return args[args.index(flag) + 1]


if not args or "--help" in args:
    print(__doc__.strip(), file=sys.stdout if args else sys.stderr)
    sys.exit(0 if args else 2)
if args[0] == "--check":
    print(json.dumps({"ok": True, "tracker": "stand-in", "projects": ["DRIFT"]}))
    sys.exit(0)
if args[0] == "list":
    print(json.dumps({"project": value("--project"), "tickets": []}))
    sys.exit(0)
if args[0] == "create":
    ticket = {"project": value("--project"), "title": value("--title"),
              "body": Path(value("--body-file")).read_text(encoding="utf-8"),
              "idempotency_key": value("--idempotency-key")}
    if "--dry-run" in args:
        print(json.dumps({"dry_run": True, **ticket}, indent=1))
        sys.exit(0)
    with open(WB / "calls.log", "a", encoding="utf-8") as log:
        log.write(f"create {ticket['project']} {ticket['idempotency_key']} {ticket['title']}\n")
    count = sum(1 for _ in open(WB / "calls.log", encoding="utf-8"))
    print(json.dumps({"key": f"{ticket['project']}-{count}", "url": f"https://tracker.example/{ticket['project']}-{count}"}))
    sys.exit(0)
print(f"error: unknown verb {args[0]!r}; see --help", file=sys.stderr)
sys.exit(2)
