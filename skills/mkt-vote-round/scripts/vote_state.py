#!/usr/bin/env python3
"""Read an audience vote's data files and say what the weekly vote step has to do.

Usage:
  python3 vote_state.py --pick data/pick.json --queue data/pick-queue.json --posts data/posts.json \
      --calendar docs/marketing/calendar.md [--pillars "Build to serve|AI built in public|Tech in conversation"] \
      [--pillar-alias "AI built in public=<the calendar's name for it>"]... [--check "<topic>"]... [--today YYYY-MM-DD]

The data files are the profile repository's vote files: pick.json (the open round and the history of closed
rounds, newest first), pick-queue.json (the next rounds, each {pillar, options}) and posts.json (posts shown on
the profile). A closed round is {round, pillar, options: {A, B, C}, counts: {A, B, C}, winner: A|B|C|null,
post_url: <url>|null}.

Prints JSON on stdout:
  pending       true when a closed round has no post_url yet
  round         the newest closed round without a post_url (with winner_topic, the winner's text, or null
                when nobody picked), or null
  older_without_post  older closed rounds that also have no post_url (their slot passed; they are not redone)
  open_round    the round open now, or null
  rotation      {pillars, source, sequence, last_pillar, next_pillar}: the pillar of the round to add after the
                queued ones. The order is --pillars when given (the strategy's order, spelled as the vote data
                spells the pillars); without it, it is read from the data only when the data already went round
                the whole cycle once, otherwise next_pillar is null. The sequence is history oldest first, then the
                open round, then the queue; the next pillar is the one after its last entry.
  slot          the first free calendar row dated after --today whose pillar is the round's pillar (or its
                --pillar-alias): {row, when, pillar, language, topic, status}, or null. A row whose status is
                drafted, scheduled, published, missed or failed already carries a post: it is passed over and
                named in warnings, so the vote post goes to the pillar's next free row.
  used_topics   every topic already used, each {topic, normalized, source}: the calendar's topic column, the
                queue, the history, the open round and the titles in posts.json
  checks        with --check: for each topic, whether it is used, and the used topics it equals or resembles
  warnings      what the data does not say

Calendar tables are found by shape, in any language: a Markdown table whose first header cell is "#"; its
columns are, in order, number, when, pillar, language, topic (the mkt-content-plan template).
Normalisation for comparing topics: accents removed, lower case, apostrophes dropped, every other character
that is not a letter or a digit turned into a space, spaces collapsed. Two topics resemble each other when
they are equal after normalisation, or when at least 3 words of 3 or more letters (plural endings dropped,
a few English filler words ignored) are shared and cover at least 80% of the shorter topic's words.
Resemblance catches the same wording; the same subject in other words or another language is the reader's check.

Exit 0 ok, 2 on a usage error or a malformed file. Standard library only; no network.
"""
import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

LETTERS = ("A", "B", "C")
ROUND_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SIMILAR_SHARE = 0.8
SIMILAR_MIN_WORDS = 3
STOPWORDS = {"the", "and", "with", "for", "what", "how", "why", "from", "that", "this", "you", "your", "are", "was"}


class Malformed(Exception):
    pass


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


