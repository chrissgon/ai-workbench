"""Tests for skills/ops-branch-sync/scripts/sync-status.sh: how a branch stands against the remote copy of its base.

Run: uv run --with pytest pytest skills/ops-branch-sync/scripts/tests

Offline: the remote is a bare repository in a temporary folder, and PATH holds only the tools the script needs,
so no hosting CLI and no network tool can be reached. Every name below is fictional.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "sync-status.sh"
BASH = shutil.which("bash")


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@localhost",
                        "-c", "commit.gpgsign=false", *args], check=True, capture_output=True, text=True)
    return r.stdout.strip()


def commit(repo: Path, name: str, text: str, message: str) -> str:
    (repo / name).write_text(text, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    """A branch `feature` one commit ahead of main; the remote main moved on by one commit that changes a manifest,
    and this clone has not fetched it yet."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True, capture_output=True)
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q")
    first = commit(work, "app.py", "x = 1\n", "base")
    git(work, "branch", "-q", "-M", "main")
    git(work, "remote", "add", "origin", str(origin))
    git(work, "push", "-q", "origin", "main")
    commit(work, "package.json", '{"name": "harbor-notes"}\n', "add a manifest")
    commit(work, "notes.md", "notes\n", "add notes")
    git(work, "push", "-q", "origin", "main")
    git(work, "reset", "-q", "--hard", first)
    git(work, "update-ref", "refs/remotes/origin/main", first)
    git(work, "switch", "-q", "-c", "feature")
    commit(work, "feature.py", "y = 2\n", "feature work")
    return work


def run(cwd: Path, tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    bin_dir = tmp_path / "bin"
    if not bin_dir.exists():
        bin_dir.mkdir()
        for name in ("python3", "sed"):
            (bin_dir / name).symlink_to(shutil.which(name))
        # git through a wrapper, not a link: started from a link, a git that finds its helper programs
        # relative to its own path (the one a commit hook has first on PATH) cannot reach a remote.
        (bin_dir / "git").write_text(f'#!/bin/sh\nexec "{shutil.which("git")}" "$@"\n', encoding="utf-8")
        (bin_dir / "git").chmod(0o755)
    env = {**os.environ, "PATH": str(bin_dir)}
    return subprocess.run([BASH, str(SCRIPT), *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=60)


def test_help_exits_zero_and_prints_the_usage(tmp_path):
    r = run(tmp_path, tmp_path, "--help")
    assert r.returncode == 0
    assert "Usage: bash sync-status.sh" in r.stdout and "--no-fetch" in r.stdout


def test_an_unknown_option_exits_two(tmp_path):
    r = run(tmp_path, tmp_path, "--rebase")
    assert r.returncode == 2 and "unknown option '--rebase'" in r.stderr and r.stdout == ""


def test_after_a_fetch_the_branch_is_behind_and_the_changed_manifest_is_named(repo, tmp_path):
    r = run(repo, tmp_path)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["branch"] == "feature" and out["base"] == "main" and out["compared_with"] == "origin/main"
    assert out["fetched"] is True
    assert out["ahead"] == 1 and out["behind"] == 2
    assert out["local_base_behind_remote"] == 2
    assert out["base_changed_dependencies"] == ["package.json"]
    assert out["pushed"] is False and out["open_pull_request"] is None
    assert out["merging"] is False and out["conflicted"] == [] and out["uncommitted"] == [] and out["untracked"] == []


def test_without_a_fetch_the_stale_remote_copy_is_what_is_compared(repo, tmp_path):
    out = json.loads(run(repo, tmp_path, "--no-fetch").stdout)
    assert out["fetched"] is False
    assert out["ahead"] == 1 and out["behind"] == 0 and out["base_changed_dependencies"] == []


def test_uncommitted_untracked_and_pushed_are_reported(repo, tmp_path):
    git(repo, "push", "-q", "origin", "feature")
    (repo / "feature.py").write_text("y = 3\n", encoding="utf-8")
    (repo / "scratch.txt").write_text("draft\n", encoding="utf-8")
    out = json.loads(run(repo, tmp_path, "--no-fetch", "--base", "main").stdout)
    assert out["pushed"] is True
    assert len(out["uncommitted"]) == 1 and out["uncommitted"][0].endswith("feature.py")
    assert out["untracked"] == ["scratch.txt"]


def test_a_merge_in_conflict_lists_the_files_in_conflict(repo, tmp_path):
    git(repo, "switch", "-q", "main")
    commit(repo, "feature.py", "y = 9\n", "the same file on main")
    git(repo, "switch", "-q", "feature")
    merge = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@localhost",
                            "-c", "commit.gpgsign=false", "merge", "main"], capture_output=True, text=True)
    assert merge.returncode != 0
    out = json.loads(run(repo, tmp_path, "--no-fetch").stdout)
    assert out["merging"] is True and out["conflicted"] == ["feature.py"]
