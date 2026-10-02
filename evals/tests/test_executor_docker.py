"""Tests of the eval container with a real docker daemon: what a run can and cannot reach. No model is called.

They build the images on first use (a few minutes) and are skipped unless WB_EVAL_DOCKER_TESTS=1:
  WB_EVAL_DOCKER_TESTS=1 uv run --with pytest pytest evals/tests/test_executor_docker.py
CI runs them in its own job, on Linux.

The image is built for the platform evidence is made on (executor.IMAGE_PLATFORM). On a machine of another
architecture, such as the CI job's, these tests build and run it for that machine's own architecture
instead (WB_EVAL_IMAGE_PLATFORM, set below): they test the definition, and no evidence comes from them.
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
spec = importlib.util.spec_from_file_location("eval_run_docker", SCRIPT.parent / "eval_run.py")
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)
REPO = SCRIPT.parents[1]
if os.environ.get("WB_EVAL_DOCKER_TESTS") == "1" and not os.environ.get(ex.PLATFORM_ENV):
    try:
        native = subprocess.run(["docker", "version", "--format", "{{.Server.Os}}/{{.Server.Arch}}"],
                                capture_output=True, text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        native = ""
    if native and native != ex.IMAGE_PLATFORM:
        os.environ[ex.PLATFORM_ENV] = native  # no emulation: the definition is what is under test here
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


def inside(root, script, network="none", env=None, pass_names=(), runner=None):
    # security-scan: allow shell-string -- every script is a literal of this test file, run inside the container
    argv, name = ex.command(["bash", "-c", script], str(root), cwd=str(root / "case"), env=env or {},
                            pass_names=pass_names, network=network, runner=runner)
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=180, env={**os.environ, **(env or {})})
    finally:
        ex.remove(name)


def code(url):
    return f"curl -s -m 15 -o /dev/null -w '%{{http_code}}' {url}"


def test_the_environment_names_the_definition_the_image_its_digest_and_its_platform(environment, root):
    assert environment["kind"] == "container" and environment["definition_sha256"] == ex.definition_hash()
    assert environment["image_id"].startswith("sha256:") and environment["image_digest"] == environment["image_id"]
    assert environment["image_platform"] == ex.image_platform()
    machine = {"linux/arm64": "aarch64", "linux/amd64": "x86_64"}[ex.image_platform()]
    assert inside(root, "uname -m").stdout.strip() == machine


def test_a_run_writes_in_its_folder_and_the_caller_owns_the_result(environment, root):
    r = inside(root, "echo made > note.txt && mkdir -p docs && echo x > docs/a.md && id -u")
    assert r.returncode == 0, r.stderr
    note = root / "case" / "note.txt"
    assert note.read_text() == "made\n"
    note.unlink()  # the caller can change and remove what a run made
    (root / "case" / "docs" / "a.md").unlink()


@pytest.mark.parametrize("harness", ["claude-code", "agents-dir"])
def test_a_run_sees_its_folder_and_the_one_adapter_script_and_nothing_else_of_the_workbench(environment, root, harness):
    runner = REPO / "adapters" / harness / "run-prompt.sh"
    r = inside(root, "find /wb | sort; echo --; ls -d /skill /wb/adapters /wb/shared 2>&1 | grep -c 'No such file'; "
                     "echo x >> /wb/run-prompt.sh 2>&1 | tail -1; head -c 19 /wb/run-prompt.sh; echo; "
                     "find / -xdev \\( -name AGENTS.md -o -name adapter.json -o -name SKILL.md -o -name README.md -path '*adapters*' \\) "
                     "-not -path '/proc/*' -not -path '/opt/runners/*' -not -path '/usr/*' 2>/dev/null | head -3; echo WB=$WB_EVAL_CONTAINER",
               runner=str(runner))
    assert r.returncode == 0, r.stderr
    listing, rest = r.stdout.split("--\n", 1)
    assert listing.split() == ["/wb", "/wb/run-prompt.sh"]  # the one file: not its folder, its README, its tests
    lines = rest.splitlines()
    assert lines[0] == "3"  # no /skill, no /wb/adapters, no /wb/shared
    assert "Read-only file system" in (r.stdout + r.stderr) and "#!/usr/bin/env bash" in rest
    assert lines[-1] == "WB=1" and not [l for l in lines if l.startswith("/")]  # no instruction file, manifest or skill anywhere
    r = inside(root, "ls /wb 2>&1 | grep -c 'No such file'")  # a setup command or the fixture commit: not even the script
    assert r.stdout.strip() == "1"


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
                     "node --version; chromium --version; gh --version; file --version; patch --version")
    assert r.returncode == 0, r.stderr
    assert "2.1.283" in r.stdout and "1.18.32" in r.stdout and "0.12.19" in r.stdout and "v24.10.0" in r.stdout
    assert "gh version 2.102.0" in r.stdout and "GNU patch" in r.stdout and "magic file from" in r.stdout
    lock = (Path(ex.DEFINITION) / "runners" / "package-lock.json").read_text()
    assert '"version": "2.1.283"' in lock and '"version": "1.18.32"' in lock  # the lock file is what was installed


def test_the_code_hosts_tool_is_installed_and_signed_out(environment, root):
    r = inside(root, "gh auth status; echo status=$?; env | grep -c -i -E '^(GH|GITHUB)_' ; ls -A ~/.config 2>/dev/null | wc -l")
    out = (r.stdout + r.stderr).lower()
    assert "status=1" in out and "not logged in" in out, out
    assert r.stdout.split()[-2:] == ["0", "0"]  # no token variable, no stored configuration


def test_the_clock_the_locale_and_the_user_are_the_images_own(environment, root):
    host = {"TZ": "America/Sao_Paulo", "LANG": "pt_BR.UTF-8", "USER": "someone"}
    r = inside(root, 'echo "$TZ|$LANG|$USER|$PYTHONDONTWRITEBYTECODE|${DEBIAN_FRONTEND:-unset}|$(date +%Z)"; '
                     "python3 -c 'import locale, sys; print(sys.stdout.encoding, locale.getpreferredencoding())'", env=host)
    assert r.returncode == 0, r.stderr
    lines = r.stdout.strip().splitlines()
    assert lines[0] == "UTC|C.UTF-8|eval|1|unset|UTC"
    assert lines[1].lower().replace("-", "") == "utf8 utf8"


def test_python_leaves_no_bytecode_in_the_case_folder(environment, root):
    r = inside(root, "printf 'X = 1\\n' > mod.py && python3 -c 'import mod; print(mod.X)' && find . -name '*.pyc' -o -name __pycache__ | wc -l")
    assert r.returncode == 0 and r.stdout.split() == ["1", "0"], r.stdout + r.stderr


def test_a_run_has_one_identity_for_its_commits_the_images(environment, root):
    host = {"GIT_AUTHOR_NAME": "someone", "GIT_AUTHOR_EMAIL": "s@host.example", "GIT_COMMITTER_NAME": "someone",
            "GIT_COMMITTER_EMAIL": "s@host.example", "GIT_ALLOW_PROTOCOL": "file"}
    r = inside(root, "git init -q . && echo x > f && git add f && git commit -q -m one && git log -1 --format='%an <%ae> / %cn <%ce>' "
                     "&& git branch --show-current && echo protocol=$GIT_ALLOW_PROTOCOL", env=host)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == ["Eval <eval@example.invalid> / Eval <eval@example.invalid>", "main", "protocol=file"]


def test_the_floor_runners_scratch_folder_can_be_written_by_the_run(environment, root):
    r = inside(root, "mkdir -p /tmp/opencode/work && echo ok > /tmp/opencode/work/pairs.json && cat /tmp/opencode/work/pairs.json "
                     "&& stat -c %a /tmp/opencode")
    assert r.returncode == 0 and r.stdout.split() == ["ok", "1777"], r.stdout + r.stderr


def test_a_run_holds_no_capability_cannot_gain_one_and_has_a_process_limit(environment, root):
    r = inside(root, "grep -E '^(CapEff|CapPrm|CapBnd|NoNewPrivs):' /proc/self/status; cat /sys/fs/cgroup/pids.max 2>/dev/null")
    assert r.returncode == 0, r.stderr
    status = dict(line.split(":") for line in r.stdout.splitlines() if ":" in line)
    assert int(status["CapEff"], 16) == 0 and int(status["CapPrm"], 16) == 0 and int(status["CapBnd"], 16) == 0
    assert status["NoNewPrivs"].strip() == "1"
    limits = [line for line in r.stdout.splitlines() if ":" not in line and line.strip()]
    assert limits == [str(ex.PIDS_LIMIT)]  # the cgroup's own limit, as the container sees it
    # The tools a run uses still work without them: a commit, a script, the browser.
    r = inside(root, "git init -q . && python3 -c 'print(1)' && chromium --headless --no-sandbox --disable-gpu --dump-dom about:blank 2>/dev/null | head -c 6")
    assert r.returncode == 0 and r.stdout.split()[0] == "1" and "<html" in r.stdout, r.stdout + r.stderr


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


def demo_workbench(tmp_path):
    """A small workbench: a skill under test that cites one shared reference, and a dependency skill."""
    wb = tmp_path / "wb"
    skill, dep = wb / "skills" / "core-demo", wb / "skills" / "core-dep"
    for folder in (skill / "evals", skill / "scripts" / "tests", dep / "evals", wb / "shared" / "references", wb / "shared" / "scripts"):
        folder.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# demo\nWalk ../../shared/references/security.md.\n")
    (skill / "evals" / "evals.json").write_text('{"expected_output": "the answer"}')
    (skill / "scripts" / "check.py").write_text("print(1)\n")
    (skill / "scripts" / "tests" / "test_check.py").write_text("def test_x():\n    assert True\n")
    (dep / "SKILL.md").write_text("# dep\n")
    (dep / "evals" / "evals.json").write_text('{"expected_output": "another answer"}')
    for name in ("security.md", "other.md"):
        (wb / "shared" / "references" / name).write_text(name + "\n")
    (wb / "shared" / "scripts" / "tool.py").write_text("print(1)\n")
    return wb, skill, dep


def test_a_run_reads_the_staged_skill_and_never_its_cases_its_tests_or_an_uncited_reference(environment, root, tmp_path, monkeypatch):
    """What the runner stages (eval_run.stage_run, as a real run calls it) is all a container holds of a skill."""
    wb, skill, dep = demo_workbench(tmp_path)
    monkeypatch.setattr(er, "ROOT", str(wb))
    staged, manifest = er.stage_run(str(root / "case"), {"skills_dir": ".tool/skills", "settings": [".tool"]}, str(skill), [str(dep)], {"id": 1})
    assert sorted(staged) == [".tool/shared", ".tool/skills/core-demo", ".tool/skills/core-dep"]
    r = inside(root, "cat .tool/skills/core-demo/SKILL.md | head -1; cat .tool/skills/core-demo/../../shared/references/security.md; "
                     "find / -xdev \\( -name evals.json -o -name 'test_check.py' -o -name other.md -o -name tool.py \\) "
                     "-not -path '/proc/*' -not -path '/usr/*' -not -path '/opt/*' 2>/dev/null | wc -l; find /eval -type l | wc -l")
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["#", "demo", "security.md", "0", "0"]

