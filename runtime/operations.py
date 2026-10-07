"""The table of operations: the one place that says what the operations layer (runtime/ops.py) offers to a shell.

A shell (the terminal's runtime/cli.py, the conversation's runtime/chat.py, a later page) derives what it accepts from
this table and spells nothing of its own: one row per operation, with its arguments, the channels that may call it
and whether it calls a model. Adding an operation adds one row here and one function in ops.py; adding a shell adds a
file. The channel rule is a column: a row lists the channels that may call it, and a row whose function takes the
channel (`channel_arg`) is told which one called it, so that code, not a prompt, refuses what a channel may not do
(an effect is approved only from the terminal, with its hash).

OPERATIONS and CHAT_OWN are pure literals (`ast.literal_eval` reads them: scripts/architecture_tables.py and a test
do, so that the generated tables and the shells cannot differ). A row:

  name         the terminal's verb and the conversation's command word (`run-next`, `/approve`)
  call         the function of ops.py that runs it
  args         the arguments, in the order the conversation reads them; each {"name": the function's parameter,
               "kind": int | str | text | flag | choice | pairs, "required": True, "flag": the terminal flag when it
               is not the name with hyphens, "label": the placeholder in a help line, "choices": for a choice}.
               `text` is the terminal's --text / --text-file pair and, in the conversation, the rest of the line;
               `flag` is true when present; `pairs` is the handler's repeated --arg k=v
  channels     which channels may call it: "terminal", "chat" ("page" is reserved for the local interface)
  model        whether it calls a model: False, True, or the words that say when ("without --flow")
  help         one line: what it does
  channel_arg  (optional) the function takes `channel=<name>` and decides what that channel may do
  chat_reply   (optional) the key of the result the conversation shows instead of the whole result

The functions are pure and use the standard library only. Runs on Python 3.9: python3 runtime/operations.py --help
"""
from __future__ import annotations

import re
import shlex
import sys

TERMINAL = "python3 runtime/cli.py"
HELP_HEAD = "Commands, one per line; any other line is a request for the planning agent, or the answer to its question:"
HELP_WIDTH = 27

