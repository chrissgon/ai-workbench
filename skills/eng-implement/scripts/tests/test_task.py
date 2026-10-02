"""Tests for skills/eng-implement/scripts/task.py: reading a task of the backlog and setting its status.

Run: uv run --with pytest pytest skills/eng-implement/scripts/tests

Offline; the backlog below is fictional.
"""
from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "task.py"

BACKLOG = """# Backlog: Harbor notes

## Milestone 1

- T-auth-1: Add the sign-in form
  Does: renders the form and posts the credentials
  Depends on: none
  Check: the form test passes
  Status: done (2030-01-05)

- T-auth-2: Keep the session after a reload
  Does: stores the session and restores it
  Depends on: T-auth-1, T-auth-9
  Check: the reload test passes
  Size: S

- T-notes-1: List the notes
  Does: shows the notes of the signed-in user
  Depends on: T-auth-1
"""


def backlog(tmp_path: Path) -> Path:
    path = tmp_path / "backlog.md"
    path.write_text(BACKLOG, encoding="utf-8")
    return path


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60)


def test_help_exits_zero_and_no_argument_is_a_usage_error():
    r = run("--help")
    assert r.returncode == 0 and "--backlog" in r.stdout
    assert run().returncode == 2


def test_a_task_is_read_with_its_fields_and_the_status_of_its_dependencies(tmp_path):
    path = backlog(tmp_path)
    r = run("--backlog", str(path), "--id", "T-auth-2")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["title"] == "Keep the session after a reload" and out["status"] == "todo"
    assert out["fields"]["Size"] == "S" and out["fields"]["Check"] == "the reload test passes"
    assert out["dependencies"] == {"T-auth-1": "done", "T-auth-9": "missing"}
    assert out["dependencies_done"] is False
    ready = json.loads(run("--backlog", str(path), "--id", "T-notes-1").stdout)
    assert ready["dependencies"] == {"T-auth-1": "done"} and ready["dependencies_done"] is True
    assert path.read_text(encoding="utf-8") == BACKLOG


def test_setting_a_status_writes_one_dated_line_inside_the_task(tmp_path):
    path = backlog(tmp_path)
    today = datetime.date.today().isoformat()
    r = run("--backlog", str(path), "--id", "T-auth-2", "--status", "blocked", "--note", "waiting for T-auth-9")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["status"] == "blocked"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[lines.index("  Size: S") + 1] == f"  Status: blocked ({today}) waiting for T-auth-9"
    out = json.loads(run("--backlog", str(path), "--id", "T-auth-2", "--status", "in-progress").stdout)
    assert out["status"] == "in-progress"
    text = path.read_text(encoding="utf-8")
    assert text.count("  Status:") == 2 and f"  Status: in-progress ({today})\n" in text and "blocked" not in text
    assert "  Status: done (2030-01-05)" in text


def test_an_unknown_task_exits_one_and_lists_the_tasks_there_are(tmp_path):
    r = run("--backlog", str(backlog(tmp_path)), "--id", "T-auth-7")
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["error"] == "task T-auth-7 not found"
    assert out["available"] == ["T-auth-1", "T-auth-2", "T-notes-1"]


def test_usage_errors_exit_two_and_leave_the_backlog_as_it_was(tmp_path):
    path = backlog(tmp_path)
    for args in (["--backlog", str(path)], ["--id", "T-auth-1"], ["--backlog", str(path), "--id", "T-auth-1", "--force", "x"],
                 ["--backlog", str(path), "--id", "T-auth-1", "--status", "finished"]):
        r = run(*args)
        assert r.returncode == 2, (args, r.stderr)
        assert r.stderr.startswith("Error:") and r.stdout == ""
    assert path.read_text(encoding="utf-8") == BACKLOG


@pytest.mark.xfail(strict=True, reason="task.py reads argv[i + 1] without checking it exists: a flag given last, "
                                       "without its value, ends in an IndexError traceback (exit 1), not exit 2")
def test_a_flag_without_its_value_is_a_usage_error(tmp_path):
    r = run("--backlog", str(backlog(tmp_path)), "--id")
    assert r.returncode == 2 and "Traceback" not in r.stderr
