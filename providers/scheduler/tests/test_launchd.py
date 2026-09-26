"""Offline tests for providers/scheduler/launchd.py.

Run: uv run --with pytest pytest providers/scheduler/tests

Nothing is loaded into launchd: SCHEDULER_LAUNCHCTL points at a fake launchctl that
records its arguments, and the job and agent folders live in a temporary directory.
"""
from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "launchd.py"


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@pytest.fixture
def env(tmp_path):
    calls = tmp_path / "launchctl-calls.txt"
    fake = tmp_path / "launchctl"
    fake.write_text(f'#!/bin/sh\necho "$@" >> "{calls}"\nexit "${{FAKE_LAUNCHCTL_EXIT:-0}}"\n')
    fake.chmod(0o755)
    values = {
        **os.environ,
        "SCHEDULER_HOME": str(tmp_path / "jobs"),
        "SCHEDULER_AGENTS_DIR": str(tmp_path / "agents"),
        "SCHEDULER_LAUNCHCTL": str(fake),
        "SCHEDULER_NOTIFY": "0",
    }
    values["_calls"] = str(calls)
    return values


def run(env, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], env=env, capture_output=True, text=True)


def command_file(tmp_path, argv_extra=(), grace=120, content="hello"):
    post = tmp_path / "post.txt"
    post.write_text(content)
    marker = tmp_path / "ran.txt"
    spec = {
        "argv": [sys.executable, "-c",
                 "import sys, json; open(sys.argv[2], 'w').write(open(sys.argv[1]).read()); "
                 "print(json.dumps({'post_url': 'https://example.test/post'}))",
                 str(post), str(marker), *argv_extra],
        "cwd": str(tmp_path),
        "snapshot": [str(post)],
        "grace_minutes": grace,
    }
    path = tmp_path / "job.json"
    path.write_text(json.dumps(spec))
    return path, post, marker


def schedule(env, tmp_path, at, job_id="post-1", **kw):
    path, post, marker = command_file(tmp_path, **kw)
    result = run(env, "schedule", "--id", job_id, "--at", iso(at), "--command-file", str(path), "--confirmed")
    return result, post, marker


def job(env, job_id="post-1"):
    return json.loads((Path(env["SCHEDULER_HOME"]) / job_id / "job.json").read_text())


def test_schedule_refuses_without_confirmed(env, tmp_path):
    path, _, _ = command_file(tmp_path)
    at = datetime.now(timezone.utc) + timedelta(days=1)
    result = run(env, "schedule", "--id", "post-1", "--at", iso(at), "--command-file", str(path))
    assert result.returncode == 2
    assert "--confirmed" in result.stderr
    assert not Path(env["SCHEDULER_HOME"]).exists()


def test_dry_run_prints_plist_and_writes_nothing(env, tmp_path):
    path, _, _ = command_file(tmp_path)
    at = datetime.now(timezone.utc) + timedelta(days=2)
    result = run(env, "schedule", "--id", "post-1", "--at", iso(at), "--command-file", str(path), "--dry-run")
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    local = at.astimezone()
    assert out["plist"]["StartCalendarInterval"] == {
        "Month": local.month, "Day": local.day, "Hour": local.hour, "Minute": local.minute}
    assert out["plist"]["ProgramArguments"][-3:] == ["run", "--id", "post-1"]
    assert not Path(env["SCHEDULER_HOME"]).exists()
    assert not Path(env["_calls"]).exists()


def test_past_time_refused(env, tmp_path):
    result, _, _ = schedule(env, tmp_path, datetime.now(timezone.utc) - timedelta(minutes=1))
    assert result.returncode == 2
    assert "past" in result.stderr


def test_schedule_snapshots_files_and_loads_agent(env, tmp_path):
    result, post, _ = schedule(env, tmp_path, datetime.now(timezone.utc) + timedelta(days=1))
    assert result.returncode == 0, result.stderr
    data = job(env)
    copy = Path(data["files"][str(post)]["copy"])
    assert copy.read_text() == "hello"
    assert str(copy) in data["argv"] and str(post) not in data["argv"]
    plist = plistlib.loads((Path(env["SCHEDULER_AGENTS_DIR"]) / "dev.ai-workbench.scheduler.post-1.plist").read_bytes())
    assert plist["Label"] == "dev.ai-workbench.scheduler.post-1"
    calls = Path(env["_calls"]).read_text()
    assert f"bootstrap gui/{os.getuid()}" in calls


