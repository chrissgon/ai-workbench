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
        status, detail = doctor.check_provider("scheduler:job", impl)
        assert status == "missing" and "is not a provider" in detail, impl
    assert doctor.check_provider("../x:y", "launchd")[0] == "unknown"
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
    assert doctor.provider_folder("scheduler:job") == doctor.provider_folder("scheduler") == "scheduler"
    assert doctor.provider_folder("reader:email") == doctor.provider_folder("mailbox") == "mailbox"
    assert doctor.provider_folder("teleporter") is None and doctor.provider_folder("reader:rss") is None
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
    assert doctor.check_class("store:runtime") == ("provider", "sqlite (only-implementation): providers/store/sqlite.py")
    monkeypatch.setattr(doctor.sys, "platform", "linux")
    assert doctor.check_class("scheduler:job")[1] == "systemd (platform-default): providers/scheduler/systemd.py"
    monkeypatch.setenv("SCHEDULER_PROVIDER", "launchd")
    assert doctor.check_class("scheduler:job")[1] == "SCHEDULER_PROVIDER=launchd: providers/scheduler/launchd.py"
    assert [c[-2:] for c in ran] == [[str(Path(doctor.PROVIDERS) / rel), "--check"] for rel in
                                     ("store/sqlite.py", "scheduler/systemd.py", "scheduler/launchd.py")]
    # Nothing to choose, or a name that is not a shipped provider: missing, and nothing is run.
    status, detail = doctor.check_class("sender:email")
    assert status == "missing" and "MAILER_PROVIDER" in detail
    monkeypatch.setenv("SCHEDULER_PROVIDER", "../x")
    assert doctor.check_class("scheduler:job")[0] == "missing" and len(ran) == 3
    # A skill that still declares an old bare name is checked as the class it became, and told so.
    monkeypatch.delenv("SCHEDULER_PROVIDER")
    assert doctor.check_class("scheduler") == ("provider", "systemd (platform-default): providers/scheduler/systemd.py "
                                               "(declared as scheduler, the old name of scheduler:job)")


def run_recorder(monkeypatch, returncode=0):
    ran = []

    class Done:
        stdout, stderr = "{}", "not ready"
    Done.returncode = returncode
    monkeypatch.setattr(doctor.subprocess, "run", lambda cmd, **k: ran.append(cmd) or Done())
    for name in [n for n in list(doctor.os.environ) if n.endswith("_PROVIDER")]:
        monkeypatch.delenv(name)
    return ran


def test_a_class_with_a_parameter_is_checked_for_its_platform(monkeypatch):
    """RS2: the doctor ran the only publisher's --check for any platform and printed `provider`."""
    ran = run_recorder(monkeypatch)
    status, detail = doctor.check_class("publisher:linkedin")
    assert status == "provider" and ran[0][-3:] == ["--check", "--platform", "linkedin"]
    status, detail = doctor.check_class("publisher:a-platform-nobody-serves")
    assert status == "missing" and "serves a-platform-nobody-serves" in detail and len(ran) == 1
    # The placeholder form asks for no platform; a class with a fixed target passes none.
    assert doctor.check_class("publisher:<platform>")[0] == "provider" and ran[1][-1] == "--check"
    assert doctor.check_class("store:runtime")[0] == "provider" and ran[2][-1] == "--check"


def test_every_failing_check_is_missing_whatever_its_exit_code(monkeypatch):
    for code in (1, 2, 3):
        run_recorder(monkeypatch, returncode=code)
        status, detail = doctor.check_class("store:runtime")
        assert status == "missing" and f"--check exit {code}: not ready" in detail


def test_a_class_the_resolver_does_not_know_is_reported_as_unknown_without_a_traceback(monkeypatch, capsys):
    """RS3: secrets_report raised UnknownClass for a class the resolution function did not have."""
    run_recorder(monkeypatch)
    monkeypatch.setitem(sys.modules, "keyring", None)  # the secrets report never reaches the OS secret store here
    declared = {"teleporter": ["eng-demo"], "reader:rss": ["eng-demo"], "store:runtime": ["eng-demo"],
                "mailbox": ["mkt-demo"]}
    monkeypatch.setattr(doctor, "collect_requires", lambda: declared)
    assert doctor.check_class("teleporter")[0] == "unknown" and "unknown class" in doctor.check_class("teleporter")[1]
    rows = doctor.secrets_report(declared)  # no exception
    readers = {c for row in rows for c in row["classes"]}
    assert "teleporter" not in readers and "reader:rss" not in readers and "mailbox" in readers
    assert doctor.main(["--json"]) == 0
    report = doctor.json.loads(capsys.readouterr().out)
    assert {c: r["status"] for c, r in report["classes"].items()} == {
        "teleporter": "unknown", "reader:rss": "unknown", "store:runtime": "provider", "mailbox": "provider"}
    assert report["missing"] == 2
    assert doctor.main(["--strict"]) == 1
