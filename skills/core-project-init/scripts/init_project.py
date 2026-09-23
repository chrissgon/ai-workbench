#!/usr/bin/env python3
"""Initialize or update a project for the workbench.

Usage:
  python3 init_project.py --root <dir> --detect
  python3 init_project.py --root <dir> --apply --name <name> --autonomy <mode> [--register <path>=<slot>]... [--dry-run]
  python3 init_project.py --root <dir> [--set-autonomy <mode>] [--register <path>=<slot>]... [--dry-run]

--detect   prints JSON: is_project_root, name_guess, state_exists, agents_md (exists, has_section),
           root_docs (specification-like *.md at the root), excluded, docs_dir (count, names).
--apply    creates docs/workbench/state.md and the workbench section in AGENTS.md. Refuses if state exists.
Update     (no --apply) changes the autonomy mode and/or adds registrations to an existing state.
--register <path>=<slot>  registers an existing document as the artifact <slot> (docs/<area>/...), in place.
--autonomy / --set-autonomy  one of: every-phase, milestones, end.
--dry-run  prints the plan, writes nothing.

Never moves, renames or edits registered documents. Never edits AGENTS.md outside the markers.
Exit codes: 0 ok, 1 refused (state exists with --apply, missing path, bad slot), 2 usage error.
"""
import datetime as dt
import json
import os
import re
import sys

MODES = ("every-phase", "milestones", "end")
START, END = "<!-- workbench:start -->", "<!-- workbench:end -->"
EXCLUDED_STEMS = {"README", "LICENSE", "CHANGELOG", "CONTRIBUTING", "CODE_OF_CONDUCT", "SECURITY", "AGENTS"}
MANIFESTS = ("package.json", "pyproject.toml", "go.mod", "Cargo.toml", "composer.json", "pom.xml", "build.gradle", "Gemfile")
HERE = os.path.dirname(os.path.abspath(__file__))
SECTION_TEMPLATE = os.path.join(HERE, "..", "assets", "agents-md-section.md")

STATE_TEMPLATE = """# Workbench state

- Project: {name}
- Current flow: none
- Current phase: none
- Updated: {date}

## Autonomy

- Checkpoints: {autonomy}

## Artifacts

| Artifact | Owner skill | Status | Updated |
|----------|-------------|--------|---------|
{rows}
## Decisions

- {date}: Project initialized for the workbench; autonomy {autonomy}. (core-project-init, confirmed by user)

## Open questions

## Approvals

| Scope | What | Approved | Expires | Status |
|-------|------|----------|---------|--------|
"""


def usage_error(msg):
    print(f"Error: {msg} See --help.", file=sys.stderr)
    return 2


def refuse(msg):
    print(f"Error: {msg}", file=sys.stderr)
    return 1


def name_guess(root):
    pj = os.path.join(root, "package.json")
    if os.path.isfile(pj):
        try:
            with open(pj, encoding="utf-8") as f:
                n = json.load(f).get("name")
            if n:
                return n.split("/")[-1]
        except (OSError, ValueError):
            pass
    py = os.path.join(root, "pyproject.toml")
    if os.path.isfile(py):
        with open(py, encoding="utf-8") as f:
            m = re.search(r'^name\s*=\s*"([^"]+)"', f.read(), re.M)
        if m:
            return m.group(1)
    return os.path.basename(os.path.abspath(root))


def detect(root):
    is_root = os.path.isdir(os.path.join(root, ".git")) or any(os.path.isfile(os.path.join(root, m)) for m in MANIFESTS)
    root_docs, excluded = [], []
    for fn in sorted(os.listdir(root)):
        if not fn.lower().endswith(".md") or not os.path.isfile(os.path.join(root, fn)):
            continue
        stem = fn[:-3]
        if stem.upper() in EXCLUDED_STEMS or stem.upper().startswith("README"):
            excluded.append(fn)
        elif stem == stem.upper():
            root_docs.append(fn)
    docs_dir = os.path.join(root, "docs")
    docs_files = []
    if os.path.isdir(docs_dir):
        for dp, _, fns in os.walk(docs_dir):
            for fn in fns:
                if fn.endswith(".md"):
                    docs_files.append(os.path.relpath(os.path.join(dp, fn), root))
    agents = os.path.join(root, "AGENTS.md")
    has_section = False
    if os.path.isfile(agents):
        with open(agents, encoding="utf-8") as f:
            has_section = START in f.read()
    return {
        "root": os.path.abspath(root),
        "is_project_root": is_root,
        "name_guess": name_guess(root),
        "state_exists": os.path.isfile(os.path.join(root, "docs", "workbench", "state.md")),
        "agents_md": {"exists": os.path.isfile(agents), "has_section": has_section},
        "root_docs": root_docs,
        "excluded": excluded,
        "docs_dir": {"count": len(docs_files), "files": sorted(docs_files)[:50]},
    }


def parse_registrations(items, root):
    regs = []
    for item in items:
        if "=" not in item:
            raise ValueError(f"--register expects <path>=<slot>, got {item!r}")
        path, slot = item.split("=", 1)
        path, slot = path.strip(), slot.strip()
        if not os.path.exists(os.path.join(root, path)):
            raise FileNotFoundError(f"registered path does not exist: {path}")
        if not slot.startswith("docs/"):
            raise ValueError(f"slot must start with docs/, got {slot!r}")
        regs.append((path, slot))
    return regs


