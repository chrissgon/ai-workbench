#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The conversation with the planning agent: one turn of it (`say`) and the memory a plain line carries to the router.

A sibling of runtime/ops.py, which exposes `say` and `chat_memory` under their names; no shell imports this file. The
names every module of the layer shares are read as `core.<name>` (runtime/ops_core.py); an operation or a helper that
stays in runtime/ops.py is reached at call time through `_ops()`, never imported at module level, so that the two
files do not import each other.

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import datetime
import importlib
import json
import os

import ops_core as core
import autonomy
import lab
import operations
import plan
import router
import skill_meta


def _ops():
    """runtime/ops.py, found at call time: the operations `say` calls and the helpers of the route stay there."""
    return importlib.import_module("ops")


# --- stage 6: the conversation with the planning agent ----------------------------------------------------------------

CONVERSATION = "project"  # one conversation per project until the local interface (stage 9)
MEMORY_TURNS = 6
MEMORY_CHARS = 4000
MEMORY_CUT = 600
MEMORY_HEAD = "Earlier in this conversation, oldest first:"
MEMORY_TAIL = "The request now:"
PLAN_NEXT = "Approve with " + operations.chat_line("approve", pending_id="{pending}")
ASK_NEXT = "Answer with a plain line, or start again with " + operations.chat_line("new", text="<text>")


def chat_memory(messages: list, settled: set) -> str:
    """The conversation's memory for the router (T23: workaround 2, the floor model's adapter takes the request as one
    argument, so the memory travels inside it, bounded): the plain lines and the router's replies after the newest
    reply whose request reached `planned`, `done` or `cancelled` (settled: those request ids); commands and their
    replies are left out. The newest MEMORY_TURNS, oldest first, each `<role>: <text>` on one line cut to MEMORY_CUT
    characters, the whole cut to MEMORY_CHARS by dropping the oldest. Empty when there is none: the first line of an
    exchange reaches the router plain."""
    # T23: workaround 2, the conversation's memory as a bounded text in the request
    start = 0
    for n, m in enumerate(messages):
        if m["role"] == "assistant" and m.get("task_id") in settled:
            start = n + 1
    kept = [m for m in messages[start:] if (m["role"] == "user" and not m["text"].startswith("/")) or
            (m["role"] == "assistant" and m.get("task_id") is not None)][-MEMORY_TURNS:]
    lines = [f"{m['role']}: {' '.join(m['text'].split())[:MEMORY_CUT]}" for m in kept]
    while lines and len("\n".join([MEMORY_HEAD, *lines])) > MEMORY_CHARS:
        lines.pop(0)
    return "\n".join([MEMORY_HEAD, *lines]) if lines else ""


def say(project: str, text: str, channel: str | None = None) -> dict:
    """One turn of the conversation with the planning agent (decision D12), one more shell of this layer. The person's
    line is stored; a line that starts with "/" is one command of the table of operations (runtime/operations.py), which calls its operation once; a plain
    line answers the router's open question on the conversation's last request, or else is a new request routed with
    the conversation's memory in front of it (one or more runs of the router: a model call), refused when the planning
    agent may not start. The reply is stored too. A model's reply is shown, never executed. A line that would route
    while another run of the project holds the run lock is refused (code 1) before the line or a request is stored.
    `channel` is the shell that carries the line (the terminal, the local page, the MCP mode; the conversation's own
    shell passes none and is `chat`): a command in the line is done only when its row lists that channel, so a shell
    that may not approve, reject, retry or cancel cannot do it by typing the command here either. Returns {"reply", "request_id", "pending_id", "ran"}."""
    ctx = core.context(project)
    said = core._text(text, "the line")
    store = ctx["store"]
    if _turn_routes(said):
        # Before anything is stored: a turn that would route during a run is refused here, so that it leaves no message
        # and no request behind (the router takes the same lock, after the line and the request would have been stored).
        with core._run_lock(ctx["cfg"]):
            pass
    core._stored(ctx, store.message_add, conversation=CONVERSATION, role="user", text=said)
    request_id, pending_id, ran, run_id = None, None, False, None
    if said.startswith("/"):
        reply, request_id, pending_id, ran, run_id = _say_command(project, ctx, said, channel or "chat")
    else:
        last = _last_request(ctx)
        asked = _router_question(ctx, last)
        if asked is not None:
            reply, request_id, pending_id, ran, run_id = _say_route(project, ctx, said, answer_to=asked)
        else:
            reply, request_id, pending_id, ran, run_id = _say_route(project, ctx, said)
    core._stored(ctx, store.message_add, conversation=CONVERSATION, role="assistant", text=reply or "(no reply)",
            task_id=request_id, run_id=run_id)
    return {"reply": reply, "request_id": request_id, "pending_id": pending_id, "ran": ran}


def _turn_routes(said: str) -> bool:
    """Whether a line makes a turn that runs the router: a plain line, or /new. A command of the table calls its own
    operation, which takes the run lock itself when it needs it, and a line that is no command gets the help."""
    if not said.startswith("/"):
        return True
    parsed = operations.parse_chat(said)
    return parsed is not None and parsed[0] == "new"


def _last_request(ctx: dict):
    """The request of the conversation's newest message that names one, or None."""
    for m in reversed(core._stored(ctx, ctx["store"].messages_list, CONVERSATION, limit=500)):
        if m.get("task_id") is not None:
            return m["task_id"]
    return None


