"""Offline tests of scripts/architecture_tables.py, which generates the volatile tables of the architecture pages
(docs/architecture/platform/), and of the validator's warning rule architecture-tables. One test reads this
repository; the others write a small tree with an invented skill, provider and runtime to a temporary folder.
Nothing calls a model, the network or a provider.

Run: uv run --with pytest pytest scripts/tests/test_architecture_tables.py
"""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "architecture_tables.py"


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tables = load("architecture_tables_under_test", "scripts/architecture_tables.py")
validate = load("validate_architecture_under_test", "scripts/validate.py")

SKILL = """---
name: biz-sample
description: Write the sample. Use when a sample is asked for.
license: MIT
metadata:
  area: business
  kind: capability
  inputs: []
  outputs: [docs/business/sample.md]
  updates: [docs/workbench/state.md]
  requires: []
  side_effects: []
  version: "0.1.0"
---
# Sample
"""

CONTRACT = """# Providers

## Verbs per class

| Class | Verb and flags | Prints |
|-------|----------------|--------|
| `integration:widget` | `spin` | `ok` |
| `search:web` | No implementation ships. | nothing |
"""

PROVIDER = '''import argparse
VERBS = {"spin": print, "stop": print}
SWITCHES = ("--dry-run", "--check")
'''

RUNTIME_CONTRACT = """# Runtime

## The limits

| # | Limit | Built by | Test |
|---|---|---|---|
| L1 | A copy is new | stage 2 | anything |
| L2 | A record \\| only grows | stage 4 | anything |
"""

LIMIT_TESTS = """def test_limit_01_a_copy_is_new():
    pass
"""

OPERATIONS_PY = '''"""The table of operations."""
OPERATIONS = (
    {"name": "go", "call": "go",
     "args": ({"name": "task_id", "kind": "int", "required": True, "flag": "id", "label": "id"},
              {"name": "dry_run", "kind": "flag", "flag": "dry-run"}),
     "channels": ("terminal", "chat"), "model": False, "help": "go on with one task"},
    {"name": "status", "call": "status", "args": (), "channels": ("terminal",), "model": "for a new request",
     "help": "where things stand"},
)
CHAT_OWN = (
    {"name": "help", "args": "", "help": "this text", "order": "first"},
    {"name": "new", "args": "text", "help": "start a new request", "order": "last"},
)
'''

DISPATCHER = '''"""The dispatcher.

  /usr/bin/python3 runtime/dispatcher.py tick  --project <dir>   ops.tick: the job
"""
ENTRY_VERBS = ("tick",)
JOBS = {"tick": 7}
'''

SQLITE = '''MIGRATIONS = {
    1: ("the first table", ["CREATE TABLE first (id INTEGER PRIMARY KEY, name TEXT)"]),
    2: ("the task table", [
        """CREATE TABLE jobs (
            id INTEGER PRIMARY KEY,
            state TEXT CHECK (state IN ('a', 'b')),
            UNIQUE (id, state))""",
        "CREATE TRIGGER jobs_kept BEFORE DELETE ON jobs BEGIN SELECT RAISE(ABORT, 'no'); END",
    ]),
    3: ("a column", ["ALTER TABLE jobs ADD COLUMN note TEXT"]),
}
'''

GATE = {"strong_model": "model-one", "strong_harness": "adapter-one", "threshold": 0.8, "runs": 3,
        "measurement_version": 4, "measurement_floor": 2, "strong_pass_env": ["SOME_VARIABLE_NAME"],
        "free_text": "never-shown-text", "web_jobs": {"strong": 2}, "epochs": [{"date": "x", "cause": "y"}]}

PAGE = "".join(f"# {name}\n\nProse kept.\n\n<!-- generated: {name} -->\nstale\n<!-- /generated -->\n\nMore prose.\n\n"
               for name in tables.TABLES)


def fixture(tmp_path):
    root = tmp_path / "wb"
    files = {
        "skills/biz-sample/SKILL.md": SKILL,
        "providers/CONTRACT.md": CONTRACT,
        "providers/widget/fake.py": PROVIDER,
        "providers/widget/auth.py": "VERBS = {'login': print}\n",
        "contracts/runtime.md": RUNTIME_CONTRACT,
        "runtime/tests/test_limits.py": LIMIT_TESTS,
        "runtime/operations.py": OPERATIONS_PY,
        "runtime/dispatcher.py": DISPATCHER,
        "providers/store/sqlite.py": SQLITE,
        "evals/eval-gate.json": json.dumps(GATE),
        "docs/architecture/platform/page.md": PAGE,
    }
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    shutil.copy(REPO / "providers" / "resolve.py", root / "providers" / "resolve.py")
    return root


def block(root, name):
    text = (root / "docs/architecture/platform/page.md").read_text(encoding="utf-8")
    return text.split(f"<!-- generated: {name} -->\n", 1)[1].split("<!-- /generated -->", 1)[0]


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60)


def test_the_blocks_of_this_repository_are_current():
    assert tables.stale_blocks(str(REPO)) == []
    named = set()
    for page in tables.pages(str(REPO)):
        named |= {m.group(2) for m in tables.BLOCK_RE.finditer((REPO / page).read_text(encoding="utf-8"))}
    assert named == set(tables.TABLES), "every table is used by a page, and a page names only known tables"


