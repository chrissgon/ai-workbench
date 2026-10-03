"""Offline tests of the artifact contract: the seven rules scripts/validate.py reports as errors, and
scripts/owner_table.py, which generates the table of owning skills. Each test writes a small tree to a
temporary folder.

Run: uv run --with pytest pytest scripts/tests/test_validate_contract.py
"""
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate = load("validate_contract_under_test", "scripts/validate.py")
owner_table = load("owner_table_under_test", "scripts/owner_table.py")

LAYOUT = """# Layout

## Placeholders

| Placeholder | Stands for |
|-------------|------------|
| `<task>` | a task |
| `<NNNN>` | a number |
| `<title>` | a title |

## Slots no built skill writes

| Path | Provided by |
|------|-------------|
| `docs/business/idea.md` | planned: biz-idea |
| `docs/workbench/runtime.json` | user |

## Owning skills

<!-- owner-table:begin -->
<!-- owner-table:end -->
"""


def skill(name, inputs=(), outputs=(), updates=()):
    return {"name": name, "where": f"skills/{name}", "inputs": list(inputs), "outputs": list(outputs),
            "updates": list(updates)}


def tree(tmp_path, layout=LAYOUT, generator=True):
    if layout is not None:
        (tmp_path / "contracts").mkdir()
        (tmp_path / "contracts" / "project-layout.md").write_text(layout, encoding="utf-8")
    if generator:
        (tmp_path / "scripts").mkdir()
        shutil.copy(REPO / "scripts" / "owner_table.py", tmp_path / "scripts" / "owner_table.py")
    return tmp_path


def check(root, skills, write_table=True):
    if write_table and (root / "contracts" / "project-layout.md").is_file():
        owner_table.write(skills, str(root))
    report = validate.Report()
    validate.check_contract(skills, report, root=str(root))
    assert report.warnings == []  # every rule of the contract is an error since the close of phase C
    return report


def found(report, rule):
    return [(w["where"], w["message"]) for w in report.errors if w.get("rule") == rule]


def rules(report):
    return sorted({w["rule"] for w in report.errors})


STATE, PLAN = "docs/workbench/state.md", "docs/engineering/plans/<task>.md"
GOOD = [skill("core-init", outputs=[STATE]),
        skill("eng-cause", inputs=[STATE], outputs=[PLAN], updates=[STATE]),
        skill("eng-tests", inputs=[STATE, PLAN, "docs/workbench/runtime.json"], updates=[PLAN, STATE]),
        skill("biz-market", inputs=["docs/business/idea.md"], outputs=["docs/business/market.md"], updates=[STATE])]


def test_a_tree_that_follows_the_contract_gets_no_warning_and_no_note(tmp_path):
    report = check(tree(tmp_path), GOOD)
    assert report.errors == [] and report.notes == []


def test_rule_1_an_updated_path_has_an_owner(tmp_path):
    report = check(tree(tmp_path), [skill("eng-tests", updates=[PLAN, "docs/marketing/calendar.md"])])
    assert found(report, "contract-updates") == [("skills/eng-tests", "[contract-updates] updates "
                                                  f"{PLAN}, docs/marketing/calendar.md: no skill's outputs lists it, "
                                                  "so it has no owner")]


def test_rule_2_an_artifact_has_one_owner_and_placeholders_match_as_wildcards(tmp_path):
    report = check(tree(tmp_path), [skill("eng-cause", outputs=[PLAN]), skill("eng-tests", outputs=[PLAN]),
                                    skill("eng-other", outputs=["docs/engineering/plans/<title>.md"])])
    owners = found(report, "contract-owner")
    assert [w for w, _ in owners] == ["skills/eng-cause", "skills/eng-tests", "skills/eng-other"]
    assert "(also eng-tests, eng-other)" in owners[0][1]
    spelled = found(report, "contract-placeholder")
    assert len(spelled) == 1 and spelled[0][0] == "skills/eng-other"
    assert "the same artifact is spelled docs/engineering/plans/<task>.md in eng-cause" in spelled[0][1]


def test_rule_3_an_input_has_an_owner_or_a_slot(tmp_path):
    report = check(tree(tmp_path), [skill("biz-market", inputs=["docs/business/idea.md", "docs/business/pricing.md",
                                                                 "docs/workbench/runtime.json"])])
    assert found(report, "contract-inputs") == [
        ("skills/biz-market", "[contract-inputs] input docs/business/pricing.md: no skill's outputs lists it and it "
         "is not in the table \"Slots no built skill writes\" of contracts/project-layout.md")]


