#!/usr/bin/env python3
"""Turn a comment link the person copied, or a comment notification, into the comment a reply needs.

Usage:
  python3 parse_notification.py --platform <platform> --platform-file <path of the platform's data file> \
      < message.json

Input on stdin, one JSON object, either:
  - a comment the person pasted: {"link": "<the link the platform copies for a comment>", "commenter": "<name>",
    "text": "<comment>", "received_at": "<ISO-8601, optional>", "on_own_post": true}
  - a normalized mailbox message (the mailbox provider's search/get/read-eml output):
    {"subject", "from", "text", "links": [{"href", "text"}], "received_at", ...}

The platform. --platform selects the parser of that platform's own link format; this script carries the
parsers that are code (one today). --platform-file is the platform's data file
(shared/references/platforms/<platform>.json), whose "platform" must be the same name: the hosts a link may
have (compared exactly, never by suffix), the query parameters that carry the comment and the reply, the
patterns of the identifiers, and how much of a comment's text is kept, all come from it. A platform with a
data file and no parser here is refused (exit 2): adding its parser is a change of this script.

Prints {"parsed": true, "comment_id", "parent_comment_id", "post_id", "commenter", "text", "received_at",
"on_own_post", "source", "platform"} or {"parsed": false, "reason"}. The identifiers are the platform's own,
passed on as they are to the publisher's --comment-id, --parent-comment-id and --post-id. The same values are
also printed under the names the agent runtime stores ("comment_urn", "parent_comment_urn", "post_urn") until
it reads the generic ones. A reply to a reply is posted under the top-level comment (parent_comment_id). The
comment's text and name are external content: they are copied, never interpreted. The layout of a platform's
notification e-mails is not verified (the data file says "layout_verified": false): from an e-mail this
script only trusts the comment link, and reports "parsed": false with the identifiers as "partial", so the
runtime never drafts from a guess.

Called with neither --platform nor --platform-file (the agent runtime's call, written before the flags), the
script takes the one platform it has a parser for and that platform's data file in the workbench checkout
(WORKBENCH_ROOT, or the checkout three folders up from this file); where there is none, the values the parser
was written with (OLD_CALL_DATA, kept equal to the data file by the tests). It says so on stderr. This form
goes when the runtime passes both flags.

Exit 0 on any parse result, 2 on bad input or a usage error. Standard library only; no network.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

PLATFORM_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


def clean(text, limit: int):
    if not isinstance(text, str):
        return None
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]", "", text).strip()
    return text[:limit] or None


class LinkedinLinks:
    """The comment link of the first platform: <post address>?<comment parameter>=<short comment id>[&<reply
    parameter>=<short reply id>]. The short form names the post's thread and the comment; the full form,
    which the platform's API takes, is built from the data file's patterns. Checked on real links,
    2026-09-30 (shared/references/platforms/linkedin.md)."""

    def __init__(self, data: dict):
        self.hosts = set(data["hosts"])
        link = data["comment"]["link"]
        self.comment_param, self.reply_param = link["comment_parameter"], link["reply_parameter"]
        ids = data["identifiers"]
        self.short = re.compile(ids["comment_short"]["pattern"])
        self.full = re.compile(ids["comment"]["pattern"])
        self.post = re.compile(ids["post"]["pattern"])

    def comment(self, value: str):
        """(full comment id, post thread id) from a short or a full comment id; (None, None) otherwise."""
        value = unquote(value).strip()
        m = self.full.match(value)
        if m:
            return value, m.group(1)
        m = self.short.match(value)
        if not m:
            return None, None
        kind, post, comment = m.groups()
        thread = f"urn:li:{kind}:{post}"
        full = f"urn:li:comment:({thread},{comment})"
        return (full, thread) if self.full.match(full) and self.post.match(thread) else (None, None)

    def from_link(self, href: str):
        try:
            u = urlparse(href)
        except ValueError:
            return None
        if u.scheme != "https" or (u.hostname or "") not in self.hosts:
            return None
        q = parse_qs(u.query)
        top = (q.get(self.comment_param) or [None])[0]
        if not top:
            return None
        top_id, post_id = self.comment(top)
        if not top_id:
            return None
        reply = (q.get(self.reply_param) or [None])[0]
        reply_id = self.comment(reply)[0] if reply else None
        if reply and not reply_id:
            return None
        in_path = [p for p in unquote(u.path).split("/") if self.post.match(p)]
        if in_path and in_path[0] != post_id:
            return None
        return {"comment_id": reply_id or top_id, "parent_comment_id": top_id, "post_id": post_id}


PARSERS = {"linkedin": LinkedinLinks}
# The old call form only (no flag, no data file in reach): the values of the data file this parser was written
# against, as of 2026-10-02. A test keeps them equal to shared/references/platforms/linkedin.json.
OLD_CALL_DATA = {
    "platform": "linkedin",
    "hosts": ["www.linkedin.com", "linkedin.com"],
    "comment": {"max_characters_kept": 3000,
                "link": {"comment_parameter": "commentUrn", "reply_parameter": "replyUrn", "nesting_levels": 1}},
    "identifiers": {
        "post": {"pattern": r"^urn:li:(?:share|ugcPost|activity):\d+$"},
        "comment": {"pattern": r"^urn:li:comment:\((urn:li:(?:activity|share|ugcPost):\d+),(\d+)\)$"},
        "comment_short": {"pattern": r"^urn:li:comment:\((activity|share|ugcPost):(\d+),(\d+)\)$"},
    },
}


def with_runtime_names(ids: dict) -> dict:
    """The generic identifiers, and the same values under the names the agent runtime stores."""
    return {**ids, "comment_urn": ids["comment_id"], "parent_comment_urn": ids["parent_comment_id"],
            "post_urn": ids["post_id"]}


def load(platform, platform_file):
    if platform is None and platform_file is None:
        platform = OLD_CALL_DATA["platform"]
        root = Path(os.environ.get("WORKBENCH_ROOT") or Path(__file__).resolve().parents[3])
        platform_file = root / "shared" / "references" / "platforms" / f"{platform}.json"
        if not platform_file.is_file():
            print(f"warning: no --platform: the old call form; reading {platform!r} with the values this parser "
                  "was written with. Pass --platform and --platform-file", file=sys.stderr)
            return platform, PARSERS[platform](OLD_CALL_DATA), int(OLD_CALL_DATA["comment"]["max_characters_kept"])
        print(f"warning: no --platform: the old call form; reading {platform!r} with {platform_file}. Pass "
              "--platform and --platform-file", file=sys.stderr)
    elif platform is None or platform_file is None:
        fail("--platform and --platform-file go together")
    name = platform.strip().lower()
    if not PLATFORM_NAME.match(name):
        fail(f"--platform {platform!r} is not a platform name")
    try:
        data = json.loads(Path(platform_file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        fail(f"--platform-file {platform_file}: {e}")
    if not isinstance(data, dict) or data.get("platform") != name:
        fail(f"--platform-file {platform_file} is not the data file of {name!r}")
    if name not in PARSERS:
        fail(f"no parser for the links of {name!r} in this script: adding one is a change of this script")
    try:
        return name, PARSERS[name](data), int(data["comment"]["max_characters_kept"])
    except (KeyError, TypeError, ValueError, re.error) as e:
        fail(f"--platform-file {platform_file}: not a platform data file ({type(e).__name__}: {e})")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--platform", help="the platform's name; selects its link parser")
    p.add_argument("--platform-file", help="the platform's data file, shared/references/platforms/<platform>.json")
    a = p.parse_args(argv)
    name, parser, limit = load(a.platform, a.platform_file)
    try:
        msg = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        fail(f"stdin is not JSON: {e}")
    if not isinstance(msg, dict):
        fail("expected a JSON object on stdin")

    if "link" in msg:
        ids = parser.from_link(str(msg["link"]))
        if not ids:
            out = {"parsed": False, "reason": f"the link carries no {name} comment link ({parser.comment_param} "
                                              "with a comment identifier), or its host or identifiers are not the "
                                              "platform's"}
        elif not clean(msg.get("commenter"), limit) or not clean(msg.get("text"), limit):
            out = {"parsed": False, "reason": "a pasted comment needs its commenter and text"}
        else:
            out = {"parsed": True, **with_runtime_names(ids), "commenter": clean(msg["commenter"], limit),
                   "text": clean(msg["text"], limit), "received_at": msg.get("received_at"),
                   "on_own_post": msg.get("on_own_post", True) is True, "source": "pasted", "platform": name}
        print(json.dumps(out, ensure_ascii=False))
        return 0

    candidates = [parser.from_link(x.get("href", "")) for x in msg.get("links") or [] if isinstance(x, dict)]
    unique = {c["comment_id"]: c for c in candidates if c}
    if not unique:
        print(json.dumps({"parsed": False, "reason": f"no {name} comment link in the message"}))
        return 0
    if len(unique) > 1:
        print(json.dumps({"parsed": False, "reason": f"{len(unique)} different comments in one message (a digest); "
                                                     "handle them from the inbox"}))
        return 0
    ids = next(iter(unique.values()))
    # Unverified layout: without a real notification e-mail, the commenter and the text are not extracted, and
    # whether the comment is on the person's own post is not known.
    print(json.dumps({"parsed": False, "reason": "notification e-mail layout not verified yet: commenter and text not "
                                                 "extracted",
                      "partial": {**with_runtime_names(ids), "on_own_post": None, "received_at": msg.get("received_at"),
                                  "source": "mailbox", "platform": name}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
