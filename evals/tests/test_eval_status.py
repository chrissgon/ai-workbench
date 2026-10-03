"""Offline tests of evals/eval_status.py (content hash, record, status, inventory block) and of the
eval-status check in scripts/validate.py. No model is called: benchmarks are written by hand here."""
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def load(name):
    folder = "evals" if name == "eval_status" else "scripts"
    spec = importlib.util.spec_from_file_location(name, REPO / folder / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


es = load("eval_status")
validate = load("validate")

INVENTORY = "# Inventory\n\n## Evaluation status\n\nIntro kept by hand.\n\n" + es.BEGIN + "\nold\n" + es.END + "\n\n## Progress\n"


@pytest.fixture
def root(tmp_path):
    for name in ("core-demo", "eng-other"):
        skill = tmp_path / "skills" / name
        (skill / "evals" / "files").mkdir(parents=True)
        (skill / "scripts").mkdir()
        (skill / "SKILL.md").write_text(f"# {name}\n")
        (skill / "scripts" / "check.py").write_text("print('ok')\n")
        (skill / "evals" / "files" / "input.md").write_text("fixture\n")
        (skill / "evals" / "evals.json").write_text(json.dumps({"evals": [
            {"id": 1, "prompt": "p", "assertions": ["a"]}, {"id": 2, "prompt": "q", "assertions": ["a"]}]}))
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "inventory.md").write_text(INVENTORY)
    return tmp_path


def record(root, skill="core-demo", strong=(1.0, 0.5), floor=(0.9, 0.3), cases=(1, 2), runs=1, complete=True, infra=0):
    """Write a record of the first round, as the runner wrote them then: nothing writes one any more, and the
    status still reads them until the bands replace it."""
    scores = {"strong_with": strong[0], "strong_without": strong[1], "floor_with": floor[0], "floor_without": floor[1]}
    rec = {"skill": skill, "content_sha256": es.content_hash(str(root / "skills" / skill)), "date": "2030-01-02", "iteration": 3,
           "runs": runs, "cases": list(cases), "harness": "h", "floor_harness": "fh", "models": {"strong": "s-model", "floor": "f-model"},
           "grader": "s-model", "threshold": 0.8, "scores": scores, "complete": complete, "infra_failures": infra,
           "measurement_version": 2, "tolerance": 0, "gate": es.gate(scores, 0.8, 0, 2)}
    (root / "skills" / skill / "evals" / "result.json").write_text(json.dumps(rec, indent=2) + "\n")
    return 0


def status(root, skill="core-demo"):
    return es.skill_status(str(root / "skills" / skill))["status"]


def test_the_hash_is_stable_and_ignores_the_record_and_caches(root):
    skill = root / "skills" / "core-demo"
    first = es.content_hash(str(skill))
    assert first == es.content_hash(str(skill)) and len(first) == 64
    (skill / "evals" / "result.json").write_text("{}")
    (skill / "scripts" / "__pycache__").mkdir()
    (skill / "scripts" / "__pycache__" / "check.cpython-311.pyc").write_text("x")
    (skill / "scripts" / "stray.pyc").write_text("x")
    (skill / ".DS_Store").write_text("x")
    (root / "skills" / "eng-other" / "SKILL.md").write_text("# changed elsewhere\n")
    (root / "outside.md").write_text("x")
    assert es.content_hash(str(skill)) == first


@pytest.mark.parametrize("rel", ["SKILL.md", "scripts/check.py"])
def test_the_hash_changes_with_any_file_a_model_reads(root, rel):
    skill = root / "skills" / "core-demo"
    first = es.content_hash(str(skill))
    (skill / rel).write_text((skill / rel).read_text() + "\n")
    assert es.content_hash(str(skill)) != first


def test_the_hash_leaves_out_all_of_evals_and_the_installers_marker(root):
    """No model that uses the skill reads its cases, its evidence, its version file or its old record."""
    skill = root / "skills" / "core-demo"
    first = es.content_hash(str(skill))
    (skill / "evals" / "evals.json").write_text(json.dumps({"evals": [{"id": 1, "prompt": "another prompt"}]}))
    (skill / "evals" / "files" / "input.md").write_text("another fixture\n")
    (skill / "evals" / "files" / "added.md").write_text("x\n")
    (skill / "evals" / "evidence").mkdir()
    (skill / "evals" / "evidence" / "lab-20300102T030405Z-0a1b2c3d.jsonl").write_text("{}\n")
    (skill / "evals" / "versions.jsonl").write_text("{}\n")
    (skill / "evals" / "result.json").write_text("{}")
    (skill / ".installed-by-ai-workbench").write_text("")  # a copy an installer made has the hash of its source
    (skill / "scripts" / ".pytest_cache").mkdir()
    (skill / "scripts" / ".pytest_cache" / "v").write_text("x")
    assert es.content_hash(str(skill)) == first
    # Only the evals folder of the skill itself, and only the marker at its top.
    (skill / "references" / "evals").mkdir(parents=True)
    (skill / "references" / "evals" / "note.md").write_text("x\n")
    second = es.content_hash(str(skill))
    (skill / "references" / ".installed-by-ai-workbench").write_text("")
    assert len({first, second, es.content_hash(str(skill))}) == 3


def test_the_hash_changes_when_a_file_is_added_or_renamed(root):
    skill = root / "skills" / "core-demo"
    first = es.content_hash(str(skill))
    (skill / "references").mkdir()
    (skill / "references" / "guide.md").write_text("g\n")
    second = es.content_hash(str(skill))
    (skill / "references" / "guide.md").rename(skill / "references" / "other.md")
    assert len({first, second, es.content_hash(str(skill))}) == 3


def test_the_hash_leaves_out_the_tests_of_the_skills_scripts(root):
    skill = root / "skills" / "core-demo"
    first = es.content_hash(str(skill))
    tests = skill / "scripts" / "tests"
    (tests / "fixtures").mkdir(parents=True)
    (tests / "test_check.py").write_text("def test_ok():\n    assert True\n")
    (tests / "conftest.py").write_text("")
    (tests / "fixtures" / "input.md").write_text("fixture\n")
    assert es.content_hash(str(skill)) == first  # added
    (tests / "test_check.py").write_text("def test_ok():\n    assert 1 == 1\n")
    assert es.content_hash(str(skill)) == first  # changed
    (tests / "test_check.py").unlink()
    (tests / "fixtures" / "input.md").unlink()
    assert es.content_hash(str(skill)) == first  # removed
    (skill / "scripts" / "check.py").write_text("print('changed')\n")
    assert es.content_hash(str(skill)) != first


def test_only_the_tests_folder_directly_under_scripts_is_left_out(root):
    skill = root / "skills" / "core-demo"
    first = es.content_hash(str(skill))
    (skill / "assets" / "scripts" / "tests").mkdir(parents=True)
    (skill / "assets" / "scripts" / "tests" / "test_app.py").write_text("x\n")
    second = es.content_hash(str(skill))
    (skill / "scripts" / "tests_helper.py").write_text("x\n")
    assert len({first, second, es.content_hash(str(skill))}) == 3


