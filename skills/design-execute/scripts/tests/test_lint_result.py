"""Tests for skills/design-execute/scripts/lint_result.py: what a results document must hold against its brief.

Run: uv run --with pytest pytest skills/design-execute/scripts/tests

Offline; the product, the tool and every run below are fictional.
"""
from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path

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

| Run | Round | Direction | Status | Pack | Outputs |
|-----|-------|-----------|--------|------|---------|
| R1 | 1 | Calm | done | packs/calm/prompt.md | out/r1.png |
| R2 | 1 | Bold | approved | packs/bold/prompt.md | https://design.example/r2 |

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


def write(tmp_path: Path, text: str = RESULT, brief: str = BRIEF, output: bool = True, packs: bool = True):
    (tmp_path / "result.md").write_text(text, encoding="utf-8")
    (tmp_path / "brief.md").write_text(brief, encoding="utf-8")
    if output:
        (tmp_path / "out").mkdir(exist_ok=True)
        (tmp_path / "out" / "r1.png").write_bytes(b"png")
    if packs:
        for direction in ("calm", "bold"):
            (tmp_path / "packs" / direction).mkdir(parents=True, exist_ok=True)
            (tmp_path / "packs" / direction / "prompt.md").write_text("# Run\n", encoding="utf-8")


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60, cwd=cwd)


def lint(tmp_path: Path, text: str = RESULT, brief: str = BRIEF, output: bool = True,
         packs: bool = True) -> tuple[int, dict]:
    write(tmp_path, text, brief, output, packs)
    r = run("--file", str(tmp_path / "result.md"), "--brief", str(tmp_path / "brief.md"), "--root", str(tmp_path))
    return r.returncode, json.loads(r.stdout)


def test_help_exits_zero_and_no_argument_is_a_usage_error():
    r = run("--help")
    assert r.returncode == 0 and "--brief" in r.stdout and "--report" in r.stdout
    r = run()
    assert r.returncode == 2 and r.stdout == "" and "--file and --brief are required" in r.stderr


def test_a_complete_results_document_passes(tmp_path):
    code, out = lint(tmp_path)
    assert code == 0, out
    assert out == {"ok": True, "counts": {"runs": 2, "done": 2, "packs": 2, "criteria": 2}, "errors": [],
                   "summary": "lint_result ok: 0 errors; 2 runs, 2 done, 2 prompt packs, 2 criteria"}


def test_missing_sections_and_header_lines_are_reported(tmp_path):
    text = RESULT.replace("## Next\n", "## Later\n").replace("- Tool: Sketchboard\n", "")
    code, out = lint(tmp_path, text)
    assert code == 1
    assert "missing section '## Next'" in out["errors"] and "missing header line '- Tool:'" in out["errors"]
    assert out["summary"].startswith("lint_result FAILED: 2 errors")


def test_runs_need_a_known_status_and_outputs_that_exist(tmp_path):
    text = RESULT.replace("| R2 | 1 | Bold | approved | packs/bold/prompt.md | https://design.example/r2 |",
                          "| R2 | 1 | Bold | finished | packs/bold/prompt.md | - |")
    code, out = lint(tmp_path, text, output=False)
    assert code == 1
    assert any(e.startswith("R2: status 'finished' is not one of") for e in out["errors"])
    assert "R1: output out/r1.png does not exist" in out["errors"]
    code, out = lint(tmp_path, RESULT.replace("| done | packs/calm/prompt.md | out/r1.png |",
                                              "| done | packs/calm/prompt.md | - |"))
    assert "R1: marked done but lists no outputs" in out["errors"]


def test_every_run_needs_its_prompt_pack(tmp_path):
    code, out = lint(tmp_path, packs=False)
    assert code == 1
    assert out["errors"] == ["R1: prompt pack packs/calm/prompt.md does not exist",
                             "R2: prompt pack packs/bold/prompt.md does not exist"]
    assert out["counts"]["packs"] == 0
    code, out = lint(tmp_path, RESULT.replace("packs/calm/prompt.md", "packs/calm/"))
    assert out["errors"] == ["R1: Pack must be the path of the run's prompt.md, got 'packs/calm/'"]


def test_a_runs_table_without_the_pack_column_is_reported(tmp_path):
    text = (RESULT.replace("| Run | Round | Direction | Status | Pack | Outputs |", "| Run | Round | Direction | Status | Outputs |")
            .replace("|-----|-------|-----------|--------|------|---------|", "|-----|-------|-----------|--------|---------|")
            .replace(" packs/calm/prompt.md |", "").replace(" packs/bold/prompt.md |", ""))
    code, out = lint(tmp_path, text)
    assert code == 1
    assert out["errors"] == ["Runs lacks the column(s) Pack"]


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


def test_report_writes_the_record_of_the_evidence_convention(tmp_path):
    write(tmp_path)
    r = run("--file", "result.md", "--brief", "brief.md", "--report", "result.lint.json", "--json", cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    text = (tmp_path / "result.lint.json").read_text(encoding="utf-8")
    assert text.endswith("\n")
    record = json.loads(text)
    printed = json.loads(r.stdout)
    assert record == {"script": "lint_result.py", "date": datetime.date.today().isoformat(),
                      "arguments": {"--file": "result.md", "--brief": "brief.md", "--json": True},
                      "ok": True, "summary": printed["summary"], "errors": [], "counts": printed["counts"]}
    (tmp_path / "packs" / "bold" / "prompt.md").unlink()
    r = run("--file", "result.md", "--brief", "brief.md", "--report", "result.lint.json", cwd=tmp_path)
    assert r.returncode == 1
    record = json.loads((tmp_path / "result.lint.json").read_text(encoding="utf-8"))
    assert record["ok"] is False and record["errors"] == ["R2: prompt pack packs/bold/prompt.md does not exist"]
    assert record["summary"] == json.loads(r.stdout)["summary"]


def test_usage_errors_exit_two_on_stderr_and_write_no_report(tmp_path):
    write(tmp_path)
    for args in (["--file", "result.md"],
                 ["--file", "result.md", "--brief", "missing.md", "--report", "r.json"],
                 ["--brief", "brief.md", "--file"],
                 ["--file", "result.md", "--brief", "brief.md", "--report"],
                 ["--file", "result.md", "--brief", "brief.md", "--reprot", "r.json"]):
        r = run(*args, cwd=tmp_path)
        assert r.returncode == 2, (args, r.stderr)
        assert r.stderr.startswith("Error:") and "Traceback" not in r.stderr and r.stdout == ""
    assert not (tmp_path / "r.json").exists()
    r = run("--file", "result.md", "--brief", "brief.md", "--root", cwd=tmp_path)
    assert r.returncode == 2 and "--root needs a value" in r.stderr
