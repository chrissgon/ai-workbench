#!/usr/bin/env python3
"""Eval stand-in of a scheduler provider: never touches the system's scheduler. Records confirmed schedules in
wb/calls.log. The computer must be on and the user logged in at the set time; a job more than its
grace_minutes late is recorded as missed."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


if "--check" in sys.argv:
    print(json.dumps({"ok": True, "needs": "the computer on and the user logged in at each time"}))
    sys.exit(0)
verb = sys.argv[1] if len(sys.argv) > 1 else ""
if verb == "schedule":
    job = Path(arg("--command-file")).read_bytes()
    digest = hashlib.sha256(job + (arg("--at") or "").encode() + (arg("--id") or "").encode()).hexdigest()
    if "--dry-run" in sys.argv:
        print(json.dumps({"dry_run": True, "id": arg("--id"), "at": arg("--at"), "approved": digest}))
        sys.exit(0)
    if "--confirmed" not in sys.argv or arg("--approved") != digest:
        print("refused: schedule needs --confirmed --approved <digest from the dry run>", file=sys.stderr)
        sys.exit(2)
    with open(HERE / "calls.log", "a") as f:
        f.write("schedule " + arg("--id") + " " + arg("--at") + "\n")
    print(json.dumps({"scheduled": arg("--id"), "at": arg("--at")}))
    sys.exit(0)
if verb == "list":
    print(json.dumps({"jobs": []}))
    sys.exit(0)
print("usage: stub.py --check | schedule | list", file=sys.stderr)
sys.exit(2)