def test_status_is_draft_then_evaluated_then_stale(root, capsys):
    assert status(root) == "draft"
    assert record(root) == 0
    rec = json.loads((root / "skills" / "core-demo" / "evals" / "result.json").read_text())
    assert rec["skill"] == "core-demo" and rec["iteration"] == 3 and rec["date"] == "2030-01-02"
    assert rec["cases"] == [1, 2] and rec["complete"] is True and rec["infra_failures"] == 0
    assert rec["scores"] == {"strong_with": 1.0, "strong_without": 0.5, "floor_with": 0.9, "floor_without": 0.3}
    assert rec["gate"] == {"floor": True, "strong": True, "strong_delta": True, "passed": True}
    assert rec["measurement_version"] == 2 and rec["tolerance"] == 0
    assert rec["content_sha256"] == es.content_hash(str(root / "skills" / "core-demo"))
    assert status(root) == "evaluated"
    (root / "skills" / "core-demo" / "SKILL.md").write_text("# edited\n")
    assert status(root) == "stale"
    out = es.all_status(str(root))
    assert out["counts"] == {"evaluated": 0, "stale": 1, "draft": 1}
    assert [r["skill"] for r in out["skills"]] == ["core-demo", "eng-other"]


@pytest.mark.parametrize("kwargs", [{"floor": (0.79, 0.3)}, {"strong": (0.6, 0.7)}])
def test_a_record_whose_gate_failed_is_draft(root, kwargs):
    assert record(root, **kwargs) == 0
    row = es.skill_status(str(root / "skills" / "core-demo"))
    assert row["status"] == "draft" and "gate did not pass" in row["reason"]


def test_a_record_of_an_incomplete_run_is_draft(root):
    record(root, runs=2, complete=False, infra=1)
    rec = json.loads((root / "skills" / "core-demo" / "evals" / "result.json").read_text())
    assert rec["complete"] is False and rec["infra_failures"] == 1 and rec["gate"]["passed"] is True
    assert status(root) == "draft"


def test_nothing_writes_a_record_any_more(root, capsys):
    """The runner writes evidence; the command that built a record from a benchmark on disk is gone (default 27)."""
    with pytest.raises(SystemExit) as e:
        es.main(["record", "--skill", "core-demo", "--benchmark", "b.json"], root=str(root))
    assert e.value.code == 2
    assert not hasattr(es, "build_record") and not hasattr(es, "update_baseline") and not hasattr(es, "write_record")


def test_inventory_write_then_check_and_check_fails_after_a_status_change(root, capsys):
    assert es.main(["inventory", "--check"], root=str(root)) == 1
    assert es.main(["inventory", "--write"], root=str(root)) == 0
    text = (root / "docs" / "inventory.md").read_text()
    assert "Intro kept by hand." in text and "\nold\n" not in text and text.endswith("## Progress\n")
    assert "| core-demo | draft | — | — | — | — | — |" in text
    assert "Counts: 0 evaluated, 0 stale, 2 draft, 2 skills." in text
    assert es.main(["inventory", "--check"], root=str(root)) == 0
    record(root)
    assert es.main(["inventory", "--check"], root=str(root)) == 1
    es.main(["inventory", "--write"], root=str(root))
    assert "| core-demo | evaluated | 1.00 | 0.50 | 0.90 | 2030-01-02 | 3 |" in (root / "docs" / "inventory.md").read_text()
    (root / "skills" / "core-demo" / "SKILL.md").write_text("# core-demo, edited\n")
    capsys.readouterr()
    assert es.main(["inventory", "--check"], root=str(root)) == 1  # evaluated became stale
    assert "inventory --write" in capsys.readouterr().err


def test_inventory_without_markers_is_an_error(root):
    (root / "docs" / "inventory.md").write_text("# Inventory\n")
    with pytest.raises(SystemExit) as e:
        es.main(["inventory", "--check"], root=str(root))
    assert e.value.code == 1


def test_usage_errors_exit_2(root):
    for argv in (["hash"], ["record", "--skill", "core-demo"], ["inventory"], ["status", "--skill", "nope"], ["frobnicate"]):
        with pytest.raises(SystemExit) as e:
            es.main(argv, root=str(root))
        assert e.value.code == 2


# --- the eval-status check of scripts/validate.py -------------------------------------------------

def check(root):
    report = validate.Report()
    validate.check_eval_status(report, root=str(root))
    return [f"{e['where']}: {e['message']}" for e in report.errors], [w["message"] for w in report.warnings]


def test_validate_passes_on_a_current_inventory_and_warns_once_per_status(root):
    record(root)
    (root / "skills" / "core-demo" / "SKILL.md").write_text("# edited\n")
    es.main(["inventory", "--write"], root=str(root))
    errors, warnings = check(root)
    assert errors == [] and len(warnings) == 2
    assert "1 skill(s) are stale" in warnings[0] and "core-demo" in warnings[0]
    assert "1 skill(s) are draft" in warnings[1] and "eng-other" in warnings[1]


def test_validate_fails_on_a_stale_inventory_block(root):
    errors, _ = check(root)
    assert len(errors) == 1 and "python3 evals/eval_status.py inventory --write" in errors[0]


@pytest.mark.parametrize("content, why", [
    ("{not json", "not valid JSON"),
    ('{"skill": "core-demo"}', "missing field"),
    (None, "must equal the folder name"),
    ("hand-edited", "gate does not follow"),
])
def test_validate_fails_on_an_invalid_record(root, content, why):
    record(root)
    path = root / "skills" / "core-demo" / "evals" / "result.json"
    rec = json.loads(path.read_text())
    if content is None:
        rec["skill"] = "eng-other"
        content = json.dumps(rec)
    elif content == "hand-edited":
        rec["scores"]["floor_with"] = 0.2
        content = json.dumps(rec)
    path.write_text(content)
    es.main(["inventory", "--write"], root=str(root))
    errors, _ = check(root)
    assert len(errors) == 1 and errors[0].startswith("skills/core-demo/evals/result.json") and why in errors[0]
    assert es.skill_status(str(root / "skills" / "core-demo"))["status"] == "draft"


def test_a_record_carries_early_ends_and_older_records_without_them_stay_valid(root):
    record(root)
    record_file = root / "skills" / "core-demo" / "evals" / "result.json"
    rec = json.loads(record_file.read_text())
    rec["early_ends"] = {"strong": {"early_ends": 0, "rate": 0.0}, "floor": {"early_ends": 1, "rate": 0.2}}
    record_file.write_text(json.dumps(rec))
    assert status(root) == "evaluated"
    del rec["early_ends"]
    record_file.write_text(json.dumps(rec))
    assert status(root) == "evaluated"
    rec["early_ends"] = {"floor": 3}
    record_file.write_text(json.dumps(rec))
    assert "early_ends must map" in es.skill_status(str(root / "skills" / "core-demo"))["reason"]


