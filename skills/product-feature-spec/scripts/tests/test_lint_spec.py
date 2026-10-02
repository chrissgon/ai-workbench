"""Tests for skills/product-feature-spec/scripts/lint_spec.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/product-feature-spec/scripts/tests
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def run(rel: str, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / rel), *args], capture_output=True, text=True,
                          cwd=cwd, input=stdin, timeout=60)


def lint(rel: str, path: Path, text: str, *args: str) -> tuple[int, dict]:
    """Write `text` to `path`, lint it, and return the exit code and the parsed JSON result."""
    path.write_text(text, encoding="utf-8")
    r = run(rel, "--file", str(path), *args)
    return r.returncode, json.loads(r.stdout)


# ---------- product-feature-spec/lint_spec.py: an NFR needs a number, an OPEN a recommendation ----------

LINT_SPEC = "skills/product-feature-spec/scripts/lint_spec.py"


def spec(nfr: str = "Results appear within 200 ms of the last keystroke",
         open_question: str = "Should search cover drafts? Blocks: nothing. Recommended: no, drafts are private") -> str:
    return f"""# Feature specification: Search

## Summary

## Goal and users

## Scope

## Sources

## Functional requirements

- REQ-1: Show matching pages when the reader types a query. Source: PRD F-1.

## Non-functional requirements

- NFR-1: {nfr}. Source: PRD M-2, measured 2026-01-05.

## Constraints

## Edge cases

- EDGE-1: empty query → show no results

## Acceptance criteria

- AC-1:
  Given an index with one page
  When the reader types its title
  Then the page is listed
  Covers: REQ-1, NFR-1

## Assumptions

## Open questions

- OPEN-1: {open_question}.

