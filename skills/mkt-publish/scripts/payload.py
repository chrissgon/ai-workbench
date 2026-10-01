#!/usr/bin/env python3
"""Build the payload of a batch of posts for one approval, and verify it before executing.

Usage:
  python3 payload.py build --content docs/marketing/content/2026-10-05-a.md [--content ...] \
      --workbench <path of the workbench checkout> [--platform linkedin] [--grace-minutes 120] [--out <folder>]
  python3 payload.py verify --manifest <out>/manifest.json --hash <plan hash> --workbench <workbench>
  python3 payload.py jobs --manifest <out>/manifest.json --workbench <workbench>
  python3 payload.py approval --state docs/workbench/state.md --hash <plan hash>

build   For each content file (written by mkt-social-copy): reads the slot time (the first ISO-8601
        date-time with offset in the header, before the first fenced block), the approval scope (a header
        line ending in ": plan" or ": action") and the exact text of the ```post and ```first-comment
        blocks, and an optional image named on a header line "- Image: <path>" (JPG, PNG or GIF, relative to
        the working directory). Writes <out>/<key>/post.txt, <out>/<key>/comment.txt (when there is a first comment),
        <out>/<key>/image.<ext> (a copy of the image, when there is one) and
        <out>/<key>/job.json, the scheduler command file that publishes the post and its first comment
        with the idempotency key <key> (the content file name without .md). Writes <out>/manifest.json
        (every post with its time, scope and the SHA-256 of each file) and prints the manifest's own
        SHA-256 as "plan_hash": the value recorded in the approval.
        <out> is a durable folder, because the approval is verified again days later: without --out it is
        .workbench-local/payloads/<first slot date>/ under the working directory ("-2", "-3" ... when that
        folder already holds a payload), created with mode 0700 and printed as "out". Inside a git
        repository the folder must be git-ignored (checked with `git check-ignore`); build refuses, exit 2,
        when it is not. --out <folder> names another folder (missing or empty), for a preview that is
        thrown away (a folder from mktemp -d) or a caller with its own durable store.
verify  Recomputes the manifest hash and every file hash listed in it, and checks that each job.json is the
        job the manifest describes at the folder's current place and --workbench. Exit 0 only when all match.
jobs    Writes each job.json again for where the payload folder and the workbench are now (after either
        was moved). The manifest and the plan_hash do not change. Prints the posts like build.
approval  Looks in the state file's "Approvals" table for a plan or action row whose Payload hash equals
        --hash. Prints {"match": true|false, "row": ..., "other_rows": [...]}: other_rows are plan or action rows
        with a different hash, which never cover this payload. Exit 0 when a row matches, 1 when none does.

The plan_hash does not depend on where the payload folder or the workbench lives: the manifest
("version": 2) holds paths relative to its own folder, and job.json, which the scheduler needs with
absolute paths, is derived from the manifest and not hashed into it. The same content files, platform
and grace minutes built again from the same working directory give the same plan_hash. A manifest
without "version" (written before this definition, with absolute paths and a job hash) is verified the
old way, and only while its folder is where it was built.

Prints JSON on stdout; diagnostics on stderr. Exit 0 ok, 1 verification failed, 2 usage or input error.
Standard library only; no network; it never publishes or schedules anything.
"""
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
IMAGE_MAGIC = {".png": [b"\x89PNG\r\n\x1a\n"], ".jpg": [b"\xff\xd8\xff"], ".jpeg": [b"\xff\xd8\xff"],
               ".gif": [b"GIF87a", b"GIF89a"]}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MANIFEST_VERSION = 2
DEFAULT_ROOT = Path(".workbench-local") / "payloads"
FILES = (("post_file", "post_sha256"), ("comment_file", "comment_sha256"), ("image_file", "image_sha256"))


def fail(message: str, code: int = 2):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    if not found.get("post"):
        raise ValueError("no ```post block")
    times = ISO.findall("\n".join(header))
    if len(set(times)) != 1:
        raise ValueError(f"expected one slot time with offset in the header, found {times or 'none'}")
    at = times[0]
    datetime.fromisoformat(at.replace("Z", "+00:00"))
    scopes = [m.group(1) for line in header for m in [SCOPE.search(line.strip())] if m]
    if len(scopes) != 1:
        raise ValueError(f"expected one approval line ending in ': plan' or ': action', found {scopes or 'none'}")
    images = [m.group(1) for line in header for m in [IMAGE_LINE.match(line)] if m]
    if len(images) > 1:
        raise ValueError(f"at most one '- Image:' line, found {len(images)}")
    return {"at": at, "scope": scopes[0], "post": found["post"], "comment": found.get("first-comment") or None,
            "image": images[0] if images else None}


