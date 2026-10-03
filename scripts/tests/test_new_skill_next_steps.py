"""The scaffold, the templates and AGENTS.md speak the reliability model, not the three old states.

The scaffold is run on a copy (the script and templates/ in a temporary folder), so nothing is
created under skills/.

Run: uv run --with pytest pytest scripts/tests/test_new_skill_next_steps.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
THREE_PART = re.compile(r'^  version: "(\d+\.\d+\.\d+)"$', re.MULTILINE)
OLD_STATES = ("`draft`", "`evaluated`", "`stale`")


@pytest.fixture
def workbench(tmp_path):
    (tmp_path / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "new-skill.sh", tmp_path / "scripts" / "new-skill.sh")
    shutil.copytree(ROOT / "templates", tmp_path / "templates")
    return tmp_path


def scaffold(workbench, *args):
    return subprocess.run(["bash", str(workbench / "scripts" / "new-skill.sh"), *args],
                          capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("name", ["agent.md", "capability.SKILL.md", "flow.SKILL.md"])
def test_every_template_starts_at_a_three_part_version(name):
    assert THREE_PART.findall((ROOT / "templates" / name).read_text(encoding="utf-8")) == ["0.1.0"]


@pytest.mark.parametrize("name, kind, area", [("eng-demo-thing", "capability", "engineering"),
                                              ("flow-demo-thing", "flow", "core")])
def test_a_scaffolded_skill_has_a_three_part_version_and_is_told_the_next_steps(workbench, name, kind, area):
    done = scaffold(workbench, "--name", name, "--kind", kind, "--area", area)
    assert done.returncode == 0, done.stderr
    skill = (workbench / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    assert THREE_PART.findall(skill) == ["0.1.0"]
    assert json.loads((workbench / "skills" / name / "evals" / "evals.json").read_text())["skill_name"] == name
    lines = done.stdout.strip().splitlines()
    assert len(lines) == 1, "the scaffold prints one JSON line"
    message = json.loads(lines[0])
    assert message["created"] == f"skills/{name}/SKILL.md"
    steps = message["next"]
    cases = next(i for i, step in enumerate(steps) if "evals.json" in step)
    full_test = next(i for i, step in enumerate(steps) if "first full test" in step)
    assert cases < full_test, "the cases come before the first full test"
    version_line = next(i for i, step in enumerate(steps) if f"python3 evals/eval_status.py bump --skill {name}" in step)
    assert version_line < full_test and "no class" in steps[version_line] and "after the last edit" in steps[version_line]
    assert f"python3 evals/eval_run.py --skill {name} --check-cases" in steps[cases]
    assert f"python3 evals/eval_run.py --skill {name} " in steps[full_test] and "done" in steps[full_test]
    assert any("scripts/validate.py" in step for step in steps)
    assert not [state for state in ("draft", "evaluated", "stale") if state in done.stdout]


def test_dry_run_creates_nothing(workbench):
    done = scaffold(workbench, "--name", "eng-demo-thing", "--kind", "capability", "--area", "engineering", "--dry-run")
    assert done.returncode == 0 and json.loads(done.stdout)["would_create"] == "skills/eng-demo-thing/SKILL.md"
    assert not (workbench / "skills").exists()


def test_agents_md_states_the_model_and_names_the_old_states_in_one_sentence_at_most():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for term in ("reference model", "full test", "partial test", "pessimistic score", "`needs a test`", "`watch`",
                 "`reliable`", "guard:<effect>", "eval_status.py bump --skill <name> --class x|y|z",
                 "evals/evidence/lab-<test id>.jsonl", "versions.jsonl", "measurement fingerprint", "scripts/evidence.py"):
        assert term in text, f"AGENTS.md does not state {term!r}"
    naming = [line for line in text.splitlines() if any(state in line for state in OLD_STATES)]
    # The transition sentence, until the tools of the model have merged; nothing else may describe the old states.
    assert len(naming) <= 1, naming
    assert "invented numbers" not in text
    assert 'version: "0.1.0"' in text and 'version: "0.1"\n' not in text
