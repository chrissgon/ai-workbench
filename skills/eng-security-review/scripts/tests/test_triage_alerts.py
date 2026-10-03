"""Tests for skills/eng-security-review/scripts/triage_alerts.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/eng-security-review/scripts/tests
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


# ---------- eng-security-review/triage_alerts.py ----------

TRIAGE = "skills/eng-security-review/scripts/triage_alerts.py"


def alert(number: int, package: str, manifest: str, fix: str | None, severity: str = "high") -> dict:
    return {"number": number, "state": "open", "severity": severity, "ecosystem": "npm",
            "package": package, "manifest_path": manifest, "first_patched_version": fix,
            "summary": "third-party text"}


def test_triage_groups_and_takes_the_highest_fix(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"kit": "2.3.0"}}))
    (tmp_path / "package-lock.json").write_text(json.dumps(
        {"packages": {"node_modules/kit": {"version": "2.3.0"}}}))
    demo = tmp_path / "examples" / "demo"
    demo.mkdir(parents=True)
    (demo / "package.json").write_text(json.dumps({"dependencies": {"tpl": "1.0.2"}}))
    alerts = [alert(1, "kit", "package.json", "2.3.4"), alert(2, "kit", "package.json", "2.10.1", "low"),
              alert(3, "tpl", "examples/demo/package.json", "2.0.0", "critical"),
              {**alert(4, "kit", "package.json", "9.0.0"), "state": "dismissed"}]
    out = run(TRIAGE, "--alerts", "-", "--repo", str(tmp_path), stdin=json.dumps({"alerts": alerts}))
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)
    assert data["open_count"] == 3
    kit, tpl = (next(g for g in data["groups"] if g["package"] == p) for p in ("kit", "tpl"))
    assert kit["clears_all_at"] == "2.10.1" and kit["major_bump"] is False
    assert kit["lockfiles"] == ["package-lock.json"] and kit["locked_versions"] == {"package-lock.json": "2.3.0"}
    assert tpl["major_bump"] is True and tpl["lockfiles"] == []
    assert tpl["parent_lockfiles"] == ["package-lock.json"] and tpl["locked_versions"] == {}
    assert tpl["path_hints"] == ["examples"] and data["groups"][0]["package"] == "tpl"


def test_triage_never_reads_a_manifest_outside_the_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"kit": "1.0.0"}}))
    alerts = [alert(1, "kit", "../package.json", "1.0.1"), alert(2, "kit", "/etc/package.json", "1.0.1")]
    out = run(TRIAGE, "--alerts", "-", "--repo", str(repo), stdin=json.dumps(alerts))
    assert out.returncode == 0, out.stderr
    for group in json.loads(out.stdout)["groups"]:
        assert group["manifest_found"] is False and group["declared"] is None


def test_triage_usage_errors_exit_2_with_a_message(tmp_path):
    for args in (["--alerts"], ["--alerts", "a.json", "--repo"], ["--repo", str(tmp_path)],
                 ["--alerts", "a.json"], ["--alerts", "a.json", "--repo", str(tmp_path / "missing")],
                 ["--unknown"]):
        out = run(TRIAGE, *args, cwd=tmp_path)
        assert out.returncode == 2, (args, out.returncode, out.stderr)
        assert out.stderr.strip() and out.stdout == "", args


def test_triage_unreadable_alerts_exit_1(tmp_path):
    out = run(TRIAGE, "--alerts", str(tmp_path / "none.json"), "--repo", str(tmp_path))
    assert out.returncode == 1 and "cannot read alerts" in out.stderr and out.stdout == ""
    (tmp_path / "bad.json").write_text("{not json")
    out = run(TRIAGE, "--alerts", str(tmp_path / "bad.json"), "--repo", str(tmp_path))
    assert out.returncode == 1 and out.stdout == ""


def test_triage_help_exits_0():
    out = run(TRIAGE, "--help")
    assert out.returncode == 0 and "Usage:" in out.stdout
