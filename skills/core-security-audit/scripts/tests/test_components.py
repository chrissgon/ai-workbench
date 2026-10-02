"""Tests for skills/core-security-audit/scripts/components.py: the component list, the slices and the skill mode.

Run: uv run --with pytest pytest skills/core-security-audit/scripts/tests

Offline; every skill, agent and provider below is fictional.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "components.py"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60)


def write(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def workbench(root: Path) -> Path:
    write(root / "skills/biz-pricing/SKILL.md")
    write(root / "skills/eng-linting/SKILL.md")
    write(root / "skills/eng-linting/scripts/lint.py")
    write(root / "skills/eng-linting/references/rules.md")
    write(root / "skills/not-a-skill/notes.md")
    write(root / "agents/reviewer.md")
    write(root / "agents/README.md")
    write(root / "scripts/validate.py")
    write(root / "scripts/tests/test_validate.py")
    write(root / ".githooks/pre-commit")
    write(root / ".github/workflows/checks.yml")
    write(root / "providers/store/local.py")
    write(root / "adapters/demo/install.sh")
    write(root / "adapters/demo/overrides/reviewer.yaml")
    return root


def test_help_exits_zero_and_names_both_modes():
    r = run("--help")
    assert r.returncode == 0
    assert "--root" in r.stdout and "--skill" in r.stdout


def test_workbench_mode_lists_every_kind_of_component(tmp_path):
    r = run("--root", str(workbench(tmp_path)))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["mode"] == "workbench"
    assert out["counts"] == {"skill": 2, "agent": 1, "script": 1, "hook": 1, "ci": 1, "provider": 1, "adapter": 1,
                             "agent-override": 1}
    skills = {c["name"]: c for c in out["components"] if c["kind"] == "skill"}
    assert skills["eng-linting"]["prefix"] == "eng" and skills["eng-linting"]["files"] == 3
    assert skills["eng-linting"]["scripts"] == ["scripts/lint.py"]
    names = {c["name"] for c in out["components"]}
    assert "README.md" not in names and "tests/test_validate.py" not in names and "not-a-skill" not in names


def test_skills_are_sliced_by_prefix_and_the_rest_is_the_last_slice(tmp_path):
    out = json.loads(run("--root", str(workbench(tmp_path)), "--slices", "3").stdout)
    slices = out["slices"]
    assert [s["id"] for s in slices] == ["A", "B", "C"]
    assert sorted(s["prefixes"][0] for s in slices[:2]) == ["biz", "eng"]
    assert sorted(n for s in slices[:2] for n in s["components"]) == ["biz-pricing", "eng-linting"]
    assert slices[2]["prefixes"] == [] and "agents/reviewer.md" in slices[2]["components"]
    one = json.loads(run("--root", str(tmp_path), "--slices", "1").stdout)["slices"]
    assert sorted(one[0]["components"]) == ["biz-pricing", "eng-linting"] and len(one) == 2


def test_skill_mode_marks_scripts_hidden_files_and_links(tmp_path):
    skill = tmp_path / "eng-linting"
    write(skill / "SKILL.md")
    write(skill / "scripts/lint.sh")
    write(skill / ".hidden/notes.md")
    (skill / "link.md").symlink_to(skill / "SKILL.md")
    r = run("--skill", str(skill))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["mode"] == "skill" and out["has_skill_md"] is True
    assert out["scripts"] == ["scripts/lint.sh"]
    assert out["hidden"] == [".hidden/notes.md"]
    assert out["links"] == ["link.md"]
    write(tmp_path / "loose/readme.md")
    assert json.loads(run("--skill", str(tmp_path / "loose")).stdout)["has_skill_md"] is False


def test_bad_arguments_exit_two(tmp_path):
    for args in (["--root", str(tmp_path / "missing")], ["--root", str(tmp_path), "--slices", "0"],
                 ["--root", str(tmp_path), "--slices", "27"], [], ["--root", str(tmp_path), "--skill", str(tmp_path)]):
        r = run(*args)
        assert r.returncode == 2, (args, r.stderr)
        assert r.stdout == ""
