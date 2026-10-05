"""The limits of the task runtime that live in code, each with a test named after it (section B.2 of the
platform plan; contracts/runtime.md, "The limits"). Offline: the stand-in tree and adapter
(runtime/tests/standin_tree.py), and a project that is a git checkout built in the test's own folder.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_run_limits.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import standin_tree as st

lab = st.load("lab")
ops = st.load("ops")
workcopy = st.load("workcopy")
skill_meta = st.load("skill_meta")
project_config = st.load("project_config")

# The numbers of the limits built so far; each has exactly one test below named test_limit_<two digits>_...
BUILT = (1, 2, 3, 4, 5, 6)

SECTION_ASSET = st.REPO / "skills" / "core-project-init" / "assets" / "agents-md-section.md"
GIT_ENV = {"GIT_AUTHOR_NAME": "Demo Person", "GIT_AUTHOR_EMAIL": "demo@example.com",
           "GIT_COMMITTER_NAME": "Demo Person", "GIT_COMMITTER_EMAIL": "demo@example.com",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


@pytest.fixture
def tree(tmp_path, monkeypatch):
    built = st.build(tmp_path, monkeypatch, lab)
    monkeypatch.setattr(ops, "ROOT", str(built["tree"]))
    project = str(built["project"])
    ops.accept_config(project, project_config.load(project)["sha256"])
    built["prepared"] = tmp_path / "prepared"
    return built


def git(project: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(project), *args], check=True, capture_output=True, timeout=60,
                   env={**os.environ, **GIT_ENV})


def write(project: Path, rel: str, text: str) -> Path:
    path = project / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def checkout(project: Path, tracked: dict) -> None:
    """Make the project a git checkout whose one commit holds every file it has now and the files of tracked."""
    for rel, text in tracked.items():
        write(project, rel, text)
    git(project, "init", "-q")
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", "the project")


def meta_of(tree, skill: str, **changes) -> dict:
    return {**skill_meta.declared(str(tree["tree"] / "skills" / skill)), **changes}


def entering(tree, skill: str, *, web: bool, cfg_changes=None, **meta_changes) -> dict:
    cfg = {**project_config.load(str(tree["project"])), **(cfg_changes or {})}
    return workcopy.entering(str(tree["project"]), meta_of(tree, skill, **meta_changes), web=web, cfg=cfg,
                             settings_names=lab.settings_names(), prepared_dir=str(tree["prepared"]))


def rels(entered: dict) -> list:
    return [rel for _, rel in entered["files"]]


def reasons(entered: dict) -> dict:
    return {item["path"]: item["reason"] for item in entered["left_out"]}


def copied(run_dir: str) -> list:
    """The files the stand-in adapter saw in the copy (its files.txt), without the staged skill."""
    text = (Path(run_dir) / "outputs" / "files.txt").read_text(encoding="utf-8")
    return [line[2:] for line in text.splitlines() if line.startswith("./") and not line.startswith("./.h/")]


def token() -> str:
    return "AKIA" + "Q" * 16  # a text in a credential's format, built at run time


def test_limit_01_every_run_starts_from_a_new_copy_with_the_skill_staged_again(tree, monkeypatch):
    path = str(tree["project"])
    ops.request(path, "Tell me which market to go after first.", "demo")
    real = lab.run_skill

    def leaves_a_trace(*args, **kwargs):
        result = real(*args, **kwargs)
        cwd = Path(result["cwd"])
        (cwd / "stray.txt").write_text("left by the first run\n")
        staged = cwd / ".h" / "skills" / "demo-asks" / "SKILL.md"
        staged.write_text(staged.read_text() + "\nchanged by the first run\n")
        return result

    monkeypatch.setattr(lab, "run_skill", leaves_a_trace)
    first = ops.run_next(path)
    monkeypatch.setattr(lab, "run_skill", real)
    ops.answer(path, first["pending_id"], "Portugal.")
    second = ops.run_next(path)
    assert second["status"] == "ok" and second["run_dir"] != first["run_dir"]
    first_cwd, second_cwd = Path(first["run_dir"]) / "cwd", Path(second["run_dir"]) / "cwd"
    assert (first_cwd / "stray.txt").is_file() and "stray.txt" not in copied(second["run_dir"])
    assert not (second_cwd / "stray.txt").exists()
    staged = (second_cwd / ".h" / "skills" / "demo-asks" / "SKILL.md").read_text()
    assert staged == (tree["tree"] / "skills" / "demo-asks" / "SKILL.md").read_text()


def test_limit_02_only_versioned_files_documents_and_declared_machine_files_enter_and_never_the_store_or_the_configuration(tree):
    project = tree["project"]
    checkout(project, {"src/app.py": "print('app')\n", ".workbench-local/other/notes.json": "{}\n"})
    write(project, "docs/business/notes.md", "# Notes\n")          # a document, not tracked
    write(project, "scratch.txt", "not tracked, outside docs\n")    # no other file outside git
    os.symlink(tree["db"], project / "docs" / "store-link.sqlite")
    entered = entering(tree, "demo-writes", web=False)
    assert entered["kind"] == "general"
    assert {"src/app.py", "docs/business/notes.md", "docs/workbench/state.md"} <= set(rels(entered))
    assert "scratch.txt" not in rels(entered)
    why = reasons(entered)
    assert why[".workbench-local/other/notes.json"] == "work data the skill does not declare"
    assert why["docs/workbench/runtime.json"] == "the runtime's configuration never enters a run"
    assert why["docs/store-link.sqlite"] == "the store and the runtime's data never enter a run"
    for rel in why:
        assert rel not in rels(entered)
    assert set(entered["base"]) == set(rels(entered))


def test_limit_03_a_run_with_the_web_receives_only_the_artifacts_its_skill_declares(tree):
    project = tree["project"]
    checkout(project, {"src/app.py": "print('app')\n", "docs/business/market.md": "# Market\n",
                       "docs/business/other.md": "# Other\n"})
    entered = entering(tree, "demo-writes", web=True)
    declared = meta_of(tree, "demo-writes")
    assert entered["kind"] == "artifacts"
    assert rels(entered) == ["docs/business/market.md", "docs/workbench/state.md"]
    assert all(skill_meta.matches(declared["inputs"] + declared["outputs"] + declared["updates"], rel)
               for rel in rels(entered))


def test_limit_04_a_tools_configuration_files_are_removed_at_any_depth(tree):
    project, path = tree["project"], str(tree["project"])
    settings = [name for name in lab.settings_names() if "." in name and not name.startswith(".")]
    folder = next(name for name in lab.settings_names() if name.startswith("."))
    checkout(project, {f"{folder}/settings.json": "{}\n", f"a/b/c/{folder}/deep.json": "{}\n",
                       f"a/b/c/{settings[0]}": "{}\n", "src/app.py": "print('app')\n"})
    ops.request(path, "Tell me which market to go after first.", "demo")
    out = ops.run_next(path)
    assert out["status"] == "ok" and out["failure"] is None
    why = {item["path"]: item["reason"] for item in out["left_out"]}
    for rel in (f"{folder}/settings.json", f"a/b/c/{folder}/deep.json", f"a/b/c/{settings[0]}"):
        assert why[rel] == "a tool's configuration"
        assert rel not in copied(out["run_dir"])
    assert "src/app.py" in copied(out["run_dir"])


def test_limit_05_agents_md_enters_only_when_the_skill_declares_it_and_without_the_two_lines_the_container_cannot_serve(tree):
    project, path = tree["project"], str(tree["project"])
    text = "# Project\n\nOur own rules.\n\n" + SECTION_ASSET.read_text(encoding="utf-8") + "\nA closing line.\n"
    (project / "AGENTS.md").write_text(text, encoding="utf-8")
    before = (project / "AGENTS.md").read_bytes()
    kept_lines = [line for line in text.splitlines()
                  if not re.sub(r"^\d+\.\s+", "", line).startswith(workcopy.REMOVED_OPENINGS)]
    assert len(kept_lines) == len(text.splitlines()) - 2
    # Declared (demo-asks declares AGENTS.md): the copy's file has neither opening and every other line.
    ops.request(path, "Tell me which market to go after first.", "demo")
    out = ops.run_next(path)
    assert out["entered"]["agents_md"] == "whole"
    in_copy = (Path(out["run_dir"]) / "cwd" / "AGENTS.md").read_text(encoding="utf-8")
    assert in_copy.splitlines() == kept_lines
    for opening in workcopy.REMOVED_OPENINGS:
        assert opening not in in_copy
    # Not declared (demo-writes does not declare it): it does not enter.
    assert "AGENTS.md" not in rels(entering(tree, "demo-writes", web=False))
    # Protected: only the section enters for a skill of a business area; the whole file for a code area.
    protected = {"protected_paths": ["AGENTS.md"]}
    section = entering(tree, "demo-asks", web=False, cfg_changes=protected)
    assert section["agents_md"] == "section"
    prepared = Path(dict((rel, src) for src, rel in section["files"])["AGENTS.md"]).read_text(encoding="utf-8")
    assert prepared.startswith(workcopy.SECTION_START) and "Our own rules." not in prepared
    assert workcopy.SECTION_END in prepared and "Skill check:" not in prepared
    whole = entering(tree, "demo-asks", web=False, cfg_changes=protected, area="engineering")
    assert whole["agents_md"] == "whole"
    # Protected and without a workbench section: nothing enters, and the reason says why.
    (project / "AGENTS.md").write_text("# Project\n\nOur own rules.\n", encoding="utf-8")
    none = entering(tree, "demo-asks", web=False, cfg_changes=protected)
    assert none["agents_md"] is None and reasons(none)["AGENTS.md"] == "protected, and it has no workbench section"
    (project / "AGENTS.md").write_bytes(before)
    assert (project / "AGENTS.md").read_bytes() == before


def test_limit_06_no_credential_enters_the_container(tree):
    project = tree["project"]
    checkout(project, {".env": "LOCAL_ONLY=1\n", "deploy.pem": "certificate\n",
                       "notes/handover.txt": f"the key is {token()}\n",
                       ".env.example": "API_KEY=<your key here>\nPASSWORD=<choose one>\n"})
    entered = entering(tree, "demo-writes", web=False)
    why = reasons(entered)
    assert why[".env"] == why["deploy.pem"] == "a credential file by its name"
    assert why["notes/handover.txt"].startswith("holds what looks like a credential (")
    assert ".env.example" in rels(entered)
    for rel in (".env", "deploy.pem", "notes/handover.txt"):
        assert rel not in rels(entered)
    assert token() not in repr(entered["left_out"])
    assert workcopy.credential_findings(f"one\nkey {token()}\ntwo") and workcopy.credential_findings("API_KEY=<x>\n") == []


def test_the_two_lines_are_put_back_where_they_were():
    text = "# Project\n\nOur own rules.\n\n" + SECTION_ASSET.read_text(encoding="utf-8") + "\nA closing line.\n"
    run_text, removed = workcopy.agents_md_for_run(text, "whole")
    assert len(removed) == 2 and run_text != text
    assert workcopy.agents_md_restored(run_text, removed) == text


def test_every_limit_built_so_far_has_a_test_named_after_it():
    names = [name for name in globals() if name.startswith("test_limit_")]
    for number in BUILT:
        assert len([n for n in names if n.startswith(f"test_limit_{number:02d}_")]) == 1, number
    assert len(names) == len(BUILT)


def test_the_prepared_folder_of_a_run_is_removed_after_it(tree):
    path = str(tree["project"])
    ops.request(path, "Tell me which market to go after first.", "demo")
    out = ops.run_next(path)
    assert out["status"] == "ok"
    assert not (tree["data"] / ops.PREPARED_DIR / str(out["run_id"])).exists()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
