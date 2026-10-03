"""Tests for skills/eng-architecture/scripts/check_design.py: the findings, the --report file and the options.

Run: uv run --with pytest pytest skills/eng-architecture/scripts/tests/test_check_design.py

Offline; every product, feature and requirement below is fictional.
"""
from __future__ import annotations

import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path

CHECK = Path(__file__).resolve().parents[1] / "check_design.py"
FIXTURE = Path(__file__).resolve().parents[2] / "evals" / "files" / "trace-check"

SPEC = "docs/product/specs/expense-export.md"
DESIGN = "docs/engineering/designs/expense-export.md"
ADR_DIR = "docs/engineering/adr"
ADR = ADR_DIR + "/0001-export-file-format.md"
REPORT = "docs/engineering/designs/expense-export.check.json"


def project(tmp_path):
    """A copy of the eval fixture, laid out as the eval runner lays it out: the folder's content at the root."""
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    return tmp_path


def run(cwd, *extra, adr_dir=ADR_DIR):
    cmd = [sys.executable, str(CHECK), "--spec", SPEC, "--design", DESIGN]
    if adr_dir:
        cmd += ["--adr-dir", adr_dir]
    p = subprocess.run(cmd + list(extra), cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def fix(root, second_option=False):
    """The correct fix of the fixture: a component for REQ-2, a row for AC-2, and the ADR removed (or completed)."""
    design = root / DESIGN
    t = design.read_text(encoding="utf-8")
    t = t.replace("| ExportRoute | Reads", "| CsvSerializer | Turns expenses into sorted rows | src/server/export/csv.ts "
                  "| expenses | CSV text | REQ-2 |\n| ExportRoute | Reads")
    t = t.replace("| AC-3 | Export a month", "| AC-2 | Serialize three expenses out of order | unit | test/csv.test.ts |\n"
                  "| AC-3 | Export a month")
    if second_option:
        adr = root / ADR
        adr.write_text(adr.read_text(encoding="utf-8").replace(
            "## Decision", "### Option B: spreadsheet file\n- Consequences: needs a library.\n\n## Decision"),
            encoding="utf-8")
    else:
        t = t.replace("| engineering | ADR-0001 |", "| decided | spec REQ-3 |")
        (root / ADR).unlink()
    design.write_text(t, encoding="utf-8")


def test_fixture_reports_the_planted_findings(tmp_path):
    root = project(tmp_path)
    code, out, _ = run(root)
    result = json.loads(out)
    assert code == 1 and result["ok"] is False
    assert (result["spec_ids"], result["covered"]) == (8, 6)
    assert result["errors"] == [
        "ids from the spec not mentioned in the design: ['AC-2', 'REQ-2']",
        "acceptance criteria without a row in the verification plan: ['AC-2']",
        "0001-export-file-format.md: only 1 option(s)",
    ]


def test_fixture_passes_after_the_adr_is_removed(tmp_path):
    root = project(tmp_path)
    fix(root)
    code, out, _ = run(root)
    assert code == 0 and json.loads(out) == {"ok": True, "summary": "check_design ok: 8/8 ids covered, 0 ADR(s) valid",
                                             "spec_ids": 8, "covered": 8, "adrs": [], "errors": [], "warnings": []}


def test_fixture_passes_after_a_second_option(tmp_path):
    root = project(tmp_path)
    fix(root, second_option=True)
    code, out, _ = run(root)
    assert code == 0 and json.loads(out)["adrs"] == [{"file": "0001-export-file-format.md", "ok": True, "problems": []}]


def test_removed_adr_still_cited_is_an_error(tmp_path):
    root = project(tmp_path)
    fix(root, second_option=True)
    (root / ADR).unlink()
    code, out, _ = run(root)
    assert code == 1 and any("ADR-0001 referenced but no file" in e for e in json.loads(out)["errors"])


def test_default_output_is_one_line(tmp_path):
    root = project(tmp_path)
    _, out, _ = run(root)
    assert len(out.strip().splitlines()) == 1
    _, pretty, _ = run(root, "--json")
    assert len(pretty.strip().splitlines()) > 1 and json.loads(pretty) == json.loads(out)


def test_report_records_the_run_and_its_arguments(tmp_path):
    root = project(tmp_path)
    code, out, _ = run(root, "--report", REPORT)
    record = json.loads((root / REPORT).read_text(encoding="utf-8"))
    result = json.loads(out)
    assert code == 1
    assert set(record) == {"script", "date", "arguments", "ok", "summary", "errors", "warnings", "counts"}
    assert record["script"] == "check_design.py"
    assert record["ok"] is False and record["errors"] == result["errors"]
    assert record["summary"] == result["summary"]
    assert record["summary"] == "check_design FAILED: 3 error(s); 6/8 ids covered, 1 of 1 ADR(s) with problems"
    assert record["arguments"] == {"--spec": SPEC, "--design": DESIGN, "--adr-dir": ADR_DIR}
    assert record["date"] == datetime.date.today().isoformat()
    assert record["counts"] == {"spec_ids": 8, "covered": 6, "adrs": 1, "adrs_failed": 1}


def test_report_holds_the_last_run(tmp_path):
    root = project(tmp_path)
    run(root, "--report", REPORT)
    fix(root)
    code, _, _ = run(root, "--report", REPORT)
    record = json.loads((root / REPORT).read_text(encoding="utf-8"))
    assert code == 0 and record["ok"] is True and record["errors"] == [] and record["counts"]["covered"] == 8


def test_report_next_to_the_design_is_not_read_as_an_adr(tmp_path):
    root = project(tmp_path)
    fix(root)
    run(root, "--report", REPORT)
    code, out, _ = run(root, "--report", REPORT)
    assert code == 0 and json.loads(out)["adrs"] == []


def test_report_without_adr_dir_records_only_the_flags_given(tmp_path):
    root = project(tmp_path)
    run(root, "--report", REPORT, "--json", adr_dir=None)
    arguments = json.loads((root / REPORT).read_text(encoding="utf-8"))["arguments"]
    assert arguments == {"--spec": SPEC, "--design": DESIGN, "--json": True}


def test_report_that_cannot_be_written_is_a_usage_error(tmp_path):
    root = project(tmp_path)
    code, out, err = run(root, "--report", "no-such-folder/check.json")
    assert code == 2 and out == "" and "cannot write the report" in err


def test_option_without_a_value_is_a_usage_error(tmp_path):
    root = project(tmp_path)
    for flag in ("--report", "--adr-dir"):
        code, out, err = run(root, flag)
        assert code == 2 and out == "" and f"{flag} needs a value" in err


def test_help_names_the_report_option():
    p = subprocess.run([sys.executable, str(CHECK), "--help"], capture_output=True, text=True)
    assert p.returncode == 0 and "--report" in p.stdout


def test_no_arguments_prints_the_usage_on_stderr():
    p = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True)
    assert p.returncode == 2 and p.stdout == "" and "Usage:" in p.stderr


def test_usage_error_writes_no_report(tmp_path):
    root = project(tmp_path)
    code, _, _ = run(root, "--report", REPORT, "--no-such-flag")
    assert code == 2 and not (root / REPORT).exists()