def check_image(path: Path) -> str:
    """Return the image's extension after checking that it is a JPG, PNG or GIF by its bytes; raise otherwise."""
    ext = path.suffix.lower()
    if ext not in IMAGE_MAGIC:
        raise ValueError(f"image {path}: only .png, .jpg, .jpeg or .gif")
    if not path.is_file():
        raise ValueError(f"image {path} not found")
    data = path.read_bytes()
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"image {path}: {len(data)} bytes, more than {MAX_IMAGE_BYTES}")
    if not any(data.startswith(m) for m in IMAGE_MAGIC[ext]):
        raise ValueError(f"image {path}: the bytes are not a {ext[1:].upper()} file")
    return ".jpg" if ext == ".jpeg" else ext


def git_ignored(folder: Path):
    """True or False when the folder is inside a git work tree (ignored or not); None when it is in none."""
    inside = folder
    while not inside.is_dir():
        inside = inside.parent
    try:
        top = subprocess.run(["git", "-C", str(inside), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=30)
        if top.returncode != 0:
            return None
        check = subprocess.run(["git", "-C", str(inside), "check-ignore", "-q", "--", str(folder / "manifest.json")],
                               capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return {0: True, 1: False}.get(check.returncode)


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


def job_for(entry: dict, platform: str, grace_minutes: int, folder: Path, wb: Path) -> dict:
    """The scheduler command file of one post: derived from the manifest, absolute for this folder and workbench."""
    provider = wb / "providers" / "publisher" / f"{platform}.py"
    resolver = wb / "providers" / "secrets" / "resolver.py"
    post_file = str(folder / entry["post_file"])
    argv = ["uv", "run", str(provider), "publish", "--platform", platform,
            "--text-file", post_file, "--idempotency-key", entry["key"]]
    snapshot = [str(provider), str(resolver), post_file]
    for name, flag in (("comment_file", "--first-comment-file"), ("image_file", "--media")):
        if name in entry:
            argv += [flag, str(folder / entry[name])]
            snapshot.append(str(folder / entry[name]))
    argv.append("--confirmed")
    return {"argv": argv, "cwd": str(wb), "snapshot": snapshot, "grace_minutes": grace_minutes}


def write_jobs(data: dict, folder: Path, wb: Path):
    for e in data["posts"]:
        job = job_for(e, data["platform"], data["grace_minutes"], folder, wb)
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
    wb = Path(a.workbench).resolve()
    missing = [str(p) for p in (wb / "providers" / "publisher" / f"{a.platform}.py",
                                wb / "providers" / "secrets" / "resolver.py") if not p.is_file()]
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
            p["ext"] = check_image(Path(p["image"])) if p["image"] else None
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
    data = {"version": MANIFEST_VERSION, "platform": a.platform, "grace_minutes": a.grace_minutes, "posts": posts}
    write_jobs(data, out, wb)
    manifest = out / "manifest.json"
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    result = {"out": str(out), "git_ignored": ignored, "manifest": str(manifest), "plan_hash": sha256(manifest),
              "posts": absolute(data, out), "missing_providers": missing}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
    print()
    if missing:
        print(f"warning: not found: {', '.join(missing)}; the jobs cannot run until the workbench path is right",
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
    data = json.loads(manifest.read_text(encoding="utf-8"))
    version = data.get("version", 1)
    if version == 1:
        verify_legacy(data, problems)
    elif version != MANIFEST_VERSION:
        problems.append(f"manifest version {version} is not known to this script")
    else:
        if not a.workbench:
            fail("verify needs --workbench <path of the workbench checkout> for this manifest")
        wb = Path(a.workbench).resolve()
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
            if job != job_for(e, data["platform"], data["grace_minutes"], folder, wb):
                problems.append(f"{e['key']}: job.json is not the job of this manifest for this folder and "
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
    if data.get("version") != MANIFEST_VERSION:
        fail(f"{manifest} is not a version {MANIFEST_VERSION} manifest: its hash covers the jobs' absolute paths, "
             "so its jobs cannot be written again; build a new payload")
    folder = manifest.resolve().parent
    write_jobs(data, folder, Path(a.workbench).resolve())
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
    b.add_argument("--workbench", required=True)
    b.add_argument("--platform", default="linkedin")
    b.add_argument("--grace-minutes", type=int, default=120)
    v = sub.add_parser("verify")
    v.add_argument("--manifest", required=True)
    v.add_argument("--hash", required=True)
    v.add_argument("--workbench")
    j = sub.add_parser("jobs")
    j.add_argument("--manifest", required=True)
    j.add_argument("--workbench", required=True)
    ap = sub.add_parser("approval")
    ap.add_argument("--state", default="docs/workbench/state.md")
    ap.add_argument("--hash", required=True)
    a = p.parse_args(argv)
    return {"build": build, "verify": verify, "jobs": jobs, "approval": approval}[a.verb](a)


if __name__ == "__main__":
    sys.exit(main())
