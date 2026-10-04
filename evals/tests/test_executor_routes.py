"""Offline tests of the two key proxy routes of evals/executor.py: the floor model's key and the strong model's
credential are each held by a key proxy of their own, on networks of their own. No docker is called, and every key
is a fake one.

Run: uv run --with pytest pytest evals/tests/test_executor_routes.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "executor.py"
spec = importlib.util.spec_from_file_location("executor_routes", SCRIPT)
ex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ex)

FOLDER = Path(__file__).resolve().parents[1] / "container" / "keyproxy"
_spec = importlib.util.spec_from_file_location("keyproxy_routes", FOLDER / "keyproxy.py")
kp = importlib.util.module_from_spec(_spec)
_writes = sys.dont_write_bytecode
sys.dont_write_bytecode = True  # a cache folder in evals/container/ would change the definition's hash
try:
    _spec.loader.exec_module(kp)
finally:
    sys.dont_write_bytecode = _writes

STRONG = "CLAUDE_CODE_OAUTH_TOKEN"
FLOOR = "OPENROUTER_API_KEY"
STRONG_KEY = "fake-strong-token-for-the-route-tests-0006"
FLOOR_KEY = "fake-floor-key-for-the-route-tests-0007"


def run_folder(tmp_path):
    root = tmp_path / "eval-abc"
    (root / "case").mkdir(parents=True)
    (root / "out").mkdir()
    (root / "prompt.md").write_text("hello\n")
    return root


def env_pairs(argv):
    return [argv[i + 1] for i, a in enumerate(argv) if a == "-e"]


def tag():
    return ex.names()["image"].split(":", 1)[1]


def test_a_strong_run_on_the_proxy_network_gets_a_placeholder_and_its_own_proxy_and_never_the_value(tmp_path):
    root = run_folder(tmp_path)
    argv, _ = ex.command(["true"], str(root), env={STRONG: STRONG_KEY}, pass_names=[STRONG], network="proxy")
    given = env_pairs(argv)
    assert f"{STRONG}=held-by-the-eval-key-proxy" in given and STRONG not in given
    assert f"ANTHROPIC_BASE_URL=http://wb-eval-keys-strong-{tag()}:8891" in given
    assert argv[argv.index("--network") + 1] == f"wb-eval-strong-{tag()}"
    assert f"NO_PROXY=localhost,127.0.0.1,wb-eval-keys-strong-{tag()}" in given
    assert STRONG_KEY not in " ".join(argv)


def test_a_strong_run_on_the_open_network_joins_the_strong_open_network(tmp_path):
    root = run_folder(tmp_path)
    argv, _ = ex.command(["true"], str(root), env={STRONG: STRONG_KEY}, pass_names=[STRONG], network="open")
    assert argv[argv.index("--network") + 1] == f"wb-eval-strong-open-{tag()}"
    assert f"{STRONG}=held-by-the-eval-key-proxy" in env_pairs(argv) and STRONG_KEY not in " ".join(argv)


@pytest.mark.parametrize("network", ["proxy", "open", "none"])
def test_a_floor_run_is_built_as_before(tmp_path, network):
    """The arguments test_executor.py's floor test expects, in full: the floor path does not change."""
    root = run_folder(tmp_path)
    n = ex.names()
    argv, _ = ex.command(["true"], str(root), env={FLOOR: FLOOR_KEY, "MODEL_KEY": "v"}, pass_names=[FLOOR, "MODEL_KEY"],
                         network=network)
    tail = argv[argv.index(f"{FLOOR}=held-by-the-eval-key-proxy") - 1:]
    expected = ["-e", f"{FLOOR}=held-by-the-eval-key-proxy", "-e", "MODEL_KEY"]
    if network == "none":
        expected += ["--network", "none"]
    else:
        expected += ["-e", f"OPENROUTER_BASE_URL=http://{n['keys']}:8890/api/v1"]
        if network == "proxy":
            proxy = f"http://{n['proxy']}:{ex.PROXY_PORT}"
            expected += ["--network", n["network"]]
            for key in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
                expected += ["-e", f"{key}={proxy}"]
            direct = f"localhost,127.0.0.1,{n['keys']}"
            expected += ["-e", f"NO_PROXY={direct}", "-e", f"no_proxy={direct}"]
        else:
            expected += ["--network", n["open_network"]]
    assert tail == expected + [n["image"], "true"]
    assert FLOOR_KEY not in " ".join(argv)


