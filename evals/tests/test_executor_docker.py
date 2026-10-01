"""Tests of the eval container with a real docker daemon: what a run can and cannot reach. No model is called.

They build the images on first use (a few minutes) and are skipped unless WB_EVAL_DOCKER_TESTS=1:
  WB_EVAL_DOCKER_TESTS=1 uv run --with pytest pytest evals/tests/test_executor_docker.py
CI runs them in its own job, on Linux.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("WB_EVAL_DOCKER_TESTS") != "1", reason="set WB_EVAL_DOCKER_TESTS=1 (needs docker)")

SCRIPT = Path(__file__).resolve().parents[1] / "executor.py"
spec = importlib.util.spec_from_file_location("executor", SCRIPT)
ex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ex)
PROVIDER = "https://openrouter.ai/api/v1/models"  # public, needs no key; on the proxy's list
OTHER = "https://github.com"  # reachable from anywhere; not on the list


@pytest.fixture(scope="module")
def environment():
    return ex.ensure()


@pytest.fixture
def root(tmp_path):
    folder = tmp_path / "eval-run"
    (folder / "case").mkdir(parents=True)
    (folder / "out").mkdir()
    return folder


def inside(root, script, network="none", env=None, pass_names=()):
    # security-scan: allow shell-string -- every script is a literal of this test file, run inside the container
    argv, name = ex.command(["bash", "-c", script], str(root), cwd=str(root / "case"), env=env or {},
                            pass_names=pass_names, network=network)
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=180, env={**os.environ, **(env or {})})
    finally:
        ex.remove(name)


def code(url):
    return f"curl -s -m 15 -o /dev/null -w '%{{http_code}}' {url}"


def test_the_environment_names_the_definition_and_the_image(environment):
    assert environment["kind"] == "container" and environment["definition_sha256"] == ex.definition_hash()
    assert environment["image_id"].startswith("sha256:")


def test_a_run_writes_in_its_folder_and_the_caller_owns_the_result(environment, root):
    r = inside(root, "echo made > note.txt && mkdir -p docs && echo x > docs/a.md && id -u")
    assert r.returncode == 0, r.stderr
    note = root / "case" / "note.txt"
    assert note.read_text() == "made\n"
    note.unlink()  # the caller can change and remove what a run made
    (root / "case" / "docs" / "a.md").unlink()


def test_a_run_sees_no_home_no_checkout_and_cannot_change_the_adapters(environment, root):
    r = inside(root, "ls /wb; ls /skill 2>&1 | head -1; touch /wb/adapters/x 2>&1 | tail -1; "
                     "find / -xdev -name AGENTS.md -not -path '/proc/*' 2>/dev/null | head -1; echo WB=$WB_EVAL_CONTAINER")
    assert r.returncode == 0, r.stderr
    assert "adapters" in r.stdout and "shared" in r.stdout and "WB=1" in r.stdout
    assert "Read-only file system" in r.stdout and "AGENTS.md" not in r.stdout.replace("find", "")


def test_without_a_network_nothing_is_reached(environment, root):
    r = inside(root, code(PROVIDER) + "; echo; " + code(OTHER))
    assert r.stdout.split() == ["000", "000"]


def test_through_the_proxy_only_the_providers_are_reached(environment, root):
    r = inside(root, code(PROVIDER) + "; echo; " + code(OTHER) + "; echo; "
                     + code("--noproxy '*' " + OTHER) + "; echo; " + code("--noproxy '*' https://1.1.1.1"), network="proxy")
    provider, other, direct, address = r.stdout.split()
    assert provider == "200" and other == "000" and direct == "000" and address == "000"


def test_a_case_that_may_use_the_web_gets_the_open_network(environment, root):
    r = inside(root, code(OTHER), network="open")
    assert r.stdout.strip() in ("200", "301", "302")


def test_a_secret_reaches_the_run_by_name_and_only_when_passed(environment, root):
    env = {"DEMO_NAMED": "named-value", "DEMO_UNNAMED": "unnamed-value"}
    r = inside(root, 'echo "named=$DEMO_NAMED unnamed=$DEMO_UNNAMED"', env=env, pass_names=["DEMO_NAMED"])
    assert r.stdout.strip() == "named=named-value unnamed="


def test_the_image_carries_the_pinned_tools(environment, root):
    r = inside(root, "claude --version; opencode --version; uv --version; git --version; python3 --version; "
                     "node --version; chromium --version")
    assert r.returncode == 0, r.stderr
    assert "2.1.283" in r.stdout and "1.18.32" in r.stdout and "0.12.19" in r.stdout and "v24.10.0" in r.stdout


def test_removing_a_container_by_name_ends_it(environment, root):
    argv, name = ex.command(["sleep", "300"], str(root))
    proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            if ex.docker("ps", "-q", "--filter", f"name={name}").stdout.strip():
                break
            import time
            time.sleep(0.1)
        ex.remove(name)
        assert proc.wait(timeout=30) != 0
        assert not ex.docker("ps", "-aq", "--filter", f"name={name}").stdout.strip()
    finally:
        proc.kill()
