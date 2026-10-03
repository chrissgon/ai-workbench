"""Tests for skills/ops-repo-baseline/scripts/secret_scan.py. Offline; every name and number below is fictional.
Secret-like strings are assembled from pieces so that this file does not trip the scanner.

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


# ---------- ops-repo-baseline/secret_scan.py and baseline_status.py ----------

SECRET_SCAN = "skills/ops-repo-baseline/scripts/secret_scan.py"


FAKE = "prod_" + "4f9a8b7c6d5e4f3a2b1c"


def test_secret_scan_finds_a_key_removed_from_the_tree_and_never_prints_it(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "pay.js").write_text(f'export const PAYMENTS_API_KEY = "{FAKE}";\n')
    (repo / "app.js").write_text("export const x = 1;\n")
    git(repo, "add", "pay.js", "app.js")
    git(repo, "commit", "-q", "-m", "add")
    git(repo, "rm", "-q", "pay.js")
    git(repo, "commit", "-q", "-m", "remove")
    tree = run(SECRET_SCAN, "--root", str(repo), "--json")
    assert tree.returncode == 0 and json.loads(tree.stdout)["findings"] == []
    hist = run(SECRET_SCAN, "--root", str(repo), "--history", "--json")
    assert hist.returncode == 1
    found = json.loads(hist.stdout)["findings"]
    assert [(f["path"].split("@")[0], f["rule"], f["kind"]) for f in found] == [("pay.js", "secret-assignment", "real")]
    assert found[0]["action"].startswith("revoke")
    assert FAKE[5:] not in hist.stdout + hist.stderr
    (repo / ".secret-scan-allow").write_text("pay.js secret-assignment -- planted for a test\n")
    assert run(SECRET_SCAN, "--root", str(repo), "--history").returncode == 0
    (repo / ".secret-scan-allow").write_text("*.js secret-assignment -- too broad\n")
    assert run(SECRET_SCAN, "--root", str(repo), "--history").returncode == 1


def test_secret_scan_flags_credential_files_but_not_examples(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / ".env").write_text("DEBUG=1\n")
    (repo / ".env.example").write_text("API_KEY=\n")
    out = json.loads(run(SECRET_SCAN, "--root", str(repo), "--json").stdout)
    assert [(f["path"], f["rule"]) for f in out["findings"]] == [(".env", "secret-file")]
    (repo / "tests").mkdir()
    (repo / "tests" / "fake.py").write_text(f"API_KEY = '{FAKE}'\n")
    kinds = {f["path"]: f["kind"] for f in json.loads(run(SECRET_SCAN, "--root", str(repo), "--json").stdout)["findings"]}
    assert kinds == {".env": "real", "tests/fake.py": "planted?"}
    assert run(SECRET_SCAN, "--root", str(tmp_path / "missing")).returncode == 2


def test_secret_scan_usage_errors_exit_2_with_a_message(tmp_path):
    r = run(SECRET_SCAN, "--root")
    assert r.returncode == 2 and "--root needs a value" in r.stderr and r.stdout == ""
    r = run(SECRET_SCAN, "--deep")
    assert r.returncode == 2 and "unknown option '--deep'" in r.stderr and r.stdout == ""
    r = run(SECRET_SCAN, "--root", str(tmp_path))
    assert r.returncode == 2 and "not a git repository" in r.stderr
    assert "Traceback" not in r.stderr
    r = run(SECRET_SCAN, "--help")
    assert r.returncode == 0 and "--history" in r.stdout


def test_secret_scan_uses_its_redact_copy_for_bearer_tokens(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    token = "Bearer " + "q7Lm2Xc9Vb4Nz8Kp3Rt6Wy1"
    (repo / "client.js").write_text(f'const API_KEY = "{FAKE}"; // {token}\n')
    r = run(SECRET_SCAN, "--root", str(repo), "--json")
    out = json.loads(r.stdout)
    assert r.returncode == 1 and out["findings"]
    text = r.stdout + r.stderr
    assert FAKE not in text and "q7Lm2Xc9Vb4Nz8Kp3Rt6Wy1" not in text
