#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The terminal shell of the task runtime: one command per operation of runtime/ops.py, nothing else.

Usage:
  python3 runtime/cli.py request  --project <dir> --flow <name> (--text <text> | --text-file <file>) [--title <title>]
  python3 runtime/cli.py run-next --project <dir> [--tier strong]
  python3 runtime/cli.py pending  --project <dir> [--id <pending id>]
  python3 runtime/cli.py answer   --project <dir> --id <pending id> (--text <text> | --text-file <file>)
  python3 runtime/cli.py release  --project <dir> --id <pending id>
  python3 runtime/cli.py retry    --project <dir> --task <task id>
  python3 runtime/cli.py cancel   --project <dir> --request <request id>
  python3 runtime/cli.py status   --project <dir>
  python3 runtime/cli.py accept-config --project <dir> --sha256 <hash>
  python3 runtime/cli.py proof    --project <dir> [--skill <name>]

request   records what you want and plans it from the flow file flows/<name>.json: its tasks, with the
          dependencies the file writes. A task without a dependency is ready at once.
run-next  runs the next ready task: one skill, once, in the eval container, on the model its proof gives (the
          floor model only where the skill is reliable there and the proof holds; --tier strong asks for the
          reference model; nothing asks for the floor model), on a copy
          of what may enter by limits L1 to L6 (runtime/workcopy.py). What the run left comes back by the path rule
          (runtime/path_rule.py); then the task waits for you. One task at a time per project. Start it with
          the secret store's library available, as the eval runner is started:
            uv run --with keyring==25.7.0 python3 runtime/cli.py run-next --project <dir>
pending   lists what waits for you; with --id, prints that pending decision whole: the reply, what came back,
          what was kept in the run folder.
answer    answers a pending decision; the task becomes ready and its next run is given your answer.
release   releases a delivery (a pending decision of kind review): the task is done and what depended on it
          becomes ready. The delivery stays a draft: releasing is not approving. A run that wrote a document
          and still asks (ending draft_with_questions) opens a review too: release it as it stands, its open
          questions left in it, or answer it. A run that wrote nothing and asks opens a question: answer it.
retry     makes a failed or blocked task ready again.
cancel    cancels a request, its tasks that are not done and their open pending decisions.
status    requests, tasks and pending decisions, from the store's records.
proof     the model each skill in use would run on, with the bands and the two checks (the measurement files,
          the eval image). It calls no model.
accept-config  records the hash of docs/workbench/runtime.json you accept. Type the hash the refusal shows, after
          reading the file. Every other command refuses a file with another hash.

--text-file - reads the text from standard input.
The project is configured in <project>/docs/workbench/runtime.json (runtime/project_config.py).
Prints one JSON object on stdout; diagnostics on stderr.
Exit codes: 0 ok, 1 the operation failed or was refused, 2 usage error, 3 the project is not configured.
Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ops  # noqa: E402  (the same folder)

VERBS = ("request", "run-next", "pending", "answer", "release", "retry", "cancel", "status", "accept-config", "proof")


class Usage(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Usage(message)


def text_of(a) -> str:
    if (a.text is None) == (a.text_file is None):
        raise Usage("give exactly one of --text and --text-file")
    if a.text is not None:
        return a.text
    try:
        if a.text_file == "-":
            return sys.stdin.read()
        with open(a.text_file, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise Usage(f"--text-file: cannot read {a.text_file}: {e.strerror}") from None


def need(a, flag: str):
    value = getattr(a, flag.lstrip("-").replace("-", "_"))
    if value is None:
        raise Usage(f"{a.verb} needs {flag}")
    return value


def run(argv) -> dict:
    p = Parser(prog="cli.py", add_help=False)
    p.add_argument("verb", choices=VERBS)
    p.add_argument("--project", required=True)
    p.add_argument("--flow")
    p.add_argument("--title")
    p.add_argument("--text")
    p.add_argument("--text-file")
    p.add_argument("--id", type=int)
    p.add_argument("--task", type=int)
    p.add_argument("--request", type=int)
    p.add_argument("--sha256")
    p.add_argument("--tier")
    p.add_argument("--skill")
    a = p.parse_args(argv)
    project = os.path.abspath(a.project)
    if a.verb == "request":
        return ops.request(project, text_of(a), need(a, "--flow"), a.title)
    if a.verb == "run-next":
        return ops.run_next(project, a.tier)
    if a.verb == "pending":
        return ops.pending(project, a.id)
    if a.verb == "answer":
        return ops.answer(project, need(a, "--id"), text_of(a))
    if a.verb == "release":
        return ops.release(project, need(a, "--id"))
    if a.verb == "retry":
        return ops.retry(project, need(a, "--task"))
    if a.verb == "cancel":
        return ops.cancel(project, need(a, "--request"))
    if a.verb == "accept-config":
        return ops.accept_config(project, need(a, "--sha256"))
    if a.verb == "proof":
        return ops.proof(project, a.skill)
    return ops.status(project)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("--help", "-h"):
        print(__doc__.strip(), file=sys.stdout if argv else sys.stderr)
        return 0 if argv else 2
    try:
        out = run(argv)
    except Usage as e:
        print(f"error: {e}. See --help.", file=sys.stderr)
        return 2
    except ops.OpsError as e:
        print(f"error: {e}", file=sys.stderr)
        return e.code
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1, default=str)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
