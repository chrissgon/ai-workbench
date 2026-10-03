#!/usr/bin/env python3
"""Compute the vote data files after a post is published or a round is queued. Never edits the inputs.

Usage:
  python3 vote_update.py --pick data/pick.json --queue data/pick-queue.json --posts data/posts.json \
      --record-post --round 2026-10-05 --post-url <the address the publisher printed> \
      --platform <platform> --platform-file <path of the platform's data file> \
      --date 2026-10-14 --lang EN --title "<post title>" [--image assets/posts/<slug>.png] --out <dir>

  python3 vote_update.py --pick ... --queue ... --posts ... \
      --queue-round --pillar "<pillar>" --option "A=<topic>" --option "B=<topic>" --option "C=<topic>" \
      --calendar docs/marketing/calendar.md [--pillars "<p1>|<p2>|<p3>"] --out <dir>

--record-post sets post_url on that closed round in pick.json and adds {date, lang, title, url, image} at the
end of posts.json (nothing is added twice). It refuses a URL that is not the address of a post on the platform, a
round that is not in the history, and a round that already has another post_url. The shape of a post's address
(scheme, hosts compared exactly, path pattern, whether a query or a fragment may follow) is read from the
platform's data file, --platform-file (shared/references/platforms/<platform>.json), whose "platform" must be
--platform; this script holds no platform's address. Called with neither flag (a caller written before them),
it checks only that the URL is https with a host and no query, fragment, user or port, and says so on stderr.
--queue-round adds {pillar, options} at the end of pick-queue.json. It refuses a missing or empty option, two
options that are the same topic, an option longer than 80 characters (the profile's pick card draws it on one
line), and any option already used: in the calendar's topic column, the queue, the history, the open round or
posts.json, compared with vote_state.py's normalisation and resemblance test. With --pillars it also refuses a
pillar that is not the next one in the rotation.

The files are written to <out>/data/<name>, only when they change, exactly as the profile repository writes them
(JSON with indent 1, characters not escaped, a final newline); every other field is kept as it was.
Prints JSON on stdout: {"mode", "changed": [{"path": "data/<name>", "file", "sha256"}], "warnings"}.
Exit 0 ok (nothing to change is ok), 1 the change is refused, 2 a usage error or a malformed file.
Standard library only; no network.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vote_state  # noqa: E402  (the same folder)

MAX_OPTION = 80
IMAGE_RE = re.compile(r"^assets/posts/[a-z0-9][a-z0-9-]*\.(png|webp|jpg|jpeg)$")
LANG_RE = re.compile(r"^[A-Z]{2}(/[A-Z]{2})*$")
PLATFORM_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class Refused(Exception):
    pass


def fail(message: str, code: int = 2) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def dump(obj) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


def post_address(platform, platform_file):
    """The shape of a post's address on the platform, from its data file; None for the old call form."""
    if platform is None and platform_file is None:
        print("warning: no --platform: only the generic shape of a post address is checked; pass --platform and "
              "--platform-file", file=sys.stderr)
        return None
    if platform is None or platform_file is None:
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
    try:
        url = data["post"]["url"]
        return {"platform": name, "scheme": url["scheme"], "hosts": list(url["hosts"]),
                "path": re.compile(url["path_pattern"]), "query": bool(url["allows_query"]),
                "fragment": bool(url["allows_fragment"]), "template": url.get("template", "")}
    except (KeyError, TypeError, re.error) as e:
        fail(f"--platform-file {platform_file}: not a platform data file ({type(e).__name__}: {e})")


def is_post_address(url: str, shape) -> bool:
    try:
        u = urlsplit(url)
        port = u.port
    except ValueError:
        return False
    if u.username is not None or u.password is not None or port is not None or not u.hostname:
        return False
    if shape is None:
        return u.scheme == "https" and not u.query and not u.fragment
    return (u.scheme == shape["scheme"] and u.hostname in shape["hosts"] and (shape["query"] or not u.query)
            and (shape["fragment"] or not u.fragment) and bool(shape["path"].match(u.path)))


def record_post(a, v: dict, posts: list):
    shape = post_address(a.platform, a.platform_file)
    if not is_post_address(a.post_url, shape):
        where = f"a post address of {shape['platform']} ({shape['template']})" if shape else "an https address"
        raise Refused(f"{a.post_url!r} is not {where}")
    try:
        date.fromisoformat(a.date)
    except (TypeError, ValueError):
        raise Refused(f"--date {a.date!r} is not a date, YYYY-MM-DD")
    if not a.lang or not LANG_RE.match(a.lang):
        raise Refused(f"--lang {a.lang!r} must be upper-case language codes such as EN, PT or EN/PT")
    if not a.title or not a.title.strip() or "\n" in a.title or len(a.title) > 200:
        raise Refused("--title must be one line of text, at most 200 characters")
    if a.image and not IMAGE_RE.match(a.image):
        raise Refused(f"--image {a.image!r} must be assets/posts/<lowercase-slug>.png|webp|jpg")
    found = next((h for h in v["history"] if h["round"] == a.round), None)
    if found is None:
        raise Refused(f"round {a.round!r} is not in pick.json's history")
    if found.get("post_url") and found["post_url"] != a.post_url:
        raise Refused(f"round {a.round} already has the post {found['post_url']}")
    found["post_url"] = a.post_url
    if not any(p.get("url") == a.post_url for p in posts):
        posts.append({"date": a.date, "lang": a.lang, "title": a.title.strip(), "url": a.post_url, "image": a.image or None})
    return {"pick.json": v, "posts.json": posts}


