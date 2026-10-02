"""Offline tests of skills/mkt-content-plan/scripts/slots.py: dates, pillars and the language rotation."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SLOTS = Path(__file__).resolve().parents[4] / "skills/mkt-content-plan/scripts/slots.py"


def run(*args):
    r = subprocess.run([sys.executable, str(SLOTS), "--start", "2027-10-11", "--days", "mon,wed,fri", "--time", "09:30",
                        "--tz", "America/Sao_Paulo", "--pillars", "a|b|c", "--rotation", "PT,EN,PT;EN,PT,EN",
                        "--today", "2027-09-29", *args], capture_output=True, text=True, timeout=60)
    return r.returncode, (json.loads(r.stdout) if r.returncode == 0 else r.stderr)


@pytest.mark.parametrize("heading", ["## Week 1: 2027-10-04 (rotation A)", "## Semana 1: 2027-10-04 (rotação A)"])  # validate: allow english-only -- the Portuguese heading under test
def test_after_calendar_continues_the_rotation_in_any_language(tmp_path, heading):
    cal = tmp_path / "calendar.md"
    cal.write_text(f"# Calendar\n\n{heading}\n\n| # | When |\n")
    code, out = run("--after-calendar", str(cal))
    assert code == 0
    assert out["first_week"] == "B"
    assert [s["language"] for s in out["slots"]] == ["EN", "PT", "EN"]
    assert [s["at"] for s in out["slots"]] == ["2027-10-11T09:30:00-03:00", "2027-10-13T09:30:00-03:00",
                                                "2027-10-15T09:30:00-03:00"]
    assert [s["pillar"] for s in out["slots"]] == ["a", "b", "c"]


def test_a_start_that_is_not_in_the_future_is_refused():
    code, err = run("--today", "2027-10-11")
    assert code == 2 and "not after today" in err


def test_without_a_previous_calendar_the_first_week_is_A():
    code, out = run()
    assert out["first_week"] == "A" and [s["language"] for s in out["slots"]] == ["PT", "EN", "PT"]


def test_row_and_week_numbers_continue_after_the_previous_calendar(tmp_path):
    cal = tmp_path / "calendar.md"
    cal.write_text("# Calendar\n\n## Week 1: 2027-10-04 (rotation A)\n\n| # | When |\n|---|------|\n"
                   "| 1 | 2027-10-04T09:00:00-03:00 |\n| 2 | 2027-10-06T09:00:00-03:00 |\n"
                   "| 3 | 2027-10-08T09:00:00-03:00 |\n")
    code, out = run("--after-calendar", str(cal), "--weeks", "2")
    assert code == 0
    assert out["after_row"] == 3
    assert [s["n"] for s in out["slots"]] == [4, 5, 6, 7, 8, 9]
    assert [s["week"] for s in out["slots"]] == [2, 2, 2, 3, 3, 3]
    assert [s["rotation"] for s in out["slots"]] == ["B", "B", "B", "A", "A", "A"]


def test_without_a_previous_calendar_rows_start_at_one():
    code, out = run()
    assert out["after_row"] == 0 and [s["n"] for s in out["slots"]] == [1, 2, 3]
    assert [s["week"] for s in out["slots"]] == [1, 1, 1]


def test_a_list_of_times_stays_with_its_days_when_they_are_sorted():
    r = subprocess.run([sys.executable, str(SLOTS), "--start", "2027-10-11", "--days", "fri,mon", "--time", "12:00,09:00",
                        "--tz", "America/Sao_Paulo", "--pillars", "a|b", "--rotation", "EN,PT", "--today", "2027-09-29"],
                       capture_output=True, text=True, timeout=60)
    out = json.loads(r.stdout)
    assert [(s["weekday"], s["at"][11:16]) for s in out["slots"]] == [("mon", "09:00"), ("fri", "12:00")]


def test_an_empty_rotation_and_too_few_pillars_say_what_to_do():
    code, err = run("--rotation", ";")
    assert code == 2 and "at least one week of languages" in err
    code, err = run("--pillars", "a|b")
    assert code == 2 and "ask the user which pillar takes the extra posts" in err
