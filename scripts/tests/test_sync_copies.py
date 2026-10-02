"""Offline tests of scripts/sync_copies.py and of the validator's check on generated copies. Each test builds
a small tree with a manifest in a temporary folder.

Run: uv run --with pytest pytest scripts/tests/test_sync_copies.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "sync_copies.py"


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync = load("sync_copies_under_test", "scripts/sync_copies.py")
validate = load("validate_for_copies_test", "scripts/validate.py")

SOURCE = "#!/usr/bin/env python3\nprint('rank')\n"
CONTRACT = "# Contract\n\nText before.\n\n<!-- table:begin -->\n| Class | Meaning |\n|---|---|\n| `a:b` | one |\n" \
           "<!-- table:end -->\n\nText after.\n"


def write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def manifest(root, copies):
    write(root, "shared/scripts/copies.json", json.dumps({"copies": copies}))


@pytest.fixture()
def tree(tmp_path):
    write(tmp_path, "shared/scripts/rank.py", SOURCE)
    write(tmp_path, "contracts/environment.md", CONTRACT)
    write(tmp_path, "skills/biz-one/scripts/rank.py", SOURCE)
    write(tmp_path, "skills/biz-two/scripts/rank.py", SOURCE.replace("rank", "an older rank"))
    manifest(tmp_path, [
        {"source": "shared/scripts/rank.py", "to": [{"path": "skills/biz-one/scripts/rank.py", "adopted": True},
                                                    {"path": "skills/biz-two/scripts/rank.py", "adopted": False},
                                                    {"path": "skills/biz-three/scripts/rank.py", "adopted": False}]},
        {"source": "contracts/environment.md", "between": ["<!-- table:begin -->", "<!-- table:end -->"],
         "header": "# Classes\n", "to": [{"path": "skills/core-router/references/classes.md", "adopted": False}]}])
    return tmp_path


def cli(root, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args], capture_output=True, text=True,
                          timeout=60)


def state(root):
    return {r["path"]: (r["adopted"], r["state"]) for r in sync.states(str(root))}


def test_states_say_what_each_copy_is(tree):
    assert state(tree) == {
        "skills/biz-one/scripts/rank.py": (True, "identical"), "skills/biz-two/scripts/rank.py": (False, "differs"),
        "skills/biz-three/scripts/rank.py": (False, "missing"),
        "skills/core-router/references/classes.md": (False, "missing")}


def test_check_compares_adopted_copies_only_so_that_main_stays_green(tree):
    r = cli(tree, "--check")
    assert r.returncode == 0 and json.loads(r.stdout) == {"checked": 1, "different": 0, "ok": True}
    write(tree, "skills/biz-one/scripts/rank.py", SOURCE + "# a hand edit\n")
    r = cli(tree, "--check")
    assert r.returncode == 1 and json.loads(r.stdout)["different"] == 1
    assert "skills/biz-one/scripts/rank.py: differs" in r.stderr and "shared/scripts/rank.py" in r.stderr
    (tree / "skills/biz-one/scripts/rank.py").unlink()
    assert "skills/biz-one/scripts/rank.py: missing" in cli(tree, "--check").stderr


def test_a_plain_run_writes_adopted_copies_and_leaves_the_others_alone(tree):
    older = (tree / "skills/biz-two/scripts/rank.py").read_text()
    write(tree, "shared/scripts/rank.py", SOURCE + "print('new behaviour')\n")
    r = cli(tree)
    assert r.returncode == 0 and json.loads(r.stdout) == {"written": ["skills/biz-one/scripts/rank.py"]}
    assert (tree / "skills/biz-one/scripts/rank.py").read_text().endswith("print('new behaviour')\n")
    assert (tree / "skills/biz-two/scripts/rank.py").read_text() == older
    assert not (tree / "skills/biz-three").exists()
    assert json.loads(cli(tree).stdout) == {"written": []}  # nothing to do the second time


def test_adopt_writes_the_copy_and_sets_its_flag(tree):
    r = cli(tree, "--adopt", "skills/biz-two/scripts/rank.py", "skills/biz-three/scripts/rank.py")
    assert r.returncode == 0, r.stderr
    assert sorted(json.loads(r.stdout)["written"]) == ["skills/biz-three/scripts/rank.py", "skills/biz-two/scripts/rank.py"]
    assert (tree / "skills/biz-three/scripts/rank.py").read_bytes() == (tree / "shared/scripts/rank.py").read_bytes()
    assert state(tree)["skills/biz-two/scripts/rank.py"] == (True, "identical")
    assert state(tree)["skills/core-router/references/classes.md"] == (False, "missing")  # not named, not touched
    saved = json.loads((tree / "shared/scripts/copies.json").read_text())
    assert saved["copies"][1]["between"] == ["<!-- table:begin -->", "<!-- table:end -->"]  # the rest is kept
    assert saved["copies"][1]["header"] == "# Classes\n"
    r = cli(tree, "--adopt", "skills/biz-four/scripts/rank.py")
    assert r.returncode == 2 and "not a copy listed" in r.stderr and "Traceback" not in r.stderr


def test_a_block_of_a_contract_is_copied_with_its_header(tree):
    assert cli(tree, "--adopt", "skills/core-router/references/classes.md").returncode == 0
    assert (tree / "skills/core-router/references/classes.md").read_text() == \
        "# Classes\n\n| Class | Meaning |\n|---|---|\n| `a:b` | one |\n"
    write(tree, "contracts/environment.md", CONTRACT.replace("| `a:b` | one |", "| `a:b` | one |\n| `c:d` | two |"))
    assert cli(tree, "--check").returncode == 1
    assert cli(tree).returncode == 0 and "| `c:d` | two |" in (tree / "skills/core-router/references/classes.md").read_text()
    write(tree, "contracts/environment.md", "# Contract\n\nno markers\n")
    r = cli(tree, "--check")
    assert r.returncode == 2 and "has no lines" in r.stderr


def test_list_and_destinations(tree):
    listed = json.loads(cli(tree, "--list").stdout)
    assert listed["manifest"] == "shared/scripts/copies.json" and len(listed["copies"]) == 4
    assert cli(tree, "--destinations").stdout.splitlines() == [
        "skills/biz-one/scripts/rank.py", "skills/biz-two/scripts/rank.py", "skills/biz-three/scripts/rank.py",
        "skills/core-router/references/classes.md"]


@pytest.mark.parametrize("copies, message", [
    ("not a list", "list \"copies\""),
    ([{"source": "shared/scripts/rank.py"}], "to is a non-empty list"),
    ([{"source": "../outside.py", "to": [{"path": "a.py", "adopted": True}]}], "without '..'"),
    ([{"source": "shared/scripts/rank.py", "to": [{"path": "/abs/a.py", "adopted": True}]}], "relative"),
    ([{"source": "shared/scripts/rank.py", "to": [{"path": "a.py"}]}], "a copy is"),
    ([{"source": "shared/scripts/rank.py", "to": [{"path": "a.py", "adopted": "yes"}]}], "a copy is"),
    ([{"source": "shared/scripts/rank.py", "to": [{"path": "a.py", "adopted": True}, {"path": "a.py", "adopted": True}]}],
     "listed twice"),
    ([{"source": "shared/scripts/rank.py", "to": [{"path": "shared/scripts/rank.py", "adopted": True}]}], "is a source"),
    ([{"source": "shared/scripts/rank.py", "between": ["one"], "to": [{"path": "a.py", "adopted": True}]}], "two marker"),
    ([{"source": "shared/scripts/rank.py", "header": "# T", "to": [{"path": "a.py", "adopted": True}]}], "goes with between"),
    ([{"source": "shared/scripts/rank.py", "mode": "x", "to": [{"path": "a.py", "adopted": True}]}], "an entry has"),
    ([{"source": "shared/scripts/absent.py", "to": [{"path": "a.py", "adopted": True}]}], "cannot be read"),
])
def test_a_manifest_that_cannot_be_used_is_refused_without_a_traceback(tree, copies, message):
    manifest(tree, copies)
    for args in (("--check",), (), ("--list",)):
        r = cli(tree, *args)
        assert r.returncode == 2 and message in r.stderr and "Traceback" not in r.stderr, (args, r.stderr)


def test_the_command_line(tmp_path):
    r = cli(tmp_path, "--help")
    assert r.returncode == 0 and "Usage:" in r.stdout and "--adopt" in r.stdout
    for args in (("--nope",), ("--check", "--list"), ("--adopt",), ("extra",), ("--check", "extra")):
        r = cli(tmp_path, *args)
        assert r.returncode == 2 and r.stderr.strip() and "Traceback" not in r.stderr, args
    assert subprocess.run([sys.executable, str(SCRIPT), "--root"], capture_output=True, text=True).returncode == 2
    missing = cli(tmp_path, "--check")  # no manifest in this tree
    assert missing.returncode == 2 and "cannot be read" in missing.stderr


# --- the validator -----------------------------------------------------------------

def validated(root):
    report = validate.Report()
    validate.check_copies(report, root=str(root))
    return report


def with_script(tree):
    shutil.copy(SCRIPT, tree / "scripts" / "sync_copies.py") if (tree / "scripts").is_dir() else \
        write(tree, "scripts/sync_copies.py", SCRIPT.read_text(encoding="utf-8"))
    return tree


def test_the_validator_fails_on_an_adopted_copy_that_differs_and_warns_on_one_not_adopted(tree):
    report = validated(with_script(tree))
    assert report.errors == []
    assert [(w["where"], w["rule"]) for w in report.warnings] == [
        ("skills/biz-three", "copy-not-adopted"), ("skills/biz-two", "copy-not-adopted"),
        ("skills/core-router", "copy-not-adopted")]
    assert "scripts/rank.py (differs; source shared/scripts/rank.py)" in report.warnings[1]["message"]
    write(tree, "skills/biz-one/scripts/rank.py", SOURCE + "# a hand edit\n")
    report = validated(tree)
    assert [(e["where"], e["message"].split(":")[0]) for e in report.errors] == [
        ("skills/biz-one/scripts/rank.py", "[copies] differs")]


def test_the_validator_reports_a_bad_manifest_and_skips_a_tree_without_the_mechanism(tree, tmp_path_factory):
    with_script(tree)
    manifest(tree, "not a list")
    report = validated(tree)
    assert [e["where"] for e in report.errors] == ["shared/scripts/copies.json"]
    (tree / "shared/scripts/copies.json").unlink()
    report = validated(tree)
    assert report.errors == [] and report.notes == ["[copies] skipped: shared/scripts/copies.json is not in this tree"]
    bare = tmp_path_factory.mktemp("bare")  # a folder an eval case builds: the validator without the mechanism
    report = validated(bare)
    assert report.errors == [] and report.notes == ["[copies] skipped: scripts/sync_copies.py is not in this tree"]


def test_this_repository_has_no_adopted_copy_that_differs():
    assert sync.check(str(REPO)) == []
    report = validated(REPO)
    assert report.errors == []
    assert "copy-not-adopted" in validate.WARNING_RULES
