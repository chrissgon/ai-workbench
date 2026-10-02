"""Tests for skills/biz-icp-positioning/scripts/lint_icp.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/biz-icp-positioning/scripts/tests
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


LINT_ICP = "skills/biz-icp-positioning/scripts/lint_icp.py"


def test_lint_icp_reports_hypotheticals_criteria_and_status(tmp_path):
    doc = tmp_path / "icp.md"
    doc.write_text("# ICP\n\n- Status: draft\n\n## Primary profile\n- 40% no-show\n\n"
                   "## Validation plan\n- Would you pay for this?\n- Validated if: 3 of 5 name the same task\n\n"
                   "## Sources\n[1] x\n", encoding="utf-8")
    r = run(LINT_ICP, "--file", str(doc), "--kind", "icp")
    assert r.returncode == 1
    checks = sorted(f["check"] for f in json.loads(r.stdout)["findings"])
    assert checks == ["hypothetical_question", "missing_criteria", "status", "uncited_figure"]


def test_lint_icp_positioning_needs_confirmed_claims(tmp_path):
    doc = tmp_path / "positioning.md"
    doc.write_text("- Status: hypothesis\n\n## What we can truly claim\n| Attribute | Against | Why | Confirmed by |\n"
                   "|---|---|---|---|\n| Independent | vendors | trust | user, 2026-09-28 |\n| Best in class | all | - | |\n",
                   encoding="utf-8")
    found = json.loads(run(LINT_ICP, "--file", str(doc), "--kind", "positioning").stdout)["findings"]
    assert [f["check"] for f in found] == ["unconfirmed_claim"]
    assert "Best in class" in found[0]["text"]
