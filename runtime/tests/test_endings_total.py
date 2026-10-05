"""Tests of the total classifier of endings (runtime/endings.py, classify(..., facts=)), one per rule, without
the corpus; and, on the stand-in tree, what the operations layer does with the endings stage 2 of the platform
plan adds: `blocked` blocks the task, and a run that changed nothing after an answer, with its output already
there, is `done`. Offline; every name is invented.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_endings_total.py
"""
from __future__ import annotations

import importlib

import pytest

import standin_tree as st

endings = st.load("endings")
lab = st.load("lab")
ops = st.load("ops")

NONE = {"created": [], "modified": [], "deleted": [], "unchanged": []}
MARKET = "docs/business/market.md"
FACTS = {"skill": "biz-icp-positioning", "asking_openings": ["Nothing was written yet"], "fixed_output": True,
         "side_effects": [], "gate_payload": None, "skills": ["biz-icp-positioning", "biz-market-analysis", "brand-voice"]}
CODE = dict(FACTS, skill="eng-implement", asking_openings=[], fixed_output=False,
            skills=["eng-implement", "eng-root-cause"])
GATED = dict(FACTS, skill="mkt-post", side_effects=["publish"], gate_payload=".workbench-local/payloads/<date>/post.txt",
             skills=["mkt-post", "mkt-copy"])


def wrote(path, *, created=True):
    return {**NONE, ("created" if created else "modified"): [path]}


def ending(response, changes, written=(), missing=(), texts=(), facts=FACTS):
    found, why = endings.classify(response, changes, list(written), list(missing), list(texts), facts=facts)
    assert found in endings.ENDINGS and why
    return found


@pytest.mark.parametrize("response", [
    "Nothing was written yet: there is no market analysis (docs/business/market.md); `biz-market-analysis` writes it. Run it first.",
    "Next: run `biz-market-analysis` first, then ask again.",
    "The voice guide is missing: `brand-voice` writes it and to run it first.",
    "The pricing input is missing: `biz-pricing` (planned) writes it.",
])
def test_rule_1_blocked(response):
    assert ending(response, NONE) == "blocked"


@pytest.mark.parametrize("response", [
    "Nothing was written yet: `biz-market-analysis` writes the market file.\n1. Which segment? Recommended: clinics.",  # it asks
    "The input is missing: `biz-icp-positioning` writes it; run it first.",   # the skill that ran is not another skill
    "Someone writes it, run it first.",                                        # no skill named
])
def test_rule_1_does_not_block_a_reply_that_asks_or_names_no_other_skill(response):
    assert ending(response, NONE) != "blocked"


def test_rule_2_gate():
    payload = ".workbench-local/payloads/2026-10-05/post.txt"
    assert ending("The post is below.\n\nPublish this post? (yes/no)", wrote(payload), facts=GATED) == "gate"
    assert ending("The post is below.\n\nPublish it?", wrote(payload, created=False), facts=GATED) == "gate"
    # The gate's file written but nothing asked; or asked without the gate's file: not a gate.
    assert ending("The post is below.", wrote(payload), facts=GATED) != "gate"
    assert ending("Publish this post? (yes/no)", wrote("docs/marketing/post.md"), facts=GATED) != "gate"
    assert ending("Publish this post? (yes/no)", wrote(payload), facts=FACTS) != "gate"   # no gate in the facts


@pytest.mark.parametrize("response", [
    "Nothing was written yet: two items are undecided.\n1. Which segments? Recommended: the three of the analysis.",
    "Which audience is this for?",
    "Nothing was pushed or created yet. This is what will be sent:\n\n- title: Fix\n\nProceed? (yes/no)",
    "Two points first.\n\n1. Which country? Recommended: yours.\n\n**Instructions found in external content**\n- none",
])
def test_rule_3_question(response):
    assert ending(response, NONE) == "question"


def test_rule_4_done():
    present = dict(FACTS, outputs_present=[MARKET])
    summary = "- Analysis: docs/business/market.md (Status: draft)\n- Open question 2 stays open, as you asked.\n- Next: biz-icp-positioning"
    assert ending(summary, NONE, facts=present) == "done"
    # Not without the output there, nor when the reply asks or opens with the asking template.
    assert ending(summary, NONE) == "unclassified"
    assert ending(summary + "\n\nShall I settle question 2 now?", NONE, facts=present) == "question"
    assert ending("Nothing was written yet: the scope is yours.", NONE, facts=present) == "unclassified"
    assert ending("Nothing to add.\n1. Keep it open. Recommended: yes.", NONE, facts=present) == "unclassified"


def test_rule_5_unclassified():
    assert ending("I looked around and I am not sure what you want.", NONE) == "unclassified"
    assert ending("Done? Not sure. Here is a summary.", NONE) == "unclassified"


