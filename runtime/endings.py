#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""How a run ended, for a run that did not fail: the classifier of endings.

The failures (a timeout, a refusal by the provider, a refused credential, a failure of the adapter, an early
end) are decided before this, by the lab's own functions (runtime/lab.py). This module reads a run that
completed and says which of the closed list it is:

  done                   the skill delivered: a declared output was written, and nothing is asked
  question               the skill stopped to ask and wrote nothing
  draft_with_questions   the skill wrote a declared output and still asks (an OPEN-<n> in it, or a closing question)
  gate                   the skill stopped at its confirmation gate          (recognised from stage 2 on)
  blocked                the skill stopped on a missing input                 (recognised from stage 2 on)
  unclassified           none of the rules below holds

It never guesses. A reply no rule recognises is `unclassified` and reaches the person whole. Without facts
(classify(..., facts=None)) it applies the first classifier's six rules (stage 1 of the platform plan). With the
facts of the skill that ran (manifest.ending_facts(), plus the run's own `outputs_present`), it recognises every
ending of the closed list, each from the run's facts, what the skill declares, or a sentence that comes from the
skills' own text (the comment beside each constant names the file). It is tested against the corpus of archived
lab runs (runtime/tests/corpus/endings.jsonl, runtime/tests/corpus/labels.json).

Usage:
  python3 runtime/endings.py --help
  python3 runtime/endings.py --corpus runtime/tests/corpus/endings.jsonl
      classify every line of a corpus with the facts of the line's skill (manifest.ending_facts) and print one
      JSON object {"lines", "by_ending", "stopped": {ending: n}, "changed": {ending: n}, "unclassified_ids"}

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import path_rule  # noqa: E402  (the same folder, as the other modules import each other)
import skill_meta  # noqa: E402

ENDINGS = ("done", "question", "draft_with_questions", "gate", "blocked", "unclassified")
# The opening of the reply the skills' asking template gives ("Nothing was searched or written yet: ...",
# "Nothing was written yet: ...").
ASK_OPENING = re.compile(r"^\W*Nothing was (?:searched or )?written yet\b", re.I)
RECOMMENDED = re.compile(r"\bRecommended:", re.I)
OPEN_MARK = re.compile(r"\bOPEN-\d+\b")
# The stop on a missing input: stop rule 1 of templates/capability.SKILL.md ("stop and tell the user that
# `<area>-<skill>` writes it and to run it first"), with the forms the skills write it in: "writes them"
# (skills/brand-strategy/SKILL.md), "writes that section" (skills/eng-tradeoffs/SKILL.md), "writes the PRD"
# (skills/product-roadmap/SKILL.md, its reply when the PRD is missing) and "run `<skill>` first"
# (skills/design-ux-flows/SKILL.md, the same reply).
MISSING_INPUT = re.compile(r"\bwrites (?:it|them|that section|the PRD)\b|\brun (?:it|`[a-z0-9-]+`) first\b", re.I)
# A skill that is not built is cited with the mark `(planned)`: the writing standard of AGENTS.md.
PLANNED = "(planned)"
# The asking reply of templates/capability.SKILL.md gives each question a "Recommended:" answer (RECOMMENDED).
# The question of a confirmation gate, asked as the reply's last line: "Proceed? (yes/no)"
# (skills/design-execute/SKILL.md), "Push? (yes/no)" (skills/ops-branch-sync/SKILL.md), "Dismiss these <n>
# alerts? (yes/no)" (skills/eng-security-review/SKILL.md). And a question closed by its recommended answer, as the
# asking reply of templates/capability.SKILL.md writes each one ("<question>? Recommended: <answer>"). Read only
# with facts: the first classifier is unchanged.
YES_NO = re.compile(r"\?\s*\(yes/no\)$", re.I)
LEADING = "*_#>`- \t"


def _lines(text: str) -> list:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _asks(response: str, lines: list, openings, yes_no: bool = False) -> bool:
    """The reply is an asking reply: it holds a question mark, and its first line starts with an asking opening
    (the skill's own, or the template's), or it holds "Recommended:", or its last line ends with a question mark."""
    if "?" not in (response or "") or not lines:
        return False
    first = lines[0].lstrip(LEADING)
    return (any(o and first.lower().startswith(o.lower()) for o in openings) or bool(ASK_OPENING.search(lines[0]))
            or bool(RECOMMENDED.search(response)) or _last_asks(lines, yes_no))


def _last_asks(lines: list, yes_no: bool = False) -> bool:
    """The reply's last line ends with a question mark. With yes_no (only with facts) also when it ends with
    "? (yes/no)", or holds a question mark followed by "Recommended:" (a question of the asking reply, written
    with its recommended answer, as the last line)."""
    if not lines:
        return False
    last = lines[-1].rstrip("*_` ")
    if last.endswith("?"):
        return True
    return yes_no and (bool(YES_NO.search(last)) or ("?" in last and bool(RECOMMENDED.search(last.split("?", 1)[1]))))


def _names_missing_input(lines: list, skill: str, skills) -> bool:
    """A line of the reply holds `writes it` or `run it first`, and the same line names another skill of the
    workbench or the mark (planned)."""
    others = [name for name in (skills or []) if name and name != skill]
    for line in lines:
        if not MISSING_INPUT.search(line):
            continue
        if PLANNED in line or any(re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", line) for name in others):
            return True
    return False


def classify(response: str, changes: dict, outputs_written, outputs_missing, output_texts, *, facts=None) -> tuple:
    """(ending, why) of a completed run.

    response         the reply, whole
    changes          {"created", "modified", "deleted", "unchanged"}: what the run did to its copy
    outputs_written  the declared outputs of the skill among the files the run created or modified
    outputs_missing  the declared outputs without a placeholder that the copy does not hold after the run
    output_texts     the text of each path of outputs_written that is a text file, in the same order
    facts            None (the first classifier), or {"skill", "asking_openings", "fixed_output", "side_effects",
                     "gate_payload", "skills"} from manifest.ending_facts(), and optionally "outputs_present": the
                     declared outputs without a placeholder that the run's copy held, unchanged, after the run

    Without facts, the first that holds:
    1. No file was created, modified or deleted, the reply holds a question mark, and either its first line is
       the asking template's opening, or it holds "Recommended:", or its last line ends with a question mark:
       `question`.
    2. No file changed and rule 1 does not hold: `unclassified`.
    3. No declared output was written: `unclassified`.
    4. A written output holds OPEN-<n>, or the reply's last line ends with a question mark:
       `draft_with_questions`.
    5. A declared output is missing: `unclassified`.
    6. Otherwise: `done`.

    With facts, the first that holds:
    1. No file changed; a line holds "writes it" or "run it first" and, on the same line, another skill of
       facts["skills"] or "(planned)"; and the reply does not hold "Recommended:": `blocked`.
    2. facts["gate_payload"] is set, a created or modified path matches it, and the reply's last line ends with a
       question mark: `gate`.
    3. No file changed, or only the state file (path_rule.STATE) changed, and the reply asks (rule 1 above, with
       the skill's own asking openings too): `question`. A run that changed only the state file and asks
       nothing goes on to rules 6 and 7.
    4. No file changed; a declared output is already in the copy (facts["outputs_present"]); the reply does not
       open with an asking opening, does not hold "Recommended:", and its last line does not end with a question
       mark: `done` (nothing was left to write: the delivery is the document already there).
    5. No file changed: `unclassified`.
    6. No declared output was written, facts["fixed_output"] is false, and the reply's last line does not end
       with a question mark: `done` (the skill's work is the project's own files).
    7. No declared output was written: `unclassified`.
    8. A written output holds OPEN-<n>, or the reply's last line ends with a question mark:
       `draft_with_questions`.
    9. A declared output without a placeholder is missing: `unclassified`.
    10. Otherwise: `done`."""
    lines = _lines(response)
    last_asks = _last_asks(lines)
    changed = list(changes.get("created") or []) + list(changes.get("modified") or []) + list(changes.get("deleted") or [])
    if facts is None:
        if not changed:
            if _asks(response, lines, ()):
                return "question", "no file changed and the reply asks"
            return "unclassified", "no file changed and the reply is not recognised as a question"
        if not outputs_written:
            return "unclassified", "files changed, none of them a declared output of the skill"
        if any(OPEN_MARK.search(text or "") for text in output_texts) or last_asks:
            return "draft_with_questions", "a declared output was written and a question is open"
        if outputs_missing:
            return "unclassified", "a declared output was written and another is missing: " + ", ".join(outputs_missing)
        return "done", "every declared output is there and nothing is asked"

    openings = list(facts.get("asking_openings") or [])
    last_asks = _last_asks(lines, yes_no=True)
    if not changed and _names_missing_input(lines, facts.get("skill") or "", facts.get("skills")) \
            and not RECOMMENDED.search(response or ""):
        return "blocked", "no file changed and the reply names a missing input and the skill that writes it"
    payload = facts.get("gate_payload")
    if payload and last_asks:
        left = list(changes.get("created") or []) + list(changes.get("modified") or [])
        if any(skill_meta.matches([payload], p) for p in left):
            return "gate", "the run wrote the file of its confirmation gate and asks for approval"
    # For telling `question` from the other endings, a change limited to the state file counts as having written
    # nothing (WP-2.13): the skills write their open questions and decisions there when they stop to ask.
    state_only = bool(changed) and all(p == path_rule.STATE for p in changed)
    if (not changed or state_only) and _asks(response, lines, openings, yes_no=True):
        return "question", ("only the state file changed and the reply asks" if state_only
                            else "no file changed and the reply asks")
    if not changed:
        first = lines[0].lstrip(LEADING).lower() if lines else ""
        opens_asking = bool(lines) and (bool(ASK_OPENING.search(lines[0]))
                                        or any(o and first.startswith(o.lower()) for o in openings))
        if facts.get("outputs_present") and lines and not last_asks and not opens_asking \
                and not RECOMMENDED.search(response or ""):
            return "done", "no file changed, a declared output is already there, and the reply asks nothing"
        return "unclassified", "no file changed and the reply is not recognised as a question"
    if not outputs_written:
        if not facts.get("fixed_output") and not last_asks:
            return "done", "the skill declares no fixed output; files changed and nothing is asked"
        return "unclassified", "files changed, none of them a declared output of the skill"
    if any(OPEN_MARK.search(text or "") for text in output_texts) or last_asks:
        return "draft_with_questions", "a declared output was written and a question is open"
    if outputs_missing:
        return "unclassified", "a declared output was written and another is missing: " + ", ".join(outputs_missing)
    return "done", "every declared output is there and nothing is asked"


def corpus_counts(corpus: str, root: str = ROOT) -> dict:
    """Classify every line of a corpus file with the facts of the line's skill (manifest.ending_facts). A corpus
    line does not record what the run's copy held, so no line has `outputs_present`."""
    import manifest  # the same folder; imported here because manifest.py reads the packs only for this command
    facts_of, out = {}, {"lines": 0, "by_ending": {}, "stopped": {}, "changed": {}, "unclassified_ids": []}
    with open(corpus, encoding="ascii") as f:
        for raw in f:
            line = json.loads(raw)
            if line["skill"] not in facts_of:
                facts_of[line["skill"]] = manifest.ending_facts(root, line["skill"])
            ending = classify_line(line, facts_of[line["skill"]])[0]
            out["lines"] += 1
            out["by_ending"][ending] = out["by_ending"].get(ending, 0) + 1
            side = "stopped" if line["stopped"] else "changed"
            out[side][ending] = out[side].get(ending, 0) + 1
            if ending == "unclassified":
                out["unclassified_ids"].append(line["id"])
    for key in ("by_ending", "stopped", "changed"):
        out[key] = dict(sorted(out[key].items()))
    return out


def classify_line(line: dict, facts: dict) -> tuple:
    """(ending, why) of one corpus line, with the facts of its skill. The corpus keeps no output's text, so an
    OPEN-<n> inside a written output is not seen; a missing output is not known either."""
    changes = {"created": line["created"], "modified": line["modified"], "deleted": line["deleted"], "unchanged": []}
    return classify(line["response"], changes, line["outputs_written"], [], [], facts=facts)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == "--corpus":
        try:
            print(json.dumps(corpus_counts(argv[1])))
        except (OSError, ValueError, KeyError) as e:
            print(f"error: the corpus cannot be read: {e}", file=sys.stderr)
            return 1
        return 0
    print(__doc__.strip(), file=sys.stdout if argv in (["--help"], ["-h"]) else sys.stderr)
    return 0 if argv in (["--help"], ["-h"]) else 2


if __name__ == "__main__":
    sys.exit(main())