def test_check_names_each_stale_block_and_write_makes_them_current(tmp_path):
    root = fixture(tmp_path)
    checked = run("--check", "--root", str(root))
    assert checked.returncode == 1 and checked.stdout == ""
    assert checked.stderr.count("differs from its source") == len(tables.TABLES)
    assert run("--write", "--root", str(root)).returncode == 0
    assert run("--check", "--root", str(root)).returncode == 0
    text = (root / "docs/architecture/platform/page.md").read_text(encoding="utf-8")
    assert "stale" not in text and text.count("Prose kept.") == len(tables.TABLES)


def test_the_tables_have_their_shape(tmp_path):
    root = fixture(tmp_path)
    run("--write", "--root", str(root))
    assert "| `docs/business/sample.md` | biz-sample | - |" in block(root, "artifacts-by-owner")
    assert "| `docs/workbench/state.md` | - | biz-sample |" in block(root, "artifacts-by-owner")
    classes = block(root, "provider-classes")
    assert "| `integration:widget` | `widget/` | `fake.py` | `--check`, `spin`, `stop` |" in classes
    assert "auth.py" not in classes and "| `search:web` | `search/` | none ships | - |" in classes
    limits = block(root, "limits")
    assert "| L1 | A copy is new | stage 2 | `runtime/tests/test_limits.py`, `test_limit_01_a_copy_is_new` |" in limits
    assert "| L2 | A record \\| only grows | stage 4 | no test named |" in limits
    ops = block(root, "operations")
    assert "| `go` | `go` | terminal, chat | no | go on with one task |" in ops
    assert "| `status` | `status` | terminal | yes, for a new request | where things stand |" in ops
    assert "| `go` | `--id` `[--dry-run]` | `go` |" in block(root, "cli-verbs")
    assert "| `status` | - | `status` |" in block(root, "cli-verbs")
    commands = block(root, "say-commands")
    assert "| `/go <id>` | go on with one task |" in commands and "`/status`" not in commands
    assert commands.index("`/help`") < commands.index("`/go <id>`") < commands.index("`/new <text>`")
    assert "| `tick` | `--project <dir>` | ops.tick: the job | 7 minutes |" in block(root, "dispatcher-jobs")
    migrations = block(root, "store-migrations")
    assert migrations.startswith("Schema version 3:")
    assert "| 2 | the task table | `jobs` | - | `jobs_kept` |" in migrations
    assert "| 3 | a column | - | `jobs.note` | - |" in migrations
    runtime_tables = block(root, "task-runtime-tables")
    assert "| `jobs` | 2 | id, state, note (migration 3) |" in runtime_tables and "`first`" not in runtime_tables


def test_the_gate_keys_show_names_and_never_a_text_that_could_be_a_credential(tmp_path):
    root = fixture(tmp_path)
    gate = tables.gate_keys(str(root))
    assert gate.startswith("Measurement version 4, measurement floor 2.")
    assert "| `strong_model` | `model-one` |" in gate and "| `threshold` | 0.8 |" in gate
    assert "| `strong_pass_env` | 1 name, not shown |" in gate and "SOME_VARIABLE_NAME" not in gate
    assert "| `free_text` | text, not shown |" in gate and "never-shown-text" not in gate
    assert "| `epochs` | 1 entry, each with `date`, `cause` |" in gate


def test_an_unknown_table_or_a_missing_source_is_named_and_the_block_kept(tmp_path):
    root = fixture(tmp_path)
    page = root / "docs/architecture/platform/other.md"
    page.write_text("<!-- generated: no-such-table -->\nkept\n<!-- /generated -->\n", encoding="utf-8")
    (root / "runtime" / "dispatcher.py").unlink()
    written = run("--write", "--root", str(root))
    assert written.returncode == 2
    assert "no-such-table: unknown table" in written.stderr and "dispatcher-jobs: source not readable" in written.stderr
    assert "kept" in page.read_text(encoding="utf-8") and block(root, "dispatcher-jobs") == "stale\n"
    assert block(root, "limits") != "stale\n"


def test_usage_errors_exit_2_on_stderr(tmp_path):
    for args in ([], ["--write", "--check"], ["--print"], ["--print", "nothing"], ["--no-such-flag"]):
        done = run(*args)
        assert done.returncode == 2 and done.stdout == "" and "error" in done.stderr, args
    assert run("--help").returncode == 0
    assert run("--check", "--root", str(tmp_path)).returncode == 2  # no pages in that tree


def test_the_validator_warns_on_a_stale_block_and_notes_a_tree_without_the_pages(tmp_path):
    root = fixture(tmp_path)
    (root / "scripts").mkdir()
    shutil.copy(SCRIPT, root / "scripts" / "architecture_tables.py")
    shutil.copy(REPO / "scripts" / "owner_table.py", root / "scripts" / "owner_table.py")
    shutil.copy(REPO / "scripts" / "validate.py", root / "scripts" / "validate.py")
    report = validate.Report()
    validate.check_architecture_tables(report, root=str(root))
    assert report.errors == [] and len(report.warnings) == len(tables.TABLES)
    assert all(w["rule"] == "architecture-tables" and "--write" in w["message"] for w in report.warnings)
    run("--write", "--root", str(root))
    report = validate.Report()
    validate.check_architecture_tables(report, root=str(root))
    assert report.warnings == [] and report.errors == []
    report = validate.Report()
    validate.check_architecture_tables(report, root=str(tmp_path / "empty"))
    assert report.warnings == [] and report.notes and "[architecture-tables] skipped" in report.notes[0]
