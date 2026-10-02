"""Tests for skills/eng-codebase-map/scripts/map_codebase.py: the stack, the module coupling and the signals.

Run: uv run --with pytest pytest skills/eng-codebase-map/scripts/tests

Offline; the project below is fictional and nothing in it is installed or executed.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "map_codebase.py"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def project(root: Path) -> Path:
    write(root / "package.json", json.dumps({"name": "harbor-notes", "version": "0.3.0", "main": "src/main.ts",
                                              "dependencies": {"vue": "^3.4.0"}, "devDependencies": {"vitest": "^2.0.0"}}))
    write(root / "README.md", "# Harbor notes\n")
    write(root / "src/main.ts", 'import { mount } from "./app/shell"\nmount()\n')
    write(root / "src/app/shell.ts", 'import { Button } from "../ui/button"\nimport debounce from "lodash/debounce"\n'
                                     "const base = process.env.NOTES_API_URL\n"
                                     'export const mount = () => fetch("https://api.harbor.example/notes")\n')
    write(root / "src/ui/button.ts", 'import { theme } from "../core/theme"\nexport const Button = theme\n')
    write(root / "src/ui/card.ts", 'import { theme } from "../core/theme"\nexport const Card = theme\n')
    write(root / "src/core/theme.ts", "export const theme = {}\n")
    write(root / "node_modules/lodash/debounce.js", "module.exports = () => {}\n")
    return root


def test_help_exits_zero_and_no_argument_is_a_usage_error():
    r = run("--help")
    assert r.returncode == 0 and "--root" in r.stdout
    assert run().returncode == 2


def test_the_stack_and_the_entry_points_come_from_the_manifest(tmp_path):
    r = run("--root", str(project(tmp_path)))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["stack"]["manifests"] == ["package.json"]
    assert out["stack"]["frameworks"] == ["Vitest", "Vue"]
    assert out["source_root"] == "src" and out["source_files"] == 5
    assert {"kind": "main", "path": "src/main.ts"} in out["entry_points"]
    assert {"kind": "file", "path": "src/main.ts"} in out["entry_points"]
    assert out["docs_at_root"] == ["README.md"]


def test_coupling_is_counted_per_module_and_dependency_folders_are_left_out(tmp_path):
    out = json.loads(run("--root", str(project(tmp_path))).stdout)
    modules = {m["module"]: m for m in out["modules"]}
    assert modules["core"]["afferent"] == 1 and modules["core"]["imported_by"] == ["ui"] and modules["core"]["efferent"] == 0
    assert modules["ui"]["files"] == 2 and modules["ui"]["imports"] == ["core"] and modules["ui"]["imported_by"] == ["app"]
    assert out["modules"][0]["afferent"] >= out["modules"][-1]["afferent"]
    assert out["top_files_by_afferent"][0] == {"file": "src/core/theme.ts", "imported_by": 2}
    assert out["external_packages"] == [{"package": "lodash", "files": 1}]
    assert "node_modules" not in out["tree"]["top_level"]


def test_integration_signals_name_the_files_they_were_seen_in(tmp_path):
    signals = json.loads(run("--root", str(project(tmp_path))).stdout)["integration_signals"]
    assert signals["env_vars"] == {"NOTES_API_URL": ["src/app/shell.ts"]}
    assert signals["urls"] == {"https://api.harbor.example/notes": ["src/app/shell.ts"]}
    assert signals["clients"] == {"fetch(": ["src/app/shell.ts"]}


def test_focus_limits_the_scan_and_top_limits_the_file_list(tmp_path):
    out = json.loads(run("--root", str(project(tmp_path)), "--focus", "src/ui", "--top", "0").stdout)
    assert out["focus"] == "src/ui" and out["source_files"] == 2
    assert out["top_files_by_afferent"] == []


def test_a_folder_without_source_files_exits_one(tmp_path):
    (tmp_path / "notes.txt").write_text("nothing to map\n", encoding="utf-8")
    r = run("--root", str(tmp_path))
    assert r.returncode == 1
    assert json.loads(r.stdout)["error"] == "no source files found"


def test_usage_errors_exit_two(tmp_path):
    for args in (["--depth", "2"], ["--root", str(tmp_path / "missing")]):
        r = run(*args)
        assert r.returncode == 2, (args, r.stderr)
        assert r.stderr.startswith("Error:") and r.stdout == ""


def test_a_flag_without_its_value_is_a_usage_error(tmp_path):
    for flag in ("--root", "--focus", "--top"):
        r = run("--root", str(tmp_path), flag)
        assert r.returncode == 2, (flag, r.stderr)
        assert f"{flag} needs a value" in r.stderr and "Traceback" not in r.stderr and r.stdout == ""


def test_a_non_integer_top_is_a_usage_error(tmp_path):
    r = run("--root", str(tmp_path), "--top", "abc")
    assert r.returncode == 2 and "whole number" in r.stderr and "Traceback" not in r.stderr and r.stdout == ""


def test_no_arguments_prints_the_usage_on_stderr():
    r = run()
    assert r.returncode == 2 and r.stdout == "" and "Usage:" in r.stderr
