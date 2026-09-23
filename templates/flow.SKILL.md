---
name: __NAME__
description: >
  __WHAT_IT_ORCHESTRATES__, phase by phase, with a checkpoint after each phase.
  Use this skill when the user wants __OUTCOME__ end to end, or asks to continue
  a previous __OUTCOME__ effort.
license: MIT
metadata:
  area: __AREA__
  kind: flow
  inputs: [docs/workbench/state.md]
  outputs: [docs/workbench/state.md]
  requires: []
  side_effects: []
  version: "0.1"
---

# __TITLE__

## Purpose

One paragraph: the outcome this flow delivers and the phases it walks through.

## Phases

| # | Phase | Skill | Optional | Produces | Checkpoint question |
|---|-------|-------|----------|----------|---------------------|
| 1 | <name> | <area>-<skill> | no | docs/<area>/<file>.md | "<one-line question the user answers to approve>" |
| 2 | <name> | <area>-<skill> | yes, when <condition> | ... | ... |

## Procedure

- [ ] Step 1: Read `docs/workbench/state.md`. If it does not exist, create it from `contracts/state.md`.
- [ ] Step 2: Find the first phase whose artifacts are not `approved` or `skipped`. Tell the user where you are resuming from.
- [ ] Step 3: For an optional phase, ask its condition question once. Record `skipped` if the answer is no.
- [ ] Step 4: Run the phase's skill. Do not do the phase's work yourself.
- [ ] Step 5: Checkpoint. Show the artifact summary and the checkpoint question. Wait for the answer.
      - approved: set `approved` in state, continue.
      - changes requested: rerun the skill with the feedback. Do not advance.
- [ ] Step 6: Update `docs/workbench/state.md` (phase, artifact rows, decisions, open questions).
- [ ] Step 7: Repeat from step 3 for the next phase. At the last phase, close with the summary template.

## Checkpoint template

```markdown
## Checkpoint: <phase name>

Produced: `docs/<area>/<file>.md` (<n> sections)
Key decisions in this phase:
- ...
Open questions:
- ...

<checkpoint question>
```

## Gotchas

- Never advance past a checkpoint without an explicit approval.
- Never run two phases in one turn unless the user asked for it.