def queue_round(a, v: dict, queue: list, posts: list):
    options = {}
    for item in a.option:
        letter, sep, text = item.partition("=")
        letter = letter.strip().upper()
        if not sep or letter not in vote_state.LETTERS:
            raise Refused(f"--option takes A=<topic>, B=<topic> or C=<topic>, not {item!r}")
        if letter in options:
            raise Refused(f"option {letter} is given twice")
        options[letter] = text.strip()
    missing = [k for k in vote_state.LETTERS if not options.get(k)]
    if missing:
        raise Refused(f"missing or empty option(s): {', '.join(missing)}")
    if not a.pillar or not a.pillar.strip():
        raise Refused("--pillar is empty")
    for k in vote_state.LETTERS:
        t = options[k]
        if "\n" in t or len(t) > MAX_OPTION:
            raise Refused(f"option {k} must be one line of at most {MAX_OPTION} characters")
    for i, x in enumerate(vote_state.LETTERS):
        for y in vote_state.LETTERS[i + 1:]:
            if vote_state.resembles(options[x], options[y]):
                raise Refused(f"options {x} and {y} are the same topic")
    rows = vote_state.calendar_rows(a.calendar)
    used = vote_state.used_topics(v, queue, posts, rows)
    hits = {k: vote_state.matches(options[k], used) for k in vote_state.LETTERS}
    hits = {k: m for k, m in hits.items() if m}
    if hits:
        raise Refused("already used: " + "; ".join(
            f"option {k} ({options[k]!r}) is {', '.join(repr(m['topic']) + ' in ' + m['source'] for m in ms)}"
            for k, ms in hits.items()))
    warnings = []
    pillars = [x.strip() for x in (a.pillars or "").split("|") if x.strip()]
    if pillars:
        rot = vote_state.rotation(v, queue, pillars)
        warnings += rot["warnings"]
        if vote_state.normalize(a.pillar) != vote_state.normalize(rot["next_pillar"]):
            raise Refused(f"the next pillar in the rotation is {rot['next_pillar']!r}, not {a.pillar!r}")
    if not rows:
        warnings.append("no calendar table found; topics in the calendar were not checked")
    queue.append({"pillar": a.pillar.strip(), "options": {k: options[k] for k in vote_state.LETTERS}})
    return {"pick-queue.json": queue}, warnings


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pick", required=True)
    p.add_argument("--queue", required=True)
    p.add_argument("--posts", required=True)
    p.add_argument("--out", required=True, help="folder for the new files; they go to <out>/data/<name>")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--record-post", action="store_true", help="record a published post on its round")
    mode.add_argument("--queue-round", action="store_true", help="add a round at the end of the queue")
    p.add_argument("--round", help="--record-post: the closed round, YYYY-MM-DD")
    p.add_argument("--post-url", help="--record-post: the published post's address, as the publisher printed it")
    p.add_argument("--platform", help="--record-post: the platform the post was published on")
    p.add_argument("--platform-file", help="--record-post: the platform's data file, "
                   "shared/references/platforms/<platform>.json")
    p.add_argument("--date", help="--record-post: the publication date, YYYY-MM-DD")
    p.add_argument("--lang", help="--record-post: EN, PT or EN/PT")
    p.add_argument("--title", help="--record-post: the title shown on the profile")
    p.add_argument("--image", help="--record-post: assets/posts/<slug>.png|webp (omit when the post has no image)")
    p.add_argument("--pillar", help="--queue-round: the round's pillar, spelled as in the vote data")
    p.add_argument("--option", action="append", default=[], help="--queue-round: A=<topic>, B=..., C=...")
    p.add_argument("--calendar", help="--queue-round: docs/marketing/calendar.md (required)")
    p.add_argument("--pillars", help="--queue-round: the rotation, separated by |; refuses a pillar out of turn")
    return p.parse_args(argv)


def main(argv=None) -> int:
    a = parse_args(argv)
    if a.record_post and not all([a.round, a.post_url, a.date, a.lang, a.title]):
        fail("--record-post needs --round, --post-url, --date, --lang and --title")
    if a.queue_round and not a.calendar:
        fail("--queue-round needs --calendar")
    inputs = {"pick.json": a.pick, "pick-queue.json": a.queue, "posts.json": a.posts}
    out_dir = Path(a.out).resolve() / "data"
    for name, src in inputs.items():
        if (out_dir / name).resolve() == Path(src).resolve():
            fail(f"--out would overwrite the input {src}; write to another folder")
    warnings = []
    try:
        v, queue, posts = vote_state.load_all(a.pick, a.queue, a.posts)
        originals = {n: Path(p).read_text(encoding="utf-8") for n, p in inputs.items()}
        if a.record_post:
            new = record_post(a, v, posts)
        else:
            new, warnings = queue_round(a, v, queue, posts)
    except vote_state.Malformed as e:
        fail(str(e))
    except Refused as e:
        fail(str(e), 1)
    changed = []
    for name, obj in new.items():
        text = dump(obj)
        if text == originals[name]:
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / name
        target.write_text(text, encoding="utf-8")
        changed.append({"path": f"data/{name}", "file": str(target),
                        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    json.dump({"mode": "record-post" if a.record_post else "queue-round", "changed": changed, "warnings": warnings},
              sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
