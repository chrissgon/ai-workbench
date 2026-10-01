"""Tests for skills/product-backlog/scripts/lint_backlog.py.

Run: uv run --with pytest pytest scripts/tests/test_product_backlog_scripts.py

Offline; every name, path and requirement below is fictional.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINT = ROOT / "skills/product-backlog/scripts/lint_backlog.py"
FILES = ROOT / "skills/product-backlog/evals/files"

SPEC = """# Feature specification: lantern

## Functional requirements
- REQ-1: The build reads every note. Source: brief
- REQ-2: The old notes page is removed. Source: brief
## Non-functional requirements
- NFR-1: The build ends in under 5 seconds. Source: brief
## Acceptance criteria
- AC-1:
  Given a note
  Then it is published
  Covers: REQ-1, NFR-1
- AC-2:
  Given the old page
  Then it is gone
  Covers: REQ-2
"""

DESIGN = """# Design: lantern

## Verification plan

| AC | Check | Type | Command or location |
|----|-------|------|---------------------|
| AC-1 | a note is published | integration | `node --test test/build.test.mjs` |
| AC-2 | the old page is gone | integration | `node --test test/removal.test.mjs` |

## Assumptions to verify before implementation

- The parser keeps the note title. Verify by parsing one note in a scratch script.

## Open questions

- none
"""

GOOD = """# Backlog: lantern

## Feature: lantern (`T-lan`)

### Tasks

- T-lan-1: Spike: the parser keeps the note title
  Does: parses one note in a scratch script
  Delivers: REQ-1
  Touches: parser
  Depends on: none
  Check: parsing one note in a scratch script prints its title (design assumption)
  Size: L, because it is a spike
  Milestone: M1
- T-lan-2: Note loader
  Does: reads every note
  Delivers: REQ-1, NFR-1, AC-1
  Touches: loader
  Depends on: T-lan-1
  Check: `node --test test/build.test.mjs`; a note is published (verification plan: AC-1)
  Size: S, because one file
  Milestone: M1
- T-lan-3: Remove the old notes page
  Does: deletes the page
  Delivers: REQ-2, AC-2
  Touches: old page
  Depends on: T-lan-2
  Check: `node --test test/removal.test.mjs`; the old page is gone (verification plan: AC-2)
  Size: S, because one deletion
  Milestone: M2

### Milestones

