"""The workbench's tools run in the folders the eval cases build, with no model.

A case may bring files of this repository into its folder ("workbench_files"): the scaffold, the validator,
the security scan, the eval runner and the status script, for a skill whose job is the workbench itself. In
that folder the tools find only what the case brings. A change that makes one of them read a file the cases
do not bring would break the case for every model, and nothing but a paid run would show it.

So this test builds, with the runner's own build_tree, the folder of every case that brings repository
files, and does there what those cases ask a model to do: scaffold a capability and a flow from the
templates, fill them to the smallest valid skill, and run the scaffold, the validator, the scan, the case
preflight, the runner's plan and the status script. Every command must end without a traceback, and the
validator and the scan with zero errors on what was made.

When it fails after a change to one of those tools, the fix is one of two: add the file the tool now reads
to the cases' "workbench_files", or make the rule skip with a message when its file is absent.

Run: uv run --with pytest pytest evals/tests/test_case_folders.py
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "eval_run.py"
spec = importlib.util.spec_from_file_location("eval_run_case_folders", SCRIPT)
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)
REPO = Path(er.ROOT)

CAPABILITY, FLOW = "eng-case-folder-probe", "flow-case-folder-probe"
# The variables git exports to a hook would point the tools at this repository instead of the case folder.
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def cases_that_bring_repository_files():
    found = []
    for path in sorted(glob.glob(str(REPO / "skills" / "*" / "evals" / "evals.json"))):
        skill = Path(path).parents[1].name
        for case in json.loads(Path(path).read_text(encoding="utf-8")).get("evals") or []:
            if case.get("workbench_files"):
                found.append(pytest.param(skill, case, id=f"{skill}-case-{case.get('id')}"))
    return found


CASES = cases_that_bring_repository_files()


def run(folder, *cmd):
    """Run one command in the case folder; no traceback is ever acceptable."""
    r = subprocess.run(list(cmd), cwd=folder, env=ENV, capture_output=True, text=True, timeout=300)
    assert "Traceback (most recent call last)" not in r.stderr + r.stdout, f"{' '.join(cmd)}\n{r.stderr[-3000:]}"
    return r


def python(folder, *args):
    return run(folder, sys.executable, *args)


def fill(folder, name):
    """Turn the scaffold's SKILL.md into the smallest valid skill, as the template's own instructions say:
    fill the placeholders, delete the section that does not apply. Then two cases of three assertions."""
    path = folder / "skills" / name / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    text = text.split("\n## Confirmation gate\n")[0].rstrip("\n") + "\n"
    text = re.sub(r"__[A-Z_]+__", "the probe", text)
    path.write_text(text, encoding="utf-8")
    cases = [{"id": i, "prompt": prompt, "expected_output": "A short report.", "files": [],
              "assertions": ["The reply names the change it reviewed", "The reply asks one question",
                             "The reply is in English, the language of the prompt"]}
             for i, prompt in ((1, "Look at the last change and tell me what it does."),
                               (2, "Something is off with the last change. What do you need from me?"))]
    (folder / "skills" / name / "evals" / "evals.json").write_text(
        json.dumps({"skill_name": name, "evals": cases}, indent=2) + "\n", encoding="utf-8")


def test_some_case_brings_repository_files():
    """If no case brings repository files any more, this file tests nothing: remove it with the feature."""
    assert CASES


@pytest.mark.parametrize("skill, case", CASES)
def test_the_tools_run_in_the_folder_the_case_builds(tmp_path, skill, case):
    folder = tmp_path / "case"
    folder.mkdir()
    skill_dir = str(REPO / "skills" / skill)
    er.build_tree(str(folder), er.case_files(skill_dir, case), case)
    assert not (folder / ".git").exists()
    brought = {Path(rel).as_posix() for _, rel in er.workbench_files(case)}
    for tool in ("scripts/new-skill.sh", "scripts/validate.py", "scripts/security_scan.py", "evals/eval_run.py",
                 "evals/eval_status.py", "templates"):
        assert tool in brought, f"the case no longer brings {tool}; this test runs it"

    # What the fixture ships is not this test's subject: a fixture may hold a skill with a planted defect.
    shipped = sorted(p.name for p in (folder / "skills").iterdir()) if (folder / "skills").is_dir() else []
    assert CAPABILITY not in shipped and FLOW not in shipped

    # The scaffold.
    r = run(folder, "bash", "scripts/new-skill.sh", "--help")
    assert r.returncode == 0 and "--name" in r.stdout
    r = run(folder, "bash", "scripts/new-skill.sh", "--name", CAPABILITY, "--kind", "capability", "--area", "engineering", "--dry-run")
    assert r.returncode == 0 and json.loads(r.stdout)["would_create"] == f"skills/{CAPABILITY}/SKILL.md"
    for name, kind, area in ((CAPABILITY, "capability", "engineering"), (FLOW, "flow", "core")):
        r = run(folder, "bash", "scripts/new-skill.sh", "--name", name, "--kind", kind, "--area", area)
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout)["created"] == f"skills/{name}/SKILL.md"

    # Straight from the template a skill is not valid, and the validator says so without failing itself.
    r = python(folder, "scripts/validate.py", "--json")
    raw = [e for e in json.loads(r.stdout)["errors"] if e["where"].split("/")[1:2] in ([CAPABILITY], [FLOW])]
    assert r.returncode == 1 and any("placeholders" in e["message"] for e in raw)

    for name in (CAPABILITY, FLOW):
        fill(folder, name)

    # The status script: the generated table first, as the skill's procedure says, then the readings.
    assert python(folder, "evals/eval_status.py", "--help").returncode == 0
    r = python(folder, "evals/eval_status.py", "inventory", "--write")
    assert r.returncode == 0, r.stderr
    r = python(folder, "evals/eval_status.py", "inventory", "--check")
    assert r.returncode == 0 and json.loads(r.stdout) == {"current": True}
    r = python(folder, "evals/eval_status.py", "status")
    assert r.returncode == 0, r.stderr
    bands = {s["skill"]: s["band"] for s in json.loads(r.stdout)["skills"]}
    assert bands[CAPABILITY] == bands[FLOW] == "needs a test" and set(bands) == set(shipped) | {CAPABILITY, FLOW}
    for name in (CAPABILITY, FLOW):
        r = python(folder, "evals/eval_status.py", "status", "--skill", name)
        row = json.loads(r.stdout)["skills"][0]
        assert r.returncode == 0 and row["band"] == "needs a test" and row["command"].endswith(f"--skill {name}"), r.stderr

    # The validator: zero errors on what was made, in a tree with no other skill (or only the fixture's), once each
    # new skill has its first version line (step 9 of the skill: the version-bump rule is an error since phase C).
    for name in (CAPABILITY, FLOW):
        r = python(folder, "evals/eval_status.py", "bump", "--skill", name)
        assert r.returncode == 0 and json.loads(r.stdout)["class"] == "new", r.stderr
    assert python(folder, "scripts/validate.py", "--help").returncode == 0
    r = python(folder, "scripts/validate.py", "--json")
    report = json.loads(r.stdout)
    # A rule that lists several skills on one line (version-bump) is the fixture's when it lists only shipped skills.
    fixtures_only = lambda e: e["where"] == "skills" and set(e["message"].rsplit(": ", 1)[-1].split(", ")) <= set(shipped)
    ours = [e for e in report["errors"] if e["where"].split("/")[1:2] not in [[s] for s in shipped] and not fixtures_only(e)]
    assert ours == [], ours
    assert report["summary"]["skills"] == len(shipped) + 2
    if not shipped:
        assert r.returncode == 0 and report["summary"] == {"skills": 2, "errors": 0, "ok": True,
                                                         "warnings": report["summary"]["warnings"]}
    # A rule whose file the case does not bring is skipped and says so; it is never an error or a traceback.
    assert all(line.split("skipped: ")[1] for line in r.stderr.splitlines() if line.startswith("NOTE"))
    assert python(folder, "scripts/validate.py", "--flags").returncode == r.returncode

    # The security scan, on the tree and on one skill, as the skill's security step asks.
    assert python(folder, "scripts/security_scan.py", "--help").returncode == 0
    for target in ((), (f"skills/{CAPABILITY}",), (f"skills/{FLOW}",)):
        r = python(folder, "scripts/security_scan.py", *target, "--json")
        summary = json.loads(r.stdout)["summary"]
        assert r.returncode == 0 and summary["errors"] == 0 and summary["files"] > 0, r.stderr

    # The runner without a model: its help, the case preflight, and the plan. With no gate configuration in
    # the folder the plan answers that the harness is required, exit 2: the skill's procedure stops there.
    assert python(folder, "evals/eval_run.py", "--help").returncode == 0
    for name in (CAPABILITY, FLOW):
        r = python(folder, "evals/eval_run.py", "--skill", name, "--check-cases")
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout) == {"skill": name, "cases": 2, "errors": [], "unchecked": []}
        r = python(folder, "evals/eval_run.py", "--skill", name, "--dry-run")
        assert r.returncode == 2 and "--harness" in r.stderr, r.stderr
        r = python(folder, "evals/eval_run.py", "--skill", name, "--harness", "agents-dir", "--model", "a-model", "--dry-run")
        assert r.returncode == 0, r.stderr

    # Nothing above wrote outside the case folder's own places.
    assert sorted(p.name for p in (folder / "skills").iterdir()) == sorted(shipped + [CAPABILITY, FLOW])