def _router_question(ctx: dict, request_id):
    """The newest open pending decision of the request, when it is a question on the request itself (the router
    asked); else None."""
    if request_id is None:
        return None
    request = core._stored(ctx, ctx["store"].task_get, request_id)
    if request["parent_id"] is not None or request["state"] != "requested":
        return None
    open_items = core._stored(ctx, ctx["store"].pending_list, "open", request_id)
    return open_items[-1]["id"] if open_items and open_items[-1]["kind"] == "question" else None


def _say_command(project: str, ctx: dict, said: str, channel: str = "chat") -> tuple:
    """(reply, request_id, pending_id, ran, run_id) of a command line: the table of operations reads it
    (operations.parse_chat); an operation it names is called once with the arguments it read and the channel `chat`
    (so an effect is never approved from a line), when its row lists the channel that carries the line (`channel`):
    a command that row does not list is refused with the place where it is done, and a line it does not read gets
    the help."""
    parsed = operations.parse_chat(said)
    if parsed is None or parsed[0] == "help":
        return operations.chat_help(), None, None, False, None
    name, found = parsed
    if name == "new":
        after, found = operations.split_new(found)
        return _say_route(project, ctx, found, after=after)
    row = operations.by_name(name)
    if channel not in row["channels"]:
        return f"error: /{name} is done in the terminal or on the page", None, None, False, None
    if row.get("channel_arg"):
        found = dict(found, channel="chat")
    try:
        out = getattr(_ops(), row["call"])(project, **found)
    except core.OpsError as e:
        return f"error: {e}", None, None, False, None
    if row.get("chat_reply"):
        return out[row["chat_reply"]], None, None, False, None
    return json.dumps(out, ensure_ascii=False, indent=1, default=str), None, None, False, None


def _planning_may_start(ctx: dict) -> tuple:
    """Whether the planning agent may run the router now (autonomy.may_start, on the tier the router's proof gives,
    with the day's runs of the router counted against it)."""
    cfg, store = ctx["cfg"], ctx["store"]
    agents = cfg["area_agents"]
    meta = skill_meta.declared(os.path.join(core.ROOT, "skills", router.ROUTER_SKILL))
    tier = _ops()._route(ctx, router.ROUTER_SKILL, meta, None, core._floor_key())["tier"]
    now = datetime.datetime.now(datetime.timezone.utc)
    standing_rows = core._stored(ctx, store.approvals_list, status="active", scope="standing")
    runs = [dict(r, agent=plan.PLANNING) if r.get("agent") is None and r.get("skill") == router.ROUTER_SKILL else r
            for r in core._stored(ctx, store.runs_since, _ops()._midnight_utc())]
    facts = autonomy.facts(plan.PLANNING, agents, standing_rows, now)
    spent = autonomy.spend(runs, plan.PLANNING, lab.reference("strong")["model"], lab.reference("floor")["model"],
                           cfg["raw"].get("max_cost_usd_per_run", _ops().PER_RUN_USD))
    ok, why = autonomy.may_start(plan.PLANNING, agents, facts, spent, tier)
    if not ok and plan.PLANNING not in agents:
        why = "no planning agent is configured (area_agents has no entry named planning)"
    return ok, why


def _say_route(project: str, ctx: dict, said: str, answer_to=None, after=None) -> tuple:
    """A plain line: the answer to the router's question (then the router runs again), or a new request with the
    memory in front of it. Either way the router runs only when the planning agent may start."""
    ok, why = _planning_may_start(ctx)
    if not ok:
        return f"The planning agent may not start now: {why}. Nothing was run.", None, None, False, None
    if answer_to is not None:
        request_id = core._stored(ctx, ctx["store"].pending_get, answer_to)["task_id"]
        _ops().answer(project, answer_to, said)
    else:
        messages = core._stored(ctx, ctx["store"].messages_list, CONVERSATION, limit=500)[:-1]  # not the line just stored
        settled = {t["id"] for t in core._stored(ctx, ctx["store"].tasks_list)
                   if t["parent_id"] is None and t["state"] in ("planned", "done", "cancelled")}
        remembered = chat_memory(messages, settled)
        text = f"{remembered}\n\n{MEMORY_TAIL}\n{said}" if remembered else said
        request_id = _ops().request(project, text, title=plan.title_of(said), after=after)["request"]
    routed = _ops().route(project, request_id)
    item = core._stored(ctx, ctx["store"].pending_get, routed["pending_id"]) if routed.get("pending_id") else None
    if item is None:
        failure = (routed.get("failure") or {}).get("reason") or "the router's run failed"
        return f"The router could not run: {failure}", request_id, None, True, routed.get("run_id")
    if item["kind"] == "plan":
        payload = item["payload"]
        lines = [item["title"]]
        lines += [f"- {t['key']}: {t['title']} ({t['skill']})" for t in payload.get("tasks") or []]
        estimate = payload.get("estimate") or {}
        lines += [f"Estimate: {estimate.get('runs', estimate.get('runs_at_least'))} runs"
                  + (f" ({estimate['formula']})" if estimate.get("formula") else ""), ""]
        for n, u in enumerate(payload.get("unrouted") or [], 1):
            lines += [f"Not planned {n}: {u['item']}. The router's reply:", u["reply"].rstrip("\n"), ""]
        lines.append(PLAN_NEXT.format(pending=item["id"]))
        reply = "\n".join(lines)
    else:
        reply = item["body"].rstrip("\n") + "\n\n" + ASK_NEXT
    return reply, request_id, item["id"], True, routed.get("run_id")
