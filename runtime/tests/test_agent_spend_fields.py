"""Tests of the fields the page needs for the meters, the wider modes and the credential (WP-9.14b): the day's spend
split into what was recorded and what is reserved, every run of the day, the commands of the wider modes, the command
in the 412 body, and the `next` of the held reasons `credential` and `secret store`. Offline; invented names.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_agent_spend_fields.py
"""
from __future__ import annotations

import json
import types

import pytest

import standin_tree as st
from test_read_ops import tree  # noqa: F401  (business, engineering and design agents; the floor tier has a model of its own)

autonomy = st.load("autonomy")
dispatcher = st.load("dispatcher")
lab = st.load("lab")
ops = st.load("ops")
operations = st.load("operations")

RUNS = [{"agent": "brand", "model": "ref", "cost_usd": None}, {"agent": "brand", "model": "ref", "cost_usd": 0.4},
        {"agent": "brand", "model": "floor", "cost_usd": 0.03}, {"agent": "brand", "model": "floor", "cost_usd": None},
        {"agent": "brand", "model": "another", "cost_usd": 0.01}, {"agent": "business", "model": "ref", "cost_usd": 0.2},
        {"agent": None, "model": "floor", "cost_usd": 0.5}]


@pytest.fixture(autouse=True)
def plain(monkeypatch):
    monkeypatch.setenv(operations.UV_MARK, "0")
    ops.SERVICE.clear()


# --- 1: the spend split ----------------------------------------------------------------------------------------------


def test_the_floor_spend_is_split_into_recorded_and_reserved_and_adds_up_to_what_the_cap_compares():
    split = autonomy.spend_split(RUNS, "brand", "floor", 0.5)
    assert split == {"usd_recorded": 0.03, "usd_reserved": 0.5, "runs_total": 5}
    spent = autonomy.spend(RUNS, "brand", "ref", "floor", 0.5)
    assert round(split["usd_recorded"] + split["usd_reserved"], 6) == spent["usd_floor"]
    assert autonomy.spend_split(RUNS, "business", "floor", 0.5) == {"usd_recorded": 0.0, "usd_reserved": 0.0, "runs_total": 1}
    assert autonomy.spend_split(RUNS, "nobody", "floor", 0.5) == {"usd_recorded": 0.0, "usd_reserved": 0.0, "runs_total": 0}


def seed_runs(tree, rows):
    """Runs of today for the business agent's task (a plan of the business pack makes one), as the stored rows."""
    import datetime
    from test_read_ops import planned
    path = str(tree["project"])
    planned(tree, "single")
    ctx = ops.context(path)
    task = next(t for t in ctx["store"].tasks_list(ctx["conn"]) if t["parent_id"] is not None)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    for model, cost in rows:
        ctx["conn"].execute("INSERT INTO task_runs (task_id, skill, model, adapter, status, started_at, cost_usd) VALUES (?, ?, ?, 'h', 'ok', ?, ?)",
                            (task["id"], task["skill"], model, now, cost))
    ctx["conn"].commit()


def test_agents_carry_the_split_the_total_and_keep_usd_today(tree):
    path = str(tree["project"])
    first = ops.agents(path)["agents"][0]
    assert (first["usd_recorded"], first["usd_reserved"], first["usd_today"], first["runs_total_today"]) == (0.0, 0.0, 0.0, 0)
    seed_runs(tree, [("m", None), ("fm", 0.4), ("fm", None), ("other", 0.1)])
    got = ops.agents(path)["agents"][0]
    assert got["runs_today"] == 2 and got["runs_total_today"] == 4  # the reference model's runs; every run of any model
    assert got["usd_recorded"] == pytest.approx(0.4) and got["usd_reserved"] == pytest.approx(ops.PER_RUN_USD)
    assert got["usd_today"] == pytest.approx(got["usd_recorded"] + got["usd_reserved"]) and got["runs_without_cost"] == 1


def test_costs_caps_carry_the_same_words_as_agents(tree):
    path = str(tree["project"])
    seed_runs(tree, [("fm", 0.4), ("fm", None)])
    agents = {a["name"]: a for a in ops.agents(path)["agents"]}
    caps = {c["agent"]: c for c in ops.costs(path)["caps"]}
    assert set(caps) == set(agents)
    for name, row in caps.items():
        assert row["max_runs_per_day"] == agents[name]["max_runs_per_day"] and row["max_usd_per_day"] == agents[name]["max_usd_per_day"]
        for key in ("runs_today", "usd_today", "usd_recorded", "usd_reserved", "runs_without_cost", "runs_total_today"):
            assert row[key] == agents[name][key], (name, key)


# --- 2: the wider modes ----------------------------------------------------------------------------------------------