def test_rule_3_a_slot_row_is_stale_once_a_skill_owns_it_or_its_planned_skill_is_built(tmp_path):
    layout = LAYOUT.replace("| `docs/workbench/runtime.json` | user |",
                            "| `docs/workbench/runtime.json` | user |\n| `docs/a.md` | planned: biz-market |\n"
                            "| `docs/b.md` | someone |")
    report = check(tree(tmp_path, layout), [skill("biz-idea", outputs=["docs/business/idea.md"]), skill("biz-market")])
    assert [m for _, m in found(report, "contract-inputs")] == [
        "[contract-inputs] slot docs/business/idea.md: biz-idea owns it now: remove the row",
        "[contract-inputs] slot docs/a.md: biz-market is built: remove the row and declare the path in its outputs",
        "[contract-inputs] slot docs/b.md: \"Provided by\" is 'someone'; it is user or planned: <skill>"]
    assert {w for w, _ in found(report, "contract-inputs")} == {"contracts/project-layout.md"}


def test_rule_3_reads_the_contracts_owner_table_for_a_tree_with_no_other_skill(tmp_path):
    """A flow made from the template in a folder an eval case builds: the owners are in the contract it brings."""
    root = tree(tmp_path, generator=False)
    owner_table.write([skill("core-init", outputs=[STATE]), skill("eng-cause", outputs=[PLAN])], str(root))
    flow = [skill("flow-probe", inputs=[STATE, "docs/engineering/plans/<task>.md"], updates=[STATE])]
    report = check(root, flow, write_table=False)
    assert report.errors == []
    assert report.notes == ["[contract-owner-table] skipped: scripts/owner_table.py is not in this tree"]


def test_rule_4_no_path_is_in_outputs_and_updates_of_one_skill(tmp_path):
    report = check(tree(tmp_path), [skill("core-init", outputs=[STATE], updates=[STATE])])
    assert rules(report) == ["contract-overlap"]


@pytest.mark.parametrize("path, why", [
    ("docs/workbench/research/<topic>.md", "<topic> is not in the vocabulary"),
    ("docs/workbench/research/*.md", "a wildcard other than a placeholder"),
    ("docs/engineering/adr/NNNN-title.md", "a wildcard other than a placeholder"),
    ("docs/engineering/plans/<task>.md#impact", "a wildcard other than a placeholder"),
    ("docs/design/{a,b}.md", "a wildcard other than a placeholder"),
    ("docs/design/<Task>.md", "<Task> is not in the vocabulary"),
])
def test_rule_5_only_the_vocabulary_and_no_other_wildcard(tmp_path, path, why):
    report = check(tree(tmp_path), [skill("eng-demo", outputs=[path])])
    messages = found(report, "contract-placeholder")
    assert len(messages) == 1 and why in messages[0][1]


def test_rule_5_accepts_a_folder_and_the_number_placeholder(tmp_path):
    report = check(tree(tmp_path), [skill("eng-demo", outputs=["docs/engineering/adr/<NNNN>-<title>.md",
                                                               "docs/design/results/<task>/"])])
    assert report.errors == []


def test_rule_6_the_graph_from_owner_to_reader_has_no_cycle_and_a_self_edge_is_not_one(tmp_path):
    report = check(tree(tmp_path), [skill("eng-a", inputs=["docs/a.md", "docs/c.md"], outputs=["docs/a.md"]),
                                    skill("eng-b", inputs=["docs/a.md"], outputs=["docs/b.md"]),
                                    skill("eng-c", inputs=["docs/b.md"], outputs=["docs/c.md"]),
                                    skill("eng-d", inputs=["docs/c.md", "docs/d.md"], outputs=["docs/d.md"])])
    assert found(report, "contract-cycle") == [("skills", "[contract-cycle] the graph \"owner of a path -> skill "
                                                "that reads it\" has a cycle of 3 skills, so it gives no order: "
                                                "eng-a, eng-b, eng-c")]


def test_updates_adds_no_edge_to_the_graph(tmp_path):
    report = check(tree(tmp_path), [skill("eng-a", inputs=["docs/b.md"], outputs=["docs/a.md"]),
                                    skill("eng-b", outputs=["docs/b.md"], updates=["docs/a.md"])])
    assert report.errors == []


def test_rule_7_the_generated_table_equals_the_frontmatters(tmp_path):
    root = tree(tmp_path)
    assert check(root, GOOD).errors == []
    changed = GOOD[:-1] + [skill("biz-market", outputs=["docs/business/market.md"])]
    assert found(check(root, changed, write_table=False), "contract-owner-table") == [
        ("contracts/project-layout.md", "[contract-owner-table] the table of owning skills differs from the skills' "
         "frontmatter: run python3 scripts/owner_table.py")]


def test_without_the_layout_contract_the_rules_that_need_it_are_skipped_with_a_note(tmp_path):
    report = check(tree(tmp_path, layout=None, generator=False),
                   [skill("flow-probe", inputs=[STATE], outputs=["docs/x/<anything>.md"])])
    assert rules(report) == ["contract-inputs"]  # as before the contract: an input nobody in the tree writes
    assert len(report.notes) == 2 and all("skipped: " in n and "is not in this tree" in n for n in report.notes)


