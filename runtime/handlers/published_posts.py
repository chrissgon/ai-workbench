#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The weekly routine that lists the published posts (backlog item PB16): the first handler of the task runtime.

Once a week, after its time, it lists the posts the publisher's ledger records as published in the last 7 days,
takes each post's title, language, date and image from the project's own post file (never from the network), and
adds the posts the target file does not hold yet, in one commit through the code provider, under an active standing
approval of its policy. Without one it commits nothing and says why; the week stays open and the next firing tries
again (choice P7 of the platform plan: no approval per run).

  python3 runtime/handlers/published_posts.py tick    --project <dir>   what the dispatcher's worker calls
  python3 runtime/handlers/published_posts.py preview --project <dir>   the week's entries and the dry run of the
                                                                        commit; writes nothing, sets no cursor

Settings, under handlers["published-posts"] of <project>/docs/workbench/runtime.json, every one the person's:

  agent       the area agent that owns the routine (an agent of area_agents)
  dispatch    true: the worker calls tick
  platform    the platform the posts were published on: the publisher is publisher:<platform>
  repo        the target repository, <owner>/<name>
  branch      the target branch
  file        the target file in it, a JSON list in the form contracts/vote-data.md gives for data/posts.json
  weekday     1 (Monday) to 7 (Sunday), local time
  not_before  HH:MM, local time: the routine is due on its weekday at or after this time, once per ISO week
  policy      the policy name of the standing approval (default "published-posts"); the action kind it records

tick: (1) not due: {"status": "not-due"}. (2) The publisher's read-only verb `posts --platform <p> --since <7 days
back>` lists the published posts; a published post with no time in the ledger (an entry written before its version
2) stops the routine with the keys, and no time is derived. Each post's file is
docs/marketing/content/<idempotency key>.md: the title is the first non-empty line of its ```post block, the language
the third field of the header line that holds the slot time ("- Slot: <time> · <pillar> · <language> · ..."), the
date the day of the ledger's time in the slot's offset, the image the path of its "- Image: <path>" line, committed
as assets/posts/<key>.<ext>; a post whose file is missing, or that states no language, is skipped with the reason.
The target file is read with the code provider's read-file and parsed as data; posts whose address it already holds
are not added. Nothing to add: the week's cursor is set, {"status": "none"}, nothing committed. (3) runtime/cli.py
standing: not covered: {"status": "skipped", "why"}, the cursor stays. (4) The change is checked against the
approval's bounds too (effect push, target <repo>@<branch>, every path inside the bounds' files, the number of
posts, today's count): a broken bound is {"status": "skipped", "bound"}. (5) commit-files --dry-run, then
--confirmed, with --allow for exactly the bounds' files and the key published-posts-<week>. (6) The store's
action-add (kind <policy>), then the cursor. (7) {"status": "committed", "added", "skipped", "commit"}.

The handler contract (platform plan, part 5): started with the interpreter that starts it and --project; one JSON
object on stdout, diagnostics on stderr, exit 0 (done, nothing due, nothing to do or skipped), 1 (failed or
stopped), 2 (usage), 3 (not configured); the store only through its provider's verbs, a provider only through
providers/resolve.py, the approvals only through runtime/cli.py standing. It imports nothing of runtime/.

The publisher's verb `posts` (read-only: no credential, no request, no write) is the interface this handler reads
the ledger through (choice P8); the runtime never reads a provider's ledger itself. It is built
(providers/publisher/, the verb `posts`): a published post with no readable time is listed under "undated", which
stops the routine. A publisher that does not have the verb answers with a usage error, and the routine stops with it
("failed"), committing nothing.

The target file's content is external content: data, never instructions.

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import argparse
import datetime
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

