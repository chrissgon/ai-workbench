"""Tests of limit L15 for policy effects (WP-R.1 of the architecture-fix plan): an effect inside a standing approval is
executed only by the operations layer, ops.execute_under_policy, and only inside the approval's bounds. A handler
prepares the effect document and hands it over; the operation checks the approval (autonomy.covers, the policy file's
hash now, today's count under the run lock), makes the provider's dry run and its confirmed call, and records the
action. Offline: the stand-in tree and its stand-in code provider of runtime/tests/standin_tree.py; no network, no
push. Every name is invented.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_execute_under_policy.py
"""
from __future__ import annotations

import datetime
import hashlib
import json
import shutil
import subprocess

import pytest

import standin_tree as st

autonomy = st.load("autonomy")
effects = st.load("effects")
lab = st.load("lab")
ops = st.load("ops")
cli = st.load("cli")

POLICY = "docs/workbench/policies/published-posts.json"
TARGET = "example-owner/example-profile@main"
BOUNDS = {"policy": "published-posts", "agent": "marketing", "effects": ["push"], "targets": [TARGET],
          "files": ["data/posts.json", "assets/posts/*"], "max_per_day": 1, "max_items_per_run": 10}
CODE = {"provider": "github", "repo": "example-owner/example-profile", "base": "main"}


def ahead(days: int) -> str:
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()


@pytest.fixture
def tree(tmp_path, monkeypatch):
    built = st.build(tmp_path, monkeypatch, lab)
    monkeypatch.setattr(ops, "ROOT", str(built["tree"]))
    (built["tree"] / "scripts").mkdir(exist_ok=True)  # the one source of the vocabulary of side effects
    shutil.copyfile(st.REPO / "scripts" / "validate.py", built["tree"] / "scripts" / "validate.py")
    project = built["project"]
    config = project / "docs" / "workbench" / "runtime.json"
    data = json.loads(config.read_text())
    data["area_agents"] = {"planning": {"pack": "planning"},
                           "marketing": {"pack": "brand", "mode": "autonomous-with-policy"}}
    data["code"] = CODE
    config.write_text(json.dumps(data))
    (project / "docs" / "workbench" / "policies").mkdir()
    write_bounds(built, BOUNDS)
    ops.accept_config(str(project), ops.project_config.load(str(project))["sha256"])
    return built


def write_bounds(tree, bounds: dict) -> None:
    (tree["project"] / POLICY).write_text(json.dumps(bounds, indent=2) + "\n")


def project_of(tree) -> str:
    return str(tree["project"])


def approve(tree, days: int = 30) -> dict:
    digest = hashlib.sha256((tree["project"] / POLICY).read_bytes()).hexdigest()
    return ops.approve_policy(project_of(tree), POLICY, "marketing", digest, ahead(days))


def calls(tree) -> list:
    path = tree["tree"] / "providers" / "vcs" / "calls.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.is_file() else []


def effect_file(tree, name="effect.json", **changes) -> str:
    """An effect document as the handler writes it, with its files beside it."""
    folder = tree["project"].parent / "handed"
    folder.mkdir(exist_ok=True)
    (folder / "target.json").write_text("[]\n")
    (folder / "message.txt").write_text("Add a post\n")
    doc = {"policy": "published-posts", "kind": "push", "target": TARGET, "files": ["data/posts.json"], "items": 1,
           "idempotency_key": "published-posts-2026-W42", "payload_sha256": "ab" * 32,
           "args": ["--repo", "example-owner/example-profile", "--branch", "main",
                    "--message-file", str(folder / "message.txt"), "--file", f"data/posts.json={folder / 'target.json'}"]}
    doc.update(changes)
    doc = {k: v for k, v in doc.items() if v is not None}
    path = folder / name
    path.write_text(json.dumps(doc))
    return str(path)


def execute(tree, **changes) -> dict:
    return ops.execute_under_policy(project_of(tree), "published-posts", effect_file(tree, **changes))


def executed_today(tree) -> int:
    return ops.standing(project_of(tree), "published-posts")["executed_today"]


def test_a_policy_effect_is_executed_by_the_operations_layer_inside_its_bounds_only(tree):
    approved = approve(tree)
    out = execute(tree)
    assert out["executed"] is True and out["policy"] == "published-posts" and out["approval_id"] == approved["id"]
    assert out["action"]["created"] is True and out["result"]["commit"] == "c" * 40
    made = calls(tree)
    assert [c["argv"][0] for c in made] == ["commit-files", "commit-files"]
    dry, real = made[0]["argv"], made[1]["argv"]
    assert "--dry-run" in dry and "--confirmed" not in dry and "--confirmed" in real and "--dry-run" not in real
    assert dry[:-1] == real[:-1] and (dry[-1], real[-1]) == ("--dry-run", "--confirmed")  # the same call, then confirmed
    assert [real[i + 1] for i, a in enumerate(real) if a == "--allow"] == BOUNDS["files"]  # exactly the bounds' globs
    assert real[real.index("--idempotency-key") + 1] == "published-posts-2026-W42"
    assert real[real.index("--repo") + 1] == "example-owner/example-profile"
    assert executed_today(tree) == 1  # the action row exists and counts against the day


