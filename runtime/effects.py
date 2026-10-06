#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The external effects of the task runtime: what a skill with a confirmation gate showed at its gate, recovered
from what the run left, and (stage 4, WP-4.8) its execution by code once the person approved its hash.

A skill with a confirmation gate runs up to the gate (limit L16). The pull-request skill writes its payload, exactly
as it shows it, to payload.md in a folder from mktemp -d and states that file's path and sha256 in its reply. The
run's temporary folder comes back inside the run folder (runtime/lab.py, tmp_in_run), and the payload is taken from
there only when it is the file the reply hashed: the reply's text is never taken in its place, and nothing here
picks "the most likely" file.

Public names: recover_payload(reply, tmp_dir, readable), parse_pull_request_payload(text).

Usage (a library): python3 runtime/effects.py --help

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

PAYLOAD_NAME = "payload.md"
CANDIDATES_MAX = 20
PAYLOAD_LINE = re.compile(r"^\s*Payload file:\s*`?(?P<path>[^`]+?)`?\s*,\s*sha256\s*`?(?P<sha>[0-9a-f]{64})`?\s*\.?\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
BASE_HEAD = re.compile(r"^Base ← head:\s*(?P<base>\S+)\s*←\s*(?P<head>\S+)\s*$")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def recover_payload(reply: str, tmp_dir, readable) -> dict:
    """The payload file a skill wrote at its gate: {"recovered": True, "file", "sha256", "text"} or {"recovered":
    False, "why"}. In order: (1) the reply holds exactly one line "Payload file: `<path>`, sha256 `<64 hex>`"; (2) the
    candidates are the regular files named payload.md under tmp_dir, found without following a link and each
    accepted by readable(tmp_dir, rel); none, or more than 20, is not recovered; (3) the chosen one is the candidate
    whose path ends with the stated path's last two parts, else the only candidate whose sha256 is the stated hash;
    (4) its bytes must have the stated hash."""
    lines = [m for m in (PAYLOAD_LINE.match(line) for line in (reply or "").splitlines()) if m]
    if not lines:
        return {"recovered": False, "why": "the reply names no payload file"}
    if len(lines) > 1:
        return {"recovered": False, "why": "the reply names more than one payload file"}
    stated, digest = lines[0].group("path").strip(), lines[0].group("sha")
    if not tmp_dir or not os.path.isdir(tmp_dir) or os.path.islink(tmp_dir):
        return {"recovered": False, "why": "the run left no temporary folder"}
    candidates = []
    for current, folders, files in os.walk(tmp_dir):  # never follows a link to a folder
        folders[:] = sorted(n for n in folders if not os.path.islink(os.path.join(current, n)))
        for name in sorted(files):
            rel = os.path.relpath(os.path.join(current, name), tmp_dir).replace(os.sep, "/")
            if name == PAYLOAD_NAME and readable(tmp_dir, rel):
                candidates.append(rel)
    if not candidates:
        return {"recovered": False, "why": "no payload.md was found under the run's temporary folder"}
    if len(candidates) > CANDIDATES_MAX:
        return {"recovered": False, "why": f"more than {CANDIDATES_MAX} payload.md files under the run's temporary folder"}
    hashes = {}
    for rel in candidates:
        with open(os.path.join(tmp_dir, *rel.split("/")), "rb") as f:
            hashes[rel] = _sha(f.read())
    tail = "/".join(stated.replace("\\", "/").rstrip("/").split("/")[-2:])
    by_path = [rel for rel in candidates if rel == tail or rel.endswith("/" + tail)]
    by_hash = [rel for rel in candidates if hashes[rel] == digest]
    chosen = by_path[0] if len(by_path) == 1 else (by_hash[0] if not by_path and len(by_hash) == 1 else None)
    if chosen is None:
        return {"recovered": False, "why": "no single payload.md under the run's temporary folder is the one the reply names"}
    if hashes[chosen] != digest:
        return {"recovered": False, "why": "the file is not the one the reply hashed"}
    path = os.path.join(tmp_dir, *chosen.split("/"))
    with open(path, "rb") as f:
        data = f.read()
    return {"recovered": True, "file": path, "sha256": digest, "text": data.decode("utf-8", errors="replace")}


def parse_pull_request_payload(text: str):
    """{"repository", "base", "head", "title", "body"} of a payload in the pull-request skill's form, or None. The
    form, line by line: "Repository: ..."; "Base ← head: <base> ← <head>"; optionally "Commits:" and its "- ..."
    lines; "Title: <title>"; "Body:"; then the body, everything after it. One leading and one trailing code-fence
    line are dropped. Anything else is None."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    if lines and FENCE.match(lines[0]):
        lines = lines[1:]
    if lines and FENCE.match(lines[-1]):
        lines = lines[:-1]
    if len(lines) < 4 or not lines[0].startswith("Repository:"):
        return None
    repository = lines[0][len("Repository:"):].strip()
    found = BASE_HEAD.match(lines[1])
    if not repository or not found:
        return None
    i = 2
    if lines[i] == "Commits:":
        i += 1
        while i < len(lines) and lines[i].startswith("- "):
            i += 1
    if i + 1 >= len(lines) or not lines[i].startswith("Title: ") or lines[i + 1] != "Body:":
        return None
    title = lines[i][len("Title: "):].strip()
    body = "\n".join(lines[i + 2:])
    if not title or not body.strip():
        return None
    return {"repository": repository, "base": found.group("base"), "head": found.group("head"), "title": title,
            "body": body}


if __name__ == "__main__":
    print(__doc__.strip())
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