# --- the eval gate configuration (evals/eval-gate.json) -----------------------------------------

def configure(root, **changes):
    config = {"strong_model": "s-model", "strong_harness": "h", "floor_model": "f-model", "floor_harness": "fh",
              "floor_pass_env": ["FLOOR_KEY"], "strong_pass_env": [], "grader": "s-model", "threshold": 0.8, "strong_tolerance": 0,
              "measurement_version": 2, "measurement_floor": 2, "measurement_sha256": "0" * 64, **changes}
    config = {k: v for k, v in config.items() if v is not None}  # None leaves a key out
    (root / "evals").mkdir(exist_ok=True)
    (root / "evals" / "eval-gate.json").write_text(json.dumps(config))


def test_a_record_on_the_configured_floor_model_is_evaluated_and_status_names_the_gate(root):
    configure(root)
    record(root)
    out = es.all_status(str(root))
    assert out["skills"][0]["status"] == "evaluated"
    assert out["gate"] == {"floor_model": "f-model", "threshold": 0.8, "strong_model": "s-model", "grader": "s-model",
                           "strong_tolerance": 0, "measurement_version": 2}


def test_a_record_on_another_floor_model_is_stale(root):
    record(root)
    assert status(root) == "evaluated"  # no configuration: any floor model
    configure(root, floor_model="new-floor")
    row = es.skill_status(str(root / "skills" / "core-demo"))
    assert row["status"] == "stale" and row["reason"] == "evaluated on another floor model (f-model); rerun the evals"
    assert es.all_status(str(root))["counts"] == {"evaluated": 0, "stale": 1, "draft": 1}
    es.main(["inventory", "--write"], root=str(root))
    assert "| core-demo | stale | 1.00 | 0.50 | 0.90 |" in (root / "docs" / "inventory.md").read_text()


def test_a_record_is_judged_against_the_configured_threshold(root):
    record(root)  # floor 0.9 on a threshold of 0.8
    configure(root, threshold=0.95)
    row = es.skill_status(str(root / "skills" / "core-demo"))
    assert row["status"] == "draft" and "floor 0.9 is below 0.95" in row["reason"]
    errors, _ = check(root)  # the record itself stays valid: its gate follows from the threshold it ran under
    assert not [e for e in errors if "result.json" in e]
    record(root, floor=(0.7, 0.3))
    configure(root, threshold=0.6)
    assert status(root) == "evaluated"


@pytest.mark.parametrize("content, why", [
    ("{not json", "not valid JSON"),
    ('{"floor_model": "f"}', "missing field 'strong_model'"),
    (None, "threshold must be between 0 and 1"),
])
def test_validate_fails_on_an_invalid_gate_configuration(root, content, why):
    configure(root, threshold=3)
    if content is not None:
        (root / "evals" / "eval-gate.json").write_text(content)
    es.main(["inventory", "--write"], root=str(root))
    errors, _ = check(root)
    assert len(errors) == 1 and errors[0].startswith("evals/eval-gate.json") and why in errors[0]
    assert es.load_gate(str(root)) == {}


def test_the_repository_gate_configuration_is_valid():
    assert es.gate_problems(str(REPO)) == [] and es.load_gate(str(REPO))["floor_model"]


# --- the gate asks the threshold of both models; a record says how it was measured ----------------

def test_the_strong_model_below_the_threshold_fails_the_gate(root):
    record(root, strong=(0.78, 0.4), floor=(0.9, 0.3))
    row = es.skill_status(str(root / "skills" / "core-demo"))
    assert row["status"] == "draft" and "strong 0.78 is below 0.8" in row["reason"]


def test_the_tolerance_forgives_a_small_loss_to_the_baseline_and_no_more(root):
    assert es.gate({"strong_with": 0.95, "strong_without": 0.96, "floor_with": 0.9, "floor_without": 0.2}, 0.8)["passed"] is False
    scores = {"strong_with": 0.95, "strong_without": 0.96, "floor_with": 0.9, "floor_without": 0.2}
    assert es.gate(scores, 0.8, 0.02)["passed"] is True
    assert es.gate({**scores, "strong_without": 0.99}, 0.8, 0.02)["passed"] is False


@pytest.mark.parametrize("change, why", [
    ({"measurement_version": 3}, "measured under version 2 of the measurement, the configured one is 3"),
    ({"strong_model": "new-strong"}, "evaluated on another strong model (s-model)"),
    ({"grader": "new-grader"}, "graded by another model (s-model)"),
])
def test_a_record_of_another_measurement_strong_model_or_grader_is_stale(root, change, why):
    configure(root)
    record(root)
    assert status(root) == "evaluated"
    configure(root, **change)
    row = es.skill_status(str(root / "skills" / "core-demo"))
    assert row["status"] == "stale" and why in row["reason"]


def test_a_record_written_under_the_earlier_rule_is_valid_and_stale(root):
    record(root)
    path = root / "skills" / "core-demo" / "evals" / "result.json"
    rec = json.loads(path.read_text())
    del rec["measurement_version"], rec["tolerance"], rec["gate"]["strong"]
    path.write_text(json.dumps(rec))
    configure(root)
    errors, _ = check(root)
    assert not [e for e in errors if "result.json" in e]
    row = es.skill_status(str(root / "skills" / "core-demo"))
    assert row["status"] == "stale" and "version 1" in row["reason"]


def test_a_configuration_needs_a_measurement_version_above_the_earlier_rule(root):
    configure(root, measurement_version=1)
    assert es.gate_problems(str(root)) == ["measurement_version must be above 1"]


@pytest.mark.parametrize("floor", [0, 3, True, "2"])
def test_the_measurement_floor_is_a_version_up_to_the_measurement_version(root, floor):
    configure(root, measurement_floor=floor)
    assert len(es.gate_problems(str(root))) == 1 and "measurement_floor" in es.gate_problems(str(root))[0]
    configure(root, measurement_floor=None)
    assert es.gate_problems(str(root)) == ["missing field 'measurement_floor'"]


def test_the_fingerprint_is_optional_and_checked_when_present(root):
    configure(root, measurement_sha256=None)
    assert es.gate_problems(str(root)) == [] and es.load_gate(str(root))["measurement_floor"] == 2
    configure(root, measurement_sha256="abc")
    assert es.gate_problems(str(root)) == ["measurement_sha256 must be 64 hexadecimal characters"]


def test_no_evidence_is_written_while_the_gate_file_carries_no_fingerprint(root, capsys):
    assert es.evidence_refusal(str(root)) is None  # no gate file: a tree with no measurement to protect
    configure(root)
    assert es.evidence_refusal(str(root)) is None
    configure(root, measurement_sha256=None)
    assert "carries no measurement_sha256: measurement version 2 is open" in es.evidence_refusal(str(root))
    configure(root, threshold=3)
    assert "is not valid" in es.evidence_refusal(str(root))


