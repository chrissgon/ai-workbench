---
name: eng-integration-tests
description: >
  Test an implemented change through the assembled system the user runs (the built output, the
  real loader, the served page, the service with its real dependencies), covering the new
  behaviour, the states around it, the hostile conditions the decision record accepted, and
  the behaviours to preserve, then prove the tests catch the problem by running them against
  the code before the change. Use this skill after eng-implement, when a behaviour only exists
  when parts work together (markup inserted after load, a request through the whole stack, a
  plugin in a host), even if the user only says "test it end to end", "e2e" or "add
  integration tests". Also use it when someone asks for integration tests of a feature that is
  not built yet, to point to failing unit tests first.
license: MIT
metadata:
  area: engineering
  kind: capability
  inputs: [docs/engineering/plans/<task>.md, docs/engineering/adr/<NNNN>-<title>.md, AGENTS.md]
  outputs: [docs/engineering/plans/<task>.md]
  requires: []
  side_effects: []
  version: "0.3"
---

# Integration tests

## Purpose

Show that the change works where users meet it, not only in the unit that was edited: the built files served the way the project serves them, the real module loading, the real interaction between parts. And show that the tests are worth keeping: each test of new behaviour must fail on the code before the change, each test of preserved behaviour must pass on it. The result is the "Integration tests" section of the plan.

## Stop rules

Check these before creating or editing any file, and again before replying. They override the procedure.

1. **The change must exist.** If the behaviour is not implemented yet ("we'll implement it next week"), write no test: reply that integration tests come after the implementation, and that the tests to write now are failing unit tests (`eng-unit-tests`).
2. **Settings are applied to the process.** A test about a time zone, a locale or another environment setting runs the code in a process started with that setting (`TZ=<zone> <command>`, or a child process with that environment), in at least two settings; passing the value as an argument does not test the server's setting.
3. **The before-the-change run is a run.** Run the new tests against the previous code (a worktree of the base commit, or the previous release's files the project keeps) and report the counts it printed. A sentence saying what would fail there is not a run.

## When not to use

- The change does not exist yet: `eng-unit-tests` writes the failing tests first; this skill runs after `eng-implement`.
- One function or one rule in isolation: `eng-unit-tests`.
- Measuring speed or size: the project's benchmark or size script, cited in the plan by `eng-implement` or `eng-tradeoffs`.

## Inputs

| Artifact | Required | If missing |
|----------|----------|------------|
| The implemented change: the plan's "Change" section, or the diff against its base commit | yes | Ask for the base commit; without it the before-and-after proof cannot run |
| The cases: the plan's preserved behaviours and bug case, and the decision record's accepted failure modes | yes | Ask which conditions the change must survive and which it may fail |
| The project's end-to-end runner and fixtures | yes | Use the runner the project has; ask before adding one |

## Procedure

Progress:
- [ ] Step 1: Find how users get the change and test through that: the built files (run the build first), served by the project's server or test fixture, loaded the way a page or client loads them. Name the fixture or entry point you will use, and the signal that says the system is ready (a module fetched, the app mounted, a health check), so no test waits on a fixed delay to start.
- [ ] Step 2: List the cases, each with its source: the new behaviour; the states around it (inserted later, hidden then shown, replaced by a re-render, a slow network, a retry); the environment settings users have (reduced motion, a time zone, a locale); the hostile conditions the decision record accepted, asserting the promised degradation (behaves as before, an error message) rather than the success; and every preserved behaviour.
- [ ] Step 3: Write the tests beside the project's end-to-end tests, one behaviour per test, named for the behaviour, with a comment pointing to the plan and the decision record. Use retrying assertions for values that arrive; when asserting that something does not happen, trigger the thing that could cause it, wait a bounded time, and assert once.
- [ ] Step 4: Run them in every runtime the runner covers. All must pass.
- [ ] Step 5: Prove they catch the problem: check out the base commit in a scratch worktree (`scratch=$(mktemp -d)`, `git worktree add "$scratch" <base>`), or, where there is no history, copy the previous release's files the project keeps into a scratch folder; link the dependencies, copy the new test files in, build, and run them there on a different port or address than the current server, so a reused server does not serve the new build. Every test of new behaviour must fail; every test of preserved or degraded behaviour must pass. A new-behaviour test that passes before the change does not test the change: rewrite it. Remove the worktree after.
- [ ] Step 6: Run the project's full check (the whole suite, build checks such as server-side imports or export resolution) once with the change.
- [ ] Step 7: Write the "Integration tests" section of the plan from the template and self-check against "Quality criteria".

## Output template

Add to `docs/engineering/plans/<task>.md`:

```markdown
## Integration tests

- Owner: eng-integration-tests
- File: `<spec>` (through `<fixture or entry point>`), runtimes: <list>: <n> passed
- Against the code before the change (`<base>`, worktree, <runtime>): new behaviour <n> failed (<names>); preserved or degraded behaviour <m> passed (<names>)
- Full check with the change: `<command>`: <result>
```

## Quality criteria

Approve only if all of the following hold:

- The tests load the built output through the project's own serving path, and wait on a named readiness signal.
- Each accepted failure mode from the decision record has a test asserting its promised degradation.
- The before-the-change run happened, with its counts, and the failures are exactly the new-behaviour tests.
- The full check passed with the change.
- No scratch worktree or port change is left behind.

## Gotchas

- A test runner that reuses a running server (`reuseExistingServer`) serves whichever build started first: the first real run moved the before-the-change copy to another port, or both runs would have tested the same files.
- The fallback module arrives after the loader, so the readiness signal was "the checkbox present at load is already mixed", not `load` or `networkidle`.
- The accepted degradation is a behaviour too: with `animation: none !important` the checkbox is not mixed until the next click, and the test asserts exactly that, so a later change that silently breaks the fallback path fails.
