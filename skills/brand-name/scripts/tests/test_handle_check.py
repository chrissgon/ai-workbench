"""Tests for skills/brand-name/scripts/handle_check.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/brand-name/scripts/tests
"""
from __future__ import annotations

import importlib.util
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
