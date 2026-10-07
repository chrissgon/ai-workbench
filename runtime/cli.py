#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The terminal shell of the task runtime: one command per operation of runtime/ops.py, nothing else.

Usage:
  python3 runtime/cli.py request  --project <dir> [--flow <name>] (--text <text> | --text-file <file>) [--title <title>]
  python3 runtime/cli.py route    --project <dir> --request <request id> [--flow <name>]
  python3 runtime/cli.py approve  --project <dir> --id <pending id> [--sha256 <plan hash> | --sha256 <effect hash>]
  python3 runtime/cli.py reject   --project <dir> --id <pending id> [--note <text>]
  python3 runtime/cli.py deps     --project <dir>
  python3 runtime/cli.py run-next --project <dir> [--tier strong]
  python3 runtime/cli.py pending  --project <dir> [--id <pending id>]
  python3 runtime/cli.py answer   --project <dir> --id <pending id> (--text <text> | --text-file <file>) [--with-comments]
  python3 runtime/cli.py release  --project <dir> --id <pending id>
  python3 runtime/cli.py retry    --project <dir> --task <task id>
  python3 runtime/cli.py cancel   --project <dir> --request <request id>
  python3 runtime/cli.py status   --project <dir>
  python3 runtime/cli.py accept-config --project <dir> --sha256 <hash>
  python3 runtime/cli.py proof    --project <dir> [--skill <name>]
  python3 runtime/cli.py verdict  --project <dir> --run <run id> --word worked|corrected|failed
  python3 runtime/cli.py sync     --project <dir> [--dry-run] [--take page|project --path <relative path>]
  python3 runtime/cli.py hand-over --project <dir> --task <task id> --file <path>
  python3 runtime/cli.py progress --project <dir> [--since 7d | <n>d | YYYY-MM-DD]
  python3 runtime/cli.py approve-policy --project <dir> --file <docs/...> --agent <name> [--sha256 <hash> --expires <YYYY-MM-DD>] [--what <text>]
  python3 runtime/cli.py revoke-policy --project <dir> --id <approval id>
  python3 runtime/cli.py standing --project <dir> --policy <name>
  python3 runtime/cli.py execute-under-policy --project <dir> --policy <name> --effect-file <path>
  python3 runtime/cli.py set-mode --project <dir> --agent <name> --mode stopped|supervised|milestones|autonomous|autonomous-with-policy
  python3 runtime/cli.py dispatch --project <dir>
  python3 runtime/cli.py poll     --project <dir>
  python3 runtime/cli.py handler  --project <dir> --name <handler> --verb <verb> [--arg <flag>=<value>]...
  python3 runtime/cli.py pin      --project <dir>
  python3 runtime/cli.py say      --project <dir> (--text <line> | --text-file <file or ->)

request   records what you want. With --flow, plans it from the flow file flows/<name>.json: its tasks, with the
          dependencies the file writes; a task without a dependency is ready at once. Without --flow, the
          request waits for its route.
route     plans a request that waits for its route. Without --flow: one run of the router skill, as it is, asked
          only for the route (it calls a model, like run-next; nothing it writes comes back); a route it gives
          becomes a plan for you to approve, a question it asks is answered with answer (then route again), and
          a reply with no recognised route reaches you whole. With --flow: the plan of that flow file, no run.
approve   approves a plan (its tasks are created; pass the plan's hash, shown with it, as --sha256 to approve
          exactly what you read) or a request written on the task board.
          An effect (a pull request a skill prepared up to its confirmation gate) is approved only here, in the
          terminal (the conversation refuses it), and only with its hash:
          code then checks that nothing moved, makes the one commit with your own git and signature through the
          code provider and opens the pull request. The provider reads the token that opens a pull request by its
          own name (VCS_GITHUB_PR_TOKEN, from the secret store or the environment, providers/vcs/README.md); the
          runtime passes none.
reject    rejects a plan or a request written on the task board: the request is cancelled. An effect rejected
          cancels its task, and nothing is sent.
run-next  runs the next ready task: one skill, once, in the eval container, on the model its proof gives (the
          floor model only where the skill is reliable there and the proof holds; --tier strong asks for the
          reference model; nothing asks for the floor model), on a copy
          of what may enter by limits L1 to L6 (runtime/workcopy.py). What the run left comes back by the path rule
          (runtime/path_rule.py); then the task waits for you. One task at a time per project. Start it with
          the secret store's library available, as the eval runner is started:
            uv run --with keyring==25.7.0 python3 runtime/cli.py run-next --project <dir>
