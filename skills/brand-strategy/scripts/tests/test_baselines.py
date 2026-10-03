"""Tests for skills/brand-strategy/scripts/baselines.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/brand-strategy/scripts/tests
"""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


def run(rel: str, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / rel), *args], capture_output=True, text=True,
                          cwd=cwd, input=stdin, timeout=60)


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BASELINES = "skills/brand-strategy/scripts/baselines.py"
WEEK = "https://api.npmjs.org/downloads/point/last-week/kvlite-example"
MONTH = "https://api.npmjs.org/downloads/point/last-month/kvlite-example"
REPO = "https://api.github.com/repos/ada-example/kvlite"
GONE = "https://api.github.com/repos/ada-example/gone"


def test_baselines_refuses_names_that_are_not_package_or_repo_names():
    for args in (["--npm", "../../etc"], ["--github", "owner"], ["--github", "a/b?x=1"], ["--npm", "x", "--today", "yesterday"], []):
        r = run(BASELINES, *args)
        assert r.returncode == 2, (args, r.stdout, r.stderr)
        assert r.stdout == ""


def test_baselines_reads_recorded_answers_and_tells_not_found_from_not_measured(tmp_path):
    answers = {
        WEEK: {"status": 200, "body": {"downloads": 120, "start": "2027-09-01", "end": "2027-09-07"}},
        MONTH: {"status": 200, "body": {"downloads": 480, "start": "2027-08-09", "end": "2027-09-07"}},
        GONE: {"status": 404},
        REPO: {"status": None},
    }
    path = tmp_path / "responses.json"
    path.write_text(json.dumps(answers), encoding="utf-8")
    r = run(BASELINES, "--npm", "kvlite-example", "--github", "ada-example/kvlite", "--github", "ada-example/gone",
            "--responses", str(path), "--today", "2027-09-08")
    assert r.returncode == 1, r.stderr
    out = json.loads(r.stdout)
    assert [(m["metric"], m["value"], m["period"], m["accessed"]) for m in out["measurements"]] == [
        ("npm downloads (last-week)", 120, "2027-09-01 to 2027-09-07", "2027-09-08"),
        ("npm downloads (last-month)", 480, "2027-08-09 to 2027-09-07", "2027-09-08")]
    assert {(e["item"], e["status"]) for e in out["errors"]} == {
        ("ada-example/kvlite", "not_measured"), ("ada-example/gone", "not_found")}


def test_baselines_exits_0_when_every_item_is_measured(tmp_path):
    answers = {WEEK: {"status": 200, "body": {"downloads": 1, "start": "a", "end": "b"}},
               MONTH: {"status": 200, "body": {"downloads": 2, "start": "a", "end": "b"}}}
    path = tmp_path / "responses.json"
    path.write_text(json.dumps(answers), encoding="utf-8")
    r = run(BASELINES, "--npm", "kvlite-example", "--responses", str(path))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["errors"] == []


def test_baselines_refuses_a_responses_file_it_cannot_use(tmp_path):
    bad = tmp_path / "bad.json"
    for content in ("not json", "[]", json.dumps({WEEK: {"status": "200"}}), json.dumps({WEEK: 200})):
        bad.write_text(content, encoding="utf-8")
        r = run(BASELINES, "--npm", "kvlite-example", "--responses", str(bad))
        assert r.returncode == 2 and r.stdout == "" and "Traceback" not in r.stderr, content
    r = run(BASELINES, "--npm", "kvlite-example", "--responses", str(tmp_path / "missing.json"))
    assert r.returncode == 2 and "cannot read --responses" in r.stderr


class FakeOpener:
    def __init__(self, outcome):
        self.outcome = outcome

    def open(self, req, timeout=None):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return io.BytesIO(self.outcome)


@pytest.mark.parametrize("outcome, expected", [
    (urllib.error.HTTPError(REPO, 404, "Not Found", {}, None), "not_found"),
    (urllib.error.URLError("Tunnel connection failed: 403 Filtered"), "not_measured"),
    (urllib.error.HTTPError(REPO, 403, "rate limit", {}, None), "not_measured"),
    (TimeoutError("timed out"), "not_measured"),
    (b"<html>not json</html>", "not_measured"),
    (b'{"name": "kvlite"}', "not_measured"),
])
def test_a_missing_repository_is_told_from_a_blocked_network(monkeypatch, outcome, expected):
    bl = load(BASELINES, "baselines_network")
    monkeypatch.setattr(bl, "OPENER", FakeOpener(outcome))
    error = bl.NotFound if expected == "not_found" else bl.NotMeasured
    with pytest.raises(error):
        bl.github("ada-example/kvlite", "2027-09-08")
