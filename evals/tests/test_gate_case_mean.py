"""Tests of the gate's means in evals/eval_status.py gate_of: each is the mean of the cases' means, so that a case
with more lines weighs as much as the others. The evidence is written as test_bands.py writes it. No model is
called.

Run: uv run --with pytest pytest evals/tests/test_gate_case_mean.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("bands_tests_for_case_mean", Path(__file__).with_name("test_bands.py"))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
es = b.es


def two_cases(root):
    return b.skill(root, cases=[{"id": i, "prompt": f"p{i}", "assertions": [f"a{j}" for j in range(10)]} for i in (1, 2)])


def test_a_case_with_more_baseline_lines_weighs_as_much_as_the_others(tmp_path):
    folder = two_cases(tmp_path)
    lines = [(c, "with", 1.0, None) for c in (1, 2) for _ in range(3)]
    lines += [(1, "without", 1.0, None)] + [(2, "without", 0.0, None)] * 3
    b.event(folder, "full", "1.0.0", "2030-01-01", lines)
    gate = es.gate_of(str(folder), b.CFG)
    assert gate["computed"] and gate["baseline"] == pytest.approx(0.5)  # over lines it was 0.25


def test_with_as_many_lines_per_case_the_means_are_those_over_lines(tmp_path):
    folder = two_cases(tmp_path)
    with_scores, base_scores = {1: [1.0, 0.8, 0.9], 2: [0.6, 0.7, 1.0]}, {1: [0.5, 0.3, 0.4], 2: [0.1, 0.2, 0.6]}
    lines = [(c, "with", s, None) for c, scores in with_scores.items() for s in scores]
    lines += [(c, "without", s, None) for c, scores in base_scores.items() for s in scores]
    b.event(folder, "full", "1.0.0", "2030-01-01", lines)
    gate = es.gate_of(str(folder), b.CFG)
    flat = lambda d: [s for scores in d.values() for s in scores]
    assert gate["computed"]
    assert gate["with"] == pytest.approx(sum(flat(with_scores)) / 6)
    assert gate["baseline"] == pytest.approx(sum(flat(base_scores)) / 6)