def test_a_command_passed_both_keys_is_refused(tmp_path):
    root = run_folder(tmp_path)
    with pytest.raises(ex.ExecutorError):
        ex.command(["true"], str(root), env={STRONG: STRONG_KEY, FLOOR: FLOOR_KEY}, pass_names=[STRONG, FLOOR], network="proxy")


def test_held_route_names_no_proxy_without_a_network_or_without_a_value():
    assert ex.held_route([STRONG], {STRONG: STRONG_KEY}, "none") is None
    assert ex.held_route([FLOOR], {FLOOR: FLOOR_KEY}, "none") is None
    assert ex.held_route([STRONG], {STRONG: ""}, "proxy") is None
    assert ex.held_route([STRONG], {}, "proxy") is None
    assert ex.held_route([STRONG], {STRONG: STRONG_KEY}, "proxy") == "strong"
    assert ex.held_route([FLOOR], {FLOOR: FLOOR_KEY}, "open") == "floor"


def test_the_strong_proxy_url_has_no_path_and_the_floor_one_keeps_its_prefix():
    strong, floor = ex.keyproxy_url(name="strong"), ex.keyproxy_url()
    assert strong.endswith(":8891") and strong == f"http://wb-eval-keys-strong-{tag()}:8891"
    assert floor.endswith(":8890/api/v1")


class FakeDocker:
    """docker as the key proxy's start sees it, for the strong route."""

    def __init__(self):
        self.calls, self.envs = [], []

    def __call__(self, *args, env=None, check=True, timeout=1800):
        import subprocess
        self.calls.append(args)
        self.envs.append(dict(env or {}))
        out, err, code = "", "", 0
        if args[0] == "inspect":
            code, err = 1, "No such object"
        elif args[0] == "logs":
            err = "keyproxy: listening on port 8891, forwarding /v1/ to https://api.anthropic.com through the egress proxy\n"
        return subprocess.CompletedProcess(["docker", *args], code, out, err)


def test_the_strong_key_proxy_starts_on_its_own_networks_with_its_own_route(monkeypatch):
    n = ex.names()
    docker = FakeDocker()
    monkeypatch.setattr(ex, "docker", docker)
    assert ex.keyproxy(env={STRONG: STRONG_KEY, "PATH": "/usr/bin"}, name="strong") == n["keys_strong"]
    run = next(c for c in docker.calls if c[0] == "run")
    assert all(STRONG_KEY not in a for c in docker.calls for a in c)
    assert docker.envs[docker.calls.index(run)][STRONG] == STRONG_KEY
    assert run[run.index("--network") + 1] == n["strong_network"] and run[run.index("--name") + 1] == n["keys_strong"]
    assert run[run.index(n["keys_image"]) + 1:] == ("--route", "/etc/keyproxy/keyproxy-strong.json")
    assert ("network", "connect", n["strong_open_network"], n["keys_strong"]) in docker.calls


def test_the_strong_route_is_valid_and_a_bad_base_path_is_refused(tmp_path):
    route = kp.load_route(str(FOLDER / "keyproxy-strong.json"))
    assert route["secret"] == STRONG and route["base_path"] == "" and route["prefix"] == "/v1/"
    bad = {**json.loads((FOLDER / "keyproxy-strong.json").read_text()), "base_path": "v1"}
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    with pytest.raises(kp.RouteError):
        kp.load_route(str(tmp_path / "bad.json"))
