#!/usr/bin/env python3
"""Lint a feature section of a backlog against its specification and, when given, its design.

Usage: python3 lint_backlog.py --backlog <backlog.md> --spec <spec.md> [--feature <abbr>] [--design <design.md>]
                               [--report <path>] [--components-heading <text>] [--assumptions-heading <text>]
                               [--plan-heading <text>] [--json]

--feature may be omitted when the backlog holds tasks of one feature only (ids `T-<abbr>-<n>`).
--report <path> writes the record of the run to <path>: one JSON object with script, date, arguments, ok,
  summary, errors, warnings and counts, on every run that reaches the check, never on a usage error.
--components-heading, --assumptions-heading and --plan-heading give the start of the design's "## " headings
  of its components table, its assumptions to verify and its verification plan, for a design written in
  another language (defaults "Components", "Assumptions to verify", "Verification plan"; any case).

Checks, for tasks whose id starts with T-<abbr>-:
  - task ids are unique and every task has Does, Delivers, Touches, Depends on, Check, Size and Milestone lines
  - every REQ/NFR/EDGE/AC id cited in Delivers or Check exists in the specification
  - every task's Delivers cites at least one REQ or AC id
  - every dependency names an existing task of the same feature; no dependency cycles
  - every REQ, NFR and AC of the specification is delivered by at least one task (Delivers or Check)
  - Check is not a vague word ("works", "done", "ok"); it carries no duration in days and no date
  - Size is S, M or L followed by ", because"
  - every task's milestone appears in the Milestones list
  - a task titled "Spike: ..." has `Depends on: none` and at least one task that depends on it
  - a task titled "Remove ..." depends on at least one task
With --design:
  - every bullet under "Assumptions to verify" has a "Spike: ..." task, whose Check ends with
    "(design assumption <n>)", n being the position of the bullet
  - every other Check ends with "(verification plan: AC-n)" and contains that row's command
  - a task whose Touches names a design component that assumption n names depends on spike n,
    directly or through other tasks; no other task is required to depend on a spike
Prints JSON: ok, summary (one line to quote in the report), tasks, critical_path (longest dependency
chain by task count), coverage, errors.

Output: the JSON on stdout; a usage error on stderr.
Exit codes: 0 ok, 1 problems, 2 usage error (a flag without its value, an unknown flag, a file that cannot be
read or written).
"""
import datetime
import json
import re
import sys

VALUE_FLAGS = ("--backlog", "--spec", "--feature", "--design", "--report", "--components-heading",
               "--assumptions-heading", "--plan-heading")
SWITCHES = ("--json",)
HEADING_DEFAULTS = {"--components-heading": "Components", "--assumptions-heading": "Assumptions to verify",
                    "--plan-heading": "Verification plan"}

ID_RE = re.compile(r"\b((?:REQ|NFR|EDGE|AC)-\d+)\b")

DEF_RE = re.compile(r"^\s*-\s*((?:REQ|NFR|EDGE|AC)-\d+)\s*(?:\([^)]*\))?:", re.M)


def defined_ids(spec_text):
    """Ids the specification defines (`- REQ-n:` lines); a definition line saying "withdrawn" is excluded.

    Ids that only appear as citations of another document (\"content-model spec REQ-10\") are not
    this specification's requirements and are not returned. Falls back to every id mentioned when
    the specification defines none in this form.
    """
    ids = set(DEF_RE.findall(spec_text))
    if not ids:
        return set(ID_RE.findall(spec_text))
    for line in spec_text.splitlines():
        m = DEF_RE.match(line)
        if m and "withdrawn" in line.lower():
            ids.discard(m.group(1))
    return ids

VAGUE_CHECKS = {"works", "it works", "work", "done", "ok", "okay", "passes", "pass", "tested", "test", "tests",
                "manual", "verified", "fine", "good", "tbd", "todo", "n/a", "none"}
DURATION_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:days?|weeks?|hours?|sprints?|months?)\b|\b\d{4}-\d{2}-\d{2}\b", re.I)
ORIGIN_RE = re.compile(r"\(\s*verification plan:\s*((?:AC-\d+)(?:\s*,\s*AC-\d+)*)\s*\)|\(\s*design assumption\s*(\d*)[^)]*\)", re.I)


