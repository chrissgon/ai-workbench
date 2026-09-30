"""Offline tests of skills/mkt-content-plan/scripts/slots.py: dates, pillars and the language rotation."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SLOTS = Path(__file__).resolve().parents[2] / "skills/mkt-content-plan/scripts/slots.py"


def run(*args):
    r = subprocess.run([sys.executable, str(SLOTS), "--start", "2026-10-12", "--days", "mon,wed,fri", "--time", "09:30",
                        "--tz", "America/Sao_Paulo", "--pillars", "a|b|c", "--rotation", "PT,EN,PT;EN,PT,EN",
                        "--today", "2026-09-30", *args], capture_output=True, text=True, timeout=60)
    return r.returncode, (json.loads(r.stdout) if r.returncode == 0 else r.stderr)


@pytest.mark.parametrize("heading", ["## Week 1: 2026-10-05 (rotation A)", "## Semana 1: 2026-10-05 (rotação A)"])  # validate: allow english-only -- the Portuguese heading under test
def test_after_calendar_continues_the_rotation_in_any_language(tmp_path, heading):
    cal = tmp_path / "calendar.md"
    cal.write_text(f"# Calendar\n\n{heading}\n\n| # | When |\n")
    code, out = run("--after-calendar", str(cal))
    assert code == 0
    assert out["first_week"] == "B"
    assert [s["language"] for s in out["slots"]] == ["EN", "PT", "EN"]
    assert [s["at"] for s in out["slots"]] == ["2026-10-12T09:30:00-03:00", "2026-10-14T09:30:00-03:00",
                                                "2026-10-16T09:30:00-03:00"]
    assert [s["pillar"] for s in out["slots"]] == ["a", "b", "c"]


def test_a_start_that_is_not_in_the_future_is_refused():
    code, err = run("--today", "2026-10-12")
    assert code == 2 and "not after today" in err


def test_without_a_previous_calendar_the_first_week_is_A():
    code, out = run()
    assert out["first_week"] == "A" and [s["language"] for s in out["slots"]] == ["PT", "EN", "PT"]
