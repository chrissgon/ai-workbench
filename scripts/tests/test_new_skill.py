"""Tests for the scaffold, scripts/new-skill.sh: what it creates and what it refuses.

Run: uv run --with pytest pytest scripts/tests/test_new_skill.py

The script runs inside a small copy of the workbench in a temporary folder (the script, the templates),
so nothing is created in this checkout. Every skill name here is invented.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")

# The table of scripts/validate.py (PREFIX_TO_AREA), which the scaffold repeats in shell.
PREFIX_AREA = {"biz": "business", "product": "product", "brand": "brand", "design": "design", "eng": "engineering",
               "ops": "delivery", "mkt": "marketing", "ai": "ai", "core": "core", "asst": "assistant"}


@pytest.fixture
def wb(tmp_path):
    (tmp_path / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "new-skill.sh", tmp_path / "scripts" / "new-skill.sh")
    shutil.copytree(ROOT / "templates", tmp_path / "templates")
    return tmp_path


def scaffold(wb: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([BASH, str(wb / "scripts" / "new-skill.sh"), *args], capture_output=True, text=True,
                          env={"PATH": os.environ["PATH"], "HOME": str(wb)}, timeout=60)


def test_a_capability_is_created_from_its_template(wb):
    r = scaffold(wb, "--name", "eng-demo-check", "--kind", "capability", "--area", "engineering")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["created"] == "skills/eng-demo-check/SKILL.md"
    text = (wb / "skills" / "eng-demo-check" / "SKILL.md").read_text(encoding="utf-8")
    assert "name: eng-demo-check\n" in text and "  area: engineering\n" in text and "  kind: capability\n" in text
    assert "# Demo check\n" in text
    assert "__NAME__" not in text and "__AREA__" not in text and "__TITLE__" not in text
    cases = json.loads((wb / "skills" / "eng-demo-check" / "evals" / "evals.json").read_text(encoding="utf-8"))
    assert cases == {"skill_name": "eng-demo-check", "evals": []}


def test_a_flow_is_created_from_the_flow_template_in_any_area(wb):
    for name, area in (("flow-demo-launch", "core"), ("flow-demo-campaign", "marketing")):
        r = scaffold(wb, "--name", name, "--kind", "flow", "--area", area)
        assert r.returncode == 0, r.stderr
        text = (wb / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert f"name: {name}\n" in text and f"  area: {area}\n" in text and "  kind: flow\n" in text


def test_dry_run_prints_the_plan_and_creates_nothing(wb):
    r = scaffold(wb, "--name", "mkt-demo-post", "--kind", "capability", "--area", "marketing", "--dry-run")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"would_create": "skills/mkt-demo-post/SKILL.md", "kind": "capability",
                                    "area": "marketing", "template": "templates/capability.SKILL.md"}
    assert not (wb / "skills").exists()


def test_every_prefix_is_accepted_with_its_own_area_and_refused_with_another(wb):
    assert PREFIX_AREA == {k: v for k, v in _validate().PREFIX_TO_AREA.items() if v}
    for prefix, area in PREFIX_AREA.items():
        ok = scaffold(wb, "--name", f"{prefix}-demo-x", "--kind", "capability", "--area", area, "--dry-run")
        assert ok.returncode == 0, (prefix, ok.stderr)
        other = "marketing" if area != "marketing" else "business"
        bad = scaffold(wb, "--name", f"{prefix}-demo-x", "--kind", "capability", "--area", other, "--dry-run")
        assert bad.returncode == 2, prefix
        assert bad.stderr.strip() == f"Error: prefix {prefix}- implies --area {area}. Received: '{other}'"
        assert bad.stdout == ""
    assert not (wb / "skills").exists()


def _validate():
    import importlib.util
    spec = importlib.util.spec_from_file_location("validate_for_scaffold", ROOT / "scripts" / "validate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("args,message", [
    ([], "--name, --kind and --area are required"),
    (["--name", "eng-demo-x", "--kind", "capability"], "--name, --kind and --area are required"),
    (["--name", "Eng-Demo", "--kind", "capability", "--area", "engineering"], "name must be lowercase"),
    (["--name", "zzz-demo-x", "--kind", "capability", "--area", "engineering"], "is not an area prefix"),
    (["--name", "eng-demo-x", "--kind", "skill", "--area", "engineering"], "--kind must be capability or flow"),
    (["--name", "eng-demo-x", "--kind", "capability", "--area", "cooking"], "--area must be one of"),
    (["--name", "flow-demo-x", "--kind", "capability", "--area", "core"], "flow- prefix requires --kind flow"),
    (["--name", "eng-demo-x", "--kind", "flow", "--area", "engineering"], "--kind flow requires the flow- prefix"),
    (["--name", "eng-demo-x", "--kind", "capability", "--area", "engineering", "--force"], "unknown option '--force'"),
    (["--kind"], "--kind needs a value"),
])
def test_usage_errors_exit_2_with_a_message_and_create_nothing(wb, args, message):
    r = scaffold(wb, *args)
    assert r.returncode == 2 and r.stdout == ""
    assert r.stderr.startswith("Error: ") and message in r.stderr
    assert not (wb / "skills").exists()


def test_an_existing_skill_is_never_overwritten(wb):
    args = ("--name", "core-demo-notes", "--kind", "capability", "--area", "core")
    assert scaffold(wb, *args).returncode == 0
    target = wb / "skills" / "core-demo-notes" / "SKILL.md"
    target.write_text("filled in\n", encoding="utf-8")
    r = scaffold(wb, *args)
    assert r.returncode == 1 and "already exists" in r.stderr
    assert target.read_text(encoding="utf-8") == "filled in\n"
