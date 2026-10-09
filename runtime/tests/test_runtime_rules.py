"""Tests of the rules the task runtime keeps outside the validator's core: no module of runtime/ or runtime/handlers/
and no flow file names an AI tool or a model id (rule R19 of the platform plan), the terminal shell imports only
the operations layer, every module runs on the system interpreter, and the Python 3.9 job of CI runs the tests of
the runtime and of the store. Offline.

Run: uv run --with pytest==9.1.1 pytest runtime/tests/test_runtime_rules.py
"""
from __future__ import annotations

import ast
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


# --- the operations layer is four files (CONS-1B): runtime/ops.py, ops_say.py, ops_reads.py and ops_core.py ----------

SHARED_NAMES = ("ROOT", "context", "_stored", "OpsError", "_run_lock", "_config_lock")


def ops_modules() -> list:
    """The files of the operations layer: ops.py and its siblings ops_*.py (not operations.py, the table)."""
    return sorted(RUNTIME.glob("ops.py")) + sorted(RUNTIME.glob("ops_*.py"))


def top_level_names(tree) -> list:
    """(name, node) of each definition and assignment at the top of a module."""
    found = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            found.append((node.name, node))
        elif isinstance(node, ast.Assign):
            found += [(t.id, node) for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            found.append((node.target.id, node))
    return found


def test_no_module_of_the_operations_layer_binds_a_name_of_ops_core_at_import():
    """A from-import of `ROOT` out of ops_core would copy the name when the module loads: a test that patches
    `ops_core.ROOT` would not reach it, and the code would run against the real checkout with nothing failing. Every
    module reads a shared name as an attribute of the module, at call time (`core.ROOT`)."""
    assert ops_modules(), "runtime/ holds no ops.py"
    found = []
    for path in ops_modules():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module == "ops_core":
                found.append(f"{path.name}:{node.lineno}")
    assert found == []


def test_the_shared_names_of_the_operations_layer_have_one_home():
    homes = {name: [] for name in SHARED_NAMES}
    for path in ops_modules():
        for name, node in top_level_names(ast.parse(path.read_text(encoding="utf-8"))):
            if name not in SHARED_NAMES:
                continue
            # the one re-export: the shells catch `ops.OpsError`, and the class is never patched
            if name == "OpsError" and isinstance(node, ast.Assign) and ast.unparse(node.value) == "core.OpsError":
                continue
            homes[name].append(path.name)
    assert homes == {name: ["ops_core.py"] for name in SHARED_NAMES}


def test_ops_core_imports_no_other_file_of_the_operations_layer():
    path = RUNTIME / "ops_core.py"
    assert path.is_file(), "runtime/ops_core.py is gone"
    names = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
        elif isinstance(node, ast.Call) and ast.unparse(node.func).endswith("import_module") and node.args:
            names.append(ast.unparse(node.args[0]).strip("\"'"))
    assert [n for n in names if n == "ops" or n.startswith("ops_")] == []

