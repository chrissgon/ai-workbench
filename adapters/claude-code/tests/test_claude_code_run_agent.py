"""Tests for run-agent.sh, the runtime contract of this adapter, with a stand-in `claude` on PATH (no model is
called). Each test runs under the `bash` on PATH and under /bin/bash when it is there (macOS ships bash 3.2, whose
empty arrays and `set -u` differ).

Run: uv run --with pytest pytest adapters/claude-code/tests
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "run-agent.sh"
FAKE = r"""#!/usr/bin/env bash
python3 - "$@" <<'PY'
import json, os, sys
args = sys.argv[1:]
prompt = args[args.index("--append-system-prompt") + 1]
skill_files = [line.split(": ", 1)[1] for line in prompt.splitlines() if line.startswith("- ") and ": " in line]
json.dump({"args": args, "cwd": os.getcwd(), "mcp": os.environ.get("ENABLE_CLAUDEAI_MCP_SERVERS"),
           "readable": {f: os.path.isfile(f) for f in skill_files}, "system_prompt": prompt},
          open(os.environ["FAKE_LOG"], "w"))
PY
case "${FAKE_MODE:-answer}" in
  hang)
    sleep 60 & echo $! > "$FAKE_CHILD"
    sleep 60 ;;
  leave)
    nohup sleep 60 >/dev/null 2>&1 & echo $! > "$FAKE_CHILD"
    echo '{"result": "done", "total_cost_usd": 0.01, "usage": {"input_tokens": 10, "output_tokens": 5}}' ;;
  *)
    echo '{"result": "done", "total_cost_usd": 0.01, "usage": {"input_tokens": 10, "output_tokens": 5}}' ;;
esac
"""
SHELLS = ["bash"] + (["/bin/bash"] if Path("/bin/bash").exists() else [])


@pytest.fixture(params=SHELLS)
def e(request, tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "claude").write_text(FAKE)
    (bin_dir / "claude").chmod(0o755)
    skill = tmp_path / "skills" / "demo"
    (skill / "scripts" / "tests").mkdir(parents=True)
    (skill / "evals").mkdir()
    (skill / "SKILL.md").write_text("demo\n")
    (skill / "scripts" / "check.py").write_text("print(1)\n")
    (skill / "scripts" / "tests" / "test_check.py").write_text("def test(): pass\n")
    (skill / "evals" / "evals.json").write_text("{}\n")
    project = tmp_path / "project"
    project.mkdir()
    agent = tmp_path / "agent.md"
    agent.write_text("---\nname: demo-agent\ndescription: x\n---\n# The agent\n")
    task = tmp_path / "task.md"
    task.write_text("Follow the skill demo.\n")
    # A PATH that holds the stand-in and the tools the script needs, never a real CLI the machine may have.
    tools = os.pathsep.join(dict.fromkeys(str(Path(shutil.which(t)).parent) for t in ("python3", "awk", "sed")))
    if shutil.which("claude", path=tools):
        pytest.skip("a real claude CLI sits next to python3; this test must not be able to reach it")
    env = {"PATH": f"{bin_dir}{os.pathsep}{tools}{os.pathsep}/usr/bin{os.pathsep}/bin", "HOME": str(tmp_path),
           "FAKE_LOG": str(tmp_path / "log.json"), "FAKE_CHILD": str(tmp_path / "child.pid")}
    assert shutil.which("claude", path=env["PATH"]) == str(bin_dir / "claude")
    return {"tmp": tmp_path, "skill": skill, "project": project, "agent": agent, "task": task, "env": env,
            "shell": request.param}


def run(e, *extra, env=None, skills=True):
    t = e["tmp"]
    cmd = [e["shell"], str(SCRIPT), "--agent-file", str(e["agent"]), "--task-file", str(e["task"]),
           "--project", str(e["project"]), "--model", "m", "--out", str(t / "out"),
           *(["--skill-dir", str(e["skill"])] if skills else []), *extra]
    return subprocess.run(cmd, capture_output=True, text=True, env={**e["env"], **(env or {})}, timeout=120)


def log(e) -> dict:
    return json.loads((e["tmp"] / "log.json").read_text())


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def gone_within(pid: int, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not alive(pid):
            return True
        time.sleep(0.1)
    return not alive(pid)


def test_the_skills_are_reachable_with_the_reading_tools_only(e):
    r = run(e)
    assert r.returncode == 0, r.stderr
    seen = log(e)
    args = seen["args"]
    assert args[args.index("--tools") + 1] == "Read,Glob,Grep"
    assert args[args.index("--add-dir") + 1] == str(e["project"].resolve())
    assert "--strict-mcp-config" in args and seen["mcp"] == "false"
    # The system prompt names the copied SKILL.md, and it is there, relative to the folder the CLI runs in.
    assert seen["readable"] == {".claude/skills/demo/SKILL.md": True}
    assert "# The agent" in seen["system_prompt"] and "name: demo-agent" not in seen["system_prompt"]
    copied = e["tmp"] / "out" / "cwd" / ".claude" / "skills" / "demo"
    assert (copied / "SKILL.md").is_file() and (copied / "scripts" / "check.py").is_file()
    assert not (copied / "evals").exists()
    assert not (copied / "scripts" / "tests").exists()  # adapters 2.2: the skill's script tests were copied in
    assert (e["tmp"] / "out" / "response.md").read_text() == "done"
    timing = json.loads((e["tmp"] / "out" / "timing.json").read_text())
    assert timing["exit_code"] == 0 and timing["cost_usd"] == 0.01 and timing["total_tokens"] == 15


def test_a_run_without_skills_names_none(e):
    r = run(e, skills=False)
    assert r.returncode == 0, r.stderr
    assert log(e)["readable"] == {} and "Skills of this run" not in log(e)["system_prompt"]


def test_the_timeout_stops_everything_the_cli_started(e):
    # The CLI was run with subprocess.run(timeout=...), which kills only the direct child: what it started went on.
    r = run(e, "--timeout-seconds", "2", env={"FAKE_MODE": "hang", "RUN_AGENT_TEST": "1"})
    assert r.returncode == 1
    timing = json.loads((e["tmp"] / "out" / "timing.json").read_text())
    assert timing["exit_code"] == 124
    assert "timeout after 2 s" in (e["tmp"] / "out" / "stderr.log").read_text()
    child = int((e["tmp"] / "child.pid").read_text())
    assert gone_within(child, 10), "a process the CLI started outlived the timeout"


def test_what_the_cli_leaves_running_ends_when_it_returns(e):
    r = run(e, env={"FAKE_MODE": "leave"})
    assert r.returncode == 0, r.stderr
    child = int((e["tmp"] / "child.pid").read_text())
    assert gone_within(child, 10), "a process the CLI left behind outlived the run"


def test_help_prints_the_header_only(e):
    r = subprocess.run([e["shell"], str(SCRIPT), "--help"], capture_output=True, text=True, env=e["env"], timeout=30)
    assert r.returncode == 0 and r.stdout.startswith("Runtime contract") and "set -euo" not in r.stdout
    assert "2 on usage errors." in r.stdout


def test_a_short_timeout_is_for_tests_only(e):
    r = run(e, "--timeout-seconds", "2")
    assert r.returncode == 2 and "30 to 3600" in r.stderr
    assert not (e["tmp"] / "out").exists()


def test_the_cli_must_be_on_the_path(e):
    shutil.rmtree(e["tmp"] / "bin")
    assert shutil.which("claude", path=e["env"]["PATH"]) is None
    r = run(e)
    assert r.returncode == 1 and "'claude' CLI not found" in r.stderr
