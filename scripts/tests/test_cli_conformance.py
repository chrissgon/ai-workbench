"""Command-line conformance of every script under skills/*/scripts: one rule set, no shared parser.

The checks, each applied to each script:

  help             `--help` exits 0 and prints text on stdout.
  value-flag-last  every value flag, given last without its value, exits 2 with a message on stderr and no
                   traceback. Value flags are read from the script's own `--help`: a flag written with its
                   value (`--file <path>`, `--file FILE`, `--kind {a,b}`, `--screen SCREEN-n`), under each
                   subcommand the help shows.
  unknown-flag     a flag the script does not have exits 2, with no traceback.
  usage-stderr     a usage error (the two probes above) says what is wrong on stderr and prints nothing on
                   stdout, where a caller reads data.
  report           `--report`, where a script has it, takes a path and writes the one record of the evidence
                   convention (scripts/tests/test_report_convention.py). The run that produces the record is
                   listed in cli_conformance_report_runs.json, since only the script knows a valid call.

Probes run in an empty folder, with no standard input and no route to the network, and never reach a
script's work: `--help`, a flag without its value and an unknown flag are all refused while arguments are read.
The unknown flag is given alone, so a script that ignores unknown flags but refuses a call without its
required arguments passes: that part of the rule rests on the script's own tests. A value flag that the help does not write with its value is not probed: the help is
where a caller learns the flags.

Scripts that fail today are fixed in their own skill's change, never here. Until then each failure is a line
of cli_conformance_expected_failures.txt (`<script> <check>`), marked as a strict expected failure: the day a
script passes, its line makes this test fail, and the change that fixed the script removes the line. A script
that fails and is not on the list fails too. The list is exact in both directions.

Run:   uv run --with pytest pytest scripts/tests/test_cli_conformance.py
Table: uv run --with pytest python3 scripts/tests/test_cli_conformance.py [<script path>...]
       (every failing check with its reason, and whether it is on the list)
"""
from __future__ import annotations

import concurrent.futures
import functools
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EXPECTED_FILE = HERE / "cli_conformance_expected_failures.txt"
REPORT_RUNS_FILE = HERE / "cli_conformance_report_runs.json"
CHECKS = ("help", "value-flag-last", "unknown-flag", "usage-stderr", "report")
RUNNERS = {".py": sys.executable, ".sh": "bash", ".mjs": "node"}
UNKNOWN_FLAG = "--no-such-flag-of-this-script"
TIMEOUT = 60
JOBS = 8  # scripts are independent of each other, so they are probed at the same time

FLAG = r"(?<![\w-])(--[a-z][a-z0-9-]*)"
# A value written after the flag: <path>, "<text>", {a,b}, FILE, SCREEN-n, or an example path with a slash.
# One space or "=", as help texts write it; two spaces start a description.
VALUE = re.compile(FLAG + r"(?:[ =])(?:<[^>\n]+>|\"[^\"\n]+\"|\{[^}\n]+\}|[A-Z][A-Z0-9_]*(?:-[a-z])?(?![\w])"
                   r"|[\w.-]+/[\w./-]+)")
TRACEBACK = re.compile(r"Traceback \(most recent call last\)|^\s+at .+:\d+:\d+\)?$|unbound variable", re.M)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report_problems = load("report_convention", HERE / "test_report_convention.py").report_problems


def skill_scripts(root=REPO):
    """Every file directly under a skill's scripts/ folder, as a path relative to the repository."""
    return sorted(str(p.relative_to(root)) for p in Path(root).glob("skills/*/scripts/*")
                  if p.is_file() and not p.name.startswith("."))


