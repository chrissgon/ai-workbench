"""Tests for skills/product-prd/scripts/lint_prd.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/product-prd/scripts/tests
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(rel: str, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / rel), *args], capture_output=True, text=True,
                          cwd=cwd, input=stdin, timeout=60)


def lint(rel: str, path: Path, text: str, *args: str) -> tuple[int, dict]:
    """Write `text` to `path`, lint it, and return the exit code and the parsed JSON result."""
    path.write_text(text, encoding="utf-8")
    r = run(rel, "--file", str(path), *args)
    return r.returncode, json.loads(r.stdout)


# ---------- product-prd/lint_prd.py: an id is not a numeric target ----------

LINT_PRD = "skills/product-prd/scripts/lint_prd.py"


def prd(target: str) -> str:
    return f"""# PRD: Plinth

## Summary

## Problem and goal

## Users

- U-1: Site owners. Situation: publishing docs. Needs: search. Source: brief.

## Scope

## Sources

## Features

- F-1: Search. Outcome: the reader can find a page. Priority: must. Phase: P-1. Source: brief.

## Success metrics

- M-1: Searches that end in a click. Target: {target}. Baseline: none. Measured by: analytics. Source: brief.

## Constraints

## Dependencies and risks

- R-1: The index grows. Trigger: many pages. Impact: slow builds. Mitigation: split the index.

## Release phases

- P-1: First release. Includes: F-1. Exit: search is live. Source: brief.

## Assumptions

## Open questions

- OPEN-2: Which share of searches should end in a click? Blocks: M-1. Recommended: 40 percent, the brief's figure.

