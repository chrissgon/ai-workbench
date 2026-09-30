#!/usr/bin/env python3
"""Publish the weekly vote post at its slot time, then record it in the profile repository's vote files.

Usage (built by scripts/runtime.py after the person's approval, run by the scheduler, never by hand):
  python3 vote_job.py --key <key> --round YYYY-MM-DD --date YYYY-MM-DD --lang EN --title "<topic>" \
      --repo <owner>/<name> --branch <branch> --platform linkedin --post-file post.txt \
      [--comment-file comment.txt] [--image post.png --image-path assets/posts/<key>.png] \
      --publisher linkedin.py --resolver resolver.py --vcs github.py \
      --vote-update vote_update.py --vote-state vote_state.py --work <folder>

Steps, each only when the one before it succeeded:
  1. publish the post (with its first comment and image) with the publisher and the idempotency key <key>;
  2. read data/pick.json, data/pick-queue.json and data/posts.json from the repository (read only), as they
     are now: the profile's own workflow may have committed since the approval;
  3. compute the recorded files with vote_update.py --record-post (post_url on the round, the post in
     posts.json); nothing else changes;
  4. commit them, and the image, with the vcs provider's commit-files, key <key>-record, only to
     data/pick.json, data/posts.json and assets/posts/*.

Every file argument is a verified copy in the scheduler's job folder (the scheduler swaps the paths), so
vote_update.py and vote_state.py sit in one folder and the import between them works. The person approved
all of it at once (scripts/runtime.py approve); a failure after the post went out leaves the post published
and prints what to record by hand.

Prints JSON on stdout, diagnostics on stderr. Exit 0 all done, 1 a step failed, 2 usage error.
Standard library only; the providers run through uv.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
ALLOW = ["data/pick.json", "data/posts.json", "assets/posts/*"]
TIMEOUT = 600


def log(message: str) -> None:
    print(message, file=sys.stderr)


def call(cmd: list, timeout: int = TIMEOUT) -> tuple[int, dict, str]:
    try:
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, {}, f"timeout after {timeout} s"
    except OSError as e:
        return 127, {}, str(e)
    try:
        out = json.loads(r.stdout) if r.stdout.strip() else {}
    except json.JSONDecodeError:
        out = {}
    return r.returncode, out, r.stderr.strip()[-600:]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("--key", "--round", "--date", "--lang", "--title", "--repo", "--branch", "--post-file",
                 "--publisher", "--resolver", "--vcs", "--vote-update", "--vote-state", "--work"):
        p.add_argument(name, required=True)
    p.add_argument("--platform", default="linkedin")
    p.add_argument("--comment-file")
    p.add_argument("--image")
    p.add_argument("--image-path")
    a = p.parse_args(argv)
    if not REPO.match(a.repo):
        log(f"error: --repo {a.repo!r} is not <owner>/<name>")
        return 2
    if bool(a.image) != bool(a.image_path):
        log("error: --image and --image-path go together")
        return 2
    if Path(a.vote_update).resolve().parent != Path(a.vote_state).resolve().parent:
        log("error: vote_update.py and vote_state.py must be in one folder")
        return 2
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True, mode=0o700)
    result = {"key": a.key, "round": a.round, "published": False, "post_url": None, "recorded": False}

    pub = ["uv", "run", a.publisher, "publish", "--platform", a.platform, "--text-file", a.post_file,
           "--idempotency-key", a.key]
    if a.comment_file:
        pub += ["--first-comment-file", a.comment_file]
    if a.image:
        pub += ["--media", a.image]
    code, out, err = call(pub + ["--confirmed"])
    if code != 0 or not out.get("post_url"):
        log(f"publish exited {code}: {err}")
        result["error"] = f"publish failed ({code}); nothing was recorded"
        print(json.dumps(result, indent=1))
        return 1
    result.update(published=True, post_url=out["post_url"], replayed=out.get("replayed"))

    data = work / "current"
    data.mkdir(exist_ok=True, mode=0o700)
    for name in ("pick.json", "pick-queue.json", "posts.json"):
        code, out, err = call(["uv", "run", a.vcs, "read-file", "--repo", a.repo, "--path", f"data/{name}",
                               "--ref", a.branch], timeout=120)
        if code != 0 or "content" not in out:
            return finish(result, f"read-file data/{name} exited {code}: {err}")
        (data / name).write_text(out["content"], encoding="utf-8")

    new = work / "new"
    upd = [sys.executable, a.vote_update, "--pick", data / "pick.json", "--queue", data / "pick-queue.json",
           "--posts", data / "posts.json", "--record-post", "--round", a.round, "--post-url", result["post_url"],
           "--date", a.date, "--lang", a.lang, "--title", a.title, "--out", new]
    if a.image_path:
        upd += ["--image", a.image_path]
    code, out, err = call(upd, timeout=60)
    if code != 0:
        return finish(result, f"vote_update.py exited {code}: {err}")
    files = [f"{c['path']}={c['file']}" for c in out.get("changed", [])]
    if a.image:
        files.append(f"{a.image_path}={a.image}")
    if not files:
        result["recorded"] = True
        result["note"] = "the vote files already held this post"
        print(json.dumps(result, indent=1))
        return 0
    message = work / "message.txt"
    message.write_text(f"vote: record the post of round {a.round}\n\n{result['post_url']}\n", encoding="utf-8")
    commit = ["uv", "run", a.vcs, "commit-files", "--repo", a.repo, "--branch", a.branch,
              "--message-file", message, "--idempotency-key", f"{a.key}-record", "--confirmed"]
    for f in files:
        commit += ["--file", f]
    for g in ALLOW:
        commit += ["--allow", g]
    code, out, err = call(commit)
    if code != 0:
        return finish(result, f"commit-files exited {code}: {err}")
    result.update(recorded=True, commit=out.get("commit"), unchanged=out.get("unchanged"))
    print(json.dumps(result, indent=1))
    return 0


def finish(result: dict, error: str) -> int:
    """The post is out but the record failed: say what to record by hand."""
    log(error)
    result["error"] = error
    result["by_hand"] = (f"record post_url {result['post_url']} on round {result['round']} with "
                         "mkt-vote-round's vote_update.py --record-post, then commit data/pick.json and data/posts.json")
    print(json.dumps(result, indent=1))
    return 1


if __name__ == "__main__":
    sys.exit(main())
