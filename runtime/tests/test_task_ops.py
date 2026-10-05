"""Tests of the operations layer (runtime/ops.py) and of its terminal shell (runtime/cli.py): a request becomes
two tasks, each runs when it is ready, the person answers and releases, and the documents come back by the
path rule. Offline: a stand-in adapter and two invented skills (runtime/tests/standin_tree.py).

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_task_ops.py
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import sys

import pytest

import standin_tree as st

lab = st.load("lab")
ops = st.load("ops")
cli = st.load("cli")


@pytest.fixture
def tree(tmp_path, monkeypatch):
    built = st.build(tmp_path, monkeypatch, lab)
    monkeypatch.setattr(ops, "ROOT", str(built["tree"]))
    project = str(built["project"])
    ops.accept_config(project, ops.project_config.load(project)["sha256"])  # the person accepted the configuration
    return built


def project_of(tree) -> str:
    return str(tree["project"])


def requested(tree) -> dict:
    return ops.request(project_of(tree), "Tell me which market to go after first.", "demo")


def test_a_request_becomes_the_tasks_of_its_flow_file_and_only_the_first_is_ready(tree):
    out = requested(tree)
    assert out["flow"] == "demo" and out["state"] == "planned"
    assert [(t["key"], t["skill"], t["state"]) for t in out["tasks"]] == [("market", "demo-asks", "ready"),
                                                                           ("profile", "demo-writes", "planned")]
    seen = ops.status(project_of(tree))
    assert seen["requests"][0]["title"] == "Demo flow" and len(seen["requests"][0]["tasks"]) == 2 and seen["pending"] == []
    assert len(seen["config"]["sha256"]) == 64


def test_the_whole_path_of_a_request_ask_answer_write_release_and_the_next_task(tree):
    project, path = tree["project"], project_of(tree)
    requested(tree)
    # 1. The first run stops to ask: nothing comes back, and the task waits on a question.
    first = ops.run_next(path)
    assert (first["skill"], first["status"], first["ending"], first["task_state"]) == ("demo-asks", "ok", "question", "waiting")
    assert first["returned"] == [] and first["left_out"] == [{"path": "AGENTS.md", "reason": "not copied in stage 1"}]
    item = ops.pending(path, first["pending_id"])
    assert item["kind"] == "question" and item["body"].startswith("Nothing was searched or written yet")
    assert ops.run_next(path)["reason"] == "no task is ready"  # a waiting task does not run
    with pytest.raises(ops.OpsError):
        ops.release(path, first["pending_id"])  # a question is answered, never released
    # 2. The answer makes the task ready; the new run is a fresh copy whose prompt carries the reply and the answer.
    assert ops.answer(path, first["pending_id"], "Portugal, remote.\r\nFree sources only.")["task_state"] == "ready"
    second = ops.run_next(path)
    assert (second["status"], second["ending"], second["task_state"]) == ("ok", "done", "waiting")
    prompt = open(os.path.join(second["run_dir"], "prompt.md"), encoding="utf-8").read()
    assert prompt.startswith("Tell me which market to go after first.\n\nFor this task: do the market analysis.\n")
    assert "--- your reply 1 ---\nNothing was searched or written yet" in prompt
    assert "--- the user's answer 1 ---\nPortugal, remote.\nFree sources only.\n" in prompt and "demo-asks" not in prompt
    # 3. What the run left came back by the path rule: the document, the machine file and the state file; the
    #    file outside docs/ is kept in the run folder and listed.
    assert second["returned"] == [{"path": "docs/business/market.lint.json", "class": "machine"},
                                  {"path": "docs/business/market.md", "class": "document"},
                                  {"path": "docs/workbench/state.md", "class": "state"}]
    assert second["kept"] == [{"path": "notes.txt", "class": "other", "reason": "this class of path is not brought back yet"}]
    assert (project / "docs" / "business" / "market.md").read_text().startswith("# Market analysis")
    assert "decision recorded by demo-asks" in (project / "docs" / "workbench" / "state.md").read_text()
    assert not (project / "notes.txt").exists() and not (project / ".h").exists()
    review = ops.pending(path, second["pending_id"])
    assert review["kind"] == "review" and review["payload"]["ending"] == "done" and review["payload"]["run_dir"] == second["run_dir"]
    # 4. Releasing the delivery finishes the task and makes the next one ready; it reads the document just returned.
    released = ops.release(path, second["pending_id"])
    assert released["task_state"] == "done" and len(released["ready"]) == 1 and released["completed"] == []
    third = ops.run_next(path)
    assert (third["skill"], third["ending"]) == ("demo-writes", "done")
    assert third["returned"] == [{"path": "docs/business/icp.md", "class": "document"}]
    assert (project / "docs" / "business" / "icp.md").is_file()
    assert ops.release(path, third["pending_id"])["completed"] == [1]
    assert [r["state"] for r in ops.status(path)["requests"]] == ["done"]
    assert st.calls(tree["adapter"]) == ["demo-asks 1", "demo-asks 2", "demo-writes 1"]


def test_a_file_that_changed_in_the_project_during_the_run_is_never_overwritten(tree, monkeypatch):
    project, path = tree["project"], project_of(tree)
    requested(tree)
    ops.answer(path, ops.run_next(path)["pending_id"], "here")
    real = lab.run_skill

    def edited_meanwhile(*args, **kwargs):
        result = real(*args, **kwargs)
        (project / "docs" / "workbench" / "state.md").write_text("# Workbench state\n\nedited by the person\n")
        (project / "docs" / "business").mkdir(exist_ok=True)
        (project / "docs" / "business" / "market.md").write_text("written by the person\n")
        return result

    monkeypatch.setattr(lab, "run_skill", edited_meanwhile)
    out = ops.run_next(path)
    assert out["returned"] == [{"path": "docs/business/market.lint.json", "class": "machine"}]
    kept = {item["path"]: item["reason"] for item in out["kept"]}
    assert kept["docs/business/market.md"] == kept["docs/workbench/state.md"] == "the project's file changed while the run was in progress"
    assert (project / "docs" / "business" / "market.md").read_text() == "written by the person\n"
    assert (project / "docs" / "workbench" / "state.md").read_text().endswith("edited by the person\n")


def test_a_run_that_fails_fails_the_task_and_brings_nothing_back_and_retry_runs_it_again(tree):
    path = project_of(tree)
    requested(tree)
    st.fail(tree["adapter"], "auth", 1)
    out = ops.run_next(path)
    assert (out["status"], out["task_state"], out["failure"]["kind"], out["pending_id"]) == ("failed", "failed", "auth", None)
    task = ops.status(path)["requests"][0]["tasks"][0]
    assert task["state"] == "failed" and "refused the key" in task["note"]
    assert ops.run_next(path)["reason"] == "no task is ready"
    assert ops.retry(path, task["id"])["state"] == "ready"
    assert ops.run_next(path)["ending"] == "question"


def test_a_reply_no_rule_recognises_reaches_the_person_whole_as_unclassified(tree, monkeypatch):
    path = project_of(tree)
    requested(tree)
    real = lab.run_skill

    def odd_reply(*args, **kwargs):
        result = real(*args, **kwargs)
        result["response"] = "I looked around and I am not sure what you want."
        return result

    monkeypatch.setattr(lab, "run_skill", odd_reply)
    out = ops.run_next(path)
    assert (out["ending"], out["task_state"]) == ("unclassified", "waiting")
    item = ops.pending(path, out["pending_id"])
    assert item["kind"] == "review" and item["body"] == "I looked around and I am not sure what you want."
    assert item["payload"]["ending"] == "unclassified"


DRAFT_REPLY = "The analysis is written; OPEN-1 (which segment first) is a close call.\n\nDo you want to settle OPEN-1 now?"


def drafted(tree, monkeypatch) -> dict:
    """The first task asks, is answered, and its second run writes the document and still asks."""
    path = project_of(tree)
    requested(tree)
    ops.answer(path, ops.run_next(path)["pending_id"], "Portugal, remote.")
    real = lab.run_skill

    def still_asks(*args, **kwargs):
        result = real(*args, **kwargs)
        if result["changes"] and result["changes"]["created"]:
            result["response"] = DRAFT_REPLY
        return result

    monkeypatch.setattr(lab, "run_skill", still_asks)
    return ops.run_next(path)


def test_a_draft_with_open_questions_opens_a_review_with_the_whole_reply(tree, monkeypatch):
    out = drafted(tree, monkeypatch)
    assert (out["ending"], out["task_state"]) == ("draft_with_questions", "waiting")
    assert {"path": "docs/business/market.md", "class": "document"} in out["returned"]
    item = ops.pending(project_of(tree), out["pending_id"])
    assert item["kind"] == "review" and item["body"] == DRAFT_REPLY
    assert item["payload"]["ending"] == "draft_with_questions"


def test_the_review_of_a_draft_with_open_questions_is_released_as_it_stands(tree, monkeypatch):
    path = project_of(tree)
    out = drafted(tree, monkeypatch)
    released = ops.release(path, out["pending_id"])
    assert released["task_state"] == "done" and len(released["ready"]) == 1
    tasks = ops.status(path)["requests"][0]["tasks"]
    assert [t["state"] for t in tasks] == ["done", "ready"]
    assert (tree["project"] / "docs" / "business" / "market.md").is_file()


def test_the_review_of_a_draft_with_open_questions_is_answered_and_the_next_run_gets_the_text(tree, monkeypatch):
    path = project_of(tree)
    out = drafted(tree, monkeypatch)
    answered = ops.answer(path, out["pending_id"], "Leave OPEN-1 open.")
    assert answered["task_state"] == "ready" and answered["ready"] == []
    again = ops.run_next(path)
    assert again["skill"] == "demo-asks"
    prompt = open(os.path.join(again["run_dir"], "prompt.md"), encoding="utf-8").read()
    assert "--- your reply 2 ---\n" + DRAFT_REPLY in prompt
    assert "--- the user's answer 2 ---\nLeave OPEN-1 open.\n" in prompt


def test_a_run_that_wrote_nothing_and_asks_still_opens_a_question_that_cannot_be_released(tree):
    path = project_of(tree)
    requested(tree)
    out = ops.run_next(path)
    assert out["ending"] == "question" and ops.pending(path, out["pending_id"])["kind"] == "question"
    with pytest.raises(ops.OpsError):
        ops.release(path, out["pending_id"])
    assert ops.status(path)["requests"][0]["tasks"][0]["state"] == "waiting"


def test_one_task_at_a_time_per_project_and_an_interrupted_run_is_ended_at_the_next_one(tree):
    path = project_of(tree)
    requested(tree)
    os.makedirs(tree["data"], exist_ok=True)
    lock = os.open(os.path.join(tree["data"], "run.lock"), os.O_WRONLY | os.O_CREAT, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX)
    with pytest.raises(ops.OpsError) as busy:
        ops.run_next(path)
    assert "one task at a time" in str(busy.value) and st.calls(tree["adapter"]) == []
    os.close(lock)
    ctx = ops.context(path)
    claimed = ctx["store"].task_claim_next(ctx["conn"])["task"]  # a run that died after it claimed its task
    out = ops.run_next(path)
    assert out["recovered"] == [claimed["id"]] and out["ran"] is None
    assert ops.status(path)["requests"][0]["tasks"][0]["state"] == "failed"


def test_cancelling_a_request_closes_what_is_open_under_it(tree):
    path = project_of(tree)
    request = requested(tree)["request"]
    pending_id = ops.run_next(path)["pending_id"]
    out = ops.cancel(path, request)
    assert out["pending"] == [pending_id] and len(out["cancelled"]) == 3
    assert ops.pending(path) == {"pending": []} and ops.run_next(path)["reason"] == "no task is ready"


def test_a_project_that_is_not_configured_or_names_another_checkout_is_refused(tree, tmp_path):
    with pytest.raises(ops.OpsError) as e:
        ops.status(str(tmp_path / "nowhere"))
    assert e.value.code == 3
    config = tree["project"] / "docs" / "workbench" / "runtime.json"
    good = json.loads(config.read_text())
    for change, word in (({"workbench": str(tmp_path / "other")}, "names the workbench checkout"),
                         ({"data_dir": "relative/data"}, "needs data_dir"),
                         ({"store_db": str(tree["project"] / "docs" / "store.sqlite")}, "inside the project"),
                         ({"data_dir": str(tree["tree"] / "data")}, "inside the workbench checkout")):
        config.write_text(json.dumps({**good, **change}))
        with pytest.raises(ops.OpsError) as e:
            ops.status(project_of(tree))
        assert e.value.code == 3 and word in str(e.value)
    with pytest.raises(ops.OpsError) as e:
        config.write_text(json.dumps(good))
        ops.request(project_of(tree), "x", "no-such-flow")
    assert e.value.code == 2 and "flows/no-such-flow.json" in str(e.value)


def test_the_configuration_is_read_with_its_hash_and_unknown_keys_are_ignored(tmp_path):
    project = tmp_path / "project"
    (project / "docs" / "workbench").mkdir(parents=True)
    text = json.dumps({"workbench": str(tmp_path / "wb"), "data_dir": str(tmp_path / "data"), "store_db": str(tmp_path / "s.sqlite"),
                       "agent": "social-manager", "area_agents": {}})
    (project / "docs" / "workbench" / "runtime.json").write_text(text)
    cfg = ops.project_config.load(str(project))
    assert cfg["sha256"] == hashlib.sha256(text.encode()).hexdigest() and cfg["raw"]["agent"] == "social-manager"
    assert cfg["path"].endswith("docs/workbench/runtime.json") and ops.project_config.REL == ops.path_rule.CONFIG
    (project / "docs" / "workbench" / "runtime.json").write_text("[1]")
    with pytest.raises(ops.project_config.ConfigError):
        ops.project_config.load(str(project))


def test_the_runtimes_own_configuration_never_enters_a_run(tree):
    files, base, left_out = ops.copy_list(project_of(tree), {"inputs": ["docs/workbench/"], "outputs": [], "updates": []})
    assert [rel for _, rel in files] == ["docs/workbench/state.md"] and "docs/workbench/runtime.json" not in base
    link = tree["project"] / "docs" / "workbench" / "linked.md"
    os.symlink(tree["project"] / "AGENTS.md", link)
    assert [rel for _, rel in ops.copy_list(project_of(tree), {"inputs": ["docs/workbench/"], "outputs": [], "updates": []})[0]] == ["docs/workbench/state.md"]


def test_the_shell_prints_one_json_object_and_uses_the_documented_exit_codes(tree, capsys, monkeypatch):
    path = project_of(tree)
    assert cli.main(["request", "--project", path, "--flow", "demo", "--text", "Which market first?"]) == 0
    assert json.loads(capsys.readouterr().out)["request"] == 1
    assert cli.main(["run-next", "--project", path]) == 0
    ran = json.loads(capsys.readouterr().out)
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("From standard input.\n"))
    assert cli.main(["answer", "--project", path, "--id", str(ran["pending_id"]), "--text-file", "-"]) == 0
    capsys.readouterr()
    assert cli.main(["pending", "--project", path, "--id", str(ran["pending_id"])]) == 0
    assert json.loads(capsys.readouterr().out)["answer"] == "From standard input."
    for argv, code in ((["status"], 2), (["request", "--project", path, "--text", "x"], 2), (["frobnicate", "--project", path], 2),
                       (["answer", "--project", path, "--id", "1", "--text", "a", "--text-file", "b"], 2),
                       (["release", "--project", path, "--id", "99"], 1), (["status", "--project", path + "-missing"], 3)):
        assert cli.main(argv) == code, argv
        captured = capsys.readouterr()
        assert captured.out == "" and captured.err.startswith("error: ") and "Traceback" not in captured.err
    assert cli.main(["--help"]) == 0 and "run-next" in capsys.readouterr().out


def test_every_script_of_the_runtime_prints_its_help_and_refuses_an_unknown_call():
    for name in ("lab", "ops", "cli", "flow_files", "path_rule", "state_merge", "endings", "project_config", "skill_meta"):
        script = str(st.REPO / "runtime" / f"{name}.py")
        helped = subprocess.run([sys.executable, script, "--help"], capture_output=True, text=True, timeout=60)
        assert helped.returncode == 0 and helped.stdout.strip() and "Traceback" not in helped.stderr, name
        refused = subprocess.run([sys.executable, script, "--no-such-flag-of-this-script"], capture_output=True, text=True, timeout=60)
        assert refused.returncode == 2 and "Traceback" not in refused.stderr, name
