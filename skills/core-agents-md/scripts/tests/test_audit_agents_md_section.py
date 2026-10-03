"""Tests for skills/core-agents-md/scripts/audit_agents_md.py: --fix never edits the workbench section, what the
check finds inside it is reported apart, and a value flag given last is a usage error. Offline, fictional data.

Run: uv run --with pytest pytest skills/core-agents-md/scripts/tests
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
AUDIT = ROOT / "skills/core-agents-md/scripts/audit_agents_md.py"
PACKAGE = {"name": "@acme/widgets", "scripts": {"build": "vite build", "test": "vitest run"}}
BLOCK = """<!-- workbench:start -->
## Working with the AI workbench
Before pushing, the owner's block says to run `bun run tests` and read `docs/ARCH.md`.
<!-- workbench:end -->
"""
AGENTS = "# Widgets\n\nRun `bun run tests` before pushing. See `docs/ARCH.md`.\n\n" + BLOCK


def run(*args):
    r = subprocess.run([sys.executable, str(AUDIT), *args], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def project(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps(PACKAGE), encoding="utf-8")
    (tmp_path / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(AGENTS, encoding="utf-8")
    (tmp_path / "baseline.md").write_text(AGENTS, encoding="utf-8")
    return tmp_path


def test_fix_changes_the_text_outside_the_section_and_never_the_section(tmp_path):
    root = project(tmp_path)
    rc, out, err = run("--root", str(root), "--audit", str(root / "AGENTS.md"), "--fix",
                       "--baseline", str(root / "baseline.md"))
    data = json.loads(out)
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    assert "Run `bun run test` before pushing. See `ARCHITECTURE.md`." in text
    assert text.endswith(BLOCK), "the workbench section is byte for byte what it was"
    assert {f["from"] for f in data["fixed"]} == {"bun run tests", "docs/ARCH.md"}
    assert data["workbench_section"] == "unchanged"
    assert data["ok"] is True and rc == 0, err
    spans = {(p["kind"], p["span"]) for p in data["in_workbench_section"]["not_fixed"]}
    assert spans == {("command", "bun run tests"), ("path", "docs/ARCH.md")}
    assert data["in_workbench_section"]["owner"] == "core-project-init"


def test_a_problem_only_inside_the_section_does_not_fail_the_audit(tmp_path):
    root = project(tmp_path)
    (root / "AGENTS.md").write_text("# Widgets\n\nRun `bun run test` before pushing.\n\n" + BLOCK, encoding="utf-8")
    rc, out, _ = run("--root", str(root), "--audit", str(root / "AGENTS.md"))
    data = json.loads(out)
    assert rc == 0 and data["ok"] is True
    assert data["unknown_commands"] == [] and data["missing_paths"] == []
    assert len(data["in_workbench_section"]["not_fixed"]) == 2


@pytest.mark.parametrize("flag", ["--root", "--audit", "--baseline"])
def test_a_value_flag_given_last_exits_2_with_a_message(tmp_path, flag):
    root = project(tmp_path)
    args = {"--root": ["--detect", "--root"],
            "--audit": ["--root", str(root), "--audit"],
            "--baseline": ["--root", str(root), "--audit", str(root / "AGENTS.md"), "--baseline"]}[flag]
    rc, out, err = run(*args)
    assert rc == 2 and out == ""
    assert f"Error: {flag} needs a value. See --help." in err
    assert "Traceback" not in err


def test_no_argument_prints_the_usage_on_stderr():
    rc, out, err = run()
    assert rc == 2 and out == "" and "Usage:" in err
