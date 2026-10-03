"""Tests for skills/core-project-init/scripts/init_project.py: the docs/ decision (--docs, the state line, the
AGENTS.md line and the .gitignore block), the usage error with no argument, the field lines of the section
asset, and the slots the script registers against the layout contract. Offline, fictional data.

Run: uv run --with pytest pytest skills/core-project-init/scripts/tests
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INIT = ROOT / "skills/core-project-init/scripts/init_project.py"
SECTION = ROOT / "skills/core-project-init/assets/agents-md-section.md"
LAYOUT = ROOT / "contracts/project-layout.md"
WORK = ["/docs/workbench/", "/docs/business/", "/docs/brand/", "/docs/marketing/", "/docs/security/"]
CODE = ["/docs/product/", "/docs/design/", "/docs/engineering/", "/docs/ai/", "/docs/delivery/"]


def run(*args):
    r = subprocess.run([sys.executable, str(INIT), *args], capture_output=True, text=True)
    return r.returncode, (json.loads(r.stdout) if r.stdout.strip().startswith("{") else r.stdout), r.stderr


def project(tmp_path, gitignore=None):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "package.json").write_text('{"name": "lumen-notes"}\n', encoding="utf-8")
    if gitignore is not None:
        (proj / ".gitignore").write_text(gitignore, encoding="utf-8")
    return proj


def read(proj, rel):
    return (proj / rel).read_text(encoding="utf-8")


def ignored(proj):
    text = read(proj, ".gitignore")
    block = re.search(r"^# workbench:start.*?\n(.*?)^# workbench:end$", text, re.S | re.M)
    return block.group(1).split() if block else []


def test_without_docs_the_decision_is_undecided_and_nothing_is_ignored(tmp_path):
    proj = project(tmp_path)
    code, out, err = run("--root", str(proj), "--apply", "--name", "Lumen Notes", "--autonomy", "every-phase")
    assert code == 0, err
    state = read(proj, "docs/workbench/state.md")
    assert "- Docs in git: undecided\n" in state
    assert re.search(r"^- \[ \] Which workbench folders under docs/ go into git: all, code .* Recommended: code\.", state, re.M)
    assert "Documents in git: `undecided`" in read(proj, "AGENTS.md")
    assert not (proj / ".gitignore").exists()
    assert out["docs_in_git"] == "undecided" and out["gitignore"] == "untouched"
    assert any(line.startswith("- Documents in git: undecided") for line in out["report"])


def test_docs_code_keeps_work_data_out_and_keeps_the_rest_of_gitignore(tmp_path):
    proj = project(tmp_path, gitignore="node_modules/\n.env\n")
    code, out, err = run("--root", str(proj), "--apply", "--name", "Lumen Notes", "--autonomy", "milestones",
                         "--docs", "code")
    assert code == 0, err
    state = read(proj, "docs/workbench/state.md")
    assert "- Docs in git: code\n" in state and "Which workbench folders" not in state
    assert "Workbench folders under docs/ in git: code. (user)" in state
    assert read(proj, ".gitignore").startswith("node_modules/\n.env\n")
    assert ignored(proj) == WORK
    agents = read(proj, "AGENTS.md")
    assert "Documents in git: `code`" in agents and "checkpoints mode is `milestones`" in agents
    report = "\n".join(out["report"])
    assert "- Documents in git: code; kept out of git: docs/workbench/" in report and "(.gitignore block added)" in report


def test_update_decides_then_changes_the_docs_decision(tmp_path):
    proj = project(tmp_path, gitignore="dist/\n")
    assert run("--root", str(proj), "--apply", "--name", "Lumen Notes", "--autonomy", "every-phase")[0] == 0
    code, out, _ = run("--root", str(proj), "--detect")
    assert out["docs_in_git"] == "undecided"
    code, out, err = run("--root", str(proj), "--docs", "none")
    assert code == 0, err
    state = read(proj, "docs/workbench/state.md")
    assert "- Docs in git: none\n" in state and "- [x] Which workbench folders" in state
    assert "- Checkpoints: every-phase\n" in state, "a docs change leaves the mode as it is"
    assert ignored(proj) == WORK + CODE
    agents = read(proj, "AGENTS.md")
    assert "Documents in git: `none`" in agents and "checkpoints mode is `every-phase`" in agents
    assert agents.count("<!-- workbench:start -->") == 1
    code, out, err = run("--root", str(proj), "--docs", "all")
    assert code == 0, err
    assert read(proj, ".gitignore") == "dist/\n", "the block leaves; the user's lines stay"
    assert "(.gitignore block removed)" in "\n".join(out["report"])
    code, out, err = run("--root", str(proj), "--set-autonomy", "end")
    assert code == 0, err
    assert "Documents in git: `all`" in read(proj, "AGENTS.md"), "a mode change keeps the docs decision"


def test_an_older_state_without_the_line_gains_it(tmp_path):
    proj = project(tmp_path)
    assert run("--root", str(proj), "--apply", "--name", "widgets", "--autonomy", "every-phase")[0] == 0
    path = proj / "docs/workbench/state.md"
    path.write_text(read(proj, "docs/workbench/state.md").replace("- Docs in git: undecided\n", ""), encoding="utf-8")
    code, _, err = run("--root", str(proj), "--docs", "code")
    assert code == 0, err
    state = read(proj, "docs/workbench/state.md")
    assert re.search(r"^- Updated: \S+\n- Docs in git: code\n", state, re.M)


def test_a_bad_docs_value_and_no_argument_are_usage_errors_on_stderr(tmp_path):
    proj = project(tmp_path)
    code, out, err = run("--root", str(proj), "--apply", "--name", "x", "--autonomy", "end", "--docs", "some")
    assert code == 2 and out == "" and "--docs must be one of" in err
    code, out, err = run()
    assert code == 2 and out == "" and "Usage:" in err
    code, out, err = run("--help")
    assert code == 0 and "Usage:" in out


def test_the_section_asset_carries_the_field_lines_and_one_pair_of_markers():
    text = SECTION.read_text(encoding="utf-8")
    assert text.startswith("<!-- workbench:start -->\n") and text.rstrip("\n").endswith("<!-- workbench:end -->")
    assert text.count("<!-- workbench:start -->") == 1
    assert "{autonomy}" in text and "{docs}" in text
    assert ('`Skill check (optional, not an approval): answer "check: worked", "check: corrected" or '
            '"check: failed".`') in text
    assert "record --start" in text and "record --verdict" in text
    assert "only in a reply that delivers a finished output, never in one that asks a question or shows a confirmation gate" in text


def test_every_slot_the_script_registers_is_named_in_the_layout_contract():
    spec = importlib.util.spec_from_file_location("init_project", INIT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tree = LAYOUT.read_text(encoding="utf-8").split("```")[1]
    lines = {}
    for line in tree.splitlines():
        m = re.match(r"^[│├└─\s]*([a-z]+)/\s+#(.*)$", line)
        if m:
            lines[m.group(1)] = m.group(2)
    for _, slot in module.SLOT_PATTERNS:
        parts = slot.split("/")
        area, rest = parts[1], "/".join(parts[2:])
        name = rest.split("/")[-1] or rest.rstrip("/").split("/")[-1] + "/"
        assert area in lines, f"{slot}: the area docs/{area}/ is not in the layout tree"
        assert name in lines[area], f"{slot}: {name} is not named under docs/{area}/ in the layout tree"
