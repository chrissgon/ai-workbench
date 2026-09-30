"""Offline tests of the private-term check in scripts/validate.py: a local, git-ignored terms file keeps a
maintainer's own names out of tracked files."""
import importlib.util
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("validate", REPO / "scripts" / "validate.py")
validate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "LICENSE").write_text("Copyright Jo Example\n")
    (tmp_path / "guide.md").write_text("A skill by Jo Example.\nThe owner repo is jo/workbench.\n")
    (tmp_path / "ok.md").write_text("Nothing personal here.\n")
    terms = tmp_path / "terms.txt"
    terms.write_text("# comment\n!LICENSE\nJo Example\nre:\\bjo/(?!workbench)\n")
    monkeypatch.setenv("WORKBENCH_PRIVATE_TERMS", str(terms))
    return tmp_path


def errors(root):
    report = validate.Report()
    validate.check_private_terms(report, root=str(root))
    return [e["where"] for e in report.errors]


def test_a_listed_term_in_a_tracked_file_is_an_error(repo):
    assert errors(repo) == ["guide.md:1"]


def test_an_excluded_path_and_a_negative_lookahead_are_respected(repo):
    (repo / "guide.md").write_text("The owner repo is jo/workbench, see jo/site.\n")
    assert errors(repo) == ["guide.md:1"]
    (repo / "guide.md").write_text("The owner repo is jo/workbench.\n")
    assert errors(repo) == []


def test_an_allow_with_a_reason_exempts_the_line(repo):
    (repo / "guide.md").write_text("Credit: Jo Example <!-- validate: allow private-term -- author credit -->\n")
    assert errors(repo) == []
    (repo / "guide.md").write_text("Credit: Jo Example <!-- validate: allow private-term -->\n")
    assert errors(repo) == ["guide.md:1"]


def test_without_a_terms_file_nothing_is_checked(repo, monkeypatch):
    monkeypatch.setenv("WORKBENCH_PRIVATE_TERMS", str(repo / "missing.txt"))
    assert errors(repo) == []
