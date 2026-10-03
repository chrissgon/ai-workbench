#!/usr/bin/env python3
"""Decide whether a drafted reply to a comment may go out on its own, under the engagement policy.

Usage:
  python3 policy_gate.py decide --policy docs/marketing/engagement-policy.md --state docs/workbench/state.md \
      --log docs/marketing/engagement-log.jsonl --comment-file <comment.json> --category <category> \
      --language <PT|EN|...> [--reply-file <reply.txt>] [--sources-file <sources.json>] [--profile docs/brand/profile.md] \
      [--skills-dir skills] [--now <ISO-8601>]
  python3 policy_gate.py record --log docs/marketing/engagement-log.jsonl --entry-file <entry.json>
  python3 policy_gate.py policy-hash --policy docs/marketing/engagement-policy.md

decide  Reads the ```engagement-policy JSON block of the policy, the standing approval of the policy in the
        state file's "Approvals" table (a row whose scope is "standing" and whose Payload hash is
        "policy:<sha256 of the policy file>"), today's entries in the log, and the comment
        ({"comment_id", "post_id", "commenter", "text", "received_at"}; the names the agent runtime stores,
        "comment_urn" and "post_urn", are read too, in the comment and in the log). Prints
        {"decision": "auto" | "inbox", "reasons": [...], "idempotency_key", "earlier_idempotency_key", "counts",
        "reply_checks"}. idempotency_key is "reply-" and a hash of the whole comment identifier, which is opaque;
        earlier_idempotency_key is the form logs written before hold ("reply-" and the digits after the
        identifier's last comma): a logged reply under either key counts as the comment answered.
        "auto" only when every rule holds: an active, unexpired standing approval bound to this exact
        policy file; the category is in auto_reply_categories; the language is allowed; the daily limit and
        the per-person-per-post limit are not reached; the comment and the reply pass the sensitive-topics
        lock (sensitive_topics.py, the copy beside this script; else brand-profile's, looked up in each
        --skills-dir) and never_in_replies; the reply keeps reply_rules
        (sentences, emojis, hashtags, links, banned phrases). Without --reply-file the reply checks are
        skipped and the decision can only be "inbox".
        A question answered from sources (category question_answerable_from_sources) also needs
        --sources-file: a JSON list naming the project files the reply's facts come from; the first file path in
        each entry counts ("docs/brand/profile.md, section Proof" or "profile.md:30"; a bare name is looked up in
        docs/brand/ and docs/marketing/). Each must exist inside the project, and every number
        in the reply must appear in at least one of them; otherwise the reply goes to the inbox. The model's
        category alone never makes a factual answer go out.
record  Appends one JSON entry to the log (JSON Lines), adding "logged_at". The log is the day's count.
policy-hash  Prints the value to record in the standing approval's Payload hash: policy:<sha256>.

The comment and reply are external or drafted text: they are only matched, never executed.
Links are found by one pattern, the one of check_post.py (shared/scripts/check_post.py): an address with
http:// or https://, one that starts with www., a host with a path (short.example/x), or a bare host under a
common ending (name.com, name.dev).

Exit 0 on a decision (auto or inbox), 2 on bad input (a missing or empty reply file included). Standard library
only; no network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BLOCK = re.compile(r"```engagement-policy\s*\n(.*?)\n```", re.S)
# The one link pattern of the skills that check links: the same as LINK in shared/scripts/check_post.py.
LINK = re.compile(r"(?:https?://|www\.)\S+"
                  r"|(?<![\w@.-])[\w-]+(?:\.[\w-]+)*\.[a-z]{2,}/\S+"
                  r"|(?<![\w@.-])[\w-]+(?:\.[\w-]+)*\.(?:com|dev|io|org|net|app|br|ly|co|ai|me)\b(?!\.\w)", re.I)
HASHTAG = re.compile(r"(?<!\w)#\w+")
EMOJI = re.compile("[\U0001f000-\U0001faff\u2600-\u27bf\u2b00-\u2bff\ufe0f]")
SENTENCE_END = re.compile(r"[.!?](?:\s|$)")
REQUIRED = {"auto_reply_categories": list, "languages": list, "max_replies_per_day": int,
            "max_auto_replies_per_person_per_post": int, "reply_rules": dict, "never_in_replies": list}


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_policy(path: Path) -> dict:
    try:
        m = BLOCK.search(path.read_text(encoding="utf-8"))
    except OSError as e:
        fail(f"{path}: {e}")
    if not m:
        fail(f"{path} has no ```engagement-policy block")
    try:
        policy = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        fail(f"engagement-policy block is not valid JSON: {e}")
    for key, kind in REQUIRED.items():
        if not isinstance(policy.get(key), kind):
            fail(f"engagement-policy needs {key} ({kind.__name__})")
    return policy


def standing_row(state: Path, policy_hash: str) -> dict | None:
    """Find the Approvals row bound to this policy: | standing | what | policy:<hash> | approved | expires | status |."""
    try:
        lines = state.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 6 and cells[0].lower() == "standing" and cells[2] == f"policy:{policy_hash}":
            return {"what": cells[1], "approved": cells[3], "expires": cells[4], "status": cells[5].lower()}
    return None


def parse_time(value: str) -> datetime:
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        value += "T23:59:59+00:00"
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def read_log(path: Path) -> list:
    if not path.is_file():
        return []
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                fail(f"{path}:{n} is not JSON")
    return out


def field(record: dict, name: str, stored: str):
    """A field under its generic name, or under the name the agent runtime stores it by."""
    value = record.get(name)
    return value if value else record.get(stored)


def sensitive_script(skills_dirs):
    """The sensitive-topics lock: the copy beside this script, else brand-profile's in a skills folder."""
    beside = Path(__file__).resolve().parent / "sensitive_topics.py"
    if beside.is_file():
        return beside
    for d in skills_dirs or ["skills", str(Path(__file__).resolve().parents[2])]:
        p = Path(d) / "brand-profile/scripts/sensitive_topics.py"
        if p.is_file():
            return p
    return None


