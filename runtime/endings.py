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

It never guesses. A reply no rule recognises is `unclassified` and reaches the person whole. This first
version (stage 1 of the platform plan) knows three endings and is deliberately narrow; stage 2 makes it total
and tests it against the corpus of archived lab runs (runtime/tests/corpus/endings.jsonl).

Usage (a library): python3 runtime/endings.py --help

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import re
import sys

ENDINGS = ("done", "question", "draft_with_questions", "gate", "blocked", "unclassified")
# The opening of the reply the skills' asking template gives ("Nothing was searched or written yet: ...",
# "Nothing was written yet: ...").
ASK_OPENING = re.compile(r"^\W*Nothing was (?:searched or )?written yet\b", re.I)
RECOMMENDED = re.compile(r"\bRecommended:", re.I)
OPEN_MARK = re.compile(r"\bOPEN-\d+\b")


def _lines(text: str) -> list:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def classify(response: str, changes: dict, outputs_written, outputs_missing, output_texts) -> tuple:
    """(ending, why) of a completed run.

    response         the reply, whole
    changes          {"created", "modified", "deleted", "unchanged"}: what the run did to its copy
    outputs_written  the declared outputs of the skill among the files the run created or modified
    outputs_missing  the declared outputs without a placeholder that the copy does not hold after the run
    output_texts     the text of each path of outputs_written that is a text file, in the same order

    Rules, the first that holds:
    1. No file was created, modified or deleted, the reply holds a question mark, and either its first line is
       the asking template's opening, or it holds "Recommended:", or its last line ends with a question mark:
       `question`.
    2. No file changed and rule 1 does not hold: `unclassified`.
    3. No declared output was written: `unclassified`.
    4. A written output holds OPEN-<n>, or the reply's last line ends with a question mark:
       `draft_with_questions`.
    5. A declared output is missing: `unclassified`.
    6. Otherwise: `done`."""
    lines = _lines(response)
    last_asks = bool(lines) and lines[-1].rstrip("*_` ").endswith("?")
    changed = list(changes.get("created") or []) + list(changes.get("modified") or []) + list(changes.get("deleted") or [])
    if not changed:
        if "?" in (response or "") and (bool(lines) and ASK_OPENING.search(lines[0]) or RECOMMENDED.search(response) or last_asks):
            return "question", "no file changed and the reply asks"
        return "unclassified", "no file changed and the reply is not recognised as a question"
    if not outputs_written:
        return "unclassified", "files changed, none of them a declared output of the skill"
    if any(OPEN_MARK.search(text or "") for text in output_texts) or last_asks:
        return "draft_with_questions", "a declared output was written and a question is open"
    if outputs_missing:
        return "unclassified", "a declared output was written and another is missing: " + ", ".join(outputs_missing)
    return "done", "every declared output is there and nothing is asked"


if __name__ == "__main__":
    print(__doc__.strip())
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
