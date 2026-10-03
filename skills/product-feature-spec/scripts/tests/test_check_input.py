"""Tests for skills/product-feature-spec/scripts/check_input.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/product-feature-spec/scripts/tests
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(rel: str, *args: str, cwd: Path | None = None, stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / rel), *args], capture_output=True, text=True,
                          cwd=cwd, input=stdin, timeout=60)


# ---------- product-feature-spec/check_input.py: is there enough input to write a specification ----------

CHECK_INPUT = "skills/product-feature-spec/scripts/check_input.py"


def check_input(root: Path, *args: str, stdin: str = "") -> dict:
    r = run(CHECK_INPUT, *args, "--root", str(root), stdin=stdin)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def words(count: int) -> str:
    return " ".join(["search"] * count)


def test_check_input_reports_none_for_a_short_request_in_an_empty_project(tmp_path):
    out = check_input(tmp_path, stdin="Add search to the docs site")
    assert (out["input"], out["sources"], out["missing_sources"], out["candidates"]) == ("none", [], [], [])
    assert out["request_words"] == 6 and out["next"].startswith("STOP. There is no input.")
    assert out["reply_template"] == load(CHECK_INPUT, "check_input").REPLY
    assert out["reply_template"].startswith("Nothing was written: there is no brief, PRD or ticket")
    assert out["reply_template"].rstrip().splitlines()[-1].endswith("because <reason>."), "a question is the last line"
    assert list(tmp_path.iterdir()) == [], "the check writes nothing"


def test_check_input_finds_a_named_source_and_lists_a_missing_or_empty_one(tmp_path):
    (tmp_path / "ticket.md").write_text("Search must match page titles.\n", encoding="utf-8")
    (tmp_path / "empty.md").write_text("", encoding="utf-8")
    out = check_input(tmp_path, "--source", "ticket.md", "--source", "gone.md", "--source", "empty.md",
                      stdin="Add search")
    assert (out["input"], out["sources"], out["missing_sources"]) == ("found", ["ticket.md"], ["gone.md", "empty.md"])
    assert "reply_template" not in out and out["next"] == "Input found. Go to step 1 and read: ticket.md."
    out = check_input(tmp_path, "--source", "gone.md", stdin="Add search")
    assert (out["input"], out["sources"], out["missing_sources"]) == ("none", [], ["gone.md"])
    assert "reply_template" in out
    out = check_input(tmp_path / "elsewhere", "--source", str(tmp_path / "ticket.md"))
    assert (out["input"], out["sources"]) == ("found", [str(tmp_path / "ticket.md")])


def test_check_input_takes_a_request_of_forty_words_as_input(tmp_path):
    out = check_input(tmp_path, stdin=words(40))
    assert (out["input"], out["request_words"]) == ("found", 40)
    assert out["next"] == "Input found. Go to step 1 and read: the user's request." and "reply_template" not in out
    out = check_input(tmp_path, stdin=words(39))
    assert (out["input"], out["request_words"]) == ("none", 39)


def test_check_input_lists_an_unnamed_brief_or_prd_as_a_candidate(tmp_path):
    (tmp_path / "docs" / "workbench" / "briefs").mkdir(parents=True)
    (tmp_path / "docs" / "product").mkdir()
    (tmp_path / "docs" / "workbench" / "briefs" / "search.md").write_text("# Brief: search\n", encoding="utf-8")
    brief = str(Path("docs", "workbench", "briefs", "search.md"))
    out = check_input(tmp_path, stdin="Add search")
    assert (out["input"], out["sources"], out["candidates"]) == ("found", [], [brief])
    assert out["next"].startswith(f"The user named no document, but the project has: {brief}. Read them now.")
    assert out["reply_template"] == load(CHECK_INPUT, "check_input").REPLY, "for the case where no candidate fits"
    (tmp_path / "docs" / "product" / "prd.md").write_text("# PRD: Plinth\n", encoding="utf-8")
    out = check_input(tmp_path, "--source", brief, stdin="Add search")
    assert (out["sources"], out["candidates"]) == ([brief], [str(Path("docs", "product", "prd.md"))])
    assert out["next"] == (f"Input found. Go to step 1 and read: {brief}. Also read these and cite them if they are "
                           "about this feature: " + str(Path("docs", "product", "prd.md")) + ".")


def test_check_input_reads_the_request_from_stdin(tmp_path):
    out = check_input(tmp_path, stdin=words(41))
    assert (out["input"], out["request_words"]) == ("found", 41)
    out = check_input(tmp_path, stdin="Add search\n")
    assert (out["input"], out["request_words"]) == ("none", 2)


def test_check_input_refuses_an_unknown_flag_and_a_flag_without_a_value(tmp_path):
    r = run(CHECK_INPUT, "--verbose", stdin="Add search")
    assert r.returncode == 2 and r.stdout == "" and "unknown argument '--verbose'" in r.stderr
    r = run(CHECK_INPUT, "Add search")
    assert r.returncode == 2 and "unknown argument 'Add search'" in r.stderr
    for flag in ("--source", "--root"):
        r = run(CHECK_INPUT, flag)
        assert r.returncode == 2 and r.stdout == "" and f"{flag} needs a value" in r.stderr, flag
    r = run(CHECK_INPUT, "--help")
    assert r.returncode == 0 and r.stdout.startswith("Decide whether there is enough input") and "Usage:" in r.stdout


def test_the_request_never_comes_from_the_command_line(tmp_path):
    """A request in a shell argument can run a command; --request is gone, and its use says where the request goes."""
    r = run(CHECK_INPUT, "--request", "Add search", "--root", str(tmp_path))
    assert r.returncode == 2 and r.stdout == "" and "read from standard input" in r.stderr
    r = run(CHECK_INPUT, "--root", str(tmp_path), stdin="")
    assert r.returncode == 2 and "standard input" in r.stderr
    request = 'Add search $(touch pwned) `touch pwned2` "quoted"'
    out = check_input(tmp_path, stdin=request)
    assert out["request_words"] == len(request.split()) and list(tmp_path.iterdir()) == []
