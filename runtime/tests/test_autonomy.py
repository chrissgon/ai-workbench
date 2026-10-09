"""Tests of runtime/autonomy.py and the operation set_mode (stage 6, WP-6.3): the five modes from three facts, the
daily caps, what a mode releases, what a policy covers, and the generated Checkpoints line. Every name below is
invented.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_autonomy.py
"""
from __future__ import annotations

import datetime
import json
import subprocess
import sys

import pytest

import standin_tree as st

autonomy = st.load("autonomy")
state_merge = st.load("state_merge")
lab = st.load("lab")
ops = st.load("ops")
ops_core = st.load("ops_core")
cli = st.load("cli")

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
LATER = "2026-12-31T00:00:00.000000Z"
EARLIER = "2026-11-01T00:00:00.000000Z"
HASH = "d" * 64
BOUNDS = {"policy": "published-posts", "agent": "marketing", "effects": ["push"],
          "targets": ["example-owner/example-profile@main"], "files": ["data/posts.json", "assets/posts/*"],
          "max_per_day": 1, "max_items_per_run": 10}


def standing(agent="marketing", expires=LATER, status="active"):
    return {"id": 1, "scope": "standing", "status": status, "expires_at": expires, "policy_sha256": HASH,
            "bounds": dict(BOUNDS, agent=agent)}


def checked(**modes) -> dict:
    return autonomy.agents({name: {"pack": "brand", "mode": mode} for name, mode in modes.items()})


def test_each_of_the_five_modes_is_one_combination_of_the_three_facts():
    table = {"stopped": (False, "every-phase", False), "supervised": (True, "every-phase", False),
             "milestones": (True, "milestones", False), "autonomous": (True, "end", False),
             "autonomous-with-policy": (True, "end", True)}
    assert tuple(table) == autonomy.MODES and autonomy.DEFAULT_MODE == "milestones"
    for mode, (enabled, checkpoints, in_force) in table.items():
        agents = autonomy.agents({"marketing": {"pack": "brand", "mode": mode}})
        f = autonomy.facts("marketing", agents, [standing()], NOW)
        assert f == {"enabled": enabled, "checkpoints": checkpoints, "standing": in_force}, mode
        assert autonomy.mode_of(f) == mode
    disabled = autonomy.agents({"marketing": {"pack": "brand", "mode": "autonomous", "enabled": False}})
    assert autonomy.mode_of(autonomy.facts("marketing", disabled, [], NOW)) == "stopped"


def test_a_policy_mode_without_an_approval_in_force_is_plain_autonomous():
    agents = checked(marketing="autonomous-with-policy")
    for rows in ([], [standing(expires=EARLIER)], [standing(agent="planning")], [standing(status="revoked")]):
        f = autonomy.facts("marketing", agents, rows, NOW)
        assert f["standing"] is False and autonomy.mode_of(f) == "autonomous", rows


def test_an_agent_set_to_autonomous_asks_for_every_effect_whatever_approvals_exist():
    f = autonomy.facts("marketing", checked(marketing="autonomous"), [standing()], NOW)
    assert f["standing"] is False and autonomy.mode_of(f) == "autonomous"


def test_an_absent_cap_is_zero_and_never_unlimited():
    agents = autonomy.agents({"planning": {"pack": "planning"}})
    assert agents["planning"] == {"pack": "planning", "enabled": True, "mode": "milestones", "max_runs_per_day": 0,
                                  "max_usd_per_day": 0}
    f = autonomy.facts("planning", agents, [], NOW)
    nothing = {"runs_reference": 0, "usd_floor": 0.0, "runs_without_cost": 0}
    assert autonomy.may_start("planning", agents, f, nothing, "strong") == (False, "cap: runs per day")
    assert autonomy.may_start("planning", agents, f, nothing, "floor") == (False, "cap: usd per day")
    assert autonomy.agents(None) == {}


def test_an_unknown_key_or_mode_of_an_agent_is_refused_by_name():
    for raw, word in (({"brand": {"pack": "brand", "speed": 3}}, "speed"),
                      ({"brand": {"pack": "brand", "mode": "turbo"}}, "turbo"),
                      ({"brand": {"pack": "brand", "max_runs_per_day": -1}}, "max_runs_per_day"),
                      ({"brand": {"pack": "brand", "max_runs_per_day": 2.5}}, "max_runs_per_day"),
                      ({"brand": {"pack": "brand", "max_usd_per_day": "1"}}, "max_usd_per_day"),
                      ({"brand": {"pack": "brand", "enabled": "yes"}}, "enabled"),
                      ({"brand": {"mode": "milestones"}}, "pack")):
        with pytest.raises(ValueError) as refused:
            autonomy.agents(raw)
        assert "brand" in str(refused.value) and word in str(refused.value), raw


