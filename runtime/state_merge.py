#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The one module that decides what a run may change in the project's state file (docs/workbench/state.md).

Stage 1 of the platform plan (this file as first written) accepts the state file a run left only as a whole,
and only when the project's state file is still the text the run was given: nothing a run returns overwrites
what changed at the origin meanwhile. Stage 2 replaces the body of merge() by the real merge: of a run's text
it accepts drafts of the skill that ran, decisions attributed to that skill and new open questions, and only
code writes what is the person's (an answer, "approved", the autonomy mode, the approval rows). The signature
does not change, and no other module writes the state file.

Usage (a library): python3 runtime/state_merge.py --help

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import sys


class Conflict(Exception):
    """The run's state file cannot be brought back; the message says why. Nothing was written."""


def merge(base, current, returned: str, skill: str) -> str:
    """The text the project's state file gets after a run of `skill`.

    base      the state file's text as the run was given it, or None when the project had none
    current   the project's state file's text now, or None when it has none
    returned  the text the run left
    Raises Conflict when the state file changed at the origin since the copy was made."""
    if current != base:
        raise Conflict("docs/workbench/state.md changed in the project while the run was in progress: what the run "
                       "left is kept in its run folder and nothing was merged")
    if not isinstance(returned, str) or not returned.strip():
        raise Conflict("the run left an empty docs/workbench/state.md: nothing was merged")
    return returned


if __name__ == "__main__":
    print(__doc__.strip())
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
