#!/usr/bin/env python3
"""Eval stub of the LinkedIn publisher provider: no network, no token. Records confirmed calls in wb/calls.log."""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
EXPIRES = os.environ.get("STUB_TOKEN_EXPIRES_AT") or (HERE / "token_expires_at.txt").read_text().strip()


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


if "--check" in sys.argv:
    print(json.dumps({"ok": True, "token_expires_at": EXPIRES}))
    sys.exit(0)
if len(sys.argv) > 1 and sys.argv[1] == "publish":
    text = Path(arg("--text-file")).read_text()
    comment = Path(arg("--first-comment-file")).read_text() if arg("--first-comment-file") else None
    if "--dry-run" in sys.argv:
        print(json.dumps({"dry_run": True, "idempotency_key": arg("--idempotency-key"),
                          "body": {"author": "urn:li:person:<resolved at publish time>", "commentary": text},
                          "first_comment": comment,
                          "note": "#word renders as a LinkedIn hashtag; @name renders as plain text"}, indent=1))
        sys.exit(0)
    if "--confirmed" not in sys.argv:
        print("refused: publish needs --confirmed or --dry-run", file=sys.stderr)
        sys.exit(2)
    with open(HERE / "calls.log", "a") as f:
        f.write("publish " + arg("--idempotency-key") + "\n")
    print(json.dumps({"post_urn": "urn:li:share:1", "replayed": False}))
    sys.exit(0)
print("usage: linkedin.py --check | publish ...", file=sys.stderr)
sys.exit(2)
