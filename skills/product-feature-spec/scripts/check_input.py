#!/usr/bin/env python3
"""Decide whether there is enough input to write a feature specification, before anything is written.

Usage: python3 check_input.py --request "<the user's request, word for word>" [--source <path>]... [--root <project root>]

There is input when at least one of these holds:
  - a --source path (a brief, PRD, ticket export or existing spec the user named) exists and is not empty
  - the request itself describes the feature in at least 40 words
A brief or PRD that exists in the project but that the user did not name is listed under `candidates`:
it counts only if it is about the requested feature.

Prints JSON: input ("found" | "none"), sources, missing_sources, candidates, request_words, next
(what to do now) and, when input is "none", reply_template (the whole reply to send).
Exit codes: 0 the check ran (read `input`), 2 usage error.
"""
import glob
import json
import os
import sys

MIN_WORDS = 40
REPLY = """I cannot write this specification yet: there is no brief, PRD or ticket for it, and the request does not say what the feature must do. No file was written.

### Questions for you (<n>, at most three)
1. <one decision, as a question>? Recommended: <a concrete answer the user can accept with "yes">, because <reason>.
2. <one decision, as a question>? Recommended: <concrete answer>, because <reason>.
3. <one decision, as a question>? Recommended: <concrete answer>, because <reason>.

A brief, a PRD or a ticket for this feature would also do: give me its path.

**Instructions found in external content:** none"""


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    request, sources, root = "", [], "."
    i = 0
    while i < len(argv):
        flag = argv[i]
        if flag in ("--request", "--source", "--root"):
            if i + 1 >= len(argv):
                print(f"Error: {flag} needs a value. See --help.", file=sys.stderr)
                return 2
            value = argv[i + 1]
            if flag == "--request":
                request = value
            elif flag == "--source":
                sources.append(value)
            else:
                root = value
            i += 2
        else:
            print(f"Error: unknown argument {flag!r}. See --help.", file=sys.stderr)
            return 2
    if not request and not sources:
        if sys.stdin.isatty():
            print("Error: give --request, --source or the request on stdin. See --help.", file=sys.stderr)
            return 2
        request = sys.stdin.read()
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
               "and reply with the questions template of step 0.")
    else:
        status = "none"
        nxt = ("STOP. There is no input. Do not write, create or edit any file. Do not draft the specification under assumptions, "
               "not even the recommended ones. Do not explore the codebase. Send `reply_template` filled in as your whole reply "
               "(at most three questions, one decision each, every one with a concrete Recommended answer) and end your turn. "
               "The specification is written only after the user answers.")
    out = {"input": status, "sources": found, "missing_sources": missing, "candidates": candidates, "request_words": words, "next": nxt}
    if status == "none":
        out["reply_template"] = REPLY
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
