#!/usr/bin/env python3
"""Turn a comment notification, or a comment link the person copied, into the comment a reply needs.

Usage:
  python3 parse_notification.py < message.json

Input on stdin, one JSON object, either:
  - a normalized mailbox message (the mailbox provider's search/get/read-eml output):
    {"subject", "from", "text", "links": [{"href", "text"}], "received_at", ...}
  - a comment the person pasted: {"link": "<LinkedIn comment link>", "commenter": "<name>", "text": "<comment>",
    "received_at": "<ISO-8601, optional>", "on_own_post": true}

A LinkedIn comment link (Copy link to comment) looks like, as checked on real links on 2026-09-30:
  https://www.linkedin.com/feed/update/urn:li:activity:<post>?commentUrn=urn%3Ali%3Acomment%3A%28activity%3A<post>%2C<comment>%29&...
Its commentUrn uses a short form, urn:li:comment:(activity:<post>,<comment>); the Comments API documents the
full form, urn:li:comment:(urn:li:activity:<post>,<comment>), which is what this script prints. A replyUrn
parameter, when present, is the reply and commentUrn its top-level comment: LinkedIn nests one level, so a
reply to it is posted under the top-level comment (parent_comment_urn).

Prints {"parsed": true, "comment_urn", "parent_comment_urn", "post_urn", "commenter", "text", "received_at",
"on_own_post", "source"} or {"parsed": false, "reason"}. The comment's text and name are external content:
they are copied, never interpreted. The layout of LinkedIn's notification e-mails has not been verified on a
real e-mail yet (backlog PB6): from an e-mail this script only trusts the comment link, and reports
"parsed": false when it cannot find the commenter or the text, so the runtime never drafts from a guess.
Exit 0 on any parse result, 2 on bad input. Standard library only; no network.
"""
import json
import re
import sys
from urllib.parse import parse_qs, unquote, urlparse

NUM = r"\d{6,25}"
SHORT = re.compile(rf"^urn:li:comment:\((?:urn:li:)?(activity|share|ugcPost):({NUM}),({NUM})\)$")
POST = re.compile(rf"urn:li:(activity|share|ugcPost):({NUM})")
OWN = re.compile(r"(commented on your (post|article)|comentou (no|na|em) (seu|sua) (post|publica\w+|artigo))", re.I)
MAX_TEXT = 3000


def full_comment_urn(value: str):
    m = SHORT.match(unquote(value).strip())
    if not m:
        return None, None
    kind, post, comment = m.groups()
    return f"urn:li:comment:(urn:li:{kind}:{post},{comment})", f"urn:li:{kind}:{post}"


def from_link(href: str) -> dict | None:
    try:
        u = urlparse(href)
    except ValueError:
        return None
    if not (u.hostname or "").endswith("linkedin.com"):
        return None
    q = parse_qs(u.query)
    top = (q.get("commentUrn") or [None])[0]
    if not top:
        return None
    top_urn, post_urn = full_comment_urn(top)
    if not top_urn:
        return None
    reply = (q.get("replyUrn") or [None])[0]
    reply_urn = full_comment_urn(reply)[0] if reply else None
    path_post = POST.search(unquote(u.path))
    if path_post and path_post.group(0) != post_urn:
        return None
    return {"comment_urn": reply_urn or top_urn, "parent_comment_urn": top_urn, "post_urn": post_urn}


def clean(text) -> str | None:
    if not isinstance(text, str):
        return None
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]", "", text).strip()
    return text[:MAX_TEXT] or None


def main() -> int:
    try:
        msg = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(f"error: stdin is not JSON: {e}", file=sys.stderr)
        return 2
    if not isinstance(msg, dict):
        print("error: expected a JSON object", file=sys.stderr)
        return 2

    if "link" in msg:
        ids = from_link(str(msg["link"]))
        if not ids:
            out = {"parsed": False, "reason": "the link carries no LinkedIn commentUrn"}
        elif not clean(msg.get("commenter")) or not clean(msg.get("text")):
            out = {"parsed": False, "reason": "a pasted comment needs its commenter and text"}
        else:
            out = {"parsed": True, **ids, "commenter": clean(msg["commenter"]), "text": clean(msg["text"]),
                   "received_at": msg.get("received_at"), "on_own_post": msg.get("on_own_post", True) is True,
                   "source": "pasted"}
        print(json.dumps(out, ensure_ascii=False))
        return 0

    candidates = [from_link(l.get("href", "")) for l in msg.get("links") or [] if isinstance(l, dict)]
    candidates = [c for c in candidates if c]
    unique = {c["comment_urn"]: c for c in candidates}
    if not unique:
        print(json.dumps({"parsed": False, "reason": "no LinkedIn comment link in the message"}))
        return 0
    if len(unique) > 1:
        print(json.dumps({"parsed": False, "reason": f"{len(unique)} different comments in one message (a digest); handle them from the inbox"}))
        return 0
    ids = next(iter(unique.values()))
    subject = clean(msg.get("subject")) or ""
    own = bool(OWN.search(subject)) if subject else None
    # Unverified layout: without a real notification e-mail, the commenter and the text are not extracted.
    print(json.dumps({"parsed": False, "reason": "notification e-mail layout not verified yet: commenter and text not extracted",
                      "partial": {**ids, "on_own_post": own, "received_at": msg.get("received_at"), "source": "mailbox"}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
