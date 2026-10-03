"""Tests for skills/ops-repo-baseline/scripts/baseline_status.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/ops-repo-baseline/scripts/tests
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


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@localhost",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)


BASELINE = "skills/ops-repo-baseline/scripts/baseline_status.py"


def test_baseline_status_reports_ecosystems_pins_and_missing_files(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / "fixtures" / "demo").mkdir(parents=True)
    git(repo, "init", "-q")
    (repo / "package.json").write_text("{}\n")
    (repo / "fixtures" / "demo" / "package.json").write_text("{}\n")
    (repo / "ignored").mkdir()
    (repo / "ignored" / "package.json").write_text("{}\n")
    (repo / ".gitignore").write_text("ignored/\n.env\n")
    (repo / ".github" / "workflows" / "ci.yml").write_text(
        "on: push\njobs:\n  t:\n    steps:\n      - uses: actions/checkout@v4\n"
        "      - uses: actions/setup-node@" + "a" * 40 + " # v4\n      - uses: ./local-action\n")
    out = run(BASELINE, "--root", str(repo))
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)
    assert {e["name"]: e["folders"] for e in data["ecosystems"]} == {"github-actions": ["/"], "npm": ["/", "/fixtures/demo"]}
    wf = data["workflows"][0]
    assert wf["unpinned_actions"] == ["actions/checkout@v4"] and wf["declares_permissions"] is False
    assert data["files"]["env_ignored"] is True and data["files"]["codeowners"] is None
    assert data["git"]["is_repo"] is True and data["git"]["commits"] == 0
    assert run(BASELINE, "--root").returncode == 2


def test_baseline_status_usage_errors_exit_2_with_a_message(tmp_path):
    for args in (["--root"], ["--deep"], ["--root", str(tmp_path / "missing")]):
        r = run(BASELINE, *args)
        assert r.returncode == 2 and r.stderr.startswith("error:") and r.stdout == "", args
        assert "Traceback" not in r.stderr
    assert run(BASELINE, "--help").returncode == 0
