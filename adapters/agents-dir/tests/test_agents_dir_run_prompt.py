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


def run(t, model="m", *extra, cmd="cat {prompt_file}; echo {model}"):
    env = {"PATH": os.environ["PATH"], "HOME": str(t), "RUN_PROMPT_CMD": cmd}
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
    env = {"PATH": f"{bindir}:{os.environ['PATH']}", "HOME": str(t)}
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
