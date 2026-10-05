#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The one module that decides what a run may change in the project's state file (docs/workbench/state.md),
limit L10 of the platform plan. No other module writes the state file.

The form of the file is contracts/state.md: a head (the lines before the first "## "), then the sections
"## Autonomy", "## Artifacts" (a table: Artifact, Owner skill, Status, Updated), "## Decisions" (lines
"- <date>: <text>. (<who>)"), "## Approvals" (a table) and "## Open questions" (lines "- [ ] <text>").

Of the state file a run left, the merge accepts three things, line by line, on top of what the project has now:
  - a row of ## Artifacts owned by the skill that ran, with the status `draft`, whose row the project did not
    change while the run was in progress;
  - a new line of ## Decisions attributed to the skill that ran (its last parenthesis starts with the skill's
    name and no item of it holds the word "user");
  - a new open question of ## Open questions ("- [ ] ...").
Everything else stays as the project has it, and each line refused is reported with its reason. Only code
writes what is the person's: an answer (with_answer()), "approved", the autonomy mode, the approval rows.

Usage (a library): python3 runtime/state_merge.py --help

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import re
import sys

ARTIFACTS = "Artifacts"
DECISIONS = "Decisions"
QUESTIONS = "Open questions"
OPEN_QUESTION = "- [ ]"
ANSWER_MAX = 2000
CUT = " [cut: the whole answer is in the runtime's records]"
WHITESPACE = re.compile(r"\s+")
SEPARATOR = re.compile(r"^\|?\s*:?-{3,}")
LAST_PARENTHESIS = re.compile(r"\(([^()]*)\)\s*\.?\s*$")
WORD_USER = re.compile(r"\buser\b", re.I)
PROTECTED = {"Autonomy": "only code writes the autonomy mode", "Approvals": "only code writes an approval row"}


class Conflict(Exception):
    """The run's state file cannot be brought back; the message says why. Nothing was written."""


def parse(text: str) -> dict:
    """{"head": [lines], "sections": [[title, [lines]]]} in the file's order; a title is the text after "## "."""
    head, sections = [], []
    for line in (text or "").splitlines():
        if line.startswith("## "):
            sections.append([line[3:].strip(), []])
        elif sections:
            sections[-1][1].append(line)
        else:
            head.append(line)
    return {"head": head, "sections": sections}


def _section(parsed: dict, title: str):
    for name, lines in parsed["sections"]:
        if name == title:
            return lines
    return None


def _cells(line: str):
    """The cells of a table row, or None when the line is not a row (or is the separator)."""
    stripped = line.strip()
    if not stripped.startswith("|") or SEPARATOR.match(stripped):
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _rows(lines) -> dict:
    """{Artifact cell: line} of the rows of an ## Artifacts table, the header row left out."""
    out = {}
    for line in lines or []:
        cells = _cells(line)
        if cells and cells[0] and cells[0] != "Artifact":
            out.setdefault(cells[0], line)
    return out


def _render(parsed: dict) -> str:
    lines = list(parsed["head"])
    for title, body in parsed["sections"]:
        lines.append("## " + title)
        lines.extend(body)
    return "\n".join(lines).rstrip("\n") + "\n"


def _append(lines: list, line: str) -> None:
    """Add a line after the last non-blank line of a section, keeping the blank lines that end it."""
    at = len(lines)
    while at > 0 and not lines[at - 1].strip():
        at -= 1
    lines.insert(at, line)


def _attributed_to(line: str, skill: str):
    """None when the decision line is attributed to the skill that ran; otherwise the reason it is refused."""
    found = LAST_PARENTHESIS.search(line)
    items = [item.strip() for item in found.group(1).split(",")] if found else []
    if any(WORD_USER.search(item) for item in items):
        return "a decision of the person is written by code"
    if not items or items[0] != skill:
        who = ", ".join(items) if items else "nobody"
        return f"a decision attributed to {who}, not to the skill that ran"
    return None