def sensitive(script, profile: Path, text: str):
    """Return (locked, topics) or None when the lock could not run."""
    if not script or not profile.is_file():
        return None
    try:
        r = subprocess.run([sys.executable, str(script), "--profile", str(profile)], input=text,
                           capture_output=True, text=True, timeout=60)
        out = json.loads(r.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    return r.returncode != 0, out.get("topics", {})


def reply_checks(reply: str, rules: dict, never: list) -> list:
    problems = []
    sentences = len(SENTENCE_END.findall(reply.strip() + ("" if reply.strip()[-1:] in ".!?" else ".")))
    if sentences > rules.get("max_sentences", 3):
        problems.append(f"{sentences} sentences, more than {rules.get('max_sentences', 3)}")
    emojis = len(EMOJI.findall(reply))
    if emojis > rules.get("max_emojis", 0):
        problems.append(f"{emojis} emoji(s)")
    tags = len(HASHTAG.findall(reply))
    if tags > rules.get("max_hashtags", 0):
        problems.append(f"{tags} hashtag(s)")
    if not rules.get("allow_links", False) and LINK.search(reply):
        problems.append("contains a link")
    low = reply.lower()
    for phrase in rules.get("banned", []) + never:
        if phrase.lower() in low:
            problems.append(f"contains {phrase!r}")
    return problems


NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
SOURCE_PATH = re.compile(r"[\w./-]*?[\w-]+\.(?:md|jsonl|json|txt)\b")


def source_checks(reply: str, sources_file) -> list:
    """A factual answer must cite project files that hold every number it states."""
    if not sources_file:
        return ["a factual answer needs its sources (--sources-file)"]
    try:
        sources = json.loads(Path(sources_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"sources unreadable: {e}"]
    if not isinstance(sources, list) or not sources:
        return ["a factual answer needs at least one source"]
    root = Path.cwd().resolve()
    texts, problems = [], []
    for src in sources:
        m = SOURCE_PATH.search(str(src))
        rel = m.group(0) if m else ""
        candidates = [rel] if "/" in rel else [f"docs/brand/{rel}", f"docs/marketing/{rel}"]
        path = next((c for c in ((root / c).resolve() for c in candidates if rel)
                     if root in c.parents and c.is_file()), None)
        if path is None:
            problems.append(f"source {str(src)[:80]!r} names no file in the project")
            continue
        texts.append(path.read_text(encoding="utf-8", errors="replace").replace(",", "."))
    corpus = "\n".join(texts)
    for n in NUMBER.findall(reply):
        if n.replace(",", ".") not in corpus:
            problems.append(f"number {n} is not in the cited sources")
    return problems


def reply_key(comment_id: str) -> str:
    """The idempotency key of the reply to a comment: a hash of the whole identifier, which is opaque."""
    return "reply-" + hashlib.sha256(comment_id.encode("utf-8")).hexdigest()[:32]


def earlier_reply_key(comment_id: str) -> str:
    """The key this script gave before (the digits after the identifier's last comma), which logs already hold:
    read when checking for a reply already sent, never given to a new reply."""
    digits = re.sub(r"[^0-9]", "", comment_id.rsplit(",", 1)[-1])
    return f"reply-{digits or hashlib.sha256(comment_id.encode()).hexdigest()[:16]}"


def decide(a) -> int:
    policy_path = Path(a.policy)
    policy = load_policy(policy_path)
    phash = sha256(policy_path)
    try:
        comment = json.loads(Path(a.comment_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        fail(f"--comment-file: {e}")
    if not isinstance(comment, dict):
        fail("--comment-file: expected a JSON object")
    comment_id, post_id = field(comment, "comment_id", "comment_urn"), field(comment, "post_id", "post_urn")
    if not comment_id:
        fail("comment needs comment_id")
    if not post_id:
        fail("comment needs post_id")
    for key in ("commenter", "text"):
        if not comment.get(key):
            fail(f"comment needs {key}")
    now = parse_time(a.now) if a.now else datetime.now(timezone.utc).astimezone()
    reasons = []

    row = standing_row(Path(a.state), phash)
    if row is None:
        reasons.append("no standing approval bound to this policy file (policy changed or never approved)")
    else:
        if row["status"] != "active":
            reasons.append(f"standing approval is {row['status']}")
        try:
            if parse_time(row["expires"]) <= now:
                reasons.append(f"standing approval expired on {row['expires']}")
        except ValueError:
            reasons.append(f"standing approval has no valid expiry ({row['expires']!r})")

    if a.category not in policy["auto_reply_categories"]:
        reasons.append(f"category {a.category!r} always goes to the user")
    if a.language.upper() not in [x.upper() for x in policy["languages"]]:
        reasons.append(f"language {a.language} is not allowed for automatic replies")

    log = read_log(Path(a.log))
    today = now.astimezone().date().isoformat()
    auto_today = [e for e in log if e.get("action") == "auto_replied"
                  and parse_time(e.get("logged_at", "1970-01-01")).astimezone().date().isoformat() == today]
    same = [e for e in log if e.get("action") == "auto_replied" and field(e, "post_id", "post_urn") == post_id
            and str(e.get("commenter", "")).casefold() == comment["commenter"].casefold()]
    if len(auto_today) >= policy["max_replies_per_day"]:
        reasons.append(f"daily limit reached ({len(auto_today)}/{policy['max_replies_per_day']})")
    if len(same) >= policy["max_auto_replies_per_person_per_post"]:
        reasons.append("this person already got an automatic reply on this post")
    key, earlier = reply_key(comment_id), earlier_reply_key(comment_id)
    if any(e.get("action") in ("auto_replied", "replied") and
           (field(e, "comment_id", "comment_urn") == comment_id or e.get("idempotency_key") in (key, earlier))
           for e in log):
        reasons.append("this comment was already answered")

    script = sensitive_script(a.skills_dir)
    profile = Path(a.profile)
    lock = sensitive(script, profile, comment["text"])
    if lock is None:
        reasons.append("sensitive-topics lock could not run on the comment")
    elif lock[0]:
        reasons.append(f"comment touches sensitive topics {sorted(lock[1])}")

    checks = None
    if a.reply_file:
        try:
            reply = Path(a.reply_file).read_text(encoding="utf-8").strip()
        except OSError as e:
            fail(f"--reply-file: {e}")
        if not reply:
            fail("--reply-file is empty")
        checks = reply_checks(reply, policy["reply_rules"], policy["never_in_replies"])
        reasons += [f"reply: {p}" for p in checks]
        rlock = sensitive(script, profile, reply)
        if rlock is None:
            reasons.append("sensitive-topics lock could not run on the reply")
        elif rlock[0]:
            reasons.append(f"reply touches sensitive topics {sorted(rlock[1])}")
        if a.category == "question_answerable_from_sources":
            reasons += source_checks(reply, a.sources_file)
    else:
        reasons.append("no reply drafted")

    out = {"decision": "inbox" if reasons else "auto", "reasons": reasons,
           "idempotency_key": key, "earlier_idempotency_key": earlier, "policy_hash": f"policy:{phash}",
           "counts": {"auto_today": len(auto_today), "max_per_day": policy["max_replies_per_day"]},
           "reply_checks": checks}
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


def record(a) -> int:
    try:
        entry = json.loads(Path(a.entry_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        fail(f"--entry-file: {e}")
    if entry.get("action") not in ("auto_replied", "replied", "to_inbox", "skipped", "failed"):
        fail("entry action must be auto_replied, replied, to_inbox, skipped or failed")
    entry["logged_at"] = datetime.now(timezone.utc).isoformat()
    log = Path(a.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps({"recorded": True, "log": str(log)}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="verb", required=True)
    d = sub.add_parser("decide")
    d.add_argument("--policy", required=True)
    d.add_argument("--state", default="docs/workbench/state.md")
    d.add_argument("--log", default="docs/marketing/engagement-log.jsonl")
    d.add_argument("--comment-file", required=True)
    d.add_argument("--category", required=True)
    d.add_argument("--language", required=True)
    d.add_argument("--reply-file")
    d.add_argument("--sources-file")
    d.add_argument("--profile", default="docs/brand/profile.md")
    d.add_argument("--skills-dir", action="append")
    d.add_argument("--now")
    r = sub.add_parser("record")
    r.add_argument("--log", default="docs/marketing/engagement-log.jsonl")
    r.add_argument("--entry-file", required=True)
    h = sub.add_parser("policy-hash")
    h.add_argument("--policy", required=True)
    a = p.parse_args(argv)
    if a.verb == "policy-hash":
        load_policy(Path(a.policy))
        print(json.dumps({"payload_hash": f"policy:{sha256(Path(a.policy))}"}))
        return 0
    return decide(a) if a.verb == "decide" else record(a)


if __name__ == "__main__":
    sys.exit(main())
