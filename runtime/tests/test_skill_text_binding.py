"""Tests without a model that bind the runtime's constants to the text of the skills, templates and contracts
they come from. Those files are edited by other people for other reasons; a reworded sentence would silently
turn a `question` into `unclassified`, or let the two AGENTS.md lines through. Each test fails with a message
that names the runtime constant to look at. No skill, template or contract is edited to make a binding pass:
when one fails on the repository as it is, the constant is wrong, or the text changed after the runtime was
written.

Every binding of stage 2 of the platform plan, and where its test is:

| The runtime relies on | Comes from | Test |
|---|---|---|
| `workcopy.REMOVED_OPENINGS`, `SECTION_START`, `SECTION_END` | `skills/core-project-init/assets/agents-md-section.md`, `init_project.py` | `test_the_two_lines_the_copy_loses_are_in_the_section_core_project_init_writes` (here) |
| `state_merge` section titles, the Artifacts header, the `draft` status | `contracts/state.md`, `STATE_TEMPLATE` of `init_project.py` | `test_the_state_files_sections_are_the_contracts` (here) |
| `state_merge.OPEN_QUESTION` (the form the merge writes) and `SKILL_PREFIXES` | `contracts/state.md`, `init_project.py`, the prefixes table of `AGENTS.md` | `test_the_open_question_form_the_merge_writes_is_the_contracts` (here) |
| the owner the merge names for a missing state file | `core-project-init`'s `outputs` | `test_the_state_file_is_owned_by_the_skill_the_merge_names` (here) |
| `endings` constants (`writes it`, `run it first`, `Recommended:`, `(planned)`, `OPEN-<n>`, the asking reply) | `templates/capability.SKILL.md`, `AGENTS.md` | `test_the_sentences_the_classifier_reads_are_in_the_templates` (here) |
| `endings` constants read from single skills (`writes them`, `writes that section`, `writes the PRD`, ``run `<skill>` first``, `? (yes/no)`) | the skills each comment names | `test_the_sentences_the_classifier_reads_from_skills_are_still_there` (here) |
| rule 3 of the classifier, for the skills in use | the asking template of each skill | `test_every_skill_in_use_asks_with_an_opening_the_classifier_knows` (here) |
| `workcopy.CODE_AREAS` | the skills' `metadata.area` | `test_the_code_areas_are_the_areas_of_the_skills_that_work_on_code` (here) |
| `ops.task_prompt` | the flow files | `test_the_prompt_of_a_run_names_no_skill_and_keeps_its_form` (here) |
| a manifest's `asking_openings` | the skill's asking template | `test_the_asking_openings_of_a_manifest_are_the_first_line_of_the_skills_asking_template` (`test_runtime_manifest.py`) |
| a manifest's checker commands | the skill's `scripts/` and its text | `test_every_checker_a_manifest_names_is_a_script_of_the_skill_and_is_named_in_its_text` (`test_runtime_manifest.py`) |
| `ops.VERDICTS` and the recorder's command line | `scripts/evidence.py` | `test_the_recorder_still_has_the_interface_the_runtime_calls` (`test_use_and_key.py`) |
| the two removed lines put back where they were | `workcopy.agents_md_for_run`, `agents_md_restored` | `test_the_two_lines_are_put_back_where_they_were` (`test_run_limits.py`) |

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_skill_text_binding.py
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import standin_tree as st

workcopy = st.load("workcopy")
state_merge = st.load("state_merge")
endings = st.load("endings")
manifest = st.load("manifest")
skill_meta = st.load("skill_meta")
ops = st.load("ops")

REPO = Path(__file__).resolve().parents[2]
INIT = REPO / "skills" / "core-project-init"
LIST_NUMBER = re.compile(r"^\s*\d+\.\s+")
NONE = {"created": [], "modified": [], "deleted": [], "unchanged": []}


def text(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def skill_names() -> list:
    return sorted(p.name for p in (REPO / "skills").iterdir() if (p / "SKILL.md").is_file())


def state_template() -> str:
    tree = ast.parse(text("skills/core-project-init/scripts/init_project.py"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "STATE_TEMPLATE" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("STATE_TEMPLATE is gone from init_project.py: look at state_merge's section titles")


def contract_template() -> str:
    """The fenced block of contracts/state.md that holds the state file's template."""
    blocks = re.findall(r"^```[a-z]*\n(.*?)^```", text("contracts/state.md"), re.S | re.M)
    found = [b for b in blocks if "## Artifacts" in b]
    assert found, "contracts/state.md has no template block with ## Artifacts: look at state_merge's section titles"
    return found[0]


