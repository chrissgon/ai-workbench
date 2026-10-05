"""Tests of the runtime manifest of a skill (runtime/manifest.py): every skill of a pack in use has a well-formed
one, a manifest that is not well formed is refused with every problem named, a skill without one does not
run, and the manifest stays outside the skill's content hash and outside every run. Offline: the real
repository for the manifests of the packs in use, the stand-in tree (runtime/tests/standin_tree.py) for runs.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_runtime_manifest.py
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

import standin_tree as st

lab = st.load("lab")
ops = st.load("ops")
manifest = st.load("manifest")
skill_meta = st.load("skill_meta")

REPO = st.REPO


@pytest.fixture
def tree(tmp_path, monkeypatch):
    built = st.build(tmp_path, monkeypatch, lab)
    monkeypatch.setattr(ops, "ROOT", str(built["tree"]))
    return built


def test_every_skill_of_a_pack_in_use_has_a_runtime_manifest_that_is_well_formed():
    names = manifest.skills_in_use(str(REPO))
    assert names, "no skill is in a pack in use"
    for name in names:
        assert manifest.load(str(REPO), name)["skill"] == name


def test_every_skill_a_flow_file_names_is_in_a_pack_in_use():
    in_use = set(manifest.skills_in_use(str(REPO)))
    named = {task["skill"] for flow in sorted((REPO / "flows").glob("*.json"))
             for task in json.loads(flow.read_text(encoding="utf-8"))["tasks"] if "skill" in task}
    assert named and named <= in_use, sorted(named - in_use)


SIDE_EFFECT_FREE = "biz-market-analysis"


def _good() -> dict:
    return json.loads(Path(manifest.path(str(REPO), SIDE_EFFECT_FREE)).read_text(encoding="utf-8"))


def _missing_key(m):
    del m["machine_files"]


def _unknown_key(m):
    m["web"] = True


def _wrong_skill(m):
    m["skill"] = "biz-icp-positioning"


def _not_an_output(m):
    m["documents"][0]["path"] = "docs/business/icp.md"


def _not_a_script(m):
    m["documents"][0]["checks"] = [["../lint_market.py", "--file", "{path}"]]


def _platform(m):
    m["documents"][0]["platform"] = "both"


def _gate(m):
    m["gate"] = {"effect": "publish", "payload_file": "docs/x.md"}


CHANGES = [(_missing_key, "machine_files"), (_unknown_key, "`web`"), (_wrong_skill, "biz-icp-positioning"),
           (_not_an_output, "docs/business/icp.md"), (_not_a_script, "../lint_market.py"), (_platform, "both"),
           (_gate, "`gate`")]


@pytest.mark.parametrize("change, named", CHANGES, ids=[c[0].__name__.strip("_") for c in CHANGES])
def test_a_manifest_that_is_not_well_formed_is_refused_with_every_problem_named(change, named):
    skill_dir = str(REPO / "skills" / SIDE_EFFECT_FREE)
    declared = skill_meta.declared(skill_dir)
    assert manifest.problems(_good(), declared, skill_dir) == []
    data = _good()
    change(data)
    found = manifest.problems(data, declared, skill_dir)
    assert len(found) == 1 and named in found[0], found
    # Two changes at once: both are named.
    other = _platform if change is not _platform else _unknown_key
    both = _good()
    change(both)
    other(both)
    assert len(manifest.problems(both, declared, skill_dir)) == 2


def test_a_skill_without_a_manifest_does_not_run(tree):
    path = str(tree["project"])
    os.remove(manifest.path(str(tree["tree"]), "demo-asks"))
    ops.request(path, "Tell me which market to go after first.", "demo")
    with pytest.raises(ops.OpsError) as raised:
        ops.run_next(path)
    assert "runtime manifest" in str(raised.value)
    task = ops.status(path)["requests"][0]["tasks"][0]
    assert task["state"] == "failed" and task["note"].startswith("the run could not start:")
    assert st.calls(tree["adapter"]) == []


def test_the_asking_openings_of_a_manifest_are_the_first_line_of_the_skills_asking_template():
    for name in manifest.skills_in_use(str(REPO)):
        text = (REPO / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert manifest.load(str(REPO), name)["asking_openings"] == manifest.asking_openings_of(text), name


def test_every_checker_a_manifest_names_is_a_script_of_the_skill_and_is_named_in_its_text():
    for name in manifest.skills_in_use(str(REPO)):
        folder = REPO / "skills" / name
        text = (folder / "SKILL.md").read_text(encoding="utf-8")
        for document in manifest.load(str(REPO), name)["documents"]:
            for check in document["checks"]:
                assert (folder / "scripts" / check[0]).is_file(), (name, check)
                assert check[0] in text, (name, check)


def test_the_manifest_is_outside_the_content_hash_and_never_enters_a_run(tree):
    before = lab.skill_identity("demo-asks")["content_sha256"]
    file = Path(manifest.path(str(tree["tree"]), "demo-asks"))
    data = json.loads(file.read_text(encoding="utf-8"))
    changed = copy.deepcopy(data)
    changed["asking_openings"] = ["Nothing was decided yet"]
    file.write_text(json.dumps(changed), encoding="utf-8")
    assert lab.skill_identity("demo-asks")["content_sha256"] == before
    path = str(tree["project"])
    ops.request(path, "Tell me which market to go after first.", "demo")
    out = ops.run_next(path)
    assert out["status"] == "ok"
    cwd = os.path.join(out["run_dir"], "cwd")
    found = [os.path.join(folder, n) for folder, _, names in os.walk(cwd) for n in names if n == "runtime-manifest.json"]
    assert found == []
