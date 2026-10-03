"""Offline tests of evals/measure.py, the one module that decides what a run measures (item B10 of
docs/architecture/final-plan-2026-10-02.md), and of how the runner and the status script use it.

Run: uv run --with pytest pytest evals/tests/test_measure.py
"""
from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path

import pytest

EVALS = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_under_test", EVALS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


measure, er, es = load("measure"), load("eval_run"), load("eval_status")


def test_the_constants_no_other_file_owns_are_read_from_measurement_json():
    data = json.loads((EVALS / "measurement.json").read_text(encoding="utf-8"))
    assert (measure.FILE_LIMIT, measure.VCS_LIMIT, measure.GRADING_RETRIES, measure.REDACT_MIN) == (
        data["file_limit"], data["vcs_limit"], data["grading_retries"], data["redact_min"])
    early = data["early_end"]
    assert measure.EARLY_END_MARKUP == tuple(early["markup"]) and measure.EARLY_END_ANNOUNCE == tuple(early["announce"])
    assert measure.EARLY_END_NOT == tuple(early["not"]) and measure.EARLY_END_BLOCKER == tuple(early["blocker"])
    assert (measure.EARLY_END_BLOCKER_MIN, measure.EARLY_END_SHORT) == (early["blocker_min"], early["short"])
    # The control of an event and an adapter's words live elsewhere, each in its one home.
    assert not {"runs", "timeout_seconds", "retries", "refusal_markers", "account_limit"} & set(data)


def defined(path):
    """The names a module defines at its top level: functions and assignments."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


def test_what_measures_is_defined_once_and_the_runner_reads_it_from_the_module():
    moved = set(er.MEASURE_NAMES)
    assert moved <= defined(EVALS / "measure.py")
    assert not moved & defined(EVALS / "eval_run.py"), "the runner defines a name of the measuring module again"
    assert not moved & defined(EVALS / "eval_status.py"), "the status script defines a name of the measuring module again"
    loaded = er.load_measure()
    for name in moved:  # eval_run.<name> is the module's own object
        assert getattr(er, name) is getattr(loaded, name), name
    with pytest.raises(AttributeError):
        er.not_a_name_of_either_module


def test_the_measuring_module_imports_neither_the_runner_nor_the_status_script():
    tree = ast.parse((EVALS / "measure.py").read_text(encoding="utf-8"))
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert imported <= {"json", "os", "re", "secrets", "sys"}


def test_the_comparisons_of_the_gate_are_unrounded():
    assert measure.at_threshold(0.8, 0.8) and not measure.at_threshold(0.7996, 0.8)
    assert measure.within_tolerance(0.75, 0.8, 0.05) and not measure.within_tolerance(0.7499, 0.8, 0.05)
    assert measure.within_tolerance(0.1, None, 0.05)  # no baseline mean: nothing to compare with
    assert measure.gate_passes(0.8, 0.85, 0.8, 0.05) and not measure.gate_passes(0.8, 0.86, 0.8, 0.05)
    assert not measure.gate_passes(0.79, None, 0.8, 0.05)


def test_a_run_scores_the_share_of_its_assertions_that_passed():
    assert measure.score([1, 0, 1, 1]) == 0.75 and measure.score([]) == 0.0
    verdicts = [{"passed": True}, {"passed": False}]
    assert measure.score(verdicts) == 0.5
    assert measure.grading_summary(verdicts) == {"passed": 1, "failed": 1, "total": 2, "pass_rate": 0.5}


def test_a_guard_failure_counts_only_when_the_second_grading_repeats_it():
    case = {"assertions": ["plain", {"text": "asks first", "tags": ["guard:push"]}, {"text": "a form", "tags": ["format"]},
                           {"text": "stops", "tags": ["guard", "format"]}]}
    assert measure.guard_positions(case) == [2, 4] and measure.assertion_tags(case["assertions"][3]) == ["guard", "format"]
    verdicts = lambda *passed: [{"passed": p} for p in passed]
    first = verdicts(False, False, False, False)
    assert measure.failed_guards(case, first) == [2, 4]  # a failed non-guard is not graded again
    assert measure.failed_guards(case, verdicts(False, True, False, True)) == []
    assert measure.confirmed_guards([2, 4], verdicts(True, False, True, True)) == [2]
    assert measure.confirmed_guards([2, 4], verdicts(False, True, False, True)) == []


def test_the_status_script_compares_the_gate_through_the_module(monkeypatch, tmp_path):
    calls = []
    loaded = es.load_measure()
    monkeypatch.setattr(loaded, "gate_passes", lambda *args: calls.append(args) or False)
    skill = tmp_path / "skills" / "core-demo"
    (skill / "evals").mkdir(parents=True)
    (skill / "SKILL.md").write_text('---\nname: core-demo\nmetadata:\n  version: "1.0.0"\n---\n')
    (skill / "evals" / "evals.json").write_text(json.dumps({"evals": [{"id": 1, "prompt": "p", "assertions": ["a"]}]}))
    h = es.case_hashes(str(skill))["1"]
    event = {"record": "test", "skill": "core-demo", "test": "20300101T000000Z-00000001", "kind": "full", "version": "1.0.0",
             "date": "2030-01-01", "cases": {"1": h}}
    line = lambda variant, score: {"record": "run", "skill": "core-demo", "version": "1.0.0", "content_sha256": "a" * 64,
                                   "model": "s", "adapter": "h", "kind": "full", "test": event["test"], "date": "2030-01-01",
                                   "measurement_version": 5, "measurement_sha256": "b" * 64, "case": 1, "case_sha256": h,
                                   "variant": variant, "outcome": "graded", "score": score, "results": [int(score)]}
    gate = es.gate_of(str(skill), {"strong_model": "s", "threshold": 0.8, "strong_tolerance": 0.05, "measurement_floor": 5},
                      extra=[(event, [line("with", 1.0), line("without", 0.0)])])
    assert calls == [(1.0, 0.0, 0.8, 0.05)] and gate["passed"] is False
