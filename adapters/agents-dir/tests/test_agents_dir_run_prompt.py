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
    # RUN_PROMPT_OS: these tests never call the real `security`; the keychain tests below use a stand-in.
    env = {"PATH": os.environ["PATH"], "HOME": str(t), "RUN_PROMPT_CMD": cmd, "RUN_PROMPT_OS": "Linux", **more}
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


# --- macOS: the throwaway HOME gets its own keychain ----------------------------------------------

def fake_security(t, exit_code=0):
    """A stand-in for /usr/bin/security that records its arguments and the HOME it was given."""
    path = t / "fake-security"
    path.write_text(f'''#!/usr/bin/env bash
printf '%s\\t%s\\n' "$HOME" "$*" >> "{t}/security.log"
exit {exit_code}
''')
    path.chmod(0o755)
    return {"RUN_PROMPT_OS": "Darwin", "RUN_PROMPT_SECURITY": str(path)}


def security_calls(t):
    log = t / "security.log"
    return [line.split("\t") for line in log.read_text().splitlines()] if log.exists() else []


def test_on_macos_the_throwaway_home_gets_an_empty_default_keychain(case):
    r = run(case, cmd='echo "$HOME" > home.txt; ls "$HOME/Library"', **fake_security(case))
    assert r.returncode == 0, r.stderr
    home = (case / "cwd" / "home.txt").read_text().strip()
    calls = security_calls(case)
    keychain = f"{home}/Library/Keychains/login.keychain-db"
    assert [args for _, args in calls] == [
        f"create-keychain -p  {keychain}", f"default-keychain -s {keychain}", f"list-keychains -d user -s {keychain}",
        f"set-keychain-settings {keychain}"]
    # Every call ran with the throwaway home, never the caller's, and never on the system domain.
    assert {h for h, _ in calls} == {home} and home != str(case) and home != os.environ.get("HOME")
    assert not any("system" in args for _, args in calls)
    assert (case / "out" / "response.md").read_text().split() == ["Keychains", "Preferences"]
    assert not Path(home).exists()  # the keychain goes with the throwaway home


def test_no_keychain_when_the_real_home_is_kept_or_off_macos(case):
    r = run(case, RUN_PROMPT_KEEP_HOME="1", **fake_security(case))
    assert r.returncode == 0, r.stderr
    r = run(case, **{**fake_security(case), "RUN_PROMPT_OS": "Linux"})
    assert r.returncode == 0, r.stderr
    r = run(case, **{**fake_security(case), "RUN_PROMPT_SECURITY": str(case / "missing")})
    assert r.returncode == 0, r.stderr
    assert security_calls(case) == []


def test_a_keychain_failure_is_one_note_and_the_run_goes_on(case):
    r = run(case, **fake_security(case, exit_code=1))
    assert r.returncode == 0 and (case / "out" / "response.md").read_text() == "hello\nm\n"
    notes = [line for line in r.stderr.splitlines() if "keychain" in line]
    assert len(notes) == 1 and notes[0].startswith("note: the keychain of the throwaway HOME is incomplete")
    for step in ("create-keychain", "default-keychain", "list-keychains", "set-keychain-settings"):
        assert f" {step} (" in notes[0]
    assert len(security_calls(case)) == 4  # a failed step does not stop the later ones


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
    env = {"PATH": os.environ["PATH"], "HOME": str(case), "RUN_PROMPT_OS": "Linux",
           "RUN_PROMPT_CMD": "sleep 300 & echo $! > child.pid; echo $$ > runner.pid; sleep 300"}
    proc = subprocess.Popen(["bash", str(SCRIPT), "--prompt-file", str(case / "prompt.md"), "--cwd", str(case / "cwd"),
                             "--model", "m", "--out", str(case / "out")], env=env, start_new_session=True)
    child, runner = int(wait_for(case / "cwd" / "child.pid")), int(wait_for(case / "cwd" / "runner.pid"))
    proc.send_signal(signal.SIGTERM)
    assert proc.wait(timeout=15) == 143
    assert gone(child) and gone(runner)
