#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The runtime manifest of a skill: skills/<name>/evals/runtime-manifest.json, read and checked.

A manifest holds only what the task runtime must know of a skill and the skill's frontmatter does not declare:
which declared outputs a person reads as documents (with the skill's own checker commands, whether a person's
edit on a platform is taken back, whether the document is bound to an approval), the machine files, whether
the next skill needs the person's approval written inside the document, how the skill's asking reply opens,
and its confirmation gate. What the frontmatter declares (the web, the artifacts, the side effects) is never
repeated here. The file sits under evals/, outside the skill's content hash and never staged into a run, so
adding or changing it costs no version bump and no lab test.

Every skill of a pack in use (PACKS_IN_USE) must have a well-formed manifest, and a task whose skill has none
does not run (runtime/ops.py).

Usage (a library):
  python3 runtime/manifest.py --help
  python3 runtime/manifest.py --check     check the manifests of the skills of the packs in use; print one JSON
                                          object {"skills": n, "problems": {skill: [...]}}; exit 1 when any

Standard library only. Runs on Python 3.9.
"""
# Leaves at the change of reference model (docs/backlog.md, T23): the stable part of the manifest (the documents,
# the asking openings, the gate) moves into the skill's frontmatter, which a change of model re-tests anyway.
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import skill_meta  # noqa: E402  (the same folder, as the other modules import each other)

REL = "evals/runtime-manifest.json"
PACKS_IN_USE = ("business",)
KEYS = ("skill", "documents", "machine_files", "mandatory_milestone", "asking_openings", "gate")
DOCUMENT_KEYS = ("path", "checks", "platform", "bound_to_approval")
PLATFORM = ("editable", "read_only")
GATE_KEYS = ("effect", "payload_file")
ASKING = re.compile(r"^The reply that asks")
FENCE = re.compile(r"^\s*(```|~~~)")


class ManifestError(Exception):
    """The manifest is missing or not well formed; the message names every problem."""


def path(root: str, skill: str) -> str:
    """<root>/skills/<skill>/evals/runtime-manifest.json"""
    return os.path.join(root, "skills", skill, *REL.split("/"))


def _texts(value) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)


def problems(data, declared: dict, skill_dir: str) -> list:
    """Every problem of a parsed manifest, as sentences; empty when it is well formed. `declared` is
    skill_meta.declared(skill_dir)."""
    if not isinstance(data, dict):
        return ["the manifest is not a JSON object"]
    out = []
    for key in KEYS:
        if key not in data:
            out.append(f"missing key `{key}`")
    for key in data:
        if key not in KEYS:
            out.append(f"unknown key `{key}`: what the frontmatter declares is never repeated here")
    name = os.path.basename(os.path.normpath(skill_dir))
    if "skill" in data and data["skill"] != name:
        out.append(f"`skill` is {data['skill']!r}, and the folder is {name!r}")
    outputs, updates = declared.get("outputs") or [], declared.get("updates") or []
    scripts = os.path.join(skill_dir, "scripts")
    if "documents" in data:
        documents = data["documents"]
        if not isinstance(documents, list):
            out.append("`documents` is not a list")
            documents = []
        seen = set()
        for n, doc in enumerate(documents, 1):
            where = f"documents[{n}]"
            if not isinstance(doc, dict):
                out.append(f"{where} is not an object")
                continue
            for key in DOCUMENT_KEYS:
                if key not in doc:
                    out.append(f"{where}: missing key `{key}`")
            for key in doc:
                if key not in DOCUMENT_KEYS:
                    out.append(f"{where}: unknown key `{key}`")
            rel = doc.get("path")
            if "path" in doc:
                if rel not in outputs:
                    out.append(f"{where}: path {rel!r} is not one of the skill's declared outputs, written as there")
                if rel in seen:
                    out.append(f"{where}: path {rel!r} is listed twice")
                seen.add(rel)
            if "checks" in doc:
                checks = doc["checks"]
                if not isinstance(checks, list) or not all(_texts(c) and c for c in checks):
                    out.append(f"{where}: `checks` is not a list of non-empty lists of texts")
                else:
                    for check in checks:
                        script = check[0]
                        if "/" in script or not os.path.isfile(os.path.join(scripts, script)):
                            out.append(f"{where}: checker {script!r} is not a file of the skill's scripts/ folder")
            if "platform" in doc and doc["platform"] not in PLATFORM:
                out.append(f"{where}: platform {doc['platform']!r} is not one of {', '.join(PLATFORM)}")
            if "bound_to_approval" in doc and not isinstance(doc["bound_to_approval"], bool):
                out.append(f"{where}: `bound_to_approval` is not true or false")
    if "machine_files" in data:
        files = data["machine_files"]
        if not _texts(files):
            out.append("`machine_files` is not a list of texts")
        else:
            for rel in files:
                if rel not in outputs and rel not in updates:
                    out.append(f"machine file {rel!r} is not one of the skill's declared outputs or updates")
    if "mandatory_milestone" in data and not isinstance(data["mandatory_milestone"], bool):
        out.append("`mandatory_milestone` is not true or false")
    if "asking_openings" in data and not _texts(data["asking_openings"]):
        out.append("`asking_openings` is not a list of non-empty texts")
    if "gate" in data:
        gate, effects = data["gate"], declared.get("side_effects") or []
        if not effects:
            if gate is not None:
                out.append("`gate` is not null, and the skill declares no side effect")
        elif not isinstance(gate, dict) or sorted(gate) != sorted(GATE_KEYS):
            out.append("`gate` is not an object with exactly `effect` and `payload_file`, and the skill declares "
                       "a side effect")
        else:
            if gate["effect"] not in effects:
                out.append(f"gate effect {gate['effect']!r} is not one of the skill's side effects")
            payload = gate["payload_file"]
            if (not isinstance(payload, str) or not payload or payload.startswith(("/", "~"))
                    or ".." in payload.replace("\\", "/").split("/")):
                out.append("gate `payload_file` is not a relative path inside the project")
    return out


def load(root: str, skill: str) -> dict:
    """The manifest of a skill, checked. Raises ManifestError when the file is missing, is not JSON, or
    problems() is not empty."""
    file = path(root, skill)
    try:
        with open(file, encoding="utf-8") as f:
            data = json.load(f)
    except OSError:
        raise ManifestError(f"{skill} has no runtime manifest ({file}): the runtime knows nothing of the skill") from None
    except ValueError as e:
        raise ManifestError(f"{file} is not valid JSON: {e}") from None
    skill_dir = os.path.join(root, "skills", skill)
    try:
        declared = skill_meta.declared(skill_dir)
    except skill_meta.SkillError as e:
        raise ManifestError(str(e)) from None
    found = problems(data, declared, skill_dir)
    if found:
        raise ManifestError(f"{file}: " + "; ".join(found))
    return data


def _select_skills(root: str):
    name = "workbench_select_skills"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(root, "scripts", "select_skills.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def skills_in_use(root: str) -> list:
    """The sorted names of the skills of every pack of PACKS_IN_USE (scripts/select_skills.py, resolve())."""
    select = _select_skills(root)
    names = set()
    for pack in PACKS_IN_USE:
        names.update(select.resolve(pack=pack))
    return sorted(names)


def asking_openings_of(skill_md: str) -> list:
    """Read from a SKILL.md text: for every line that starts "The reply that asks" and is followed, after blank
    lines, by a fenced block, the first line of that block cut before its first ":" and stripped. Empty when the
    skill has no such block."""
    lines = skill_md.splitlines()
    out = []
    for i, line in enumerate(lines):
        if not ASKING.match(line):
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j + 1 < len(lines) and FENCE.match(lines[j]):
            first = lines[j + 1].split(":", 1)[0].strip()
            if first:
                out.append(first)
    return out


def bound_among(manifest: dict, paths) -> list:
    """The paths of `paths` that match a document with bound_to_approval true or an entry of machine_files: what
    runtime/path_rule.py gets as facts["bound"]."""
    bound = [d["path"] for d in manifest.get("documents") or [] if d.get("bound_to_approval")]
    bound += list(manifest.get("machine_files") or [])
    return [p for p in paths if skill_meta.matches(bound, p)]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv != ["--check"]:
        print(__doc__.strip(), file=sys.stdout if argv in (["--help"], ["-h"]) else sys.stderr)
        return 0 if argv in (["--help"], ["-h"]) else 2
    names = skills_in_use(ROOT)
    found = {}
    for name in names:
        try:
            load(ROOT, name)
        except ManifestError as e:
            found[name] = [str(e)]
    print(json.dumps({"skills": len(names), "problems": found}))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