def test_the_repository_measurement_is_at_version_5_with_its_floor(root):
    """Phase B changes what the grader is shown, so nothing measured before it counts: version 5, floor 5."""
    gate = es.load_gate(str(REPO))
    assert gate["measurement_version"] >= 5 and gate["measurement_floor"] >= 5


def test_a_record_of_the_container_era_names_its_environment(root):
    record(root)
    path = root / "skills" / "core-demo" / "evals" / "result.json"
    rec = json.loads(path.read_text())
    rec["measurement_version"] = 3
    rec["gate"] = es.gate(rec["scores"], rec["threshold"], rec["tolerance"], 3)
    path.write_text(json.dumps(rec))
    errors, _ = check(root)
    assert any("names the container it ran in" in e for e in errors)
    rec["environment"] = {"kind": "container", "definition_sha256": "0" * 64, "image": "img:tag", "image_id": "sha256:1"}
    path.write_text(json.dumps(rec))
    errors, _ = check(root)
    assert not [e for e in errors if "result.json" in e]



# --- the keys that control a test event ------------------------------------------------------------

def test_the_control_of_an_event_has_defaults_and_the_gate_file_overrides_them(root):
    assert es.event_config({}) == {"runs": 3, "timeout_seconds": 900, "retries": 2, "max_resumes": 3, "total_jobs": 10,
                                   "web_jobs": {"strong": 2, "floor": 2}}
    configure(root, runs=5, max_resumes=1, web_jobs={"strong": 1, "floor": 4})
    assert es.gate_problems(str(root)) == []
    control = es.event_config(es.load_gate(str(root)))
    assert (control["runs"], control["max_resumes"], control["web_jobs"], control["retries"]) == (5, 1, {"strong": 1, "floor": 4}, 2)


@pytest.mark.parametrize("change, why", [
    ({"runs": 0}, "runs must be a whole number from 1 to 10"),
    ({"runs": True}, "runs must be a whole number"),
    ({"timeout_seconds": 5}, "timeout_seconds must be a whole number from 30"),
    ({"retries": 6}, "retries must be a whole number from 0 to 5"),
    ({"max_resumes": -1}, "max_resumes must be a whole number"),
    ({"total_jobs": 0}, "total_jobs must be a whole number"),
    ({"web_jobs": {"strong": 2}}, "web_jobs must give a whole number"),
    ({"web_jobs": {"strong": 2, "floor": 0}}, "web_jobs must give a whole number"),
    ({"web_cases": {"core-demo": []}}, "web_cases must map a skill name"),
    ({"web_cases": ["core-demo"]}, "web_cases must map a skill name"),
    ({"strong_web_pass_env": ["not a name"]}, "strong_web_pass_env must list variable names"),
    ({"run": 3}, "unknown field 'run'"),
])
def test_a_control_key_outside_its_form_makes_the_gate_file_invalid(root, change, why):
    configure(root, **change)
    problems = es.gate_problems(str(root))
    assert len(problems) == 1 and why in problems[0] and es.load_gate(str(root)) == {}


def test_a_case_may_use_the_web_only_when_the_gate_file_lists_it(root):
    assert es.web_case_allowed({}, "core-demo", 1) is True  # no gate file: no list, nothing refused
    configure(root)
    gate = es.load_gate(str(root))
    assert es.web_case_allowed(gate, "core-demo", 1) is False  # a gate file with no list: no case
    configure(root, web_cases={"core-demo": [1, "b"]})
    gate = es.load_gate(str(root))
    assert es.web_case_allowed(gate, "core-demo", 1) and es.web_case_allowed(gate, "core-demo", "1") and es.web_case_allowed(gate, "core-demo", "b")
    assert not es.web_case_allowed(gate, "core-demo", 2) and not es.web_case_allowed(gate, "eng-other", 1)


# --- the evidence store: the hashes, the version, the model ids, the closed forms of a line ---------------

def test_each_case_has_its_own_hash_over_the_whole_case_and_its_fixtures(root):
    skill = root / "skills" / "core-demo"
    cases = [{"id": 1, "prompt": "p", "files": ["evals/files"], "assertions": ["a", {"text": "b", "tags": ["guard"]}],
              "workbench_files": ["scripts/validate.py"]},
             {"id": 2, "prompt": "q", "assertions": ["a"]}]
    write = lambda: (skill / "evals" / "evals.json").write_text(json.dumps({"evals": cases}))
    write()
    first = es.case_hashes(str(skill))
    assert set(first) == {"1", "2"} and first["1"] != first["2"] and all(len(h) == 64 for h in first.values())
    assert es.case_hashes(str(skill)) == first  # stable
    # A change to one case drops the evidence of that case only: every part of the case object counts.
    for change in ({"prompt": "another"}, {"assertions": ["a", {"text": "b", "tags": ["format"]}]}, {"setup": ["true"]},
                   {"allow_web": True}, {"grader_files": ["input.md"]}, {"skills": ["eng-other"]}, {"tags": ["guard"]},
                   {"workbench_files": ["scripts/validate.py", "templates"]}, {"expected_output": "x"}):
        saved, cases[0] = cases[0], {**cases[0], **change}
        write()
        now = es.case_hashes(str(skill))
        assert now["1"] != first["1"] and now["2"] == first["2"], change
        cases[0] = saved
    write()
    assert es.case_hashes(str(skill)) == first
    # The bytes of its fixture files count; a cache beside them does not.
    (skill / "evals" / "files" / "input.md").write_text("another fixture\n")
    assert es.case_hashes(str(skill))["1"] != first["1"] and es.case_hashes(str(skill))["2"] == first["2"]
    (skill / "evals" / "files" / "input.md").write_text("fixture\n")
    (skill / "evals" / "files" / "__pycache__").mkdir()
    (skill / "evals" / "files" / "__pycache__" / "x.pyc").write_text("x")
    (skill / "evals" / "files" / ".DS_Store").write_text("x")
    assert es.case_hashes(str(skill)) == first
    (skill / "evals" / "files" / "more.md").write_text("x\n")
    assert es.case_hashes(str(skill))["1"] != first["1"]


def test_a_repository_file_a_case_brings_enters_its_hash_as_a_path_never_as_content(root):
    skill = root / "skills" / "core-demo"
    (root / "scripts").mkdir()
    (root / "scripts" / "validate.py").write_text("print('one')\n")
    (skill / "evals" / "evals.json").write_text(json.dumps({"evals": [{"id": 1, "prompt": "p", "workbench_files": ["scripts/validate.py"]}]}))
    first = es.case_hashes(str(skill))
    (root / "scripts" / "validate.py").write_text("print('edited')\n")
    assert es.case_hashes(str(skill)) == first  # an edit of that file changes no hash and no evidence


