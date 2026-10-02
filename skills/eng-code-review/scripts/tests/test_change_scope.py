"""Tests for skills/eng-code-review/scripts/change_scope.py. Offline; every name and number below is fictional.
Secret-like strings are assembled from pieces so that this file does not trip the scanner.

Run: uv run --with pytest pytest skills/eng-code-review/scripts/tests
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


# ---------- eng-code-review/change_scope.py and the shared redaction (H06, L19, M22) ----------

SCOPE = "skills/eng-code-review/scripts/change_scope.py"
AWS = "AKIA" + "Q7ZT2MLP4RX9KW1V"
VALUE = "q8Zt2mLp" + "4Rx9Kw1v"


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


def test_secret_suspect_markers_are_masked(tmp_path):
    repo = repo_with_change(tmp_path, f'API_TOKEN = "{VALUE}"\nAWS = "{AWS}"\nprint(API_TOKEN, "{AWS}")  # TODO\n')
    r = run(SCOPE, "--repo", str(repo), "--worktree")
    assert r.returncode == 0, r.stderr
    assert VALUE not in r.stdout and AWS not in r.stdout
    markers = json.loads(r.stdout)["markers"]
    secrets = [m for m in markers if m["kind"] == "secret-suspect"]
    assert {m["line"] for m in secrets} == {2, 3, 4}
    assert {m["rule"] for m in secrets} == {"credential assignment", "AWS access key"}
    assert any(m["kind"] == "todo" and "<redacted AWS access key>" in m["text"] for m in markers)
    assert all("<redacted" in m["text"] for m in secrets)


def test_range_that_looks_like_an_option_is_refused(tmp_path):
    repo = repo_with_change(tmp_path, "y = 2\n")
    git(repo, "commit", "-q", "-am", "change")
    target = tmp_path / "written"
    for rng in (f"--output={target}", "-x..HEAD", f"HEAD..--output={target}", "no-such-ref..HEAD"):
        r = run(SCOPE, "--repo", str(repo), "--range", rng)
        assert r.returncode == 2, (rng, r.stderr)
        assert "refused" in r.stderr
    assert not target.exists()
    for rng in ("HEAD~1..HEAD", "HEAD~1...HEAD"):
        ok = run(SCOPE, "--repo", str(repo), "--range", rng)
        assert ok.returncode == 0, ok.stderr
        assert json.loads(ok.stdout)["totals"]["files"] == 1
