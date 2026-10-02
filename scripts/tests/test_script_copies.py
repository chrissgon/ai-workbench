"""The generated copies of this repository: one identity test for every copy the manifest lists, instead of
one test per family that named its paths.

The manifest is shared/scripts/copies.json; scripts/sync_copies.py writes and checks the copies (its own tests
are in test_sync_copies.py). The pre-commit hook runs this file whenever a shared source, the manifest or a
copy changes. The tests of a shared script live at its source, in shared/scripts/tests/.

Run: uv run --with pytest pytest scripts/tests/test_script_copies.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sync = load("scripts/sync_copies.py", "sync_copies_for_identity")
COPIES = sync.states(str(ROOT))
AWS = "AKIA" + "Q7ZT2MLP4RX9KW1V"


def test_the_manifest_lists_copies():
    assert COPIES and all(r["source"] and r["path"] for r in COPIES)
    assert any(r["adopted"] for r in COPIES)


@pytest.mark.parametrize("copy", [r for r in COPIES if r["adopted"]], ids=lambda r: r["path"])
def test_an_adopted_copy_is_identical_to_its_source(copy):
    assert copy["state"] == "identical", (
        f"{copy['path']} {copy['state']}: it is a generated copy of {copy['source']}. Change the source, then run "
        "python3 scripts/sync_copies.py")


@pytest.mark.parametrize("copy", [r for r in COPIES if not r["adopted"]], ids=lambda r: r["path"])
def test_a_copy_that_is_already_identical_is_marked_adopted(copy):
    """A flag left false on a copy that equals its source would let a later hand edit of it pass."""
    assert copy["state"] != "identical", (
        f"{copy['path']} equals {copy['source']}: run python3 scripts/sync_copies.py --adopt {copy['path']}")


def test_every_source_is_in_the_core_and_every_script_source_has_its_tests():
    for source in sorted({r["source"] for r in COPIES}):
        assert (ROOT / source).is_file(), source
        if source.startswith("shared/scripts/") and source.endswith(".py") and not source.endswith("conftest.py"):
            test = ROOT / "shared/scripts/tests" / f"test_shared_{Path(source).stem}.py"
            assert test.is_file(), f"{source} has no tests at the source ({test.relative_to(ROOT)})"


def test_no_script_under_shared_scripts_is_left_out_of_the_manifest():
    listed = {r["source"] for r in COPIES}
    for path in sorted((ROOT / "shared/scripts").glob("*.py")):
        assert f"shared/scripts/{path.name}" in listed, f"{path.name} is a source with no copy in the manifest"


def test_the_scan_imports_a_generated_copy_of_the_shared_redaction():
    assert (ROOT / "scripts/redact.py").read_bytes() == (ROOT / "shared/scripts/redact.py").read_bytes()
    scan = load("scripts/security_scan.py", "security_scan_shared")
    shared = load("shared/scripts/redact.py", "redact_shared")
    assert scan.redact("k " + AWS) == shared.redact("k " + AWS) == "k <redacted AWS access key>"
    assert scan.VALUE_RES is not None and [label for label, _ in scan.VALUE_RES] == [label for label, _ in shared.VALUE_RES]
