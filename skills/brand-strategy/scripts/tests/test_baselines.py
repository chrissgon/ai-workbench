"""Tests for skills/brand-strategy/scripts/baselines.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/brand-strategy/scripts/tests
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def run(rel: str, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / rel), *args], capture_output=True, text=True,
                          cwd=cwd, input=stdin, timeout=60)


BASELINES = "skills/brand-strategy/scripts/baselines.py"


def test_baselines_refuses_names_that_are_not_package_or_repo_names():
    for args in (["--npm", "../../etc"], ["--github", "owner"], ["--github", "a/b?x=1"], ["--npm", "x", "--today", "yesterday"], []):
        r = run(BASELINES, *args)
        assert r.returncode == 2, (args, r.stdout, r.stderr)
        assert r.stdout == ""
