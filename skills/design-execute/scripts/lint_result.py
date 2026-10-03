#!/usr/bin/env python3
"""Lint a design results document against its brief.

Usage: python3 lint_result.py --file <results.md> --brief <brief.md> [--root <dir>]
                              [--report <results.lint.json>] [--json]

Checks:
  - required sections (Runs, Critique, Decision, Next) and header lines (Brief, Tool, Mode)
  - Runs has the columns Run, Round, Direction, Status, Pack and Outputs
  - every run row has a status among planned, waiting on user, done, approved
  - every run row names its prompt pack in Pack (a path ending in prompt.md), and that file exists
  - every run marked done or approved lists outputs, and every output path that is not a URL exists
    (paths are relative to --root, default the current directory)
  - every CRIT of the brief has a Critique row, and every done or approved run has a verdict in it:
    pass, partial or fail followed by ':' and evidence
  - when every run of the latest round is done, a Recommendation is written
  - the document status is "waiting on user" when any run is waiting on the user

Prints JSON on stdout: ok, summary (the line a reply quotes), counts, errors. --report <path> also writes
the record of the evidence convention to that file (script, date, arguments, ok, summary, errors, counts),
kept next to the results document as the evidence of the last run. Usage errors go to stderr.
Exit codes: 0 ok, 1 problems found, 2 usage error.
"""
import datetime
import json
import os
import re
import sys

STATUSES = {"planned", "waiting on user", "done", "approved"}
VALUE_FLAGS = ("--file", "--brief", "--root", "--report")
SWITCHES = ("--json",)
COLUMNS = ("Run", "Round", "Direction", "Status", "Pack", "Outputs")
EMPTY = ("", "-", "—")


def section(text, title):
    m = re.search(r"^## " + re.escape(title) + r"\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^## ", rest, re.M)
    return rest[: n.start()] if n else rest


def table(sec):
    rows = []
    for ln in sec.splitlines():
        if ln.startswith("|") and not re.match(r"^\|\s*-", ln):
            rows.append([c.strip() for c in ln.strip().strip("|").split("|")])
    return rows[0] if rows else [], rows[1:]


def parse(argv):
    """The flags given, as {flag: value or True}, and None; or None and the message of a usage error."""
    args, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a in VALUE_FLAGS:
            if i + 1 >= len(argv):
                return None, f"{a} needs a value"
            args[a] = argv[i + 1]
            i += 2
        elif a in SWITCHES:
            args[a] = True
            i += 1
        else:
            return None, f"unknown argument {a!r}"
    if "--file" not in args or "--brief" not in args:
        return None, "--file and --brief are required"
    return args, None


