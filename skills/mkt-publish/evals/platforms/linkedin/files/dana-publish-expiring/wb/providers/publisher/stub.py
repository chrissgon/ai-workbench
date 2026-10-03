#!/usr/bin/env python3
"""Eval stand-in of a publisher provider: no network, no token. Records confirmed calls in wb/calls.log."""
import json
import sys
from pathlib import Path

PLATFORMS = ("linkedin",)
HERE = Path(__file__).resolve().parents[2]
EXPIRES = (HERE / "token_expires_at.txt").read_text().strip()


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


platform = arg("--platform")
if platform is not None and platform not in PLATFORMS:
    print(f"error: --platform {platform!r} is not served by this provider", file=sys.stderr)
    sys.exit(2)
if "--check" in sys.argv:
    print(json.dumps({"ok": True, "token_expires_at": EXPIRES}))
    sys.exit(0)
if len(sys.argv) > 1 and sys.argv[1] == "publish":
    if platform is None:
        print("error: publish needs --platform", file=sys.stderr)
        sys.exit(2)
    text = Path(arg("--text-file")).read_text()
    comment = Path(arg("--first-comment-file")).read_text() if arg("--first-comment-file") else None
    if "--dry-run" in sys.argv:
        print(json.dumps({"dry_run": True, "idempotency_key": arg("--idempotency-key"), "text": text,
                          "first_comment": comment, "ledger": str(HERE / "ledger.json"),
                          "note": "#word renders as a hashtag; @name stays plain text"}, indent=1))
        sys.exit(0)
    if "--confirmed" not in sys.argv:
        print("refused: publish needs --confirmed or --dry-run", file=sys.stderr)
        sys.exit(2)
    with open(HERE / "calls.log", "a") as f:
        f.write("publish " + arg("--idempotency-key") + "\n")
    print(json.dumps({"post_url": "https://www.linkedin.com/feed/update/urn:li:share:7000000000000000001/",
                      "replayed": False}))
    sys.exit(0)
print("usage: stub.py --check --platform <p> | publish --platform <p> ...", file=sys.stderr)
sys.exit(2)