def probe_env():
    """The caller's environment without git's hook variables, and with no route to the network: a probe is
    refused while arguments are read, and one that is not must not reach a registry or a code host."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    for name in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        env[name] = "http://127.0.0.1:9"
    env.update(PYTHONDONTWRITEBYTECODE="1", NO_COLOR="1", GH_PROMPT_DISABLED="1", GIT_TERMINAL_PROMPT="0")
    return env


def run(script, args, cwd, root=REPO):
    path = Path(root) / script
    try:
        p = subprocess.run([RUNNERS[path.suffix], str(path), *args], cwd=cwd, env=probe_env(), text=True,
                           stdin=subprocess.DEVNULL, capture_output=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"args": args, "code": None, "out": "", "err": f"no exit after {TIMEOUT} s"}
    return {"args": args, "code": p.returncode, "out": p.stdout, "err": p.stderr}


def usage_line(script_name, line):
    """A match when the line is a usage line written by hand: the script's name after its interpreter or
    after "usage:", with the subcommand, if any, as group 1. Prose that names the script is not one."""
    return re.search(r"(?:\b(?:python3?|bash|sh|node)[ \t]+(?:\S*/)?|\busage:[ \t]*)" + re.escape(script_name)
                     + r"(?:[ \t]+([a-z][a-z0-9_-]*))?(?=[ \t]|$)", line, re.I)


def subcommands(help_text, script_name):
    """The subcommands a help text shows: argparse's `{a,b} ...` in the usage line, or a bare word after the
    script's name in a usage line written by hand (`script.py check --rules <file>`)."""
    found = []
    usage = re.search(r"^usage:.*?(?=\n\S|\n\n|\Z)", help_text, re.S | re.M)
    for group in re.findall(r"\{([a-z][\w-]*(?:,[a-z][\w-]*)*)\}\s+\.\.\.", usage.group(0) if usage else ""):
        found += group.split(",")
    found += [m.group(1) for m in map(functools.partial(usage_line, script_name), help_text.splitlines())
              if m and m.group(1)]
    return list(dict.fromkeys(found))


def value_flags(help_text, script_name, subs):
    """(prefix, flag) for every value flag of a help text. In a help written by hand a flag belongs to the
    subcommand of the usage line it stands on (a line that names the script, and the lines that continue it)."""
    found, prefix = [], ()
    for line in help_text.splitlines():
        named = usage_line(script_name, line)
        if named:
            prefix = (named.group(1),) if named.group(1) in subs else ()
        elif not line.strip():
            prefix = ()
        for flag in VALUE.findall(line):
            if (prefix, flag) not in found:
                found.append((prefix, flag))
    return found


def probe(script, root=REPO):
    """Run the probes of one script and return {check: [problems]}, plus what was found, under "_facts"."""
    name = Path(script).name
    problems = {check: [] for check in CHECKS}
    with tempfile.TemporaryDirectory() as cwd:
        helped = run(script, ["--help"], cwd, root)
        if helped["code"] != 0:
            problems["help"].append(f"--help exits {helped['code']}, not 0")
        elif len(helped["out"].strip()) < 20:
            problems["help"].append("--help prints no text on stdout")
        text = helped["out"] if helped["code"] == 0 else ""
        subs = subcommands(text, name)
        flags = value_flags(text, name, subs)
        all_flags = set(re.findall(FLAG, text))
        for sub in subs:  # a parser library documents a subcommand's flags under `<sub> --help`
            sub_help = run(script, [sub, "--help"], cwd, root)
            if sub_help["code"] == 0 and sub_help["out"].strip() != text.strip():
                all_flags |= set(re.findall(FLAG, sub_help["out"]))
                flags += [((sub,), f) for f in dict.fromkeys(VALUE.findall(sub_help["out"]))
                          if ((sub,), f) not in flags]
        usage_runs = []
        for prefix, flag in flags:
            r = run(script, [*prefix, flag], cwd, root)
            usage_runs.append(r)
            shown = " ".join([*prefix, flag])
            if r["code"] != 2:
                problems["value-flag-last"].append(f"`{shown}` last exits {r['code']}, not 2"
                                                   + (" (traceback)" if TRACEBACK.search(r["err"]) else ""))
            elif TRACEBACK.search(r["err"]):
                problems["value-flag-last"].append(f"`{shown}` last ends in a traceback")
        for prefix in [()] + [(s,) for s in subs]:
            r = run(script, [*prefix, UNKNOWN_FLAG], cwd, root)
            usage_runs.append(r)
            shown = " ".join([*prefix, "<unknown flag>"])
            if r["code"] != 2:
                problems["unknown-flag"].append(f"`{shown}` exits {r['code']}, not 2"
                                                + (" (traceback)" if TRACEBACK.search(r["err"]) else ""))
            elif TRACEBACK.search(r["err"]):
                problems["unknown-flag"].append(f"`{shown}` ends in a traceback")
        for r in usage_runs:
            if r["code"] in (0, None):
                continue  # not refused: the check that expected exit 2 says so
            shown = " ".join(a if a != UNKNOWN_FLAG else "<unknown flag>" for a in r["args"])
            if not r["err"].strip():
                problems["usage-stderr"].append(f"`{shown}`: no message on stderr")
            if r["out"].strip():
                problems["usage-stderr"].append(f"`{shown}`: the message is on stdout")
        if "--report" in all_flags:
            problems["report"] = report_check(script, [f for _, f in flags], root)
    problems["_facts"] = {"subcommands": subs, "value_flags": [" ".join([*p, f]) for p, f in flags]}
    return problems


