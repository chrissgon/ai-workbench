"""Tests for shared/scripts/rank.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest shared/scripts/tests
"""
from __future__ import annotations

import json

from shared_helpers import clean_usage_error, run

RANK = "rank.py"


def options(a_demand: dict, b_demand: dict) -> str:
    return json.dumps({"criteria": [{"name": "demand"}, {"name": "fit", "weight": 2}],
                       "options": [{"name": "A", "scores": {"demand": a_demand, "fit": {"score": 1, "sources": []}}},
                                   {"name": "B", "scores": {"demand": b_demand, "fit": {"score": 3, "sources": ["2"]}}}]})


GOOD = options({"score": 5, "sources": ["1"]}, {"score": 2, "sources": ["3"]})


def test_rank_orders_by_weighted_total_and_marks_missing_evidence():
    r = run(RANK, stdin=GOOD)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert [o["name"] for o in out["ranked"]] == ["B", "A"]
    assert out["ranked"][0]["total"] == 8 and out["ranked"][1]["total"] == 7
    assert out["close_call"] is True
    assert "1 (no evidence)" in out["table"]


def test_rank_reads_a_file_as_it_reads_standard_input(tmp_path):
    path = tmp_path / "options.json"
    path.write_text(GOOD, encoding="utf-8")
    assert json.loads(run(RANK, "--input", str(path)).stdout) == json.loads(run(RANK, stdin=GOOD).stdout)


def test_rank_refuses_a_score_without_a_source_with_exit_1():
    r = run(RANK, stdin=options({"score": 4, "sources": []}, {"score": 2, "sources": ["3"]}))
    assert r.returncode == 1
    assert "has no source" in r.stderr
    assert r.stdout == ""


def test_rank_refuses_out_of_range_and_unscored_criteria():
    bad = json.loads(options({"score": 6, "sources": ["1"]}, {"score": 2, "sources": ["3"]}))
    del bad["options"][1]["scores"]["fit"]
    r = run(RANK, stdin=json.dumps(bad))
    assert r.returncode == 1
    assert "integer from 1 to 5" in r.stderr and "is not scored" in r.stderr


def test_rank_translates_the_no_evidence_label():
    r = run(RANK, "--no-evidence-label", "sin evidencia", stdin=GOOD)
    assert r.returncode == 0, r.stderr
    assert "1 (sin evidencia)" in json.loads(r.stdout)["table"]


def test_rank_refuses_sources_that_are_not_references():
    r = run(RANK, stdin=options({"score": 4, "sources": ["recurring revenue model"]}, {"score": 2, "sources": ["3"]}))
    assert r.returncode == 1
    assert "are not references" in r.stderr
    ok = run(RANK, stdin=options({"score": 4, "sources": ["2b", "M1"]}, {"score": 2, "sources": [3]}))
    assert ok.returncode == 0, ok.stderr


def test_an_input_that_cannot_be_read_exits_2_and_a_refused_content_exits_1(tmp_path):
    """The input was unreadable and the scores were wrong under the same exit code, 1; the other check scripts
    answer 2 for a file they cannot read."""
    missing = run(RANK, "--input", str(tmp_path / "absent.json"))
    assert clean_usage_error(missing) and "cannot read input" in missing.stderr
    assert clean_usage_error(run(RANK, "--input", str(tmp_path)))  # a folder
    assert clean_usage_error(run(RANK, stdin="not json"))
    binary = tmp_path / "options.json"
    binary.write_bytes(b"\xff\xfe{}")
    assert clean_usage_error(run(RANK, "--input", str(binary)))
    assert run(RANK, stdin="[]").returncode == 1  # read, and refused: not an object
    assert run(RANK, stdin='{"criteria": [], "options": []}').returncode == 1


def test_help_and_usage_errors():
    r = run(RANK, "--help")
    assert r.returncode == 0 and "Usage:" in r.stdout and "Exit codes" in r.stdout
    assert clean_usage_error(run(RANK, "--input"))  # a flag given last, without its value
    assert clean_usage_error(run(RANK, "--nope"))