def test_editing_the_original_after_scheduling_does_not_change_the_run(env, tmp_path):
    _, post, marker = schedule(env, tmp_path, datetime.now(timezone.utc) + timedelta(minutes=1))
    post.write_text("edited later")
    result = run(env, "run", "--id", "post-1")
    assert result.returncode == 0, result.stderr
    assert marker.read_text() == "hello"
    data = job(env)
    assert data["status"] == "done"
    assert data["post_url"] == "https://example.test/post"
    assert not (Path(env["SCHEDULER_AGENTS_DIR"]) / "dev.ai-workbench.scheduler.post-1.plist").exists()


def test_run_refuses_a_changed_copy(env, tmp_path):
    _, post, marker = schedule(env, tmp_path, datetime.now(timezone.utc) + timedelta(minutes=1))
    copy = Path(job(env)["files"][str(post)]["copy"])
    copy.chmod(0o600)
    copy.write_text("tampered")
    result = run(env, "run", "--id", "post-1")
    assert result.returncode == 1
    assert job(env)["status"] == "refused"
    assert not marker.exists()


def test_run_twice_runs_once(env, tmp_path):
    _, _, marker = schedule(env, tmp_path, datetime.now(timezone.utc) + timedelta(minutes=1))
    assert run(env, "run", "--id", "post-1").returncode == 0
    marker.unlink()
    assert run(env, "run", "--id", "post-1").returncode == 0
    assert not marker.exists()


def test_early_fire_waits(env, tmp_path):
    _, _, marker = schedule(env, tmp_path, datetime.now(timezone.utc) + timedelta(hours=3))
    assert run(env, "run", "--id", "post-1").returncode == 0
    assert job(env)["status"] == "scheduled"
    assert not marker.exists()


def test_late_fire_after_grace_is_missed(env, tmp_path):
    _, _, marker = schedule(env, tmp_path, datetime.now(timezone.utc) + timedelta(minutes=1), grace=0)
    data = job(env)
    data["at"] = iso(datetime.now(timezone.utc) - timedelta(minutes=10))
    (Path(env["SCHEDULER_HOME"]) / "post-1" / "job.json").write_text(json.dumps(data))
    assert run(env, "run", "--id", "post-1").returncode == 1
    assert job(env)["status"] == "missed"
    assert not marker.exists()


def test_failed_command_is_recorded(env, tmp_path):
    path, _, _ = command_file(tmp_path)
    spec = json.loads(path.read_text())
    spec["argv"] = [sys.executable, "-c", "import sys; sys.exit(4)"]
    path.write_text(json.dumps(spec))
    at = datetime.now(timezone.utc) + timedelta(minutes=1)
    assert run(env, "schedule", "--id", "post-1", "--at", iso(at), "--command-file", str(path), "--confirmed").returncode == 0
    assert run(env, "run", "--id", "post-1").returncode == 1
    data = job(env)
    assert data["status"] == "failed" and data["exit_code"] == 4


def test_cancel_and_list(env, tmp_path):
    schedule(env, tmp_path, datetime.now(timezone.utc) + timedelta(days=1))
    assert run(env, "cancel", "--id", "post-1").returncode == 2
    assert run(env, "cancel", "--id", "post-1", "--confirmed").returncode == 0
    listed = json.loads(run(env, "list").stdout)["jobs"]
    assert [(j["id"], j["status"], j["plist_present"]) for j in listed] == [("post-1", "cancelled", False)]


def test_bootstrap_failure_is_reported(env, tmp_path):
    env["FAKE_LAUNCHCTL_EXIT"] = "5"
    result, _, _ = schedule(env, tmp_path, datetime.now(timezone.utc) + timedelta(days=1))
    assert result.returncode == 1
    assert job(env)["status"] == "failed"
