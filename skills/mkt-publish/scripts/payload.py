#!/usr/bin/env python3
"""Build the payload of a batch of posts for one approval, and verify it before executing.

Usage:
  python3 payload.py build --content docs/marketing/content/2027-10-11-a.md [--content ...] \
      --platform <platform> --platform-file <path of the platform's data file> \
      --publisher <path resolve.py printed> --workbench <path of the workbench checkout> \
      [--grace-minutes 120] [--out <folder>]
  python3 payload.py verify --manifest <out>/manifest.json --hash <plan hash> --publisher <path> --workbench <path>
  python3 payload.py jobs --manifest <out>/manifest.json --publisher <path> --workbench <path>
  python3 payload.py approval --state docs/workbench/state.md --hash <plan hash>

build   For each content file (written by mkt-social-copy): reads the slot time (the first ISO-8601
        date-time with offset in the header, before the first fenced block), the approval scope (a header
        line ending in ": plan" or ": action") and the exact text of the ```post and ```first-comment
        blocks, and an optional image named on a header line "- Image: <path>" (relative to the working
        directory). Writes <out>/<key>/post.txt, <out>/<key>/comment.txt (when there is a first comment),
        <out>/<key>/image.<ext> (a copy of the image, when there is one) and <out>/<key>/job.json, the
        scheduler command file that runs the publisher with the idempotency key <key> (the content file name
        without .md). Writes <out>/manifest.json (every post with its time, scope and the SHA-256 of each
        file) and prints the manifest's own SHA-256 as "plan_hash": the value recorded in the approval.
        <out> is a durable folder, because the approval is verified again days later: without --out it is
        .workbench-local/payloads/<first slot date>/ under the working directory ("-2", "-3" ... when that
        folder already holds a payload), created with mode 0700 and printed as "out". Inside a git
        repository the folder must be git-ignored (checked with `git check-ignore`); build refuses, exit 2,
        when it is not, and when git cannot answer. --out <folder> names another folder (missing or empty),
        for a preview that is thrown away (a folder from mktemp -d) or a caller with its own durable store.

The platform. --platform is the platform's name; it is lower-cased, so that two spellings of one platform give
one plan_hash. --platform-file is that platform's data file (shared/references/platforms/<platform>.json): its
"platform" must be the same name. From it, build reads whether a post needs text, the most characters a post and
a first comment may have, whether a first comment is supported, and the media a post may carry (types told by
their first bytes, size, count). This script holds no limit of a platform. Without --platform-file (the call of a
caller written before the flag) a post must have text and may carry no image, and a line on stderr says so.

The publisher. --publisher is the path of the publisher provider that `providers/resolve.py --class
publisher:<platform>` printed; this script never builds a provider's path. The job runs it with `uv run`, from
--workbench, and its snapshot holds the publisher and the secret resolver the publisher reads beside its own
folder (<publisher's folder>/../secrets/resolver.py). Without --publisher, build writes no job.json
("jobs_written": false): for a caller that writes its own job; `jobs` writes them later.

verify  Recomputes the manifest hash and every file hash listed in it, and checks that each job.json is the
        job the manifest describes at the folder's current place, for --publisher and --workbench. Exit 0 only
        when all match; a manifest that is not JSON is a problem (exit 1).
jobs    Writes each job.json again for where the payload folder, the publisher and the workbench are now (after
        one was moved). The manifest and the plan_hash do not change. Prints the posts like build.
approval  Looks in the state file's "Approvals" table for a plan or action row whose Payload hash equals
        --hash. Prints {"match": true|false, "row": ..., "other_rows": [...]}: other_rows are plan or action rows
        with a different hash, which never cover this payload. Exit 0 when a row matches, 1 when none does.

The plan_hash does not depend on where the payload folder, the publisher or the workbench lives: the manifest
("version": 2) holds paths relative to its own folder, and job.json, which the scheduler needs with absolute
paths, is derived from the manifest and not hashed into it. The same content files, platform and grace minutes
built again from the same working directory give the same plan_hash. A manifest without "version" (written
before this definition, with absolute paths and a job hash) is verified the old way, and only while its folder
is where it was built.

Prints JSON on stdout; diagnostics on stderr. Exit 0 ok, 1 verification failed, 2 usage or input error.
Standard library only; no network; it never publishes or schedules anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

FENCE = re.compile(r"^```([\w-]*)\s*$")
ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:\d{2}|Z)")
SCOPE = re.compile(r":\s*(plan|action)\s*$")
KEY = re.compile(r"^[a-z0-9][a-z0-9.-]{0,79}$")
IMAGE_LINE = re.compile(r"^\s*-\s*Image:\s*(\S+)\s*$")
PLATFORM_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MANIFEST_VERSION = 2
DEFAULT_ROOT = Path(".workbench-local") / "payloads"
FILES = (("post_file", "post_sha256"), ("comment_file", "comment_sha256"), ("image_file", "image_sha256"))
# Without a data file: text required, no media, no limit this script could know.
NO_DATA = {"requires_text": True, "max_characters": None, "first_comment": True, "first_comment_max": None,
           "max_count": 0, "max_bytes": 0, "types": []}


def fail(message: str, code: int = 2):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def platform_name(value: str) -> str:
    name = value.strip().lower()
    if not PLATFORM_NAME.match(name):
        fail(f"--platform {value!r} is not a platform name (lowercase letters, digits and hyphens)")
    return name


def platform_rules(name: str, platform_file) -> dict:
    """What a post may hold on this platform, from its data file."""
    if not platform_file:
        print(f"warning: no --platform-file: a post needs text and may carry no image; pass the data file of "
              f"{name!r} to apply its rules", file=sys.stderr)
        return dict(NO_DATA)
    try:
        data = json.loads(Path(platform_file).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("not a JSON object")
        if data.get("platform") != name:
            fail(f"--platform-file {platform_file} is the data file of {data.get('platform')!r}, not of {name!r}")
        post, media = data["post"], data["media"]
        types = [{"name": t["name"], "extensions": [e.lower() for e in t["extensions"]],
                  "magic": [bytes.fromhex(m) for m in t["magic_hex"]]} for t in media["types"]]
        return {"requires_text": bool(post["requires_text"]), "max_characters": int(post["max_characters"]),
                "first_comment": bool(post["first_comment"]["supported"]),
                "first_comment_max": int(post["first_comment"]["max_characters"]),
                "max_count": int(media["max_count"]), "max_bytes": int(media["max_bytes"]), "types": types}
    except OSError as e:
        fail(f"--platform-file: {e}")
    except (ValueError, KeyError, TypeError) as e:
        fail(f"--platform-file {platform_file}: not a platform data file ({type(e).__name__}: {e})")


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    header, found, name, buf, in_header = [], {}, None, [], True
    for line in text.splitlines():
        m = FENCE.match(line)
        if name is None:
            if m:
                in_header = False
                if m.group(1) in ("post", "first-comment"):
                    if m.group(1) in found:
                        raise ValueError(f"more than one ```{m.group(1)} block")
                    name, buf = m.group(1), []
            elif in_header:
                header.append(line)
        elif m and m.group(1) == "":
            found[name] = "\n".join(buf).strip("\n")
            name = None
        else:
            buf.append(line)
    if name is not None:
        raise ValueError(f"```{name} block is not closed")
    times = ISO.findall("\n".join(header))
    if len(set(times)) != 1:
        raise ValueError(f"expected one slot time with offset in the header, found {times or 'none'}")
    at = times[0]
    datetime.fromisoformat(at.replace("Z", "+00:00"))
    scopes = [m.group(1) for line in header for m in [SCOPE.search(line.strip())] if m]
    if len(scopes) != 1:
        raise ValueError(f"expected one approval line ending in ': plan' or ': action', found {scopes or 'none'}")
    images = [m.group(1) for line in header for m in [IMAGE_LINE.match(line)] if m]
    return {"at": at, "scope": scopes[0], "post": found.get("post") or "",
            "comment": found.get("first-comment") or None, "images": images}


def check_post(p: dict, rules: dict):
    """Raise when the post breaks a rule of the platform."""
    if not p["post"] and (rules["requires_text"] or not p["images"]):
        raise ValueError("no ```post block, or an empty one: a post on this platform needs text")
    if rules["max_characters"] is not None and len(p["post"]) > rules["max_characters"]:
        raise ValueError(f"the post has {len(p['post'])} characters, more than {rules['max_characters']}")
    if p["comment"]:
        if not rules["first_comment"]:
            raise ValueError("this platform takes no first comment")
        if rules["first_comment_max"] is not None and len(p["comment"]) > rules["first_comment_max"]:
            raise ValueError(f"the first comment has {len(p['comment'])} characters, more than "
                             f"{rules['first_comment_max']}")
    if len(p["images"]) > 1:
        raise ValueError(f"at most one '- Image:' line, found {len(p['images'])}")
    if p["images"] and rules["max_count"] < 1:
        raise ValueError("this platform takes no image here" if rules["types"] else
                         "an image needs --platform-file: the media a platform takes are read from its data file")


def check_image(path: Path, rules: dict) -> str:
    """Return the image's extension after checking its type, by its bytes, and its size; raise otherwise."""
    ext = path.suffix.lower()
    kind = next((t for t in rules["types"] if ext in t["extensions"]), None)
    if kind is None:
        allowed = ", ".join(e for t in rules["types"] for e in t["extensions"])
        raise ValueError(f"image {path}: only {allowed}")
    if not path.is_file():
        raise ValueError(f"image {path} not found")
    data = path.read_bytes()
    if len(data) > rules["max_bytes"]:
        raise ValueError(f"image {path}: {len(data)} bytes, more than {rules['max_bytes']}")
    if not any(data.startswith(m) for m in kind["magic"]):
        raise ValueError(f"image {path}: the bytes are not a {kind['name'].upper()} file")
    return kind["extensions"][0]


