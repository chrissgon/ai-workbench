---
name: eng-unit-tests
description: >
  Write the tests a change must satisfy before the change exists: one test per case of the
  plan or the specification, in the project's own runner and conventions, run once to prove
  that the new behaviour fails for the right reason and the behaviour to preserve passes. Use
  this skill after a root cause is confirmed or a task's acceptance criteria are known, before
  eng-implement, even if the user only says "escreve os testes primeiro", "TDD" or "add a
  regression test". Also use it when a bug fix has no test that fails without it. Also use it
  when the request names a test framework ("write Jest tests"), to check it against the
  project's runner first.
license: MIT
metadata:
  area: engineering
  kind: capability
  inputs: [docs/engineering/plans/<task>.md, docs/product/specs/<feature>.md, docs/product/backlog.md, AGENTS.md]
  outputs: [docs/engineering/plans/<task>.md]
  requires: []
  side_effects: []
  version: "0.6"
---

# Unit tests

## Purpose

Turn a plan's cases into tests that fail today and will pass when the change is right, so `eng-implement` has a check that proves the work instead of an opinion about it. The tests live in the project's runner, next to its existing tests; the "Failing tests" section of the plan lists them with what each one showed before the change. A test that cannot fail, or that fails for a different reason than the one it names, is worse than none: it turns a broken change green.

## When not to use

- The cause of a bug is not confirmed: `eng-root-cause` first; a test written against a guessed cause pins the guess.
- Tests that need the whole system assembled (a browser flow across pages, a service with its database, markup inserted after load): `eng-integration-tests`, after the change exists.
- The change is behaviour-preserving (a refactor): the existing tests are the check; `eng-refactor`.

## Inputs

| Artifact | Required | If missing |
|----------|----------|------------|
| The cases: a plan's "Root cause" (the bug case and "What a fix must preserve"), or a spec's REQ, EDGE and AC, or a backlog task's Check | yes | Ask which behaviour must change and which must stay; do not derive cases from the code under test |
| The project's test runner and conventions (`AGENTS.md`, the test configuration, two existing tests) | yes | Read them from the repository; never add a runner, a framework or a dependency without asking |
| `docs/engineering/plans/<task>.md` | no | Create it with the header of `eng-root-cause`'s template |

## Procedure

Progress:
- [ ] Step 1: Read the runner's configuration and two existing tests. If the user asks for another runner or framework than the project's, say which one the project uses and ask before adding anything, recommending the project's; write nothing until answered. Write down: the command, where tests and fixtures live, the runtimes the runner covers (browser projects, Node versions), and the assertion style. The unit is the smallest thing this runner isolates: a function for a library of functions, one rule on one element in a fixture page for a stylesheet, one handler with its request for a server. Use that; do not bring another runner's idea of a unit.
- [ ] Step 2: List the cases, each with its source line (`Root cause › Reproduction`, `What a fix must preserve`, `AC-3`, `EDGE-2`) and its expected state today: `fails now` (the behaviour the change adds or repairs) or `passes now` (a behaviour the change must keep). Every bug case and every preserved behaviour gets a case; add the boundary inputs the source implies (the empty group, the value without a name, the zero).
- [ ] Step 3: Stop and ask when a case asserts a behaviour no source states (what a control shows in a state the plan never mentions, an error message nobody specified), and when the request uses a word that can be read two ways (a "day" that is a calendar day or 24 hours, "empty" that is `""` or missing); your own reading of it is a decision, not a fact. Give a recommended answer grounded in the project's documentation. Write the rest; mark the case `pending decision` until answered.
- [ ] Step 4: Write the tests in the project's layout: a fixture beside the existing fixtures, a spec beside the existing specs, names that say the behaviour ("a group with nothing checked shows empty rings"), a comment pointing to the plan. Assert exact observable values (the computed colour, the returned string, the status code), never "does not throw" or "is defined". For values that animate or arrive late, use the runner's retrying assertion (Playwright's `toHaveCSS`, `expect.poll`) instead of a fixed wait.
- [ ] Step 5: Run the new tests in every runtime the runner covers, against the code as it is. Record each result. Every `fails now` case must fail, and its message must show the wrong value the plan describes; every `passes now` case must pass. A `fails now` case that passes means the test does not reach the bug, and a failure with another message (a missing fixture, a selector typo) means the test is broken: fix the test, never the code under test.
- [ ] Step 6: Write the "Failing tests" section of the plan from the template, and reply with the runner's own output for each failing test (the lines with the expected and received values, quoted, not summarized), the counts, and the pending decisions. Then self-check against "Quality criteria". Do not touch the code under test; the change belongs to `eng-implement`.

## Output template

Add to `docs/engineering/plans/<task>.md`:

```markdown
## Failing tests

- Owner: eng-unit-tests
- Command: `<the command that runs them>`
- Files: `<spec>`, `<fixture>`

| Test | Source | Expected before the change | Observed before (per runtime) |
|------|--------|----------------------------|-------------------------------|
| <name> | <Root cause › …, AC-n> | fails now | <runtime 1>: <received value>; <runtime 2>: … |
| <name> | <What a fix must preserve> | passes now | passes in every runtime |

- Result before the change: <n> failed, <m> passed (the failures are exactly the `fails now` rows)
- Pending decisions: <case and the question asked, or "none">
```

## Quality criteria

Approve only if all of the following hold:

- Every case of the source has a test, and every test names its source.
- The tests ran in every runtime the runner covers, and the observed column is filled from that run, with the wrong value quoted for each failure.
- The failing tests are exactly the `fails now` rows; no `passes now` test fails, and no `fails now` test passes.
- Assertions compare exact values; no fixed sleep waits for an animated or late value.
- No runner, dependency or configuration was added, and no file under test was changed.
- Every behaviour no source states, and every ambiguous word of the request, is a `pending decision` with the question asked, not an assertion chosen silently.
- The reply quotes the runner's output for the failures.

## Gotchas

- In a stylesheet project the fixture page must load the built file the user downloads (`dist/…css`), and the build must run before the tests, or the tests pass against a stale build.
- A retrying assertion waits out a 150 ms colour transition; `getComputedStyle` read once does not. The first real run's reproduction had to wait explicitly for the same reason.
- Tests for the behaviours to preserve pass before the change on purpose: they are the regression guard, and the report says so, so nobody mistakes them for tests that miss the bug.
- The first real run found an unstated behaviour while writing the tests (what a switch shows when a script sets `indeterminate`): the documentation defined the mixed state for the checkbox only. That is the user's call, asked with the documentation as the recommendation's ground.
