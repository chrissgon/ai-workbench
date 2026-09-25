#!/usr/bin/env python3
"""Lint a feature section of a backlog against its specification.

Usage: python3 lint_backlog.py --backlog <backlog.md> --spec <spec.md> --feature <abbr> [--json]

Checks, for tasks whose id starts with T-<abbr>-:
  - task ids are unique and every task has Does, Delivers, Touches, Depends on, Check, Size and Milestone lines
  - every REQ/NFR/EDGE/AC id cited in Delivers or Check exists in the specification
  - every dependency names an existing task of the same feature; no dependency cycles
  - every REQ, NFR and AC of the specification is delivered by at least one task (Delivers or Check)
  - Size is S, M or L followed by ", because"
  - every task's milestone appears in the Milestones list
Prints JSON including the critical path (longest dependency chain by task count).

Exit codes: 0 ok, 1 problems, 2 usage error.
"""
import json
import re
import sys

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


def main(argv):
    if not argv or "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0 if argv else 2
    backlog = spec = abbr = None
    as_json = "--json" in argv
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--backlog": backlog = argv[i + 1]; i += 2
        elif a == "--spec": spec = argv[i + 1]; i += 2
        elif a == "--feature": abbr = argv[i + 1]; i += 2
        elif a == "--json": i += 1
        else:
            print(f"Error: unknown option {a!r}. See --help.", file=sys.stderr); return 2
    if not (backlog and spec and abbr):
        print("Error: --backlog, --spec and --feature are required. See --help.", file=sys.stderr); return 2
    try:
        b, s = open(backlog, encoding="utf-8").read(), open(spec, encoding="utf-8").read()
    except OSError as e:
        print(f"Error: {e}", file=sys.stderr); return 2
    errors, warnings = [], []
    spec_ids = defined_ids(s)
    tasks = parse_tasks(b, abbr)
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
        if not (field(t, "Check:") or "").strip():
            errors.append(f"{tid} has an empty Check")
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
    must_cover = sorted((i for i in spec_ids if i.startswith(("REQ-", "NFR-", "AC-"))), key=lambda x: (x.split("-")[0], int(x.split("-")[1])))
    uncovered = [i for i in must_cover if i not in delivered]
    if uncovered:
        errors.append(f"spec ids delivered by no task: {uncovered}")
    ok = not errors
    print(json.dumps({"ok": ok, "tasks": len(tasks), "milestones": sorted(milestones), "critical_path": critical,
                      "coverage": {"required": len(must_cover), "covered": len(must_cover) - len(uncovered)},
                      "errors": errors, "warnings": warnings}, indent=2 if as_json else None))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
