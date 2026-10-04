"""Offline tests of the strong model's account-limit markers (adapters/claude-code/eval.json "account_limit"),
read by evals/eval_run.py account_limit(). The texts are what the pinned command-line tool left in a real run
that met the limit: its reply, and the result object of raw.json. No model is called."""
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "evals" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


er = load("eval_run")
MARKERS = er.adapter_eval("claude-code")["account_limit"]
# The reply of a run that met the 5-hour limit (a real run of 2026-09-29), and the start of its raw.json.
SESSION = "You've hit your session limit · resets 7:20pm (America/Sao_Paulo)"
RAW = '{"type":"result","subtype":"success","is_error":true,"api_error_status":429,"terminal_reason":"api_error"}'


def leave(tmp_path, name, text):
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    (out / name).write_text(text, encoding="utf-8")
    return str(out)


def test_the_reply_of_a_run_that_met_the_5_hour_limit_is_an_account_limit(tmp_path):
    assert er.account_limit(leave(tmp_path, "response.md", SESSION), MARKERS)


def test_the_weekly_limit_and_spent_credits_are_account_limits(tmp_path):
    for text in ("You've hit your weekly limit · resets Oct 9", "You're out of usage credits"):
        assert er.account_limit(leave(tmp_path, "response.md", text), MARKERS), text


def test_a_result_that_ended_on_a_429_is_an_account_limit_whatever_the_reply_says(tmp_path):
    out = leave(tmp_path, "response.md", "")
    leave(tmp_path, "raw.json", RAW)
    assert er.account_limit(out, MARKERS)


def test_an_ordinary_reply_and_result_are_not(tmp_path):
    out = leave(tmp_path, "response.md", "The plan is ready. A rate limit of the API is described in section 3.")
    leave(tmp_path, "raw.json", json.dumps({"type": "result", "is_error": False, "result": "ok"}, separators=(",", ":")))
    assert er.account_limit(out, MARKERS) is None