def report_runs():
    return json.loads(REPORT_RUNS_FILE.read_text(encoding="utf-8"))


def report_check(script, flags, root=REPO, runs=None):
    if "--report" not in flags:
        return ["--report is a switch; the convention is `--report <path>`"]
    entry = (report_runs() if runs is None else runs).get(script)
    if not entry:
        return [f"--report has no run in {REPORT_RUNS_FILE.name}: add the arguments and input files of one "
                "run that reaches the check"]
    with tempfile.TemporaryDirectory() as cwd:
        for rel, content in entry.get("files", {}).items():
            target = Path(cwd) / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        r = run(script, [*entry["args"], "--report", "report.json"], cwd, root)
        if r["code"] not in (0, 1):
            return [f"the listed run exits {r['code']}, so it does not reach the check: {r['err'].strip()[:200]}"]
        written = Path(cwd) / "report.json"
        if not written.is_file():
            return ["the listed run wrote no file at the --report path"]
        args, given = entry["args"], {}
        for i, a in enumerate(args):
            if a in flags and i + 1 < len(args):
                given[a] = args[i + 1]
        return report_problems(written.read_text(encoding="utf-8"), Path(script).name, r["code"],
                               given=given, stdout=r["out"])


@functools.lru_cache(maxsize=None)
def results():
    """{script: {check: [problems]}} for every script that has a runner, all probed once, in parallel."""
    scripts = [s for s in skill_scripts() if Path(s).suffix in RUNNERS and shutil.which(RUNNERS[Path(s).suffix])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=JOBS) as pool:
        return dict(zip(scripts, pool.map(probe, scripts)))


def expected_failures(path=EXPECTED_FILE):
    """The (script, check) pairs of the list, in file order. A line is `<script> <check>`; `#` starts a comment."""
    pairs = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            script, _, check = line.partition(" ")
            pairs.append((script, check.strip()))
    return pairs


def cases():
    expected = set(expected_failures())
    for script in skill_scripts():
        for check in CHECKS:
            marks = [pytest.mark.xfail(strict=True, reason="listed in " + EXPECTED_FILE.name)] \
                if (script, check) in expected else []
            yield pytest.param(script, check, id=f"{script}::{check}", marks=marks)


@pytest.mark.parametrize("script,check", list(cases()))
def test_script_conforms(script, check):
    suffix = Path(script).suffix
    assert suffix in RUNNERS, f"{script}: no runner for {suffix!r} files; add one to RUNNERS, with its probes"
    if not shutil.which(RUNNERS[suffix]):
        pytest.skip(f"{RUNNERS[suffix]} is not installed")
    problems = results()[script][check]
    assert not problems, f"{script} fails `{check}`: " + "; ".join(problems)


def test_the_expected_failure_list_is_exact_in_form():
    """Every line names a script that exists and a check of this file, once, in sorted order, so that two
    changes that each remove a line do not conflict on more than their own line."""
    pairs = expected_failures()
    scripts = set(skill_scripts())
    assert [p for p in pairs if p[0] not in scripts] == [], "lines that name no script under skills/*/scripts"
    assert [p for p in pairs if p[1] not in CHECKS] == [], f"lines whose check is not one of {CHECKS}"
    assert len(pairs) == len(set(pairs)), "a line is there twice"
    assert pairs == sorted(pairs), "the list is not sorted"


