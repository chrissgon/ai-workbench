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
json.dump({"args": sys.argv[1:], "mcp": os.environ.get("ENABLE_CLAUDEAI_MCP_SERVERS")}, open(os.environ["FAKE_LOG"], "w"))
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
            "env": {"PATH": f"{bin_dir}:{os.environ['PATH']}", "HOME": str(tmp_path), "FAKE_LOG": str(tmp_path / "log.json")}}


def run(e, *extra):
    t = e["tmp"]
    cmd = ["bash", str(SCRIPT), "--prompt-file", str(t / "prompt.md"), "--cwd", str(t / "cwd"), "--model", "m",
           "--out", str(t / "out"), *extra]
    return subprocess.run(cmd, capture_output=True, text=True, env=e["env"])


def test_skills_are_copied_not_linked_and_connectors_are_off(env):
    r = run(env, "--skill-dir", str(env["skill"]), "--extra-skill-dir", str(env["dep"]), "--allow-command", "npm test")
    assert r.returncode == 0, r.stderr
    for name in ("demo", "dep"):
        dest = env["tmp"] / "cwd" / ".claude" / "skills" / name
        assert dest.is_dir() and not dest.is_symlink()
    (env["tmp"] / "cwd" / ".claude" / "skills" / "demo" / "SKILL.md").write_text("edited\n")
    assert (env["skill"] / "SKILL.md").read_text() == "demo\n"
    log = json.loads(env["log"].read_text())
    assert "--strict-mcp-config" in log["args"] and log["mcp"] == "false"
    assert "Bash(npm test *)" in log["args"][log["args"].index("--allowedTools") + 1]
    assert (env["tmp"] / "out" / "response.md").read_text() == "done"


@pytest.mark.parametrize("prefix", ["npm test)", "git status,Bash(rm", "npm *"])
def test_prefixes_that_add_rules_are_refused(env, prefix):
    r = run(env, "--allow-command", prefix)
    assert r.returncode == 2
    assert not env["log"].exists()


@pytest.mark.parametrize("planted", [".claude/settings.json", "sub/.claude/settings.local.json", ".mcp.json"])
def test_a_case_folder_with_harness_settings_is_refused(env, planted):
    p = env["tmp"] / "cwd" / planted
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}")
    r = run(env, "--skill-dir", str(env["skill"]))
    assert r.returncode == 2 and "harness settings" in r.stderr
    assert not env["log"].exists()


def test_shared_references_resolve_from_the_copied_skill(env):
    r = run(env, "--skill-dir", str(env["skill"]))
    assert r.returncode == 0, r.stderr
    skill = env["tmp"] / "cwd" / ".claude" / "skills" / "demo"
    assert (skill / ".." / ".." / "shared" / "references" / "security.md").is_file()
    assert not (env["tmp"] / "cwd" / ".claude" / "shared").is_symlink()


def test_the_skill_evals_are_not_copied(env):
    evals = env["skill"] / "evals"
    evals.mkdir()
    (evals / "evals.json").write_text('{"assertions": ["the answer"]}\n')
    r = run(env, "--skill-dir", str(env["skill"]))
    assert r.returncode == 0, r.stderr
    dest = env["tmp"] / "cwd" / ".claude" / "skills" / "demo"
    assert (dest / "SKILL.md").is_file() and not (dest / "evals").exists()
    assert (evals / "evals.json").is_file()


def test_max_cost_becomes_a_budget_and_bad_values_are_refused(env):
    r = run(env, "--max-cost-usd", "0.50")
    assert r.returncode == 0, r.stderr
    args = json.loads(env["log"].read_text())["args"]
    assert args[args.index("--max-budget-usd") + 1] == "0.50"
    assert run(env, "--max-cost-usd", "0.5; rm -rf x").returncode == 2


def test_skill_scripts_are_allowed_by_relative_and_absolute_path(env):
    r = run(env, "--skill-dir", str(env["skill"]))
    assert r.returncode == 0, r.stderr
    log = json.loads(env["log"].read_text())
    rules = log["args"][log["args"].index("--allowedTools") + 1]
    cwd = env["tmp"] / "cwd"
    assert "Bash(python3 .claude/skills/demo/scripts/check.py *)" in rules
    assert f"Bash(python3 {cwd}/.claude/skills/demo/scripts/check.py *)" in rules


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


def test_the_cli_keeps_the_callers_home_and_no_keychain_tool_is_called(env):
    security = env["tmp"] / "bin" / "security"
    security.write_text(f"#!/usr/bin/env bash\necho called >> {env['tmp']}/security.log\n")
    security.chmod(0o755)
    stand_in(env, f"echo \"$HOME\" > {env['tmp']}/home.txt\necho '{{\"result\": \"done\"}}'\n")
    r = run(env)
    assert r.returncode == 0, r.stderr
    assert (env["tmp"] / "home.txt").read_text().strip() == str(env["tmp"])
    assert not (env["tmp"] / "security.log").exists()


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
