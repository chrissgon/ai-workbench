"""Tests for skills/eng-implement/scripts/task.py: reading a task of the backlog and setting its status.

Run: uv run --with pytest pytest skills/eng-implement/scripts/tests

Offline; the backlog below is fictional. Two tests make a git repository in a temporary folder.
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

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


def run_in(cwd: Path, *args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60,
                          cwd=cwd, env=env)


def test_help_exits_zero_and_no_argument_is_a_usage_error_on_stderr():
    r = run("--help")
    assert r.returncode == 0 and "--backlog" in r.stdout and "worktree_changes" in r.stdout
    r = run()
    assert r.returncode == 2 and r.stdout == "" and "--backlog" in r.stderr


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
    out = json.loads(r.stdout)
    assert out["status"] == "blocked" and out["previous"] == "todo"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[lines.index("  Size: S") + 1] == f"  Status: blocked ({today}) waiting for T-auth-9"
    out = json.loads(run("--backlog", str(path), "--id", "T-auth-2", "--status", "in-progress").stdout)
    assert out["status"] == "in-progress" and out["previous"] == "blocked"
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
                 ["--backlog", str(path), "--id", "T-auth-1", "--status", "finished"],
                 ["--backlog", str(path), "--id", "T-auth-2", "--note", "a note needs a status"]):
        r = run(*args)
        assert r.returncode == 2, (args, r.stderr)
        assert r.stderr.startswith("Error:") and r.stdout == ""
    assert path.read_text(encoding="utf-8") == BACKLOG


def test_a_flag_without_its_value_is_a_usage_error(tmp_path):
    path = backlog(tmp_path)
    for args in (["--backlog", str(path), "--id"], ["--id", "T-auth-1", "--backlog"],
                 ["--backlog", str(path), "--id", "T-auth-1", "--status"],
                 ["--backlog", str(path), "--id", "T-auth-1", "--status", "done", "--note"],
                 ["--backlog", "--id", "T-auth-1"]):
        r = run(*args)
        assert r.returncode == 2, (args, r.stderr)
        assert "Traceback" not in r.stderr and r.stderr.startswith("Error:") and r.stdout == ""
    assert path.read_text(encoding="utf-8") == BACKLOG


def test_a_missing_backlog_is_a_usage_error_that_names_the_path(tmp_path):
    missing = tmp_path / "docs" / "backlog.md"
    r = run("--backlog", str(missing), "--id", "T-auth-1")
    assert r.returncode == 2 and "Traceback" not in r.stderr and r.stdout == ""
    assert r.stderr.startswith("Error: backlog not found") and str(missing) in r.stderr


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, timeout=60)


def test_setting_a_status_prints_one_line_with_the_working_tree_before_the_write(tmp_path):
    project = tmp_path / "project"
    (project / "docs").mkdir(parents=True)
    (project / "docs" / "backlog.md").write_text(BACKLOG, encoding="utf-8")
    git(project, "init", "-q")
    git(project, "add", "-A")
    git(project, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
        "commit", "-q", "-m", "fixture")
    r = run_in(project, "--backlog", "docs/backlog.md", "--id", "T-auth-2", "--status", "in-progress")
    assert r.returncode == 0, r.stderr
    assert r.stdout.count("\n") == 1
    assert json.loads(r.stdout) == {"id": "T-auth-2", "status": "in-progress", "previous": "todo",
                                    "worktree_changes": []}
    (project / "src.js").write_text("x\n", encoding="utf-8")
    r = run_in(project, "--backlog", "docs/backlog.md", "--id", "T-auth-2", "--status", "done", "--note", "2 passed")
    out = json.loads(r.stdout)
    assert out["previous"] == "in-progress" and out["status"] == "done"
    assert out["worktree_changes"] == [" M docs/backlog.md", "?? src.js"]


def test_outside_a_git_repository_the_working_tree_is_null(tmp_path):
    path = backlog(tmp_path)
    r = run_in(tmp_path, "--backlog", str(path), "--id", "T-auth-2", "--status", "in-progress",
               env_extra={"GIT_CEILING_DIRECTORIES": str(tmp_path.parent)})
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["worktree_changes"] is None
