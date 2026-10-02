"""Tests for skills/biz-market-analysis/scripts/capacity.py. Offline; every name and number below is fictional.

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


CAPACITY = "skills/biz-market-analysis/scripts/capacity.py"


def test_capacity_computes_jobs_per_month_and_refuses_bad_values():
    r = run(CAPACITY, "--hours-per-week", "15", "--hours-per-job", "40", "--utilization", "0.7")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["jobs_per_month"] == 1.1
    assert run(CAPACITY, "--hours-per-week", "0", "--hours-per-job", "40").returncode == 2
    assert run(CAPACITY, "--hours-per-week", "15", "--hours-per-job", "40", "--utilization", "2").returncode == 2