RUNS = [{"agent": "brand", "model": "ref", "cost_usd": None}, {"agent": "brand", "model": "ref", "cost_usd": 0.4},
        {"agent": "brand", "model": "floor", "cost_usd": 0.03}, {"agent": "brand", "model": "floor", "cost_usd": None},
        {"agent": "brand", "model": "another", "cost_usd": 0.01}, {"agent": "business", "model": "ref", "cost_usd": 0.2},
        {"agent": None, "model": "floor", "cost_usd": 0.5}]


def test_the_day_s_runs_are_counted_per_agent_and_per_model():
    assert autonomy.spend(RUNS, "brand", "ref", "floor", 0.5) == {"runs_reference": 3, "usd_floor": 0.53,
                                                                    "runs_without_cost": 1}
    assert autonomy.spend(RUNS, "business", "ref", "floor", 0.5) == {"runs_reference": 1, "usd_floor": 0.0,
                                                                       "runs_without_cost": 0}


def test_a_floor_run_without_a_cost_counts_at_the_per_run_limit():
    spent = autonomy.spend([{"agent": "brand", "model": "floor", "cost_usd": None}] * 2, "brand", "ref", "floor", 0.25)
    assert spent == {"runs_reference": 0, "usd_floor": 0.5, "runs_without_cost": 2}


def test_a_stopped_agent_and_an_agent_at_its_cap_may_not_start():
    agents = autonomy.agents({"brand": {"pack": "brand", "max_runs_per_day": 2, "max_usd_per_day": 0.5},
                              "quiet": {"pack": "brand", "mode": "stopped", "max_runs_per_day": 9}})
    f = autonomy.facts("brand", agents, [], NOW)
    spent = {"runs_reference": 1, "usd_floor": 0.4, "runs_without_cost": 0}
    assert autonomy.may_start("brand", agents, f, spent, "strong") == (True, "")
    assert autonomy.may_start("brand", agents, f, spent, "floor") == (True, "")
    at_cap = {"runs_reference": 2, "usd_floor": 0.5, "runs_without_cost": 0}
    assert autonomy.may_start("brand", agents, f, at_cap, "strong") == (False, "cap: runs per day")
    assert autonomy.may_start("brand", agents, f, at_cap, "floor") == (False, "cap: usd per day")
    quiet = autonomy.facts("quiet", agents, [], NOW)
    assert autonomy.may_start("quiet", agents, quiet, spent, "strong") == (False, "stopped")
    assert autonomy.may_start("nobody", agents, autonomy.facts("nobody", agents, [], NOW), spent, "strong") == \
        (False, "stopped")


def review(ending="done", why="a declared output was written", **payload):
    return {"kind": "review", "payload": dict({"ending": ending, "why": why}, **payload)}


def facts_of(mode: str) -> dict:
    return autonomy.facts("brand", checked(brand=mode), [], NOW)


def test_a_question_and_an_unclassified_reply_are_never_released_by_a_mode():
    f, task = facts_of("autonomous"), {"milestone": 0}
    assert autonomy.review_action(task, review(), f, True, False) == "release"
    for pending in ({"kind": "question", "payload": {"ending": "question"}}, review("unclassified"),
                    review("draft_with_questions"), review("gate"), {"kind": "effect", "payload": {}},
                    {"kind": "plan", "payload": {}}, {"kind": "acceptance", "payload": {}},
                    review(why="no file changed, a declared output is already there, and the reply asks nothing"),
                    review(changeset={"blocked": True})):
        assert autonomy.review_action(task, pending, f, True, False) == "hold", pending


def test_a_mandatory_milestone_is_held_in_every_mode():
    for mode in autonomy.MODES:
        assert autonomy.review_action({"milestone": 0}, review(), facts_of(mode), True, True) == "hold", mode


def test_supervised_holds_everything_milestones_holds_milestones_autonomous_holds_neither():
    plain, milestone = {"milestone": 0}, {"milestone": 1}
    expected = {"stopped": ("hold", "hold"), "supervised": ("hold", "hold"), "milestones": ("release", "hold"),
                "autonomous": ("release", "release"), "autonomous-with-policy": ("release", "release")}
    for mode, (on_plain, on_milestone) in expected.items():
        f = facts_of(mode)
        assert autonomy.review_action(plain, review(), f, True, False) == on_plain, mode
        assert autonomy.review_action(milestone, review(), f, True, False) == on_milestone, mode


def test_a_skill_that_is_not_proven_is_held_in_every_mode():
    for mode in autonomy.MODES:
        assert autonomy.review_action({"milestone": 0}, review(), facts_of(mode), False, False) == "hold", mode


EFFECT = {"kind": "push", "target": "example-owner/example-profile@main",
          "files": ["data/posts.json", "assets/posts/week-45.png"], "items": 4}


def test_a_policy_covers_an_effect_only_inside_every_bound():
    approval = standing()
    assert autonomy.covers(approval, HASH, EFFECT, 0, NOW) == (True, "")
    broken = [(dict(approval, status="revoked"), HASH, EFFECT, 0),
              (dict(approval, expires_at=EARLIER), HASH, EFFECT, 0),
              (approval, "e" * 64, EFFECT, 0),
              (approval, HASH, dict(EFFECT, kind="publish"), 0),
              (approval, HASH, dict(EFFECT, target="example-owner/another@main"), 0),
              (approval, HASH, dict(EFFECT, files=["assets/posts/deep/week-45.png"]), 0),
              (approval, HASH, dict(EFFECT, items=11), 0),
              (approval, HASH, EFFECT, 1)]
    for case in broken:
        allowed, why = autonomy.covers(*case, NOW)
        assert allowed is False and why, case


