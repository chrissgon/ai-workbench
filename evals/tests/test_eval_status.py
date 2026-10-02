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


def benchmark(skill="core-demo", strong=(1.0, 0.5), floor=(0.9, 0.3), cases=(1, 2), runs=1, drop=()):
    means = {"with_skill": strong[0], "without_skill": strong[1], "with_skill.floor": floor[0], "without_skill.floor": floor[1]}
    summary = {name: {"pass_rate": {"mean": mean, "stddev": 0.0, "n": len(cases) * runs},
                      "cases": [{"case": c, "run": k, "pass_rate": mean} for c in cases for k in range(1, runs + 1)]}
               for name, mean in means.items() if name not in drop}
    return {"skill": skill, "runs": runs, "harness": "h", "floor_harness": "fh", "models": {"strong": "s-model", "floor": "f-model"},
            "grader": "s-model", "threshold": 0.8, "run_summary": summary, "failures": 0}


def record(root, skill="core-demo", **kwargs):
    path = root / "evals-workspace" / skill / "iteration-3" / "benchmark.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(benchmark(skill, **kwargs)))
    return es.main(["record", "--skill", skill, "--benchmark", str(path), "--date", "2030-01-02"], root=str(root))


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


@pytest.mark.parametrize("rel", ["SKILL.md", "scripts/check.py", "evals/files/input.md", "evals/evals.json"])
def test_the_hash_changes_with_any_file_of_the_skill(root, rel):
    skill = root / "skills" / "core-demo"
    first = es.content_hash(str(skill))
    (skill / rel).write_text((skill / rel).read_text() + "\n")
    assert es.content_hash(str(skill)) != first


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
    (skill / "evals" / "files" / "scripts" / "tests").mkdir(parents=True)
    (skill / "evals" / "files" / "scripts" / "tests" / "test_app.py").write_text("x\n")
    second = es.content_hash(str(skill))
    (skill / "scripts" / "tests_helper.py").write_text("x\n")
    assert len({first, second, es.content_hash(str(skill))}) == 3


def test_status_is_draft_then_evaluated_then_stale(root, capsys):
    assert status(root) == "draft"
    assert record(root) == 0
    assert "CURRENT hash" in capsys.readouterr().err
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
    path = root / "b.json"
    bench = benchmark(runs=2)
    bench["run_summary"]["with_skill.floor"]["cases"].pop()  # one floor run failed on the provider
    path.write_text(json.dumps(bench))
    assert es.main(["record", "--skill", "core-demo", "--benchmark", str(path)], root=str(root)) == 0
    rec = json.loads((root / "skills" / "core-demo" / "evals" / "result.json").read_text())
    assert rec["complete"] is False and rec["infra_failures"] == 1 and rec["gate"]["passed"] is True
    assert status(root) == "draft"


@pytest.mark.parametrize("kwargs, why", [
    ({"cases": (1,)}, "case(s) 2"),
    ({"drop": ("without_skill.floor",)}, "without_skill.floor did not run"),
    ({"floor": (None, 0.3)}, "no score"),
    ({"skill": "eng-other"}, "not 'core-demo'"),
])
def test_record_refuses_a_partial_benchmark(root, capsys, kwargs, why):
    path = root / "b.json"
    bench = benchmark(**kwargs)
    if kwargs.get("floor", (1,))[0] is None:
        for row in bench["run_summary"]["with_skill.floor"]["cases"]:
            row["pass_rate"] = None
    path.write_text(json.dumps(bench))
    with pytest.raises(SystemExit) as e:
        es.main(["record", "--skill", "core-demo", "--benchmark", str(path)], root=str(root))
    assert e.value.code == 1 and why in capsys.readouterr().err
    assert not (root / "skills" / "core-demo" / "evals" / "result.json").exists()


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
    (root / "skills" / "core-demo" / "evals" / "evals.json").write_text(json.dumps({"evals": [{"id": 1, "prompt": "new"}]}))
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
    path = root / "b.json"
    bench = benchmark()
    bench["early_ends"] = {"strong": {"attempts": 4, "early_ends": 0, "rate": 0.0, "by_case": {}},
                           "floor": {"attempts": 5, "early_ends": 1, "rate": 0.2, "by_case": {"1": 1}}}
    path.write_text(json.dumps(bench))
    assert es.main(["record", "--skill", "core-demo", "--benchmark", str(path)], root=str(root)) == 0
    record_file = root / "skills" / "core-demo" / "evals" / "result.json"
    rec = json.loads(record_file.read_text())
    assert rec["early_ends"] == {"strong": {"early_ends": 0, "rate": 0.0}, "floor": {"early_ends": 1, "rate": 0.2}}
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