def test_the_files_allow_web_applies_to_every_case_of_the_file(root):
    skill = root / "skills" / "core-demo"
    first = es.case_hashes(str(skill))
    data = json.loads((skill / "evals" / "evals.json").read_text())
    (skill / "evals" / "evals.json").write_text(json.dumps({**data, "allow_web": True}))
    assert all(es.case_hashes(str(skill))[k] != first[k] for k in first)
    assert es.case_hashes(str(root / "skills" / "missing")) == {}


@pytest.mark.parametrize("text, version", [
    ('---\nname: x\nmetadata:\n  version: "1.2.3"\n---\n', "1.2.3"),
    ('---\nname: x\nmetadata:\n  version: "0.2"   # two parts, as before the version rules\n---\n', "0.2.0"),
    ("---\nname: x\nmetadata:\n  version: 10.20.30\n---\n", "10.20.30"),
    ('---\nname: x\nmetadata:\n  version: "one"\n---\n', None),
    ("---\nname: x\n---\nversion: 1.2.3 in the body is not it\n", None),
    ("# no frontmatter\n", None),
])
def test_the_version_of_a_skill_is_read_as_three_parts(root, text, version):
    skill = root / "skills" / "core-demo"
    (skill / "SKILL.md").write_text(text)
    assert es.skill_version(str(skill)) == version


def test_a_model_is_written_under_its_listed_id_and_anything_else_as_unknown(root):
    assert es.model_id({}, "anything/at-all") == "anything/at-all"  # no gate file: no list
    configure(root)
    gate = es.load_gate(str(root))
    assert es.model_id(gate, "s-model") == "s-model" and es.model_id(gate, "f-model") == "f-model"
    assert es.model_id(gate, "a-private-model-name") == "unknown"
    configure(root, models={"s-model": ["provider/s-model"], "f-model": ["vendor/f-model", "f"], "third": []})
    gate = es.load_gate(str(root))
    assert gate and es.model_id(gate, "provider/s-model") == "s-model" and es.model_id(gate, "f") == "f-model"
    assert es.model_id(gate, "third") == "third" and es.model_id(gate, "fourth") == "unknown"


@pytest.mark.parametrize("models, why", [
    ({"s-model": [], "f-model": ["s-model"]}, "names an id or an alias twice"),
    ({"s-model": []}, "floor_model 'f-model' is not in models"),
    ({"s-model": "alias", "f-model": []}, "models must map each known model id"),
    ({"s-model": [], "f-model": [], "unknown": []}, "models must map each known model id"),
    ({}, "models must map each known model id"),
])
def test_the_model_list_names_every_configured_model_once(root, models, why):
    configure(root, models=models)
    assert len(es.gate_problems(str(root))) >= 1 and why in es.gate_problems(str(root))[0]


def test_the_fingerprint_follows_the_files_that_decide_what_a_run_measures(root):
    (root / "evals" / "container").mkdir(parents=True)
    (root / "evals" / "grading-prompt.md").write_text("template\n")
    (root / "evals" / "container" / "Dockerfile").write_text("FROM x\n")
    for harness in ("one", "two"):
        (root / "adapters" / harness).mkdir(parents=True)
        (root / "adapters" / harness / "adapter.json").write_text("{}")
    (root / "adapters" / "one" / "run-prompt.sh").write_text("echo\n")
    first = es.measurement_fingerprint(str(root))
    assert len(first) == 64 and es.measurement_fingerprint(str(root)) == first
    seen = {first}
    for rel, text in (("evals/grading-prompt.md", "another template\n"), ("evals/container/Dockerfile", "FROM y\n"),
                      ("adapters/one/run-prompt.sh", "echo changed\n"), ("adapters/one/adapter.json", '{"eval": {}}')):
        (root / rel).write_text(text)
        seen.add(es.measurement_fingerprint(str(root)))
    assert len(seen) == 5
    # What decides nothing: a skill, a document, the manifest of an adapter that runs no eval.
    (root / "adapters" / "two" / "adapter.json").write_text('{"changed": true}')
    (root / "skills" / "core-demo" / "SKILL.md").write_text("# edited\n")
    assert es.measurement_fingerprint(str(root)) in seen and len(seen) == 5


def test_a_test_id_is_its_utc_time_and_eight_random_characters():
    import datetime
    a = es.new_test_id(datetime.datetime(2030, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc))
    assert a.startswith("20300102T030405Z-") and es.TEST_ID_RE.fullmatch(a)
    assert len({es.new_test_id() for _ in range(50)}) == 50


TEST_ID = "20300102T030405Z-0a1b2c3d"
H = {c: c * 64 for c in "abcdef"}


def event_line(**changes):
    line = {"record": "test", "skill": "core-demo", "test": TEST_ID, "kind": "full", "version": "1.0.0", "content_sha256": H["a"],
            "date": "2030-01-02", "models": {"strong": "s-model", "floor": "f-model"}, "adapters": {"strong": "h", "floor": "fh"},
            "adapter_sha256": {"h": H["b"], "fh": H["c"]}, "grader": "s-model", "runs": 3, "timeout_seconds": 900, "retries": 2,
            "measurement_version": 5, "measurement_sha256": H["d"], "image_digest": "sha256:" + H["e"], "image_platform": "linux/arm64",
            "grading_template_sha256": H["f"], "tools": {"git": "git version 2.47.3"}, "cases": {"1": H["a"], "2": H["b"]},
            "baseline": {"1": "run", "2": "reused"}, "web_cases": [2],
            "counts": {"s-model": {"with": dict.fromkeys(es.COUNT_KEYS, 0), "without": dict.fromkeys(es.COUNT_KEYS, 0)},
                       "f-model": {"with": {**dict.fromkeys(es.COUNT_KEYS, 0), "invoked": 6}}},
            "extra_pass_env": [], "complete": True,
            "gate": {"passed": True, "with": 0.9, "baseline": 0.5, "threshold": 0.8, "tolerance": 0.05}}
    line.update(changes)
    return {k: v for k, v in line.items() if v is not DROP}


DROP = object()


def run_line(**changes):
    line = {"record": "run", "skill": "core-demo", "version": "1.0.0", "content_sha256": H["a"], "model": "s-model", "adapter": "h",
            "kind": "full", "test": TEST_ID, "date": "2030-01-02", "measurement_version": 5, "measurement_sha256": H["d"],
            "case": 1, "case_sha256": H["a"], "variant": "with", "outcome": "graded", "score": 0.5, "results": [1, 0]}
    line.update(changes)
    return {k: v for k, v in line.items() if v is not DROP}


def evidence(root, lines, name=f"lab-{TEST_ID}.jsonl", skill="core-demo"):
    folder = root / "skills" / skill / "evals" / "evidence"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text("".join(json.dumps(line) + "\n" for line in lines))
    return folder / name