def check(text, brief, root):
    """(errors, counts) of a results document against its brief."""
    errors = []
    for s in ("Runs", "Critique", "Decision", "Next"):
        if not re.search(r"^## " + s + r"\s*$", text, re.M):
            errors.append(f"missing section '## {s}'")
    for h in ("Brief", "Tool", "Mode"):
        if not re.search(r"^- " + h + r":\s*\S", text, re.M):
            errors.append(f"missing header line '- {h}:'")
    run_head, runs = table(section(text, "Runs"))
    missing = [c for c in COLUMNS if c not in run_head]
    if run_head and missing:
        errors.append("Runs lacks the column(s) " + ", ".join(missing))
    col = {c: run_head.index(c) for c in COLUMNS if c in run_head}

    def cell(row, name):
        return row[col[name]] if name in col and col[name] < len(row) else ""

    run_ids, done_ids, waiting, rounds, packs = [], [], False, {}, 0
    for r in runs:
        if len(r) < len(run_head):
            errors.append(f"run row {r[0] if r else '?'} has fewer than {len(run_head)} cells")
            continue
        rid, status, outputs = cell(r, "Run"), cell(r, "Status"), cell(r, "Outputs")
        run_ids.append(rid)
        st = status.lower()
        if st not in STATUSES:
            errors.append(f"{rid}: status {status!r} is not one of {sorted(STATUSES)}")
        rounds.setdefault(cell(r, "Round"), []).append(st)
        if st == "waiting on user":
            waiting = True
        if "Pack" in col:
            pack = cell(r, "Pack").strip(" `")
            if not pack.endswith("prompt.md"):
                errors.append(f"{rid}: Pack must be the path of the run's prompt.md, got {pack!r}")
            elif not os.path.isfile(os.path.join(root, pack)):
                errors.append(f"{rid}: prompt pack {pack} does not exist")
            else:
                packs += 1
        if st in ("done", "approved"):
            done_ids.append(rid)
            paths = [p.strip(" `") for p in re.split(r"[,;]| and ", outputs) if p.strip(" `") not in EMPTY]
            if not paths:
                errors.append(f"{rid}: marked {st} but lists no outputs")
            for p in paths:
                if re.match(r"https?://", p) or " " in p:
                    continue
                if not os.path.exists(os.path.join(root, p)):
                    errors.append(f"{rid}: output {p} does not exist")
    if not run_ids:
        errors.append("Runs has no rows")
    head, crit_rows = table(section(text, "Critique"))
    brief_crits = re.findall(r"^\s*-\s*(CRIT-\d+):", section(brief, "Evaluation criteria"), re.M)
    by_crit = {r[0]: r for r in crit_rows if r}
    for c in brief_crits:
        if c not in by_crit:
            errors.append(f"{c} of the brief has no Critique row")
            continue
        for rid in done_ids:
            if rid not in head:
                errors.append(f"Critique has no column for {rid}")
                continue
            verdict = by_crit[c][head.index(rid)] if head.index(rid) < len(by_crit[c]) else ""
            if not re.match(r"^(pass|partial|fail)\s*:\s*\S", verdict, re.I):
                errors.append(f"{c} × {rid}: verdict must be 'pass|partial|fail: evidence', got {verdict!r}")
    if rounds:
        latest = sorted(rounds, key=lambda x: int(re.sub(r"\D", "", x) or 0))[-1]
        if all(s in ("done", "approved") for s in rounds[latest]):
            if not re.search(r"^- Recommendation:\s*(?!\{)\S", section(text, "Decision"), re.M):
                errors.append("every run of the latest round is done but no Recommendation is written")
    if waiting and not re.search(r"^- Status:\s*waiting on user", text, re.M):
        errors.append("a run is waiting on the user but the document status is not 'waiting on user'")
    counts = {"runs": len(run_ids), "done": len(done_ids), "packs": packs, "criteria": len(brief_crits)}
    return errors, counts


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    args, problem = parse(argv)
    if problem:
        print(f"Error: {problem}. See --help.", file=sys.stderr)
        return 2
    try:
        text = open(args["--file"], encoding="utf-8").read()
        brief = open(args["--brief"], encoding="utf-8").read()
    except OSError as e:
        print(f"Error: cannot read input: {e}", file=sys.stderr)
        return 2
    errors, counts = check(text, brief, args.get("--root", "."))
    ok = not errors
    summary = (f"lint_result {'ok' if ok else 'FAILED'}: {len(errors)} errors; {counts['runs']} runs, "
               f"{counts['done']} done, {counts['packs']} prompt packs, {counts['criteria']} criteria")
    if "--report" in args:
        record = {"script": "lint_result.py", "date": datetime.date.today().isoformat(),
                  "arguments": {k: v for k, v in args.items() if k != "--report"},
                  "ok": ok, "summary": summary, "errors": errors, "counts": counts}
        try:
            with open(args["--report"], "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
                f.write("\n")
        except OSError as e:
            print(f"Error: cannot write the report: {e}", file=sys.stderr)
            return 2
    result = {"ok": ok, "summary": summary, "counts": counts, "errors": errors}
    print(json.dumps(result, indent=2 if args.get("--json") else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
