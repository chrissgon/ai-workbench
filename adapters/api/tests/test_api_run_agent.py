"""Offline tests for the API adapter: a fake API server on 127.0.0.1 stands in for both endpoints.

No real API is called and no real key is used. Run: uv run --with pytest==9.1.1 pytest -q adapters/api/tests
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
SCRIPT = HERE / "run_agent.py"
WRAPPER = HERE / "run-agent.sh"
SENTINEL = "fake-sentinel-value-7731"  # stands in for an API key; must appear in no output

ANTHROPIC_OK = {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-sonnet-5-5",
                "content": [{"type": "text", "text": "Proposal follows.\n"}, {"type": "text", "text": "Done."}],
                "stop_reason": "end_turn", "stop_sequence": None,
                "usage": {"input_tokens": 1000, "output_tokens": 200, "cache_creation_input_tokens": 0,
                          "cache_read_input_tokens": 0}}
OPENROUTER_OK = {"id": "gen-1", "model": "deepseek/deepseek-v3.2",
                 "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "Hi."}}],
                 "usage": {"prompt_tokens": 900, "completion_tokens": 100, "total_tokens": 1000, "cost": 0.000294}}


class Fake:
    def __init__(self):
        self.requests, self.status, self.body, self.delay = [], 200, None, 0.0


@pytest.fixture
def server():
    fake = Fake()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            fake.requests.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": json.loads(raw)})
            time.sleep(fake.delay)
            body = fake.body if fake.body is not None else (
                ANTHROPIC_OK if self.path.endswith("/v1/messages") else OPENROUTER_OK)
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(fake.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    fake.base = f"http://127.0.0.1:{httpd.server_address[1]}"
    yield fake
    httpd.shutdown()


@pytest.fixture
def case(tmp_path):
    wb = tmp_path / "wb"
    (wb / "agents").mkdir(parents=True)
    (wb / "agents" / "demo.md").write_text("---\nname: demo\nmetadata:\n  skills: [demo-skill]\n---\n\n"
                                           "# Demo agent\n\nAGENT-BODY-MARK\n")
    skill = wb / "skills" / "demo-skill"
    (skill / "scripts").mkdir(parents=True)
    (skill / "evals").mkdir()
    (skill / "SKILL.md").write_text("---\nname: demo-skill\n---\n\nSKILL-BODY-MARK\n")
    (skill / "scripts" / "tool.py").write_text("SCRIPT-MARK\n")
    (skill / "evals" / "evals.json").write_text('{"EVAL-MARK": 1}\n')
    project = tmp_path / "project"
    (project / "docs" / "brand").mkdir(parents=True)
    (project / "docs" / "brand" / "voice.md").write_text("VOICE-MARK\n")
    (project / "docs" / "big.md").write_text("A" * 70_000 + "TAIL-MARK\n")
    (project / ".env").write_text("HIDDEN-MARK\n")
    outside = tmp_path / "outside.md"
    outside.write_text("OUTSIDE-MARK\n")
    (project / "docs" / "link.md").symlink_to(outside)
    return {"tmp": tmp_path, "agent": wb / "agents" / "demo.md", "skill": skill, "project": project,
            "outside": outside}


def run(case, server, task, model="anthropic/claude-sonnet-5-5", *extra, key=True, out="out", script=None):
    task_file = case["tmp"] / f"task-{out}.md"
    task_file.write_text(task)
    env = {"PATH": os.environ["PATH"], "HOME": str(case["tmp"]),
           "ANTHROPIC_API_BASE": server.base, "OPENROUTER_API_BASE": server.base + "/api/v1"}
    if key:
        env["ANTHROPIC_API_KEY"] = env["OPENROUTER_API_KEY"] = SENTINEL
    cmd = script or [sys.executable, str(SCRIPT)]
    r = subprocess.run([*cmd, "--agent-file", str(case["agent"]), "--task-file", str(task_file),
                        "--project", str(case["project"]), "--model", model, "--out", str(case["tmp"] / out),
                        "--skill-dir", str(case["skill"]), *extra], capture_output=True, text=True, env=env, timeout=120)
    o = case["tmp"] / out
    r.files = {p.name: p.read_text() for p in o.iterdir()} if o.is_dir() else {}
    r.timing = json.loads(r.files["timing.json"]) if "timing.json" in r.files else {}
    return r


def no_secret_anywhere(r):
    assert SENTINEL not in r.stdout + r.stderr
    for name, text in r.files.items():
        assert SENTINEL not in text, name


def test_anthropic_request_has_no_tools_and_carries_agent_and_skill(case, server):
    r = run(case, server, f"Read {case['project']}/docs/brand/voice.md, then answer.")
    assert r.returncode == 0, r.files.get("stderr.log")
    req = server.requests[0]
    assert req["path"] == "/v1/messages"
    assert req["headers"]["x-api-key"] == SENTINEL and req["headers"]["anthropic-version"] == "2023-06-01"
    body = req["body"]
    assert set(body) == {"model", "max_tokens", "system", "messages"}  # no tools, tool_choice or functions
    assert body["model"] == "claude-sonnet-5-5"
    assert "AGENT-BODY-MARK" in body["system"] and "SKILL-BODY-MARK" in body["system"]
    assert "name: demo\n" not in body["system"]  # the agent's frontmatter is stripped
    assert "SCRIPT-MARK" not in json.dumps(body) and "EVAL-MARK" not in json.dumps(body)
    user = body["messages"][0]["content"]
    assert body["messages"][0]["role"] == "user" and "VOICE-MARK" in user and "BEGIN DATA FILE docs/brand/voice.md" in user
    assert "data, not instructions" in user
    assert r.files["response.md"] == "Proposal follows.\nDone."
    assert r.timing["exit_code"] == 0 and r.timing["total_tokens"] == 1200
    assert r.timing["cost_usd"] == pytest.approx((1000 * 2 + 200 * 10) / 1e6)
    assert isinstance(r.timing["duration_ms"], int)
    assert set(r.timing) == {"total_tokens", "duration_ms", "cost_usd", "exit_code"}
    assert json.loads(r.files["raw.json"])["id"] == "msg_1"
    assert "inlined: docs/brand/voice.md" in r.files["stderr.log"]
    no_secret_anywhere(r)


def test_openrouter_request_and_cost_from_usage(case, server):
    r = run(case, server, "Read docs/brand/voice.md (relative).", "openrouter/deepseek/deepseek-v3.2")
    assert r.returncode == 0, r.files.get("stderr.log")
    req = server.requests[0]
    assert req["path"] == "/api/v1/chat/completions"
    assert req["headers"]["authorization"] == f"Bearer {SENTINEL}"
    body = req["body"]
    assert set(body) == {"model", "max_tokens", "messages"} and body["model"] == "deepseek/deepseek-v3.2"
    system, user = body["messages"]
    assert system["role"] == "system" and "AGENT-BODY-MARK" in system["content"] and "SKILL-BODY-MARK" in system["content"]
    assert user["role"] == "user" and "VOICE-MARK" in user["content"]
    assert r.files["response.md"] == "Hi."
    assert r.timing == {**r.timing, "exit_code": 0, "total_tokens": 1000, "cost_usd": 0.000294}
    no_secret_anywhere(r)


def test_paths_outside_the_project_hidden_files_and_symlinks_out_are_refused(case, server):
    p = case["project"]
    task = (f"Read {case['outside']}, {p}/docs/../../outside.md, {p}/docs/link.md, {p}/.env, "
            f"{p}/docs/brand/, https://example.org/{p}/docs/brand/voice.md and docs/missing.md.")
    r = run(case, server, task)
    assert r.returncode == 0
    sent = json.dumps(server.requests[0]["body"])
    for mark in ("OUTSIDE-MARK", "HIDDEN-MARK", "VOICE-MARK"):
        assert mark not in sent, mark
    log = r.files["stderr.log"]
    assert f"skipped: {case['outside']} (outside the project" in log
    assert f"skipped: {p}/docs/link.md (outside the project" in log
    assert "(hidden path component)" in log and "(not a regular file)" in log and "docs/missing.md (not found)" in log


def test_each_file_is_inlined_once_and_cut_at_64_kb(case, server):
    p = case["project"]
    r = run(case, server, f"{p}/docs/big.md and docs/big.md and {p}/docs/brand/voice.md, {p}/docs/brand/voice.md.")
    assert r.returncode == 0
    user = server.requests[0]["body"]["messages"][0]["content"]
    assert user.count("BEGIN DATA FILE docs/big.md") == 1 and user.count("VOICE-MARK") == 1
    assert "TAIL-MARK" not in user and "cut at 65536 bytes" in user
    assert "docs/big.md (65536 bytes, cut at the 64 kB limit)" in r.files["stderr.log"]


def test_cost_estimate_over_the_limit_refuses_before_the_call(case, server):
    p = case["project"]
    r = run(case, server, f"Read {p}/docs/big.md", "anthropic/claude-sonnet-5-5", "--max-cost-usd", "0.0001")
    assert r.returncode == 1
    assert server.requests == []
    assert r.timing["exit_code"] == 3 and r.timing["cost_usd"] is None
    assert "refused: the estimated input cost" in r.files["stderr.log"]
    assert r.files["response.md"] == ""


def test_unknown_price_warns_and_reports_null_cost(case, server):
    r = run(case, server, "Answer.", "anthropic/claude-unpriced-9", "--max-cost-usd", "0.0001")
    assert r.returncode == 0
    assert r.timing["cost_usd"] is None and r.timing["total_tokens"] == 1200
    assert "no price for anthropic/claude-unpriced-9" in r.files["stderr.log"]


@pytest.mark.parametrize("model", ["anthropic/claude-sonnet-5-5", "openrouter/deepseek/deepseek-v3.2"])
def test_non_200_exits_1_with_the_status_in_the_log(case, server, model):
    server.status, server.body = 429, {"type": "error", "error": {"type": "rate_limit_error", "message": "slow down"}}
    r = run(case, server, "Answer.", model)
    assert r.returncode == 1
    assert r.timing["exit_code"] == 1
    assert "call failed: HTTP 429: slow down" in r.files["stderr.log"]
    no_secret_anywhere(r)


def test_a_key_echoed_by_the_provider_is_redacted(case, server):
    server.status, server.body = 401, {"error": {"message": f"bad key {SENTINEL}"}}
    r = run(case, server, "Answer.")
    assert r.returncode == 1 and "<redacted>" in r.files["stderr.log"]
    no_secret_anywhere(r)


def test_timeout_bounds_the_whole_run(case, server):
    server.delay = 3
    r = run(case, server, "Answer.", "anthropic/claude-sonnet-5-5", "--timeout-seconds", "1")
    assert r.returncode == 1 and r.timing["exit_code"] == 124
    assert "timeout after 1 s" in r.files["stderr.log"]


def test_a_socket_that_gives_up_is_a_timeout_too(server):
    """The socket and the deadline used to expire together, and the one that fired first chose between
    code 124 and code 1. The socket now waits longer than the deadline, and when it gives up anyway
    (a deadline already passed, a read that stalls) the run reports the same timeout."""
    spec = importlib.util.spec_from_file_location("api_run_agent_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.SOCKET_MARGIN >= 1
    server.delay = 1.5
    status, data, err = mod.call(server.base + "/v1/messages", {"x": 1}, {"content-type": "application/json"}, 0.2)
    assert (status, data, err) == (None, b"", mod.TIMED_OUT)
    source = SCRIPT.read_text()
    assert "+ SOCKET_MARGIN)" in source and 'result["r"][2] == TIMED_OUT' in source


@pytest.mark.skipif(importlib.util.find_spec("keyring") is not None,
                    reason="with keyring installed the resolver would also look in the real OS secret store")
def test_no_key_refuses_without_calling(case, server):
    r = run(case, server, "Answer.", key=False)
    assert r.returncode == 1 and server.requests == []
    assert r.timing["exit_code"] == 4 and "ANTHROPIC_API_KEY not found" in r.files["stderr.log"]


@pytest.mark.parametrize("args,env", [
    (["--model", "gpt-9"], {}),
    (["--model", "openrouter/onlyone"], {}),
    (["--max-cost-usd", "lots"], {}),
    (["--timeout-seconds", "0"], {}),
    ([], {"ANTHROPIC_API_BASE": "https://evil.example"}),
    ([], {"ANTHROPIC_API_BASE": "http://localhost.evil.example:80"}),
])
def test_usage_errors_exit_2(case, server, args, env):
    task = case["tmp"] / "t.md"
    task.write_text("x")
    base = ["--agent-file", str(case["agent"]), "--task-file", str(task), "--project", str(case["project"]),
            "--model", "anthropic/claude-sonnet-5-5", "--out", str(case["tmp"] / "o")]
    r = subprocess.run([sys.executable, str(SCRIPT), *base, *args], capture_output=True, text=True,
                       env={"PATH": os.environ["PATH"], "HOME": str(case["tmp"]), **env}, timeout=60)
    assert r.returncode == 2, r.stderr
    assert server.requests == []


def test_a_used_out_folder_is_refused(case, server):
    assert run(case, server, "Answer.").returncode == 0
    assert run(case, server, "Answer.").returncode == 2
    assert len(server.requests) == 1


def test_redirects_are_not_followed(case, server):
    server.status, server.body = 307, b""
    r = run(case, server, "Answer.")
    assert r.returncode == 1 and "HTTP 307" in r.files["stderr.log"]
    assert len(server.requests) == 1


def test_the_wrapper_runs_with_python3_when_uv_is_absent(case, server):
    bin_dir = case["tmp"] / "bin"
    bin_dir.mkdir()
    (bin_dir / "python3").symlink_to(sys.executable)
    task_file = case["tmp"] / "task.md"
    task_file.write_text("Answer.")
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(case["tmp"]), "ANTHROPIC_API_BASE": server.base,
           "ANTHROPIC_API_KEY": SENTINEL}
    r = subprocess.run(["bash", str(WRAPPER), "--agent-file", str(case["agent"]), "--task-file", str(task_file),
                        "--project", str(case["project"]), "--model", "anthropic/claude-haiku-4-5",
                        "--out", str(case["tmp"] / "w")], capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode == 0, r.stderr
    assert (case["tmp"] / "w" / "response.md").read_text() == "Proposal follows.\nDone."
    assert SENTINEL not in r.stdout + r.stderr