# --- the baseline measured again, alone (eval_run.py --only without --update-record) ---------------

def baseline_bench(strong=0.2, floor=0.1, **changes):
    bench = benchmark(strong=(None, strong), floor=(None, floor), drop=("with_skill", "with_skill.floor"))
    return {**bench, **changes}


def test_update_baseline_replaces_the_two_scores_and_validates_the_field(root):
    record(root)
    skill_dir = str(root / "skills" / "core-demo")
    rec = es.update_baseline(skill_dir, baseline_bench(), 7, "2030-02-03")
    assert rec["scores"] == {"strong_with": 1.0, "strong_without": 0.2, "floor_with": 0.9, "floor_without": 0.1}
    assert rec["baseline"] == {"date": "2030-02-03", "iteration": 7, "runs": 1} and rec["iteration"] == 3
    es.write_record(skill_dir, rec)
    assert status(root) == "evaluated"
    rec["baseline"] = {"date": "yesterday"}
    es.write_record(skill_dir, rec)
    assert "baseline must be" in es.skill_status(skill_dir)["reason"]


def test_a_baseline_above_the_score_with_the_skill_makes_the_skill_draft(root):
    record(root)
    skill_dir = str(root / "skills" / "core-demo")
    rec = es.update_baseline(skill_dir, baseline_bench(strong=1.0, floor=0.5) | {"run_summary": {
        **baseline_bench()["run_summary"],
        "without_skill": {"pass_rate": {"mean": 1.0}, "cases": [{"case": c, "run": 1, "pass_rate": 1.0} for c in (1, 2)]}}}, 4, "2030-02-03")
    rec["scores"]["strong_with"] = 0.9  # as if run-to-run noise put the baseline above it
    rec["gate"] = es.gate(rec["scores"], rec["threshold"], rec["tolerance"], rec["measurement_version"])
    es.write_record(skill_dir, rec)
    row = es.skill_status(skill_dir)
    assert row["status"] == "draft" and "strong with the skill 0.9 is below without it 1.0" in row["reason"]


@pytest.mark.parametrize("how, why", [
    ("none", "no record to update"), ("stale", "another content of the skill"),
    ("model", "the record's floor model is f-model, this run's is other"),
    ("configured", "the configured one is new-floor"), ("threshold", "the record's threshold is 0.8, the configured one is 0.9"),
    ("case", "without_skill.floor has no graded run of case(s) 2"),
])
def test_update_baseline_refuses(root, how, why):
    skill_dir = str(root / "skills" / "core-demo")
    if how != "none":
        record(root)
    bench, config = baseline_bench(), {}
    if how == "stale":
        (root / "skills" / "core-demo" / "SKILL.md").write_text("# edited\n")
    elif how == "model":
        bench["models"]["floor"] = "other"
    elif how == "configured":
        config = {"floor_model": "new-floor", "strong_model": "s-model", "threshold": 0.8}
    elif how == "threshold":
        config = {"floor_model": "f-model", "strong_model": "s-model", "threshold": 0.9}
    elif how == "case":
        bench["run_summary"]["without_skill.floor"]["cases"].pop()
    with pytest.raises(ValueError) as e:
        es.update_baseline(skill_dir, bench, 4, "2030-02-03", config)
    assert why in str(e.value)


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
    assert es.evidence_refusal(str(root)) is None and record(root) == 0
    recorded = (root / "skills" / "core-demo" / "evals" / "result.json").read_text()
    configure(root, measurement_sha256=None)
    assert "carries no measurement_sha256: measurement version 2 is open" in es.evidence_refusal(str(root))
    with pytest.raises(SystemExit) as e:
        record(root, strong=(0.9, 0.5))
    assert e.value.code == 1 and "record refused" in capsys.readouterr().err
    assert (root / "skills" / "core-demo" / "evals" / "result.json").read_text() == recorded
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

