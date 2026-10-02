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


def test_integration_class_maps_to_its_service_folder(monkeypatch):
    assert doctor.provider_folder("integration:vcs") == "vcs"
    assert doctor.provider_folder("publisher:linkedin") == "publisher"
    assert doctor.provider_folder("scheduler") == "scheduler"
    assert "github" in doctor.known_providers(doctor.provider_folder("integration:vcs"))
    for name in [n for n in list(doctor.os.environ) if n.endswith("_PROVIDER")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("INTEGRATION_PROVIDER", "github")
    assert doctor.env_provider("integration:vcs") == (None, None)  # no shared fallback across services
    monkeypatch.setenv("INTEGRATION_VCS_PROVIDER", "github")
    assert doctor.env_provider("integration:vcs") == ("INTEGRATION_VCS_PROVIDER", "github")
    monkeypatch.setenv("INTEGRATION_ISSUE_TRACKER_PROVIDER", "jira")
    assert doctor.env_provider("integration:issue-tracker") == ("INTEGRATION_ISSUE_TRACKER_PROVIDER", "jira")
    monkeypatch.setenv("PUBLISHER_PROVIDER", "linkedin")
    assert doctor.env_provider("publisher:linkedin") == ("PUBLISHER_PROVIDER", "linkedin")


def test_vcs_provider_runs_its_check(monkeypatch):
    ran = []

    class Done:
        returncode, stdout, stderr = 0, "{}", ""

    monkeypatch.setattr(doctor.subprocess, "run", lambda cmd, **k: ran.append(cmd) or Done())
    status, detail = doctor.check_provider("integration:vcs", "github")
    assert status == "provider" and detail == "providers/vcs/github.py"
    assert ran[0][-2:] == [str(Path(doctor.PROVIDERS) / "vcs" / "github.py"), "--check"]
    assert doctor.check_provider("integration:vcs", "gitlab")[0] == "missing"


def test_a_class_is_checked_through_the_resolution_function(monkeypatch):
    ran = []

    class Done:
        returncode, stdout, stderr = 0, "{}", ""

    monkeypatch.setattr(doctor.subprocess, "run", lambda cmd, **k: ran.append(cmd) or Done())
    for name in [n for n in list(doctor.os.environ) if n.endswith("_PROVIDER")]:
        monkeypatch.delenv(name)
    # No variable is set: the only store provider resolves, and the scheduler follows the platform.
    assert doctor.check_class("store") == ("provider", "sqlite (only-implementation): providers/store/sqlite.py")
    monkeypatch.setattr(doctor.sys, "platform", "linux")
    assert doctor.check_class("scheduler")[1] == "systemd (platform-default): providers/scheduler/systemd.py"
    monkeypatch.setenv("SCHEDULER_PROVIDER", "launchd")
    assert doctor.check_class("scheduler")[1] == "SCHEDULER_PROVIDER=launchd: providers/scheduler/launchd.py"
    assert [c[-2:] for c in ran] == [[str(Path(doctor.PROVIDERS) / rel), "--check"] for rel in
                                     ("store/sqlite.py", "scheduler/systemd.py", "scheduler/launchd.py")]
    # Nothing to choose, or a name that is not a shipped provider: missing, and nothing is run.
    status, detail = doctor.check_class("mailer")
    assert status == "missing" and "MAILER_PROVIDER" in detail
    monkeypatch.setenv("SCHEDULER_PROVIDER", "../x")
    assert doctor.check_class("scheduler")[0] == "missing" and len(ran) == 3
