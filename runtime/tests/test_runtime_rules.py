"""Tests of the rules the task runtime keeps outside the validator's core: no module of runtime/ or runtime/handlers/
and no flow file names an AI tool or a model id (rule R19 of the platform plan), the terminal shell imports only
the operations layer, every module runs on the system interpreter, and the Python 3.9 job of CI runs the tests of
the runtime and of the store. Offline.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_runtime_rules.py
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / "runtime"

spec = importlib.util.spec_from_file_location("validate_for_runtime_rules", REPO / "scripts" / "validate.py")
validate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate)


def runtime_modules() -> list:
    """Every module of runtime/ and of runtime/handlers/ (the handlers the dispatcher ticks)."""
    return sorted(RUNTIME.glob("*.py")) + sorted((RUNTIME / "handlers").glob("*.py"))


def scanned_files() -> list:
    return runtime_modules() + [RUNTIME / "README.md"] + sorted((REPO / "flows").glob("*.json"))


def known_model_ids() -> set:
    """Every model id the gate file names: the reference and floor models, the grader, and each id of its
    `models` table with its aliases. The gate file is the one place that names them (rule R19)."""
    gate = json.loads((REPO / "evals" / "eval-gate.json").read_text(encoding="utf-8"))
    ids = {gate[key] for key in ("strong_model", "floor_model", "grader") if isinstance(gate.get(key), str)}
    for name, aliases in (gate.get("models") or {}).items():
        ids |= {name, *aliases}
    return {i for i in ids if i}


def test_no_module_of_the_runtime_and_no_flow_file_names_an_ai_tool():
    assert any(p.parent.name == "handlers" for p in runtime_modules()), "runtime/handlers/ holds no module"
    found = []
    for path in scanned_files():
        match = validate.HARNESS_RE.search(path.read_text(encoding="utf-8"))
        if match:
            found.append(f"{path.relative_to(REPO)}: {match.group(0)!r}")
    assert found == []


def test_no_module_of_the_runtime_and_no_flow_file_names_a_model_id():
    ids = known_model_ids()
    assert len(ids) >= 2, "the gate file names no model"
    found = [f"{path.relative_to(REPO)}: {i!r}" for path in scanned_files() for i in sorted(ids)
             if i in path.read_text(encoding="utf-8")]
    assert found == [], "the model comes from evals/eval-gate.json, never from a literal in the runtime"


# 2026-10-07: the social handler was ported unchanged (stage 7, WP-7.1) and still confirms its publisher call and
# records its action through its own gate, the engagement policy's. WP-7.6 hands them to execute-under-policy and
# removes this exemption.
PORTED = ("social.py", "social_vote.py", "social_vote_job.py")


def test_no_handler_executes_an_effect_itself():
    """Limit L15 lives in one operation (ops.execute_under_policy): a handler prepares an effect and hands it over,
    it never confirms a provider verb and never records an action."""
    for handler in sorted((RUNTIME / "handlers").glob("*.py")):
        if handler.name in PORTED:
            continue
        text = handler.read_text(encoding="utf-8")
        for word in ("--confirmed", "action-add", "action_add"):
            assert word not in text, f"{handler.name} holds {word!r}: hand the effect to execute-under-policy"


def test_the_terminal_shell_imports_only_the_operations_layer():
    source = (RUNTIME / "cli.py").read_text(encoding="utf-8")
    imported = re.findall(r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", source, re.M)
    assert [name for name in imported if name not in ("__future__", "argparse", "json", "os", "sys")] == ["ops"]
    for loader in ("importlib", "__import__", "spec_from_file_location"):
        assert loader not in source, f"runtime/cli.py loads a module another way: {loader}"


def test_every_module_of_the_runtime_is_on_the_list_the_python_39_job_checks():
    listed = (REPO / "scripts" / "tests" / "test_runtime_python39.py").read_text(encoding="utf-8")
    missing = [p.relative_to(REPO).as_posix() for p in runtime_modules()
               if f'"{p.relative_to(REPO).as_posix()}"' not in listed]
    assert missing == []


def test_the_python_39_job_runs_the_tests_of_the_runtime_and_of_the_store():
    text = (REPO / ".github" / "workflows" / "checks.yml").read_text(encoding="utf-8")
    rest = text[text.index("\n  python39:") + 1:]
    following = re.search(r"\n  [A-Za-z0-9_-]+:\n", rest)
    job = rest[:following.start()] if following else rest
    assert "runtime/tests" in job
    assert "providers/store/tests" in job
