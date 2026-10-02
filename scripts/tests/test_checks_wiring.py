"""Tests of the checks that keep other checks running: test-folder discovery and the eval-cases preflight
that scripts/validate.py runs. Offline; every skill and file here is invented.

Run: uv run --with pytest pytest scripts/tests/test_checks_wiring.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


test_dirs = load("test_dirs")
validate = load("validate")


def test_test_folders_are_discovered_and_fixture_folders_are_not(tmp_path):
    for folder in ("scripts/tests", "evals/tests", "providers/demo/tests", "adapters/demo/tests",
                   "skills/core-demo/scripts/tests", "skills/core-demo/evals/files/app/tests", "providers/empty/tests"):
        (tmp_path / folder).mkdir(parents=True)
        if "empty" not in folder:
            (tmp_path / folder / "test_x.py").write_text("def test_x():\n    assert True\n")
    assert test_dirs.test_dirs(str(tmp_path)) == ["scripts/tests", "evals/tests", "providers/demo/tests",
                                                  "adapters/demo/tests", "skills/core-demo/scripts/tests"]


def test_every_test_folder_of_this_repository_is_in_the_list_ci_runs():
    found = set(test_dirs.test_dirs())
    assert {"scripts/tests", "evals/tests"} <= found
    workflow = (REPO / ".github" / "workflows" / "checks.yml").read_text()
    assert "$(python3 scripts/test_dirs.py)" in workflow


HOOK_CASES = [
    (".githooks/pre-commit", "scripts/tests"), (".github/workflows/checks.yml", "scripts/tests"),
    ("packs/default.txt", "scripts/tests"), ("templates/agent.md", "scripts/tests"),
    ("agents/reviewer.md", "scripts/tests"), ("scripts/validate.py", "scripts/tests"),
    ("providers/resolve.py", "scripts/tests"), ("providers/store/sqlite.py", "providers/store/tests"),
    ("evals/eval_run.py", "evals/tests"), ("adapters/api/run_agent.py", "adapters/api/tests"),
    ("skills/core-demo/scripts/tool.py", "skills/core-demo/scripts/tests"),
    ("skills/core-demo/SKILL.md", None), ("docs/backlog.md", None), ("README.md", None),
]


def test_the_hook_maps_each_folder_to_the_tests_that_cover_it(tmp_path):
    """The hook's own `case` block, taken from the file and run on one path at a time."""
    hook = (REPO / ".githooks" / "pre-commit").read_text()
    start, end = hook.index('  case "$f" in'), hook.index("  esac\n") + len("  esac\n")
    block = hook[start:end].replace("*) continue ;;", '*) d="" ;;')
    script = tmp_path / "map.sh"
    script.write_text('set -euo pipefail\nf="$1"\n' + block + 'printf "%s" "$d"\n')
    for path, expected in HOOK_CASES:
        out = subprocess.run(["bash", str(script), path], capture_output=True, text=True,
                             env={"PATH": os.environ["PATH"]}, timeout=30)
        assert out.returncode == 0, out.stderr
        assert (out.stdout or None) == expected, path


def tree(tmp_path, cited):
    """A repository with the real runner and one skill whose case ships `shipped.md` and cites `cited`."""
    (tmp_path / "evals").mkdir()
    for name in ("eval_run.py", "eval_status.py", "grading-prompt.md"):
        shutil.copy(REPO / "evals" / name, tmp_path / "evals" / name)
    skill = tmp_path / "skills" / "core-demo"
    (skill / "evals" / "files").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: core-demo\n---\n# demo\n")
    (skill / "evals" / "files" / "shipped.md").write_text("shipped\n")
    (skill / "evals" / "evals.json").write_text(json.dumps({"skill_name": "core-demo", "evals": [
        {"id": 1, "prompt": f"Read `{cited}` and summarise it.", "files": ["evals/files/shipped.md"],
         "expected_output": "a summary", "assertions": ["The summary names the file."]}]}))
    return tmp_path


def errors_of(root):
    report = validate.Report()
    validate.check_eval_cases(report, root=str(root))
    return [f"{e['where']}: {e['message']}" for e in report.errors]


def test_validate_accepts_cases_whose_cited_files_are_shipped(tmp_path):
    assert errors_of(tree(tmp_path, "shipped.md")) == []


def test_validate_reports_a_case_that_cites_a_file_it_does_not_ship(tmp_path):
    errors = errors_of(tree(tmp_path, "docs/missing.md"))
    assert len(errors) == 1 and errors[0].startswith("skills/core-demo/evals/evals.json: [eval-cases]")
    assert "docs/missing.md" in errors[0] and "--check-cases" in errors[0]
