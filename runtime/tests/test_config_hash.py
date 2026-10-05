"""Tests of the configuration's hash (runtime/ops.py, runtime/project_config.py): no operation runs on a
docs/workbench/runtime.json the person did not accept by its hash, and only accept_config records that hash.
Offline: the stand-in tree (runtime/tests/standin_tree.py).

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_config_hash.py
"""
from __future__ import annotations

import json

import pytest

import standin_tree as st

lab = st.load("lab")
ops = st.load("ops")
cli = st.load("cli")
project_config = st.load("project_config")


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """The stand-in tree and project, with a configuration nobody accepted yet."""
    built = st.build(tmp_path, monkeypatch, lab)
    monkeypatch.setattr(ops, "ROOT", str(built["tree"]))
    return built


def sha(tree) -> str:
    return project_config.load(str(tree["project"]))["sha256"]


def refused(call, *needles) -> None:
    with pytest.raises(ops.OpsError) as raised:
        call()
    assert raised.value.code == 3, str(raised.value)
    for needle in needles:
        assert needle in str(raised.value)


def test_no_operation_runs_before_the_person_accepted_the_configuration(tree):
    path, digest = str(tree["project"]), sha(tree)
    for call in (lambda: ops.request(path, "Tell me which market to go after first.", "demo"),
                 lambda: ops.run_next(path), lambda: ops.pending(path), lambda: ops.pending(path, 1),
                 lambda: ops.answer(path, 1, "yes"), lambda: ops.release(path, 1), lambda: ops.retry(path, 1),
                 lambda: ops.cancel(path, 1), lambda: ops.status(path)):
        refused(call, digest, "accept-config", "none: no configuration was accepted yet")
    assert st.calls(tree["adapter"]) == []


def test_accepting_takes_the_hash_the_person_typed_and_refuses_another(tree):
    path, digest = str(tree["project"]), sha(tree)
    with pytest.raises(ops.OpsError) as raised:
        ops.accept_config(path, "0" * 64)
    assert raised.value.code == 1 and "nothing was accepted" in str(raised.value)
    refused(lambda: ops.status(path), "none: no configuration was accepted yet")
    out = ops.accept_config(path, digest)
    assert (out["accepted"], out["previous"]) == (digest, None) and out["path"].endswith("docs/workbench/runtime.json")
    assert ops.status(path)["config"]["sha256"] == digest


def test_a_configuration_that_changed_after_it_was_accepted_stops_every_operation_and_names_both_hashes(tree):
    path, old = str(tree["project"]), sha(tree)
    ops.accept_config(path, old)
    with open(project_config.path(path), "ab") as f:
        f.write(b" ")
    new = sha(tree)
    assert new != old
    refused(lambda: ops.status(path), old, new)
    refused(lambda: ops.request(path, "x", "demo"), old, new)
    assert ops.accept_config(path, new)["previous"] == old
    assert ops.status(path)["config"]["sha256"] == new


def test_the_shell_exposes_accept_config_and_exits_3_on_a_configuration_that_was_not_accepted(tree, capsys):
    path, digest = str(tree["project"]), sha(tree)
    assert cli.main(["status", "--project", path]) == 3
    captured = capsys.readouterr()
    assert captured.out == "" and digest in captured.err and "accept-config" in captured.err
    assert cli.main(["accept-config", "--project", path, "--sha256", digest]) == 0
    assert json.loads(capsys.readouterr().out)["accepted"] == digest
    assert cli.main(["status", "--project", path]) == 0
    assert json.loads(capsys.readouterr().out)["config"]["sha256"] == digest
    assert cli.main(["accept-config", "--project", path]) == 2  # --sha256 is required


def test_protected_paths_is_a_list_of_globs_or_absent(tree):
    path = str(tree["project"])
    file = project_config.path(path)
    good = json.loads(open(file, encoding="utf-8").read())
    assert project_config.load(path)["protected_paths"] == []
    with open(file, "w", encoding="utf-8") as f:
        json.dump({**good, "protected_paths": ["AGENTS.md", "docs/legal/*"]}, f)
    assert project_config.load(path)["protected_paths"] == ["AGENTS.md", "docs/legal/*"]
    for bad in ("AGENTS.md", ["AGENTS.md", ""], [1]):
        with open(file, "w", encoding="utf-8") as f:
            json.dump({**good, "protected_paths": bad}, f)
        with pytest.raises(project_config.ConfigError) as raised:
            project_config.load(path)
        assert "protected_paths must be a list of path globs" in str(raised.value)
