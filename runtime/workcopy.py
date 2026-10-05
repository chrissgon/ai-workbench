#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""What enters a run copy, and what comes back from it: the limits of the task runtime that decide which files
of a project a run sees (L1 to L6) and which files a run leaves come back (L7, L8, L12, L14).

What enters (entering()):
  L1  every run starts from a new copy, with the skill staged again: the lab facade makes a new run root and
      stages the skill on every attempt (runtime/lab.py); nothing here keeps a copy between runs
  L2  a run without the web sees the versioned files (git ls-files, with the person's git), the project's
      documents and state file under docs/, and the machine files the skill declares. No other file outside
      git. The store, the runtime's data and its configuration never
  L3  a run with the web sees only the artifacts its skill declares (strict form: no allowance for web and
      code together is built)
  L4  a path with a part that carries a tool's settings never enters, at any depth
  L5  the project's AGENTS.md enters only when the skill declares it, without the two lines the container
      cannot serve; when a protected path covers it and the skill is not of a code area, only its workbench
      section enters
  L6  no credential enters: a credential file by its name, a file too large to scan, a file whose text holds
      what looks like a credential

Every file left out is listed with its reason, except a path inside a folder the path rule drops.

Usage (a library): python3 runtime/workcopy.py --help

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import fnmatch
import hashlib
import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import path_rule  # noqa: E402  (the same folder)
import skill_meta  # noqa: E402

CODE_AREAS = ("engineering", "delivery")
SECTION_START = "<!-- workbench:start -->"
SECTION_END = "<!-- workbench:end -->"
REMOVED_OPENINGS = ("Recording a use, where no hook does it:", "Skill check:")
CREDENTIAL_NAMES = (".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*", ".netrc", ".npmrc",
                    ".pypirc")
CREDENTIAL_NAME_EXAMPLES = (".env.example", ".env.sample", ".env.template")
SCAN_MAX = 5 * 1024 * 1024
AGENTS_MD = "AGENTS.md"
# The credential formats the security scan and the skills' scripts share; loaded from this checkout, never from
# a root a test points elsewhere.
REDACT = os.path.join(os.path.dirname(HERE), "scripts", "redact.py")
LIST_NUMBER = re.compile(r"^\d+\.\s+")
UNSAFE_VALUE = re.compile(r"[<>{}$*]")


class CopyError(Exception):
    """The copy could not be built (git failed on a git checkout, the prepared folder cannot be written)."""


def _redact():
    name = "workbench_runtime_redact"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, REDACT)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def credential_findings(text: str) -> list:
    """The labels of what looks like a credential in a text, one per line that has one; empty when none. Never
    the value."""
    redact = _redact()
    found = []
    for line in (text or "").splitlines():
        label = redact.token_label(line)
        if label is None:
            for value_label, value in redact.secret_values(line):
                if any(c.isdigit() for c in value) and not UNSAFE_VALUE.search(value):
                    label = value_label
                    break
        if label is not None:
            found.append(label)
    return found


def agents_md_for_run(text: str, mode: str) -> tuple:
    """(text for the run, removed): the project's AGENTS.md without the two lines the container cannot serve;
    with mode "section", only the workbench section. removed lists {"line", "after"} in order."""
    # Leaves at the change of reference model (docs/backlog.md, T23): the two lines leave the copy in its base
    # commit; with a model that does not need them hidden, the file enters as it is.
    lines = (text or "").splitlines(keepends=True)
    bare = [line.rstrip("\r\n") for line in lines]
    start = bare.index(SECTION_START) if SECTION_START in bare else None
    end = None
    if start is not None:
        end = next((i for i in range(start + 1, len(bare)) if bare[i] == SECTION_END), None)
    if start is None or end is None:
        start = end = None
    if mode == "section" and start is None:
        return "", []
    kept, removed = [], []
    for i, line in enumerate(lines):
        inside = start is not None and start <= i <= end
        if mode == "section" and not inside:
            continue
        if inside and LIST_NUMBER.sub("", bare[i], count=1).startswith(REMOVED_OPENINGS):
            removed.append({"line": line, "after": kept[-1] if kept else None})
            continue
        kept.append(line)
    return "".join(kept), removed