def test_the_two_lines_the_copy_loses_are_in_the_section_core_project_init_writes():
    lines = text("skills/core-project-init/assets/agents-md-section.md").strip("\n").splitlines()
    assert lines[0] == workcopy.SECTION_START and lines[-1] == workcopy.SECTION_END, \
        "the section's markers changed: look at workcopy.SECTION_START and SECTION_END"
    for opening in workcopy.REMOVED_OPENINGS:
        hits = [line for line in lines if LIST_NUMBER.sub("", line, count=1).startswith(opening)]
        assert len(hits) == 1, f"{opening!r} starts {len(hits)} lines of the section: look at workcopy.REMOVED_OPENINGS"
    script = text("skills/core-project-init/scripts/init_project.py")
    assert workcopy.SECTION_START in script and workcopy.SECTION_END in script, \
        "init_project.py writes other markers: look at workcopy.SECTION_START and SECTION_END"


def test_the_state_files_sections_are_the_contracts():
    titles = [state_merge.ARTIFACTS, state_merge.DECISIONS, state_merge.QUESTIONS, *state_merge.PROTECTED]
    header = "| Artifact | Owner skill | Status | Updated |"
    for name, block in (("contracts/state.md", contract_template()), ("STATE_TEMPLATE", state_template())):
        headings = {line[3:].strip() for line in block.splitlines() if line.startswith("## ")}
        missing = [t for t in titles if t not in headings]
        assert not missing, f"{name} has no section {missing}: look at state_merge's section titles"
        assert header in block, f"{name} has another Artifacts header: look at state_merge's reading of the table"
    assert "`Status` is `draft`, `approved` or `skipped`" in text("contracts/state.md"), \
        "the statuses of an artifact row changed: look at state_merge's rule on draft rows"


def test_the_open_question_form_the_merge_writes_is_the_contracts():
    block = contract_template()
    section = block.split("## Open questions", 1)[1]
    items = [line for line in section.splitlines() if line.strip()]
    assert items and all(line.startswith(state_merge.OPEN_QUESTION + " ") for line in items), \
        "the open questions of contracts/state.md's template are in another form: look at state_merge.OPEN_QUESTION"
    assert "Open questions are checkboxes" in text("contracts/state.md"), \
        "contracts/state.md no longer says open questions are checkboxes: look at state_merge.OPEN_QUESTION"
    assert 'f"' + state_merge.OPEN_QUESTION + ' {q}' in text("skills/core-project-init/scripts/init_project.py"), \
        "core-project-init writes open questions in another form: look at state_merge.OPEN_QUESTION"
    # What the merge writes for a question read in another form is the contract's form.
    base = block.replace(items[0] + "\n", "")
    returned = block.replace(items[0], "- OPEN-1 " + state_merge._question(items[0])[0])
    written = state_merge.merge_report(base, base, returned, "flow-fix-bug")["accepted"]
    assert [a["line"] for a in written] == ["- [ ] OPEN-1 " + state_merge._question(items[0])[0]]
    # Who raised a question is read from the skill prefixes of AGENTS.md.
    prefixes = set(re.findall(r"^\| `([a-z]+)-` \|", text("AGENTS.md"), re.M))
    assert prefixes == set(state_merge.SKILL_PREFIXES), \
        "the area prefixes of AGENTS.md changed: look at state_merge.SKILL_PREFIXES"


def test_the_state_file_is_owned_by_the_skill_the_merge_names():
    assert "core-project-init writes it" in text("runtime/state_merge.py")
    assert "docs/workbench/state.md" in skill_meta.declared(str(INIT))["outputs"], \
        "core-project-init no longer writes the state file: look at the message of state_merge's rule 2"