def test_updates_is_a_required_key_and_must_be_a_list(tmp_path, monkeypatch):
    monkeypatch.setattr(validate, "SKILLS", str(tmp_path / "skills"))
    folder = tmp_path / "skills" / "eng-demo"
    folder.mkdir(parents=True)
    head = "---\nname: eng-demo\ndescription: Does a thing. Use when asked.\nlicense: MIT\nmetadata:\n" \
           "  area: engineering\n  kind: capability\n  inputs: []\n  outputs: [docs/a.md]\n{}  requires: []\n" \
           "  side_effects: []\n  version: \"0.1\"\n---\n\n# Demo\n"
    (folder / "SKILL.md").write_text(head.format(""), encoding="utf-8")
    report = validate.Report()
    got = validate.check_skill("eng-demo", report, {})
    assert [w["message"] for w in report.warnings] == ["[meta-keys] missing: metadata.updates"]
    assert got["outputs"] == ["docs/a.md"] and got["updates"] == []
    (folder / "SKILL.md").write_text(head.format("  updates: docs/b.md\n"), encoding="utf-8")
    report = validate.Report()
    validate.check_skill("eng-demo", report, {})
    assert [e["message"] for e in report.errors] == ["metadata.updates must be a list"]
    assert validate.declarations(str(tmp_path)) == [skill("eng-demo", outputs=["docs/a.md"])]


def test_the_rules_are_errors_since_the_close_of_phase_c_and_leave_the_flags_document():
    assert not [r for r in validate.WARNING_RULES if r.startswith("contract-")]
    assert [r for r in validate.ERROR_RULES if r.startswith("contract-")] == [
        "contract-updates", "contract-owner", "contract-inputs", "contract-overlap", "contract-placeholder",
        "contract-cycle", "contract-owner-table"]


# --- scripts/owner_table.py ---------------------------------------------------------

def test_the_table_has_one_row_per_artifact_with_its_owner_and_its_updaters():
    assert owner_table.table(GOOD) == (
        "| Artifact | Owning skill | Updated by |\n|----------|--------------|------------|\n"
        "| `docs/business/market.md` | biz-market | - |\n"
        "| `docs/engineering/plans/<task>.md` | eng-cause | eng-tests |\n"
        "| `docs/workbench/state.md` | core-init | biz-market, eng-cause, eng-tests |\n")


def test_writing_touches_only_the_block_and_is_idempotent(tmp_path):
    root = tree(tmp_path)
    owner_table.write(GOOD, str(root))
    text = (root / "contracts" / "project-layout.md").read_text(encoding="utf-8")
    before, after = LAYOUT.split("<!-- owner-table:begin -->\n")
    assert text.startswith(before + "<!-- owner-table:begin -->\n| Artifact |") and text.endswith(after)
    owner_table.write(GOOD, str(root))
    assert (root / "contracts" / "project-layout.md").read_text(encoding="utf-8") == text
    assert owner_table.current(GOOD, str(root)) is True and owner_table.current(GOOD[:1], str(root)) is False
    assert owner_table.read_owners(str(root))["docs/engineering/plans/*.md"] == ["eng-cause"]


def run(*args):
    return subprocess.run([sys.executable, str(REPO / "scripts" / "owner_table.py"), *args],
                          capture_output=True, text=True)


def test_the_command_line(tmp_path):
    assert run("--help").returncode == 0 and "Usage:" in run("--help").stdout
    assert run("--nope").returncode == 2 and run("--root").returncode == 2
    assert run("--check", "--print").returncode == 2
    empty = run("--check", "--root", str(tmp_path))
    assert empty.returncode == 2 and "missing or has no" in empty.stderr and "Traceback" not in empty.stderr
    root = tree(tmp_path)
    (root / "scripts" / "validate.py").write_text((REPO / "scripts" / "validate.py").read_text(encoding="utf-8"),
                                                  encoding="utf-8")
    skill_dir = root / "skills" / "eng-demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: eng-demo\nmetadata:\n  outputs: [docs/a.md]\n---\n", encoding="utf-8")
    stale = run("--check", "--root", str(root))
    assert stale.returncode == 1 and "run python3 scripts/owner_table.py" in stale.stderr
    assert run("--root", str(root)).returncode == 0 and run("--check", "--root", str(root)).returncode == 0
    assert "| `docs/a.md` | eng-demo | - |" in run("--print", "--root", str(root)).stdout


def test_the_table_of_this_repository_is_current_and_names_every_owned_path():
    skills = validate.declarations(str(REPO))
    assert owner_table.current(skills, str(REPO)) is True
    assert len(owner_table.rows(skills)) >= 40
