---
name: __NAME__
description: >
  __WHAT_IT_DOES__. Use this skill when __WHEN_TO_USE__, even if the user
  does not say "__KEYWORD__" explicitly. Also use it when __EDGE_CASE__.
license: MIT
metadata:
  area: __AREA__
  kind: capability
  inputs: []
  outputs: []
  requires: []
  side_effects: []
  version: "0.1"
---

# __TITLE__

## Purpose

One paragraph: what this skill produces and why it matters to the phase it belongs to.

## When not to use

- Bullet the near-misses that belong to another skill, naming that skill.

## Inputs

| Artifact | Required | If missing |
|----------|----------|------------|
| docs/<area>/<file>.md | no | Ask the user for <the two facts you need>, or offer to run <skill> |

## Procedure

Progress:
- [ ] Step 1: <verb> <object>. Open <file>, look for <thing>, write <result> to <place>.
- [ ] Step 2: ...
- [ ] Step 3: Stop and ask the user if <condition>, with a recommended answer. Do not guess; do not pick the most likely option; do not proceed until answered.
- [ ] Step 4: Produce the output from the template below.
- [ ] Step 5: Self-check against "Quality criteria". Fix, then re-check.

When you reach step N, read [references/<file>.md](references/<file>.md).

## Output template

Write to `docs/<area>/<file>.md`:

```markdown
# <Title>

- Owner: __NAME__
- Status: draft
- Date: <YYYY-MM-DD>

## <Section>
<one line of guidance>
```

## Quality criteria

Approve the output only if all of the following hold:

- <criterion that can be checked by reading the output>
- <criterion>

## Gotchas

- <non-obvious fact that defies assumptions; add one after every mistake you have to fix>

## Confirmation gate

Delete this section unless `side_effects` is non-empty. Otherwise:

1. Read the "Approvals" table in `docs/workbench/state.md`. If an approval covers this exact payload (or a plan or standing approval that includes it), skip to step 4.
2. Show the exact payload: <list the fields: text, media, recipients, time, target>.
3. Ask once: "Proceed? (yes/no)". Stop on anything other than an explicit yes.
4. Execute (now, or at the scheduled time after verifying the payload still matches). Record or update the approval row with status `executed` and a timestamp.
