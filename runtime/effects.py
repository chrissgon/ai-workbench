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

When the person approves the hash of the effect document (effect.json in the run folder, which binds the repository
and the base of the configuration, the head the runtime named, the title and the body the skill showed, and every
file of the change set by its hash), code checks that nothing moved since, makes the one commit through the code
provider (commit-files, with the person's own git and signature) and opens the pull request (open-pr). The runtime
passes the provider no credential: it reads its own. No module of runtime/ runs git commit or git push itself.

Public names: recover_payload(reply, tmp_dir, readable), parse_pull_request_payload(text), EffectError,
document(...), write(run_dir, doc), body(doc, sha256), verify(...), execute(...), provider_call(provider, args[, run]), approval_row(approval, doc).

Usage (a library): python3 runtime/effects.py --help

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import project_config  # noqa: E402  (the same folder: the resolver is loaded from here)

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


# --- the effect: approved by its hash, executed by code (WP-4.8; limits L15, L16, L17) -----------------------------

EFFECT_FILE = "effect.json"
PROVIDER_TIMEOUT = 600


class EffectError(Exception):
    """kind is "deviation" (something moved since the gate), "provider" (the code provider failed), "not-configured"
    or "usage"."""

    def __init__(self, kind: str, reason: str):
        super().__init__(reason)
        self.kind, self.reason = kind, reason


def document(code_cfg: dict, request: dict, payload: dict, changeset: dict, head: str, payload_file_sha256: str) -> dict:
    """The effect document: the exact content the person approves, bound by one hash. repo and base come from the
    project's configuration (code_cfg), never from the payload; head is the branch the runtime named
    (<branch_prefix>request-<id>); title and body are the parsed payload's, as the skill showed them; the files and
    the removed paths are the change set's, each file by its hash."""
    return {"effect": "pull-request", "provider": code_cfg["provider"], "repo": code_cfg["repo"],
            "base": code_cfg["base"], "head": head, "title": payload["title"], "body": payload["body"],
            "commit_message": payload["title"] + "\n", "payload_file_sha256": payload_file_sha256,
            "project_commit": changeset["project_commit"], "changeset_sha256": changeset["sha256"],
            "files": [{"path": f["path"], "sha256": f["sha256"], "executable": bool(f["executable"])}
                      for f in sorted(changeset["files"], key=lambda f: f["path"])],
            "removed": sorted(changeset["removed"])}


def _text(doc: dict) -> bytes:
    return (json.dumps(doc, sort_keys=True, indent=1, ensure_ascii=True) + "\n").encode("ascii")


def write(run_dir: str, doc: dict) -> tuple:
    """Write <run_dir>/effect.json (sorted keys, one-space indent, ASCII escapes, a final newline). Returns (path,
    sha256): the sha256 is the pending decision's payload_sha256, the hash the person types to approve."""
    data = _text(doc)
    path = os.path.join(run_dir, EFFECT_FILE)
    with open(path, "wb") as f:
        f.write(data)
    return path, _sha(data)


def body(doc: dict, sha256: str) -> str:
    """What the person reads before approving: the repository, base and head, the title, the body whole, each file
    with its hash, each removed path, the hash, and the command that approves."""
    lines = ["Code opens this pull request after your approval, and nothing else:", "",
             f"Repository: {doc['repo']}", f"Base ← head: {doc['base']} ← {doc['head']}",
             f"Commit: one commit, made by the code provider with your own git and signature, over {doc['project_commit']}",
             f"Title: {doc['title']}", "Body:", doc["body"].rstrip("\n"), "", "Files:"]
    lines += [f"- {f['path']}" + (" (executable)" if f["executable"] else "") + f" sha256 {f['sha256']}" for f in doc["files"]]
    if doc["removed"]:
        lines += ["Removed:"] + [f"- {rel}" for rel in doc["removed"]]
    lines += ["", f"Hash of this effect: {sha256}",
              "Approve exactly this: python3 runtime/cli.py approve --project <project> --id <this pending decision's id> "
              f"--sha256 {sha256}",
              "Or answer with what to change, or reject it: nothing is sent until you approve."]
    return "\n".join(lines) + "\n"


def verify(effect_file: str, sha256: str, changeset: dict, facts: dict, protected) -> dict:
    """Before execution: the effect file's hash is the approved one; every stored file of the change set still has
    its hash (changeset.load() did it, and the document's files are the change set's); the change set still passes
    changeset.verify_for_commit with the project's versioned paths now and the protected paths accepted now.
    Returns the document. Raises EffectError("deviation")."""
    import changeset as changesets  # noqa: E402  (the same folder; only when an effect is executed)
    try:
        with open(effect_file, "rb") as f:
            data = f.read()
    except OSError as e:
        raise EffectError("deviation", f"the effect file cannot be read: {e.strerror}") from None
    if _sha(data) != sha256:
        raise EffectError("deviation", "the effect file is not the one approved: its hash changed")
    doc = json.loads(data.decode("ascii"))
    stored = [{"path": f["path"], "sha256": f["sha256"], "executable": bool(f["executable"])}
              for f in sorted(changeset["files"], key=lambda f: f["path"])]
    if (doc.get("files") != stored or doc.get("removed") != sorted(changeset["removed"])
            or doc.get("changeset_sha256") != changeset["sha256"]):
        raise EffectError("deviation", "the change set is not the one the effect names")
    try:
        changesets.verify_for_commit(changeset, facts, protected)
    except changesets.ChangesetError as e:
        raise EffectError("deviation", e.reason) from None
    return doc


def provider_call(provider: str, args: list, run=None) -> dict:
    """One verb of the provider script at the path `provider` (the code provider, found by its class in the
    operations layer), started by providers/resolve.py (resolve.invoke: the interpreter its header asks for): the one
    JSON object it printed. `run(argv)` starts the process (a stand-in in tests; _subprocess by default). Raises
    EffectError ("usage", "not-configured" or "provider")."""
    resolve = project_config.resolver(os.path.dirname(HERE))
    try:
        return resolve.invoke(provider, None, args, timeout=PROVIDER_TIMEOUT, run=run or _subprocess)
    except resolve.ProviderCallError as e:
        kind = {"usage": "usage", "not-configured": "not-configured"}.get(e.kind, "provider")
        raise EffectError(kind, f"{args[0]}: {e.reason}") from None


def _subprocess(argv):
    return subprocess.run(argv, capture_output=True, text=True, timeout=PROVIDER_TIMEOUT, check=False)


def execute(doc: dict, changeset_dir: str, work_dir: str, provider: str, key_prefix: str, run=None) -> dict:
    """Run the code provider's verbs, as scripts/runtime_vote.py starts the same verb (the interpreter the script's header asks for, then the verb): the
    runtime passes no credential, the provider reads its own. In order: write the commit message, the title and the
    body into work_dir (a private folder); a dry run of commit-files, whose base commit must be the document's
    project_commit and whose branch must not exist yet (unless the key already committed); commit-files, one commit
    of exactly the change set's files, modes and removals; then, only when it succeeded, open-pr. Each verb has its
    own idempotency key (<key_prefix>-commit, <key_prefix>-pr): approving again after a failure replays what was
    done. Returns {"commit", "pushed", "pull_request": {"number", "url"}, "replayed"}. Raises EffectError."""
    run = run or _subprocess
    os.makedirs(work_dir, mode=0o700, exist_ok=True)
    files = {}
    for name, text in (("message.txt", doc["commit_message"]), ("title.txt", doc["title"] + "\n"), ("body.md", doc["body"])):
        files[name] = os.path.join(work_dir, name)
        with open(files[name], "w", encoding="utf-8") as f:
            f.write(text)
    commit = ["commit-files", "--repo", doc["repo"], "--branch", doc["head"], "--from-branch", doc["base"],
              "--message-file", files["message.txt"]]
    for item in doc["files"]:
        commit += ["--file", f"{item['path']}={os.path.join(changeset_dir, 'files', *item['path'].split('/'))}",
                   "--mode", f"{item['path']}={'755' if item['executable'] else '644'}"]
    for rel in doc["removed"]:
        commit += ["--delete", rel]
    for rel in [item["path"] for item in doc["files"]] + doc["removed"]:
        commit += ["--allow", rel]
    commit += ["--idempotency-key", f"{key_prefix}-commit"]
    seen = provider_call(provider, commit + ["--dry-run"], run)
    if seen.get("existing_status") != "committed":
        if seen.get("base_commit") != doc["project_commit"]:
            raise EffectError("deviation", "the base branch moved since the change was made: it is at "
                                           f"{seen.get('base_commit')}, the change was made against {doc['project_commit']}")
        if seen.get("branch_exists"):
            raise EffectError("deviation", f"the branch {doc['head']} already exists on the remote and is not this request's")
    made = provider_call(provider, commit + ["--confirmed"], run)
    opened = provider_call(provider, ["open-pr", "--repo", doc["repo"], "--head", doc["head"], "--base", doc["base"],
                                      "--title-file", files["title.txt"], "--body-file", files["body.md"],
                                      "--idempotency-key", f"{key_prefix}-pr", "--confirmed"], run)
    return {"commit": made.get("commit"), "pushed": bool(made.get("pushed")),
            "pull_request": {"number": opened.get("number"), "url": opened.get("url")},
            "replayed": bool(made.get("replayed")) and bool(opened.get("replayed"))}


def approval_row(approval: dict, doc: dict) -> list:
    """The generated copy of an approval for the state file's ## Approvals table (contracts/state.md): Scope, What,
    Payload hash, Approved, Expires, Status."""
    what = f"pull request {doc['head']} into {doc['base']} of {doc['repo']}: {doc['title']}"
    clean = lambda text: " ".join(str(text).replace("|", "/").split())
    return [approval["scope"], clean(what), f"sha256:{approval['payload_sha256']}", approval["approved_at"][:10],
            approval.get("expires_at") or "after execution", approval["status"]]


if __name__ == "__main__":
    print(__doc__.strip())
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
