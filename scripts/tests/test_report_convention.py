"""The evidence convention: the one shape of the record a check script writes with `--report <path>`.

A check script (a lint or a check of an artifact) that takes `--report` takes it as `--report <path>` and
writes one JSON object there on every run that reaches the check (exit 0 or 1), never on a usage error:

  {
    "script": "lint_thing.py",                  the script's file name
    "date": "2026-10-02",                       the day of the run, YYYY-MM-DD
    "arguments": {"--file": "docs/thing.md"},   every flag given except --report, as typed: a value flag maps
                                                to its value (a repeated one to the list of its values), a
                                                switch to true
    "ok": false,                                true exactly when the script exits 0
    "summary": "lint_thing FAILED: 2 errors",   one line; the same `summary` the script prints on stdout, and
                                                the line a reply quotes
    "errors": ["...", "..."],                   one string per problem; empty exactly when ok is true
    "warnings": ["..."],                        optional: strings that do not fail the check
    "counts": {"sections": 4}                   optional: what was counted, name to number
  }

No other key. `report_problems` is the reference check of that shape; scripts/tests/test_cli_conformance.py
applies it to every script under skills/*/scripts that takes `--report`. The text of the convention for
authors is in templates/capability.SKILL.md, and the last test here keeps the two in agreement.

Run: uv run --with pytest pytest scripts/tests/test_report_convention.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REQUIRED = ("script", "date", "arguments", "ok", "summary", "errors")
OPTIONAL = ("warnings", "counts")
REPLY_CHECK_LINE = ("- Check: `<the command exactly as run>` → `<the summary line it printed, copied character "
                    "for character>`; recorded in <the path given to --report>")
REPLY_FILES_LINE = ("- Files changed: <the lines `git status --short` printed, copied; `none` when it printed "
                    "nothing>")
ASSERTION_FORM = ("`<report path>` is among the files the run produced, its `ok` is true, and the reply quotes "
                  "its `summary` line")


def strings(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def report_problems(text, script, exit_code, given=None, stdout=None):
    """What is wrong with the record a check script wrote, as a list of sentences; empty when it conforms.

    text: the content of the file; script: the script's file name; exit_code: what the run exited with;
    given: the flags the run was given, as the record's `arguments` must hold them (optional);
    stdout: what the run printed, to compare its `summary` with the record's (optional)."""
    try:
        record = json.loads(text)
    except ValueError as e:
        return [f"the report is not JSON: {e}"]
    if not isinstance(record, dict):
        return ["the report is not one JSON object"]
    problems = []
    if not text.endswith("\n"):
        problems.append("the report does not end with a newline")
    missing = [k for k in REQUIRED if k not in record]
    if missing:
        problems.append("missing keys: " + ", ".join(missing))
    unknown = [k for k in record if k not in REQUIRED + OPTIONAL]
    if unknown:
        problems.append("keys outside the shape: " + ", ".join(sorted(unknown)))
    if "script" in record and record["script"] != script:
        problems.append(f'"script" is {record["script"]!r}, not the file name {script!r}')
    if "date" in record and not (isinstance(record["date"], str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["date"])):
        problems.append('"date" is not YYYY-MM-DD')
    arguments = record.get("arguments")
    if "arguments" in record:
        if not isinstance(arguments, dict):
            problems.append('"arguments" is not an object')
        else:
            bad = [k for k, v in arguments.items()
                   if not k.startswith("--") or not (v is True or isinstance(v, str) or (strings(v) and v))]
            if bad:
                problems.append('"arguments" entries that are not a flag with its value, its values or true: '
                                + ", ".join(sorted(bad)))
            if "--report" in arguments:
                problems.append('"arguments" holds --report')
            for flag, value in (given or {}).items():
                if arguments.get(flag) != value:
                    problems.append(f'"arguments" lacks {flag} with the value given')
    ok = record.get("ok")
    if "ok" in record:
        if not isinstance(ok, bool):
            problems.append('"ok" is not true or false')
        elif ok != (exit_code == 0):
            problems.append(f'"ok" is {json.dumps(ok)} and the exit code is {exit_code}')
    summary = record.get("summary")
    if "summary" in record and not (isinstance(summary, str) and summary.strip() and "\n" not in summary):
        problems.append('"summary" is not one non-empty line')
    if "errors" in record:
        if not strings(record["errors"]):
            problems.append('"errors" is not a list of strings')
        elif isinstance(ok, bool) and ok != (not record["errors"]):
            problems.append('"errors" is empty exactly when "ok" is true')
    if "warnings" in record and not strings(record["warnings"]):
        problems.append('"warnings" is not a list of strings')
    if "counts" in record and not (isinstance(record["counts"], dict) and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in record["counts"].values())):
        problems.append('"counts" is not an object of numbers')
    if stdout is not None and isinstance(summary, str):
        try:
            printed = json.loads(stdout)
        except ValueError:
            printed = None
        if not isinstance(printed, dict) or printed.get("summary") != summary or printed.get("ok") != ok:
            problems.append('stdout is not JSON with the same "ok" and "summary" as the report')
    return problems


