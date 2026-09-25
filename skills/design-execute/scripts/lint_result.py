#!/usr/bin/env python3
"""Lint a design results document against its brief.

Usage: python3 lint_result.py --file <results.md> --brief <brief.md> [--root <dir>] [--json]

Checks:
  - required sections (Runs, Critique, Decision, Next) and header lines (Brief, Tool, Mode)
  - every run row has a status among planned, waiting on user, done, approved
  - every run marked done or approved lists outputs, and every output path that is not a URL exists
    (relative to --root, default the current directory)
  - every CRIT of the brief has a Critique row, and every done or approved run has a verdict in it:
    pass, partial or fail followed by ':' and evidence
  - when every run of the latest round is done, a Recommendation is written
  - the document status is "waiting on user" when any run is waiting on the user

Prints JSON. Exit codes: 0 ok, 1 problems found, 2 usage error.
"""
import json
import os
import re
import sys

STATUSES = {"planned", "waiting on user", "done", "approved"}


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


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        print(__doc__)
        return 0 if argv else 2
    as_json = "--json" in argv
    args = {}
    for flag in ("--file", "--brief", "--root"):
        if flag in argv:
            args[flag] = argv[argv.index(flag) + 1]
    if "--file" not in args or "--brief" not in args:
        print("Error: --file and --brief are required. See --help.", file=sys.stderr)
        return 2
    root = args.get("--root", ".")
    try:
        text = open(args["--file"], encoding="utf-8").read()
        brief = open(args["--brief"], encoding="utf-8").read()
    except OSError as e:
        print(f"Error: cannot read input: {e}", file=sys.stderr)
        return 2
    errors = []
    for s in ("Runs", "Critique", "Decision", "Next"):
        if not re.search(r"^## " + s + r"\s*$", text, re.M):
            errors.append(f"missing section '## {s}'")
    for h in ("Brief", "Tool", "Mode"):
        if not re.search(r"^- " + h + r":\s*\S", text, re.M):
            errors.append(f"missing header line '- {h}:'")
    _, runs = table(section(text, "Runs"))
    run_ids, done_ids, waiting, rounds = [], [], False, {}
    for r in runs:
        if len(r) < 5:
            errors.append(f"run row {r[0] if r else '?'} has fewer than 5 cells"); continue
        rid, rnd, _, status, outputs = r[:5]
        run_ids.append(rid)
        st = status.lower()
        if st not in STATUSES:
            errors.append(f"{rid}: status {status!r} is not one of {sorted(STATUSES)}")
        rounds.setdefault(rnd, []).append(st)
        if st == "waiting on user":
            waiting = True
        if st in ("done", "approved"):
            done_ids.append(rid)
            paths = [p.strip(" `") for p in re.split(r"[,;]| and ", outputs) if p.strip(" `")]
            if not paths or outputs.strip() in ("", "-", "—"):
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
                errors.append(f"Critique has no column for {rid}"); continue
            cell = by_crit[c][head.index(rid)] if head.index(rid) < len(by_crit[c]) else ""
            if not re.match(r"^(pass|partial|fail)\s*:\s*\S", cell, re.I):
                errors.append(f"{c} × {rid}: verdict must be 'pass|partial|fail: evidence', got {cell!r}")
    if rounds:
        latest = sorted(rounds, key=lambda x: int(re.sub(r"\D", "", x) or 0))[-1]
        if all(s in ("done", "approved") for s in rounds[latest]):
            if not re.search(r"^- Recommendation:\s*(?!\{)\S", section(text, "Decision"), re.M):
                errors.append("every run of the latest round is done but no Recommendation is written")
    if waiting and not re.search(r"^- Status:\s*waiting on user", text, re.M):
        errors.append("a run is waiting on the user but the document status is not 'waiting on user'")
    ok = not errors
    print(json.dumps({"ok": ok, "counts": {"runs": len(run_ids), "done": len(done_ids),
                      "criteria": len(brief_crits)}, "errors": errors}, indent=2 if as_json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
