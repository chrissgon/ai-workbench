"""WP-7.1: the ported social handler is its source with a closed list of replacements, byte for byte.

The three files under runtime/handlers/ were made with cp from scripts/runtime.py, scripts/runtime_vote.py and
scripts/vote_job.py and edited only as REPLACEMENTS says. While the old scripts stay (until WP-7.5), this test
keeps the two from drifting: a repair made to a source must be made in the port too, and the other way round.
The test of vote_job's port is retired from WP-7.3 on, and all of them at WP-7.6.
"""
import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HANDLERS = REPO / "runtime" / "handlers"
sys.path.insert(0, str(HANDLERS))

# source -> (ported file, [(find, replace, times in the source)])
REPLACEMENTS = {
    "scripts/runtime.py": ("runtime/handlers/social.py", [
        ("python3 scripts/runtime.py", "python3 runtime/handlers/social.py", 7),
        ("import runtime_vote  # noqa: E402  (the same folder)",
         "import social_vote as runtime_vote  # noqa: E402  (the same folder)", 1),
        ('here.parent / "providers" / "resolve.py"', 'here.parent.parent / "providers" / "resolve.py"', 1),
        ("`runtime.py pin`", "`social.py pin`", 1),
        ("<workbench>/scripts/runtime.py approve", "<workbench>/runtime/handlers/social.py approve", 1),
        ('"harness": "claude-code"', '"harness": "<harness>"', 1),  # R19: no AI tool named under runtime/
    ]),
    "scripts/runtime_vote.py": ("runtime/handlers/social_vote.py", [
        ('"job": wb / "scripts" / "vote_job.py",', '"job": wb / "runtime" / "handlers" / "social_vote_job.py",', 1),
    ]),
    "scripts/vote_job.py": ("runtime/handlers/social_vote_job.py", [
        ("python3 vote_job.py", "python3 social_vote_job.py", 1),
    ]),
}
VERBS_LINE = 'VERBS = ("tick", "pin", "add-comment", "status", "inbox", "approve", "reject")\n'
# No comment or docstring line was reworded: the lines that still name the old paths stay as they are.
REWORDED_LINES = []


def read(rel):
    return (REPO / rel).read_text(encoding="utf-8")


def test_each_ported_file_is_its_source_with_only_the_listed_replacements():
    for source, (port, replacements) in REPLACEMENTS.items():
        text = read(source)
        for find, replace, times in replacements:
            text = text.replace(find, replace)
        ported = read(port)
        if port.endswith("social.py"):
            assert ported.count(VERBS_LINE) == 1
            ported = ported.replace(VERBS_LINE, "")
        assert ported == text, f"{port} is not {source} with the listed replacements"
    assert REWORDED_LINES == []


def test_every_listed_replacement_occurs_the_stated_number_of_times():
    for source, (_, replacements) in REPLACEMENTS.items():
        text = read(source)
        for find, _, times in replacements:
            assert text.count(find) == times, f"{source}: {find!r} occurs {text.count(find)} times, not {times}"


def test_the_handler_lists_the_verbs_its_command_takes():
    import social
    source = read("runtime/handlers/social.py")
    choices = re.search(r'p\.add_argument\("verb", choices=(\[.*?\])\)', source).group(1)
    assert list(social.VERBS) == ast.literal_eval(choices)  # a literal list of words, read from our own file
    assert list(social.VERBS) == ["tick", "pin", "add-comment", "status", "inbox", "approve", "reject"]