def good(**changes):
    record = {"script": "lint_thing.py", "date": "2026-10-02", "arguments": {"--file": "docs/thing.md"},
              "ok": False, "summary": "lint_thing FAILED: 1 error", "errors": ["section Scope is missing"]}
    record.update(changes)
    return record


def dump(record):
    return json.dumps(record, indent=2) + "\n"


def test_a_conforming_record_has_no_problem():
    assert report_problems(dump(good()), "lint_thing.py", 1) == []
    full = good(ok=True, errors=[], summary="lint_thing ok: 0 errors", warnings=["a long line"],
                counts={"sections": 4}, arguments={"--file": "a.md", "--source": ["b.md", "c.md"], "--strict": True})
    stdout = json.dumps({"ok": True, "summary": "lint_thing ok: 0 errors", "errors": []})
    assert report_problems(dump(full), "lint_thing.py", 0, given={"--file": "a.md"}, stdout=stdout) == []


def test_each_departure_from_the_shape_is_named():
    def problems(record, exit_code=1, **kw):
        return " | ".join(report_problems(dump(record), "lint_thing.py", exit_code, **kw))

    assert "not JSON" in " ".join(report_problems("ok: true\n", "lint_thing.py", 0))
    assert "not one JSON object" in " ".join(report_problems("[]\n", "lint_thing.py", 0))
    assert "newline" in " ".join(report_problems(json.dumps(good()), "lint_thing.py", 1))
    without = good()
    del without["summary"], without["script"]
    assert "missing keys: script, summary" in problems(without)
    # The three shapes the four scripts wrote before the convention: arguments as top-level keys.
    assert "keys outside the shape: file, prd" in problems(good(file="a.md", prd="b.md"))
    assert "not the file name" in problems(good(script="skills/x/scripts/lint_thing.py"))
    assert "YYYY-MM-DD" in problems(good(date="02/10/2026"))
    assert '"arguments" is not an object' in problems(good(arguments=["--file", "a.md"]))
    assert "not a flag with its value" in problems(good(arguments={"file": "a.md"}))
    assert "not a flag with its value" in problems(good(arguments={"--phase": None}))
    assert "holds --report" in problems(good(arguments={"--report": "lint.json"}))
    assert "lacks --file" in problems(good(), given={"--file": "other.md"})
    assert "not true or false" in problems(good(ok="false"))
    assert "the exit code is 0" in problems(good(), exit_code=0)
    assert "one non-empty line" in problems(good(summary="two\nlines"))
    assert "one non-empty line" in problems(good(summary=" "))
    assert '"errors" is not a list of strings' in problems(good(errors=[{"id": "E1"}]))
    assert "empty exactly when" in problems(good(errors=[]))
    assert "empty exactly when" in problems(good(ok=True), exit_code=0)
    assert '"warnings" is not a list of strings' in problems(good(warnings="one"))
    assert '"counts" is not an object of numbers' in problems(good(counts={"sections": "4"}))
    assert "stdout is not JSON with the same" in problems(good(), stdout=json.dumps({"ok": False, "summary": "other"}))
    assert "stdout is not JSON with the same" in problems(good(), stdout="lint_thing FAILED")


def test_the_capability_template_states_the_convention_this_file_checks():
    """An author reads the template, the conformance test applies this file: they must say the same thing."""
    template = (REPO / "templates" / "capability.SKILL.md").read_text(encoding="utf-8")
    assert REPLY_CHECK_LINE in template
    assert REPLY_FILES_LINE in template
    assert ASSERTION_FORM in template
    assert "`--report <path>`" in template
    shape = re.search(r"^Check scripts\b.*$", template, re.M)
    assert shape, "the paragraph that starts with 'Check scripts' is gone from the template"
    for key in REQUIRED + OPTIONAL:
        assert f"`{key}`" in shape.group(0), f"the template's shape paragraph does not name `{key}`"