def section(text, heading_start):
    """Lines of the first `## ` section whose heading starts with heading_start (case-insensitive)."""
    out, inside = [], False
    for ln in text.splitlines():
        if ln.startswith("## "):
            if inside:
                break
            inside = ln[3:].strip().lower().startswith(heading_start.lower())
            continue
        if inside:
            out.append(ln)
    return out


def design_facts(design_text, headings=None):
    """(assumptions, plan): assumptions is one list per bullet under "Assumptions to verify", holding the
    design components (first column of the Components table, its header row left out) that the bullet
    names; plan maps an AC id to the commands in backticks of its verification-plan row. headings maps a
    heading option to the text its section's heading starts with; a missing one takes its default."""
    headings = {**HEADING_DEFAULTS, **(headings or {})}
    components, header_seen = [], False
    for ln in section(design_text, headings["--components-heading"]):
        if not ln.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if not header_seen:
            header_seen = True
            continue
        if cells and cells[0] and not set(cells[0]) <= set("-: "):
            components.append(cells[0])
    assumptions = []
    for ln in section(design_text, headings["--assumptions-heading"]):
        if re.match(r"^\s*[-*]\s+\S", ln) and ln.strip().lstrip("-* ").lower().rstrip(".") != "none":
            assumptions.append([c for c in components if c.lower() in ln.lower()])
    plan = {}
    for ln in section(design_text, headings["--plan-heading"]):
        m = re.match(r"^\|\s*(AC-\d+)\s*\|", ln)
        if m:
            plan[m.group(1)] = re.findall(r"`([^`]+)`", ln.split("|")[-2] if ln.rstrip().endswith("|") else ln)
    return assumptions, plan


def is_spike(task):
    return task["title"].lower().startswith("spike")


def is_removal(task):
    return re.match(r"^(remove|removal|delete)\b", task["title"], re.I) is not None


FIELDS = ("Does:", "Delivers:", "Touches:", "Depends on:", "Check:", "Size:", "Milestone:")


def parse_tasks(text, abbr):
    tasks = {}
    cur = None
    for ln in text.splitlines():
        m = re.match(r"^- (T-" + re.escape(abbr) + r"-\d+):\s*(.*)$", ln)
        if m:
            cur = m.group(1)
            tasks[cur] = {"title": m.group(2).strip(), "lines": []}
            continue
        if cur and ln.startswith("  "):
            tasks[cur]["lines"].append(ln.strip())
        elif ln.strip() == "" or ln.startswith("#") or ln.startswith("- "):
            cur = None
    return tasks


def field(task, name):
    for l in task["lines"]:
        if l.startswith(name):
            return l[len(name):].strip()
    return None