def test_a_well_formed_evidence_file_is_valid_and_changes_no_status(root, capsys):
    configure(root)
    path = evidence(root, [event_line(), run_line(), run_line(variant="without", score=0.0, results=[0, 0]),
                           run_line(model="f-model", adapter="fh", case=2, case_sha256=H["b"], context_sha256=H["c"], score=1.0, results=[1, 1]),
                           run_line(outcome="timeout", score=0, results=[0, 0]),
                           run_line(guard_failed=[2])])
    assert es.evidence_file_problems(str(path), str(root)) == []
    assert es.evidence_problems(str(root)) == ({}, 1) and es.main(["evidence"], root=str(root)) == 0
    assert json.loads(capsys.readouterr().out) == {"files": 1, "problems": {}}
    assert es.main(["evidence", "--skill", "eng-other"], root=str(root)) == 0
    assert [str(p) for p in map(Path, es.evidence_files(str(root / "skills" / "core-demo")))] == [str(path)]
    # The old path is intact: the status still reads result.json, and evidence does not make a skill stale.
    assert status(root) == "draft"


@pytest.mark.parametrize("change, why", [
    ({"note": "free text"}, "unknown key 'note'"),
    ({"score": DROP}, "missing key 'score'"),
    ({"skill": "Core Demo"}, "skill must be a skill name"),
    ({"version": "1.0"}, "version must be X.Y.Z"),
    ({"content_sha256": "abc"}, "content_sha256 must be 64 hexadecimal characters"),
    ({"model": "a-private-model"}, "model must be an id of the gate file's model list"),
    ({"adapter": "../h"}, "adapter must be an adapter's folder name"),
    ({"kind": "smoke"}, "kind must be full or partial"),
    ({"date": "2030-13-01"}, "date must be YYYY-MM-DD"),
    ({"date": "02/01/2030"}, "date must be YYYY-MM-DD"),
    ({"measurement_version": "5"}, "measurement_version must be a whole number"),
    ({"case": 1.5}, "case must be a case id"),
    ({"variant": "ablated"}, "variant must be with or without"),
    ({"outcome": "refused"}, "outcome must be graded or timeout"),
    ({"score": 1.2}, "score must be a number from 0 to 1"),
    ({"score": True}, "score must be a number from 0 to 1"),
    ({"score": 0.9}, "score must be the share of results that are 1"),
    ({"results": []}, "results must be a list of 0 and 1"),
    ({"results": [1, 2]}, "results must be a list of 0 and 1"),
    ({"results": [True, False]}, "results must be a list of 0 and 1"),
    ({"outcome": "timeout", "score": 0.5}, "a timeout has score 0 and results all 0"),
    ({"guard_failed": [1]}, "guard_failed must be a list of positions of assertions whose result is 0"),
    ({"guard_failed": [3]}, "guard_failed must be a list of positions"),
    ({"guard_failed": [2], "variant": "without"}, "guard_failed belongs to a with-skill run only"),
    ({"platform": "Chirp!"}, "platform must be a platform name"),
    ({"context_sha256": "x"}, "context_sha256 must be 64 hexadecimal characters"),
    ({"version": "1.0.1"}, "version differs from the event line of the file"),
    ({"test": "20300102T030405Z-ffffffff"}, "test differs from the event line of the file"),
    ({"kind": "partial"}, "kind differs from the event line of the file"),
    ({"measurement_sha256": H["a"]}, "measurement_sha256 differs from the event line of the file"),
    ({"model": "unknown"}, "model is not one of the event's models"),
    ({"adapter": "other"}, "adapter is not one of the event's adapters"),
    ({"case": 3}, "case and case_sha256 are not a case of the event line"),
    ({"case_sha256": H["f"]}, "case and case_sha256 are not a case of the event line"),
])
def test_a_run_line_with_an_unknown_key_or_a_value_outside_its_form_is_an_error(root, capsys, change, why):
    configure(root)
    path = evidence(root, [event_line(), run_line(), run_line(**change)])
    problems = es.evidence_file_problems(str(path), str(root))
    assert len(problems) == 1 and problems[0].startswith("line 3: ") and why in problems[0]
    assert es.main(["evidence"], root=str(root)) == 1 and why in capsys.readouterr().err


@pytest.mark.parametrize("change, why", [
    ({"operator": "someone"}, "unknown key 'operator'"),
    ({"grader": DROP}, "missing key 'grader'"),
    ({"record": "run"}, "record must be \"test\""),
    ({"test": "yesterday"}, "test must be a test id"),
    ({"models": {"floor": "f-model"}}, "models must be"),
    ({"models": {"strong": "a-private-model", "floor": "f-model"}}, "models must be"),
    ({"adapters": {"strong": "h"}}, "adapters must be an adapter's folder name for each tier"),
    ({"adapter_sha256": {"h": H["b"]}}, "adapter_sha256 must be the sha256 of the run-prompt.sh of each adapter"),
    ({"grader": "a-private-grader"}, "grader must be a listed model id"),
    ({"runs": 0}, "runs must be a whole number, 1 or more"),
    ({"retries": -1}, "retries must be a whole number, 0 or more"),
    ({"image_digest": None}, "image_digest must be sha256:"),
    ({"image_platform": "arm64"}, "image_platform must be a platform"),
    ({"tools": {"git": "a version line\nwith a second line"}}, "tools must be"),
    ({"cases": {}}, "cases must be"),
    ({"baseline": {"1": "run"}}, "baseline must be run, reused or none for each case"),
    ({"baseline": {"1": "run", "2": "skipped"}}, "baseline must be run, reused or none"),
    ({"web_cases": [9]}, "web_cases must be a list of ids of cases"),
    ({"counts": {"s-model": {"with": {"retries": 0}}}}, "counts must be"),
    ({"counts": {"s-model": {"without": {**dict.fromkeys(es.COUNT_KEYS, 0), "invoked": 1}}}}, "counts must be"),
    ({"counts": {"private": {"with": dict.fromkeys(es.COUNT_KEYS, 0)}}}, "counts must be"),
    ({"extra_pass_env": ["not a name"]}, "extra_pass_env must be a list of variable names"),
    ({"complete": "yes"}, "complete must be true or false"),
    ({"gate": DROP}, "a complete full test carries its gate"),
    ({"gate": {"passed": True}}, "gate must be"),
    ({"gate": {"passed": True, "with": 0.9, "baseline": 0.5, "threshold": 0.8, "tolerance": 0.05, "note": "anything"}}, "gate must be"),
    ({"kind": "partial"}, "gate belongs to a full test only"),
    ({"complete": False}, "gate is written by a complete full test only"),
    ({"upstream": {"f-model": "a provider\nname"}}, "upstream must be"),
    ({"skill": "eng-other"}, "skill must be the folder's name, core-demo"),
    ({"test": "20300102T030405Z-ffffffff"}, "test differs from the file's name"),
])
def test_an_event_line_with_an_unknown_key_or_a_value_outside_its_form_is_an_error(root, change, why):
    configure(root)
    path = evidence(root, [event_line(**change)])
    problems = es.evidence_file_problems(str(path), str(root))
    assert problems and problems[0].startswith("line 1: ") and why in problems[0], problems


