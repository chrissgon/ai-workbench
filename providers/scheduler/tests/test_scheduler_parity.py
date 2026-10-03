"""The functions launchd.py and systemd.py share are the same text in both files.

The two scheduler providers are separate files because a job runs a copy of one of them, alone, with the
system interpreter: they cannot import a common module. So what they share is written twice, and a fix to
the snapshot, the lock or the hash check in one file must reach the other. This test is what makes that
happen: a function of SHARED that differs fails here, and so does a function both files define that is on
neither list.

Run: uv run --with pytest pytest providers/scheduler/tests/test_scheduler_parity.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
LAUNCHD, SYSTEMD = HERE.parent / "launchd.py", HERE.parent / "systemd.py"

# Identical in both files: change one, change the other in the same commit.
SHARED = (
    "ProviderError", "acquire_lock", "archive_finished", "argument_file", "changed_since_approval",
    "copy_verified", "execute", "iso", "job_dir", "kill_group", "last_firing", "load_command_file", "log",
    "main", "now", "parse_iso", "private_dir", "read_job", "record_firing", "release_lock", "run_one_shot",
    "runner_alive", "runs_path", "sha256", "snapshot_argv", "split_argument", "tail", "test_mode",
    "unverified_file", "validate_id", "write_job", "write_private",
)
# The same name and another body, because the two services differ (unit files or a plist, the service's own
# time limit, where the jobs live). A function moves here only with that reason.
DIFFERENT = (
    "Stopped", "approval_digest", "build_parser", "cmd_cancel", "cmd_check", "cmd_list", "cmd_resolve",
    "cmd_run", "cmd_schedule", "finish", "home", "notify", "plan_job", "resolve_program", "run_command",
    "run_recurring", "unload",
)


def definitions(path: Path) -> dict:
    """The source text of every top-level function and class of a file, by name."""
    source = path.read_text(encoding="utf-8")
    return {node.name: ast.get_source_segment(source, node) for node in ast.parse(source).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


LAUNCHD_DEFS, SYSTEMD_DEFS = definitions(LAUNCHD), definitions(SYSTEMD)


@pytest.mark.parametrize("name", SHARED)
def test_a_shared_function_is_the_same_text_in_both_providers(name):
    assert name in LAUNCHD_DEFS and name in SYSTEMD_DEFS, f"{name} is gone from one provider; update SHARED"
    assert LAUNCHD_DEFS[name] == SYSTEMD_DEFS[name], (
        f"{name} differs between launchd.py and systemd.py: make the same change in both files")


def test_every_function_both_providers_define_is_classified():
    common = set(LAUNCHD_DEFS) & set(SYSTEMD_DEFS)
    assert not set(SHARED) & set(DIFFERENT)
    assert common == set(SHARED) | set(DIFFERENT), (
        "a function both providers define must be listed in SHARED (identical) or DIFFERENT (with a reason): "
        f"{sorted(common ^ (set(SHARED) | set(DIFFERENT)))}")


def test_the_lists_say_what_is_true_today():
    """DIFFERENT is not a place to park a function that could be shared: one that became identical moves."""
    assert [name for name in DIFFERENT if LAUNCHD_DEFS[name] == SYSTEMD_DEFS[name]] == []


# --- SC8: what the scheduler reads of a command's output is what the contract says a publisher prints ---


def prints_column(cls: str) -> str:
    """The "Prints" cell of a class's row in the verbs table of providers/CONTRACT.md."""
    contract = (HERE.parents[1] / "CONTRACT.md").read_text(encoding="utf-8")
    table = contract.split("\n## Verbs per class\n", 1)[1].split("\n## ", 1)[0]
    (row,) = [line for line in table.splitlines() if line.startswith(f"| `{cls}` |")]
    return row.rstrip().rstrip("|").rsplit(" | ", 1)[1]


@pytest.mark.parametrize("script", [LAUNCHD, SYSTEMD], ids=lambda path: path.name)
def test_the_scheduler_reads_the_address_under_the_contracts_name(script):
    source = script.read_text(encoding="utf-8")
    (key,) = re.findall(r'^ADDRESS_KEY = "(\w+)"', source, flags=re.MULTILINE)
    assert f"`{key}`" in prints_column("publisher:<platform>"), (
        "the scheduler reads a key the contract's Prints column does not name for the publisher")
    assert f"`{key}`" in prints_column("scheduler:job")
    # The key is written once: no other line of the provider's code spells it.
    code = source.split('"""', 2)[2]
    assert [line for line in code.splitlines() if f'"{key}"' in line] == [f'ADDRESS_KEY = "{key}"']
