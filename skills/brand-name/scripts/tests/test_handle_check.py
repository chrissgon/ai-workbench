"""Tests for skills/brand-name/scripts/handle_check.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/brand-name/scripts/tests
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(rel: str, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / rel), *args], capture_output=True, text=True,
                          cwd=cwd, input=stdin, timeout=60)


HANDLE_CHECK = "skills/brand-name/scripts/handle_check.py"


def test_handle_check_refuses_bad_names_and_tlds_before_any_request():
    for args in (["--name", "../etc"], ["--name", "a b"], ["--name", "ok", "--tld", "d.e.v.x"], ["--name", "ok", "--today", "x"]):
        r = run(HANDLE_CHECK, *args)
        assert r.returncode == 2, (args, r.stdout)
        assert r.stdout == ""


def test_handle_check_domain_status_needs_the_control_domain(monkeypatch):
    hc = load(HANDLE_CHECK, "handle_check")
    answers = {"https://rdap.org/domain/google.io": (None, b""), "https://rdap.org/domain/me.io": (404, b""),
               "https://rdap.org/domain/google.dev": (200, b""), "https://rdap.org/domain/me.dev": (404, b"")}
    monkeypatch.setattr(hc, "http_status", lambda url: answers[url])
    assert hc.check_domain("me", "io")["status"] == "unknown"
    assert hc.check_domain("me", "dev")["status"] == "not_found"


def responses_file(tmp_path: Path, answers: dict) -> str:
    path = tmp_path / "responses.json"
    path.write_text(json.dumps({url: {"status": status} for url, status in answers.items()}), encoding="utf-8")
    return str(path)


def test_handle_check_reads_recorded_answers_and_sends_no_request(tmp_path, monkeypatch):
    answers = {"https://rdap.org/domain/google.dev": 200, "https://rdap.org/domain/quorvel.dev": 404,
               "https://rdap.org/domain/google.com": 200, "https://rdap.org/domain/quorvel.com": 200,
               "https://api.github.com/users/quorvel": 200, "https://registry.npmjs.org/-/user/quorvel/package": 404}
    r = run(HANDLE_CHECK, "--name", "quorvel", "--tld", "dev", "--tld", "com", "--tld", "io",
            "--responses", responses_file(tmp_path, answers), "--today", "2027-10-02")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    status = {row["check"]: row["status"] for row in out["checks"]}
    assert status == {"domain quorvel.dev": "not_found", "domain quorvel.com": "registered",
                      "domain quorvel.io": "unknown", "github quorvel": "registered", "npm quorvel": "not_found",
                      "devto quorvel": "unknown", "youtube quorvel": "unknown"}
    assert {row["checked_at"] for row in out["checks"]} == {"2027-10-02"}
    assert out["all_unknown"] is False
    assert out["check_by_hand"] == ["linkedin", "instagram", "x", "threads", "tiktok"]
    # In-process: with recorded answers the opener is never used.
    hc = load(HANDLE_CHECK, "handle_check_offline")
    monkeypatch.setattr(hc, "OPENER", None)
    monkeypatch.setattr(hc, "RESPONSES", {})
    assert hc.check_platform("quorvel", "github")["status"] == "unknown"


def test_handle_check_says_when_every_check_is_unknown(tmp_path):
    r = run(HANDLE_CHECK, "--name", "quorvel", "--responses", responses_file(tmp_path, {}))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["all_unknown"] is True and {row["status"] for row in out["checks"]} == {"unknown"}


def test_handle_check_refuses_a_responses_file_it_cannot_use(tmp_path):
    bad = tmp_path / "bad.json"
    for content in ("not json", "[1, 2]", '{"https://a.example/": {"status": "200"}}', '{"https://a.example/": 200}'):
        bad.write_text(content, encoding="utf-8")
        r = run(HANDLE_CHECK, "--name", "quorvel", "--responses", str(bad))
        assert r.returncode == 2 and r.stdout == "" and "Traceback" not in r.stderr, content
    r = run(HANDLE_CHECK, "--name", "quorvel", "--responses", str(tmp_path / "missing.json"))
    assert r.returncode == 2 and "cannot read --responses" in r.stderr