def test_each_agent_lists_every_mode_above_its_own_with_the_absolute_command(tree):
    path = str(tree["project"])
    order = list(autonomy.MODES)
    for agent in ops.agents(path)["agents"]:
        above = order[order.index(agent["mode"]) + 1:]
        assert [w["mode"] for w in agent["wider"]] == above, agent["name"]
        for w in agent["wider"]:
            assert w["command"] == (f"python3 {tree['tree']}/runtime/cli.py set-mode --project {path} --agent {agent['name']} "
                                    f"--mode {w['mode']}")
    top = [a for a in ops.agents(path)["agents"] if a["mode"] == "autonomous-with-policy"]
    assert top and all(a["wider"] == [] for a in top)


def test_the_wider_commands_carry_the_uv_prefix_when_the_process_was_started_that_way(tree, monkeypatch):
    monkeypatch.setenv(operations.UV_MARK, "1")
    wider = ops.agents(str(tree["project"]))["agents"][0]["wider"]
    assert wider and all(w["command"].startswith("uv run --with keyring==25.7.0 python3 ") for w in wider)


# --- 3: the 412 body -------------------------------------------------------------------------------------------------


def test_the_412_body_carries_the_accept_config_command_beside_the_message(tree):
    import test_service as ts
    path = str(tree["project"])
    config = tree["project"] / "docs" / "workbench" / "runtime.json"
    config.write_text(config.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    projects = [{"id": ts.service.project_id(path), "name": "p", "path": path}]
    world = types.SimpleNamespace(svc=ts.service.Service(ops, projects, ts.TOKEN, ts.PORT, None, log=lambda line: None), projects=projects)
    status, _, body = ts.call(world, "GET", ts.api(world, "/status"))
    sha = ops.project_config.load(path)["sha256"]
    assert status == 412 and body["error"] == "not_configured"
    assert body["next"] == f"python3 {tree['tree']}/runtime/cli.py accept-config --project {path} --sha256 {sha}"
    assert body["next"] in body["message"]
    with pytest.raises(ops.OpsError) as refused:
        ops.status(path)
    assert refused.value.next == body["next"]
    assert ops.OpsError("x", 1).next is None  # an error with no command has none
    assert set(ts.call(world, "GET", "/api/v1/projects/" + "0" * 12 + "/status")[2]) == {"error", "message"}  # others keep two keys


# --- 4: held.next for the credential ---------------------------------------------------------------------------------


def test_a_missing_credential_with_a_readable_store_says_where_it_is_stored(tree, monkeypatch):
    path = str(tree["project"])
    from test_read_ops import planned
    planned(tree, "single")
    monkeypatch.setattr(lab, "credential_missing", lambda tier: ["EXAMPLE_REFERENCE_KEY"])
    monkeypatch.setattr(dispatcher, "store_readable", lambda: "ok")
    monkeypatch.setattr(lab, "reference", lambda tier="strong": {
        "tier": tier, "model": "m", "adapter": "h", "pass_env": ["EXAMPLE_REFERENCE_KEY"], "timeout_seconds": 60, "retries": 2,
        "control": {"total_jobs": 2, "web_jobs": {"strong": 1, "floor": 1}}})
    ops.dispatch(path)
    [entry] = [h for h in ops.status(path)["held"] if h["reason"] == "credential"]
    text = entry["next"]
    assert "EXAMPLE_REFERENCE_KEY" in text and "keyring set ai-workbench" in text and "the `secrets` list" in text
    assert "contracts/secrets.md" in text
    assert not any(ch in text for ch in "\n\r")


def test_an_unreadable_secret_store_still_gets_the_service_start_line(tree):
    line = ops._held_next(str(tree["project"]), "secret store")
    assert line.startswith("uv run --with keyring==25.7.0 python3 ") and line.endswith(f"--project {tree['project']}")
    assert ops._held_next(str(tree["project"]), "stopped") is None


def test_a_job_that_fails_with_a_command_carries_it_in_its_error(tree):
    import test_service as ts
    path = str(tree["project"])
    projects = [{"id": ts.service.project_id(path), "name": "p", "path": path}]
    world = types.SimpleNamespace(svc=ts.service.Service(ops, projects, ts.TOKEN, ts.PORT, None, log=lambda line: None), projects=projects)

    def refuse():
        raise ops.OpsError("nope", 3, next="python3 /w/runtime/cli.py accept-config --project /p --sha256 ab")

    job = world.svc.start_job(projects[0]["id"], "sync", refuse)[1]
    job.join(10)
    error = world.svc.job_shown(1)["error"]
    assert error["error"] == "not_configured" and error["next"].startswith("python3 /w/runtime/cli.py accept-config")