def test_every_listed_report_run_names_a_script():
    scripts = set(skill_scripts())
    assert [s for s in report_runs() if s not in scripts] == []


# The checks themselves, on three invented scripts: a conforming one, one written the way the nine failing
# scripts are, and one that takes --report.

GOOD = '''#!/usr/bin/env python3
"""Count the lines of a file.

Usage: python3 count.py --file <path> [--phase P-n] [--json]
"""
import json, sys

def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__.strip()); return 0
    args, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a in ("--file", "--phase"):
            if i + 1 >= len(argv):
                print(f"Error: {a} needs a value", file=sys.stderr); return 2
            args[a] = argv[i + 1]; i += 2
        elif a == "--json":
            i += 1
        else:
            print(f"Error: unknown argument {a}", file=sys.stderr); return 2
    if "--file" not in args:
        print("Error: --file is required", file=sys.stderr); return 2
    print(json.dumps({"lines": len(open(args["--file"]).read().splitlines())})); return 0

sys.exit(main(sys.argv[1:]))
'''

BAD = '''#!/usr/bin/env python3
"""Count the lines of a file.

Usage: python3 count.py --file <path> [--top N]
"""
import json, sys
argv = sys.argv[1:]
if "--help" in argv:
    print(__doc__.strip()); sys.exit(0)
if "--top" in argv:
    top = argv[argv.index("--top") + 1]
if "--file" not in argv:
    print(json.dumps({"error": "--file is required"})); sys.exit(2)
path = argv[argv.index("--file") + 1]
print(len(open(path).read().splitlines()))
'''

REPORTING = '''#!/usr/bin/env python3
"""Check that a file has a title.

Usage: python3 lint_title.py --file <path> [--report <path>]
"""
import json, sys
argv = sys.argv[1:]
if "--help" in argv:
    print(__doc__.strip()); sys.exit(0)
args = {}
for flag in ("--file", "--report"):
    if flag in argv:
        if argv.index(flag) + 1 >= len(argv):
            print(f"Error: {flag} needs a value", file=sys.stderr); sys.exit(2)
        args[flag] = argv[argv.index(flag) + 1]
if "--file" not in args or [a for a in argv if a.startswith("--") and a not in args]:
    print("Error: usage: --file <path> [--report <path>]", file=sys.stderr); sys.exit(2)
try:
    text = open(args["--file"]).read()
except OSError as e:
    print(f"Error: cannot read {args['--file']}: {e}", file=sys.stderr); sys.exit(2)
errors = [] if text.startswith("# ") else ["the first line is not a title"]
ok = not errors
summary = f"lint_title {'ok' if ok else 'FAILED'}: {len(errors)} errors"
if "--report" in args:
    record = {"script": "lint_title.py", "date": "2026-10-02", "arguments": {"--file": args["--file"]},
              "ok": ok, "summary": summary, "errors": errors__EXTRA__}
    with open(args["--report"], "w") as f:
        json.dump(record, f); f.write("\\n")
print(json.dumps({"ok": ok, "summary": summary, "errors": errors}))
sys.exit(0 if ok else 1)
'''


def invented(tmp_path, name, source):
    folder = tmp_path / "skills" / "core-demo" / "scripts"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(source)
    (folder / "tests").mkdir(exist_ok=True)
    return f"skills/core-demo/scripts/{name}"


def test_a_conforming_script_passes_every_check(tmp_path):
    script = invented(tmp_path, "count.py", GOOD)
    assert skill_scripts(tmp_path) == [script], "the tests folder is not a script"
    found = probe(script, tmp_path)
    assert found["_facts"]["value_flags"] == ["--file", "--phase"]
    assert {check: found[check] for check in CHECKS} == {check: [] for check in CHECKS}


