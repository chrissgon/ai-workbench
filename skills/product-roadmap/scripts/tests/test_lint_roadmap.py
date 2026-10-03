"""Tests for skills/product-roadmap/scripts/lint_roadmap.py. Offline, fictional data."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LINT = ROOT / "skills/product-roadmap/scripts/lint_roadmap.py"

PRD = """# PRD: Tally

## Features

- F-1: Receipt list. Outcome: every receipt is visible. Priority: must. Phase: P-1. Source: brief
- F-2: Monthly digest. Outcome: a digest is sent. Priority: should. Phase: P-1. Source: brief
- F-3: Shared folders. Outcome: two people share receipts. Priority: later. Phase: P-2. Source: brief
"""

ROADMAP = """# Roadmap: Tally

- Owner: product-roadmap
- Status: draft
- Date: 2031-02-03
- PRD: docs/product/prd.md

## Summary

Two releases; the first proves receipts can be listed.

## Sources

- docs/product/prd.md

## Method

Method: dependency first, then priority, then risk. Dates: none.

## Dependencies

- F-1: Depends on: none.
- F-2: Depends on: F-1, because the digest reads the receipt list (PRD F-2).

## Releases

- R-1: Core. Goal: list receipts. Includes: F-1, F-2. Order: F-1 (no dependency), then F-2 (needs F-1). Exit: a person lists receipts and gets a digest. Depends on: none.
- R-2: Sharing. Goal: share receipts. Includes: F-3. Order: F-3 (only feature). Exit: two people see one folder. Depends on: R-1.

## Now, next, later

- Now: F-1
- Next: F-2
- Later: F-3

## Risks by release

- R-1: none in the PRD.

## Not planned

- none

## Assumptions

- ASSUMPTION-1: One language. Safe because: the brief names one.

## Open questions

- OPEN-1: Which mail sender? Blocks: F-2. Recommended: the existing one, because it is configured.

## Readiness

- Ready for design and engineering: no, because OPEN-1 blocks F-2
"""


def lint(tmp_path: Path, roadmap: str, prd: str = PRD) -> tuple[int, dict]:
    (tmp_path / "roadmap.md").write_text(roadmap, encoding="utf-8")
    (tmp_path / "prd.md").write_text(prd, encoding="utf-8")
    p = subprocess.run([sys.executable, str(LINT), "--file", "roadmap.md", "--prd", "prd.md"],
                       cwd=tmp_path, capture_output=True, text=True, check=False)
    return p.returncode, json.loads(p.stdout)


def test_clean_roadmap_passes_and_gives_a_line_to_quote(tmp_path):
    code, out = lint(tmp_path, ROADMAP)
    assert code == 0 and out["ok"] is True
    assert out["summary"] == "lint_roadmap.py --file roadmap.md --prd prd.md: ok: true, 0 errors, 0 warnings"


def test_header_date_is_not_a_delivery_date(tmp_path):
    code, out = lint(tmp_path, ROADMAP)
    assert code == 0 and out["warnings"] == []


def test_summary_counts_errors(tmp_path):
    code, out = lint(tmp_path, ROADMAP.replace("Includes: F-1, F-2.", "Includes: F-1."))
    assert code == 1 and out["ok"] is False
    assert any("F-2 (should) is in 0 releases" in e for e in out["errors"])
    assert out["summary"].endswith(f"ok: false, {len(out['errors'])} errors, 0 warnings")


def test_blocking_open_question_needs_readiness_no(tmp_path):
    code, out = lint(tmp_path, ROADMAP.replace("engineering: no, because OPEN-1 blocks F-2", "engineering: yes: start with F-1"))
    assert code == 1
    assert any("OPEN-1 blocks F-2" in e and "Readiness" in e for e in out["errors"])


def test_non_blocking_open_question_allows_readiness_yes(tmp_path):
    text = ROADMAP.replace("Blocks: F-2.", "Blocks: nothing.").replace(
        "engineering: no, because OPEN-1 blocks F-2", "engineering: yes: start with F-1")
    code, out = lint(tmp_path, text)
    assert code == 0, out["errors"]


def test_effort_and_unsourced_date_on_a_release(tmp_path):
    code, out = lint(tmp_path, ROADMAP.replace("Depends on: R-1.", "Depends on: R-1. Ships 2031-05-01 after 3 weeks."))
    assert code == 1
    assert any("R-2 states effort" in e for e in out["errors"])
    assert any("R-2 carries a date" in w for w in out["warnings"])


def test_missing_prd_flag_is_a_usage_error(tmp_path):
    (tmp_path / "roadmap.md").write_text(ROADMAP, encoding="utf-8")
    p = subprocess.run([sys.executable, str(LINT), "--file", "roadmap.md"], cwd=tmp_path,
                       capture_output=True, text=True, check=False)
    assert p.returncode == 2 and "--prd" in p.stderr


def run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(LINT), *args], cwd=tmp_path, capture_output=True, text=True, check=False)


def test_a_value_flag_given_last_and_an_unknown_flag_are_usage_errors(tmp_path):
    for flag in ("--file", "--prd", "--report"):
        p = run(tmp_path, "--file", "roadmap.md", "--prd", "prd.md", flag)
        assert p.returncode == 2 and p.stdout == "" and f"{flag} needs a value" in p.stderr, flag
        assert "Traceback" not in p.stderr
    p = run(tmp_path, "--file", "roadmap.md", "--prd", "prd.md", "--reprot", "x.json")
    assert p.returncode == 2 and p.stdout == "" and "unknown option '--reprot'" in p.stderr
    p = run(tmp_path)
    assert p.returncode == 2 and p.stdout == "" and "Usage" in p.stderr


def test_report_writes_the_record_of_the_run(tmp_path):
    lint(tmp_path, ROADMAP.replace("Includes: F-1, F-2.", "Includes: F-1."))
    p = run(tmp_path, "--file", "roadmap.md", "--prd", "prd.md", "--report", "roadmap.lint.json")
    printed, record = json.loads(p.stdout), json.loads((tmp_path / "roadmap.lint.json").read_text(encoding="utf-8"))
    assert p.returncode == 1
    assert set(record) == {"script", "date", "arguments", "ok", "summary", "errors", "warnings", "counts"}
    assert record["script"] == "lint_roadmap.py" and record["arguments"] == {"--file": "roadmap.md", "--prd": "prd.md"}
    assert record["ok"] is False and record["summary"] == printed["summary"] and record["errors"] == printed["errors"]
    assert record["counts"] == {"releases": 2, "features": 3, "placed": 2, "unplaced": 1}
    lint(tmp_path, ROADMAP)
    p = run(tmp_path, "--file", "roadmap.md", "--prd", "prd.md", "--report", "roadmap.lint.json")
    record = json.loads((tmp_path / "roadmap.lint.json").read_text(encoding="utf-8"))
    assert p.returncode == 0 and record["ok"] is True and record["errors"] == []