def row(slot, path, date):
    return f"| {slot} (at {path}) | existing | approved | {date} |"


def section_text(autonomy):
    with open(SECTION_TEMPLATE, encoding="utf-8") as f:
        return f.read().replace("{autonomy}", autonomy).rstrip("\n") + "\n"


def upsert_section(content, section):
    if START in content and END in content:
        pre = content[: content.index(START)]
        post = content[content.index(END) + len(END):]
        return pre + section.rstrip("\n") + post, "section updated"
    sep = "" if content.endswith("\n\n") else ("\n" if content.endswith("\n") else "\n\n")
    return content + sep + section, "section added"


def write(path, content, dry):
    if dry:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def apply(root, name, autonomy, regs, dry):
    date = dt.date.today().isoformat()
    state_path = os.path.join(root, "docs", "workbench", "state.md")
    if os.path.isfile(state_path):
        return refuse("docs/workbench/state.md already exists; use --set-autonomy or --register to update.")
    rows = "".join(row(s, p, date) + "\n" for p, s in regs)
    write(state_path, STATE_TEMPLATE.format(name=name, date=date, autonomy=autonomy, rows=rows), dry)
    agents = os.path.join(root, "AGENTS.md")
    section = section_text(autonomy)
    if os.path.isfile(agents):
        with open(agents, encoding="utf-8") as f:
            content, action = upsert_section(f.read(), section)
    else:
        content, action = f"# {name}\n\n" + section, "created"
    write(agents, content, dry)
    print(json.dumps({
        "dry_run": dry, "action": "apply", "name": name, "autonomy": autonomy,
        "state": "created", "agents_md": action,
        "registered": [{"slot": s, "at": p} for p, s in regs],
    }))
    return 0


def update(root, set_autonomy, regs, dry):
    date = dt.date.today().isoformat()
    state_path = os.path.join(root, "docs", "workbench", "state.md")
    if not os.path.isfile(state_path):
        return refuse("no docs/workbench/state.md to update; run with --apply first.")
    with open(state_path, encoding="utf-8") as f:
        state = f.read()
    changes = []
    if set_autonomy:
        new = re.sub(r"^- Checkpoints: .*$", f"- Checkpoints: {set_autonomy}", state, count=1, flags=re.M)
        if new != state:
            state, changes = new, changes + [f"autonomy -> {set_autonomy}"]
        agents = os.path.join(root, "AGENTS.md")
        if os.path.isfile(agents):
            with open(agents, encoding="utf-8") as f:
                content, _ = upsert_section(f.read(), section_text(set_autonomy))
            write(agents, content, dry)
            changes.append("AGENTS.md section refreshed")
    added = []
    for p, s in regs:
        if f"(at {p})" in state:
            continue
        marker = "## Decisions"
        state = state.replace(marker, row(s, p, date) + "\n" + marker, 1) if marker in state else state + row(s, p, date) + "\n"
        added.append({"slot": s, "at": p})
    if changes or added:
        state = re.sub(r"^- Updated: .*$", f"- Updated: {date}", state, count=1, flags=re.M)
        write(state_path, state, dry)
    print(json.dumps({"dry_run": dry, "action": "update", "changes": changes, "registered": added,
                      "unchanged": not (changes or added)}))
    return 0


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        print(__doc__)
        return 0 if argv else 2
    root, mode, name, autonomy, set_autonomy, regs, dry = ".", None, None, None, None, [], False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--root", "--name", "--autonomy", "--set-autonomy", "--register"):
            if i + 1 >= len(argv):
                return usage_error(f"{a} needs a value.")
            v = argv[i + 1]
            if a == "--root":
                root = v
            elif a == "--name":
                name = v
            elif a == "--autonomy":
                autonomy = v
            elif a == "--set-autonomy":
                set_autonomy = v
            else:
                regs.append(v)
            i += 2
        elif a == "--detect":
            mode = "detect"
            i += 1
        elif a == "--apply":
            mode = "apply"
            i += 1
        elif a == "--dry-run":
            dry = True
            i += 1
        else:
            return usage_error(f"unknown option {a!r}.")
    if not os.path.isdir(root):
        return usage_error(f"--root {root!r} is not a directory.")
    if mode == "detect":
        print(json.dumps(detect(root), indent=2))
        return 0
    try:
        parsed = parse_registrations(regs, root)
    except (ValueError, FileNotFoundError) as e:
        return refuse(str(e))
    if mode == "apply":
        if not name or not autonomy:
            return usage_error("--apply requires --name and --autonomy.")
        if autonomy not in MODES:
            return usage_error(f"--autonomy must be one of {MODES}.")
        return apply(root, name, autonomy, parsed, dry)
    if set_autonomy and set_autonomy not in MODES:
        return usage_error(f"--set-autonomy must be one of {MODES}.")
    if not set_autonomy and not parsed:
        return usage_error("nothing to do: pass --detect, --apply, --set-autonomy or --register.")
    return update(root, set_autonomy, parsed, dry)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