def test_an_edited_bounds_file_covers_nothing_until_it_is_approved_again():
    approval = standing()
    edited = "f" * 64
    assert autonomy.covers(approval, edited, EFFECT, 0, NOW) == (False, "the bounds file changed since it was approved")
    again = dict(approval, id=2, policy_sha256=edited)
    assert autonomy.covers(again, edited, EFFECT, 0, NOW) == (True, "")


@pytest.fixture
def tree(tmp_path, monkeypatch):
    built = st.build(tmp_path, monkeypatch, lab)
    monkeypatch.setattr(ops_core, "ROOT", str(built["tree"]))
    config = built["project"] / "docs" / "workbench" / "runtime.json"
    data = json.loads(config.read_text())
    data["area_agents"] = {"planning": {"pack": "planning", "mode": "supervised"},
                           "brand": {"pack": "brand", "mode": "autonomous", "max_runs_per_day": 3}}
    config.write_text(json.dumps(data))
    project = str(built["project"])
    ops.accept_config(project, ops.project_config.load(project)["sha256"])
    return built


def test_set_mode_changes_one_word_of_the_configuration_and_asks_for_acceptance(tree, capsys):
    project = str(tree["project"])
    config = tree["project"] / "docs" / "workbench" / "runtime.json"
    before = json.loads(config.read_text())
    out = ops.set_mode(project, "brand", "autonomous-with-policy")  # a move up the order: the person accepts it
    after = json.loads(config.read_text())
    before["area_agents"]["brand"]["mode"] = "autonomous-with-policy"
    assert after == before and config.read_text().endswith("}\n")
    assert out["agent"] == "brand" and out["mode"] == "autonomous-with-policy" and out["accepted"] is False
    assert out["config_sha256"] == ops.project_config.load(project)["sha256"]
    assert "accept-config" in out["next"] and out["config_sha256"] in out["next"]
    with pytest.raises(ops.OpsError) as refused:
        ops.status(project)
    assert refused.value.code == 3
    accepted = ops.accept_config(project, out["config_sha256"])
    assert accepted["checkpoints"] == {"written": True, "value": "every-phase"}
    for agent, mode in (("brand", "turbo"), ("nobody", "milestones")):
        with pytest.raises(ops.OpsError) as refused:
            ops.set_mode(project, agent, mode)
        assert refused.value.code == 2
    assert cli.main(["set-mode", "--project", project, "--agent", "brand", "--mode", "autonomous"]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "autonomous"
    assert cli.main(["set-mode", "--project", project, "--agent", "brand"]) == 2
    script = str(st.RUNTIME / "autonomy.py")
    helped = subprocess.run([sys.executable, script, "--help"], capture_output=True, text=True, timeout=60)
    assert helped.returncode == 0 and "mode_of(facts)" in helped.stdout
    assert subprocess.run([sys.executable, script, "--frobnicate"], capture_output=True, timeout=60).returncode == 2


def test_the_state_file_s_checkpoints_line_is_the_most_careful_of_the_enabled_agents(tree):
    assert autonomy.state_checkpoints(checked(a="autonomous", b="milestones")) == "milestones"
    assert autonomy.state_checkpoints(checked(a="autonomous", b="autonomous-with-policy")) == "end"
    assert autonomy.state_checkpoints(checked(a="autonomous", b="supervised")) == "every-phase"
    assert autonomy.state_checkpoints(checked(a="stopped", b="autonomous")) == "end"
    assert autonomy.state_checkpoints({}) == "every-phase"
    text = "# State\n\n## Autonomy\n\n- Checkpoints: every-phase   # every-phase | milestones | end\n\n## Decisions\n"
    written, done = state_merge.with_checkpoints(text, "end")
    assert done is True and written == text.replace("every-phase   #", "end   #")
    assert state_merge.with_checkpoints("# State\n\n## Decisions\n", "end") == ("# State\n\n## Decisions\n", False)
    project = str(tree["project"])
    state = tree["project"] / "docs" / "workbench" / "state.md"
    assert "- Checkpoints: every-phase" in state.read_text()  # supervised planning is the most careful
    ops.set_mode(project, "planning", "stopped")
    accepted = ops.accept_config(project, ops.project_config.load(project)["sha256"])
    assert accepted["checkpoints"]["value"] == "end" and "- Checkpoints: end" in state.read_text()
    state.write_text(state.read_text().replace("- Checkpoints: end\n", ""))
    ops.set_mode(project, "planning", "supervised")
    accepted = ops.accept_config(project, ops.project_config.load(project)["sha256"])
    assert accepted["checkpoints"] == "no line to write"