def test_the_forms_that_are_optional_or_depend_on_the_kind(root):
    configure(root)
    for line in (event_line(kind="partial", gate=DROP), event_line(complete=False, gate=DROP),  # an abandoned full test
                 event_line(gate={"passed": False, "with": 0.5, "baseline": None, "threshold": 0.8, "tolerance": 0.05, "note": "baseline expired"}),
                 event_line(upstream={"f-model": "a-provider"}), event_line(models={"strong": "s-model"}, adapters={"strong": "h"},
                                                                            adapter_sha256={"h": H["b"]}, counts={})):
        assert es.event_line_problems(line, {"s-model", "f-model"}) == [], line
    assert es.run_line_problems(run_line(model="unknown")) == [] and es.run_line_problems(run_line(case="a-case"), None, None) == []


def test_a_file_that_is_no_evidence_file_is_an_error(root, capsys):
    configure(root)
    assert "the name must be lab-<test id>.jsonl" in es.evidence_file_problems(str(evidence(root, [event_line()], "notes.jsonl")), str(root))[0]
    (root / "skills" / "core-demo" / "evals" / "evidence" / "notes.jsonl").unlink()
    path = evidence(root, [])
    assert es.evidence_file_problems(str(path), str(root)) == ["the file is empty: an evidence file has an event line"]
    path.write_text("{not json\n" + json.dumps(run_line()) + "\n[1]\n")
    problems = es.evidence_file_problems(str(path), str(root))
    assert problems[:2] == ["line 1: not valid JSON", "line 3: must be a JSON object"] and "unknown key" in problems[2]
    # A contributed field file is another item's to validate; anything else in the folder is flagged.
    path.unlink()
    evidence(root, [{"record": "use"}], "field-0123456789ab.jsonl")
    assert es.evidence_problems(str(root)) == ({}, 0)
    evidence(root, [event_line()], "lab-notes.txt")
    found, checked = es.evidence_problems(str(root))
    assert checked == 1 and list(found) == [str(Path("skills") / "core-demo" / "evals" / "evidence" / "lab-notes.txt")]
    assert es.main(["evidence", "--file", str(root / "skills" / "core-demo" / "evals" / "evidence" / "lab-notes.txt")], root=str(root)) == 1


def test_the_hash_command_prints_the_content_hash_the_version_and_the_case_hashes(root, capsys):
    (root / "skills" / "core-demo" / "SKILL.md").write_text('---\nname: core-demo\nmetadata:\n  version: "0.4"\n---\n')
    assert es.main(["hash", "--skill", "core-demo"], root=str(root)) == 0
    out = json.loads(capsys.readouterr().out)
    skill = str(root / "skills" / "core-demo")
    assert out == {"skill": "core-demo", "content_sha256": es.content_hash(skill), "version": "0.4.0", "cases": es.case_hashes(skill)}


def test_the_48_old_records_stay_as_history_and_no_evidence_is_converted_from_them():
    records = sorted(REPO.glob("skills/*/evals/result.json"))
    assert len(records) >= 48 and not list(REPO.glob("skills/*/evals/evidence/*"))
    assert es.evidence_problems(str(REPO)) == ({}, 0)
    gate = es.load_gate(str(REPO))
    assert set(gate["models"]) >= {gate["strong_model"], gate["floor_model"], gate["grader"]}
    assert es.model_id(gate, "deepseek/deepseek-v4.1-flash") == gate["floor_model"]  # the same model without the router's prefix


# --- the gate from the lines: epochs, the floor, a major version ---------------------------------------

def gate_tree(root, events, cfg_changes=None, version="1.2.0"):
    """A skill with two cases and the given evidence: [(test id, kind, version, date, complete, [(case, variant,
    score, date)])]. Returns (skill folder, configuration)."""
    skill = root / "skills" / "core-demo"
    (skill / "SKILL.md").write_text(f'---\nname: core-demo\nmetadata:\n  version: "{version}"\n---\n')
    hashes = es.case_hashes(str(skill))
    for test, kind, ver, date, complete, lines in events:
        event = event_line(test=test, kind=kind, version=ver, date=date, complete=complete, cases=hashes,
                           baseline={k: "run" for k in hashes}, web_cases=[],
                           gate={"passed": True, "with": 1.0, "baseline": 0.0, "threshold": 0.8, "tolerance": 0.05}
                           if kind == "full" and complete else DROP)
        evidence(root, [event] + [run_line(test=test, kind=kind, version=ver, date=d, case=c, case_sha256=hashes[str(c)],
                                           variant=v, score=sc, results=[1] if sc == 1 else [0]) for c, v, sc, d in lines],
                 name=f"lab-{test}.jsonl")
    cfg = {"strong_model": "s-model", "floor_model": "f-model", "grader": "s-model", "threshold": 0.8, "strong_tolerance": 0.05,
           "measurement_floor": 5, **(cfg_changes or {})}
    return str(skill), cfg


T1, T2, T3 = "20300101T000000Z-00000001", "20300201T000000Z-00000002", "20300301T000000Z-00000003"
FULL_LINES = lambda d, w=1, b=0: [(1, "with", w, d), (2, "with", w, d), (1, "without", b, d), (2, "without", b, d)]


def test_the_gate_reads_every_full_test_of_the_newest_version_and_no_partial_test(root):
    skill, cfg = gate_tree(root, [(T1, "full", "1.2.0", "2030-01-01", True, FULL_LINES("2030-01-01")),
                                  (T2, "partial", "1.2.0", "2030-02-01", True, [(1, "with", 0, "2030-02-01")]),
                                  (T3, "full", "1.2.1", "2030-03-01", True, [(1, "with", 0, "2030-03-01"), (2, "with", 1, "2030-03-01")])])
    gate = es.gate_of(skill, cfg)
    # Z change 1.2.0 to 1.2.1: one X.Y, so both full tests count; the partial test's zero does not.
    assert (gate["computed"], gate["version"], gate["test"], gate["with"], gate["baseline"]) == (True, "1.2", T3, 0.75, 0.0)
    assert gate["passed"] is False and gate["cases"] == ["1", "2"] and gate["pending"] == []


def test_a_newer_x_y_starts_a_new_gate_and_a_major_version_has_none_until_its_full_test(root):
    lines = FULL_LINES("2030-01-01")
    skill, cfg = gate_tree(root, [(T1, "full", "1.2.0", "2030-01-01", True, lines),
                                  (T2, "full", "1.3.0", "2030-02-01", True, [(1, "with", 0, "2030-02-01"), (2, "with", 0, "2030-02-01")])],
                           version="1.3.0")
    assert es.gate_of(skill, cfg)["with"] == 0.0  # only the lines of 1.3
    skill, cfg = gate_tree(root, [(T1, "full", "1.2.0", "2030-01-01", True, lines)], version="2.0.0")
    gate = es.gate_of(skill, cfg)
    assert gate["computed"] is False and gate["cause"] == "no full test of the current major version"


