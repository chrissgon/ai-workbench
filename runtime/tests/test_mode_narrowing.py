"""Tests of the page narrowing autonomy (WP-9.14, item A-17): `set-mode` to a mode lower in the order stopped <
supervised < milestones < autonomous < autonomous-with-policy is accepted by code at once, recorded as
`code:narrowing`, so nothing refuses afterwards; to a higher one it leaves the hash unaccepted and returns the
command, and no code path accepts a widening. Offline; invented names.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_mode_narrowing.py
"""
from __future__ import annotations

import ast
import itertools
import json

import pytest

import standin_tree as st
from test_autonomy import tree  # noqa: F401  (planning supervised, brand autonomous; the configuration accepted)

autonomy = st.load("autonomy")
ops = st.load("ops")
project_config = st.load("project_config")

ORDER = ("stopped", "supervised", "milestones", "autonomous", "autonomous-with-policy")
PAIRS = list(itertools.product(ORDER, ORDER))


def config_path(tree):
    return tree["project"] / "docs" / "workbench" / "runtime.json"


def put(tree, agent, mode):
    """The agent in this mode, in the file, accepted by the person: the starting point of a test."""
    raw = json.loads(config_path(tree).read_text(encoding="utf-8"))
    raw["area_agents"][agent]["mode"] = mode
    config_path(tree).write_text(json.dumps(raw), encoding="utf-8")
    project = str(tree["project"])
    ops.accept_config(project, project_config.load(project)["sha256"])


def cursor(tree, name):
    ctx = ops.context(str(tree["project"]), check_config=False)
    return ctx["store"].cursor_get(ctx["conn"], name)


def test_the_order_of_the_modes_is_data_in_autonomy():
    assert autonomy.MODES == ORDER
    for old, new in PAIRS:
        assert autonomy.narrows(old, new) is (ORDER.index(new) < ORDER.index(old)), (old, new)
    with pytest.raises(ValueError):
        autonomy.narrows("autonomous", "turbo")


@pytest.mark.parametrize("old,new", PAIRS)
def test_a_move_down_the_order_is_accepted_by_code_and_a_move_up_never_is(tree, old, new):
    project = str(tree["project"])
    put(tree, "brand", old)
    accepted_before = cursor(tree, project_config.ACCEPTED)
    out = ops.set_mode(project, "brand", new)
    after = project_config.load(project)
    if old == new:
        assert out["accepted"] is True and out["unchanged"] is True and out["next"] is None
        assert out["config_sha256"] == accepted_before  # the file was not rewritten
    elif ORDER.index(new) < ORDER.index(old):
        assert out["accepted"] is True and out["by"] == "code:narrowing" and out["next"] is None
        assert cursor(tree, project_config.ACCEPTED) == after["sha256"] == out["config_sha256"]
        assert cursor(tree, ops.ACCEPTED_BY) == "code:narrowing"
        assert ops.status(project)["config"]["sha256"] == after["sha256"]  # no route refuses afterwards
        assert ops.config(project)["accepted"] is True
    else:
        assert out["accepted"] is False and out["by"] is None
        assert "runtime/cli.py accept-config" in out["next"] and out["config_sha256"] in out["next"]
        assert cursor(tree, project_config.ACCEPTED) == accepted_before != after["sha256"]  # the hash stays unaccepted
        with pytest.raises(ops.OpsError) as refused:
            ops.status(project)
        assert refused.value.code == 3
        assert ops.config(project)["accepted"] is False
    assert after["area_agents"]["brand"]["mode"] == new


def test_a_narrowing_writes_the_state_file_s_checkpoints_line_as_the_person_s_acceptance_does(tree):
    project = str(tree["project"])
    state = tree["project"] / "docs" / "workbench" / "state.md"
    put(tree, "planning", "milestones")
    put(tree, "brand", "milestones")
    ops.accept_config(project, project_config.load(project)["sha256"])
    assert "- Checkpoints: milestones" in state.read_text(encoding="utf-8")
    out = ops.set_mode(project, "planning", "supervised")
    assert out["accepted"] is True and out["checkpoints"] == {"written": True, "value": "every-phase"}
    assert "- Checkpoints: every-phase" in state.read_text(encoding="utf-8")


