"""Offline tests of evals/executor.py: what a container is given, and nothing more. No docker is called.

Run: uv run --with pytest pytest evals/tests/test_executor.py
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "executor.py"
spec = importlib.util.spec_from_file_location("executor", SCRIPT)
ex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ex)


def run_folder(tmp_path):
    root = tmp_path / "eval-abc"
    (root / "case").mkdir(parents=True)
    (root / "out").mkdir()
    (root / "prompt.md").write_text("hello\n")
    skill = tmp_path / "skills" / "core-demo"
    skill.mkdir(parents=True)
    return root, skill


def mounted(argv):
    return [argv[i + 1] for i, a in enumerate(argv) if a == "-v"]


def test_the_definition_hash_follows_the_files_and_names_everything(tmp_path):
    (tmp_path / "proxy").mkdir()
    (tmp_path / "Dockerfile").write_text("FROM scratch\n")
    (tmp_path / "proxy" / "allow.txt").write_text("^model\\.example$\n")
    first = ex.definition_hash(str(tmp_path))
    assert first == ex.definition_hash(str(tmp_path)) and len(first) == 64
    (tmp_path / "proxy" / "allow.txt").write_text("^other\\.example$\n")
    second = ex.definition_hash(str(tmp_path))
    assert second != first
    n = ex.names(str(tmp_path))
    assert all(second[:12] in value for value in n.values()) and set(n) == {"image", "proxy_image", "network", "proxy"}


def test_a_command_sees_the_run_folder_the_adapters_and_the_skill_and_nothing_else(tmp_path):
    root, skill = run_folder(tmp_path)
    cmd = ["bash", os.path.join(ex.ROOT, "adapters", "demo", "run-prompt.sh"), "--prompt-file", str(root / "prompt.md"),
           "--cwd", str(root / "case"), "--out", str(root / "out"), "--skill-dir", str(skill), "--model", "m"]
    argv, name = ex.command(cmd, str(root), cwd=str(root), skills=[str(skill)], network="proxy")
    inside = argv[argv.index(ex.names()["image"]) + 1:]
    assert inside == ["bash", "/wb/adapters/demo/run-prompt.sh", "--prompt-file", "/eval/prompt.md", "--cwd", "/eval/case",
                      "--out", "/eval/out", "--skill-dir", "/skill/core-demo", "--model", "m"]
    targets = {m.split(":")[1]: m for m in mounted(argv)}
    assert set(targets) == {"/eval", "/wb/adapters", "/wb/shared", "/skill/core-demo"}
    assert not targets["/eval"].endswith(":ro") and all(targets[t].endswith(":ro") for t in targets if t != "/eval")
    home = os.path.realpath(os.path.expanduser("~"))
    assert all(m.split(":")[0] != home and not home.startswith(m.split(":")[0] + os.sep) for m in mounted(argv))
    assert argv[argv.index("-w") + 1] == "/eval" and name.startswith("wb-eval-run-") and name in argv
    assert "--rm" in argv and "--privileged" not in argv


def test_a_secret_travels_by_name_and_only_when_named(tmp_path):
    root, _ = run_folder(tmp_path)
    env = {"MODEL_KEY": "value-that-must-not-appear", "OTHER_KEY": "another-value", "GIT_ALLOW_PROTOCOL": "file"}
    argv, _ = ex.command(["true"], str(root), env=env, pass_names=["MODEL_KEY", "UNSET_KEY"], network="proxy")
    joined = " ".join(argv)
    assert "value-that-must-not-appear" not in joined and "another-value" not in joined
    assert ["-e", "MODEL_KEY"] in [argv[i:i + 2] for i in range(len(argv))]
    assert "OTHER_KEY" not in joined and "UNSET_KEY" not in joined
    assert "GIT_ALLOW_PROTOCOL=file" in argv


@pytest.mark.parametrize("network, expected", [("none", ["--network", "none"]), ("proxy", None), ("open", [])])
def test_network_is_none_the_proxied_internal_one_or_open(tmp_path, network, expected):
    root, _ = run_folder(tmp_path)
    argv, _ = ex.command(["true"], str(root), network=network)
    n = ex.names()
    if network == "none":
        assert argv[argv.index("--network") + 1] == "none" and not any("PROXY" in a.upper() for a in argv)
    elif network == "proxy":
        assert argv[argv.index("--network") + 1] == n["network"]
        assert f"HTTPS_PROXY=http://{n['proxy']}:{ex.PROXY_PORT}" in argv
    else:
        assert "--network" not in argv and not any("PROXY" in a.upper() for a in argv)


def test_an_unknown_network_is_refused(tmp_path):
    root, _ = run_folder(tmp_path)
    with pytest.raises(ex.ExecutorError):
        ex.command(["true"], str(root), network="host")


def test_only_the_model_providers_are_on_the_proxys_list():
    lines = [l for l in (Path(ex.DEFINITION) / "proxy" / "allow.txt").read_text().splitlines() if l.strip()]
    assert lines and all(l.startswith("^") and l.endswith("$") for l in lines)  # anchored: no partial match
    conf = (Path(ex.DEFINITION) / "proxy" / "tinyproxy.conf").read_text()
    assert "FilterDefaultDeny Yes" in conf and "ConnectPort 443" in conf