def test_a_raised_measurement_floor_leaves_every_earlier_line_without_weight(root):
    skill, cfg = gate_tree(root, [(T1, "full", "1.2.0", "2030-01-01", True, FULL_LINES("2030-01-01"))], {"measurement_floor": 6})
    gate = es.gate_of(skill, cfg)
    assert gate["computed"] is False and "have no run with the skill" in gate["cause"]
    assert es.baseline_lines(skill, cfg) == {}


def test_after_an_epoch_the_baselines_expire_and_the_written_result_stands_with_its_note(root):
    epoch = {"date": "2030-01-15", "models": ["s-model"], "skills": "all", "cause": "the model changed under its id"}
    skill, cfg = gate_tree(root, [(T1, "full", "1.2.0", "2030-01-01", True, FULL_LINES("2030-01-01"))], {"epochs": [epoch]})
    gate = es.gate_of(skill, cfg)
    assert gate["note"] == "baseline expired" and gate["passed"] is True and gate["computed"] is False
    assert es.baseline_lines(skill, cfg) == {}
    # An epoch of another model or of another skill reaches nothing here.
    for other in ({**epoch, "models": ["f-model"]}, {**epoch, "skills": ["eng-other"]}, {**epoch, "date": "2029-12-31"}):
        assert es.gate_of(skill, {**cfg, "epochs": [other]})["computed"] is True


def test_runs_before_an_epoch_are_not_of_the_epoch_of_the_newest_full_test(root):
    epoch = {"date": "2030-01-15", "models": "all", "skills": ["core-demo"], "cause": "the image changed"}
    skill, cfg = gate_tree(root, [(T1, "full", "1.2.0", "2030-01-01", True, FULL_LINES("2030-01-01", w=0)),
                                  (T2, "full", "1.2.0", "2030-02-01", True, FULL_LINES("2030-02-01"))], {"epochs": [epoch]})
    gate = es.gate_of(skill, cfg)
    assert gate["computed"] and gate["with"] == 1.0 and gate["baseline"] == 0.0  # the zeros of before the epoch are not in it


def test_a_deleted_case_leaves_the_gate_to_the_cases_that_remain(root):
    skill, cfg = gate_tree(root, [(T1, "full", "1.2.0", "2030-01-01", True,
                                   [(1, "with", 1, "2030-01-01"), (2, "with", 0, "2030-01-01"), (1, "without", 0, "2030-01-01"),
                                    (2, "without", 0, "2030-01-01")])])
    assert es.gate_of(skill, cfg)["with"] == 0.5
    data = json.loads((root / "skills" / "core-demo" / "evals" / "evals.json").read_text())
    (root / "skills" / "core-demo" / "evals" / "evals.json").write_text(json.dumps({"evals": data["evals"][:1]}))
    gate = es.gate_of(skill, cfg)
    assert gate["cases"] == ["1"] and gate["with"] == 1.0 and gate["passed"] is True


def test_the_gate_command_prints_it(root, capsys):
    configure(root)
    assert es.main(["gate", "--skill", "core-demo"], root=str(root)) == 0
    assert json.loads(capsys.readouterr().out)["cause"] == "no full test of the current major version"
    with pytest.raises(SystemExit) as e:
        es.main(["gate"], root=str(root))
    assert e.value.code == 2


# --- the platforms' cases (the plan's decision 14c, item B7a) ------------------------------------------

def platform_cases(root, name="chirp", cases=None):
    folder = root / "skills" / "core-demo" / "evals" / "platforms"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.json").write_text(json.dumps({"skill_name": "core-demo", "platform": name,
                                                     "evals": cases or [{"id": 7, "prompt": "post it", "assertions": ["a", "b"]}]}))
    return es.case_hashes(str(root / "skills" / "core-demo"), name)


def test_a_line_of_a_platforms_case_belongs_to_a_partial_test_with_the_skill(root):
    configure(root)
    assert es.run_line_problems(run_line(kind="partial", platform="chirp")) == []
    assert "a line of a platform's case runs in a partial test" in es.run_line_problems(run_line(platform="chirp"))[0]
    assert "a line of a platform's case runs in a partial test" in es.run_line_problems(
        run_line(kind="partial", variant="without", platform="chirp"))[0]
    assert "platform must be a platform name" in es.run_line_problems(run_line(kind="partial", platform="Chirp"))[0]
    path = evidence(root, [event_line(kind="partial", gate=DROP), run_line(kind="partial", platform="chirp")])
    assert es.evidence_file_problems(str(path), str(root)) == []


def test_status_shows_a_mean_and_runs_per_platform_and_model_and_the_gate_never_reads_them(root, capsys):
    skill = root / "skills" / "core-demo"
    skill_dir, cfg = gate_tree(root, [(T1, "full", "1.2.0", "2030-01-01", True, FULL_LINES("2030-01-01"))])
    before = es.gate_of(skill_dir, cfg)
    hashes = platform_cases(root)
    lines = [run_line(test=T2, kind="partial", version="1.2.0", case=7, case_sha256=hashes["7"], platform="chirp", score=s,
                      results=r, model=m) for s, r, m in ((1.0, [1, 1], "s-model"), (0.5, [1, 0], "s-model"), (0.0, [0, 0], "f-model"))]
    lines.append(run_line(test=T2, kind="partial", version="1.2.0", case=7, case_sha256=H["f"], platform="chirp", score=1.0,
                          results=[1, 1]))  # a case changed since: weight 0
    evidence(root, [event_line(test=T2, kind="partial", version="1.2.0", gate=DROP, cases={"7": hashes["7"]},
                               baseline={"7": "none"}, web_cases=[])] + lines, name=f"lab-{T2}.jsonl")
    assert es.platform_results(skill_dir, cfg) == {"chirp": {"f-model": {"mean": 0.0, "runs": 1}, "s-model": {"mean": 0.75, "runs": 2}}}
    assert es.gate_of(skill_dir, cfg) == before  # a platform's lines change neither the gate nor its pool
    assert es.platform_results(skill_dir, {**cfg, "measurement_floor": 6}) == {}
    (skill / "SKILL.md").write_text('---\nname: core-demo\nmetadata:\n  version: "2.0.0"\n---\n')
    assert es.platform_results(skill_dir, cfg) == {}  # nothing is carried across a major version
    (skill / "SKILL.md").write_text('---\nname: core-demo\nmetadata:\n  version: "1.2.0"\n---\n')
    configure(root)
    rows = {r["skill"]: r for r in es.all_status(str(root))["skills"]}
    assert set(rows["core-demo"]["platforms"]["chirp"]) == {"s-model", "f-model"} and "platforms" not in rows["eng-other"]
    assert "score" not in json.dumps(rows["core-demo"]["platforms"])
    assert es.main(["hash", "--skill", "core-demo"], root=str(root)) == 0
    assert json.loads(capsys.readouterr().out)["platform_cases"] == {"chirp": hashes}