## Readiness
"""


def test_lint_spec_accepts_an_nfr_with_a_number_and_an_open_with_a_recommendation(tmp_path):
    code, out = lint(LINT_SPEC, tmp_path / "spec.md", spec())
    assert (code, out["errors"]) == (0, [])


def test_lint_spec_refuses_an_nfr_without_a_number(tmp_path):
    # the digits of its own id, of a cited id and of the Source: text are not the requirement's figure
    code, out = lint(LINT_SPEC, tmp_path / "spec.md", spec(nfr="Results appear soon after REQ-1 runs"))
    assert code == 1 and out["errors"] == [
        "NFR-1 states no number: give the sourced figure, or move it to an OPEN with a Recommended value"]


def test_lint_spec_refuses_an_open_without_a_recommendation(tmp_path):
    code, out = lint(LINT_SPEC, tmp_path / "spec.md", spec(open_question="Should search cover drafts? Blocks: nothing"))
    assert code == 1 and out["errors"] == ["OPEN-1 has no Recommended: entry"]
    code, out = lint(LINT_SPEC, tmp_path / "spec.md", spec(open_question="Should search cover drafts"))
    assert out["errors"] == ["OPEN-1 has no Blocks: entry", "OPEN-1 has no Recommended: entry"]


# ---------- product-feature-spec/lint_spec.py: the shape of the bullets, the report and next lines ----------

SPEC_REQ_LINE = "- REQ-1: Show matching pages when the reader types a query. Source: PRD F-1.\n"
SPEC_EDGE_LINE = "- EDGE-1: empty query → show no results\n"
SPEC_COUNTS = "(1 REQ, 1 NFR, 1 EDGE, 1 AC, 0 ASSUMPTION, 1 OPEN)"


def line_numbers(text: str, wanted: str) -> list[int]:
    return [n for n, ln in enumerate(text.splitlines(), 1) if ln == wanted]


def test_lint_spec_groups_the_empty_bullets_in_one_error(tmp_path):
    text = spec().replace(SPEC_REQ_LINE, SPEC_REQ_LINE + "-\n").replace("## Assumptions\n", "## Assumptions\n\n-\n")
    text = text.replace("## Summary\n", "## Summary\n\n  -\n")
    where = sorted(line_numbers(text, "-") + line_numbers(text, "  -"))
    assert len(where) == 3
    code, out = lint(LINT_SPEC, tmp_path / "spec.md", text)
    assert code == 1 and out["errors"] == [f"empty bullet '-' on lines {where}: delete those lines"]


def test_lint_spec_groups_the_bullets_with_no_space_after_the_dash(tmp_path):
    text = spec().replace(SPEC_REQ_LINE, "-" + SPEC_REQ_LINE[2:]).replace(SPEC_EDGE_LINE, "-" + SPEC_EDGE_LINE[2:])
    where = [n for n, ln in enumerate(text.splitlines(), 1) if ln.startswith(("-REQ-1:", "-EDGE-1:"))]
    assert len(where) == 2
    code, out = lint(LINT_SPEC, tmp_path / "spec.md", text)
    assert code == 1 and out["errors"] == [
        f"no space after the dash on lines {where}: write '- REQ-1: ...', not '-REQ-1: ...'"]
    assert out["counts"]["REQ"] == 1 and out["counts"]["EDGE"] == 1


def test_lint_spec_refuses_an_edge_case_with_an_arrow_and_no_id(tmp_path):
    for arrow in ("→", "->"):
        bullet = f"- very long query {arrow} cut it at 200 characters"
        text = spec().replace(SPEC_EDGE_LINE, SPEC_EDGE_LINE + bullet + "\n")
        n = line_numbers(text, bullet)[0]
        code, out = lint(LINT_SPEC, tmp_path / "spec.md", text)
        assert code == 1 and out["errors"] == [
            f"line {n} in '## Edge cases' is not '- EDGE-n: ...': give it the next EDGE id, or delete it: {bullet}"]


def test_lint_spec_accepts_the_notes_of_skipped_edge_categories(tmp_path):
    notes = "- Timing: not applicable\n- Categories skipped: permissions, the feature has no roles\n"
    code, out = lint(LINT_SPEC, tmp_path / "spec.md", spec().replace(SPEC_EDGE_LINE, SPEC_EDGE_LINE + notes))
    assert (code, out["errors"], out["counts"]["EDGE"]) == (0, [], 1)


def test_lint_spec_refuses_a_requirement_bullet_without_its_id(tmp_path):
    bullet = "- The reader can filter the results by tag"
    text = spec().replace(SPEC_REQ_LINE, SPEC_REQ_LINE + bullet + "\n")
    n = line_numbers(text, bullet)[0]
    code, out = lint(LINT_SPEC, tmp_path / "spec.md", text)
    assert code == 1 and out["errors"] == [
        f"line {n} in '## Functional requirements' is not '- REQ-n: ...': give it the next REQ id, or delete it: {bullet}"]
    for none in ("- none", "- None: the feature only changes a limit"):
        code, out = lint(LINT_SPEC, tmp_path / "spec.md", spec().replace(SPEC_REQ_LINE, none + "\n"))
        assert (code, out["errors"], out["counts"]["REQ"]) == (0, [], 0), none


def test_lint_spec_prints_the_report_line_and_what_to_do_next(tmp_path):
    doc = tmp_path / "spec.md"
    code, out = lint(LINT_SPEC, doc, spec())
    assert code == 0 and out["ok"] is True
    assert out["report"] == f"lint_spec.py --file {doc}: ok: true, 0 errors, 0 warnings {SPEC_COUNTS}"
    assert out["next"].startswith("Lint passed.")
    code, out = lint(LINT_SPEC, doc, spec().replace(SPEC_REQ_LINE, SPEC_REQ_LINE + "-\n"))
    assert code == 1 and out["ok"] is False
    assert out["report"] == f"lint_spec.py --file {doc}: ok: false, 1 errors, 0 warnings {SPEC_COUNTS}"
    assert out["next"].startswith("Not done")
    # a warning alone keeps the exit code at 0 and still says the work is not done
    code, out = lint(LINT_SPEC, doc, spec().replace("Show matching pages", "Show matching pages in a simple list"))
    assert code == 0 and len(out["warnings"]) == 1
    assert out["report"] == f"lint_spec.py --file {doc}: ok: true, 0 errors, 1 warnings {SPEC_COUNTS}"
    assert out["next"].startswith("Not done")
