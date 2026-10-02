"""Tests for skills/design-execute/scripts/lint_result.py: what a results document must hold against its brief.

Run: uv run --with pytest pytest skills/design-execute/scripts/tests

Offline; the product, the tool and every run below are fictional.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "lint_result.py"

BRIEF = """# Brief: Harbor landing

## Evaluation criteria

- CRIT-1: the headline is readable at 320 px
- CRIT-2: the pricing link is reachable from the first screen
"""

RESULT = """# Results: Harbor landing

- Brief: docs/design/brief.md
- Tool: Sketchboard
- Mode: assisted
- Status: done

## Runs

| Run | Round | Direction | Status | Outputs |
|-----|-------|-----------|--------|---------|
| R1 | 1 | Calm | done | out/r1.png |
| R2 | 1 | Bold | approved | https://design.example/r2 |

## Critique

| Criterion | R1 | R2 |
|-----------|----|----|
| CRIT-1 | pass: the headline fits on two lines | partial: the headline wraps to four lines |
| CRIT-2 | fail: no pricing link | pass: the pricing link is in the header |

## Decision

- Recommendation: R2, after shortening the headline.

## Next

- Ask the user to choose a direction.
"""


def lint(tmp_path: Path, text: str = RESULT, brief: str = BRIEF, output: bool = True) -> tuple[int, dict]:
    (tmp_path / "result.md").write_text(text, encoding="utf-8")
    (tmp_path / "brief.md").write_text(brief, encoding="utf-8")
    if output:
        (tmp_path / "out").mkdir(exist_ok=True)
        (tmp_path / "out" / "r1.png").write_bytes(b"png")
    r = subprocess.run([sys.executable, str(SCRIPT), "--file", str(tmp_path / "result.md"), "--brief",
                        str(tmp_path / "brief.md"), "--root", str(tmp_path)], capture_output=True, text=True, timeout=60)
    return r.returncode, json.loads(r.stdout)


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60)


def test_help_exits_zero_and_no_argument_is_a_usage_error():
    r = run("--help")
    assert r.returncode == 0 and "--brief" in r.stdout
    assert run().returncode == 2


def test_a_complete_results_document_passes(tmp_path):
    code, out = lint(tmp_path)
    assert code == 0, out
    assert out == {"ok": True, "counts": {"runs": 2, "done": 2, "criteria": 2}, "errors": []}


def test_missing_sections_and_header_lines_are_reported(tmp_path):
    text = RESULT.replace("## Next\n", "## Later\n").replace("- Tool: Sketchboard\n", "")
    code, out = lint(tmp_path, text)
    assert code == 1
    assert "missing section '## Next'" in out["errors"] and "missing header line '- Tool:'" in out["errors"]


def test_runs_need_a_known_status_and_outputs_that_exist(tmp_path):
    text = RESULT.replace("| R2 | 1 | Bold | approved | https://design.example/r2 |", "| R2 | 1 | Bold | finished | - |")
    code, out = lint(tmp_path, text, output=False)
    assert code == 1
    assert any(e.startswith("R2: status 'finished' is not one of") for e in out["errors"])
    assert "R1: output out/r1.png does not exist" in out["errors"]
    code, out = lint(tmp_path, RESULT.replace("| done | out/r1.png |", "| done | - |"))
    assert "R1: marked done but lists no outputs" in out["errors"]


def test_every_criterion_of_the_brief_needs_a_verdict_with_evidence_per_done_run(tmp_path):
    text = RESULT.replace("| CRIT-2 | fail: no pricing link | pass: the pricing link is in the header |\n", "")
    text = text.replace("partial: the headline wraps to four lines", "good")
    code, out = lint(tmp_path, text)
    assert code == 1
    assert "CRIT-2 of the brief has no Critique row" in out["errors"]
    assert any(e.startswith("CRIT-1 × R2: verdict must be") for e in out["errors"])


def test_a_finished_round_needs_a_recommendation_and_a_waiting_run_the_document_status(tmp_path):
    code, out = lint(tmp_path, RESULT.replace("- Recommendation: R2, after shortening the headline.\n", ""))
    assert code == 1
    assert out["errors"] == ["every run of the latest round is done but no Recommendation is written"]
    waiting = RESULT.replace("| Bold | approved |", "| Bold | waiting on user |")
    code, out = lint(tmp_path, waiting)
    assert out["errors"] == ["a run is waiting on the user but the document status is not 'waiting on user'"]
    code, out = lint(tmp_path, waiting.replace("- Status: done", "- Status: waiting on user"))
    assert code == 0, out


def test_usage_errors_exit_two(tmp_path):
    (tmp_path / "result.md").write_text(RESULT, encoding="utf-8")
    for args in (["--file", str(tmp_path / "result.md")],
                 ["--file", str(tmp_path / "result.md"), "--brief", str(tmp_path / "missing.md")]):
        r = run(*args)
        assert r.returncode == 2, (args, r.stderr)
        assert r.stderr.startswith("Error:")


@pytest.mark.xfail(strict=True, reason="lint_result.py reads argv[index + 1] without checking it exists: a flag given "
                                       "last, without its value, ends in an IndexError traceback (exit 1), not exit 2")
def test_a_flag_without_its_value_is_a_usage_error(tmp_path):
    r = run("--brief", str(tmp_path / "brief.md"), "--file")
    assert r.returncode == 2 and "Traceback" not in r.stderr
