"""Tests for shared/scripts/contrast.py: one source for the two copies that had diverged (one read pairs
with a use on standard input and refused bad colours; the other read a file of light and dark pairs, printed
a table and ended in a traceback on a bad colour or a flag without its value). Offline; every name and
number below is fictional.

Run: uv run --with pytest pytest shared/scripts/tests
"""
from __future__ import annotations

import json

import pytest

from shared_helpers import clean_usage_error, run

CONTRAST = "contrast.py"
PAIRS = {"pairs": [{"name": "white on black", "fg": "#FFF", "bg": "#000000", "use": "text"},
                   {"name": "blue on white", "fg": "#0092CD", "bg": "#FFFFFF", "use": "large"},
                   {"name": "blue on white small", "fg": "#0092CD", "bg": "#FFFFFF", "use": "text"}]}
MODES = [{"name": "body", "light": ["#1A1A1A", "#FFFFFF"], "dark": ["#F2F2F2", "#121212"]},
         {"name": "button label", "light": ["#FFFFFF", "#0092CD"], "large": True},
         {"name": "focus ring", "dark": ["#0092CD", "#121212"], "use": "graphic"}]


# --- pairs with a use, on standard input: JSON ---------------------------------------------------------

def test_contrast_computes_wcag_ratios_and_fails_by_use():
    r = run(CONTRAST, stdin=json.dumps(PAIRS))
    assert r.returncode == 1
    result = json.loads(r.stdout)
    out = {p["name"]: p for p in result["pairs"]}
    assert result["ok"] is False
    assert out["white on black"] == {"name": "white on black", "fg": "#FFF", "bg": "#000000", "use": "text",
                                     "ratio": 21.0, "minimum": 4.5, "pass": True}
    assert out["blue on white"]["ratio"] == 3.5 and out["blue on white"]["pass"] is True
    assert out["blue on white small"]["pass"] is False


def test_every_pair_passing_exits_0():
    r = run(CONTRAST, stdin=json.dumps({"pairs": PAIRS["pairs"][:2]}))
    assert r.returncode == 0 and json.loads(r.stdout)["ok"] is True


def test_contrast_refuses_bad_colours_and_uses():
    for pair in ({"fg": "blue", "bg": "#000"}, {"fg": "#000", "bg": "#FFF", "use": "huge"}, {"fg": "#12", "bg": "#000"},
                 {"light": ["#000"]}, {"light": "#000", "dark": None}, {"dark": ["#000", "#GGGGGG"]}, "#000 on #FFF"):
        assert clean_usage_error(run(CONTRAST, stdin=json.dumps({"pairs": [pair]}))), pair
    for text in ("[]", "{}", '{"pairs": []}', "not json", ""):
        assert clean_usage_error(run(CONTRAST, stdin=text)), text


# --- pairs in a light and a dark mode: a file, a table ----------------------------------------------------

def pairs_file(tmp_path, data=MODES):
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_a_file_of_pairs_prints_a_table_with_a_ratio_per_mode(tmp_path):
    r = run(CONTRAST, "--pairs", pairs_file(tmp_path))
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == [
        "| Pair | Light ratio | Dark ratio | AA |",
        "|------|-------------|------------|----|",
        "| body | 17.40:1 | 16.73:1 | pass (needs 4.5:1) |",
        "| button label | 3.50:1 | n/a | pass (needs 3.0:1) |",
        "| focus ring | n/a | 5.35:1 | pass (needs 3.0:1) |"]


def test_the_table_is_printed_and_the_exit_is_1_when_a_pair_fails_in_one_mode(tmp_path):
    """The copy that printed the table always exited 0, so a failing pair had to be read off the table."""
    data = [{"name": "muted", "light": ["#767676", "#FFFFFF"], "dark": ["#767676", "#121212"]}]
    r = run(CONTRAST, "--pairs", pairs_file(tmp_path, data))
    assert r.returncode == 1 and "| muted | 4.54:1 | 4.12:1 | fail (needs 4.5:1) |" in r.stdout
    as_json = json.loads(run(CONTRAST, "--pairs", pairs_file(tmp_path, data), "--json").stdout)
    assert as_json == {"ok": False, "pairs": [{
        "name": "muted", "use": "text", "minimum": 4.5, "pass": False,
        "light": {"fg": "#767676", "bg": "#FFFFFF", "ratio": 4.54, "pass": True},
        "dark": {"fg": "#767676", "bg": "#121212", "ratio": 4.12, "pass": False}}]}


def test_a_file_may_hold_either_shape_of_pair_and_either_wrapping(tmp_path):
    wrapped = run(CONTRAST, "--pairs", pairs_file(tmp_path, {"pairs": PAIRS["pairs"][:1] + MODES[:1]}))
    assert wrapped.returncode == 0
    assert "| white on black | 21.00:1 | n/a | pass (needs 4.5:1) |" in wrapped.stdout and "| body |" in wrapped.stdout
    both = run(CONTRAST, stdin=json.dumps({"pairs": MODES}))  # the two-mode shape on standard input: JSON
    assert both.returncode == 0 and [p["name"] for p in json.loads(both.stdout)["pairs"]] == ["body", "button label", "focus ring"]


def test_one_pair_on_the_command_line():
    r = run(CONTRAST, "--pair", "label", "#FFFFFF", "#0092CD")
    assert r.returncode == 1 and "| label | 3.50:1 | n/a | fail (needs 4.5:1) |" in r.stdout
    assert run(CONTRAST, "--pair", "label", "#FFFFFF", "#0092CD", "--large").returncode == 0
    r = run(CONTRAST, "--pair", "ring", "#fff", "#0092cd", "--use", "graphic", "--json")
    assert r.returncode == 0 and json.loads(r.stdout)["pairs"][0]["use"] == "graphic"


@pytest.mark.parametrize("args", [
    ("--pairs",), ("--pair",), ("--pair", "label"), ("--pair", "label", "#FFFFFF"), ("--use",), ("--nope",),
    ("--pair", "label", "#FFFFFF", "#0092CD", "--use"), ("--pair", "label", "#FFFFFF", "#0092CD", "--use", "huge"),
    ("--pair", "label", "#FFFFFF", "#0092CD", "--large", "--use", "text"), ("--pair", "label", "#12", "#0092CD"),
    ("--pair", "label", "white", "black"), ("--json",), ("--large",), ("extra",),
])
def test_every_flag_is_checked(args):
    """A flag given last without its value, and a colour that is not #RGB or #RRGGBB, ended in a traceback."""
    assert clean_usage_error(run(CONTRAST, *args)), args


def test_a_pairs_file_is_checked_too(tmp_path):
    good = pairs_file(tmp_path)
    assert clean_usage_error(run(CONTRAST, "--pairs", str(tmp_path / "absent.json")))
    assert clean_usage_error(run(CONTRAST, "--pairs", good, "--large"))
    assert clean_usage_error(run(CONTRAST, "--pairs", good, "--pair", "label", "#FFFFFF", "#0092CD"))
    assert clean_usage_error(run(CONTRAST, "--pairs", good, "--pairs", good))
    assert clean_usage_error(run(CONTRAST, "--pairs", pairs_file(tmp_path, [])))
    (tmp_path / "pairs.json").write_text("not json", encoding="utf-8")
    assert clean_usage_error(run(CONTRAST, "--pairs", good))


def test_help_exits_0_wherever_it_is_given():
    for args in (("--help",), ("-h",), ("--pairs", "--help")):
        r = run(CONTRAST, *args)
        assert r.returncode == 0 and "Usage:" in r.stdout and "Exit codes" in r.stdout
