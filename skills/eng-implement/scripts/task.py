#!/usr/bin/env python3
"""Read a task from the Markdown backlog, or set its status.

Usage:
  python3 task.py --backlog <backlog.md> --id T-<abbr>-<n>
  python3 task.py --backlog <backlog.md> --id T-<abbr>-<n> --status <todo|in-progress|done|blocked> [--note "<text>"]

Reading a task prints JSON on stdout: its title, its fields, its status, its dependencies with their
status, and whether they are all done.

Setting a status writes one "  Status: <value> (<date>) <note>" line inside the task (absent means todo)
and prints one line of JSON on stdout, to be quoted as it is:
  {"id": "T-cm-2", "status": "in-progress", "previous": "todo", "worktree_changes": []}
worktree_changes is what `git status --short`, run in the current folder, printed just before the status
line was written: [] when no file was changed yet, null outside a git repository.

A task id is T-<abbr>-<n>, the abbreviation in lowercase letters and digits (T-cm-2).
Exit codes: 0 ok; 1 task not found (a JSON object with "error" and "available" on stdout);
2 usage error or unreadable backlog (a message on stderr).
"""
import datetime as dt
import json
import re
import subprocess
import sys

FIELDS = ("Does", "Delivers", "Touches", "Depends on", "Check", "Size", "Milestone", "Status")
VALUE_FLAGS = ("--backlog", "--id", "--status", "--note")
STATUSES = ("todo", "in-progress", "done", "blocked")


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


def worktree_changes():
    """The lines `git status --short` prints in the current folder, or None outside a git repository."""
    try:
        r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def usage_error(message):
    print(f"Error: {message} See --help.", file=sys.stderr)
    return 2


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    values = {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a not in VALUE_FLAGS:
            return usage_error(f"unknown option {a!r}.")
        if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
            return usage_error(f"{a} needs a value.")
        values[a] = argv[i + 1]
        i += 2
    backlog, tid = values.get("--backlog"), values.get("--id")
    status, note = values.get("--status"), values.get("--note")
    if not backlog or not tid:
        return usage_error("--backlog and --id are required.")
    if status and status not in STATUSES:
        return usage_error("--status must be todo, in-progress, done or blocked.")
    if note is not None and not status:
        return usage_error("--note goes with --status.")
    try:
        lines = load(backlog)
    except OSError as e:
        print(f"Error: backlog not found or unreadable: {backlog} ({e.strerror}).", file=sys.stderr)
        return 2
    tasks = find_tasks(lines)
    if tid not in tasks:
        print(json.dumps({"error": f"task {tid} not found", "available": sorted(tasks)[:20]}))
        return 1
    t = tasks[tid]
    if status:
        previous = status_of(t)
        changes = worktree_changes()
        line = f"  Status: {status} ({dt.date.today().isoformat()})" + (f" {note}" if note else "")
        idx = next((k for k in range(t["start"] + 1, t["end"] + 1) if lines[k].strip().startswith("Status:")), None)
        if idx is not None:
            lines[idx] = line
        else:
            lines.insert(t["end"] + 1, line)
        with open(backlog, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(json.dumps({"id": tid, "status": status, "previous": previous, "worktree_changes": changes}))
        return 0
    deps = [] if t["fields"].get("Depends on", "none").strip().lower() in ("none", "") else re.findall(r"T-[a-z0-9]+-\d+", t["fields"].get("Depends on", ""))
    dep_status = {d: (status_of(tasks[d]) if d in tasks else "missing") for d in deps}
    print(json.dumps({"id": tid, "title": t["title"], "fields": {k: v for k, v in t["fields"].items()},
                      "status": status_of(t), "dependencies": dep_status,
                      "dependencies_done": all(s == "done" for s in dep_status.values())}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