def parse_args(argv):
    """(values, None), or (None, a usage error). values maps each flag given to its value, a switch to True."""
    values, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a in VALUE_FLAGS:
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                return None, f"Error: {a} needs a value. See --help."
            values[a] = argv[i + 1]
            i += 2
        elif a in SWITCHES:
            values[a] = True
            i += 1
        else:
            return None, f"Error: unknown option {a!r}. See --help."
    return values, None


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    values, problem = parse_args(argv)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    backlog, spec, abbr, design = (values.get(f) for f in ("--backlog", "--spec", "--feature", "--design"))
    as_json = "--json" in values
    if not (backlog and spec):
        print("Error: --backlog and --spec are required. See --help.", file=sys.stderr); return 2
    try:
        b, s = open(backlog, encoding="utf-8").read(), open(spec, encoding="utf-8").read()
        d_text = open(design, encoding="utf-8").read() if design else None
    except OSError as e:
        print(f"Error: {e}", file=sys.stderr); return 2
    if not abbr:
        found = sorted(set(re.findall(r"^- T-([A-Za-z0-9]+)-\d+:", b, re.M)))
        if len(found) != 1:
            print(f"Error: --feature is required: the backlog holds tasks of {found or 'no feature'}. See --help.",
                  file=sys.stderr); return 2
        abbr = found[0]
    errors, warnings = [], []
    spec_ids = defined_ids(s)
    tasks = parse_tasks(b, abbr)
    ids_seen = re.findall(r"^- (T-" + re.escape(abbr) + r"-\d+):", b, re.M)
    for dup in sorted({i for i in ids_seen if ids_seen.count(i) > 1}):
        errors.append(f"{dup} is defined more than once")
    headings = {f: values[f] for f in HEADING_DEFAULTS if f in values}
    assumptions, plan = design_facts(d_text, headings) if d_text is not None else ([], {})
    spikes = [tid for tid, t in tasks.items() if is_spike(t)]
    spike_of = {}
    if not tasks:
        errors.append(f"no tasks with prefix T-{abbr}- found")
    milestones = set(re.findall(r"^- (M\d+)\b", b, re.M))
    deps = {}
    delivered = set()
    for tid, t in tasks.items():
        for f in FIELDS:
            if field(t, f) is None:
                errors.append(f"{tid} lacks {f}")
        cited = set(ID_RE.findall(field(t, "Delivers:") or "")) | set(ID_RE.findall(field(t, "Check:") or ""))
        unknown = sorted(c for c in cited if c not in spec_ids)
        if unknown:
            errors.append(f"{tid} cites ids not in the spec: {unknown}")
        delivered |= cited
        if field(t, "Delivers:") is not None and not any(
                c.startswith(("REQ-", "AC-")) for c in ID_RE.findall(field(t, "Delivers:"))):
            errors.append(f"{tid} Delivers cites no REQ or AC id: {field(t, 'Delivers:')[:60]!r}")
        d = field(t, "Depends on:") or ""
        deps[tid] = [] if d.strip().lower() in ("none", "") else re.findall(r"T-" + re.escape(abbr) + r"-\d+", d)
        for dep in deps[tid]:
            if dep not in tasks:
                errors.append(f"{tid} depends on unknown task {dep}")
        size = field(t, "Size:") or ""
        if not re.match(r"^[SML]\s*,\s*because\s+\S", size):
            errors.append(f"{tid} Size must be 'S|M|L, because <reason>': {size[:60]!r}")
        ms = field(t, "Milestone:") or ""
        if ms and milestones and ms.split()[0] not in milestones:
            errors.append(f"{tid} milestone {ms!r} is not in the Milestones list")
        check = (field(t, "Check:") or "").strip()
        if field(t, "Check:") is not None and not check:
            errors.append(f"{tid} has an empty Check")
        bare = ORIGIN_RE.sub("", check).strip().strip(".!`'\" ").lower()
        if check and bare in VAGUE_CHECKS:
            errors.append(f"{tid} Check {check!r} is not a command, a test file or an observable result")
        for name in ("Does:", "Size:"):
            m = DURATION_RE.search(field(t, name) or "")
            if m:
                errors.append(f"{tid} {name} carries a duration or a date: {m.group(0)!r}")
        if is_spike(t) and deps[tid]:
            errors.append(f"{tid} is a spike and must have 'Depends on: none'")
        if is_removal(t) and not deps[tid]:
            errors.append(f"{tid} is a removal and must depend on the tasks that replace what it removes")
        if d_text is not None and check:
            m = ORIGIN_RE.search(check)
            if not m:
                errors.append(f"{tid} Check must end with its origin: '(verification plan: AC-n)' or, on a spike, "
                              f"'(design assumption <n>)'")
            elif m.group(1):
                for ac in re.findall(r"AC-\d+", m.group(1)):
                    if ac not in plan:
                        errors.append(f"{tid} Check cites {ac}, which has no row in the design's verification plan")
                    elif plan[ac] and not any(cmd in check for cmd in plan[ac]):
                        errors.append(f"{tid} Check cites verification plan {ac} but lacks its command `{plan[ac][0]}`")
            elif not is_spike(t):
                errors.append(f"{tid} Check cites '(design assumption)' but the task is not titled 'Spike: ...'")
            elif not m.group(2) or not 1 <= int(m.group(2)) <= len(assumptions):
                errors.append(f"{tid} Check must end with '(design assumption <n>)', n from 1 to {len(assumptions)}: "
                              f"the position of the assumption in the design's list")
            else:
                spike_of.setdefault(int(m.group(2)), tid)
    # cycles + critical path
    order, state, path_len, longest = [], {}, {}, {}
    def visit(n, stack):
        if state.get(n) == 1:
            errors.append(f"dependency cycle through {n}: {' -> '.join(stack + [n])}"); return
        if state.get(n) == 2:
            return
        state[n] = 1
        for d in deps.get(n, []):
            if d in tasks:
                visit(d, stack + [n])
        state[n] = 2
        order.append(n)
    for tid in tasks:
        visit(tid, [])
    for n in order:
        best = max(((path_len[d], d) for d in deps.get(n, []) if d in path_len), default=(0, None))
        path_len[n] = best[0] + 1
        longest[n] = (longest[best[1]] if best[1] else []) + [n]
    critical = max(longest.values(), key=len) if longest else []
    for sp in spikes:
        if not any(sp in deps.get(n, []) for n in tasks):
            errors.append(f"{sp} is a spike no task depends on: make the tasks its assumption affects depend on it")
    for n, named in enumerate(assumptions, 1):
        if n not in spike_of:
            errors.append(f"assumption {n} of the design has no spike: add a task titled 'Spike: ...' whose Check "
                          f"ends with '(design assumption {n})'")
            continue
        sp, reach = spike_of[n], {}
        for t in order:
            reach[t] = t == sp or any(reach.get(d, False) for d in deps.get(t, []))
        for t in sorted(tasks, key=lambda x: int(x.rsplit("-", 1)[1])):
            touched = [c for c in named if c.lower() in (field(tasks[t], "Touches:") or "").lower()]
            if touched and not is_spike(tasks[t]) and not reach.get(t, False):
                errors.append(f"{t} touches {touched[0]!r}, which assumption {n} of the design names, but does not "
                              f"depend on its spike {sp}, directly or through another task")
    must_cover = sorted((i for i in spec_ids if i.startswith(("REQ-", "NFR-", "AC-"))), key=lambda x: (x.split("-")[0], int(x.split("-")[1])))
    uncovered = [i for i in must_cover if i not in delivered]
    if uncovered:
        errors.append(f"spec ids delivered by no task: {uncovered}")
    ok = not errors
    by_kind = {}
    for kind in ("REQ", "NFR", "AC"):
        need = [i for i in must_cover if i.startswith(kind + "-")]
        by_kind[kind] = {"required": len(need), "covered": len([i for i in need if i in delivered])}
    covered = len(must_cover) - len(uncovered)
    summary = (f"lint_backlog: ok: {'true' if ok else 'false'}; errors: {len(errors)}; tasks: {len(tasks)}; "
               f"coverage: {covered}/{len(must_cover)} ("
               + ", ".join(f"{k} {v['covered']}/{v['required']}" for k, v in by_kind.items()) + ")")
    print(json.dumps({"ok": ok, "summary": summary, "feature": abbr, "tasks": len(tasks),
                      "milestones": sorted(milestones), "spikes": spikes, "critical_path": critical,
                      "coverage": {"required": len(must_cover), "covered": covered, **by_kind},
                      "errors": errors, "warnings": warnings}, indent=2 if as_json else None))
    if "--report" in values:
        record = {"script": "lint_backlog.py", "date": datetime.date.today().isoformat(),
                  "arguments": {k: v for k, v in values.items() if k != "--report"}, "ok": ok,
                  "summary": summary, "errors": errors, "warnings": warnings,
                  "counts": {"tasks": len(tasks), "milestones": len(milestones), "spikes": len(spikes),
                             "critical_path": len(critical), "required": len(must_cover), "covered": covered}}
        try:
            with open(values["--report"], "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
                f.write("\n")
        except OSError as e:
            print(f"Error: cannot write the report {values['--report']}: {e}", file=sys.stderr)
            return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