def test_the_sentences_the_classifier_reads_are_in_the_templates():
    template = text("templates/capability.SKILL.md")
    assert "writes it and to run it first" in template, "look at endings.MISSING_INPUT"
    assert endings.RECOMMENDED.search(template), "look at endings.RECOMMENDED"
    assert re.search(r"^The reply that asks.*\n\s*\n```", template, re.M), \
        "the asking reply of the template is not a fenced block after 'The reply that asks': look at manifest.ASKING"
    agents = text("AGENTS.md")
    assert endings.PLANNED in agents, "look at endings.PLANNED"
    assert "OPEN-<n>" in agents, "look at endings.OPEN_MARK"


def test_the_sentences_the_classifier_reads_from_skills_are_still_there():
    expected = {
        "skills/brand-strategy/SKILL.md": "writes them and to run it first",
        "skills/eng-tradeoffs/SKILL.md": "writes that section and to run it first",
        "skills/product-roadmap/SKILL.md": "writes the PRD",
        "skills/design-ux-flows/SKILL.md": "Next: run `product-prd` first",
        "skills/design-execute/SKILL.md": "Proceed? (yes/no)",
        "skills/ops-branch-sync/SKILL.md": "Push? (yes/no)",
        "skills/eng-security-review/SKILL.md": "alerts? (yes/no)",
    }
    source = text("runtime/endings.py")
    for rel, sentence in expected.items():
        assert rel in source, f"endings.py no longer cites {rel}: update this table"
        assert sentence in text(rel), f"{rel} no longer holds {sentence!r}: look at endings.MISSING_INPUT and YES_NO"
        constant = endings.YES_NO if "yes/no" in sentence else endings.MISSING_INPUT
        assert constant.search(sentence), f"endings does not read {sentence!r}: look at MISSING_INPUT and YES_NO"


def test_every_skill_in_use_asks_with_an_opening_the_classifier_knows():
    for skill in manifest.skills_in_use(str(REPO)):
        facts = manifest.ending_facts(str(REPO), skill)
        firsts = manifest.asking_openings_of(text(f"skills/{skill}/SKILL.md"))
        assert facts["asking_openings"], f"{skill} has no asking opening: look at its manifest"
        for opening in facts["asking_openings"]:
            assert any(first.startswith(opening) for first in firsts), \
                f"{skill}: {opening!r} does not start the first line of its asking template"
            reply = f"{opening}: two points are undecided.\n\n1. Which country? Recommended: yours."
            got = endings.classify(reply, NONE, [], [], [], facts=facts)[0]
            assert got == "question", f"{skill}: a reply that opens with {opening!r} is {got}: look at rule 3"


def test_the_code_areas_are_the_areas_of_the_skills_that_work_on_code():
    found = {}
    for name in skill_names():
        found[name] = skill_meta.declared(str(REPO / "skills" / name))["area"]
    for name, area in found.items():
        if name.startswith(("eng-", "ops-")):
            assert area in workcopy.CODE_AREAS, f"{name} is in {area}: look at workcopy.CODE_AREAS"
        elif not name.startswith("flow-"):
            assert area not in workcopy.CODE_AREAS, f"{name} is in {area}: look at workcopy.CODE_AREAS"
    # A flow takes the area of the work it orchestrates: one that runs code skills is in a code area too.
    for name in (n for n in found if n.startswith("flow-") and found[n] in workcopy.CODE_AREAS):
        assert re.search(r"`(?:eng|ops)-[a-z-]+`", text(f"skills/{name}/SKILL.md")), \
            f"{name} is in {found[name]} and runs no code skill: look at workcopy.CODE_AREAS"
    assert sum(1 for n, a in found.items() if n.startswith("eng-") and a == "engineering") >= 12
    assert sum(1 for n, a in found.items() if n.startswith("ops-") and a == "delivery") >= 4


def test_the_prompt_of_a_run_names_no_skill_and_keeps_its_form():
    names = skill_names()
    flows = sorted((REPO / "flows").glob("*.json"))
    assert flows
    for flow in flows:
        for task in json.loads(flow.read_text(encoding="utf-8"))["tasks"]:
            prompt = ops.task_prompt("Tell me which market to go after first.", task["text"], [])
            named = [n for n in names if re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", prompt)]
            assert not named, f"{flow.name}, task {task['key']}: the prompt names {named}"
            assert prompt.count("For this task: ") == 1, f"{flow.name}, task {task['key']}: look at ops.task_prompt"