pending   lists what waits for you; with --id, prints that pending decision whole: the reply, what came back,
          what was kept in the run folder.
answer    answers a pending decision; the task becomes ready and its next run is given your answer. With
          --with-comments, the comments saved from the task board for that task, and from the documents platform
          for the documents its skill writes, are added to your answer, under
          "Comments left on the platform:"; without it, no comment enters an answer.
release   releases a delivery (a pending decision of kind review): the task is done and what depended on it
          becomes ready. The delivery stays a draft: releasing is not approving. A run that wrote a document
          and still asks (ending draft_with_questions) opens a review too: release it as it stands, its open
          questions left in it, or answer it. A run that wrote nothing and asks opens a question: answer it.
retry     makes a failed or blocked task ready again.
cancel    cancels a request, its tasks that are not done and their open pending decisions.
status    requests, tasks and pending decisions, from the store's records; for each request and task, whether it is
          on the task board and how many comments saved from there are open; each mirrored document, its status
          and its note.
proof     the model each skill in use would run on, with the bands and the two checks (the measurement files,
          the eval image). It calls no model.
verdict   records your verdict on what one run delivered (worked, corrected, failed), with the existing
          recorder (scripts/evidence.py), on the use the run recorded. One verdict per run; only you give one.
sync      mirrors the tasks with the project's task board (task_board in runtime.json): a title, a text or a
          comment you wrote there comes in, and three state moves are taken (ready on a failed or blocked task,
          cancelled on a request, done on a task waiting on a review); any other move is written back. An item
          you wrote there waits for your approve before it can be routed. With documents in runtime.json it then
          mirrors the documents a skill's runtime manifest lists: a page you edited comes into the project when the
          project's file is still what was last written there and the skill's checker passes (else nothing changes
          and the document is rejected, with the reason; no task that reads it runs until it is settled), and a
          document that changed in the project goes to the platform, its open comments saved first. --dry-run
          reads nothing and prints every write it would make. A page that changed since the last write is never
          written over: a read-only type's page (it carries a notice saying so) is rejected until settled.
          --take page|project with --path settles a rejected document: the page's text (for a read-only type,
          the page kept as it is and the file not mirrored until it changes), or the project's file over the
          page.
hand-over copies one file of yours into the task's file drop, <project>/.workbench-local/drop/<task id>/: it
          enters that task's runs and no other, and the run's prompt lists it; what a run leaves there never comes
          back. Refused for a link, a folder, a file over 25 MB, a name with other characters than letters,
          digits, '.', '_' and '-', a name already handed over, a task that is done, cancelled or running, a
          file holding what looks like a credential, a git project that does not ignore .workbench-local/, and a
          task whose skill uses the web (a web task receives only the artifacts its skill declares).
deps      installs the dependency sets of runtime.json ("dependencies") by code, with no model: in the eval
          image, in a step that sees only the dependency files, on the open network; the result is cached under
          the data folder by the files and the image, and a run whose copy holds versioned files gets a copy of it.
progress  where the work stands (each open request, what waits for you, what is stuck) and what happened in a
          period (default the last 7 days; --since <n>d or a date YYYY-MM-DD): deliveries, runs, the known cost and
          the runs without one, your decisions and those of an autonomy mode, the effects executed. Computed from
          the store's records; it calls no model. "text" holds the same as plain lines.
approve-policy  approves a policy file for one area agent (a standing approval). Without --sha256 it shows the
          file's bounds and hash and writes nothing; type the hash it shows with --expires, a date at most 365 days
          ahead. A bounds file (docs/workbench/policies/<policy>.json) is checked whole; any other file under docs/
          (an engagement policy) is bound by its hash only. An earlier approval of the same policy and agent is
          revoked; the state file's Approvals table gets the generated row a skill's gate reads. An edited file is
          covered by nothing until you approve it again. Only an agent in the mode autonomous-with-policy acts on it.
revoke-policy  ends a standing approval; its row leaves the state file.
standing  whether an active standing approval covers a policy now, and why not; it executes nothing.
execute-under-policy  the one place an effect under a standing approval is executed: it checks the effect document a
          handler wrote against the approval's bounds, holding the run lock, makes the provider's dry run and its
          confirmed call, and records the action. {"executed": false, "why"} when the approval does not cover it:
          nothing ran. A handler never confirms a provider verb itself.