- M1 notes publish: T-lan-1, T-lan-2 → usable state: notes are published
- M2 old page gone: T-lan-3 → usable state: only generated pages remain
"""


def lint(tmp_path, backlog: str, *extra: str, design: bool = True, feature: str | None = "lan"):
    (tmp_path / "backlog.md").write_text(backlog, encoding="utf-8")
    (tmp_path / "spec.md").write_text(SPEC, encoding="utf-8")
    (tmp_path / "design.md").write_text(DESIGN, encoding="utf-8")
    args = [sys.executable, str(LINT), "--backlog", str(tmp_path / "backlog.md"), "--spec", str(tmp_path / "spec.md")]
    if design:
        args += ["--design", str(tmp_path / "design.md")]
    if feature:
        args += ["--feature", feature]
    r = subprocess.run([*args, *extra], capture_output=True, text=True, timeout=60)
    return r, (json.loads(r.stdout) if r.stdout.strip() else None)


def errors_with(out, text):
    return [e for e in out["errors"] if text in e]


def test_good_backlog_passes_and_summary_states_the_counts(tmp_path):
    r, out = lint(tmp_path, GOOD)
    assert r.returncode == 0, out
    assert out["ok"] is True and out["errors"] == []
    assert out["summary"] == "lint_backlog: ok: true; errors: 0; tasks: 3; coverage: 5/5 (REQ 2/2, NFR 1/1, AC 2/2)"
    assert out["critical_path"] == ["T-lan-1", "T-lan-2", "T-lan-3"]
    assert out["spikes"] == ["T-lan-1"]
    assert out["coverage"]["AC"] == {"required": 2, "covered": 2}


def test_feature_is_detected_when_the_backlog_has_one(tmp_path):
    r, out = lint(tmp_path, GOOD, feature=None)
    assert r.returncode == 0 and out["feature"] == "lan"


def test_feature_is_required_when_the_backlog_has_two(tmp_path):
    r, out = lint(tmp_path, GOOD + "\n- T-oar-1: other\n  Does: x\n", feature=None)
    assert r.returncode == 2 and out is None
    assert "--feature is required" in r.stderr and "oar" in r.stderr


def test_help_and_usage_errors():
    r = subprocess.run([sys.executable, str(LINT), "--help"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "--design" in r.stdout
    r = subprocess.run([sys.executable, str(LINT), "--backlog", "x.md"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 2 and "required" in r.stderr


def test_the_bad_fixture_reports_its_six_findings():
    r = subprocess.run([sys.executable, str(LINT), "--backlog", str(FILES / "backlog-bad.md"),
                        "--spec", str(FILES / "spec-tiny.md")], capture_output=True, text=True, timeout=60)
    out = json.loads(r.stdout)
    assert r.returncode == 1 and out["ok"] is False
    assert out["summary"] == "lint_backlog: ok: false; errors: 6; tasks: 2; coverage: 1/5 (REQ 1/2, NFR 0/1, AC 0/2)"
    for text in ("dependency cycle", "REQ-9", "Check 'works'", "'big'", "'M3'", "delivered by no task"):
        assert errors_with(out, text), text


def test_vague_check_is_an_error_and_a_concrete_one_is_not(tmp_path):
    bad = GOOD.replace("Check: `node --test test/build.test.mjs`; a note is published (verification plan: AC-1)",
                       "Check: Works.")
    _, out = lint(tmp_path, bad, design=False)
    assert errors_with(out, "T-lan-2 Check 'Works.' is not a command")
    _, out = lint(tmp_path, GOOD, design=False)
    assert out["ok"] is True


def test_task_without_a_req_or_ac_id_is_an_error(tmp_path):
    _, out = lint(tmp_path, GOOD.replace("Delivers: REQ-1\n", "Delivers: none (de-risks NFR-1)\n"))
    assert errors_with(out, "T-lan-1 Delivers cites no REQ or AC id")


def test_spike_with_a_dependency_is_an_error(tmp_path):
    bad = GOOD.replace("  Touches: parser\n  Depends on: none", "  Touches: parser\n  Depends on: T-lan-2")
    _, out = lint(tmp_path, bad)
    assert errors_with(out, "T-lan-1 is a spike and must have 'Depends on: none'")


def test_task_that_can_start_before_a_spike_is_an_error(tmp_path):
    bad = GOOD.replace("  Touches: loader\n  Depends on: T-lan-1", "  Touches: loader\n  Depends on: none")
    _, out = lint(tmp_path, bad)
    assert errors_with(out, "can start before any spike is done")
    assert "T-lan-2" in errors_with(out, "can start before any spike")[0]


def test_no_spike_rule_when_the_backlog_has_no_spike(tmp_path):
    no_spike = GOOD.replace("Spike: the parser keeps the note title", "Parser check").replace(
        " (design assumption)", "")
    _, out = lint(tmp_path, no_spike, design=False)
    assert not errors_with(out, "spike")


def test_removal_without_a_dependency_is_an_error(tmp_path):
    bad = GOOD.replace("  Touches: old page\n  Depends on: T-lan-2", "  Touches: old page\n  Depends on: none")
    _, out = lint(tmp_path, bad)
    assert errors_with(out, "T-lan-3 is a removal and must depend")


def test_design_requires_one_spike_per_assumption(tmp_path):
    bad = GOOD.replace("Spike: the parser keeps the note title", "Parser check").replace(
        "(design assumption)", "(verification plan: AC-1) `node --test test/build.test.mjs`")
    _, out = lint(tmp_path, bad)
    assert errors_with(out, "the design lists 1 assumptions to verify but the backlog has 0")


def test_check_origin_is_required_with_a_design(tmp_path):
    bad = GOOD.replace("; a note is published (verification plan: AC-1)", "; a note is published")
    _, out = lint(tmp_path, bad)
    assert errors_with(out, "T-lan-2 Check must end with its origin")
    _, out = lint(tmp_path, bad, design=False)
    assert out["ok"] is True


def test_check_must_carry_the_command_of_the_row_it_cites(tmp_path):
    bad = GOOD.replace("`node --test test/build.test.mjs`; a note is published", "`node --test test/load.test.mjs`")
    _, out = lint(tmp_path, bad)
    assert errors_with(out, "T-lan-2 Check cites verification plan AC-1 but lacks its command")


def test_check_citing_an_ac_without_a_plan_row_is_an_error(tmp_path):
    design = DESIGN.replace("| AC-2 | the old page is gone | integration | `node --test test/removal.test.mjs` |\n", "")
    (tmp_path / "d2.md").write_text(design, encoding="utf-8")
    (tmp_path / "backlog.md").write_text(GOOD, encoding="utf-8")
    (tmp_path / "spec.md").write_text(SPEC, encoding="utf-8")
    r = subprocess.run([sys.executable, str(LINT), "--backlog", str(tmp_path / "backlog.md"), "--spec",
                        str(tmp_path / "spec.md"), "--design", str(tmp_path / "d2.md")],
                       capture_output=True, text=True, timeout=60)
    assert errors_with(json.loads(r.stdout), "T-lan-3 Check cites AC-2, which has no row")


def test_design_assumption_origin_on_a_task_that_is_not_a_spike(tmp_path):
    bad = GOOD.replace("`node --test test/build.test.mjs`; a note is published (verification plan: AC-1)",
                       "a note is published (design assumption)")
    _, out = lint(tmp_path, bad)
    assert errors_with(out, "T-lan-2 Check cites '(design assumption)' but the task is not titled")


def test_duration_in_size_is_an_error(tmp_path):
    _, out = lint(tmp_path, GOOD.replace("Size: S, because one file", "Size: S, because it takes 2 days"))
    assert errors_with(out, "T-lan-2 Size: carries a duration or a date")


def test_duplicate_task_id_is_an_error(tmp_path):
    dup = GOOD.replace("- T-lan-3: Remove the old notes page", "- T-lan-2: Remove the old notes page")
    _, out = lint(tmp_path, dup)
    assert errors_with(out, "T-lan-2 is defined more than once")
