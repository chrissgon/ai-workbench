"""Tests of the change signal of the local interface (WP-9.13): the `version` operation of runtime/ops.py, its row in the
table of operations, its route on the local service and the service's aggregate route, so that a page can tell with one
cheap read whether anything was written to a project's store since it last looked. Offline; invented names.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_live_version.py
"""
from __future__ import annotations

import datetime
import json
import os
import re

import pytest

import standin_tree as st
from test_read_ops import planned, stored, tree  # noqa: F401  (the stand-in project of test_read_ops.py)
from test_service import PORT, TOKEN, Standin, STATUS, call, world  # noqa: F401  (the stand-in service of test_service.py)

ops = st.load("ops")
operations = st.load("operations")
service = st.load("service")

ISO = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z")


def number(path: str) -> int:
    return ops.version(path)["version"]


# --- the operation -------------------------------------------------------------------------------------------------------


def test_version_returns_a_whole_number_and_the_time_of_the_last_write(tree):
    path = str(tree["project"])
    found = ops.version(path)
    assert set(found) == {"version", "changed_at"}
    assert type(found["version"]) is int and found["version"] >= 0
    assert ISO.fullmatch(found["changed_at"]), found["changed_at"]
    assert datetime.datetime.strptime(found["changed_at"], "%Y-%m-%dT%H:%M:%S.%fZ") <= datetime.datetime.utcnow() + datetime.timedelta(seconds=2)


def test_reading_changes_nothing_so_the_number_stays_while_nobody_writes(tree):
    path = str(tree["project"])
    planned(tree, "single")
    first = ops.version(path)
    for read in (ops.status, ops.agents, ops.pending, ops.flows, ops.artifacts, ops.conversation, ops.config, ops.skills):
        read(path)
    again = ops.version(path)
    assert again["version"] == first["version"] and again["changed_at"] == first["changed_at"]


def test_the_number_grows_on_every_kind_of_write(tree):
    path = str(tree["project"])
    (tree["tree"] / "flows" / "ask.json").write_text(json.dumps({"flow": "ask", "title": "Ask", "tasks": [
        {"key": "market", "skill": "demo-asks", "title": "Market", "text": "study the market."}]}), encoding="utf-8")
    seen = [number(path)]

    def moved(label):
        seen.append(number(path))
        assert seen[-1] > seen[-2], f"{label} did not raise the version: {seen}"

    request = ops.request(path, "Add a sale page.", title="Sale page")["request"]
    moved("a request")
    pending_id = ops.route(path, request, "ask")["pending_id"]
    moved("a plan (a decision opens)")
    ops.approve(path, pending_id, ops.pending(path, pending_id)["payload"]["plan_sha256"])
    moved("an approval")
    out = ops.run_next(path)
    assert out["ending"] == "question"
    moved("a run that ends in a question (the run, the task and a decision)")
    ops.answer(path, out["pending_id"], "For people who knit.")
    moved("an answer")
    ops.run_next(path)
    moved("a second run")
    ops.say(path, "/status")
    moved("a conversation message")
    ops.cancel(path, request)
    moved("a cancellation")


def test_the_number_is_a_property_of_the_project_not_of_the_process(tree):
    path = str(tree["project"])
    before = number(path)
    store, conn = stored(tree)                       # another connection, as the terminal's process or a loop's thread is
    store.message_add(conn, conversation=ops.CONVERSATION, role="user", text="from the terminal")
    assert number(path) == before + 1


def test_it_refuses_a_configuration_nobody_accepted_yet_as_every_operation_does(tree):
    path = str(tree["project"])
    runtime = tree["project"] / "docs" / "workbench" / "runtime.json"
    raw = json.loads(runtime.read_text(encoding="utf-8"))
    raw["area_agents"]["business"]["max_runs_per_day"] = 4
    runtime.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ops.OpsError) as status_refused:
        ops.status(path)
    with pytest.raises(ops.OpsError) as version_refused:
        ops.version(path)
    assert version_refused.value.code == status_refused.value.code == 3
    assert "accept-config" in str(version_refused.value)
    ops.accept_config(path, ops.project_config.load(path)["sha256"])
    assert type(ops.version(path)["version"]) is int


