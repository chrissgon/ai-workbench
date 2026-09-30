#!/usr/bin/env python3
"""Build the payload of a batch of posts for one approval, and verify it before executing.

Usage:
  python3 payload.py build --content docs/marketing/content/2026-10-05-a.md [--content ...] \
      --out <folder from mktemp -d> --workbench <path of the workbench checkout> [--platform linkedin] \
      [--grace-minutes 120]
  python3 payload.py verify --manifest <out>/manifest.json --hash <plan hash>
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
verify  Recomputes the manifest hash and every file hash listed in it. Exit 0 only when all match.
approval  Looks in the state file's "Approvals" table for a plan or action row whose Payload hash equals
        --hash. Prints {"match": true|false, "row": ..., "other_rows": [...]}: other_rows are plan or action rows
        with a different hash, which never cover this payload. Exit 0 when a row matches, 1 when none does.

Prints JSON on stdout; diagnostics on stderr. Exit 0 ok, 1 verification failed, 2 usage or input error.
Standard library only; no network; it never publishes or schedules anything.
"""
import argparse
import hashlib
import json
import re
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


def build(a) -> int:
    out = Path(a.out).resolve()
    if not out.is_dir():
        fail(f"--out {out} is not a folder (create it with mktemp -d)")
    if any(out.iterdir()):
        fail(f"--out {out} is not empty; use a new folder from mktemp -d")
    wb = Path(a.workbench).resolve()
    provider = wb / "providers" / "publisher" / f"{a.platform}.py"
    resolver = wb / "providers" / "secrets" / "resolver.py"
    missing = [str(p) for p in (provider, resolver) if not p.is_file()]
    posts, keys = [], set()
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
        except (OSError, ValueError) as e:
            fail(f"{c}: {e}")
        d = out / key
        d.mkdir(mode=0o700)
        post_file = d / "post.txt"
        post_file.write_text(p["post"] + "\n", encoding="utf-8")
        argv = ["uv", "run", str(provider), "publish", "--platform", a.platform,
                "--text-file", str(post_file), "--idempotency-key", key]
        snapshot = [str(provider), str(resolver), str(post_file)]
        entry = {"key": key, "content": c, "at": p["at"], "scope": p["scope"],
                 "post_file": str(post_file), "post_sha256": sha256(post_file), "post_chars": len(p["post"])}
        if p["comment"]:
            comment_file = d / "comment.txt"
            comment_file.write_text(p["comment"] + "\n", encoding="utf-8")
            argv += ["--first-comment-file", str(comment_file)]
            snapshot.append(str(comment_file))
            entry.update(comment_file=str(comment_file), comment_sha256=sha256(comment_file))
        if p["image"]:
            try:
                ext = check_image(Path(p["image"]))
            except ValueError as e:
                fail(f"{c}: {e}")
            image_file = d / f"image{ext}"
            image_file.write_bytes(Path(p["image"]).read_bytes())
            argv += ["--media", str(image_file)]
            snapshot.append(str(image_file))
            entry.update(image_source=p["image"], image_file=str(image_file), image_sha256=sha256(image_file))
        argv.append("--confirmed")
        job = {"argv": argv, "cwd": str(wb), "snapshot": snapshot, "grace_minutes": a.grace_minutes}
        job_file = d / "job.json"
        job_file.write_text(json.dumps(job, indent=1) + "\n", encoding="utf-8")
        entry.update(job_file=str(job_file), job_sha256=sha256(job_file))
        posts.append(entry)
    posts.sort(key=lambda e: datetime.fromisoformat(e["at"].replace("Z", "+00:00")))
    manifest = out / "manifest.json"
    manifest.write_text(json.dumps({"platform": a.platform, "posts": posts}, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    result = {"manifest": str(manifest), "plan_hash": sha256(manifest), "posts": posts,
              "missing_providers": missing}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
    print()
    if missing:
        print(f"warning: not found: {', '.join(missing)}; the jobs cannot run until the workbench path is right",
              file=sys.stderr)
    return 0


def verify(a) -> int:
    manifest = Path(a.manifest)
    if not manifest.is_file():
        print(json.dumps({"ok": False, "problems": [f"{manifest} not found"]}))
        return 1
    problems = []
    if sha256(manifest) != a.hash.strip().lower():
        problems.append("manifest hash differs from the approval")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    for e in data.get("posts", []):
        for f, h in (("post_file", "post_sha256"), ("comment_file", "comment_sha256"), ("image_file", "image_sha256"),
                     ("job_file", "job_sha256")):
            if f in e:
                p = Path(e[f])
                if not p.is_file():
                    problems.append(f"{e['key']}: {p} missing")
                elif sha256(p) != e[h]:
                    problems.append(f"{e['key']}: {p.name} changed")
    print(json.dumps({"ok": not problems, "problems": problems}, indent=1))
    return 0 if not problems else 1


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
    b.add_argument("--out", required=True)
    b.add_argument("--workbench", required=True)
    b.add_argument("--platform", default="linkedin")
    b.add_argument("--grace-minutes", type=int, default=120)
    v = sub.add_parser("verify")
    v.add_argument("--manifest", required=True)
    v.add_argument("--hash", required=True)
    ap = sub.add_parser("approval")
    ap.add_argument("--state", default="docs/workbench/state.md")
    ap.add_argument("--hash", required=True)
    a = p.parse_args(argv)
    return {"build": build, "verify": verify, "approval": approval}[a.verb](a)


if __name__ == "__main__":
    sys.exit(main())
