"""Tests of runtime/lab.py, the one file of runtime/ that talks to the lab: what a run sees, what comes back,
how a failed attempt is handled, and which names of evals/eval_run.py the file may read. Offline: the adapter is
a stand-in shell script and runs on this machine (runtime/tests/standin_tree.py); every name is invented.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_lab_facade.py
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest

import standin_tree as st

lab = st.load("lab")


@pytest.fixture
def tree(tmp_path, monkeypatch):
    return st.build(tmp_path, monkeypatch, lab)


def run(tree, tmp_path, skill="demo-asks", prompt="please\n", files=(), **more):
    with lab.session():
        return lab.run_skill(skill, prompt, list(files), str(tmp_path / "data" / "run-1"), **more)


def test_a_run_sees_the_staged_skill_and_the_given_files_and_nothing_else(tree, tmp_path):
    state = tree["project"] / "docs" / "workbench" / "state.md"
    out = run(tree, tmp_path, files=[(str(state), "docs/workbench/state.md")])
    assert out["status"] == "ok" and out["failure"] is None and out["response"].startswith("Nothing was searched")
    seen = (Path(out["outputs"]) / "files.txt").read_text().split("\n")[:-1]
    assert "./docs/workbench/state.md" in seen and "./.h/skills/demo-asks/SKILL.md" in seen
    assert "./.h/skills/demo-asks/scripts/check.py" in seen
    assert not [p for p in seen if "/evals/" in p or "/scripts/tests/" in p]  # staged as in a lab run
    assert not [p for p in seen if "AGENTS.md" in p or "runtime.json" in p]  # only what the caller listed
    assert out["staged"] == [os.path.join(".h", "skills", "demo-asks")]
    assert out["changes"] == {"created": [], "modified": [], "deleted": [], "unchanged": ["docs/workbench/state.md"]}
    assert (out["model"], out["adapter"], out["tier"], out["web"]) == ("m", "h", "strong", False)
    assert out["timing"]["skills_loaded"] == ["demo-asks"] and out["counts"]["attempts"] == 1


def test_the_folders_of_a_run_come_back_to_its_run_folder_and_the_prompt_is_kept(tree, tmp_path):
    out = run(tree, tmp_path, prompt="first line\n--- the user's answer 1 ---\nhere\n")
    dest = tmp_path / "data" / "run-1"
    assert (out["run_dir"], out["cwd"], out["outputs"]) == (str(dest), str(dest / "cwd"), str(dest / "outputs"))
    assert (dest / "prompt.md").read_text() == "first line\n--- the user's answer 1 ---\nhere\n"
    assert (dest / "cwd" / "docs" / "business" / "market.md").is_file() and (dest / "outputs" / "response.md").is_file()
    assert out["changes"]["created"] == ["docs/business/market.lint.json", "docs/business/market.md",
                                         "docs/workbench/state.md", "notes.txt"]
    assert not [p for p in os.listdir(tmp_path) if p.startswith("eval-")]  # the fresh folder is outside and removed


def test_a_run_whose_adapter_fails_is_made_again_and_the_failed_attempt_is_kept(tree, tmp_path):
    st.fail(tree["adapter"], "adapter", 1)
    out = run(tree, tmp_path)
    assert out["status"] == "ok" and out["counts"]["attempts"] == 2 and out["counts"]["adapter_failures"] == 1
    assert st.calls(tree["adapter"]) == ["demo-asks 1", "demo-asks 2"]
    assert "the provider is down" in (tmp_path / "data" / "run-1" / "failed-1" / "outputs" / "error.log").read_text()


@pytest.mark.parametrize("kind, expected, calls", [("adapter", "adapter", 3), ("refused", "refused", 3),
                                                    ("early", "early_end", 3), ("auth", "auth", 1)])
def test_a_failure_on_every_attempt_is_returned_with_its_kind_and_a_refused_key_is_never_retried(tree, tmp_path, kind, expected, calls):
    st.fail(tree["adapter"], kind, 9)
    out = run(tree, tmp_path)
    assert out["status"] == "failed" and out["failure"]["kind"] == expected and out["changes"] is None
    assert len(st.calls(tree["adapter"])) == calls  # the gate's two retries, and none for a refused key
    if expected == "auth":
        assert out["failure"]["detail"] == "HTTP 401" and "no variable" in out["failure"]["reason"]


def test_a_run_past_its_timeout_is_stopped_and_fails_as_a_timeout(tree, tmp_path):
    st.fail(tree["adapter"], "timeout", 9)
    out = run(tree, tmp_path, timeout=1, retries=0)
    assert out["failure"]["kind"] == "timeout" and out["failure"]["reason"].startswith("timeout: stopped after 1s")
    assert out["counts"] == {"attempts": 1, "timeouts": 1, "refusals": 0, "adapter_failures": 0, "early_ends": 0,
                             "pauses": 0, "redactions": 0}


def test_a_run_that_meets_the_account_limit_pauses_and_starts_again_without_counting_as_a_failure(tree, tmp_path, capsys):
    st.fail(tree["adapter"], "limit", 1)
    out = run(tree, tmp_path, retries=0)  # one failure of any kind would end the run: the limit is none
    assert out["status"] == "ok" and out["counts"]["pauses"] == 1 and out["counts"]["attempts"] == 1
    assert (tree["adapter"] / "probes.txt").is_file() and "PAUSED" in capsys.readouterr().err
    assert (tmp_path / "data" / "run-1" / "paused-1" / "outputs" / "error.log").is_file()
    assert not list((tmp_path / "locks").glob("pause-*.json"))  # the pause is over


def test_a_copy_that_carries_a_tools_settings_is_refused_before_any_model_call(tree, tmp_path):
    planted = tmp_path / "h-settings.json"
    planted.write_text("{}")
    out = run(tree, tmp_path, files=[(str(planted), "config/h-settings.json")])
    assert out["failure"]["kind"] == "settings" and "config/h-settings.json" in out["failure"]["reason"]
    assert st.calls(tree["adapter"]) == []


def test_the_value_of_a_passed_variable_is_replaced_in_everything_a_run_leaves(tree, tmp_path, monkeypatch):
    monkeypatch.setenv("STANDIN_KEY", "invented-value-0123456789")
    out = run(tree, tmp_path, pass_env=["STANDIN_KEY"])
    left = (Path(out["cwd"]) / "leak.txt").read_text() + (Path(out["outputs"]) / "stderr.log").read_text()
    assert "invented-value-0123456789" not in left and "[redacted:STANDIN_KEY]" in left
    assert out["counts"]["redactions"] == 2


def test_what_cannot_run_at_all_is_an_error_that_names_no_value(tree, tmp_path, monkeypatch):
    monkeypatch.delenv("STANDIN_KEY", raising=False)
    for kwargs, word in (({"skill": "no-such-skill"}, "no skill"), ({"pass_env": ["STANDIN_KEY"]}, "STANDIN_KEY is not set"),
                         ({"adapter": "missing"}, "configuration")):
        with pytest.raises(lab.LabError) as e:
            run(tree, tmp_path, **kwargs)
        assert e.value.kind == "config" and word in e.value.reason
    link = tmp_path / "link.md"
    os.symlink(tree["project"] / "AGENTS.md", link)
    for files in ([(str(link), "docs/a.md")], [(str(tree["project"] / "AGENTS.md"), "../a.md")]):
        with pytest.raises(lab.LabError) as e:
            run(tree, tmp_path, files=files)
        assert e.value.kind == "copy"
    assert st.calls(tree["adapter"]) == []


def test_the_runtime_never_builds_the_eval_image_a_missing_one_is_an_error(tree, tmp_path, monkeypatch):
    """Lab evidence is bound to one built image; the executor's ensure() builds a missing one, so the facade
    looks for the image first and never reaches ensure() without it."""
    called = []

    class Executor:
        @staticmethod
        def names():
            return {"image": "wb-eval:invented"}

        @staticmethod
        def docker(*args, check=True, **kwargs):
            called.append(args[:2])
            return type("Result", (), {"returncode": 1, "stdout": "", "stderr": "No such image"})()

        @staticmethod
        def ensure():
            called.append(("ensure",))
            return {}

    er = lab.load()
    monkeypatch.setattr(er, "EXECUTOR", "container")
    monkeypatch.setattr(er, "load_executor", lambda: Executor)
    with pytest.raises(lab.LabError) as e:
        run(tree, tmp_path)
    assert e.value.kind == "container" and "never builds it" in e.value.reason
    assert called == [("image", "inspect")] and st.calls(tree["adapter"]) == []


def test_only_the_allowed_names_of_the_runner_can_be_read_and_every_listed_name_exists():
    er = lab.load()
    for name in lab.ALLOWED:
        assert hasattr(er, name) or name in er.MEASURE_NAMES, name
        getattr(lab.LAB, name)
    for name in lab.FORBIDDEN:
        assert hasattr(er, name) or name in er.MEASURE_NAMES, f"{name} is not a name of the runner any more"
        with pytest.raises(AttributeError):
            getattr(lab.LAB, name)
    assert not set(lab.ALLOWED) & set(lab.FORBIDDEN)


def test_no_other_module_of_the_runtime_reads_the_lab():
    """The rule of the facade: lab.py is the one file of runtime/ that names anything under evals/, and inside
    lab.py every read of the runner goes through LAB."""
    for path in sorted((st.REPO / "runtime").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        code = "\n".join(line for line in text.split('"""')[2::2]) if path.name != "lab.py" else ""
        assert not re.search(r"eval_run|eval_status|executor\.py|measure\.py", code), path.name
    tree = ast.parse((st.REPO / "runtime" / "lab.py").read_text(encoding="utf-8"))
    read = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name) and node.value.id == "LAB"}
    assert read <= set(lab.ALLOWED), read - set(lab.ALLOWED)


def test_the_names_of_a_tools_settings_come_from_the_adapters_lists(tree):
    assert lab.settings_names() == sorted(st.EVAL_JSON["settings"])
