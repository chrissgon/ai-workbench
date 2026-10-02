"""Tests for run-prompt.sh with RUN_PROMPT_CMD standing in for a runner (no model is called).

Run: uv run --with pytest pytest adapters/agents-dir/tests
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "run-prompt.sh"


@pytest.fixture
def case(tmp_path):
    skill = tmp_path / "skills" / "demo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("demo\n")
    (tmp_path / "cwd").mkdir()
    (tmp_path / "prompt.md").write_text("hello\n")
    return tmp_path


def run(t, model="m", *extra, cmd="cat {prompt_file}; echo {model}", **more):
    # WB_EVAL_CONTAINER: the adapter starts only inside the eval container, which sets it.
    env = {"PATH": os.environ["PATH"], "HOME": str(t), "RUN_PROMPT_CMD": cmd, "WB_EVAL_CONTAINER": "1", **more}
    return subprocess.run(["bash", str(SCRIPT), "--prompt-file", str(t / "prompt.md"), "--cwd", str(t / "cwd"),
                           "--model", model, "--out", str(t / "out"), *extra], capture_output=True, text=True, env=env)


def test_the_skill_is_copied_not_linked(case):
    r = run(case, "m", "--skill-dir", str(case / "skills" / "demo"), "--extra-skill-dir", str(case / "skills" / "demo"))
    assert r.returncode == 0, r.stderr
    dest = case / "cwd" / ".agents" / "skills" / "demo"
    assert dest.is_dir() and not dest.is_symlink()


def test_the_model_id_cannot_add_commands(case):
    r = run(case, "m; touch pwned")
    assert r.returncode == 0, r.stderr
    assert not (case / "cwd" / "pwned").exists()
    assert (case / "out" / "response.md").read_text() == "hello\nm; touch pwned\n"


@pytest.mark.parametrize("planted", [".agents/skills/x/SKILL.md", "opencode.json", "sub/.opencode/config"])
def test_a_case_folder_with_harness_settings_is_refused(case, planted):
    p = case / "cwd" / planted
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}")
    r = run(case, "m", "--skill-dir", str(case / "skills" / "demo"))
    assert r.returncode == 2 and "harness settings" in r.stderr


def test_shared_references_resolve_from_the_copied_skill(case):
    r = run(case, "m", "--skill-dir", str(case / "skills" / "demo"))
    assert r.returncode == 0, r.stderr
    skill = case / "cwd" / ".agents" / "skills" / "demo"
    assert (skill / ".." / ".." / "shared" / "references" / "security.md").is_file()
    assert not (case / "cwd" / ".agents" / "shared").is_symlink()


def test_the_skill_evals_are_not_copied(case):
    evals = case / "skills" / "demo" / "evals"
    evals.mkdir()
    (evals / "evals.json").write_text('{"assertions": ["the answer"]}\n')
    r = run(case, "m", "--skill-dir", str(case / "skills" / "demo"))
    assert r.returncode == 0, r.stderr
    dest = case / "cwd" / ".agents" / "skills" / "demo"
    assert (dest / "SKILL.md").is_file() and not (dest / "evals").exists()
    assert (evals / "evals.json").is_file()


def test_the_tests_of_the_skill_scripts_are_not_copied(case):
    scripts = case / "skills" / "demo" / "scripts"
    (scripts / "tests").mkdir(parents=True)
    (scripts / "check.py").write_text("print(1)\n")
    (scripts / "tests" / "test_x.py").write_text("def test_x():\n    assert True\n")
    r = run(case, "m", "--skill-dir", str(case / "skills" / "demo"))
    assert r.returncode == 0, r.stderr
    dest = case / "cwd" / ".agents" / "skills" / "demo"
    assert (dest / "scripts" / "check.py").is_file() and not (dest / "scripts" / "tests").exists()
    assert (scripts / "tests" / "test_x.py").is_file()


def test_max_cost_is_accepted_and_said_to_be_unenforced(case):
    r = run(case, "m", "--max-cost-usd", "0.50")
    assert r.returncode == 0, r.stderr
    assert "--max-cost-usd is not enforced" in r.stderr


def run_local(t, model, keep_home=False):
    """Run with a fake `opencode` on PATH that prints the configuration it was given."""
    bindir = t / "bin"
    bindir.mkdir(exist_ok=True)
    fake = bindir / "opencode"
    fake.write_text('#!/usr/bin/env bash\ncat "$XDG_CONFIG_HOME/opencode/opencode.json" 2>/dev/null || echo "no config"\n')
    fake.chmod(0o755)
    env = {"PATH": f"{bindir}:{os.environ['PATH']}", "HOME": str(t), "WB_EVAL_CONTAINER": "1"}
    if keep_home:
        env["RUN_PROMPT_KEEP_HOME"] = "1"
    return subprocess.run(["bash", str(SCRIPT), "--prompt-file", str(t / "prompt.md"), "--cwd", str(t / "cwd"),
                           "--model", model, "--out", str(t / "out")], capture_output=True, text=True, env=env)


def test_a_local_model_gets_its_provider_in_the_throwaway_home(case):
    import json
    r = run_local(case, "ollama/demo-model:27b")
    assert r.returncode == 0, r.stderr
    cfg = json.loads((case / "out" / "response.md").read_text())
    provider = cfg["provider"]["ollama"]
    assert provider["options"]["baseURL"] == "http://127.0.0.1:11434/v1"
    assert list(provider["models"]) == ["demo-model:27b"]
    assert not list((case / "cwd").rglob("opencode.json"))  # nothing is written into the case folder


def test_a_hosted_model_gets_no_local_provider(case):
    r = run_local(case, "vendor/some-model")
    assert r.returncode == 0 and "no config" in (case / "out" / "response.md").read_text()


@pytest.mark.parametrize("model", ["ollama/", "ollama/a b", 'ollama/x"; rm -rf ~', "ollama/$(id)"])
def test_a_malformed_local_model_id_is_refused(case, model):
    r = run_local(case, model)
    assert r.returncode == 2 and "local model id" in r.stderr


def test_a_local_model_needs_the_throwaway_home(case):
    r = run_local(case, "ollama/demo-model:27b", keep_home=True)
    assert r.returncode == 2 and "throwaway HOME" in r.stderr


def test_outside_the_eval_container_the_adapter_refuses_to_start(case):
    r = run(case, WB_EVAL_CONTAINER="")
    assert r.returncode == 2 and "only inside the container" in r.stderr
    assert not (case / "out").exists() and not (case / "cwd" / ".agents").exists()


# --- stopping the adapter stops what the runner started --------------------------------------------

def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def gone(pid, seconds=8):
    import time
    end = time.monotonic() + seconds
    while alive(pid) and time.monotonic() < end:
        time.sleep(0.1)
    return not alive(pid)


def wait_for(path, seconds=10):
    import time
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if path.exists() and path.read_text().strip():
            return path.read_text().strip()
        time.sleep(0.05)
    raise AssertionError(f"{path} was not written")


def test_what_the_runner_leaves_in_the_background_stops_when_it_returns(case):
    r = run(case, cmd="sleep 300 & echo $! > child.pid; echo done")
    assert r.returncode == 0, r.stderr
    assert (case / "out" / "response.md").read_text() == "done\n"
    assert gone(int((case / "cwd" / "child.pid").read_text()))


def test_a_stopped_adapter_stops_the_runner_and_its_children(case):
    import signal
    env = {"PATH": os.environ["PATH"], "HOME": str(case), "WB_EVAL_CONTAINER": "1",
           "RUN_PROMPT_CMD": "sleep 300 & echo $! > child.pid; echo $$ > runner.pid; sleep 300"}
    proc = subprocess.Popen(["bash", str(SCRIPT), "--prompt-file", str(case / "prompt.md"), "--cwd", str(case / "cwd"),
                             "--model", "m", "--out", str(case / "out")], env=env, start_new_session=True)
    child, runner = int(wait_for(case / "cwd" / "child.pid")), int(wait_for(case / "cwd" / "runner.pid"))
    proc.send_signal(signal.SIGTERM)
    assert proc.wait(timeout=15) == 143
    assert gone(child) and gone(runner)