set-mode  sets one area agent's autonomy mode in docs/workbench/runtime.json (area_agents): stopped (it starts
          nothing), supervised (every delivery waits for you), milestones (the default: a milestone waits, the rest is
          released by the mode), autonomous (only what must reach you waits), autonomous-with-policy (as autonomous,
          and an effect inside a policy you approved runs without asking). A question, an unclassified reply, a
          draft with open questions and a mandatory milestone always wait for you. Then accept the new hash with
          accept-config, which also rewrites the Checkpoints line of the state file.
dispatch  one round of the dispatcher: the ticks of the handlers whose dispatch is true, the deliveries each area
          agent's mode releases (released, never approved), and the next ready tasks, one at a time, while the agent's
          mode and its daily caps allow (runs per day on the reference model, dollars per day on the floor model). It
          calls a model, like run-next. The scheduler's worker job calls it.
poll      the short job: mirrors the task board and the documents, expires standing approvals, rewrites the state file's
          generated lines, and releases what a mode releases. It calls no model and starts no task.
pin       writes the pin of the dispatcher's two jobs (<data_dir>/dispatch-pin.json): the path and the hash of the
          accepted runtime.json. The scheduler's entry (runtime/dispatcher.py) refuses to run when the file changed;
          after any change: accept-config, pin, then schedule both jobs again with the new command files.
say       one turn of the conversation with the planning agent (the same as one line of runtime/chat.py): a command
          (/help lists them), the answer to its question, or a new request, which runs the router (a model call) and
          shows the plan; refused when the planning agent is stopped or at its cap.
handler   starts one verb of a handler (runtime/handlers/) that handlers in runtime.json names, and prints its result.
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

table = ops.operations  # the table of operations, re-exported by the operations layer


class Usage(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Usage(message)


def dest_of(arg: dict) -> str:
    """The name a flag's value is kept under: never `verb` or `text`, which a flag and the command word both use."""
    return "f_" + table.flag_of(arg).replace("-", "_")


def build_parser() -> Parser:
    """The parser of every verb: the command word, --project, and every flag of every row of the table, once
    (the same flag of two rows is the same kind: a test checks it)."""
    p = Parser(prog="cli.py", add_help=False)
    p.add_argument("command", choices=table.terminal_verbs())
    p.add_argument("--project", required=True)
    seen = set()
    for row in table.OPERATIONS:
        if "terminal" not in row["channels"]:
            continue
        for arg in row["args"]:
            flag = "--" + table.flag_of(arg)
            if flag in seen:
                continue
            seen.add(flag)
            kind = arg["kind"]
            if kind == "text":
                p.add_argument("--text")
                p.add_argument("--text-file")
            elif kind == "int":
                p.add_argument(flag, dest=dest_of(arg), type=int)
            elif kind == "flag":
                p.add_argument(flag, dest=dest_of(arg), action="store_true")
            elif kind == "choice":
                p.add_argument(flag, dest=dest_of(arg), choices=arg["choices"])
            elif kind == "pairs":
                p.add_argument(flag, dest=dest_of(arg), action="append", default=[])
            else:
                p.add_argument(flag, dest=dest_of(arg))
    return p


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


def pairs_of(items: list, flag: str) -> dict:
    pairs = {}
    for item in items:
        if "=" not in item:
            raise Usage(f"--{flag} takes <flag>=<value>, not {item!r}")
        key, value = item.split("=", 1)
        pairs[key] = value
    return pairs


def run(argv) -> dict:
    a = build_parser().parse_args(argv)
    project = os.path.abspath(a.project)
    row = table.by_name(a.command)
    kwargs = {}
    for arg in row["args"]:
        flag = table.flag_of(arg)
        if arg["kind"] == "text":
            kwargs[arg["name"]] = text_of(a)
            continue
        value = getattr(a, dest_of(arg))
        if value is None and arg.get("required"):
            raise Usage(f"{a.command} needs --{flag}")
        kwargs[arg["name"]] = pairs_of(value, flag) if arg["kind"] == "pairs" else value
    if row.get("channel_arg"):
        kwargs["channel"] = "terminal"
    return getattr(ops, row["call"])(project, **kwargs)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or "--help" in argv or "-h" in argv:
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