def agents_md_restored(text: str, removed) -> str:
    """The inverse of agents_md_for_run on the way back: each removed line goes back after the line it followed."""
    lines = (text or "").splitlines(keepends=True)
    position, previous = 0, object()
    for item in removed:
        after = item["after"]
        if after == previous:
            at = position  # removed lines that were next to each other go back next to each other
        elif after is None:
            at = 0
        else:
            found = next((k for k in range(position, len(lines)) if lines[k] == after), None)
            at = len(lines) if found is None else found + 1
        lines.insert(at, item["line"])
        position, previous = at + 1, after
    return "".join(lines)


def _sha256(path: str):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _walk(project: str, folder: str) -> list:
    """Every path relative to the project under one folder of it, without following a link; links are listed
    too, so that the rules can name them."""
    out = []
    top = os.path.join(project, folder)
    if not os.path.isdir(top) or os.path.islink(top):
        return out
    for current, names, files in os.walk(top):
        names[:] = sorted(n for n in names if not os.path.islink(os.path.join(current, n)))
        links = [n for n in os.listdir(current) if os.path.islink(os.path.join(current, n)) and n not in files]
        for name in sorted(set(files) | set(links)):
            out.append(os.path.relpath(os.path.join(current, name), project).replace(os.sep, "/"))
    return out