## Readiness
"""


def test_lint_prd_accepts_a_numeric_target(tmp_path):
    code, out = lint(LINT_PRD, tmp_path / "prd.md", prd("40 percent of searches"))
    assert (code, out["errors"]) == (0, [])


def test_lint_prd_does_not_take_an_id_for_a_numeric_target(tmp_path):
    for target in ("OPEN-2", "set by OPEN-2 and F-1"):
        code, out = lint(LINT_PRD, tmp_path / "prd.md", prd(target))
        assert code == 1 and out["errors"] == ["M-1 has no numeric Target:"], target


# ---------- product-prd/lint_prd.py: numbers and dates come from a source, ids are well formed ----------

PRD_BRIEF = "# Brief: Plinth\n\nDecision 1: 40 percent of searches end in a click.\n"
PRD_BRIEF_NO_FIGURE = "# Brief: Plinth\n\nDecision 1: most searches end in a click.\n"
# the same document without the '- Brief:' line: every Source: names the document and the decision
PRD_UNNAMED = prd("40 percent of searches").replace("Source: brief.", "Source: brief.md decision 1.")
PRD_NAMED = PRD_UNNAMED.replace("# PRD: Plinth\n", "# PRD: Plinth\n\n- Brief: brief.md\n")
PRD_TARGET = "Target: 40 percent of searches."
PRD_USER_LINE = "- U-1: Site owners. Situation: publishing docs. Needs: search. Source: brief.md decision 1.\n"
PRD_FEATURE_LINE = "- F-1: Search. Outcome: the reader can find a page. Priority: must. Phase: P-1. Source: brief.md decision 1.\n"
PRD_METRIC_LINE = ("- M-1: Searches that end in a click. Target: 40 percent of searches. Baseline: none. "
                   "Measured by: analytics. Source: brief.md decision 1.\n")
PRD_PHASE_LINE = "- P-1: First release. Includes: F-1. Exit: search is live. Source: brief.md decision 1.\n"
PRD_SKIPPED = "number check skipped: no source file could be read (name the brief on the '- Brief:' line or pass --source)"


def prd_lint(tmp_path: Path, text: str, *args: str, brief: str | None = None) -> tuple[int, dict]:
    """Lint `text` from inside `tmp_path`, so that only the files a test writes there can be sources."""
    if brief is not None:
        (tmp_path / "brief.md").write_text(brief, encoding="utf-8")
    doc = tmp_path / "prd.md"
    doc.write_text(text, encoding="utf-8")
    r = run(LINT_PRD, "--file", str(doc), *args, cwd=tmp_path)
    return r.returncode, json.loads(r.stdout)


def test_lint_prd_fixture_lines_are_the_ones_the_tests_replace():
    for line in (PRD_USER_LINE, PRD_FEATURE_LINE, PRD_METRIC_LINE, PRD_PHASE_LINE):
        assert PRD_NAMED.count(line) == 1, line
    assert PRD_UNNAMED != PRD_NAMED and "Source: brief.\n" not in PRD_NAMED


def test_lint_prd_refuses_a_target_number_the_brief_does_not_have(tmp_path):
    code, out = prd_lint(tmp_path, PRD_NAMED, brief=PRD_BRIEF_NO_FIGURE)
    assert code == 1 and out["errors"] == ["M-1 target number 40 is in no source file"]
    code, out = prd_lint(tmp_path, PRD_NAMED, brief=PRD_BRIEF)
    assert (code, out["errors"], out["warnings"]) == (0, [], [])


def test_lint_prd_reads_a_thousands_separator_as_the_same_number(tmp_path):
    for in_prd, in_brief in (("1000", "1,000"), ("1,000", "1000")):
        text = PRD_NAMED.replace(PRD_TARGET, f"Target: {in_prd} searches a week.")
        code, out = prd_lint(tmp_path, text, brief=f"Decision 1: reach {in_brief} searches a week.\n")
        assert (code, out["errors"]) == (0, []), in_prd
    text = PRD_NAMED.replace(PRD_TARGET, "Target: 1,000 searches a week.")
    code, out = prd_lint(tmp_path, text, brief="Decision 1: reach 100 searches a week.\n")
    assert code == 1 and out["errors"] == ["M-1 target number 1000 is in no source file"]


def test_lint_prd_list_numbering_and_iso_dates_do_not_ground_a_number(tmp_path):
    text = PRD_NAMED.replace(PRD_TARGET, "Target: 3 percent of searches.")
    code, out = prd_lint(tmp_path, text, brief="Decisions:\n\n3. Search ships first.\n4) Themes ship later.\n")
    assert code == 1 and out["errors"] == ["M-1 target number 3 is in no source file"]
    text = PRD_NAMED.replace(PRD_TARGET, "Target: 12 percent of searches.")
    code, out = prd_lint(tmp_path, text, brief="Decided on 2031-05-12: search ships first.\n")
    assert code == 1 and out["errors"] == ["M-1 target number 12 is in no source file"]


def test_lint_prd_a_user_answer_line_grounds_a_number(tmp_path):
    answered = PRD_NAMED.replace("## Sources\n", '## Sources\n\n- User answer 2031-05-12: "40 percent"\n')
    assert answered != PRD_NAMED
    code, out = prd_lint(tmp_path, answered, brief=PRD_BRIEF_NO_FIGURE)
    assert (code, out["errors"]) == (0, [])
    # the same words outside a "- User answer" line ground nothing
    noted = PRD_NAMED.replace("## Sources\n", '## Sources\n\n- Note 2031-05-12: "40 percent"\n')
    code, out = prd_lint(tmp_path, noted, brief=PRD_BRIEF_NO_FIGURE)
    assert code == 1 and out["errors"] == ["M-1 target number 40 is in no source file"]


def test_lint_prd_refuses_a_date_the_sources_do_not_have(tmp_path):
    phase = PRD_NAMED.replace("Exit: search is live.", "Exit: search is live by 2031-06-30.")
    code, out = prd_lint(tmp_path, phase, brief=PRD_BRIEF)
    assert code == 1 and out["errors"] == ["P-1 date 2031-06-30 is in no source file"]
    code, out = prd_lint(tmp_path, phase, brief=PRD_BRIEF + "Decision 2: launch on 2031-06-30.\n")
    assert (code, out["errors"]) == (0, [])
    metric = PRD_NAMED.replace(PRD_TARGET, "Target: 40 percent of searches by June 2031.")
    code, out = prd_lint(tmp_path, metric, brief=PRD_BRIEF)
    assert code == 1 and out["errors"] == ["M-1 date June 2031 is in no source file"]
    code, out = prd_lint(tmp_path, metric, brief=PRD_BRIEF + "Decision 2: reach it by June 2031.\n")
    assert (code, out["errors"]) == (0, [])


def test_lint_prd_finds_sources_on_the_brief_line_under_sources_and_in_the_flag(tmp_path):
    def real(paths: list[str]) -> list[Path]:
        return [Path(p).resolve() for p in paths]

    code, out = prd_lint(tmp_path, PRD_NAMED, brief=PRD_BRIEF)
    assert code == 0 and real(out["sources_read"]) == [(tmp_path / "brief.md").resolve()]

    listed = tmp_path / "listed"
    (listed / "notes").mkdir(parents=True)
    (listed / "notes" / "research.md").write_text(PRD_BRIEF, encoding="utf-8")
    text = PRD_UNNAMED.replace("## Sources\n", "## Sources\n\n- notes/research.md: interview notes\n")
    code, out = prd_lint(listed, text)
    assert (code, out["errors"]) == (0, []) and real(out["sources_read"]) == [(listed / "notes" / "research.md").resolve()]

    flagged = tmp_path / "flagged"
    flagged.mkdir()
    (flagged / "figures.txt").write_text(PRD_BRIEF_NO_FIGURE, encoding="utf-8")
    code, out = prd_lint(flagged, PRD_UNNAMED, "--source", "figures.txt")
    assert real(out["sources_read"]) == [(flagged / "figures.txt").resolve()]
    assert code == 1 and out["errors"] == ["M-1 target number 40 is in no source file"]


def test_lint_prd_skips_the_number_check_with_a_warning_when_no_source_can_be_read(tmp_path):
    for text, args in ((PRD_UNNAMED, ()), (PRD_NAMED, ()), (PRD_UNNAMED, ("--source", "missing.md"))):
        dated = text.replace("Exit: search is live.", "Exit: search is live by 2031-06-30.")
        code, out = prd_lint(tmp_path, dated, *args)
        assert (code, out["errors"], out["sources_read"]) == (0, [], [])
        assert out["warnings"] == [PRD_SKIPPED]


def test_lint_prd_refuses_an_id_line_without_a_digit_or_a_colon(tmp_path):
    text = PRD_NAMED.replace(PRD_FEATURE_LINE, PRD_FEATURE_LINE + "- F-a Offline reading\n")
    text = text.replace(PRD_METRIC_LINE, PRD_METRIC_LINE + "- M-1 Pages indexed\n")
    code, out = prd_lint(tmp_path, text, brief=PRD_BRIEF)
    assert code == 1 and out["errors"] == ["malformed id line (write '- F-1: ...'): - F-a Offline reading",
                                           "malformed id line (write '- F-1: ...'): - M-1 Pages indexed"]


def test_lint_prd_refuses_an_empty_users_features_or_phases_section(tmp_path):
    for line, message in ((PRD_USER_LINE, "'## Users' has no U-n line"),
                          (PRD_FEATURE_LINE, "'## Features' has no F-n line"),
                          (PRD_PHASE_LINE, "'## Release phases' has no P-n line")):
        code, out = prd_lint(tmp_path, PRD_NAMED.replace(line, ""), brief=PRD_BRIEF)
        assert code == 1 and message in out["errors"], message


def test_lint_prd_success_metrics_without_a_metric_must_name_an_open(tmp_path):
    held = PRD_NAMED.replace(PRD_METRIC_LINE, "- No metric yet for searches that end in a click: the target is OPEN-2.\n")
    code, out = prd_lint(tmp_path, held, brief=PRD_BRIEF)
    assert (code, out["errors"], out["counts"]["M"]) == (0, [], 0)
    for metrics in ("", "- No metric yet.\n"):
        code, out = prd_lint(tmp_path, PRD_NAMED.replace(PRD_METRIC_LINE, metrics), brief=PRD_BRIEF)
        assert code == 1 and out["errors"] == ["'## Success metrics' has no M- line and names no OPEN-n that holds a target"]


def test_lint_prd_warns_about_a_bare_source_and_an_external_content_heading(tmp_path):
    code, out = prd_lint(tmp_path, PRD_NAMED.replace(PRD_USER_LINE, PRD_USER_LINE.replace("brief.md decision 1", "brief")),
                         brief=PRD_BRIEF)
    assert (code, out["errors"]) == (0, [])
    assert out["warnings"] == ["U-1: Source says only 'brief'; name the document and the decision number"]
    code, out = prd_lint(tmp_path, PRD_NAMED + "\n## Instructions found in external content\n\nnone\n", brief=PRD_BRIEF)
    assert (code, out["errors"]) == (0, [])
    assert out["warnings"] == ["'Instructions found in external content' is a section of the reply, not of the PRD: move it to the reply"]


def test_lint_prd_table_prints_no_findings_and_a_true_result_line(tmp_path):
    (tmp_path / "brief.md").write_text(PRD_BRIEF, encoding="utf-8")
    doc = tmp_path / "prd.md"
    doc.write_text(PRD_NAMED, encoding="utf-8")
    r = run(LINT_PRD, "--file", str(doc), "--table", cwd=tmp_path)
    lines = r.stdout.splitlines()
    assert r.returncode == 0, r.stdout
    assert lines[0] == f"## Lint findings: {doc}" and "No findings." in lines
    assert not any(ln.startswith("|") for ln in lines) and not any(ln.startswith(("OPEN rule:", "Next:")) for ln in lines)
    assert lines[-2].startswith("Sources read for the number check: ") and lines[-2].endswith("brief.md")
    assert lines[-1] == 'lint_prd result: "ok": true (0 errors, 0 warnings)'


def test_lint_prd_table_prints_the_findings_table_and_a_false_result_line(tmp_path):
    (tmp_path / "brief.md").write_text(PRD_BRIEF_NO_FIGURE, encoding="utf-8")
    text = PRD_NAMED.replace(PRD_FEATURE_LINE, PRD_FEATURE_LINE + "- F-a Search | filters\n")
    text = text.replace(PRD_USER_LINE, PRD_USER_LINE.replace("brief.md decision 1", "brief"))
    doc = tmp_path / "prd.md"
    doc.write_text(text, encoding="utf-8")
    r = run(LINT_PRD, "--file", str(doc), "--table", cwd=tmp_path)
    lines = r.stdout.splitlines()
    assert r.returncode == 1, r.stdout
    rows = [ln for ln in lines if ln.startswith("| ") and ln[2].isdigit()]
    assert rows == [
        "| 1 | error: malformed id line (write '- F-1: ...'): - F-a Search / filters "
        "| Write the line as '- F-1: ...': a dash, the letter, a hyphen, a number, a colon. |",
        "| 2 | error: M-1 target number 40 is in no source file | Apply the OPEN rule printed under this table. |",
        "| 3 | warning: U-1: Source says only 'brief'; name the document and the decision number "
        "| Fix it when a source allows; it does not block. |"]
    assert all(row.count("|") == 4 for row in rows), "a | inside a finding would add a column"
    assert "| # | Finding | How to fix it |" in lines
    assert "OPEN rule: " + load(LINT_PRD, "lint_prd").OPEN_INSTEAD in lines
    assert "Next: fix every error as its row says, then run this command again." in lines
    assert lines[-1] == 'lint_prd result: "ok": false (2 errors, 1 warnings)'


def test_lint_prd_how_to_fix_follows_the_errors_one_to_one(tmp_path):
    mod = load(LINT_PRD, "lint_prd")
    text = PRD_NAMED.replace(PRD_FEATURE_LINE, PRD_FEATURE_LINE + "- F-a Offline reading\n")
    text = text.replace(" Exit: search is live.", "").replace("## Readiness\n", "")
    code, out = prd_lint(tmp_path, text, brief=PRD_BRIEF_NO_FIGURE)
    assert code == 1 and out["errors"] == ["missing section '## Readiness'",
                                           "malformed id line (write '- F-1: ...'): - F-a Offline reading",
                                           "M-1 target number 40 is in no source file",
                                           "P-1 has no Exit: line"]
    assert out["how_to_fix"] == [mod.how_to_fix(e) for e in out["errors"]]
    assert [fix.split(":")[0].split(".")[0] for fix in out["how_to_fix"]] == [
        "Add the heading exactly as in assets/prd-template", "Write the line as '- F-1",
        "Do not pick another number or date", "Append 'Exit"]
    code, out = prd_lint(tmp_path, PRD_NAMED, brief=PRD_BRIEF)
    assert out["how_to_fix"] == []


# ---------- product-prd/lint_prd.py: the command line and the record of --report ----------

def test_lint_prd_source_given_last_is_a_usage_error_not_a_silent_drop(tmp_path):
    """`--source` without its value used to be dropped, so the run checked numbers against fewer sources and said
    nothing. It is a usage error now, as every value flag given last is."""
    (tmp_path / "brief.md").write_text(PRD_BRIEF, encoding="utf-8")
    doc = tmp_path / "prd.md"
    doc.write_text(PRD_NAMED, encoding="utf-8")
    r = run(LINT_PRD, "--file", str(doc), "--source", cwd=tmp_path)
    assert r.returncode == 2 and r.stdout == "" and "--source needs a value" in r.stderr
    assert "Traceback" not in r.stderr
    r = run(LINT_PRD, "--file", str(doc), "--source", "--table", cwd=tmp_path)
    assert r.returncode == 2 and "--source needs a value" in r.stderr


def test_lint_prd_usage_errors_go_to_stderr_with_exit_2(tmp_path):
    r = run(LINT_PRD, cwd=tmp_path)
    assert r.returncode == 2 and r.stdout == "" and "Usage" in r.stderr
    for flag in ("--file", "--report"):
        r = run(LINT_PRD, "--file", "prd.md", flag, cwd=tmp_path)
        assert r.returncode == 2 and r.stdout == "" and f"{flag} needs a value" in r.stderr, flag
    r = run(LINT_PRD, "--file", "prd.md", "--reprot", "x.json", cwd=tmp_path)
    assert r.returncode == 2 and r.stdout == "" and "unknown option '--reprot'" in r.stderr
    assert not (tmp_path / "x.json").exists()


def test_lint_prd_report_writes_the_record_beside_the_table(tmp_path):
    (tmp_path / "brief.md").write_text(PRD_BRIEF_NO_FIGURE, encoding="utf-8")
    doc = tmp_path / "prd.md"
    doc.write_text(PRD_NAMED, encoding="utf-8")
    r = run(LINT_PRD, "--file", str(doc), "--table", "--report", "prd.lint-before.json", "--source", "brief.md",
            cwd=tmp_path)
    record = json.loads((tmp_path / "prd.lint-before.json").read_text(encoding="utf-8"))
    assert r.returncode == 1
    assert set(record) == {"script", "date", "arguments", "ok", "summary", "errors", "warnings", "counts"}
    assert record["script"] == "lint_prd.py" and len(record["date"]) == 10
    assert record["arguments"] == {"--file": str(doc), "--table": True, "--source": ["brief.md"]}
    assert record["ok"] is False and record["errors"] == ["M-1 target number 40 is in no source file"]
    assert record["summary"] == r.stdout.splitlines()[-1] == 'lint_prd result: "ok": false (1 errors, 0 warnings)'
    (tmp_path / "brief.md").write_text(PRD_BRIEF, encoding="utf-8")
    r = run(LINT_PRD, "--file", str(doc), "--report", "prd.lint.json", cwd=tmp_path)
    printed, record = json.loads(r.stdout), json.loads((tmp_path / "prd.lint.json").read_text(encoding="utf-8"))
    assert r.returncode == 0 and record["ok"] is True and record["errors"] == []
    assert printed["summary"] == record["summary"] == 'lint_prd result: "ok": true (0 errors, 0 warnings)'