def test_a_configuration_edited_by_hand_and_not_accepted_is_never_accepted_by_a_narrowing(tree):
    project = str(tree["project"])
    raw = json.loads(config_path(tree).read_text(encoding="utf-8"))
    raw["area_agents"]["brand"]["max_runs_per_day"] = 99  # a widening of a cap, edited in the file
    config_path(tree).write_text(json.dumps(raw), encoding="utf-8")
    before = config_path(tree).read_text(encoding="utf-8")
    with pytest.raises(ops.OpsError) as refused:
        ops.set_mode(project, "planning", "stopped")
    assert refused.value.code == 3 and config_path(tree).read_text(encoding="utf-8") == before


def test_a_narrowing_that_finds_the_file_changed_under_it_is_not_accepted(tree, monkeypatch):
    project = str(tree["project"])
    real = project_config.load
    calls = {"n": 0}

    def load(path):
        calls["n"] += 1
        if calls["n"] == 2:  # the read after the write: someone else edited the file in between
            raw = json.loads(config_path(tree).read_text(encoding="utf-8"))
            raw["area_agents"]["brand"]["max_runs_per_day"] = 99
            config_path(tree).write_text(json.dumps(raw), encoding="utf-8")
        return real(path)

    accepted_before = cursor(tree, project_config.ACCEPTED)
    monkeypatch.setattr(ops.project_config, "load", load)
    out = ops.set_mode(project, "brand", "stopped")
    assert out["accepted"] is False and "accept-config" in out["next"]
    assert cursor(tree, project_config.ACCEPTED) == accepted_before


def test_the_acceptance_cursor_is_written_by_one_function_that_two_operations_call_and_a_narrowing_guards():
    tree_ = ast.parse((st.RUNTIME / "ops.py").read_text(encoding="utf-8"))
    functions = {f.name: f for f in ast.walk(tree_) if isinstance(f, ast.FunctionDef)}
    writers = [name for name, f in functions.items() for n in ast.walk(f)
               if isinstance(n, ast.Call) and "cursor_set" in ast.unparse(n) and "project_config.ACCEPTED" in ast.unparse(n)]
    assert writers == ["_record_acceptance"], writers
    callers = sorted(name for name, f in functions.items() for n in ast.walk(f)
                     if isinstance(n, ast.Call) and ast.unparse(n.func) == "_record_acceptance")
    assert callers == ["accept_config", "set_mode"], callers
    guarded = [n for n in ast.walk(functions["set_mode"]) if isinstance(n, ast.If)
               and "autonomy.narrows" in ast.unparse(n.test)
               and any(isinstance(c, ast.Call) and ast.unparse(c.func) == "_record_acceptance" for b in n.body for c in ast.walk(b))]
    assert len(guarded) == 1  # the only call inside set_mode sits under the narrowing test
    inside = [n for n in ast.walk(functions["set_mode"]) if isinstance(n, ast.Call) and ast.unparse(n.func) == "_record_acceptance"]
    assert len(inside) == 1


def test_no_other_operation_writes_the_cursor_of_the_accepted_hash():
    sources = {p.name: p.read_text(encoding="utf-8") for p in st.RUNTIME.glob("*.py")}
    holders = sorted(name for name, text in sources.items() if "ACCEPTED" in text and "cursor_set" in text)
    assert holders == ["ops.py"], holders


def test_from_the_page_a_narrowing_is_accepted_and_the_next_read_succeeds_and_a_widening_is_refused_with_the_command(tree, monkeypatch):
    import types
    monkeypatch.setenv("WORKBENCH_STARTED_WITH_UV", "0")
    import test_service as ts
    project = str(tree["project"])
    projects = [{"id": ts.service.project_id(project), "name": "p", "path": project}]
    world = types.SimpleNamespace(svc=ts.service.Service(ops, projects, ts.TOKEN, ts.PORT, None, log=lambda line: None), projects=projects)
    put(tree, "brand", "milestones")
    status, _, body = ts.call(world, "POST", ts.api(world, "/agents/brand/mode"), {"mode": "supervised"})
    assert status == 200 and body["accepted"] is True and body["by"] == "code:narrowing" and body["next"] is None
    assert ts.call(world, "GET", ts.api(world, "/status"))[0] == 200  # a read that succeeds
    status, _, body = ts.call(world, "POST", ts.api(world, "/agents/brand/mode"), {"mode": "autonomous"})
    assert status == 200 and body["accepted"] is False and "accept-config" in body["next"]
    status, _, refused = ts.call(world, "GET", ts.api(world, "/status"))
    assert status == 412 and body["next"] in refused["message"]  # the refusal names the same absolute command
    assert body["next"].startswith(f"python3 {tree['tree']}/runtime/cli.py accept-config")
