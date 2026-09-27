---
name: eng-refactor
description: >
  Change the shape of code without changing what it does. Use this skill whenever a request
  says refactor, "tidy this up", "clean up", "simplify" or "remove the duplication", including a
  request that also asks for a fix on the way ("refactor due.js and fix the bug"): the skill
  keeps the fix out of the refactor. It names the smell with the evidence that removing it
  changes nothing, gets the user's agreement on a target it chose itself, records the
  project's full check and measurements before, makes one kind of change at a time, and shows
  the same check green and the measurements after. Also use it to propose a target when asked
  what is worth refactoring.
license: MIT
metadata:
  area: engineering
  kind: capability
  inputs: [docs/engineering/architecture.md, AGENTS.md]
  outputs: [docs/engineering/plans/<task>.md]
  requires: []
  side_effects: []
  version: "0.4"
---

# Refactor

## Purpose

Make code cheaper to keep without anyone noticing a difference in behaviour. The proof is not a reading of the diff: it is the project's full check green before and after, plus the measurements the project cares about (size, speed, count of anything its rules limit) moving the right way. The "Refactor" section of the plan records the smell, why the change preserves behaviour, and the before-and-after table.

## Stop rules

Check these before creating or editing any file, and again before replying. They override the procedure.

1. **A named target is an agreed target.** When the user names the smell and the files ("remove the duplicated validation and the dead code in due.js"), proceed through every step: run the checks before, change, run them after. Ask for agreement only when you chose the target yourself.
2. **No behaviour change rides along.** If the request also asks for a fix or a feature, do the refactor only, leave the behaviour exactly as it was (the bug included), and say in the reply that the fix is a separate change (`eng-root-cause`, then `eng-unit-tests`).
3. **Several kinds of change, one at a time.** Removing dead code and removing duplication are two kinds: do one, run the full check, then the other, and give each its own row in the table.

## When not to use

- Behaviour must change (a bug, a feature): `eng-root-cause` or `eng-implement`; a refactor that fixes something on the way hides the fix from the review.
- The code has no check that exercises it: write the missing tests first (`eng-unit-tests` against today's behaviour), or the refactor is a rewrite on trust.
- A redesign across modules or an API change: `eng-architecture`; the user decides it.

## Inputs

| Artifact | Required | If missing |
|----------|----------|------------|
| The target: files and the smell, agreed with the user | yes | Propose one: the smell, the files, the evidence it changes nothing, the expected gain, and ask |
| The project's full check and measurement commands (`AGENTS.md`, the manifest's scripts, CI) | yes | Read them from the manifest and CI; say which you will use |

## Procedure

Progress:
- [ ] Step 1: Name the smell and the evidence that removing it keeps behaviour: dead code that cannot change an outcome (say why it cannot, from the language's semantics), duplication whose copies are identical in effect, a name that lies. Quote the lines. When you were asked to find a target, stop here and propose it with the expected gain; do not change code until the user agrees.
- [ ] Step 2: Run the project's full check (build, every suite in every runtime, build-time checks) and every measurement its rules name (a size budget, a benchmark), and record the results. A red check before you start is not yours to fix: stop and report it.
- [ ] Step 3: Make one kind of change across the target, nothing else: no rename while removing dead code, no formatting of untouched lines beyond what the formatter does to the lines you changed. Keep every guard that does change behaviour (a server-side guard, an error path), and say which ones you kept.
- [ ] Step 4: Run the same check and measurements. Any difference in a test result is a behaviour change: revert and re-examine the smell. Any measurement that moves the wrong way is reported, not hidden.
- [ ] Step 5: Confine the diff: `git diff --stat` lists only the target files; the formatter's changes are named.
- [ ] Step 6: Write the "Refactor" section of the plan from the template, with anything found while reading listed as separate changes, and self-check against "Quality criteria".

## Output template

Write to `docs/engineering/plans/<task>.md`:

```markdown
# Plan: <task>

- Task: <the target as agreed, and who agreed>
- Date: <YYYY-MM-DD>

## Refactor

- Owner: eng-refactor
- Smell: <quoted lines and why removing them cannot change behaviour>
- Behaviour kept: <guards and paths deliberately left in place>
- Files: <paths> (<git diff --stat summary>)

| Check | Before | After |
|-------|--------|-------|
| `<full check command>` | <result> | <result> |
| `<measurement>` | <numbers> | <numbers> |

- Not done here (found while reading, each a separate change): <list or "none">
```

## Quality criteria

Approve only if all of the following hold:

- The smell is quoted, and the reason it cannot change behaviour is stated from the language's or platform's semantics, not from "it looks unused".
- The full check ran before and after with identical results, and the measurements the project names are in the table.
- The diff contains one kind of change, in the agreed files only.
- A target proposed by the skill was agreed by the user before any code changed.

## Gotchas

- "Unused" is a claim about semantics: the first real run removed an `installed` flag from five modules after writing down why it could never be `true` on entry (an ES module evaluates once per URL, and a second copy from another URL has its own flag), and kept the `typeof document` guard beside it, which does matter on the server.
- A small refactor can pay for a feature: the same run saved 74 B across five fallbacks, 12 of them in the one every browser downloads, which offset part of a fix made the same day.
- The formatter may rewrap a comment near your change; name it in the files line so the reviewer does not look for a hidden edit.