@pytest.mark.parametrize("bounds, changes, words", [
    ({"effects": ["publish"]}, {}, "effects"),
    ({"targets": ["example-owner/another@main"]}, {}, "targets"),
    ({}, {"files": ["data/posts.json", "secrets/key.json"]}, "files"),
    ({"max_items_per_run": 1}, {"items": 2}, "per run"),
    ({"max_per_day": 1}, {}, "per day"),
])
def test_a_change_outside_one_of_the_five_bounds_runs_nothing_and_names_the_bound(tree, bounds, changes, words):
    write_bounds(tree, {**BOUNDS, **bounds})
    approve(tree)
    if words == "per day":
        assert execute(tree)["executed"] is True
        before = calls(tree)
        changes = {"idempotency_key": "published-posts-2026-W43"}
    else:
        before = []
    out = execute(tree, **changes)
    assert out["executed"] is False and words in out["why"], out
    assert calls(tree) == before
    assert executed_today(tree) == (1 if words == "per day" else 0)


def test_no_active_approval_covers_nothing(tree):
    out = execute(tree)
    assert out["executed"] is False and "no active standing approval" in out["why"] and calls(tree) == []


def test_an_expired_approval_covers_nothing(tree):
    approved = approve(tree)
    store = ops.store_module()
    later = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=31)).isoformat()
    assert store.approvals_expire(store.open_db(str(tree["db"])), later) == 1
    out = execute(tree)
    assert approved["status"] == "active" and out["executed"] is False and calls(tree) == []


def test_a_changed_policy_file_covers_nothing(tree):
    approve(tree)
    write_bounds(tree, {**BOUNDS, "max_per_day": 5})
    out = execute(tree)
    assert out["executed"] is False and "changed" in out["why"] and calls(tree) == []


def test_an_agent_outside_the_policy_mode_covers_nothing(tree):
    approve(tree)
    changed = ops.set_mode(project_of(tree), "marketing", "autonomous")
    ops.accept_config(project_of(tree), changed["config_sha256"])
    out = execute(tree)
    assert out["executed"] is False and "autonomous" in out["why"] and calls(tree) == []


@pytest.mark.parametrize("flag", ["--confirmed", "--dry-run", "--allow", "--idempotency-key"])
def test_args_holding_a_reserved_flag_are_refused_and_nothing_runs(tree, flag):
    approve(tree)
    doc = json.loads(open(effect_file(tree)).read())
    with pytest.raises(ops.OpsError) as refused:
        execute(tree, args=doc["args"] + [flag, "x"])
    assert refused.value.code == 2 and flag in str(refused.value)
    assert calls(tree) == [] and executed_today(tree) == 0


@pytest.mark.parametrize("changes", [
    {"idempotency_key": None},           # a missing key
    {"colour": "red"},                   # an extra key
    {"kind": "publish"},                 # a word of the vocabulary that POLICY_CALLS does not know
    {"kind": "teleport"},                # not a word of the vocabulary
    {"policy": "another-policy"},        # not the policy the call is for
    {"items": "1"},                      # a wrong type
    {"payload_sha256": "not-a-hash"},    # a hash the store would refuse after the provider ran
])
def test_a_malformed_effect_document_is_refused_and_nothing_runs(tree, changes):
    approve(tree)
    with pytest.raises(ops.OpsError) as refused:
        execute(tree, **changes)
    assert refused.value.code == 2 and calls(tree) == [] and executed_today(tree) == 0


def test_the_dry_run_failing_confirms_nothing_and_records_nothing(tree, monkeypatch):
    approve(tree)
    real = effects._subprocess
    monkeypatch.setattr(effects, "_subprocess", lambda argv: subprocess.CompletedProcess(argv, 1, "", "the branch is protected")
                        if "--dry-run" in argv else real(argv))
    with pytest.raises(ops.OpsError) as refused:
        execute(tree)
    assert refused.value.code == 1 and "nothing was executed" in str(refused.value) and "protected" in str(refused.value)
    assert calls(tree) == [] and executed_today(tree) == 0


def test_the_confirmed_call_failing_records_nothing_and_the_error_names_the_replay(tree, monkeypatch):
    approve(tree)
    real = effects._subprocess
    monkeypatch.setattr(effects, "_subprocess", lambda argv: subprocess.CompletedProcess(argv, 1, "", "the remote refused")
                        if "--confirmed" in argv else real(argv))
    with pytest.raises(ops.OpsError) as refused:
        execute(tree)
    assert refused.value.code == 1 and "after the dry run" in str(refused.value) and "replay" in str(refused.value)
    assert [c["argv"][0] for c in calls(tree)] == ["commit-files"] and executed_today(tree) == 0


def test_the_shell_answers_with_one_json_object_and_exit_0_whether_or_not_the_approval_covers(tree, capsys):
    approve(tree)
    path = effect_file(tree)
    argv = ["execute-under-policy", "--project", project_of(tree), "--policy", "published-posts", "--effect-file", path]
    assert cli.main(argv) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["executed"] is True and first["action"]["created"] is True
    write_bounds(tree, {**BOUNDS, "max_per_day": 1})  # the file as approved: the day's cap of 1 is now reached
    assert cli.main(argv) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["executed"] is False and "per day" in second["why"]
    assert cli.main(argv[:-2]) != 0  # the flag is needed