def test_a_script_that_reads_past_the_arguments_fails_three_checks(tmp_path):
    found = probe(invented(tmp_path, "count.py", BAD), tmp_path)
    assert found["help"] == []
    assert found["value-flag-last"] == ["`--file` last exits 1, not 2 (traceback)",
                                        "`--top` last exits 1, not 2 (traceback)"]
    assert found["unknown-flag"] == []  # refused for the missing --file: the limit the docstring states
    assert found["usage-stderr"] == ["`<unknown flag>`: no message on stderr",
                                     "`<unknown flag>`: the message is on stdout"]


def test_a_script_without_help_fails_the_help_check(tmp_path):
    found = probe(invented(tmp_path, "read.py", "import json, sys\njson.load(sys.stdin)\n"), tmp_path)
    assert found["help"] == ["--help exits 1, not 0"]
    assert found["unknown-flag"] == ["`<unknown flag>` exits 1, not 2 (traceback)"]


def test_subcommands_are_read_from_both_kinds_of_help(tmp_path):
    by_hand = ("Usage:\n  python3 stats.py profile <file>...\n  python3 stats.py check --rules <file>\n"
               "                         [--max 3]\n\n  --rules <file> also applies to nothing else\n")
    assert subcommands(by_hand, "stats.py") == ["profile", "check"]
    assert value_flags(by_hand, "stats.py", ["profile", "check"]) == [(("check",), "--rules"), ((), "--rules")]
    library = "usage: state.py [-h] {show,add} ...\n\npositional arguments:\n  {show,add}\n"
    assert subcommands(library, "state.py") == ["show", "add"]
    script = invented(tmp_path, "state.py", "import argparse\np = argparse.ArgumentParser()\n"
                      "s = p.add_subparsers(dest='cmd', required=True)\na = s.add_parser('add')\n"
                      "a.add_argument('--id', required=True)\na.add_argument('--dry-run', action='store_true')\n"
                      "s.add_parser('show')\np.parse_args()\n")
    found = probe(script, tmp_path)
    assert found["_facts"] == {"subcommands": ["add", "show"], "value_flags": ["add --id"]}
    assert {check: found[check] for check in CHECKS} == {check: [] for check in CHECKS}


def test_value_flags_are_the_flags_written_with_a_value():
    text = ("  --file FILE     the file\n  -k, --kind {a,b}  the kind\n  --json          print JSON output\n"
            "[--flows <flows.md> --screen SCREEN-n] [--report] --out=<dir>\n  --quiet  A switch.\n"
            '[--note "<text>"] --state docs/workbench/state.md --dry-run and then\n')
    assert [f for _, f in value_flags(text, "x.py", [])] == ["--file", "--kind", "--flows", "--screen", "--out",
                                                             "--note", "--state"]


def test_the_report_check(tmp_path):
    script = invented(tmp_path, "lint_title.py", REPORTING.replace("__EXTRA__", ""))
    runs = {script: {"args": ["--file", "a.md"], "files": {"a.md": "no title\n"}}}
    assert report_check(script, ["--file", "--report"], tmp_path, runs) == []
    assert "is a switch" in report_check(script, ["--file"], tmp_path, runs)[0]
    assert "has no run" in report_check(script, ["--file", "--report"], tmp_path, {})[0]
    missing = {script: {"args": ["--file", "absent.md"]}}
    assert "does not reach the check" in report_check(script, ["--file", "--report"], tmp_path, missing)[0]
    other = invented(tmp_path, "lint_title.py", REPORTING.replace("__EXTRA__", ', "file": args["--file"]'))
    assert report_check(other, ["--file", "--report"], tmp_path, runs) == ["keys outside the shape: file"]
    found = probe(script, tmp_path)  # no run listed in the repository's own file for an invented script
    assert "has no run" in found["report"][0]


def main(argv):
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    wanted, expected, failing = set(argv), set(expected_failures()), 0
    for script, found in results().items():
        if wanted and script not in wanted:
            continue
        for check in CHECKS:
            if found[check]:
                failing += 1
                listed = "listed" if (script, check) in expected else "NOT LISTED"
                print(f"{script} {check}  [{listed}]\n    " + "\n    ".join(found[check]))
    print(f"{failing} failing checks", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