OPERATIONS = (
    {"name": "request", "call": "request",
     "args": ({"name": "text", "kind": "text", "required": True}, {"name": "flow", "kind": "str"},
              {"name": "title", "kind": "str"}),
     "channels": ("terminal",), "model": False,
     "help": "record what you want; with a flow, plan it from the flow file, else it waits for its route"},
    {"name": "route", "call": "route",
     "args": ({"name": "request_id", "kind": "int", "required": True, "flag": "request"}, {"name": "flow", "kind": "str"}),
     "channels": ("terminal",), "model": "without --flow",
     "help": "plan a request that waits for its route: one run of the router skill, or the plan of a flow file"},
    {"name": "status", "call": "status", "args": (), "channels": ("terminal", "chat"), "model": False,
     "help": "requests, tasks and what waits for you"},
    {"name": "progress", "call": "progress", "args": ({"name": "since", "kind": "str"},),
     "channels": ("terminal", "chat"), "model": False, "chat_reply": "text",
     "help": "where the work stands and what happened (since: 7d, <n>d or YYYY-MM-DD)"},
    {"name": "pending", "call": "pending",
     "args": ({"name": "pending_id", "kind": "int", "flag": "id"},),
     "channels": ("terminal", "chat"), "model": False,
     "help": "what waits for you; with an id, that decision whole"},
    {"name": "answer", "call": "answer",
     "args": ({"name": "pending_id", "kind": "int", "required": True, "flag": "id"},
              {"name": "text", "kind": "text", "required": True},
              {"name": "with_comments", "kind": "flag", "flag": "with-comments"}),
     "channels": ("terminal", "chat"), "model": False,
     "help": "answer a pending decision"},
    {"name": "release", "call": "release",
     "args": ({"name": "pending_id", "kind": "int", "required": True, "flag": "id"},),
     "channels": ("terminal", "chat"), "model": False,
     "help": "release a delivery (it stays a draft)"},
    {"name": "approve", "call": "approve",
     "args": ({"name": "pending_id", "kind": "int", "required": True, "flag": "id"}, {"name": "sha256", "kind": "str"}),
     "channels": ("terminal", "chat"), "model": False, "channel_arg": True,
     "help": "approve a plan or an acceptance; an effect is approved in the terminal, with its hash"},
    {"name": "reject", "call": "reject",
     "args": ({"name": "pending_id", "kind": "int", "required": True, "flag": "id"}, {"name": "note", "kind": "str"}),
     "channels": ("terminal", "chat"), "model": False,
     "help": "reject a plan, an acceptance or an effect"},
    {"name": "retry", "call": "retry",
     "args": ({"name": "task_id", "kind": "int", "required": True, "flag": "task", "label": "task id"},),
     "channels": ("terminal", "chat"), "model": False,
     "help": "make a failed or blocked task ready again"},
    {"name": "cancel", "call": "cancel",
     "args": ({"name": "request_id", "kind": "int", "required": True, "flag": "request", "label": "request id"},),
     "channels": ("terminal", "chat"), "model": False,
     "help": "cancel a request"},
    {"name": "deps", "call": "deps", "args": (), "channels": ("terminal",), "model": False,
     "help": "install the dependency sets of runtime.json, by code"},
    {"name": "run-next", "call": "run_next", "args": ({"name": "tier", "kind": "str"},),
     "channels": ("terminal",), "model": True,
     "help": "run the next ready task: one skill, once, on the model its proof gives"},
    {"name": "accept-config", "call": "accept_config",
     "args": ({"name": "sha256", "kind": "str", "required": True},),
     "channels": ("terminal",), "model": False,
     "help": "record the hash of runtime.json you accept"},
    {"name": "proof", "call": "proof", "args": ({"name": "skill", "kind": "str"},),
     "channels": ("terminal",), "model": False,
     "help": "the model each skill in use would run on, with its bands and the two checks"},
    {"name": "verdict", "call": "verdict",
     "args": ({"name": "run_id", "kind": "int", "required": True, "flag": "run"},
              {"name": "word", "kind": "str", "required": True}),
     "channels": ("terminal",), "model": False,
     "help": "record your verdict on what one run delivered (worked, corrected or failed)"},
    {"name": "sync", "call": "sync",
     "args": ({"name": "dry_run", "kind": "flag", "flag": "dry-run"},
              {"name": "take", "kind": "choice", "choices": ("page", "project")}, {"name": "path", "kind": "str"}),
     "channels": ("terminal",), "model": False,
     "help": "mirror the tasks with the task board and the documents with the documents platform"},
    {"name": "hand-over", "call": "hand_over",
     "args": ({"name": "task_id", "kind": "int", "required": True, "flag": "task"},
              {"name": "file", "kind": "str", "required": True}),
     "channels": ("terminal",), "model": False,
     "help": "copy one file of yours into a task's file drop"},
    {"name": "set-mode", "call": "set_mode",
     "args": ({"name": "agent", "kind": "str", "required": True}, {"name": "mode", "kind": "str", "required": True}),
     "channels": ("terminal",), "model": False,
     "help": "set one area agent's autonomy mode in runtime.json"},
    {"name": "approve-policy", "call": "approve_policy",
     "args": ({"name": "file", "kind": "str", "required": True}, {"name": "agent", "kind": "str", "required": True},
              {"name": "sha256", "kind": "str"}, {"name": "expires", "kind": "str"}, {"name": "what", "kind": "str"}),
     "channels": ("terminal",), "model": False,
     "help": "approve a policy file for one area agent (a standing approval)"},
    {"name": "revoke-policy", "call": "revoke_policy",
     "args": ({"name": "approval_id", "kind": "int", "required": True, "flag": "id"},),
     "channels": ("terminal",), "model": False,
     "help": "end a standing approval"},
    {"name": "standing", "call": "standing",
     "args": ({"name": "policy", "kind": "str", "required": True},),
     "channels": ("terminal",), "model": False,
     "help": "whether an active standing approval covers a policy now; it executes nothing"},
    {"name": "execute-under-policy", "call": "execute_under_policy",
     "args": ({"name": "policy", "kind": "str", "required": True},
              {"name": "effect_file", "kind": "str", "required": True, "flag": "effect-file"}),
     "channels": ("terminal",), "model": False,
     "help": "execute an effect a handler wrote, inside the bounds of a standing approval"},
    {"name": "dispatch", "call": "dispatch", "args": (), "channels": ("terminal",), "model": True,
     "help": "one round of the dispatcher: the handlers' ticks, the releases by a mode, the next ready tasks"},
    {"name": "poll", "call": "poll", "args": (), "channels": ("terminal",), "model": False,
     "help": "the short job: mirrors, expired approvals, the state file's generated lines, the releases"},
    {"name": "handler", "call": "handler_call",
     "args": ({"name": "name", "kind": "str", "required": True}, {"name": "verb", "kind": "str", "required": True},
              {"name": "args", "kind": "pairs", "flag": "arg"}),
     "channels": ("terminal",), "model": False,
     "help": "start one verb of a handler that runtime.json names"},
    {"name": "pin", "call": "pin", "args": (), "channels": ("terminal",), "model": False,
     "help": "write the pin of the dispatcher's two jobs"},
    {"name": "say", "call": "say", "args": ({"name": "text", "kind": "text", "required": True},),
     "channels": ("terminal",), "model": "for a new request",
     "help": "one turn of the conversation with the planning agent"},
)

# What the conversation answers itself, with no operation: the help, and a new request whatever is open.
CHAT_OWN = (
    {"name": "help", "args": "", "help": "this text", "order": "first"},
    {"name": "new", "args": "text", "help": "start a new request, whatever is open", "order": "last"},
)

POSITIONAL = ("int", "str", "text")  # the kinds the conversation reads from a line


def by_name(name: str) -> dict:
    """The row of an operation. KeyError when there is none."""
    for row in OPERATIONS:
        if row["name"] == name:
            return row
    raise KeyError(name)


