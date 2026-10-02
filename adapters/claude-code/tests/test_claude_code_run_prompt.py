"""Tests for run-prompt.sh with a stand-in `claude` on PATH (no model is called).

Run: uv run --with pytest pytest adapters/claude-code/tests
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "run-prompt.sh"
FAKE = """#!/usr/bin/env bash
python3 - "$@" <<'PY'
import json, os, sys
json.dump({"args": sys.argv[1:], "mcp": os.environ.get("ENABLE_CLAUDEAI_MCP_SERVERS"),
           "budget": os.environ.get("SLASH_COMMAND_TOOL_CHAR_BUDGET")}, open(os.environ["FAKE_LOG"], "w"))
PY
echo '{"result": "done"}'
"""


@pytest.fixture
def env(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "claude").write_text(FAKE)
    (bin_dir / "claude").chmod(0o755)
    skill = tmp_path / "skills" / "demo"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("demo\n")
    (skill / "scripts" / "check.py").write_text("print(1)\n")
    dep = tmp_path / "skills" / "dep"
    dep.mkdir()
    (dep / "SKILL.md").write_text("dep\n")
    (tmp_path / "cwd").mkdir()
    (tmp_path / "prompt.md").write_text("hello\n")
    return {"tmp": tmp_path, "skill": skill, "dep": dep, "log": tmp_path / "log.json",
            "env": {"PATH": f"{bin_dir}:{os.environ['PATH']}", "HOME": str(tmp_path), "FAKE_LOG": str(tmp_path / "log.json"),
                    "WB_EVAL_CONTAINER": "1"}}


def run(e, *extra):
    t = e["tmp"]
    cmd = ["bash", str(SCRIPT), "--prompt-file", str(t / "prompt.md"), "--cwd", str(t / "cwd"), "--model", "m",
           "--out", str(t / "out"), *extra]
    return subprocess.run(cmd, capture_output=True, text=True, env=e["env"])


def test_the_adapter_installs_nothing_and_connectors_are_off(env):
    """The runner stages the skills before the adapter starts (scripts/stage_skills.py): the adapter runs the prompt."""
    r = run(env)
    assert r.returncode == 0, r.stderr
    assert list((env["tmp"] / "cwd").iterdir()) == []  # no skill folder, no shared folder: nothing was written
    log = json.loads(env["log"].read_text())
    assert "--strict-mcp-config" in log["args"] and log["mcp"] == "false"
    assert (env["tmp"] / "out" / "response.md").read_text() == "done"


@pytest.mark.parametrize("flag", ["--skill-dir", "--extra-skill-dir"])
def test_the_options_that_made_the_adapter_copy_a_skill_are_gone(env, flag):
    r = run(env, flag, str(env["skill"]))
    assert r.returncode == 2 and "unknown option" in r.stderr
    assert not env["log"].exists() and list((env["tmp"] / "cwd").iterdir()) == []


def test_a_skill_the_runner_staged_is_left_as_it_is(env):
    staged = env["tmp"] / "cwd" / ".claude" / "skills" / "demo"
    staged.mkdir(parents=True)
    (staged / "SKILL.md").write_text("staged by the runner\n")
    r = run(env)
    assert r.returncode == 0, r.stderr
    assert (staged / "SKILL.md").read_text() == "staged by the runner\n"
    assert sorted(p.name for p in (env["tmp"] / "cwd" / ".claude").iterdir()) == ["skills"]


def test_the_manifest_names_where_the_harness_finds_skills_and_what_carries_its_settings():
    manifest = json.loads((SCRIPT.parent / "adapter.json").read_text(encoding="utf-8"))
    assert manifest["eval"]["skills_dir"] == ".claude/skills"
    # Its settings folder, its server list and its project-instructions files: the runner refuses a case that carries one.
    assert set(manifest["eval"]["settings"]) == {".claude", ".mcp.json", "CLAUDE.md", "CLAUDE.local.md"}
    assert manifest["eval_runner"] == "run-prompt.sh" and manifest["runtime_runner"] == "run-agent.sh"
    assert (SCRIPT.parent / manifest["runtime_runner"]).is_file()
    assert set(manifest["consumes"]) == set(manifest["strategy"])  # nothing consumed without saying how


def test_max_cost_becomes_a_budget_and_bad_values_are_refused(env):
    r = run(env, "--max-cost-usd", "0.50")
    assert r.returncode == 0, r.stderr
    args = json.loads(env["log"].read_text())["args"]
    assert args[args.index("--max-budget-usd") + 1] == "0.50"
    assert run(env, "--max-cost-usd", "0.5; rm -rf x").returncode == 2


# --- stopping the adapter stops what the CLI started; HOME is left alone ---------------------------

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


def stand_in(e, body):
    cli = e["tmp"] / "bin" / "claude"
    cli.write_text("#!/usr/bin/env bash\n" + body)
    cli.chmod(0o755)


def test_what_the_cli_leaves_in_the_background_stops_when_it_returns(env):
    stand_in(env, f"sleep 300 &\necho $! > {env['tmp']}/child.pid\necho '{{\"result\": \"done\"}}'\n")
    r = run(env)
    assert r.returncode == 0, r.stderr
    assert (env["tmp"] / "out" / "response.md").read_text() == "done"
    assert gone(int((env["tmp"] / "child.pid").read_text()))


def test_a_stopped_adapter_stops_the_cli_and_its_children(env):
    import signal
    import time
    stand_in(env, f"sleep 300 &\necho $! > {env['tmp']}/child.pid\necho $$ > {env['tmp']}/cli.pid\nsleep 300\n")
    t = env["tmp"]
    proc = subprocess.Popen(["bash", str(SCRIPT), "--prompt-file", str(t / "prompt.md"), "--cwd", str(t / "cwd"),
                             "--model", "m", "--out", str(t / "out")], env=env["env"], start_new_session=True)
    end = time.monotonic() + 10
    while not ((t / "cli.pid").exists() and (t / "cli.pid").read_text().strip()) and time.monotonic() < end:
        time.sleep(0.05)
    child, cli = int((t / "child.pid").read_text()), int((t / "cli.pid").read_text())
    proc.send_signal(signal.SIGTERM)
    assert proc.wait(timeout=15) == 143
    assert gone(child) and gone(cli)


def test_inside_the_eval_container_every_tool_is_allowed_and_the_web_only_when_asked(env):
    r = run(env)
    assert r.returncode == 0, r.stderr
    args = json.loads(env["log"].read_text())["args"]
    assert "--dangerously-skip-permissions" in args and "--settings" not in args and "--allowedTools" not in args
    assert args[args.index("--disallowedTools") + 1] == "WebSearch,WebFetch"
    r = run(env, "--allow-web")
    assert r.returncode == 0, r.stderr
    assert "--disallowedTools" not in json.loads(env["log"].read_text())["args"]


def test_a_grading_call_gets_no_tool_at_all(env):
    """--no-tools: the grader holds the tier's credential and reads text a model wrote; it is given nothing to act with."""
    r = run(env, "--no-tools")
    assert r.returncode == 0, r.stderr
    args = json.loads(env["log"].read_text())["args"]
    assert args[args.index("--tools") + 1] == ""  # the CLI's way to disable every built-in tool
    assert "--dangerously-skip-permissions" not in args and "--disallowedTools" not in args and "--allowedTools" not in args
    assert "--strict-mcp-config" in args  # and no server's tools either
    assert (env["tmp"] / "out" / "response.md").read_text() == "done"
    env["log"].unlink()
    r = run(env, "--no-tools", "--allow-web")
    assert r.returncode == 2 and "do not go together" in r.stderr and not env["log"].exists()


def test_a_model_run_keeps_its_tools(env):
    r = run(env)
    assert r.returncode == 0, r.stderr
    assert "--tools" not in json.loads(env["log"].read_text())["args"]


def test_outside_the_eval_container_the_adapter_refuses_to_start(env):
    env["env"]["WB_EVAL_CONTAINER"] = ""
    r = run(env)
    assert r.returncode == 2 and "only inside the container" in r.stderr
    assert not env["log"].exists() and not (env["tmp"] / "out").exists()


def test_a_command_allowance_is_no_longer_an_option(env):
    assert run(env, "--allow-command", "git status").returncode == 2


def test_the_skill_listing_budget_is_raised_so_the_skill_keeps_its_description(env):
    r = run(env)
    assert r.returncode == 0, r.stderr
    assert int(json.loads(env["log"].read_text())["budget"]) >= 100000