def merge_report(base, current, returned, skill: str) -> dict:
    """{"text", "accepted": [{"section", "line"}], "rejected": [{"section", "line", "reason"}]}: the project's
    state file after a run of `skill`.

    base      the state file's text as the run was given it, or None when the project had none
    current   the project's state file's text now, or None when it has none
    returned  the text the run left
    Raises Conflict when the run's text cannot be read (empty, or no "## Artifacts") or the project has no
    state file."""
    if not isinstance(returned, str) or not returned.strip() or "## Artifacts" not in returned.splitlines():
        raise Conflict("the run left a state file that cannot be read: nothing was merged")
    if current is None:
        raise Conflict("the project has no state file: core-project-init writes it")
    old, now, new = parse(base or ""), parse(current), parse(returned)
    accepted, rejected = [], []

    def refuse(section: str, line: str, reason: str) -> None:
        rejected.append({"section": section, "line": line, "reason": reason})

    # Head, Autonomy, Approvals and every other section: as the project has them.
    for line in new["head"]:
        if line not in old["head"]:
            refuse("head", line, "a run does not change this part of the state file")
    for title, lines in new["sections"]:
        if title in (ARTIFACTS, DECISIONS, QUESTIONS):
            continue
        before = _section(old, title) or []
        for line in lines:
            if line not in before:
                refuse(title, line, PROTECTED.get(title, "a run does not change this part of the state file"))
    # Artifacts: a draft row of the skill that ran, on a row the project did not change meanwhile.
    rows_before, rows_now = _rows(_section(old, ARTIFACTS)), _rows(_section(now, ARTIFACTS))
    target = _section(now, ARTIFACTS)
    for artifact, line in _rows(_section(new, ARTIFACTS)).items():
        if rows_before.get(artifact) == line:
            continue
        cells = _cells(line)
        if len(cells) < 3 or cells[1] != skill:
            refuse(ARTIFACTS, line, "the row belongs to another skill")
        elif cells[2] != "draft":
            refuse(ARTIFACTS, line, "only the person approves: a run may set draft only")
        elif rows_now.get(artifact) != rows_before.get(artifact):
            refuse(ARTIFACTS, line, "changed at the origin since the copy was made")
        elif target is None:
            refuse(ARTIFACTS, line, "the project's state file has no such section")
        else:
            if artifact in rows_now:
                target[target.index(rows_now[artifact])] = line
            else:
                last = max((i for i, l in enumerate(target) if _cells(l) is not None), default=None)
                if last is None:
                    _append(target, line)
                else:
                    target.insert(last + 1, line)
            rows_now[artifact] = line
            accepted.append({"section": ARTIFACTS, "line": line})
    # Decisions: new lines attributed to the skill that ran.
    before, target = _section(old, DECISIONS) or [], _section(now, DECISIONS)
    for line in _section(new, DECISIONS) or []:
        if not line.strip() or line in before:
            continue
        reason = _attributed_to(line, skill)
        if reason:
            refuse(DECISIONS, line, reason)
        elif target is None:
            refuse(DECISIONS, line, "the project's state file has no such section")
        else:
            if line not in target:
                _append(target, line)
            accepted.append({"section": DECISIONS, "line": line})
    for line in before:
        if line.strip() and line not in (_section(new, DECISIONS) or []):
            refuse(DECISIONS, line, "a run may add a decision of its own, never change or remove one")
    # Open questions: new ones are added; none is closed, changed or removed.
    before, target = _section(old, QUESTIONS) or [], _section(now, QUESTIONS)
    returned_questions = _section(new, QUESTIONS) or []
    for line in returned_questions:
        if not line.strip() or line in before:
            continue
        if not line.lstrip().startswith(OPEN_QUESTION):
            refuse(QUESTIONS, line, "a run may add an open question, never close or remove one")
        elif target is None:
            refuse(QUESTIONS, line, "the project's state file has no such section")
        else:
            if line not in target:
                _append(target, line)
            accepted.append({"section": QUESTIONS, "line": line})
    for line in before:
        if line.strip() and line not in returned_questions:
            refuse(QUESTIONS, line, "a run may add an open question, never close or remove one")
    return {"text": _render(now), "accepted": accepted, "rejected": rejected}


def merge(base, current, returned: str, skill: str) -> str:
    """merge_report(...)["text"]. Raises Conflict as merge_report() says."""
    return merge_report(base, current, returned, skill)["text"]


def with_answer(text: str, *, date: str, skill: str, pending_id: int, answer: str) -> str:
    """The state file's text with the person's answer added as the last line of ## Decisions. Code calls it; no
    run can produce its effect (merge_report() refuses a decision that names the user)."""
    parsed = parse(text)
    target = _section(parsed, DECISIONS)
    if target is None:
        raise Conflict("the state file has no ## Decisions section: the answer was not written into it")
    said = WHITESPACE.sub(" ", answer or "").strip()
    if len(said) > ANSWER_MAX:
        said = said[:ANSWER_MAX] + CUT
    _append(target, f"- {date}: Answer to {skill} (pending decision {pending_id}): {said} (user)")
    return _render(parsed)


if __name__ == "__main__":
    print(__doc__.strip())
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
