"""Tests for skills/design-brief/scripts/longest_value.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/design-brief/scripts/tests
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


# ---------- design-brief/longest_value.py ----------

LONGEST = "skills/design-brief/scripts/longest_value.py"


def test_longest_value_counts_characters_and_keeps_the_first_of_a_tie():
    r = run(LONGEST, "Button", "Input Group", " Date Picker ", "Tabs")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {
        "count": 4, "longest": "Input Group", "characters": 11, "words": 2,
        "runners_up": [{"value": "Date Picker", "characters": 11}, {"value": "Button", "characters": 6}]}


def test_longest_value_reads_stdin_and_refuses_no_value():
    out = json.loads(run(LONGEST, stdin="Tabs\n\n  Größenübersicht  \n").stdout)
    assert out["count"] == 2 and out["longest"] == "Größenübersicht" and out["characters"] == 15  # characters, not bytes
    r = run(LONGEST, stdin="\n  \n")
    assert r.returncode == 2 and "give the values" in r.stderr and r.stdout == ""


def test_longest_value_refuses_an_unknown_flag_and_takes_dashes_after_a_lone_separator():
    r = run(LONGEST, "Button", "--reprot", "x")
    assert r.returncode == 2 and "unknown argument '--reprot'" in r.stderr and r.stdout == ""
    out = json.loads(run(LONGEST, "--", "--ds-ink", "Tabs").stdout)
    assert out["longest"] == "--ds-ink" and out["count"] == 2