# ---------- topics ----------

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"['‘’`´]", "", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def stem(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def words(text: str) -> set:
    return {stem(w) for w in normalize(text).split() if len(w) >= 3 and w not in STOPWORDS}


def resembles(a: str, b: str) -> bool:
    """True when a and b are the same topic after normalisation, or share most of their words."""
    if normalize(a) == normalize(b):
        return True
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return False
    shared = len(wa & wb)
    return shared >= SIMILAR_MIN_WORDS and shared / min(len(wa), len(wb)) >= SIMILAR_SHARE


def matches(topic: str, used: list) -> list:
    return [u for u in used if resembles(topic, u["topic"])]


# ---------- files ----------

def load_json(path: str, what: str):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        raise Malformed(f"{what}: {e}")
    except json.JSONDecodeError as e:
        raise Malformed(f"{what} is not valid JSON: {e}")


def check_options(obj, where: str) -> dict:
    if not isinstance(obj, dict) or set(obj) != set(LETTERS):
        raise Malformed(f"{where}: options must have exactly the keys A, B and C")
    for k in LETTERS:
        if not isinstance(obj[k], str) or not obj[k].strip():
            raise Malformed(f"{where}: option {k} must be non-empty text")
    return obj


def check_text(obj: dict, key: str, where: str) -> str:
    if not isinstance(obj.get(key), str) or not obj[key].strip():
        raise Malformed(f"{where}: '{key}' must be non-empty text")
    return obj[key]


def check_pick(v) -> dict:
    if not isinstance(v, dict):
        raise Malformed("pick.json must be an object")
    if not isinstance(v.get("open"), bool):
        raise Malformed("pick.json: 'open' must be true or false")
    if not isinstance(v.get("history"), list):
        raise Malformed("pick.json: 'history' must be a list")
    if not isinstance(v.get("picks", {}), dict):
        raise Malformed("pick.json: 'picks' must be an object")
    if v["open"]:
        for key in ("round", "closes", "pillar"):
            check_text(v, key, "pick.json")
        if not ROUND_RE.match(v["round"]):
            raise Malformed("pick.json: 'round' must be a date, YYYY-MM-DD")
        check_options(v.get("options"), "pick.json")
    for i, h in enumerate(v["history"]):
        where = f"pick.json history[{i}]"
        if not isinstance(h, dict):
            raise Malformed(f"{where} must be an object")
        check_text(h, "round", where)
        if not ROUND_RE.match(h["round"]):
            raise Malformed(f"{where}: 'round' must be a date, YYYY-MM-DD")
        check_text(h, "pillar", where)
        check_options(h.get("options"), where)
        counts = h.get("counts")
        if not isinstance(counts, dict) or set(counts) != set(LETTERS) or \
                not all(isinstance(counts[k], int) and not isinstance(counts[k], bool) and counts[k] >= 0 for k in LETTERS):
            raise Malformed(f"{where}: counts must be whole numbers for A, B and C")
        if h.get("winner") not in (*LETTERS, None):
            raise Malformed(f"{where}: winner must be A, B, C or null")
        if h.get("post_url") is not None and not isinstance(h["post_url"], str):
            raise Malformed(f"{where}: post_url must be text or null")
    rounds = [h["round"] for h in v["history"]]
    if len(set(rounds)) != len(rounds):
        raise Malformed("pick.json: a round appears twice in the history")
    return v


def check_queue(q) -> list:
    if not isinstance(q, list):
        raise Malformed("pick-queue.json must be a list")
    for i, item in enumerate(q):
        if not isinstance(item, dict):
            raise Malformed(f"pick-queue.json[{i}] must be an object")
        check_text(item, "pillar", f"pick-queue.json[{i}]")
        check_options(item.get("options"), f"pick-queue.json[{i}]")
    return q


def check_posts(p) -> list:
    if not isinstance(p, list):
        raise Malformed("posts.json must be a list")
    for i, post in enumerate(p):
        if not isinstance(post, dict):
            raise Malformed(f"posts.json[{i}] must be an object")
        for key in ("date", "title", "url"):
            check_text(post, key, f"posts.json[{i}]")
    return p


def load_all(pick: str, queue: str, posts: str):
    return (check_pick(load_json(pick, "pick.json")), check_queue(load_json(queue, "pick-queue.json")),
            check_posts(load_json(posts, "posts.json")))


def cells(line: str) -> list:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def calendar_rows(path: str) -> list:
    """Rows of every calendar table (first header cell '#'): {row, when, pillar, language, topic, status}."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as e:
        raise Malformed(f"calendar: {e}")
    rows, header = [], None
    for line in lines:
        if not line.strip().startswith("|"):
            header = None
            continue
        c = cells(line)
        if header is None:
            header = c if c and c[0] == "#" and len(c) >= 5 else []
            continue
        if not header or all(re.fullmatch(r":?-+:?", x) for x in c if x):
            continue
        c += [""] * (len(header) - len(c))
        rows.append({"row": c[0], "when": c[1], "pillar": c[2], "language": c[3], "topic": c[4],
                     "status": c[-1] if len(header) >= 6 else ""})
    return rows


def used_topics(v: dict, queue: list, posts: list, rows: list) -> list:
    used = []

    def add(topic, source):
        if isinstance(topic, str) and topic.strip() and topic.strip() not in ("-", "—"):
            used.append({"topic": topic.strip(), "normalized": normalize(topic), "source": source})

    for r in rows:
        add(r["topic"], f"calendar row {r['row']} ({r['when'][:10]})")
    for i, item in enumerate(queue):
        for k in LETTERS:
            add(item["options"][k], f"pick-queue.json[{i}] option {k}")
    for h in v["history"]:
        for k in LETTERS:
            add(h["options"][k], f"history round {h['round']} option {k}")
    if v["open"]:
        for k in LETTERS:
            add(v["options"][k], f"open round {v['round']} option {k}")
    for p in posts:
        add(p["title"], f"posts.json {p['date']}")
    return used


# ---------- rotation ----------

def pillar_sequence(v: dict, queue: list) -> list:
    seq = [h["pillar"] for h in sorted(v["history"], key=lambda h: h["round"])]
    if v["open"]:
        seq.append(v["pillar"])
    return seq + [q["pillar"] for q in queue]


def rotation(v: dict, queue: list, pillars: list) -> dict:
    seq = pillar_sequence(v, queue)
    out = {"pillars": pillars or None, "source": "--pillars" if pillars else None, "sequence": seq,
           "last_pillar": seq[-1] if seq else None, "next_pillar": None, "warnings": []}
    order = pillars
    if not order:
        cycle = []
        for p in seq:
            if normalize(p) in [normalize(x) for x in cycle]:
                break
            cycle.append(p)
        if len(seq) > len(cycle):
            order, out["pillars"], out["source"] = cycle, cycle, "data"
        else:
            out["warnings"].append("the data has not gone round the pillars once; pass --pillars in the strategy's order")
            return out
    names = [normalize(p) for p in order]
    for a, b in zip(seq, seq[1:]):
        if normalize(a) in names and normalize(b) in names and \
                names[(names.index(normalize(a)) + 1) % len(names)] != normalize(b):
            out["warnings"].append(f"the data goes from '{a}' to '{b}', which is not the rotation's order")
    if not seq:
        out["next_pillar"] = order[0]
        return out
    if normalize(seq[-1]) not in names:
        raise Malformed(f"the last queued pillar '{seq[-1]}' is not one of the pillars: {', '.join(order)}")
    out["next_pillar"] = order[(names.index(normalize(seq[-1])) + 1) % len(order)]
    return out


# ---------- slot ----------

TAKEN = {"drafted", "scheduled", "published", "missed", "failed"}


def find_slot(rows: list, pillar: str, aliases: dict, today: date, skipped: list):
    """The first free row of the pillar after today; rows that already carry a post (status drafted or later)
    are appended to skipped and passed over."""
    names = {normalize(pillar)} | {normalize(a) for a in aliases.get(normalize(pillar), [])}
    for r in rows:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", r["when"])
        if not m or date.fromisoformat(m.group(1)) <= today:
            continue
        cell = normalize(r["pillar"])
        if any(cell == n or cell.startswith(n + " ") for n in names):
            if (normalize(r["status"]).split() or [""])[0] in TAKEN:
                skipped.append(r)
                continue
            return r
    return None


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pick", required=True, help="the vote's pick.json")
    p.add_argument("--queue", required=True, help="the vote's pick-queue.json")
    p.add_argument("--posts", required=True, help="the profile's posts.json")
    p.add_argument("--calendar", required=True, help="docs/marketing/calendar.md")
    p.add_argument("--pillars", help="the pillars in the strategy's order, spelled as in the vote data, separated by |")
    p.add_argument("--pillar-alias", action="append", default=[],
                   help="<vote pillar>=<calendar pillar>, when the calendar names a pillar differently (repeatable)")
    p.add_argument("--check", action="append", default=[], help="a candidate topic to check against the used ones (repeatable)")
    p.add_argument("--today", help="today's date, YYYY-MM-DD (default: the system date)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    a = parse_args(argv)
    try:
        today = date.fromisoformat(a.today) if a.today else date.today()
    except ValueError as e:
        fail(f"bad --today: {e}")
    pillars = [x.strip() for x in (a.pillars or "").split("|") if x.strip()]
    aliases = {}
    for item in a.pillar_alias:
        name, sep, alias = item.partition("=")
        if not sep or not name.strip() or not alias.strip():
            fail(f"--pillar-alias takes <vote pillar>=<calendar pillar>, not {item!r}")
        aliases.setdefault(normalize(name), []).append(alias.strip())
    try:
        v, queue, posts = load_all(a.pick, a.queue, a.posts)
        rows = calendar_rows(a.calendar)
        rot = rotation(v, queue, pillars)
    except Malformed as e:
        fail(str(e))
    warnings = rot.pop("warnings")
    if not rows:
        warnings.append("no calendar table found (a Markdown table whose first header cell is '#')")
    open_ = sorted((h for h in v["history"] if not h.get("post_url")), key=lambda h: h["round"], reverse=True)
    rnd = None
    if open_:
        h = open_[0]
        rnd = {**h, "winner_topic": h["options"][h["winner"]] if h.get("winner") else None}
    used = used_topics(v, queue, posts, rows)
    skipped = []
    slot = find_slot(rows, rnd["pillar"], aliases, today, skipped) if rnd else None
    if skipped:
        warnings.append("rows of the pillar passed over because they already carry a post: "
                        + ", ".join(f"{r['row']} ({r['when'][:10]}, {r['status']})" for r in skipped))
    if rnd and slot is None:
        warnings.append(f"no free calendar row after {today} carries the pillar '{rnd['pillar']}': add a row of that"
                        " pillar to the calendar (pass --pillar-alias when the calendar names it differently)")
    out = {
        "today": today.isoformat(),
        "pending": rnd is not None,
        "round": rnd,
        "older_without_post": [h["round"] for h in open_[1:]],
        "open_round": {k: v[k] for k in ("round", "closes", "pillar", "options")} if v["open"] else None,
        "rotation": rot,
        "slot": slot,
        "used_topics": used,
        "checks": [{"topic": t, "used": bool(matches(t, used)), "matches": matches(t, used)} for t in a.check],
        "warnings": warnings,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