def terminal_verbs() -> tuple:
    """The verbs of the terminal shell, in the table's order."""
    return tuple(row["name"] for row in OPERATIONS if "terminal" in row["channels"])


def flag_of(arg: dict) -> str:
    """The terminal flag of an argument, without the leading dashes."""
    return arg.get("flag") or arg["name"].replace("_", "-")


def _label(arg: dict) -> str:
    return arg.get("label") or (flag_of(arg) if arg["kind"] == "int" else arg["name"])


def _usage(row: dict) -> str:
    parts = ["/" + row["name"]]
    for arg in row["args"]:
        if arg["kind"] in POSITIONAL:
            parts.append(f"<{_label(arg)}>" if arg.get("required") else f"[{_label(arg)}]")
    return " ".join(parts)


def chat_commands() -> tuple:
    """The conversation's commands, in the order of its help: {"name", "usage", "help"}. The rows that list the chat
    channel, between the conversation's own two (CHAT_OWN)."""
    own = [{"name": c["name"], "usage": "/" + c["name"] + (f" <{c['args']}>" if c["args"] else ""), "help": c["help"],
            "order": c["order"]} for c in CHAT_OWN]
    rows = [{"name": r["name"], "usage": _usage(r), "help": r["help"]} for r in OPERATIONS if "chat" in r["channels"]]
    first = [{k: v for k, v in c.items() if k != "order"} for c in own if c["order"] == "first"]
    last = [{k: v for k, v in c.items() if k != "order"} for c in own if c["order"] == "last"]
    return tuple(first + rows + last)


def chat_help() -> str:
    """The text the conversation shows for /help and for a line it does not understand."""
    lines = [HELP_HEAD]
    lines += [f"{c['usage']:<{HELP_WIDTH}}{c['help']}" for c in chat_commands()]
    return "\n".join(lines)


def parse_chat(line: str):
    """One line of the conversation. None when it is not one of its commands with its arguments: the shell then shows
    the help and runs nothing. ("help", rest) and ("new", text) are the conversation's own; (name, kwargs) is an
    operation of the table that lists the chat channel, kwargs being the function's parameters. The arguments are
    read in the row's order, one word each; an integer is digits only; the last argument that is not an integer takes
    the rest of the line; anything left over, or a required argument missing, is None."""
    word, _, rest = line.partition(" ")
    if not word.startswith("/"):
        return None
    name, rest = word[1:], rest.strip()
    if name == "help":
        return ("help", rest)
    if name == "new":
        return ("new", rest) if rest else None
    try:
        row = by_name(name)
    except KeyError:
        return None
    if "chat" not in row["channels"]:
        return None
    args = [a for a in row["args"] if a["kind"] in POSITIONAL]
    kwargs = {}
    for n, arg in enumerate(args):
        if not rest:
            break
        if n == len(args) - 1 and arg["kind"] != "int":
            value, rest = rest, ""
        else:
            parts = rest.split(None, 1)
            value, rest = parts[0], (parts[1].strip() if len(parts) > 1 else "")
        if arg["kind"] == "int":
            if not (value.isascii() and value.isdigit()):
                return None
            value = int(value)
        kwargs[arg["name"]] = value
    if rest or any(a.get("required") and a["name"] not in kwargs for a in args):
        return None
    return (name, kwargs)


def _word(value) -> str:
    text = str(value)
    return text if re.fullmatch(r"<[^<>]*>", text) else shlex.quote(text)


def command_line(name: str, project: str, /, **args) -> str:
    """The terminal's form of one operation: the one place that spells the terminal's syntax. An argument that is
    None or False is left out; a value written as <placeholder> is kept as it is."""
    row = by_name(name)
    known = {a["name"] for a in row["args"]}
    unknown = sorted(set(args) - known)
    if unknown:
        raise ValueError(f"{name} has no argument {', '.join(unknown)}")
    parts = [TERMINAL, name, "--project", _word(project)]
    for arg in row["args"]:
        value = args.get(arg["name"])
        if value is None or value is False:
            continue
        flag = "--" + flag_of(arg)
        if arg["kind"] == "flag":
            parts.append(flag)
        elif arg["kind"] == "pairs":
            for key, item in value.items():
                parts += [flag, _word(f"{key}={item}")]
        else:
            parts += [flag, _word(value)]
    return " ".join(parts)


def chat_line(name: str, /, **args) -> str:
    """The conversation's form of one command, such as `/approve 12 <hash>`; what parse_chat reads back."""
    if name == "help":
        return "/help"
    if name == "new":
        return f"/new {args['text']}"
    row = by_name(name)
    parts = ["/" + name]
    for arg in row["args"]:
        if arg["kind"] not in POSITIONAL:
            continue
        value = args.get(arg["name"])
        if value is None:
            if arg.get("required"):
                raise ValueError(f"{name} needs {arg['name']}")
            break
        parts.append(str(value))
    return " ".join(parts)


if __name__ == "__main__":
    print(__doc__.strip())
    sys.exit(0 if sys.argv[1:] in (["--help"], ["-h"]) else 2)
