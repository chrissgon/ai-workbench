"""Offline tests of providers/resolve.py: a requirement class resolves to one provider script.

They live here because scripts/test_dirs.py discovers providers/<class>/tests, not a tests folder directly
under providers/. Every workbench below is a temporary folder with empty provider files; nothing is run.

Run: uv run --with pytest pytest scripts/tests/test_provider_resolve.py
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "providers" / "resolve.py"
spec = importlib.util.spec_from_file_location("workbench_provider_resolve_under_test", SCRIPT)
resolve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolve)


def workbench(tmp_path, *files):
    root = tmp_path / "wb"
    for rel in files:
        path = root / "providers" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    (root / "providers").mkdir(parents=True, exist_ok=True)
    return root


def cli(args, env=None):
    base = {"PATH": "/usr/bin:/bin"}
    return subprocess.run([sys.executable, str(SCRIPT), *args], env={**base, **(env or {})},
                          capture_output=True, text=True, timeout=30)


def test_class_maps_to_its_folder_and_variables():
    assert resolve.folder("scheduler") == "scheduler"
    assert resolve.folder("publisher:linkedin") == "publisher"
    assert resolve.folder("integration:vcs") == "vcs"
    assert resolve.folder("integration:issue-tracker") == "issue-tracker"
    assert resolve.variables("publisher:linkedin") == ["PUBLISHER_LINKEDIN_PROVIDER", "PUBLISHER_PROVIDER"]
    assert resolve.variables("publisher:<platform>") == ["PUBLISHER_PROVIDER"]  # a placeholder means "any"
    assert resolve.variables("scheduler") == ["SCHEDULER_PROVIDER"]
    assert resolve.variables("integration:vcs") == ["INTEGRATION_VCS_PROVIDER"]  # no shared fallback
    assert resolve.variables("integration:issue-tracker") == ["INTEGRATION_ISSUE_TRACKER_PROVIDER"]


@pytest.mark.parametrize("cls", ["nope", "../x:y", "integration", "publisher:Linked In", "a:b:c", "", "scheduler/../x"])
def test_unknown_class_is_refused(cls):
    with pytest.raises(resolve.UnknownClass):
        resolve.resolve(cls, env={})


def test_environment_wins_most_specific_first(tmp_path):
    root = workbench(tmp_path, "publisher/linkedin.py", "publisher/buffer.py", "publisher/auth.py")
    env = {"PUBLISHER_PROVIDER": "linkedin", "PUBLISHER_LINKEDIN_PROVIDER": "buffer"}
    got = resolve.resolve("publisher:linkedin", root=root, env=env)
    assert (got["implementation"], got["source"], got["variable"]) == ("buffer", "environment", "PUBLISHER_LINKEDIN_PROVIDER")
    assert got["path"] == str(root.resolve() / "providers" / "publisher" / "buffer.py")
    got = resolve.resolve("publisher:x", root=root, env=env)
    assert (got["implementation"], got["variable"]) == ("linkedin", "PUBLISHER_PROVIDER")
    assert resolve.implementations("publisher:linkedin", root=root) == ["buffer", "linkedin"]  # auth.py is a helper


def test_scheduler_default_follows_the_platform(tmp_path):
    root = workbench(tmp_path, "scheduler/launchd.py", "scheduler/systemd.py")
    for platform, name in (("darwin", "launchd"), ("linux", "systemd")):
        got = resolve.resolve("scheduler", root=root, env={}, platform=platform)
        assert (got["implementation"], got["source"]) == (name, "platform-default")
    got = resolve.resolve("scheduler", root=root, env={"SCHEDULER_PROVIDER": "launchd"}, platform="linux")
    assert (got["implementation"], got["source"]) == ("launchd", "environment")
    with pytest.raises(resolve.Unresolved) as e:
        resolve.resolve("scheduler", root=root, env={}, platform="win32")
    assert "SCHEDULER_PROVIDER" in str(e.value) and "launchd" in str(e.value)


def test_the_only_implementation_resolves_and_none_or_several_do_not(tmp_path):
    root = workbench(tmp_path, "store/sqlite.py", "vcs/github.py", "vcs/gitlab.py", "scheduler/launchd.py")
    got = resolve.resolve("store", root=root, env={})
    assert (got["implementation"], got["source"]) == ("sqlite", "only-implementation")
    # A platform default that is not shipped is not chosen; the only implementation is.
    assert resolve.resolve("scheduler", root=root, env={}, platform="linux")["implementation"] == "launchd"
    with pytest.raises(resolve.Unresolved) as e:
        resolve.resolve("integration:vcs", root=root, env={})
    assert "INTEGRATION_VCS_PROVIDER" in str(e.value)
    with pytest.raises(resolve.Unresolved) as e:
        resolve.resolve("mailer", root=root, env={})
    assert "MAILER_PROVIDER" in str(e.value)


def test_a_name_is_never_a_path(tmp_path):
    root = workbench(tmp_path, "scheduler/launchd.py", "publisher/linkedin.py", "publisher/auth.py")
    for bad in ("../../tmp/x", "/tmp/x", "auth", "LAUNCHD", "nope", "launchd.py", ""):
        with pytest.raises(resolve.Unresolved):
            resolve.resolve("scheduler", root=root, env={}, implementation=bad)
        if bad:
            with pytest.raises(resolve.Unresolved):
                resolve.resolve("publisher:linkedin", root=root, env={"PUBLISHER_PROVIDER": bad})


def test_an_explicit_implementation_wins_over_the_environment(tmp_path):
    root = workbench(tmp_path, "scheduler/launchd.py", "scheduler/systemd.py")
    got = resolve.resolve("scheduler", root=root, env={"SCHEDULER_PROVIDER": "systemd"}, platform="linux",
                          implementation="launchd")
    assert (got["implementation"], got["source"]) == ("launchd", "configuration")


def test_workbench_root_comes_from_the_variable_then_from_the_script(tmp_path):
    root = workbench(tmp_path, "store/sqlite.py")
    assert resolve.workbench_root(env={}) == REPO
    assert resolve.workbench_root(env={"WORKBENCH_ROOT": str(root)}) == root.resolve()
    assert resolve.workbench_root(root=tmp_path, env={"WORKBENCH_ROOT": str(root)}) == tmp_path.resolve()
    with pytest.raises(resolve.Unresolved):
        resolve.workbench_root(env={"WORKBENCH_ROOT": "relative/path"})
    assert resolve.secret_resolver(env={}) == REPO / "providers" / "secrets" / "resolver.py"
    assert resolve.provider_path("store", env={"WORKBENCH_ROOT": str(root)}) == root.resolve() / "providers/store/sqlite.py"


def test_cli_prints_the_path_and_uses_the_documented_exit_codes(tmp_path):
    root = workbench(tmp_path, "store/sqlite.py", "scheduler/launchd.py", "scheduler/systemd.py")
    env = {"WORKBENCH_ROOT": str(root), "SCHEDULER_PROVIDER": "systemd"}
    r = cli(["--class", "scheduler"], env)
    assert r.returncode == 0 and r.stdout.strip() == str(root.resolve() / "providers" / "scheduler" / "systemd.py")
    r = cli(["--class", "store", "--json"], env)
    assert r.returncode == 0 and json.loads(r.stdout)["implementation"] == "sqlite"
    r = cli(["--class", "mailbox"], env)
    assert r.returncode == 3 and r.stdout == "" and "MAILBOX_PROVIDER" in r.stderr
    r = cli(["--class", "scheduler"], {**env, "SCHEDULER_PROVIDER": "cron"})
    assert r.returncode == 3 and "SCHEDULER_PROVIDER" in r.stderr and "cron" in r.stderr
    r = cli(["--class", "teleporter"], env)
    assert r.returncode == 2 and "unknown class" in r.stderr
    assert cli([], env).returncode == 2 and cli(["--class", "store", "--list"], env).returncode == 2
    assert cli(["--help"]).returncode == 0
    r = cli(["--class", "store", "--root", str(REPO)], env)  # --root beats the variable
    assert r.stdout.strip() == str(REPO / "providers" / "store" / "sqlite.py")


def test_cli_list_names_every_class_and_what_resolves(tmp_path):
    root = workbench(tmp_path, "store/sqlite.py", "vcs/github.py", "vcs/gitlab.py")
    r = cli(["--list"], {"WORKBENCH_ROOT": str(root)})
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["root"] == str(root.resolve()) and out["root_variable"] == "WORKBENCH_ROOT"
    rows = {row["class"]: row for row in out["classes"]}
    assert set(rows) == set(resolve.LISTED)
    assert rows["store"]["resolves"] == "sqlite" and rows["store"]["source"] == "only-implementation"
    assert rows["integration:vcs"]["implementations"] == ["github", "gitlab"]
    assert rows["integration:vcs"]["resolves"] is None and "INTEGRATION_VCS_PROVIDER" in rows["integration:vcs"]["note"]
    assert rows["mailer"]["implementations"] == []


def test_this_checkout_resolves_what_it_ships():
    env = {}
    assert resolve.resolve("store", env=env)["implementation"] == "sqlite"
    assert resolve.resolve("mailbox", env=env)["implementation"] == "gmail"
    assert resolve.resolve("publisher:linkedin", env=env)["implementation"] == "linkedin"
    assert resolve.resolve("integration:vcs", env=env)["implementation"] == "github"
    assert resolve.resolve("scheduler", env=env, platform="darwin")["implementation"] == "launchd"
    assert resolve.resolve("scheduler", env=env, platform="linux")["implementation"] == "systemd"
    for cls in resolve.LISTED:  # every listed class is a class
        resolve.variables(cls)


def test_every_class_of_the_environment_contract_is_listed():
    text = (REPO / "contracts" / "environment.md").read_text(encoding="utf-8")
    table = text.split("## Classes", 1)[1].split("\n## ", 1)[0]
    classes = [line.split("|")[1].strip().strip("`") for line in table.splitlines()
               if line.startswith("| `")]
    assert classes and sorted(classes) == sorted(resolve.LISTED)