def test_it_reads_the_accepted_hash_and_the_header_and_nothing_else(tree, monkeypatch):
    path = str(tree["project"])
    planned(tree, "single")
    store = ops.store_module()
    statements = []
    real = store.connect

    def traced(db_path):
        conn = real(db_path)
        conn.set_trace_callback(statements.append)
        return conn

    monkeypatch.setattr(store, "connect", traced)
    monkeypatch.setattr(store, "init_db", lambda *a, **k: pytest.fail("a read at rest migrates nothing"))
    ops.version(path)
    reads = [s for s in statements if s not in ("BEGIN IMMEDIATE", "COMMIT")]
    assert len(reads) == 2 and reads[0].startswith("SELECT value FROM cursors") and reads[1] == "PRAGMA user_version", reads
    assert not any(s.split()[0] in ("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER") for s in statements)


def test_a_project_whose_store_does_not_exist_yet_gets_one_made_and_must_accept_its_configuration_again(tree):
    path = str(tree["project"])
    db = ops.project_config.load(path)["store_db"]
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(db + suffix):
            os.remove(db + suffix)
    with pytest.raises(ops.OpsError) as refused:
        ops.version(path)
    assert refused.value.code == 3 and os.path.isfile(db), "the record of the acceptance was in the store that is gone"
    ops.accept_config(path, ops.project_config.load(path)["sha256"])
    assert type(ops.version(path)["version"]) is int


# --- its row in the table of operations ----------------------------------------------------------------------------------


def test_the_table_has_one_row_for_it_listing_the_page_and_the_mcp_channels_and_no_model():
    row = operations.by_name("version")
    assert row["call"] == "version" and row["args"] == () and set(row["channels"]) == {"page", "mcp"}
    assert row["model"] is False and not row.get("job") and not row.get("channel_arg")
    assert "terminal" not in row["channels"] and "chat" not in row["channels"]


# --- its routes on the local service -------------------------------------------------------------------------------------


def test_the_service_has_the_route_of_the_operation_and_the_aggregate_one():
    found = {(r["method"], r["pattern"]): r for r in service.ROUTES}
    route = found[("GET", "/projects/{p}/version")]
    assert route["op"] == "version" and route["take"] == () and not route["bind"]
    assert found[("GET", "/versions")]["own"] == "versions"


def test_the_version_route_needs_the_token_and_returns_what_the_operation_returned(world):
    world.fake.answers["version"] = {"version": 41, "changed_at": "2026-10-08T12:00:00.000000Z"}
    path = f"/api/v1/projects/{world.projects[0]['id']}/version"
    assert call(world, "GET", path, auth=False)[0] == 401
    assert world.fake.named("version") == []
    status, headers, body = call(world, "GET", path)
    assert status == 200 and body == {"version": 41, "changed_at": "2026-10-08T12:00:00.000000Z"}
    assert headers["Cache-Control"] == "no-store"
    assert world.fake.named("version") == [("version", world.projects[0]["path"], {})]
    assert call(world, "GET", path + "?after=3")[0] == 400, "the route takes no query"
    assert call(world, "POST", path, {})[0] == 405
    assert call(world, "GET", "/api/v1/projects/000000000000/version")[0] == 404


def test_the_aggregate_route_answers_for_every_project_in_one_request(world):
    def answer(project, **kwargs):
        return {"version": 7 if project.endswith("alpha") else 9, "changed_at": "2026-10-08T12:00:00.000000Z"}

    world.fake.answers["version"] = answer
    status, headers, body = call(world, "GET", "/api/v1/versions", auth=False)
    assert status == 401
    status, headers, body = call(world, "GET", "/api/v1/versions")
    assert status == 200 and headers["Cache-Control"] == "no-store"
    assert body == {"versions": {world.projects[0]["id"]: {"version": 7, "changed_at": "2026-10-08T12:00:00.000000Z"},
                                 world.projects[1]["id"]: {"version": 9, "changed_at": "2026-10-08T12:00:00.000000Z"}}}
    assert [c[0] for c in world.fake.calls] == ["version", "version"], "one operation per project, nothing else"
    assert call(world, "GET", "/api/v1/versions?x=1")[0] == 400
    assert call(world, "POST", "/api/v1/versions", {})[0] == 405


def test_one_project_that_cannot_be_read_does_not_hide_the_others(world):
    def answer(project, **kwargs):
        if project.endswith("beta"):
            raise ops.OpsError("the configuration names another checkout", 3)
        return {"version": 5, "changed_at": "2026-10-08T12:00:00.000000Z"}

    world.fake.answers["version"] = answer
    status, _, body = call(world, "GET", "/api/v1/versions")
    assert status == 200
    assert body["versions"][world.projects[0]["id"]]["version"] == 5
    assert body["versions"][world.projects[1]["id"]] == {"error": "the configuration names another checkout"}