def _versioned(project: str) -> tuple:
    """(paths git tracks, None) or ([], the left_out entry) when the project is not a git checkout."""
    if not os.path.exists(os.path.join(project, ".git")):
        return [], {"path": ".", "reason": "the project is not a git checkout: no versioned file enters"}
    try:
        done = subprocess.run(["git", "-C", project, "ls-files", "-z"], capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise CopyError(f"git ls-files failed in {project}: {e}") from None
    if done.returncode != 0:
        raise CopyError(f"git ls-files failed in {project}: {done.stderr.decode('utf-8', 'replace').strip()}")
    return [p for p in done.stdout.decode("utf-8", "surrogateescape").split("\0") if p], None


def _inside(project: str, rel: str) -> bool:
    real = os.path.realpath(os.path.join(project, *rel.split("/")))
    return real.startswith(project + os.sep)


def _under(real: str, folder: str) -> bool:
    return real == folder or real.startswith(folder + os.sep)


def _never(project: str, rel: str, declared, cfg: dict, settings_names) -> str | None:
    """The reason a candidate never enters, by rules (a) to (h) of the plan; "" for a silent one (a dropped
    folder); None when it may enter as far as these rules go."""
    source = os.path.join(project, *rel.split("/"))
    real = os.path.realpath(source)
    parts = rel.split("/")
    if rel == path_rule.CONFIG:
        return "the runtime's configuration never enters a run"
    if real == cfg["store_db"] or _under(real, cfg["data_dir"]):
        return "the store and the runtime's data never enter a run"
    if os.path.islink(source) or not os.path.isfile(source) or not _inside(project, rel):
        return "a link, or outside the project"
    if any(p in settings_names for p in parts):
        return "a tool's configuration"
    if any(p in path_rule.DROPPED_DIRS for p in parts):
        return ""
    if rel.startswith(path_rule.LOCAL_DIR) and not skill_meta.matches(declared, rel):
        return "work data the skill does not declare"
    if rel == AGENTS_MD and AGENTS_MD not in declared:
        return "the skill does not declare it"
    name = parts[-1]
    if any(fnmatch.fnmatchcase(name, p) for p in CREDENTIAL_NAMES) and name not in CREDENTIAL_NAME_EXAMPLES:
        return "a credential file by its name"
    return None


def _scan(data: bytes) -> str | None:
    if len(data) > SCAN_MAX:
        return "too large to scan for credentials"
    found = credential_findings(data.decode("utf-8", errors="replace"))
    if found:
        return f"holds what looks like a credential ({', '.join(sorted(set(found)))})"
    return None


def entering(project: str, meta: dict, *, web: bool, cfg: dict, settings_names, prepared_dir: str) -> dict:
    """What one run sees of the project. Returns {"files": [(source, rel)], "base": {rel: sha256}, "left_out":
    [{"path", "reason"}], "kind": "artifacts" or "general", "agents_md": None, "whole" or "section"}.

    meta is skill_meta.declared() of the skill; cfg is project_config.load() of the project; settings_names
    is lab.settings_names(); prepared_dir is a private folder for files written for this run only."""
    project = os.path.realpath(project)
    declared = list(dict.fromkeys(meta["inputs"] + meta["outputs"] + meta["updates"]))
    settings_names = set(settings_names)
    kind = "artifacts" if web else "general"
    left_out, candidates = [], []
    if kind == "artifacts":
        for folder in ("docs", path_rule.LOCAL_DIR.rstrip("/")):
            candidates += [rel for rel in _walk(project, folder) if skill_meta.matches(declared, rel)]
    else:
        versioned, note = _versioned(project)
        if note:
            left_out.append(note)
        candidates += versioned
        for rel in _walk(project, "docs"):
            cls = path_rule.classify(rel)
            if cls in ("document", "state") or (cls == "machine" and skill_meta.matches(declared, rel)):
                candidates.append(rel)
            elif rel == path_rule.CONFIG or os.path.islink(os.path.join(project, *rel.split("/"))):
                candidates.append(rel)  # listed with its reason, so that the person sees it was kept out
        candidates += _walk(project, path_rule.LOCAL_DIR.rstrip("/"))
    files, base = [], {}
    for rel in sorted(set(candidates)):
        if rel == AGENTS_MD and AGENTS_MD in declared:
            continue  # rule 5, below
        reason = _never(project, rel, declared, cfg, settings_names)
        if reason is None:
            source = os.path.join(project, *rel.split("/"))
            try:
                with open(source, "rb") as f:
                    data = f.read(SCAN_MAX + 1)
            except OSError as e:
                reason = f"cannot be read: {e.strerror}"
            else:
                reason = _scan(data)
        if reason is None:
            files.append((source, rel))
            base[rel] = _sha256(source)
        elif reason:
            left_out.append({"path": rel, "reason": reason})
    agents_md = None
    source = os.path.join(project, AGENTS_MD)
    if AGENTS_MD in declared and os.path.lexists(source):
        reason = _never(project, AGENTS_MD, declared, cfg, settings_names)
        if reason is None:
            protected = any(fnmatch.fnmatchcase(AGENTS_MD, glob) for glob in cfg.get("protected_paths") or [])
            mode = "section" if protected and meta.get("area") not in CODE_AREAS else "whole"
            with open(source, encoding="utf-8", errors="replace") as f:
                text, _removed = agents_md_for_run(f.read(), mode)  # the removed lines stay in memory only
            reason = "protected, and it has no workbench section" if not text else _scan(text.encode("utf-8"))
        if reason:
            left_out.append({"path": AGENTS_MD, "reason": reason})
        else:
            prepared = os.path.join(prepared_dir, AGENTS_MD)
            try:
                os.makedirs(prepared_dir, mode=0o700, exist_ok=True)
                with open(prepared, "w", encoding="utf-8") as f:
                    f.write(text)
            except OSError as e:
                raise CopyError(f"the prepared folder {prepared_dir} cannot be written: {e.strerror}") from None
            files.append((prepared, AGENTS_MD))
            base[AGENTS_MD] = _sha256(source)
            agents_md = mode
    files.sort(key=lambda item: item[1])
    return {"files": files, "base": base, "left_out": left_out, "kind": kind, "agents_md": agents_md}


if __name__ == "__main__":
    print(__doc__.strip())
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