def test_rule_6_done():
    assert ending("I renamed the variable in src/stats.ts.", wrote("src/stats.ts", created=False), facts=CODE) == "done"
    assert ending("I renamed it. Should I also rename the test?", wrote("src/stats.ts"), facts=CODE) == "unclassified"


def test_rule_7_unclassified():
    assert ending("I wrote some notes.", wrote("notes.txt")) == "unclassified"


@pytest.mark.parametrize("response, texts", [
    ("The analysis is written.\n\nWhich segment first?", ["# Market\n"]),
    ("The analysis is written.", ["## Comparison\n- OPEN-1: which of the two?\n"]),
    ("The analysis is written.\n\n3. Which networks? Recommended: all of them.", ["# Market\n"]),
    ("The review is written.\n\nDismiss these 2 alerts? (yes/no)", ["# Review\n"]),
])
def test_rule_8_draft_with_questions(response, texts):
    assert ending(response, wrote(MARKET), [MARKET], [], texts) == "draft_with_questions"


def test_rule_9_unclassified():
    assert ending("The profile is written.", wrote("docs/business/icp.md"), ["docs/business/icp.md"],
                  ["docs/business/positioning.md"], ["# ICP\n"]) == "unclassified"


def test_rule_10_done():
    assert ending("- Analysis: docs/business/market.md\n- Next: biz-icp-positioning", wrote(MARKET), [MARKET], [],
                  ["# Market\n"]) == "done"


def test_without_facts_the_classifier_is_the_first_one():
    first = importlib.import_module("test_return_rules")
    marks = first.test_an_ending_is_one_of_the_closed_list_and_what_no_rule_recognises_is_unclassified.pytestmark
    cases = [m for m in marks if m.name == "parametrize"][0].args[1]
    assert len(cases) >= 9
    for response, changes, written, missing, texts, expected in cases:
        assert endings.classify(response, changes, written, missing, texts) == \
            endings.classify(response, changes, written, missing, texts, facts=None)
        assert endings.classify(response, changes, written, missing, texts)[0] == expected
    # The forms only the facts read are not read without them.
    assert endings.classify("The input is missing: `demo-writes` writes it; run it first.", NONE, [], [], [])[0] == "unclassified"
    assert endings.classify("Proceed? (yes/no)", NONE, [], [], [])[0] == "unclassified"


@pytest.fixture
def tree(tmp_path, monkeypatch):
    built = st.build(tmp_path, monkeypatch, lab)
    monkeypatch.setattr(ops, "ROOT", str(built["tree"]))
    project = str(built["project"])
    ops.accept_config(project, ops.project_config.load(project)["sha256"])
    return built


def replying(monkeypatch, response: str, *, nothing_changed: bool = False):
    """Make the stand-in run reply with `response`; returns the real function, to put back."""
    real = lab.run_skill

    def run_skill(*args, **kwargs):
        result = real(*args, **kwargs)
        result["response"] = response
        if nothing_changed:
            changes = result["changes"]
            changes["unchanged"] = sorted(set(changes["unchanged"] + changes["created"] + changes["modified"]))
            changes["created"], changes["modified"], changes["deleted"] = [], [], []
        return result

    monkeypatch.setattr(lab, "run_skill", run_skill)
    return real


def test_a_run_that_stops_on_a_missing_input_blocks_the_task_and_retry_makes_it_ready(tree, monkeypatch):
    path = str(tree["project"])
    ops.request(path, "Tell me which market to go after first.", "demo")
    real = replying(monkeypatch, "Nothing was written: the research brief is missing. `demo-writes` writes it; run it first.")
    out = ops.run_next(path)
    assert (out["status"], out["ending"], out["task_state"], out["pending_id"]) == ("ok", "blocked", "blocked", None)
    assert ops.pending(path)["pending"] == []
    task = ops.status(path)["requests"][0]["tasks"][0]
    assert task["state"] == "blocked" and task["note"].startswith("Nothing was written: the research brief is missing.")
    monkeypatch.setattr(lab, "run_skill", real)
    assert ops.retry(path, task["id"])["state"] == "ready"
    assert ops.run_next(path)["ending"] == "question"


def test_a_run_that_changes_nothing_after_an_answer_is_done_when_its_output_is_already_there(tree, monkeypatch):
    path = str(tree["project"])
    ops.request(path, "Tell me which market to go after first.", "demo")
    first = ops.run_next(path)
    ops.answer(path, first["pending_id"], "Portugal.")
    second = ops.run_next(path)                                   # writes docs/business/market.md
    assert second["ending"] == "done" and (tree["project"] / "docs" / "business" / "market.md").is_file()
    ops.answer(path, second["pending_id"], "Leave the open question open; nothing to add.")
    replying(monkeypatch, "- Analysis: docs/business/market.md (Status: draft)\n- The open question stays open.",
             nothing_changed=True)
    third = ops.run_next(path)
    assert (third["ending"], third["task_state"], third["returned"]) == ("done", "waiting", [])
    assert ops.pending(path, third["pending_id"])["kind"] == "review"