def git_ignored(folder: Path):
    """True or False when the folder is inside a git work tree (ignored or not); None when it is in none.
    A check that git cannot answer is a refusal (exit 2), never read as "not a repository"."""
    inside = folder
    while not inside.is_dir():
        inside = inside.parent
    try:
        top = subprocess.run(["git", "-C", str(inside), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if top.returncode != 0:
        return None
    try:
        check = subprocess.run(["git", "-C", str(inside), "check-ignore", "-q", "--", str(folder / "manifest.json")],
                               capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        fail(f"git check-ignore could not run for {folder}: {e}; nothing was written")
    if check.returncode not in (0, 1):
        fail(f"git check-ignore exited {check.returncode} for {folder} ({check.stderr.strip()[:200]}): whether "
             "the folder is ignored is not known; nothing was written")
    return check.returncode == 0


def default_out(first_date: str) -> Path:
    base = DEFAULT_ROOT.resolve() / first_date
    n, out = 1, base
    while out.exists() and (not out.is_dir() or any(out.iterdir())):
        n += 1
        out = base.with_name(f"{base.name}-{n}")
    return out


def make_private(folder: Path):
    """Create the folder and its missing parents with mode 0700."""
    missing = []
    while not folder.exists():
        missing.append(folder)
        folder = folder.parent
    for d in reversed(missing):
        d.mkdir(mode=0o700)
        d.chmod(0o700)


def publisher_path(value) -> Path:
    path = Path(value).resolve()
    if not path.is_file():
        fail(f"--publisher {value}: no such file; pass the path `providers/resolve.py --class publisher:<platform>` "
             "printed")
    return path


def job_for(entry: dict, platform: str, grace_minutes: int, folder: Path, publisher: Path, wb: Path) -> dict:
    """The scheduler command file of one post: derived from the manifest, absolute for this folder, publisher and
    workbench."""
    resolver = publisher.parent.parent / "secrets" / "resolver.py"
    post_file = str(folder / entry["post_file"])
    argv = ["uv", "run", str(publisher), "publish", "--platform", platform,
            "--text-file", post_file, "--idempotency-key", entry["key"]]
    snapshot = [str(publisher), str(resolver), post_file]
    for name, flag in (("comment_file", "--first-comment-file"), ("image_file", "--media")):
        if name in entry:
            argv += [flag, str(folder / entry[name])]
            snapshot.append(str(folder / entry[name]))
    argv.append("--confirmed")
    return {"argv": argv, "cwd": str(wb), "snapshot": snapshot, "grace_minutes": grace_minutes}


def write_jobs(data: dict, folder: Path, publisher: Path, wb: Path):
    for e in data["posts"]:
        job = job_for(e, data["platform"], data["grace_minutes"], folder, publisher, wb)
        (folder / e["job_file"]).write_text(json.dumps(job, indent=1) + "\n", encoding="utf-8")


def absolute(data: dict, folder: Path) -> list:
    """The manifest's posts with the file paths made absolute, for the caller's next commands."""
    names = [f for f, _ in FILES] + ["job_file"]
    return [{k: (str(folder / v) if k in names else v) for k, v in e.items()} for e in data["posts"]]


def relative_to_cwd(path: str) -> str:
    try:
        return Path(path).resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path


def build(a) -> int:
    platform = platform_name(a.platform)
    rules = platform_rules(platform, a.platform_file)
    wb = Path(a.workbench).resolve()
    publisher = publisher_path(a.publisher) if a.publisher else None
    missing = []
    if publisher and not (publisher.parent.parent / "secrets" / "resolver.py").is_file():
        missing.append(str(publisher.parent.parent / "secrets" / "resolver.py"))
    parsed, keys = [], set()
    for c in a.content:
        path = Path(c)
        key = path.stem
        if not KEY.match(key):
            fail(f"{c}: file name {key!r} is not a valid key (lowercase letters, digits, dots, hyphens)")
        if key in keys:
            fail(f"{c}: duplicate key {key}")
        keys.add(key)
        try:
            p = parse(path)
            check_post(p, rules)
            p["image"] = p["images"][0] if p["images"] else None
            p["ext"] = check_image(Path(p["image"]), rules) if p["image"] else None
        except (OSError, ValueError) as e:
            fail(f"{c}: {e}")
        parsed.append((datetime.fromisoformat(p["at"].replace("Z", "+00:00")), c, key, p))
    parsed.sort(key=lambda t: t[0])

    out = Path(a.out).resolve() if a.out else default_out(parsed[0][3]["at"][:10])
    if out.exists() and not out.is_dir():
        fail(f"--out {out} is not a folder")
    if out.is_dir() and any(out.iterdir()):
        fail(f"--out {out} is not empty; leave --out off to get a new folder under {DEFAULT_ROOT}")
    ignored = git_ignored(out)
    if ignored is False:
        fail(f"{out} is inside a git repository and is not git-ignored: a payload is never committed. "
             f"Add the line '{DEFAULT_ROOT.parts[0]}/' to the project's .gitignore and run build again")
    make_private(out)

    posts = []
    for _, c, key, p in parsed:
        d = out / key
        d.mkdir(mode=0o700)
        post_file = d / "post.txt"
        post_file.write_text(p["post"] + "\n", encoding="utf-8")
        entry = {"key": key, "content": relative_to_cwd(c), "at": p["at"], "scope": p["scope"],
                 "post_file": f"{key}/post.txt", "post_sha256": sha256(post_file), "post_chars": len(p["post"])}
        if p["comment"]:
            comment_file = d / "comment.txt"
            comment_file.write_text(p["comment"] + "\n", encoding="utf-8")
            entry.update(comment_file=f"{key}/comment.txt", comment_sha256=sha256(comment_file))
        if p["image"]:
            image_file = d / f"image{p['ext']}"
            image_file.write_bytes(Path(p["image"]).read_bytes())
            entry.update(image_source=p["image"], image_file=f"{key}/{image_file.name}",
                         image_sha256=sha256(image_file))
        entry["job_file"] = f"{key}/job.json"
        posts.append(entry)
    data = {"version": MANIFEST_VERSION, "platform": platform, "grace_minutes": a.grace_minutes, "posts": posts}
    if publisher:
        write_jobs(data, out, publisher, wb)
    manifest = out / "manifest.json"
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    result = {"out": str(out), "git_ignored": ignored, "manifest": str(manifest), "plan_hash": sha256(manifest),
              "platform": platform, "jobs_written": publisher is not None, "posts": absolute(data, out),
              "missing_providers": missing}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
    print()
    if not publisher:
        print("warning: no --publisher: no job.json was written; run `payload.py jobs` with the path resolve.py "
              "printed before scheduling", file=sys.stderr)
    if missing:
        print(f"warning: not found: {', '.join(missing)}; the jobs cannot run until the publisher's path is right",
              file=sys.stderr)
    return 0


def verify_legacy(data: dict, problems: list):
    """A manifest written before "version": absolute paths, and the hash of each job.json."""
    for e in data.get("posts", []):
        for f, h in FILES + (("job_file", "job_sha256"),):
            if f in e:
                p = Path(e[f])
                if not p.is_file():
                    problems.append(f"{e['key']}: {p} missing")
                elif sha256(p) != e[h]:
                    problems.append(f"{e['key']}: {p.name} changed")


def verify(a) -> int:
    manifest = Path(a.manifest)
    if not manifest.is_file():
        print(json.dumps({"ok": False, "problems": [f"{manifest} not found"]}))
        return 1
    folder = manifest.resolve().parent
    problems = []
    if sha256(manifest) != a.hash.strip().lower():
        problems.append("manifest hash differs from the approval")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("posts", []), list):
            raise ValueError("not a manifest object")
    except (OSError, ValueError) as e:
        problems.append(f"{manifest} is not a readable manifest: {e}")
        print(json.dumps({"ok": False, "manifest_version": None, "payload": str(folder), "problems": problems},
                         indent=1))
        return 1
    version = data.get("version", 1)
    if version == 1:
        verify_legacy(data, problems)
    elif version != MANIFEST_VERSION:
        problems.append(f"manifest version {version} is not known to this script")
    else:
        if not a.workbench or not a.publisher:
            fail("verify needs --publisher <path resolve.py printed> and --workbench <path of the workbench "
                 "checkout> for this manifest")
        wb, publisher = Path(a.workbench).resolve(), Path(a.publisher).resolve()
        for e in data["posts"]:
            for f, h in FILES:
                if f in e:
                    p = folder / e[f]
                    if not p.is_file():
                        problems.append(f"{e['key']}: {p} missing")
                    elif sha256(p) != e[h]:
                        problems.append(f"{e['key']}: {p.name} changed")
            job_file = folder / e["job_file"]
            try:
                job = json.loads(job_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                job = None
            if job != job_for(e, data["platform"], data["grace_minutes"], folder, publisher, wb):
                problems.append(f"{e['key']}: job.json is not the job of this manifest for this folder, publisher and "
                                "workbench (after a move, run: payload.py jobs)")
    print(json.dumps({"ok": not problems, "manifest_version": version, "payload": str(folder),
                      "problems": problems}, indent=1))
    return 0 if not problems else 1


def jobs(a) -> int:
    manifest = Path(a.manifest)
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        fail(f"--manifest: {e}")
    if not isinstance(data, dict) or data.get("version") != MANIFEST_VERSION:
        fail(f"{manifest} is not a version {MANIFEST_VERSION} manifest: its hash covers the jobs' absolute paths, "
             "so its jobs cannot be written again; build a new payload")
    folder = manifest.resolve().parent
    write_jobs(data, folder, publisher_path(a.publisher), Path(a.workbench).resolve())
    json.dump({"out": str(folder), "manifest": str(manifest.resolve()), "plan_hash": sha256(manifest),
               "posts": absolute(data, folder)}, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


def approval(a) -> int:
    want = a.hash.strip().lower()
    try:
        lines = Path(a.state).read_text(encoding="utf-8").splitlines()
    except OSError as e:
        fail(f"--state: {e}")
    match, others = None, []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 6 and cells[0].lower() in ("plan", "action"):
            row = {"scope": cells[0], "what": cells[1], "payload_hash": cells[2], "approved": cells[3],
                   "expires": cells[4], "status": cells[5]}
            if cells[2].lower() == want and match is None:
                match = row
            else:
                others.append(row)
    print(json.dumps({"match": match is not None, "row": match, "other_rows": others}, ensure_ascii=False, indent=1))
    return 0 if match else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="verb", required=True)
    b = sub.add_parser("build")
    b.add_argument("--content", action="append", required=True)
    b.add_argument("--out", help="payload folder, missing or empty (default: a new folder under "
                   ".workbench-local/payloads/ in the working directory)")
    b.add_argument("--platform", required=True, help="the platform's name; lower-cased")
    b.add_argument("--platform-file", help="the platform's data file, shared/references/platforms/<platform>.json")
    b.add_argument("--publisher", help="the publisher's path, as providers/resolve.py printed it")
    b.add_argument("--workbench", required=True, help="the workbench checkout the jobs run from")
    b.add_argument("--grace-minutes", type=int, default=120)
    v = sub.add_parser("verify")
    v.add_argument("--manifest", required=True)
    v.add_argument("--hash", required=True)
    v.add_argument("--publisher")
    v.add_argument("--workbench")
    j = sub.add_parser("jobs")
    j.add_argument("--manifest", required=True)
    j.add_argument("--publisher", required=True)
    j.add_argument("--workbench", required=True)
    ap = sub.add_parser("approval")
    ap.add_argument("--state", default="docs/workbench/state.md")
    ap.add_argument("--hash", required=True)
    a = p.parse_args(argv)
    return {"build": build, "verify": verify, "jobs": jobs, "approval": approval}[a.verb](a)


if __name__ == "__main__":
    sys.exit(main())
