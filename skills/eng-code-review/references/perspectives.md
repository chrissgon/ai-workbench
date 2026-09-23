# Review perspectives

Loaded at step 5 of `eng-code-review`. Go through the six lists in order. Answer each question against the diff, the script output and the notes from steps 2 to 4. A "yes, and here is the line" becomes a finding; a "no" becomes one line under "Checked with no finding" naming where you looked. Questions that do not apply to the change (no database, no network, no UI) are skipped and said so in one line for the perspective.

Evidence to quote for any finding: the changed line (`file:line`), and, for regressions, the consumer line.

## 1. Scope and contracts

- Does every hunk serve the intent (`Does:` / the user's words)? List hunks that do something else; each is a finding (medium, or high when it alters behaviour).
- Is anything the intent requires missing from the diff (a `Delivers:` requirement, an acceptance criterion, a file the design names)?
- Do the changed routes, schemas, interfaces, file shapes, config keys and exports match the design's contracts? Quote both sides when they differ.
- Does the diff follow the conventions in `AGENTS.md` (naming, layout, error handling, commit rules)? Name the rule and the line that breaks it.
- Does the change contradict a recorded decision in `docs/workbench/state.md` or an approved artifact?
- `outside_touches` from the script: is each listed file justified by the intent? A lockfile is justified when `dependencies` is non-empty; the backlog's `Status:` line is justified by the implementation; anything else is a finding.
- Stubs, transitional settings, feature flags, disabled strictness or lint rules introduced by the diff: does each point at a backlog task that removes it?

## 2. Quality and maintainability

- Can a reader who did not write this understand each changed function from its name and signature alone? Name the misleading name.
- Is logic duplicated inside the diff, or with code that already exists (grep for the same expression)?
- Are errors caught and then ignored, logged without rethrow at a place that cannot recover, or turned into a default value silently?
- Do added `any`, casts, non-null assertions, `ignore` comments or `unknown` hide a type the code could state?
- Is there dead code: unused imports, variables, parameters, branches that cannot run, commented-out code?
- Did the diff add an abstraction, option or parameter that has one caller and no stated future use?
- `markers` from the script: debug output, lint suppression, TODO without a task, focused or skipped tests. Each is at least medium; a skipped or focused test is blocking.
- Are magic values (numbers, strings, URLs) that the code compares against or sends named and placed where the conventions put them?

## 3. Edge cases and robustness

For each changed function or template, answer with the input that breaks it:

- Empty: empty string, empty list, empty object, zero rows, no children.
- Absent: `null`, `undefined`, missing key, optional parameter omitted, environment variable unset.
- Boundary: first and last element, zero, negative, maximum length, one over the limit, the same value twice.
- Shape: wrong type at runtime (a string where a number is expected), extra keys, trailing whitespace, different case, unexpected encoding.
- Order and time: out-of-order events, a second call before the first finishes, retries, time zones, daylight saving, month and year boundaries.
- Partial failure: one item of a batch fails, the network drops mid-request, the file is half written, the process is interrupted.
- Environment: server versus browser (browser-only globals at module or component setup), development versus production defaults, another operating system's path separator.
- Idempotency: is calling it twice safe? What is left behind after a failure?

A finding states the input, the line that mishandles it and what happens.

## 4. Regression and performance

- `Consumers:` from step 4: for every changed export, route, schema, config key, CSS variable or file path, does each consumer still work with the new shape, name or behaviour? Quote the consumer line.
- Removed or renamed public names: is anything outside the diff still importing the old name (grep the old name)?
- Behaviour that existing callers relied on (return value on error, ordering, defaults, side effects): did it change without every caller being updated?
- Data: schema or stored-format changes without a migration or a reader that accepts both shapes.
- Dependencies (`dependencies` from the script): a major bump, a removed package, a new package. For each: is it required by the intent, is the version pinned as the conventions say, does the changelog or migration guide name a breaking change the diff does not handle?
- Work inside loops: a query, a network call, a file read or a heavy computation per item that was once per request before.
- Growth: what happens at ten times the data (pages, rows, files)? Unbounded lists, missing pagination, whole-file reads.
- Startup and bundle: new heavy imports on the critical path, browser bundles that grew by a dependency, work moved from build time to request time.
- Caching and invalidation: a cache added without a rule for when it is wrong.

## 5. Security and data

- Input that crosses a trust boundary (request body, query, headers, file upload, environment, third-party response): is it validated for type, length and format before use? Is validation server-side?
- Injection: is user-controlled text concatenated into a query, a shell command, a path, HTML, a template or a regular expression?
- Authorization: does every new entry point (route, handler, resolver, job) check who may call it, not only who is logged in?
- Secrets: `secret-suspect` markers from the script; keys, tokens or passwords in source, config, tests, fixtures or commit history; credentials read from the environment as the conventions say.
- Personal data: new fields that store or log names, emails, addresses, identifiers; logs that print request bodies.
- Output: HTML rendered from strings (`v-html`, `innerHTML`, `dangerouslySetInnerHTML`), redirects built from input, error messages that expose internals.
- Dependencies: a new package with a small user base or no maintenance; a postinstall script; a version range that floats.
- Files and processes: paths built from input, temporary files with predictable names, child processes with a shell.

## 6. Tests

- Does the diff change behaviour without a test that fails without the change? For a project with a test suite, missing tests for new behaviour are high.
- Do the tests assert the behaviour the intent describes, or only that the code runs (no assertion, assertion on a mock's call, snapshot of everything)?
- Do the tests cover the edge cases found in perspective 3? Name the missing case.
- Were tests weakened: an assertion removed or loosened, an expected value changed to match the new output without a stated reason, a timeout raised, a retry added?
- Focused or skipped tests (`.only`, `.skip`, `xit`, `@skip`): blocking.
- Do the tests depend on order, real time, the network or the developer's machine (absolute paths, a running service)?
- A test that passes before the change is not a regression test; for a bug fix, see the bug-fix checklist.
- Test count from step 3 versus test files touched: did a runner report `0 tests` or "no tests found"?
