"""Tests for skills/biz-market-analysis/scripts/rank.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/biz-market-analysis/scripts/tests
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def run(rel: str, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / rel), *args], capture_output=True, text=True,
                          cwd=cwd, input=stdin, timeout=60)


# ---------- biz-market-analysis/rank.py and capacity.py ----------

RANK = "skills/biz-market-analysis/scripts/rank.py"


def options(a_demand: dict, b_demand: dict) -> str:
    return json.dumps({"criteria": [{"name": "demand"}, {"name": "fit", "weight": 2}],
                       "options": [{"name": "A", "scores": {"demand": a_demand, "fit": {"score": 1, "sources": []}}},
                                   {"name": "B", "scores": {"demand": b_demand, "fit": {"score": 3, "sources": ["2"]}}}]})


def test_rank_orders_by_weighted_total_and_marks_missing_evidence():
    r = run(RANK, stdin=options({"score": 5, "sources": ["1"]}, {"score": 2, "sources": ["3"]}))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert [o["name"] for o in out["ranked"]] == ["B", "A"]
    assert out["ranked"][0]["total"] == 8 and out["ranked"][1]["total"] == 7
    assert out["close_call"] is True
    assert "1 (no evidence)" in out["table"]


def test_rank_refuses_a_score_without_a_source():
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
    r = run(RANK, "--no-evidence-label", "sem evidência",
            stdin=options({"score": 5, "sources": ["1"]}, {"score": 2, "sources": ["3"]}))
    assert r.returncode == 0, r.stderr
    assert "1 (sem evidência)" in json.loads(r.stdout)["table"]


def test_rank_refuses_sources_that_are_not_references():
    r = run(RANK, stdin=options({"score": 4, "sources": ["recurring revenue model"]}, {"score": 2, "sources": ["3"]}))
    assert r.returncode == 1
    assert "are not references" in r.stderr
    ok = run(RANK, stdin=options({"score": 4, "sources": ["2b", "M1"]}, {"score": 2, "sources": [3]}))
    assert ok.returncode == 0, ok.stderr