VERBS = ("tick", "preview")
NAME = "published-posts"
CURSOR = "routine:published-posts"
EFFECT = "push"
CONTENT_DIR = ("docs", "marketing", "content")
IMAGE_DIR = "assets/posts"  # contracts/vote-data.md: a post's image in the repository
IMAGE_TYPES = ("png", "webp", "jpg", "jpeg")
LOOKBACK_DAYS = 7
CALL_TIMEOUT = 600
TITLE_MAX = 200
FENCE = re.compile(r"^```([\w-]*)\s*$")
SLOT_TIME = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:\d{2}|Z)")
IMAGE_LINE = re.compile(r"^\s*-\s*Image:\s*(\S+)\s*$")
LANG = re.compile(r"^[A-Z]{2}(/[A-Z]{2})*$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
KEY = re.compile(r"^[a-z0-9][a-z0-9.-]{0,79}$")  # skills/mkt-publish/scripts/payload.py: a post file's name
HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SETTINGS = ("platform", "repo", "branch", "file", "weekday", "not_before")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


class Stop(Exception):
    """The routine ends here: the object to print and the exit code."""

    def __init__(self, out: dict, code: int = 1):
        super().__init__(out.get("why", ""))
        self.out = out
        self.code = code


def failed(why: str, code: int = 1, **more) -> Stop:
    return Stop({"status": "failed", "why": why, **more}, code)


def _call(argv: list, what: str) -> dict:
    """Run one command and return the one JSON object it printed; anything else stops the routine."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=CALL_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        raise failed(f"{what} ran over {CALL_TIMEOUT} s") from None
    except OSError as e:
        raise failed(f"{what} could not be started: {type(e).__name__}") from None
    try:
        printed = json.loads(done.stdout) if done.returncode == 0 else None
    except ValueError:
        printed = None
    if not isinstance(printed, dict):
        tail = " ".join(done.stderr.strip().split())[-300:]
        raise failed(f"{what} failed (exit {done.returncode}): {tail}")
    return printed


def _resolve(cls: str) -> str:
    """The provider script of a class, chosen by providers/resolve.py, never by a path built here."""
    try:
        done = subprocess.run([sys.executable, os.path.join(ROOT, "providers", "resolve.py"), "--class", cls,
                               "--root", ROOT], capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise failed(f"providers/resolve.py --class {cls} could not run: {type(e).__name__}", 3) from None
    path = done.stdout.strip()
    if done.returncode != 0 or not os.path.isabs(path):
        raise failed(f"the class {cls} does not resolve: {' '.join(done.stderr.split())[-200:]}", 3)
    return path


class Store:
    """The store's verbs (class store:runtime), on the database the project's configuration names."""

    def __init__(self, db: str):
        self.script, self.db = _resolve("store:runtime"), db

    def __call__(self, *args) -> dict:
        return _call([sys.executable, self.script, "--db", self.db, *args], f"the store's {args[0]}")


def config(project: str) -> tuple:
    """(settings, store_db) from the project's runtime.json; a missing or malformed setting is exit 3."""
    path = os.path.join(project, "docs", "workbench", "runtime.json")
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        raise failed(f"{path} cannot be read: {type(e).__name__}", 3) from None
    settings = ((raw.get("handlers") if isinstance(raw, dict) else None) or {}).get(NAME)
    if not isinstance(settings, dict):
        raise failed(f"{path} has no handlers.{NAME}", 3)
    missing = [key for key in SETTINGS if key not in settings]
    if missing:
        raise failed(f"handlers.{NAME} needs {', '.join(missing)}", 3)
    s = dict(settings)
    s.setdefault("policy", NAME)
    if not isinstance(s["platform"], str) or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", s["platform"]):
        raise failed(f"handlers.{NAME}.platform is a platform name", 3)
    if not isinstance(s["repo"], str) or not REPO.fullmatch(s["repo"]):
        raise failed(f"handlers.{NAME}.repo is <owner>/<name>", 3)
    for key in ("branch", "file", "policy"):
        if not isinstance(s[key], str) or not s[key].strip() or s[key].startswith(("/", "-")) or ".." in s[key]:
            raise failed(f"handlers.{NAME}.{key} is a relative name", 3)
    if isinstance(s["weekday"], bool) or s["weekday"] not in range(1, 8):
        raise failed(f"handlers.{NAME}.weekday is 1 (Monday) to 7 (Sunday)", 3)
    if not isinstance(s["not_before"], str) or not HHMM.fullmatch(s["not_before"]):
        raise failed(f"handlers.{NAME}.not_before is HH:MM", 3)
    db = raw.get("store_db")
    if not isinstance(db, str) or not os.path.isabs(db):
        raise failed(f"{path} needs store_db: an absolute path", 3)
    return s, db


def week_of(now: datetime.datetime) -> str:
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def due(settings: dict, cursor, now: datetime.datetime) -> bool:
    """True on the weekday, at or after not_before (local time), when the cursor does not hold this ISO week."""
    return (now.isoweekday() == settings["weekday"] and now.strftime("%H:%M") >= settings["not_before"]
            and cursor != week_of(now))


def _when(value: str) -> datetime.datetime:
    raw = value.strip()
    parsed = datetime.datetime.fromisoformat(raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw)
    if parsed.tzinfo is None:
        raise ValueError(f"{value!r} has no offset")
    return parsed


def read_post(path: str) -> dict:
    """What a post file states: {"title", "slot", "lang", "images"}, read as the publisher's payload reads it (a
    header before the first fence, a ```post block)."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    header, block, name, in_header = [], None, None, True
    for line in text.splitlines():
        fence = FENCE.match(line)
        if name is None:
            if fence:
                in_header = False
                if fence.group(1) == "post" and block is None:
                    name, block = "post", []
                elif fence.group(1):
                    name = fence.group(1)
            elif in_header:
                header.append(line)
        elif fence and fence.group(1) == "":
            name = None
        elif name == "post":
            block.append(line)
    title = next((line.strip() for line in block or [] if line.strip()), "")
    slot, lang = None, None
    for line in header:
        found = SLOT_TIME.search(line)
        if found and slot is None:
            slot = found.group(0)
            fields = [part.strip() for part in line.split("·")]
            lang = fields[2].upper() if len(fields) > 2 and LANG.fullmatch(fields[2].upper()) else None
    images = [m.group(1) for line in header for m in [IMAGE_LINE.match(line)] if m]
    return {"title": title, "slot": slot, "lang": lang, "images": images}


def _post_entry(project: str, post: dict) -> tuple:
    """(entry, image or None, None) for one post of the ledger, or (None, None, why it is skipped)."""
    key = post["idempotency_key"]
    if not KEY.fullmatch(key):
        return None, None, f"the key {key!r} is not the name of a post file"
    rel = "/".join(CONTENT_DIR + (f"{key}.md",))
    path = os.path.join(project, *CONTENT_DIR, f"{key}.md")
    if not os.path.isfile(path) or os.path.islink(path):
        return None, None, f"no post file {rel}"
    stated = read_post(path)
    if not stated["title"]:
        return None, None, f"{rel} has no ```post block, or an empty one"
    if len(stated["title"]) > TITLE_MAX:
        return None, None, f"the first line of the post in {rel} is over {TITLE_MAX} characters"
    if stated["lang"] is None:
        return None, None, f"{rel} states no language on its slot line"
    try:
        published = _when(post["published_at"])
        offset = _when(stated["slot"]).tzinfo if stated["slot"] else None
    except (ValueError, TypeError, KeyError):
        return None, None, f"the time of {key} cannot be read"
    day = (published.astimezone(offset) if offset else published.astimezone()).date().isoformat()
    image = None
    if len(stated["images"]) > 1:
        return None, None, f"{rel} names more than one image"
    if stated["images"]:
        source = os.path.realpath(os.path.join(project, stated["images"][0]))
        ext = os.path.splitext(source)[1].lstrip(".").lower()
        if not source.startswith(os.path.realpath(project) + os.sep) or not os.path.isfile(source):
            return None, None, f"the image {stated['images'][0]} of {rel} is not a file of the project"
        if ext not in IMAGE_TYPES or not SLUG.fullmatch(key):
            return None, None, f"the image of {rel} cannot be named {IMAGE_DIR}/<key>.<{'|'.join(IMAGE_TYPES)}>"
        image = {"path": f"{IMAGE_DIR}/{key}.{ext}", "local": source}
    entry = {"date": day, "lang": stated["lang"], "title": stated["title"], "url": post["post_url"],
             "image": image["path"] if image else None}
    return entry, image, None


def collect(settings: dict, project: str, now: datetime.datetime) -> tuple:
    """(entries, images, skipped) of the posts the publisher's ledger records as published in the last 7 days,
    oldest first. Stops when the ledger holds a published post with no time."""
    publisher = _resolve(f"publisher:{settings['platform']}")
    since = (now - datetime.timedelta(days=LOOKBACK_DAYS)).isoformat(timespec="seconds")
    listed = _call(["uv", "run", publisher, "posts", "--platform", settings["platform"], "--since", since],
                   "the publisher's posts")
    undated = listed.get("undated") or []
    if undated:
        raise Stop({"status": "stopped", "undated": undated,
                    "why": "the publisher's ledger holds published posts with no time (entries written before its "
                           "version 2); the routine derives no time and lists nothing until the person settles them"})
    entries, images, skipped = [], [], []
    for post in listed.get("posts") or []:
        if not isinstance(post, dict) or not all(isinstance(post.get(k), str) for k in
                                                 ("idempotency_key", "post_url", "published_at")):
            raise failed("the publisher's posts printed an entry without idempotency_key, post_url or published_at")
        entry, image, why = _post_entry(project, post)
        if why:
            skipped.append({"idempotency_key": post["idempotency_key"], "why": why})
            continue
        entries.append(entry)
        if image:
            images.append(image)
    return entries, images, skipped


def dump(items: list) -> str:
    """The form contracts/vote-data.md requires: indent of one space, characters not escaped, a final newline."""
    return json.dumps(items, indent=1, ensure_ascii=False) + "\n"


def merge(posts_text: str, entries: list) -> tuple:
    """(the target's new text, the entries added). The existing text is data: parsed, every item kept as it is, the
    new ones added at the end; an entry whose address the file already holds is not added. A file that is not a
    list in the contract's form is refused, so no existing byte is rewritten."""
    try:
        items = json.loads(posts_text)
    except ValueError:
        raise failed("the target file is not JSON; nothing is changed") from None
    if not isinstance(items, list) or dump(items) != posts_text:
        raise failed("the target file is not a list in the form contracts/vote-data.md requires (indent of one "
                     "space, characters not escaped, a final newline); nothing is changed")
    held = {item.get("url") for item in items if isinstance(item, dict)}
    added = []
    for entry in entries:
        if entry["url"] in held:
            continue
        held.add(entry["url"])
        added.append(entry)
    return dump(items + added), added


def _inside(path: str, globs: list) -> bool:
    """A repository path inside one glob, part by part, as the code provider's --allow reads it."""
    parts = path.split("/")

    def part_matches(part: str, glob_part: str) -> bool:
        hidden = part.startswith(".") and not glob_part.startswith(".")  # a glob never matches a leading dot
        return fnmatch.fnmatchcase(part, glob_part) and not hidden

    for glob in globs:
        pattern = glob.split("/")
        if len(pattern) == len(parts) and all(part_matches(p, g) for p, g in zip(parts, pattern)):
            return True
    return False


def broken_bound(answer: dict, settings: dict, paths: list, count: int):
    """The name of the first bound the change breaks, or None."""
    bounds = (answer.get("approval") or {}).get("bounds") or {}
    if EFFECT not in (bounds.get("effects") or []):
        return "effects"
    if f"{settings['repo']}@{settings['branch']}" not in (bounds.get("targets") or []):
        return "targets"
    if not all(_inside(path, bounds.get("files") or []) for path in paths):
        return "files"
    if not isinstance(bounds.get("max_items_per_run"), int) or count > bounds["max_items_per_run"]:
        return "max_items_per_run"
    if not isinstance(bounds.get("max_per_day"), int) or int(answer.get("executed_today") or 0) >= bounds["max_per_day"]:
        return "max_per_day"
    return None


def _target(vcs: str, settings: dict) -> str:
    read = _call(["uv", "run", vcs, "read-file", "--repo", settings["repo"], "--path", settings["file"],
                  "--ref", settings["branch"]], "the code provider's read-file")
    if not isinstance(read.get("content"), str):
        raise failed("the code provider's read-file printed no content")
    return read["content"]


def _commit_argv(vcs: str, settings: dict, folder: str, text: str, images: list, globs: list, key: str, added: list):
    local = os.path.join(folder, "target.json")
    with open(local, "w", encoding="utf-8") as f:
        f.write(text)
    message = os.path.join(folder, "message.txt")
    with open(message, "w", encoding="utf-8") as f:
        f.write(f"Add the posts published in the week before {key[len(NAME) + 1:]}\n\n" +
                "".join(f"- {entry['date']} {entry['url']}\n" for entry in added))
    argv = ["uv", "run", vcs, "commit-files", "--repo", settings["repo"], "--branch", settings["branch"],
            "--message-file", message, "--file", f"{settings['file']}={local}"]
    for image in images:
        argv += ["--file", f"{image['path']}={image['local']}"]
    for glob in globs:
        argv += ["--allow", glob]
    return argv + ["--idempotency-key", key]


def preview(project: str, now: datetime.datetime) -> dict:
    """The week's entries and the dry run of the commit: nothing is written and no cursor is set."""
    settings, _ = config(project)
    entries, images, skipped = collect(settings, project, now)
    vcs = _resolve("integration:vcs")
    text, added = merge(_target(vcs, settings), entries)
    if not added:
        return {"status": "none", "skipped": skipped}
    used = [image for image in images if image["path"] in {entry["image"] for entry in added}]
    paths = [settings["file"]] + [image["path"] for image in used]
    with tempfile.TemporaryDirectory(prefix="wb-published-posts-") as folder:
        argv = _commit_argv(vcs, settings, folder, text, used, paths, f"{NAME}-{week_of(now)}", added)
        dry = _call(argv + ["--dry-run"], "the code provider's commit-files --dry-run")
    return {"status": "preview", "week": week_of(now), "added": added, "skipped": skipped, "dry_run": dry}


def tick(project: str, now: datetime.datetime) -> dict:
    settings, db = config(project)
    store = Store(db)
    week = week_of(now)
    if not due(settings, store("cursor-get", "--name", CURSOR).get("value"), now):
        return {"status": "not-due"}
    entries, images, skipped = collect(settings, project, now)
    vcs = _resolve("integration:vcs")
    text, added = merge(_target(vcs, settings), entries)
    if not added:
        store("cursor-set", "--name", CURSOR, "--value", week)
        return {"status": "none", "skipped": skipped}
    answer = _call([sys.executable, os.path.join(ROOT, "runtime", "cli.py"), "standing", "--project", project,
                    "--policy", settings["policy"]], "runtime/cli.py standing")
    if answer.get("covered") is not True:
        return {"status": "skipped", "why": answer.get("why") or "no standing approval covers the policy",
                "skipped": skipped}
    used = [image for image in images if image["path"] in {entry["image"] for entry in added}]
    paths = [settings["file"]] + [image["path"] for image in used]
    bound = broken_bound(answer, settings, paths, len(added))
    if bound:
        return {"status": "skipped", "bound": bound, "why": f"the change is outside the approved bounds: {bound}",
                "skipped": skipped}
    key = f"{NAME}-{week}"
    globs = list(answer["approval"]["bounds"]["files"])
    with tempfile.TemporaryDirectory(prefix="wb-published-posts-") as folder:
        argv = _commit_argv(vcs, settings, folder, text, used, globs, key, added)
        _call(argv + ["--dry-run"], "the code provider's commit-files --dry-run")
        commit = _call(argv + ["--confirmed"], "the code provider's commit-files")
        result = os.path.join(folder, "result.json")
        with open(result, "w", encoding="utf-8") as f:
            json.dump(commit, f)
        store("action-add", "--kind", settings["policy"], "--idempotency-key", key, "--target",
              f"{settings['repo']}@{settings['branch']}", "--payload-sha256",
              hashlib.sha256(text.encode("utf-8")).hexdigest(), "--result-file", result)
    store("cursor-set", "--name", CURSOR, "--value", week)
    return {"status": "committed", "added": len(added), "skipped": skipped, "commit": commit}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Stop({"status": "failed", "why": f"{message}. See --help."}, 2)


def main(argv=None, now=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or "--help" in argv or "-h" in argv:
        print(__doc__.strip(), file=sys.stdout if argv else sys.stderr)
        return 0 if argv else 2
    now = now or datetime.datetime.now().astimezone()
    try:
        p = _Parser(prog="published_posts.py", add_help=False)
        p.add_argument("verb", choices=VERBS)
        p.add_argument("--project", required=True)
        a = p.parse_args(argv)
        project = os.path.realpath(a.project)
        out, code = (tick(project, now) if a.verb == "tick" else preview(project, now)), 0
    except Stop as e:
        out, code = e.out, e.code
        print(f"{out.get('status')}: {out.get('why')}", file=sys.stderr)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return code


if __name__ == "__main__":
    sys.exit(main())
