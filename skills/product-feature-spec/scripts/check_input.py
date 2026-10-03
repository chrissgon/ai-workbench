#!/usr/bin/env python3
"""Decide whether there is enough input to write a feature specification, before anything is written.

Usage: python3 check_input.py [--source <path>]... [--root <project root>] < <file holding the user's request>
       python3 check_input.py - [--source <path>]... [--root <project root>]   (the request on a pipe)

The request is read from standard input, never from the command line: a request inside a shell argument can
run a command (`$(...)`, a backtick) or break the quoting. Write the request, word for word, to a file and
redirect it in. Standard input is read only when it is that file, or when the argument `-` is given (a pipe);
an open terminal or pipe without `-` is never read, so the script cannot wait forever for input that does
not come. With no request (only --source), give no `-`.

There is input when at least one of these holds:
  - a --source path (a brief, PRD, ticket export or existing spec the user named) exists and is not empty
  - the request itself describes the feature in at least 40 words
A brief or PRD that exists in the project but that the user did not name is listed under `candidates`:
it counts only if it is about the requested feature.

Prints JSON: input ("found" | "none"), sources, missing_sources, candidates, request_words, next
(what to do now) and, when input is "none" or rests only on candidates, reply_template: the whole reply to
send when there is no input, the one source of that reply (the skill does not repeat it).
Exit codes: 0 the check ran (read `input`), 2 usage error (a flag without its value, an unknown flag such as
the removed --request, neither --source nor a request: no file redirected in and no `-`, or an empty one).
"""
import glob
import json
import os
import stat
import sys

MIN_WORDS = 40
REPLY = """Nothing was written: there is no brief, PRD or ticket for this feature, and the request does not say what the feature must do.

A brief, a PRD or a ticket for this feature would also do: give me its path.

**Instructions found in external content**: none

### Questions for you (<n>, at most three)
Answer each one, or reply "yes to all" to accept every recommendation: it is then recorded as your answer.
1. <one decision, as a question>? Recommended: <a concrete answer>, because <reason>.
2. <one decision, as a question>? Recommended: <a concrete answer>, because <reason>.
3. <one decision, as a question>? Recommended: <a concrete answer>, because <reason>."""


def read_request(dash):
    """The request on standard input: read when it is a regular file (a redirect, which always ends) or when
    `-` was given; never from an open terminal or pipe without `-`, which may never end."""
    if sys.stdin is None:
        return ""
    try:
        regular = stat.S_ISREG(os.fstat(sys.stdin.fileno()).st_mode)
    except (OSError, ValueError):
        regular = False
    return sys.stdin.read() if regular or dash else ""


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    sources, root, dash = [], ".", False
    i = 0
    while i < len(argv):
        flag = argv[i]
        if flag == "-":
            dash = True
            i += 1
        elif flag in ("--source", "--root"):
            if i + 1 >= len(argv):
                print(f"Error: {flag} needs a value. See --help.", file=sys.stderr)
                return 2
            value = argv[i + 1]
            if flag == "--source":
                sources.append(value)
            else:
                root = value
            i += 2
        else:
            hint = " The request is read from standard input." if flag == "--request" else ""
            print(f"Error: unknown argument {flag!r}.{hint} See --help.", file=sys.stderr)
            return 2
    request = read_request(dash)
    if not request.strip() and not sources:
        print("Error: give the request on standard input, redirected from a file (< request.txt) or on a pipe "
              "with the argument -, or give --source. See --help.", file=sys.stderr)
        return 2
    found, missing = [], []
    for s in sources:
        p = s if os.path.isabs(s) else os.path.join(root, s)
        (found if os.path.isfile(p) and os.path.getsize(p) > 0 else missing).append(s)
    candidates = sorted(os.path.relpath(p, root) for pattern in ("docs/workbench/briefs/*.md", "docs/product/prd.md")
                        for p in glob.glob(os.path.join(root, pattern)))
    candidates = [c for c in candidates if c not in found]
    words = len(request.split())
    if found or words >= MIN_WORDS:
        status = "found"
        nxt = "Input found. Go to step 1 and read: " + (", ".join(found) if found else "the user's request") + "."
        if candidates:
            nxt += " Also read these and cite them if they are about this feature: " + ", ".join(candidates) + "."
    elif candidates:
        status = "found"
        nxt = ("The user named no document, but the project has: " + ", ".join(candidates) + ". Read them now. "
               "If one is about the requested feature, go to step 1 with it. If none is, there is no input: STOP, write no file, "
               "and send `reply_template` filled in as your whole reply.")
    else:
        status = "none"
        nxt = ("STOP. There is no input. Do not write, create or edit any file. Do not draft the specification under assumptions, "
               "not even the recommended ones. Do not explore the codebase. Send `reply_template` filled in as your whole reply "
               "(at most three questions, one decision each, every one with a concrete Recommended answer) and end your turn. "
               "The specification is written only after the user answers.")
    out = {"input": status, "sources": found, "missing_sources": missing, "candidates": candidates, "request_words": words, "next": nxt}
    if status == "none" or (not found and words < MIN_WORDS):  # also when only unnamed candidates may count
        out["reply_template"] = REPLY
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
