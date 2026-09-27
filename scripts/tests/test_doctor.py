"""Tests for scripts/doctor.py: a provider name from the environment is validated before it runs.

Run: uv run --with pytest pytest scripts/tests
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "doctor.py"
spec = importlib.util.spec_from_file_location("doctor", SCRIPT)
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)


def test_unknown_or_path_like_provider_is_not_run(monkeypatch):
    ran = []
    monkeypatch.setattr(doctor.subprocess, "run", lambda *a, **k: ran.append(a))
    for impl in ("../../tmp/x", "/tmp/x", "auth", "LAUNCHD", "nope", ""):
        status, detail = doctor.check_provider("scheduler:local", impl)
        assert status == "missing" and "is not a provider" in detail, impl
    assert doctor.check_provider("../x:y", "launchd")[0] == "missing"
    assert ran == []


def test_known_providers_exclude_helpers():
    assert "linkedin" in doctor.known_providers("publisher")
    assert "auth" not in doctor.known_providers("publisher")
    assert doctor.known_providers("..") == []


def test_harness_name_is_validated():
    r = subprocess.run([sys.executable, str(SCRIPT), "--harness", "../providers"], capture_output=True, text=True)
    assert r.returncode == 2
