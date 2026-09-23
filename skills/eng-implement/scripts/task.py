#!/usr/bin/env python3
"""Read a task from the Markdown backlog, or set its status.

Usage:
  python3 task.py --backlog <backlog.md> --id T-<abbr>-<n>
  python3 task.py --backlog <backlog.md> --id T-<abbr>-<n> --status <todo|in-progress|done|blocked> [--note "<text>"]

Prints JSON: the task's fields, its dependencies with their status, and whether they are all done.
Status is stored as a "  Status: <value> (<date>) <note>" line inside the task; absent means todo.
Exit codes: 0 ok, 1 task not found, 2 usage error.
"""
import datetime as dt
import json
import re
import sys

FIELDS = ("Does", "Delivers", "Touches", "Depends on", "Check", "Size", "Milestone", "Status")


def load(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def find_tasks(lines):
    tasks, cur = {}, None
    for i, ln in enumerate(lines):
        m = re.match(r"^- (T-[a-z0-9]+-\d+):\s*(.*)$", ln)
        if m:
            cur = m.group(1)
            tasks[cur] = {"title": m.group(2).strip(), "start": i, "end": i, "fields": {}}
            continue
        if cur and ln.startswith("  "):
            tasks[cur]["end"] = i
            for f in FIELDS:
                if ln.strip().startswith(f + ":"):
                    tasks[cur]["fields"][f] = ln.strip()[len(f) + 1:].strip()
        elif ln.strip() == "" or ln.startswith("#") or ln.startswith("- "):
            cur = None
    return tasks


def status_of(t):
    s = t["fields"].get("Status", "")
    return s.split()[0] if s else "todo"


def main(argv):
    if not argv or "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0 if argv else 2
    backlog = tid = status = note = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--backlog": backlog = argv[i + 1]; i += 2
        elif a == "--id": tid = argv[i + 1]; i += 2
        elif a == "--status": status = argv[i + 1]; i += 2
        elif a == "--note": note = argv[i + 1]; i += 2
        else:
            print(f"Error: unknown option {a!r}. See --help.", file=sys.stderr); return 2
    if not backlog or not tid:
        print("Error: --backlog and --id are required. See --help.", file=sys.stderr); return 2
    if status and status not in ("todo", "in-progress", "done", "blocked"):
        print("Error: --status must be todo, in-progress, done or blocked.", file=sys.stderr); return 2
    lines = load(backlog)
    tasks = find_tasks(lines)
    if tid not in tasks:
        print(json.dumps({"error": f"task {tid} not found", "available": sorted(tasks)[:20]}))
        return 1
    if status:
        t = tasks[tid]
        line = f"  Status: {status} ({dt.date.today().isoformat()})" + (f" {note}" if note else "")
        idx = next((k for k in range(t["start"] + 1, t["end"] + 1) if lines[k].strip().startswith("Status:")), None)
        if idx is not None:
            lines[idx] = line
        else:
            lines.insert(t["end"] + 1, line)
        with open(backlog, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        lines = load(backlog)
        tasks = find_tasks(lines)
    t = tasks[tid]
    deps = [] if t["fields"].get("Depends on", "none").strip().lower() in ("none", "") else re.findall(r"T-[a-z0-9]+-\d+", t["fields"].get("Depends on", ""))
    dep_status = {d: (status_of(tasks[d]) if d in tasks else "missing") for d in deps}
    print(json.dumps({"id": tid, "title": t["title"], "fields": {k: v for k, v in t["fields"].items()},
                      "status": status_of(t), "dependencies": dep_status,
                      "dependencies_done": all(s == "done" for s in dep_status.values())}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
