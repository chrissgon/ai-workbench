"""Tests for skills/ops-pull-request/scripts/pr-context.sh. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/ops-pull-request/scripts/tests
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@localhost",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)


def repo_with_change(tmp_path: Path, text: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    git(repo, "add", "app.py")
    git(repo, "commit", "-q", "-m", "base")
    (repo / "app.py").write_text("x = 1\n" + text, encoding="utf-8")
    return repo


# ---------- ops-pull-request/pr-context.sh (M22) ----------

PR_CONTEXT = ROOT / "skills/ops-pull-request/scripts/pr-context.sh"
BASH = __import__("shutil").which("bash")


def only_tools(tmp_path: Path, *names: str) -> dict:
    """An environment whose PATH holds only the named tools, so no host CLI or network tool is reachable."""
    import os
    import shutil
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for n in names:
        (bin_dir / n).symlink_to(shutil.which(n))
    return {**os.environ, "PATH": str(bin_dir)}


def test_pr_context_refuses_option_like_base(tmp_path):
    repo = repo_with_change(tmp_path, "y = 2\n")
    env = only_tools(tmp_path, "git", "python3", "sed", "dirname")
    for base in ("--upload-pack=touch pwned", "-x", "main..evil", "a b"):
        r = subprocess.run([BASH, str(PR_CONTEXT), "--base", base], cwd=repo, env=env,
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 2, (base, r.stderr)
        assert "is not a branch name" in r.stderr
    assert not (repo / "pwned").exists()
    git(repo, "branch", "-q", "-M", "main")
    git(repo, "switch", "-q", "-c", "feature")
    git(repo, "commit", "-q", "-am", "feature work")
    r = subprocess.run([BASH, str(PR_CONTEXT), "--base", "main"], cwd=repo, env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["compared_with"] == "main" and len(out["commits"]) == 1
