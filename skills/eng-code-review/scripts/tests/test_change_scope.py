"""Tests for skills/eng-code-review/scripts/change_scope.py. Offline; every name and number below is fictional.
Secret-like strings are assembled from pieces so that this file does not trip the scanner.

Run: uv run --with pytest pytest skills/eng-code-review/scripts/tests
The script is found from this file's own folder, so the tests also run on the skill folder copied alone.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCOPE = Path(__file__).resolve().parents[1] / "change_scope.py"


def run(script: Path, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True,
                          cwd=cwd, input=stdin, timeout=60)


# ---------- eng-code-review/change_scope.py and the shared redaction (H06, L19, M22) ----------

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


# ---------- arguments ----------

def test_value_flag_given_last_exits_2_without_traceback():
    for flag in ("--repo", "--range", "--patch", "--touches", "--max-files", "--max-lines"):
        r = run(SCOPE, "--worktree", flag)
        assert r.returncode == 2, (flag, r.stderr)
        assert f"{flag} needs a value" in r.stderr
        assert "Traceback" not in r.stderr and r.stdout == ""


def test_non_integer_limit_exits_2_without_traceback():
    for flag in ("--max-files", "--max-lines"):
        r = run(SCOPE, "--worktree", flag, "abc")
        assert r.returncode == 2, (flag, r.stderr)
        assert "whole number" in r.stderr and "Traceback" not in r.stderr and r.stdout == ""


def test_no_arguments_prints_the_usage_on_stderr():
    r = run(SCOPE)
    assert r.returncode == 2
    assert r.stdout == "" and "Usage:" in r.stderr


def test_help_exits_0_on_stdout():
    r = run(SCOPE, "--help")
    assert r.returncode == 0 and "Usage:" in r.stdout


# ---------- measurement ----------

PATCH = """diff --git a/src/money.py b/src/money.py
--- a/src/money.py
+++ b/src/money.py
@@ -1,2 +1,3 @@
 def parse(text):
-    return float(text)
+    text = text.strip()
+    return float(text)
diff --git a/tests/test_money.py b/tests/test_money.py
--- a/tests/test_money.py
+++ b/tests/test_money.py
@@ -1 +1,2 @@
 import money
+assert money.parse(" 1 ") == 1.0
"""


def test_patch_file_gives_the_totals_and_the_tests_touched(tmp_path):
    patch = tmp_path / "change.patch"
    patch.write_text(PATCH, encoding="utf-8")
    r = run(SCOPE, "--patch", str(patch), "--touches", "money")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["totals"]["files"] == 2
    assert out["totals"]["added"] == 3 and out["totals"]["deleted"] == 1
    assert out["tests_touched"] == ["tests/test_money.py"]
    assert out["outside_touches"] == []


def test_touches_lists_the_files_outside_the_task(tmp_path):
    repo = repo_with_change(tmp_path, "y = 2\n")
    (repo / "report.py").write_text("z = 3\n", encoding="utf-8")
    r = run(SCOPE, "--repo", str(repo), "--worktree", "--touches", "app")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["outside_touches"] == ["report.py"]


def test_empty_change_exits_3(tmp_path):
    repo = repo_with_change(tmp_path, "")
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    r = run(SCOPE, "--repo", str(repo), "--worktree")
    assert r.returncode == 3, r.stderr
    assert "Nothing to review" in r.stderr


def test_pure_rename_is_counted(tmp_path):
    repo = repo_with_change(tmp_path, "")
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "lib").mkdir()
    (repo / "app.py").rename(repo / "lib" / "app.py")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "move")
    r = run(SCOPE, "--repo", str(repo), "--range", "HEAD~1..HEAD")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["totals"]["pure_renames"] == 1
    assert out["review_groups"]["verify_rename_only"] == ["app.py -> lib/app.py"]
