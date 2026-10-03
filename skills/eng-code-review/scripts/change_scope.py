#!/usr/bin/env python3
"""Measure a code change so the review works from numbers, not impressions.

Usage:
  python3 change_scope.py --repo <dir> --range <git-range> [--touches "<a>, <b>"]
  python3 change_scope.py --repo <dir> --worktree           [--touches "<a>, <b>"]
  python3 change_scope.py --repo <dir> --staged             [--touches "<a>, <b>"]
  python3 change_scope.py --patch <file> [--repo <dir>]     [--touches "<a>, <b>"]

Options:
  --range <r>       anything `git diff` accepts: HEAD~1, main...HEAD, abc123..def456
  --worktree        every change against HEAD, staged or not, plus untracked files
  --staged          the index against HEAD
  --patch <file>    a unified diff file (a pull request downloaded as .patch); no git needed
  --touches <list>  comma-separated tokens from the task's "Touches:" line; changed files whose
                    path contains none of them are listed under outside_touches
  --max-files <n>   files in the read-line-by-line group above which the change is "large" (20)
  --max-lines <n>   added+deleted lines in that group above which the change is "large" (800)
  --help            this text

Prints one JSON object to stdout with:
  source            what was measured
  files[]           path, old_path, status (added|modified|deleted|renamed|renamed+modified|binary),
                    kind (source|test|config|docs|generated|lockfile|asset), added, deleted
  totals            files, added, deleted, pure_renames, by_kind
  review_groups     read_line_by_line, verify_rename_only, verify_deleted, skim
  large             true when the read group exceeds --max-files or --max-lines
  dependencies      package.json sections diffed exactly when both sides are readable;
                    manifest_lines for every other manifest (added/removed lines)
  markers[]         path, line, kind (debug|skip-test|lint-suppress|todo|secret-suspect), text;
                    secret-suspect markers also carry rule (the credential format, or
                    "credential assignment")
  tests_touched[]   changed files classified as tests
  outside_touches[] changed files matching no --touches token (empty when --touches is absent)
Secrets are never printed: every quoted line goes through redact.py (the same formats as the
workbench's security scan), and a secret-suspect marker's text is masked entirely, keeping only
the shape of the line (api_key = "<redacted>"). Quote that masked text; never the raw line.
A --range whose sides start with "-" or are not commits is refused before git sees it.
Diagnostics go to stderr.
Exit codes: 0 ok, 1 git or file error, 2 usage error, 3 the change is empty.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from redact import ASSIGN_RE, mask_secret_line, redact, token_label  # noqa: E402

LOCKFILES = {"package-lock.json", "bun.lock", "bun.lockb", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
             "uv.lock", "Cargo.lock", "Gemfile.lock", "composer.lock", "go.sum", "Pipfile.lock"}
MANIFESTS = {"package.json", "requirements.txt", "requirements-dev.txt", "pyproject.toml", "go.mod",
             "Cargo.toml", "Gemfile", "composer.json", "Pipfile"}
ASSET_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".woff", ".woff2", ".ttf", ".otf",
             ".pdf", ".mp4", ".mp3"}
DOC_EXT = {".md", ".mdx", ".rst", ".txt", ".adoc"}
CONFIG_EXT = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env", ".editorconfig"}
CONFIG_NAMES = {"Dockerfile", "Makefile", "Procfile", "LICENSE", ".gitignore", ".eslintrc", ".eslintignore",
                ".prettierrc", ".npmrc", ".nvmrc"}
CONFIG_RE = re.compile(r"(^|/)([a-zA-Z0-9.-]+\.config\.[a-z]+|tsconfig[^/]*\.json|\.[a-z]+rc(\.[a-z]+)?)$")
TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs", "e2e", "evals"}
TEST_FILE_RE = re.compile(r"(\.(test|spec)\.[a-z]+$)|(_test\.go$)|(^test_.*\.py$)|(_test\.py$)|(_spec\.rb$)|(Tests?\.(java|cs)$)")
GENERATED_RE = re.compile(r"(\.min\.(js|css)$)|(\.snap$)|(\.generated\.)|(__generated__/)|(\.pb\.go$)|(^|/)(dist|build|\.output|\.nuxt|\.next|coverage)/")
SCRIPT_DIR_RE = re.compile(r"(^|/)(scripts|bin|cli|tools)/")

MARKERS = [
    ("debug", re.compile(r"\bconsole\.(log|debug|trace)\(|\bdebugger\b|\bbinding\.pry\b|\bvar_dump\(|\bdd\(")),
    ("skip-test", re.compile(r"\.(only|skip)\(|\b(xit|xdescribe|fit|fdescribe|xtest)\(|@pytest\.mark\.skip|pytest\.skip\(|@unittest\.skip|skipTest\(|\bt\.Skip\(")),
    ("lint-suppress", re.compile(r"eslint-disable|@ts-ignore|@ts-nocheck|@ts-expect-error|#\s*noqa|#\s*type:\s*ignore|#\s*nosec|rubocop:disable|//\s*nolint")),
    ("todo", re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")),
    ("secret-suspect", re.compile(
        r"(?i)(api[_-]?key|secret|token|passw(or)?d|private[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]"
        r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(sk|pk|rk)_(live|test)_[0-9A-Za-z]{10,}|\bAKIA[0-9A-Z]{16}\b"
        r"|\bghp_[0-9A-Za-z]{30,}|\bxox[baprs]-[0-9A-Za-z-]{10,}|\beyJ[A-Za-z0-9_-]{20,}\.eyJ")),
]
PY_PRINT_RE = re.compile(r"^\s*print\(")
SECRET_SAFE_RE = re.compile(r"process\.env|import\.meta\.env|os\.environ|getenv|ENV\[|example|placeholder|<[^>]+>|\$\{|your[_-]")


def err(msg):
    print(msg, file=sys.stderr)


def git(repo, *args):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout


def classify(path):
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()
    parts = path.split("/")
    if name in LOCKFILES:
        return "lockfile"
    if GENERATED_RE.search(path):
        return "generated"
    if ext in ASSET_EXT:
        return "asset"
    if ext in DOC_EXT:
        return "docs"
    if any(p in TEST_DIRS for p in parts[:-1]) or TEST_FILE_RE.search(name):
        return "test"
    if name in CONFIG_NAMES or name in MANIFESTS or CONFIG_RE.search(path) or ext in CONFIG_EXT:
        return "config"
    return "source"


# ---------- git sources ----------

def parse_name_status(text):
    toks = text.split("\0")
    out, i = {}, 0
    while i < len(toks) and toks[i] != "":
        st = toks[i]
        if st[0] in "RC":
            old, new = toks[i + 1], toks[i + 2]
            i += 3
            sim = int(st[1:]) if st[1:].isdigit() else 0
            status = "renamed" if sim == 100 else "renamed+modified"
            out[new] = {"path": new, "old_path": old, "status": status}
        else:
            path = toks[i + 1]
            i += 2
            status = {"A": "added", "M": "modified", "D": "deleted", "T": "modified"}.get(st[0], "modified")
            out[path] = {"path": path, "old_path": None, "status": status}
    return out


def parse_numstat(text):
    toks = text.split("\0")
    out, i = {}, 0
    while i < len(toks) and toks[i] != "":
        a, d, path = toks[i].split("\t", 2)
        if path == "":
            old, new = toks[i + 1], toks[i + 2]
            i += 3
            path = new
        else:
            i += 1
        binary = a == "-"
        out[path] = {"added": 0 if binary else int(a), "deleted": 0 if binary else int(d), "binary": binary}
    return out


def parse_unified(text, line_sink):
    """Walk a unified diff; call line_sink(path, lineno, text) for every added line.
    Return per-path {added, deleted, header info} for patch mode."""
    files, cur, new_ln = {}, None, 0
    for raw in text.splitlines():
        if raw.startswith("diff --git "):
            m = re.match(r'diff --git "?a/(.*?)"? "?b/(.*?)"?$', raw)
            cur = {"path": m.group(2) if m else raw, "old_path": None, "status": "modified",
                   "added": 0, "deleted": 0, "binary": False, "similarity": None}
            files[cur["path"]] = cur
            new_ln = 0
            continue
        if cur is None:
            continue
        if raw.startswith("rename from "):
            cur["old_path"] = raw[len("rename from "):]
        elif raw.startswith("rename to "):
            new = raw[len("rename to "):]
            files.pop(cur["path"], None)
            cur["path"] = new
            files[new] = cur
        elif raw.startswith("similarity index "):
            cur["similarity"] = int(raw.split()[2].rstrip("%"))
        elif raw.startswith("new file mode"):
            cur["status"] = "added"
        elif raw.startswith("deleted file mode"):
            cur["status"] = "deleted"
        elif raw.startswith("Binary files"):
            cur["binary"] = True
        elif raw.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            new_ln = int(m.group(1)) if m else 0
        elif raw.startswith("+++") or raw.startswith("---"):
            continue
        elif raw.startswith("+"):
            cur["added"] += 1
            line_sink(cur["path"], new_ln, raw[1:])
            new_ln += 1
        elif raw.startswith("-"):
            cur["deleted"] += 1
        elif raw.startswith(" "):
            new_ln += 1
    for f in files.values():
        if f["old_path"]:
            f["status"] = "renamed" if f["similarity"] == 100 and f["added"] == 0 and f["deleted"] == 0 else "renamed+modified"
    return files


def split_range(rng):
    """(base, head, separator) of a range; an empty side means HEAD, head None means the worktree."""
    for sep in ("...", ".."):
        if sep in rng:
            a, b = rng.split(sep, 1)
            return a or "HEAD", b or "HEAD", sep
    return rng, None, ""


def check_range(repo, rng):
    """Refuse a range git could read as an option (--output=, --upload-pack=) or that names no commit."""
    a, b, _ = split_range(rng)
    for side in (a, b):
        if side is None:
            continue
        if not side or side.startswith("-") or any(c.isspace() or c == "\0" for c in side):
            raise ValueError(f"--range side {side!r} is not a revision")
        p = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "--quiet", "--end-of-options",
                            side + "^{commit}"], capture_output=True, text=True)
        if p.returncode != 0:
            raise ValueError(f"--range side {side!r} is not a commit in {repo}")


def sides_for(mode, rng, repo):
    if mode == "worktree":
        return "HEAD", None
    if mode == "staged":
        return "HEAD", ":"
    a, b, sep = split_range(rng)
    if sep == "...":
        return git(repo, "merge-base", "--end-of-options", a, b).strip(), b
    return a, b


def read_side(repo, ref, path):
    """ref None = working file; ':' = index; else a commit."""
    try:
        if ref is None:
            with open(os.path.join(repo, path), encoding="utf-8", errors="replace") as f:
                return f.read()
        return git(repo, "show", "--end-of-options", f"{ref}:{path}")
    except (OSError, RuntimeError):
        return None


def diff_args(mode, rng):
    """Revision arguments for git diff: options end before the range, paths start after it."""
    return {"worktree": ["--end-of-options", "HEAD", "--"], "staged": ["--cached", "--"],
            "range": ["--end-of-options", rng, "--"]}[mode]


def collect_git(repo, mode, rng):
    args = diff_args(mode, rng)
    ns = parse_name_status(git(repo, "diff", "-M", "--name-status", "-z", *args))
    num = parse_numstat(git(repo, "diff", "-M", "--numstat", "-z", *args))
    files = {}
    for path, meta in ns.items():
        n = num.get(path, {"added": 0, "deleted": 0, "binary": False})
        files[path] = {**meta, "added": n["added"], "deleted": n["deleted"], "binary": n["binary"]}
    markers = []
    parse_unified(git(repo, "diff", "-M", "-U0", *args), lambda p, ln, t: scan_line(markers, p, ln, t))
    if mode == "worktree":
        for path in git(repo, "ls-files", "--others", "--exclude-standard", "-z").split("\0"):
            if not path or path in files:
                continue
            full = os.path.join(repo, path)
            if os.path.isdir(full):
                continue
            try:
                with open(full, encoding="utf-8", errors="replace") as f:
                    lines = f.read().splitlines()
                binary = False
            except OSError:
                lines, binary = [], True
            files[path] = {"path": path, "old_path": None, "status": "added", "added": len(lines),
                           "deleted": 0, "binary": binary}
            for i, t in enumerate(lines, 1):
                scan_line(markers, path, i, t)
    base, head = sides_for(mode, rng, repo)
    return files, markers, (lambda p, side: read_side(repo, base if side == "base" else head, p)), f"{mode} {rng or ''}".strip()


def collect_patch(patch_path):
    with open(patch_path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    markers = []
    files = parse_unified(text, lambda p, ln, t: scan_line(markers, p, ln, t))
    return files, markers, (lambda p, side: None), f"patch {patch_path}"


# ---------- analysis ----------

def scan_line(markers, path, lineno, text):
    kind = classify(path)
    if kind in ("lockfile", "generated", "asset"):
        return
    label = token_label(text)
    for name, rx in MARKERS:
        if name == "secret-suspect":
            if label or ((rx.search(text) or ASSIGN_RE.search(text)) and not SECRET_SAFE_RE.search(text)):
                markers.append({"path": path, "line": lineno, "kind": name, "rule": label or "credential assignment",
                                "text": mask_secret_line(text)})
        elif rx.search(text):
            markers.append({"path": path, "line": lineno, "kind": name, "text": redact(text)})
    if path.endswith(".py") and kind == "source" and not SCRIPT_DIR_RE.search(path) and PY_PRINT_RE.search(text):
        markers.append({"path": path, "line": lineno, "kind": "debug", "text": redact(text)})


def package_json_diff(base_text, head_text):
    try:
        base = json.loads(base_text) if base_text else {}
        head = json.loads(head_text) if head_text else {}
    except json.JSONDecodeError as e:
        return {"error": f"package.json is not valid JSON on one side: {e}"}
    out = {"added": {}, "removed": {}, "changed": {}}
    # A version can be a URL with a token in it (git+https://user:token@host/...).
    clean = lambda v: redact(v, limit=400) if isinstance(v, str) else v
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        b, h = base.get(section, {}) or {}, head.get(section, {}) or {}
        for k in sorted(set(b) | set(h)):
            key = f"{section}:{k}"
            if k not in b:
                out["added"][key] = clean(h[k])
            elif k not in h:
                out["removed"][key] = clean(b[k])
            elif b[k] != h[k]:
                out["changed"][key] = [clean(b[k]), clean(h[k])]
    return out


def dependencies(files, read, patch_text):
    out = {}
    for path in files:
        name = os.path.basename(path)
        if name not in MANIFESTS:
            continue
        if name == "package.json":
            base, head = read(path, "base"), read(path, "head")
            if base is not None or head is not None:
                out[path] = package_json_diff(base, head)
                continue
        out[path] = {"manifest_lines": added_removed_lines(path, patch_text)}
    return out


def added_removed_lines(path, patch_text):
    added, removed, inside = [], [], False
    for raw in patch_text.splitlines():
        if raw.startswith("diff --git "):
            inside = raw.rstrip().endswith("b/" + path) or raw.rstrip().endswith('b/' + path + '"')
            continue
        if not inside or raw.startswith("+++") or raw.startswith("---"):
            continue
        t = redact(raw[1:], limit=400)
        if raw.startswith("+") and t and t not in "{}[],":
            added.append(t)
        elif raw.startswith("-") and t and t not in "{}[],":
            removed.append(t)
    return {"added": added, "removed": removed}


VALUE_FLAGS = ("--repo", "--range", "--patch", "--touches", "--max-files", "--max-lines")


def main(argv):
    if not argv:
        err(__doc__)
        err("Error: no arguments. See --help.")
        return 2
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    repo, mode, rng, patch, touches = ".", None, None, None, []
    max_files, max_lines = 20, 800
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in VALUE_FLAGS and i + 1 >= len(argv):
            err(f"Error: {a} needs a value. See --help."); return 2
        if a in ("--max-files", "--max-lines"):
            try:
                n = int(argv[i + 1])
            except ValueError:
                err(f"Error: {a} needs a whole number, got {argv[i + 1]!r}. See --help."); return 2
            if a == "--max-files": max_files = n
            else: max_lines = n
            i += 2
        elif a == "--repo": repo = argv[i + 1]; i += 2
        elif a == "--range": mode, rng = "range", argv[i + 1]; i += 2
        elif a == "--worktree": mode = "worktree"; i += 1
        elif a == "--staged": mode = "staged"; i += 1
        elif a == "--patch": mode, patch = "patch", argv[i + 1]; i += 2
        elif a == "--touches": touches = [t.strip().lower() for t in argv[i + 1].split(",") if t.strip()]; i += 2
        else:
            err(f"Error: unknown option '{a}'. See --help."); return 2
    if mode is None:
        err("Error: one of --range, --worktree, --staged or --patch is required. See --help."); return 2
    try:
        if mode == "patch":
            if not os.path.isfile(patch):
                err(f"Error: patch file not found: {patch}"); return 1
            files, markers, read, source = collect_patch(patch)
            with open(patch, encoding="utf-8", errors="replace") as f:
                patch_text = f.read()
        else:
            if mode == "range":
                check_range(repo, rng)
            files, markers, read, source = collect_git(repo, mode, rng)
            patch_text = git(repo, "diff", "-M", *diff_args(mode, rng))
    except ValueError as e:
        err(f"Error: refused: {e}"); return 2
    except RuntimeError as e:
        err(f"Error: {e}"); return 1
    if not files:
        err("Nothing to review: the change is empty."); return 3

    rows = []
    for path in sorted(files):
        f = files[path]
        kind = classify(path)
        status = "binary" if f.get("binary") else f["status"]
        rows.append({"path": path, "old_path": f.get("old_path"), "status": status, "kind": kind,
                     "added": f["added"], "deleted": f["deleted"]})
    by_kind = {}
    for r in rows:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    read_group = [r["path"] for r in rows if r["kind"] in ("source", "test", "config") and r["status"] not in ("renamed", "deleted")]
    deleted_group = [r["path"] for r in rows if r["status"] == "deleted"]
    rename_group = [f'{r["old_path"]} -> {r["path"]}' for r in rows if r["status"] == "renamed"]
    skim_group = [r["path"] for r in rows if r["kind"] in ("docs", "lockfile", "generated", "asset") and r["status"] not in ("renamed", "deleted")]
    read_lines = sum(r["added"] + r["deleted"] for r in rows if r["path"] in set(read_group))
    outside = []
    if touches:
        for r in rows:
            hay = (r["path"] + " " + (r["old_path"] or "")).lower()
            if not any(t in hay for t in touches):
                outside.append(r["path"])
    result = {
        "source": source,
        "files": rows,
        "totals": {"files": len(rows), "added": sum(r["added"] for r in rows), "deleted": sum(r["deleted"] for r in rows),
                   "pure_renames": len(rename_group), "by_kind": by_kind},
        "review_groups": {"read_line_by_line": read_group, "verify_rename_only": rename_group,
                          "verify_deleted": deleted_group, "skim": skim_group},
        "large": len(read_group) > max_files or read_lines > max_lines,
        "dependencies": dependencies(files, read, patch_text),
        "markers": markers,
        "tests_touched": [r["path"] for r in rows if r["kind"] == "test"],
        "outside_touches": outside,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
