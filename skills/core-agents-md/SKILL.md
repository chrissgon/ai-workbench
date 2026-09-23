---
name: core-agents-md
description: >
  Create, update or audit a project's AGENTS.md so that any AI tool works from the same,
  verified conventions: what the project is, where its architecture is documented, the exact
  build, test, lint and release commands, code style, testing, security and commit rules, and
  the working rules the maintainer wants followed. Use this skill when the user asks for an
  AGENTS.md, when a project was initialized for the workbench but has no conventions yet, when
  a tool-specific instruction file should become tool-neutral, or after build or test tooling
  changed. Every command is checked against the repository; nothing is written from memory.
license: MIT
metadata:
  area: core
  kind: capability
  inputs: [AGENTS.md, docs/workbench/state.md]
  outputs: [AGENTS.md]
  requires: []
  side_effects: []
  version: "0.1"
---

# Project instructions (AGENTS.md)

## Purpose

`AGENTS.md` is read at the start of every session by every tool, so it must be short, true and current. This skill owns everything in it except the workbench section between `<!-- workbench:start -->` and `<!-- workbench:end -->`, which belongs to `core-project-init` and is preserved byte for byte.

## When not to use

- Initializing the state file or the workbench section: `core-project-init`.
- Writing architecture documentation: `eng-codebase-map` or `eng-architecture`; `AGENTS.md` links to it, never duplicates it.
- Documenting a feature: `eng-docs`.

## Inputs

| Artifact | Required | If missing |
|----------|----------|------------|
| AGENTS.md | no | Create it from the template. |
| docs/workbench/state.md | no | Without registered artifacts, link root documents found by detection instead. |
| Tool-specific instruction files at the root | no | Nothing to carry over; say so in the report. |

## Procedure

Progress:
- [ ] Step 1: Detect. Run `python3 scripts/audit_agents_md.py --root . --detect`. It prints JSON: manifests and their scripts, lint, format and type-check configs, test frameworks and folders, CI and deploy files, root documents, instruction-like files, and the sections of the current `AGENTS.md` with whether it has the workbench section.
- [ ] Step 2: Read the current `AGENTS.md` in full and every instruction-like file in full. List each convention they state (commands, rules, review process, communication preferences) with the file it came from. These are the maintainer's words; they are candidates to carry over, never to reinterpret.
- [ ] Step 3: Build the fact list, one line per fact with its source: commands from package scripts or Makefile targets; style from lint and format configs; tests from test configs and folders; architecture from the registered architecture artifact in the state file or a root document; CI from workflow files; commit rules from commitlint or hooks. Anything you cannot ground in a file becomes a question, not a sentence.
- [ ] Step 4: Ask the user once, at most three questions with recommended answers: (a) which of the carried-over conventions to keep, shown as a list (recommend all, verbatim in meaning); (b) what to do with the tool-specific files afterwards (recommend keeping them and adding one line pointing to `AGENTS.md`; never delete or rename them); (c) anything the repository cannot show that they want written (team rules, review process, who to ask). Wait for the answers.
- [ ] Step 5: Write. New file: fill [assets/agents-md-template.md](assets/agents-md-template.md), dropping sections with nothing grounded. Existing file: update facts in place, keep every sentence the maintainer wrote unless it is now false (then replace it and list the change in the report), keep the workbench section untouched, keep section order. Link the architecture artifact instead of pasting it. Target under 200 lines.
- [ ] Step 6: Audit. Run `python3 scripts/audit_agents_md.py --root . --audit AGENTS.md`. Every command in backticks must resolve to a script, a Makefile target or a binary; every path in backticks must exist. Fix and re-run until `ok` is true.
- [ ] Step 7: Report: created or updated, sections written, conventions carried over and from where, facts changed because they were false, questions still open, and the exact byte-identity check of the workbench section (the audit prints it).
- [ ] Step 8: Self-check against "Quality criteria".

## Output template

The file layout is in [assets/agents-md-template.md](assets/agents-md-template.md). The report:

```markdown
## AGENTS.md <created | updated>: <project>

- Sections: <list>
- Commands verified: <n> (audit ok)
- Carried over from <file>: <n> conventions (<kept | edited with approval>)
- Changed because false: <list or "none">
- Workbench section: unchanged
- Still open: <questions or "none">
```

## Quality criteria

Approve only if all of the following hold:

- The audit reports `ok: true`: every command resolves, every referenced path exists.
- The workbench section is byte-identical to before (audit prints `workbench_section: unchanged`).
- No sentence written by the maintainer was removed; replaced sentences are listed in the report with the reason.
- Conventions from tool-specific files appear only after the user confirmed them, and those files still exist.
- Architecture is linked, not duplicated; the file is under 200 lines.
- Nothing in the file lacks a source in the repository or in the user's answers.

## Gotchas

- The real conventions often live in a tool-specific file ("reply in Portuguese", "one phase at a time, stop and report"). They are the maintainer's rules, not the tool's: carry them over with confirmation, in tool-neutral words.
- Never delete, rename or archive an existing instruction file. Other people or tools may read it. Add a pointer line at its top only if the user agrees.
- Commands drift. `bun run test` documented last year may be `bun test` today; the audit exists for this, run it every time tooling changes.
- `AGENTS.md` costs context in every session. A 600-line file is read once and skimmed forever. Link the depth.
- "Overview" comes from the README and the manifest description, not from what the code seems to do.
- A linter's rules are enforced by the linter; document the command that runs it, not the rules it checks.
- Empty sections are worse than missing sections: they teach the model that the file is a template.
