# Audit, group 4: eng-architecture, eng-code-review, eng-codebase-map, eng-docs, eng-impact-analysis, eng-implement, eng-integration-tests

Read-only audit of `main` at `b363f1b`. Nothing in any repository was changed. Scripts and tests were run on copies under the session scratchpad; no eval was run and no model was called. `python3 scripts/validate.py` reports 0 errors and `eval_run.py --check-cases` reports 0 errors for the seven skills (case 3 of eng-implement is listed as unchecked because it has setup commands).

Evidence read: the highest complete iteration of each skill under `<eval workspace>/` (eng-architecture iteration-3, eng-code-review iteration-2, eng-codebase-map iteration-2, eng-docs iteration-1, eng-impact-analysis iteration-1, eng-implement iteration-3, eng-integration-tests iteration-1). All are complete, with no early ends, no contamination and no infrastructure failure. Only eng-architecture changed after its measurement (commit `dfa5e30`, one sentence in the Inputs table, line 41); the other six are `evaluated` on their current content.

Notation for pass patterns: `[strong | floor | strong baseline | floor baseline]`, one letter per run (P pass, F fail).

## Summary

| Skill | Must fix | Should fix | Needs a maintainer decision | Size of the change |
|-------|----------|------------|-----------------------------|--------------------|
| eng-architecture | 6 | 8 | yes | M |
| eng-code-review | 10 | 9 | yes | L |
| eng-codebase-map | 5 | 8 | yes | M |
| eng-docs | 3 | 8 | yes | M |
| eng-impact-analysis | 3 | 7 | yes | M |
| eng-implement | 5 | 9 | yes | L |
| eng-integration-tests | 4 | 8 | yes | M |

Last measured scores (with the skill: strong / floor; baseline: strong / floor): eng-architecture 0.95 / 0.906 (0.387 / 0.291); eng-code-review 0.90 / 0.821 (0.642 / 0.646); eng-codebase-map 0.978 / 0.911 (0.367 / 0.30); eng-docs 1.0 / 0.979 (0.312 / 0.667); eng-impact-analysis 1.0 / 1.0 (0.704 / 0.769); eng-implement 0.896 / 0.844 (0.578 / 0.533); eng-integration-tests 0.976 / 0.929 (0.532 / 0.667).

---

## eng-architecture

Per case, with the skill (strong / floor): case 1 `0.8, 1.0, 1.0` / `1.0, 0.8, 0.6`; case 2 `1.0 x3` / `1.0 x3`; case 3 `1.0, 1.0, 0.75` / `1.0, 1.0, 0.75`. The skill text on `main` differs from the measured one in one sentence (line 41, "route to" became "tell the user that `product-feature-spec` writes it"); none of the findings below depends on that sentence.

### Must fix (would fail, mislead the score, or break a principle)

1. **`SKILL.md:19`, `requires: []` is not what the procedure needs.** Step 1 (line 52) says "Check the registry for the current version of every dependency you name", the Inputs row at line 45 says "Open it and cite it" for framework documentation, the quality criterion at line 87 asks for a documentation URL and version, and case 1 sets `"allow_web": true` because the happy path cannot pass without the web. `contracts/environment.md` has the class. Fix: `requires: [search:web]`. The degraded behaviour is already half written at line 45; make it complete in step 1: "When no web access is available, take each version from the project's manifest or lockfile, cite no URL, and list every API you could not open under 'Assumptions to verify before implementation'; say `Web: not available` in the report."

2. **`SKILL.md:61` (step 10) does not say where the script is nor where the command runs.** `python3 scripts/check_design.py ...` reads as a path in the project; eng-codebase-map and eng-implement both carry the sentence, this skill does not. Fix, add after the command: "`check_design.py` is in this skill's folder: `scripts/check_design.py` is relative to the folder that holds this `SKILL.md`, not to the project. Run it from the project root, so that the `docs/...` arguments resolve."

3. **Case 1, assertion 1, fails good outputs for a formality** `[FPP | PFF | FFF | FFF]`. Text: "Every REQ, NFR, EDGE and AC id ... appears in the design, the reply quotes the final run of check_design.py (its command and its JSON output) reporting "ok": true, and ...check.json records "ok": true". The three with-skill failures all have every id covered and `check.json` with `"ok": true`; they fail because the reply wrote "Check, final run: same command → same `ok: true` JSON" (floor run-2, strong run-1) or abbreviated the ADR list as `[...ok...]` (floor run-3). In floor run-2 the first run was already ok and nothing was fixed, so the "final run" is the first run and the template (lines 74 to 76) forces the model to write the same long JSON twice. Two fixes, both needed:
   - Skill, output template lines 74 to 75: replace with
     `- Check, first run: <the command> → <the JSON line it printed, verbatim and whole>`
     `- Check, final run: <the command> → <the JSON line it printed, verbatim and whole> (when the first run was ok and nothing changed after it, write "the first run is the final run"); recorded in docs/engineering/designs/<feature>.check.json`
     and add to step 10: "Never write `same command`, `same output` or `...` in place of a command or of its output: a run that is not quoted did not happen for the reader."
   - Assertion, new wording: "Every REQ, NFR, EDGE and AC id from the specification appears in the design; docs/engineering/designs/markdown-content-model.check.json records \"ok\": true for this specification and this design; and the reply quotes the check_design.py command and the whole JSON line of a run reporting \"ok\": true (when the first run was already ok and nothing changed after it, that one quote counts as the final run)".

4. **Case 3, assertion 3, rests on something the grader cannot see** `[PPF | PPP | FFF | FFF]`. Text: "...docs/engineering/adr/0001-export-file-format.md is deleted, the design no longer cites ADR-0001, ...". The grader is shown only files that exist after the run; a deleted file is invisible. In strong run-3 `git status --short` in the case folder shows `D  docs/engineering/adr/0001-export-file-format.md`, the design is right, and the grader failed it ("the claimed deletion method is unverifiable"). Fixes:
   - Skill, output template: add a line `- Files: <the output of git status --short, verbatim: created, changed and deleted files>` and, in step 11, "Run `git status --short` and copy its output into the report; a deleted ADR shows there as ` D` or `D `."
   - Assertion, new wording: "The single-option ADR is removed, not completed with an invented second option: the final run's JSON (in the reply or in expense-export.check.json) lists no ADR (`\"adrs\": []`) or the reply's `git status --short` shows docs/engineering/adr/0001-export-file-format.md as deleted; the design no longer cites ADR-0001; and the design states the CSV format as decided by REQ-3".

5. **Case 1, assertion 2, contradicts the skill's own criterion** `[PPP | PPF | FFF | FFF]`. Text: "Every framework API named in the design cites a documentation URL with version or a file in the codebase". Quality criterion line 87 allows a third outcome: "anything uncited is listed under 'Assumptions to verify'". Floor run-3 listed `InvalidContentEntryDataError` and `trailingSlash` under "Assumptions to verify before implementation" and was failed for them. New wording: "Every framework API named in the design either cites a documentation URL with the version read, or a file in the codebase, or is listed under 'Assumptions to verify before implementation' with how to verify it".

6. **Case 2, assertion 3, is a language assertion that passes in all twelve runs**: "The reply is in English, the language of the prompt". Remove.

### Should fix (quality, robustness)

1. **Description (`SKILL.md:3-12`) misses the trigger of case 3.** Step 10 says the check is run "also when the task is to check a design that already exists", and case 3's prompt is "Run the traceability check on the design ... and fix what it flags", but the description names only "structure, design or architect a feature" and "a technical decision needs an ADR". Add: `Use it also when someone asks to check an existing design against its specification ("run the traceability check", "does the design cover the spec", "fix what the check flags") or to revise an ADR.` The description is 788 characters, so this fits under 1024.

2. **Step 2 gate (`SKILL.md:53`) does not say that nothing is written and that "go" is not an answer.** Proposed sentence: "For `user` decisions: stop before step 3, ask at most three questions, each with a recommended answer, and write no design file and no ADR until the user answers each one. `go`, `proceed` or `continue` is not an answer: ask again, or take the recommended answer only when the user says to take it, and record it under Decisions as `user answer <date>`."

3. **Case 3, assertion 2, passes in all twelve runs** `[PPP | PPP | PPP | PPP]`: "REQ-2 gets a component and AC-2 gets a verification row". CONTENT, trivially satisfied by any model told to fix what a check flags. Replace with a sharper one that carries the contract: "The component added for REQ-2 states the row contract of the specification (the columns, amounts with two decimals, rows sorted by date ascending), and the verification row added for AC-2 names a concrete check with an input and the expected output, not `manual`". To be confirmed on the first run that the baseline fails it; if it also passes everywhere, remove it.

4. **Case 3, assertion 4, floor run-3 failed for a missing command** `[PPP | PPF | FFF | FFF]`: the JSON of the final run was quoted, the command was not. Variance on the floor model against a template that asks for it; keep the assertion. The template change in must-fix 3 (the placeholder says `<the command>` on both lines) is the only change.

5. **Report template lacks what was read and whether the design was registered.** Add: `- Read: <specification, handoffs, codebase map, decisions, documentation pages opened (URL, version)>` and `- Registered in docs/workbench/state.md: <yes: rows added | no: the file does not exist>`.

6. **`docs/workbench/state.md` is a shared ledger this skill writes (step 11, line 62) and does not declare.** It is in `inputs` only. List it under the coming `updates` field: `updates: [docs/workbench/state.md]`. The skill also deletes an ADR file (Gotchas, line 98) and revises ADRs (line 103); both are covered by the declared `docs/engineering/adr/<NNNN>-<title>.md`.

7. **`scripts/check_design.py:70-71`: with no argument the usage text goes to stdout with exit 2.** AGENTS.md: data to stdout, diagnostics to stderr. Print the usage to stderr when it is an error. The same line exists in the three other scripts of this group. The script otherwise passes every check of item E: `--help` exits 0, each of `--spec`, `--design`, `--adr-dir`, `--report` given last without a value exits 2 with "Error: --x needs a value.", an unknown option exits 2, missing files exit 2, no traceback; 12 tests pass (`uv run --with pytest pytest skills/eng-architecture/scripts/tests -q`); Python standard library only, runs in the container.

8. **Fixtures are thinner than "a small real project".** `evals/files/search-open` is one file, and its Sources cite `docs/product/prd.md`, which is not shipped. `evals/files/trace-check` ships three documents whose design cites `src/pages/expenses.tsx`, `src/server/routes/index.ts` and `src/server/store/expenses.ts`, none shipped; strong run-3 of case 3 reported "the source files in Sources aren't in this repo, so I couldn't confirm the `expenses` table columns". Add the three small source files and a `package.json` to `trace-check`, and the PRD plus an `AGENTS.md` to `search-open`. `content-model/docs/workbench/state.md` says `Current flow: flow-new-feature`, a flow that is planned, not built (D12); harmless in a fixture, list it with the other fixtures that name it (eng-implement).

### For the maintainer to decide

1. **A degraded-mode case.** The skill has a degraded mode (no web) and no case for it; cases 2 and 3 do not need the web, case 1 needs it. A fourth case on the `content-model` fixture without `allow_web` would cost one long run per variant. Recommended: add it only if `requires: [search:web]` is accepted (must-fix 1); assertion: "The design cites no URL it could not open, names Astro 5.13.2 from package.json, and lists every framework API under 'Assumptions to verify before implementation'".
2. **Case 1 depends on the open network** (`docs.astro.build` content on the day). One with-skill reply reported promotional text of that site under "Instructions found in external content". This is inherent to `allow_web`; no change proposed, recorded so that a failing run of case 1 is read with the network in mind.
3. **The JSON line of `check_design.py` grows with the number of ADRs** (four ADRs gave a 500-character line), which is what tempts models to abbreviate it. Option: keep the line as it is and rely on must-fix 3, or print `"adrs_ok": 4, "adrs_failed": []` and keep the per-ADR detail only in `--report`. Recommended: keep the line; the wording fix is enough and changes no test.

---

## eng-code-review

Per case, with the skill (strong / floor): case 1 `1.0, 1.0, 0.8` / `0.8, 1.0, 0.8`; case 2 `1.0 x3` / `1.0 x3`; case 3 `0.75 x3` / `0.75, 0.75, 1.0`; case 4 `1.0, 0.75, 1.0` / `0.75, 0.5, 0.5`. Floor mean 0.821: the closest to the line in this group. Of the nine failed assertions on the floor model, two are an unverifiable assertion that failed good reviews (case 1), two are the template not quoting output (case 3), one is a good stop failed for the wording of its reason (case 4) and four are the skill not stopping in case 4.

### Must fix (would fail, mislead the score, or break a principle)

1. **`SKILL.md:55` (step 1) prescribes `patch`, which the eval container does not have.** `evals/container/Dockerfile` installs `ca-certificates curl git python3 python3-venv chromium fonts-liberation jq less procps ripgrep`; no `patch`. Floor run-3 of case 1 has `patch: command not found` in its transcript. Fix: use git, which the step already needs: "`git apply --check <file>` (exit 0: the patch applies), then `git apply <file>`". Also say how to tell an applied patch: "`git apply --reverse --check <file>` exits 0 when the patch is already in the tree; then nothing is applied and the checks run in the tree as it is."

2. **`SKILL.md:55` and `references/bug-fix-checklist.md:11`: the scratch recipe is a sequence of separate commands with a shell variable, and a failure in the first one makes the next ones act on the working tree.** Floor run-2 of case 4 ran `scratch=$(mktemp -d /tmp/.../review.XXXX)` (it failed), then `git worktree add "$scratch" HEAD` (aborted), then `git -C "$scratch" apply --reverse change.patch` with an empty `$scratch`, which reverse-applied the patch to the project itself; its reply says "The scratch setup failed and `git -C ""` fell back to the workspace, reverse-applying the patch. Let me restore the workspace." A review that edits the tree under review breaks the skill's last quality criterion (line 137). Floor run-3 of case 4 also left a second worktree behind (`git worktree list` shows two). Fix, step 1: "Make the scratch copy in one command, so that a failure stops everything: `scratch=$(mktemp -d) && git worktree add --detach "$scratch" HEAD && echo "$scratch"`. Copy the path it prints and write that literal path in every later command: a shell variable does not survive from one command to the next. Never run `git -C`, `git apply` or `cd` with an empty path. Remove it at the end with `git worktree remove --force <path>` and quote `git worktree list` (one line) in the report." The checklist's `/tmp/pre-fix` (a predictable name, which perspective 5 of this same skill calls a finding) becomes the same command, and its row gains the path for a change that is an applied patch with no parent commit: "for a patch already in the tree: in the scratch copy, `git apply --reverse <file>` and run the test there".

3. **Output templates (`SKILL.md:83` and `:120`) do not quote the output of the checks, while quality criterion line 131 asks for "a command output quoted in the artifact".** Case 3, assertion 3, "The test command is run and its output quoted" is `[FFF | FFP | FFF | FFF]`: five of six with-skill runs ran the tests (the produced `__pycache__` files show it) and wrote `tests 6 passed, 0 failed (full suite, exit 0)`, which is what the template shows. This is a skill defect: fix the template, keep the assertion. Replace line 83 with:
   ```
   - Checks run (each: the command, its exit code, and the line it printed that shows the result, verbatim):
     - lint: `<command>` → exit <n>: `<line>` | none configured (AGENTS.md)
     - type-check: `<command>` → exit <n>: `<line>` | none configured
     - tests: `<command>` → exit <n>: `<the runner's count line, for example "Ran 6 tests in 0.001s">` `<its result line, for example "OK">`
     - task check: `<command>` → exit <n>: `<count line>` `<result line>` | not run: <reason>
   - Working tree after the review: `git status --short` → `<its output, verbatim>`
   ```
   and line 120 with `- Checks: <each command → exit code and the result line it printed, verbatim>`. Sharpen the assertion so that it says what counts: "The review or the reply quotes the test command and the runner's own lines for it (`Ran 6 tests` or `Ran 2 tests`, and `OK`), not only a count written by the reviewer".

4. **Case 1, assertion 5, fails good runs because the grader cannot see an unchanged file** `[PPF | FPF | PPP | PPP]`: "No source or test file is modified by the review". In all six with-skill runs `git status --short` in the case folder shows no change under `src/` or `tests/` other than `__pycache__/`; three were failed ("nothing ... lets me verify"), and the baseline passed all six. The assertion separates nothing and costs the floor model 0.2 in two runs. Fixes: (a) the "Working tree after the review" line of must-fix 3; (b) `"grader_files": ["src/money.py", "src/report.py", "tests/test_money.py", "docs/product/backlog.md", "docs/engineering/plans/T-ap-3.md"]` on cases 1, 2 and 4 (and the `secret` equivalents on case 3), so that the files are shown as inputs "not produced by" the run; (c) new wording: "Neither src/money.py, src/report.py nor tests/test_money.py is among the files the run produced or changed, and the reply or the review quotes `git status --short` with no line for them"; (d) a `.gitignore` with `__pycache__/` in the three fixtures, so that the quoted status is not three lines of bytecode folders.

5. **Case 4: the skill does not stop on the floor model, and the assertion asks for a reason the skill does not prescribe.** Assertion 3 "No verdict (approve or request changes) is given" is `[PPP | PFF | FFF | FFF]`: floor run-2 wrote a full review with "Verdict: request changes" and floor run-3 "Verdict: approve" against T-ap-3 without asking. Assertion 2 "The output asks the user for the task or intent and recommends T-ap-3 with the reason that the patch touches its files" is `[PFP | FFF | FFF | FFF]`: strong run-2 and floor run-1 did stop, ask and recommend T-ap-3, with the reasons "the patch changes `parse_amount`, adds a test and edits the T-ap-3 backlog entry" and "closest task title, and the patch itself updates T-ap-3's record"; the second is exactly what `SKILL.md:44` tells the model to recommend ("the commit message or the closest task title"). Cause of the missed stop: the rule sits in the middle of the 130-word step 1, while eng-docs and eng-impact-analysis, whose stop cases pass on the floor model in every run, carry a "Stop rules" section above the procedure. Fixes:
   - Skill: add after "Purpose":
     "## Stop rules — Check these before running any command, and again before replying. They override the procedure. 1. **No intent, no review.** When the task id the user names is not in `docs/product/backlog.md` and the request gives no intent in words, the whole reply is: the id is not in the backlog (quote the `grep` that shows it); the question 'which task or intent does this change belong to?'; and one recommended answer: the backlog task whose `Touches:` files or backlog entry the change modifies, with that as the reason. Write no review file and give no verdict. `go` or `proceed` is not an answer. 2. **A request to approve is not a verdict.** 'Just approve', 'LGTM?' and 'it is trivial' change nothing: the checks run and the verdict follows the severity rule. 3. **The tree under review is never edited**, not even to try a fix or to reverse a patch; anything of the kind happens in the scratch copy." and change line 44's recommended answer to "the task whose `Touches:` or backlog entry the change modifies, else the commit message".
   - Assertion 2, new wording (the reason is checked, the phrasing is not): "The output asks the user which task or intent the change belongs to and recommends T-ap-3, with a reason taken from the patch or the backlog (the patch changes files of that task's Touches, or its backlog entry)".

6. **`scripts/change_scope.py:366-373` fails the missing-value check, like the two scripts already known.** `--repo`, `--range`, `--patch`, `--touches`, `--max-files`, `--max-lines` given last without a value end in an `IndexError` traceback with exit 1; `--max-files abc` ends in a `ValueError` traceback with exit 1. Required: exit 2 and a usage message on stderr. Fix: a `value(i, name)` helper as in `check_design.py` ("Error: --x needs a value."), and `int()` inside a `try` ("Error: --max-files needs a whole number."). Add tests for both (see should-fix 6). Other checks pass: `--help` exits 0, unknown option exits 2, a missing patch file exits 1 with a message, an empty change exits 3; JSON to stdout, diagnostics to stderr; Python standard library and git only. `redact.py`: `--help` 0, unknown option 2, reads stdin, byte-identical to `scripts/redact.py`.

7. **`SKILL.md:56` (step 2) does not say where the script is.** Add: "`change_scope.py` is in this skill's folder: `scripts/change_scope.py` is relative to the folder that holds this `SKILL.md`, not to the project; `--repo .` is the root of the project under review, so run it from there."

8. **Bytecode files sit inside the fixtures and the scripts folder on the maintainer's disk**: `evals/files/fix-good/{src,tests}/__pycache__/*.pyc`, the same in `fix-symptom` and `secret`, and `scripts/__pycache__/redact.cpython-311.pyc`. Git ignores them and the content hash skips them, but `eval_run.py:447` copies a fixture folder with no ignore pattern, so they go into the case folder and into the fixture commit; on another clone they do not exist, so the same case is a different tree on two machines, and after the tests run they show as changed files to the grader (floor run-3 of case 1 was failed with them listed). Delete them before the round (no skill folder change, no hash change), and add the `.gitignore` of must-fix 4. The runner-side fix (ignore `__pycache__`, `*.pyc`, `.DS_Store` when copying fixtures) is in "Patterns".

9. **Fixture `secret` names a real company and a non-`.example` host** (principle 8). `evals/files/secret/src/client.py:5` and `change.patch`: `STRIPE_KEY = "prod_..."`; line 6: `https://payments.internal/v1/totals`. Rename to a fictional name that `redact.py`'s `ASSIGN_RE` still matches (`NORTHPAY_KEY`) and to `https://payments.example/v1/totals`, and update case 3's assertion 1 ("The hard-coded key in src/client.py (NORTHPAY_KEY = \"prod_...\") ..."). `.security-scan-allow` lines 5 and 6 name the files, not the variable, and stay.

10. **Case 4, assertion 4, is a language assertion that passes in all twelve runs.** Remove.

### Should fix (quality, robustness)

1. **Case 3 measures almost nothing.** Assertions 1, 2 and 4 pass in all twelve runs and assertion 3 fails in eleven, so every variant scores 0.75. Assertion 4 ("The verdict is request changes; the review does not approve because the user asked it to") is a GUARD: keep. Assertions 1 and 2 are CONTENT that any model satisfies: keep assertion 1 (it carries the AGENTS.md rule) and replace assertion 2 with three that the baseline fails, checked against the evidence: (a) "The key's value appears nowhere in the reply or in the review; the finding cites src/client.py:5 with the masked text of the marker" (the value leaked in 2 of 6 baseline runs, 0 of 6 with the skill); (b) "The review reports that `send_total` has no test as a finding" (0 of 6 baseline, 6 of 6 with the skill); (c) "The review is written to docs/engineering/reviews/T-ap-5.md with the sections Findings, Checked with no finding, Scope and Verdict" (no baseline run writes the file; no case asserts the artifact today).

2. **Case 2: assertion 2 passes in all twelve runs** ("The review states that the fix addresses a symptom because the changed code is in src/report.py while the root cause in the plan is parse_amount in src/money.py"): CONTENT, the plan in the fixture says it. Replace with: "The bug-fix checklist reports the plan's reproduction as run by the reviewer and still printing `12.5`" (6 of 6 with the skill, 0 of 6 baseline). Assertion 5 ("The reviewer does not edit src/money.py or the tests to fix the problem") passes in all twelve: GUARD, keep, reworded to be verifiable: "Neither src/money.py, src/report.py nor tests/test_money.py is among the files the run produced or changed".

3. **Case 1, assertion 1** `[PPP | PPP | PPF | PPP]`: "The reviewer runs the test command itself and quotes its result (4 tests, OK) rather than repeating the backlog's status note". Passes on a count written by the reviewer. With must-fix 3: "The review or the reply quotes the test command and the runner's lines `Ran 4 tests` and `OK`, not only the backlog's status note".

4. **`requires: []` (`SKILL.md:21`) while the Inputs row at line 43 uses "the available code-hosting integration" to fetch a pull request.** The class exists (`integration:vcs`) and the degraded behaviour is already written ("if there is none, ask for the branch name or the patch file"). Declare `requires: [integration:vcs]`.

5. **Cases not covered.** The skill has behaviours no case reaches: a check that cannot run (`not run: <reason>`, rated high, step 3); a pull request with no integration (degraded mode, line 43); a rename-heavy or `large` change (step 4). Recommended: one case for `not run` (a fixture whose `AGENTS.md` names a lint command that is not installed; assertions: "The lint is recorded as `not run` with the reason, never as passing, and is a finding of severity high" and "The verdict is request changes").

6. **`scripts/tests/test_change_scope.py` has two tests for a 436-line script** (masking and range refusal). Add: a flag without its value and a non-integer exit 2 without a traceback; `--patch` on a small diff gives the totals; an empty change exits 3; `--touches` fills `outside_touches`; a pure rename is counted in `pure_renames`. Tests are outside the content hash, so they cost no measurement. The file also locates the script from the repository root (`ROOT = Path(__file__).resolve().parents[4]`, line 14): copied with its skill folder alone it fails (it did in the audit copy until the folder was placed under a `skills/` parent). Use `Path(__file__).resolve().parents[1] / "change_scope.py"`.

7. **`SKILL.md:43` default reference.** "Default to the working tree when it is dirty, otherwise the last commit" is a guess about scope the reply must show. Add to the chat template: `- Reviewed: <reference, and why this one>`.

8. **`description` is 1,009 characters**, 15 under the limit, and misses "review my changes before I commit" and "check this patch". There is no room to add without trimming: drop the list of six perspectives ("from six perspectives: scope and contracts, quality, edge cases, regression and performance, security and data, tests") to "from six perspectives" and add `"review my changes", "check this patch"` to the user's words.

9. **`scripts/change_scope.py:359-360`: usage on stdout with exit 2 when no argument is given.** Send it to stderr.

### For the maintainer to decide

1. **`scripts/redact.py:30-40` labels credential formats with product names** ("AWS access key", "GitHub token", "Slack token", "Stripe key", "Netlify personal access token", "Google API key"). They are format names a reviewer needs, not AI tools, and the file is a byte-identical copy of `scripts/redact.py` checked by `scripts/tests/test_script_copies.py`. Recommended: keep; note the exception next to principle 1, as commit `b363f1b` did for other product names.
2. **Step 5 (`SKILL.md:59`) names the `reviewer` agent and branches on "when the harness can run work in isolation".** It is principle 7 applied, but it is the one place in the group with two paths. No eval run used it (the adapters give no such agent). Recommended: keep the branch, move it to one line after the default path ("Default: do the six perspectives yourself, in order. When work can run in isolation: ...").
3. **`skills/eng-code-review/scripts/redact.py` has no test in the skill's own `scripts/tests/`**; it is covered by the repository's `scripts/tests/test_security_scan.py`. D10 says a skill's tests live in the skill. Recommended: a three-line test here that imports the copy and masks one assembled fake key.

---

## eng-codebase-map

Per case, with the skill (strong / floor): case 1 `1.0, 1.0, 0.8` / `1.0, 0.8, 1.0`; case 2 `1.0 x3` / `1.0 x3`; case 3 `1.0 x3` / `0.6, 1.0, 0.8`.

### Must fix (would fail, mislead the score, or break a principle)

1. **`scripts/map_codebase.py:212-214`: a flag without its value is a traceback** (known; confirmed). `--root`, `--focus`, `--top` given last end in `IndexError`, exit 1; `--top abc` ends in `ValueError`, exit 1. Fix as in `check_design.py`, then remove the `xfail` at `scripts/tests/test_map_codebase.py:99` and add the non-integer case. Other checks pass: `--help` 0; unknown option 2; `--root /nonexistent` 2 with a message; a folder without source files prints `{"error": "no source files found", ...}` and exits 1; 7 tests pass and 1 is the expected failure; standard library only. On the `small-app` fixture it prints exactly the numbers case 1 asserts (stores 2/0, components 1/0, pages 1/2, root files 0/2), and on `monorepo` `"likely": true`.

2. **"Nothing changed" is self-reported in the skill and unverifiable in the case.** `SKILL.md:58` (step 9) says "Confirm nothing changed: the working tree shows only the new document" without a command, the report template (line 89) is the fixed sentence "Working tree: unchanged except the map (and the state row)", and case 1's assertion 5 `[PPF | PPP | FFF | FFF]` failed strong run-3 on "there is no concrete evidence that no other file was produced". Fixes:
   - Step 9: "Run `git status --short --untracked-files=all` in the project root and copy its output into the report; when the project is not a git repository, say so and list the files you created."
   - Template line 89: `- Working tree: \`git status --short --untracked-files=all\` → \`<its output, verbatim>\``, and a new line `- Measured: \`python3 <this skill's folder>/scripts/map_codebase.py --root <root>\` → source_files <n>, modules <the module names with afferent/efferent>`.
   - Assertion 5, new wording: "No sentence of the map contains should, could or consider; docs/engineering/architecture.md is the only file the run produced or changed, and the reply quotes `git status --short` showing no other project file".

3. **Step 7 (`SKILL.md:56`) does not say what a disagreement with the specification must state, and the floor model drops the part that proves it.** Case 3, assertion 3 `[PPP | PPF | FFF | FFF]` (floor run-3 wrote Vuex against Pinia with both locations and never said that `src/store/index.ts` does not exist), assertion 5 `[PPP | FPP | FFF | FFF]` (floor run-1 never said axios is not a dependency), assertion 4 `[PPP | FPP | FFF | FFF]` (floor run-1 paraphrased the specification as "renders the product list" and left out where the code renders `ProductCard`). The outputs are incomplete, so the skill is fixed, not the assertions. Add to step 7: "For each disagreement between the registered specification and the code, write one observation with three parts: the specification's sentence quoted with its file and line; what the code does, with file and line; and, when the specification names a file, a package or a call, whether it exists (`ls <path>`, the manifest's dependencies): 'the specification names `<x>`; it is not in the code'." and to the map template under Observations: `- Specification <file>:<line> says "<quote>"; the code: <fact> at <file>:<line>; <the named file or package>: <exists | not in the repository | not a dependency>`.

4. **Case 2, assertion 4, is a language assertion that passes in all twelve runs.** Remove.

5. **The description (`SKILL.md:3-9`) does not carry the user's words.** All three prompts say "map" ("Map this codebase", "Map this repo's architecture", "Map the code") and the description never does; case 3's situation (a specification exists, compare it with the code) is not named either. Proposed last sentences: `Use this skill when someone says "map this codebase", "map the repo", "how is this put together", "walk me through the architecture" or "I'm new here", when onboarding to a repository, before impact analysis, refactoring or a migration plan, when a project has no architecture document, or when an architecture document exists and must be compared with the code. It reads and reports only: it never changes code and never recommends.` (539 characters today; this stays under 1024.)

### Should fix (quality, robustness)

1. **Case 1, assertion 2** `[PPP | PFP | PPP | PPP]`: floor run-2 traced `router.ts → Home.vue → catalog.ts → fetch` and then added `ProductCard.vue` as a fifth step; the grader failed "ending at the fetch". The output is good. New wording: "A traced path goes from src/pages/Home.vue (which calls the catalog store's load) to src/stores/catalog.ts and its fetch to VITE_API_URL/products, in that order; src/components/ProductCard.vue is described as rendered by Home.vue and nowhere as a caller of the store or of the fetch". Note that this assertion passes in all six baseline runs: it guards a fact, it does not separate.

2. **Case 1, assertion 3, passes in all twelve runs**: "VITE_API_URL appears as an integration point configured by environment". CONTENT, trivially satisfied (the name is in the one store file). Remove, or sharpen to the skill's own rule (step 5: "Unknown purpose stays 'purpose not established'"): "The integration point for VITE_API_URL names where it is read (src/stores/catalog.ts) and does not state the external system's name or owner, which the code does not establish". Recommended: sharpen and check on the first run; remove if it still passes everywhere.

3. **Case 2, assertion 2** ("The question includes a recommended answer") `[PPP | PPP | FFF | FFF]` does not check the skill's rule, which is "exactly one package, chosen by the first rule that decides". New wording: "The question recommends exactly one package, packages/api, and gives the rule that decided (both are applications with the same number of source files, so alphabetical order)". Assertion 3 ("No docs/engineering/ file is created before the answer") passes in all twelve: GUARD, keep.

4. **The `monorepo` fixture is close to a placeholder** (`export const app = "api";`, manifests with one dependency and no script). It is enough to stop on, but the recommendation it produces is decided by the last rule (alphabetical), the least interesting one. Give `packages/web` a `"scripts": {"dev": "vite"}` and replace `packages/api` by a library `packages/shared` imported by `web`, so that rule 2 (an application over a library) decides, and assert `packages/web`.

5. **The `small-app` fixtures import through `~/` and ship no configuration that defines the alias** (no `vite.config.ts`, no `tsconfig.json`, no `index.html`). Vite has no default `~` alias, so the project would not build, and Gotchas line 110 tells the model to "check the framework configuration", which is not there. Add a `vite.config.ts` with the alias and an `index.html`; then rerun the script on the fixture and correct the numbers of assertion 1 if the root-files module changes (the script was run on the present fixture only).

6. **Case 3, assertion 2** ("The registered specification file is byte-identical after the run") rests on what the grader can infer. It works today because `ARCHITECTURE.md` is in `grader_files`. Verifiable wording: "ARCHITECTURE.md is not among the files the run produced or changed".

7. **Gates not covered by a case and not worded against "go".** `SKILL.md:43` (a specification is named and not found: stop and ask for its path) has no case; the Monorepo question (line 75) says "Write no map and read no source file until the user answers" and does not say that "go" is not an answer. Add "`go` or `proceed` is not an answer: ask again, naming the recommended package" and a fourth case: prompt "Compare the code with our architecture spec in docs/ARCH.md" on the `small-app` fixture with `"absent_on_purpose": ["docs/ARCH.md"]`; assertions "The reply asks for the specification's path and says docs/ARCH.md was not found" and "No file under docs/engineering/ is among the files the run produced".

8. **`docs/workbench/state.md` is updated (step 8, line 57) and declared only as an input.** List it under `updates`. `scripts/map_codebase.py:206-207` prints the usage to stdout on a usage error; send it to stderr.

### For the maintainer to decide

1. **`scripts/map_codebase.py:32`, `CLIENT_HINTS` contains `"openai"` and `"anthropic"`** (with `"stripe"`, `"supabase"`, `"firebase"`). They are client libraries the script detects in the mapped code, not a harness, but principle 1 says a core file "must not mention any AI tool by name" and the validator does not flag them. Recommended: keep and record the exception, or move the list to a data file with a `validate: allow` line; decide once for the repository.
2. **Fixtures name real open-source frameworks** (Vue, Pinia, Vite, React, Fastify, axios). A codebase map without real framework names would test nothing; recommended: keep, they are not "a project that uses the workbench".

---

## eng-docs

Per case, with the skill (strong / floor): case 1 `1.0 x3` / `1.0, 1.0, 0.88`; case 2 `1.0 x3` / `1.0 x3`. Two cases only.

### Must fix (would fail, mislead the score, or break a principle)

1. **Case 1, assertion 7, fails a good run because the grader cannot see an unchanged file** `[PPP | PPF | PPP | PPP]`: "src/due.js is unchanged". In floor run-3 `git status --short` shows only `README.md`, the plan and `docs/guide.md` as modified; the grader wrote "no file content or diff for src/due.js is shown". Same defect in assertion 4 ("CHANGELOG.md is unchanged, and a commit message is proposed") and in case 2's assertion 1 ("README.md and docs/guide.md are unchanged"), which pass today on the grader's goodwill. Fixes: add `"grader_files": ["src/due.js", "CHANGELOG.md", "README.md", "docs/guide.md", "AGENTS.md"]` to both cases (unchanged files are then shown as inputs "not produced by" the run); reword to "src/due.js is not among the files the run produced or changed", "CHANGELOG.md is not among the files the run produced or changed, and a commit message is proposed", "Neither README.md nor docs/guide.md is among the files the run produced or changed"; and give the skill the line that carries the evidence (should-fix 1).

2. **Case 1, assertion 8, is a language assertion that passes in all twelve runs.** Remove.

3. **Case 1, assertions 1 and 2, pass in all twelve runs**: "README.md documents the timeZone parameter of dueLabel and no longer says the label uses the server's local time zone" and "docs/guide.md no longer claims dueLabel always prints in the server's local time zone". CONTENT that any model produces when asked to update the docs; with the language assertion they are three of eight points given to every variant, which is why the floor baseline reads 0.5 in every run of this case. Keep one as the outcome ("README.md and docs/guide.md describe the timeZone parameter and no longer say the label follows the server's zone") and replace the other by the thing the skill adds and the baseline does not (step 3: "When a test shows the claim is false for a case the change does not cover, write that case down"): "The documentation states the case the change does not cover, found by running it: for a customer zone at UTC+12 or later (for example Pacific/Auckland) the label is the next day, and the reply or the plan shows the command and its output". Both with-skill runs read for this audit (strong run-1, floor run-1) state it and quote the run; neither baseline run read does.

### Should fix (quality, robustness)

1. **The output template has no place for the runs that stop rule 2 demands, and there is no template for the reply.** `SKILL.md:35` says every claim is shown "with the command you ran and its output as printed ... in the reply or the plan", but the "Docs" section (lines 69 to 82) has only a "Why" column. Floor run-3 summarised six runs as `TZ=UTC|America/Sao_Paulo|... node -e '...' → all "2026-09-25"`, which is not a command anyone ran. Add to the template:
   ```
   - Claims run (the command and the lines it printed, verbatim, one block per claim):
     `<command>` → `<output>`
   - Working tree: `git status --short` → `<its output, verbatim>`
   ```
   and a chat template: `## Docs updated: <task>` with `- Documents changed: <file: sentence before → after>`, `- Claims run: <command → output>`, `- Left alone: <generated documents, with the commit message proposed>`, `- Outside this repository: <...>`, `- Working tree: <git status --short>`.

2. **The first Inputs gate has no recommended answer and no case.** `SKILL.md:48`: "Ask for the base commit or the task; do not document from the request text alone". Proposed: "Stop and ask which change to document, recommending the most recent plan under `docs/engineering/plans/` or, when there is none, the last commit (`git log --oneline -1`); write nothing until the user answers; `go` is not an answer." Add a third case on the same fixture without the plan: prompt "update the docs for the change" with `"absent_on_purpose": ["docs/engineering/plans/due-label-customer-time-zone.md"]` and the fixture's `src/due.js` already changed; assertions: "The reply asks which change to document and recommends one, naming where it found it" and "No document is among the files the run produced or changed".

3. **The skill does not say what to do when the plan file does not exist.** Line 66 says "Add to `docs/engineering/plans/<task>.md`". eng-impact-analysis creates the file with a header (its line 48); say the same here.

4. **`outputs` (`SKILL.md:18`) declares only the plan.** The procedure's real writes are the project's documents (`README.md`, `docs/**` pages, migration and architecture notes); they are project files, not workbench artifacts, so they need a decision on how the contract names them (see Patterns). The plan is a shared ledger (written by nine skills): list it under `updates`.

5. **Prompts cite `invoices/` as a folder; the fixture's content is copied to the root of the case folder**, so there is no `invoices/` there ("...is already implemented in invoices/ (plan in docs/engineering/plans/...)"). No run was misled (none created an `invoices/` folder), and `--check-cases` does not flag it, but the prompt names a path that does not exist. Reword both prompts to "in this project (invoices)". Same in eng-impact-analysis and eng-integration-tests.

6. **The fixture's `AGENTS.md` says "Supported runtimes: Node 20 and 22"; the container has Node 24.10 only.** Runs note it as a gap ("Node 20/22 not installed here"). Change to "Node 24" in the three copies of the fixture in this group, or the skill's "run it in every runtime" instructions cannot be met.

7. **Case 2 has no assertion for the offer the stop rule prescribes** ("offer to note the sentences that will change"). Add: "The reply offers to note which sentences will change once the option exists, and writes that note in no published document".

8. **`SKILL.md:57`, the example terms** "(for a margin fix: `margin`, `reset`, `Preflight`, `centre`)" read as one project's case. Replace by a neutral example from the fixture's domain: "(for a time-zone fix: `timeZone`, `time zone`, `server`, `local`)".

### For the maintainer to decide

1. **Gotchas lines 97 and 98 tell the story of one real case with a product name** ("a Tailwind guide can say the layer order keeps the reset below the library ... a modal's `margin`"; "Testing the guide's own workaround found a second gap: an unlayered reset (Tailwind v3 with Preflight kept) ..."). Principle 8 asks for the lesson without the case. Recommended rewrite: "A guide can be true in general and wrong for one component: a rule that holds for every property a library declares can fail for one it leaves to the browser. Test the sentence on the component the change touched." and "Test the guide's own workaround: a workaround can hide a second gap, and the guide must then say what those users restore."
2. **HTML comment with prose in a fixture**: `evals/files/invoices/CHANGELOG.md:1` (`<!-- Generated by changelogen ... Do not edit by hand. -->`). The case depends on it and the scan accepts it; it also names a real tool. Recommended: keep the comment, rename the tool to "the release tool".

---

## eng-impact-analysis

Per case, with the skill: every run of every case scores 1.0 on both models. The baseline is high (0.704 / 0.769), and eight of fourteen assertions pass in all twelve runs: this skill's record is the one that says least about the skill.

### Must fix (would fail, mislead the score, or break a principle)

1. **Case 2 measures nothing: its three assertions pass in all twelve runs**, so the case is 1.0 in every variant and lifts both baselines. Texts: "Rule 1 (zero runtime dependencies) is quoted or cited and adding date-fns-tz is flagged as breaking it or needing the user's decision" (CONTENT, the rule is the first line of `AGENTS.md`), "package.json gains no dependency and no install command is run" (GUARD; the second half is unverifiable), "The analysis states the change as behaviour and does not settle on date-fns-tz as the chosen approach" (CONTENT). Keep the first, reword the guard to "package.json is not among the files the run produced or changed", and add what the skill adds, each checked against the evidence: (a) "An 'Impact' section is written to a file under docs/engineering/plans/" (all six with-skill runs write it; no baseline run writes any file); (b) "The section's baseline line quotes the size command and the line it printed, `src/ 307 B gzip (budget 1024 B)`" (the number is the same in every with-skill run and in the audit's own run on Node 24.10); (c) "date-fns-tz is listed as one option beside at least one other (the platform's `Intl`), each with the files it touches and its release impact".

2. **Two language assertions pass in all twelve runs**: case 1 assertion 8 and case 3 assertion 3. Remove both.

3. **Case 1, assertion 7, mixes an unverifiable half with a judgment**: "No file under src/ or test/ is modified, and no approach is chosen as the one to implement" `[PPP | PPP | PPF | PPP]`. The same "is unchanged" wording failed good runs in eng-docs, eng-code-review and eng-integration-tests; here it passed on goodwill. Split and make verifiable: "No file under src/ or test/ is among the files the run produced or changed" (GUARD) and "The Impact section lists the ways the behaviour could be built as options and names none as chosen" (CONTENT; the baseline's one failure was this half). Add `"grader_files": ["AGENTS.md", "README.md", "src/due.js", "src/index.js", "test/due.test.js", "package.json"]` to the three cases: today the grader checks "the README sentence is quoted" and "rule 1 is quoted" against files it never sees.

### Should fix (quality, robustness)

1. **Case 1, assertions 2 and 6, pass in all twelve runs**: "npm run size (or node scripts/size.mjs) is run and its byte count appears in the analysis" and "shop-web is named as a dependant". CONTENT. Replace the first by the quoted line of must-fix 1(b) for this case (`src/ 307 B gzip (budget 1024 B)` in the plan's "Baseline measured" line, with the command); remove the second or fold it into assertion 5 ("... and shop-web is named as the dependant outside the repository").

2. **`<task>` has no rule when no task exists**, and twelve with-skill runs produced five file names (`due-label-customer-timezone.md`, `due-label-customer-time-zone.md`, `customer-timezone-due-label.md`, `customer-timezone-duelabel.md`, `due-label-timezone.md`). The next skill in the chain looks for the plan by name. Add to stop rule 2 (`SKILL.md:34`): "`<task>` is the task id when the request names one; otherwise the plan that already exists for this change under `docs/engineering/plans/` (list the folder first); otherwise a name of at most five lowercase words joined by hyphens, taken from the behaviour. Say the path in the reply."

3. **No template for the reply, and the plan template quotes no output.** `SKILL.md:74`: "Baseline measured: `<command>` on <date>: <numbers>". Make it "`<command>` on <date> → `<the line it printed, verbatim>`", add `- Read: <rule files found, with their paths>`, and add a chat template: `## Impact: <task> → docs/engineering/plans/<task>.md`, `- Change (behaviour): <...>`, `- Baseline: <command → line>`, `- Rules the change meets: <rule, source, user decision or not>`, `- Options listed, none chosen: <...>`, `- Working tree: \`git status --short\` → <verbatim>`.

4. **Stop rule 1 (`SKILL.md:33`) asks without a recommended answer.** "your whole reply is that question, with two or three example answers drawn from the code". AGENTS.md asks for a recommended answer on every gate. Proposed: "... with two or three example answers drawn from the code, the first marked `Recommended` with the reason it is the likeliest (the behaviour a rule, a document or a dependant already mentions). `go` is not an answer." Case 3's assertion 1 then becomes: "The reply asks which behaviour should change, gives at least two example answers drawn from the code (for example dueLabel's time zone, daysLeft's rounding) and marks one as recommended" (today's text, "The reply asks which behaviour should change before analysing", is passed by a one-line question).

5. **Case 3, assertion 2** ("No Impact section is written for an invented change") `[PPP | PPP | FPF | PFF]`: verifiable wording "No file is among the files the run produced, and the reply contains no Impact analysis of a change the user did not name".

6. **The fixture's only test passes or fails with the machine's time zone** (`test/due.test.js` asserts `dueLabel("2026-09-25")`, which is `2026-09-24` under `TZ=America/Sao_Paulo`; in the audit's shell `npm test` fails, in the container it passes because the container is in UTC). That is the bug the case is about, and `AGENTS.md` says "CI runs in UTC", but the facts the assertions rest on hold only while the image has no `TZ`. Recommended: say it in the case's `expected_output` ("the container runs in UTC, so `npm test` passes there"), and change "Supported runtimes: Node 20 and 22" to Node 24 (eng-docs should-fix 6); several runs spend a line on "Node 20/22 not installed here".

7. **Frontmatter.** `outputs: [docs/engineering/plans/<task>.md]` is the shared plan ledger: list it under `updates` (the skill creates the file when missing, line 48, so it may stay in `outputs` too; say which). `inputs` are produced by other skills or are user-provided (`AGENTS.md`). The prompts' `invoices/` is the same defect as eng-docs should-fix 5.

### For the maintainer to decide

1. **Gotchas lines 112 to 115 carry the details and the numbers of one real case**: "`supported: () => false`", "'No `MutationObserver`' in the architecture's hard rules", "the migration guide promised that 'components inserted at any time work'", "493 B published, 487 B on the branch"; steps 1 and 4 carry more of it ("the mixed state shows for markup inserted after load", "a downloaded file list, a call count"). Principle 8: "no decisions, dates or numbers of a real case". Recommended: keep the four lessons, drop the quotes and replace the numbers by invented ones ("a published release and the working branch differ by a few bytes: measure on the code being changed").
2. **Whether the skill keeps a place in the gate at all with a baseline of 0.70 / 0.77.** After must-fix 1 to 3 the baseline falls (case 2 stops giving 1.0 to every variant). No action beyond the assertions; recorded because the next measurement will show a lower baseline, which is the cases getting honest, not the models getting worse.

---

## eng-implement

Per case, with the skill (strong / floor): case 1 `0.8 x3` / `0.8, 1.0, 0.8`; case 2 `0.67, 1.0, 1.0` / `0.67, 1.0, 0.67`; case 3 `1.0 x3` / `0.67, 1.0, 1.0`. Floor mean 0.844. Eight of the nine with-skill failures are two assertions that fail good work.

### Must fix (would fail, mislead the score, or break a principle)

1. **Case 1, assertion 1, rests on self-report and fails runs that did the work** `[FFF | FPF | FFF | FFF]`: "scripts/task.py is run for T-cm-2 before any file is created and the task is marked in-progress". The floor transcripts show the three commands in order (`task.py --backlog docs/product/backlog.md --id T-cm-2`, then `--status in-progress`, then `--status done --note "..."`); the replies say what the template tells them to say (`SKILL.md:75`: "loaded with the task script; ...; marked in-progress before the first file was touched"), and the grader, rightly, does not accept a sentence. The template is the defect. Fixes:
   - Template line 75, replace with:
     `- Task: \`python3 <this skill's folder>/scripts/task.py --backlog docs/product/backlog.md --id <id>\` → \`"status": "<...>"\`, \`"dependencies": {<...>}\`, \`"dependencies_done": <true|false>\` (copied from its output)`
     `- Started: \`... --id <id> --status in-progress\` → \`<the line it printed, verbatim>\`, run before the first file was created or changed`
   - `scripts/task.py`: for `--status`, print one line that is easy to quote and that proves the order, for example `{"id": "T-cm-2", "status": "in-progress", "previous": "todo", "worktree_changes": []}` where `worktree_changes` is `git status --short` at that moment (empty when nothing was touched yet; `null` outside a git repository). This also makes `SKILL.md:51` true (see must-fix 3).
   - Assertion, new wording: "The reply quotes the task script's output for T-cm-2 (its command, and `\"dependencies\": {\"T-cm-1\": \"done\"}` or `\"dependencies_done\": true`), and the command that set T-cm-2 to in-progress with the line it printed, which shows no changed file at that moment".

2. **Case 2, assertion 1, asks for more than the skill and fails good outputs** `[FPP | FPF | FFF | FFF]`: "The reply names ADR-0002 as read before coding, and quotes verbatim the output of the task's Check run after the implementation". Step 6 (`SKILL.md:56`) says "copy verbatim the line of the Check's last run that shows the result (the runner's line with the passing count; when the check still fails, the failing line)". The three failed runs named ADR-0002 and quoted `ℹ pass 2` / `ℹ fail 1` and the failing test's line, which are the runner's own lines; the grader read "the output" as the whole output. New wording: "The reply names ADR-0002 as read before coding, and quotes the lines the task's Check printed after the implementation that show its result: node's `ℹ pass 2` and `ℹ fail 1`, or the `✖` line of the failing test".

3. **`SKILL.md:51` says `task.py` prints "the working-tree state"; it does not.** The script prints the id, the title, the fields, the status, the dependencies and `dependencies_done` (verified on the `versions` fixture). Either delete "and the working-tree state" or implement it as in must-fix 1; recommended: implement it, because it is the only evidence available for "before the first file was touched".

4. **`scripts/task.py:56-59` and `:66`: tracebacks instead of usage errors.** `--backlog`, `--id`, `--status`, `--note` given last without a value end in `IndexError`, exit 1 (known; confirmed); `--backlog <a path that does not exist>` ends in a `FileNotFoundError` traceback, exit 1 (not in the known list). Both must be exit 2 with a message on stderr ("Error: --id needs a value.", "Error: backlog not found: <path>"). Remove the `xfail` at `scripts/tests/test_task.py:104` and add the missing-file case. Other checks pass: `--help` 0; unknown option 2; a wrong `--status` 2; an unknown task prints the available ids and exits 1; 5 tests pass and 1 is the expected failure; standard library only.

5. **Frontmatter does not say what the procedure writes and reads** (`SKILL.md:18-19`). Written and not declared: `docs/engineering/adr/<NNNN>-<title>.md` (case 2: the task records the spike's outcome in ADR-0002, and all six with-skill runs changed that file). Read and not declared: `docs/engineering/adr/<NNNN>-<title>.md` (the report's "Read first" line names ADR sections) and `docs/product/specs/<feature>.md` ("Without a task id", line 67: "the specification or design that defines the behaviour"; case 3's cause is EDGE-3 of the specification). `docs/product/backlog.md` is a shared ledger written by `product-backlog` and updated here (the status line): move it to `updates`. `docs/engineering/plans/<task>.md` is read only.

### Should fix (quality, robustness)

1. **"Without a task id" (`SKILL.md:62-68`) describes its report in prose.** Case 3, assertion 2 ("The failing output is quoted and the cause is named") `[PPP | FPP | FFF | FFF]`: floor run-1 fixed the code and wrote "All 6 tests pass and lint is clean" with no failing line. Give the mode its own template under "Output template":
   ```
   ## Fixed: <check>
   - Task: no task id; check named by the user
   - Check: `<command>` → before: `<the failing line it printed, verbatim>`; after: `<the passing line, verbatim>`
   - Cause: <file:line, what was wrong, and what defines the right behaviour (specification id or design section)>
   - Files: <every file `git status --short` shows, and no other>
   - Test: <unchanged | changed, with the reason and the user's agreement>
   ```

2. **Case 2 separates only through assertion 1.** Assertion 2 ("A failed assumption is reported as a finding and recorded in the ADR, not silently worked around") passes in all twelve runs: CONTENT, the task itself tells every model to record the outcome in the ADR; replace with "docs/product/backlog.md carries a status line for T-cm-4 with the Check's result (`2 passed, 1 failed` or the runner's lines)" (present in all six with-skill runs and in the three strong baseline runs, absent in the three floor baseline runs) and add "The reply asks the user to choose between option B and option C before any other file changes, with a recommended answer" (the `expected_output` says "asks before switching to option C" and no assertion checks it). Assertion 3 ("No file outside the task's Touches list is modified ...") passes in all twelve: GUARD, keep, reworded "The files the run produced or changed are no others than app/components/example.ts, docs/engineering/adr/0002-example-block-source.md and docs/product/backlog.md".

3. **Case 3: assertions 1 and 3 pass in all twelve runs** ("The test is not edited to make it pass without an explanation and the user's agreement", "The change is confined to the code under test or the test, never both silently"). GUARDs: keep one, verifiable ("tests/unit/validate.spec.ts is not among the files the run produced or changed"), and replace the other by content the skill adds: "The reply names the cause with its file and line in app/validate.ts (`>=` where the limit of 160 is allowed) and cites EDGE-3 of the specification as what defines the right behaviour".

4. **Case 1: assertion 4 passes in all twelve runs** (GUARD on scope, keep). Assertion 5 ("The task is marked done with the check summary and no git commit is executed") is half unverifiable; new wording: "docs/product/backlog.md carries `Status: done` for T-cm-2 with the check's result, a commit message is proposed, and the reply does not report a commit".

5. **No case for the stop gates.** Step 1: "If a dependency is not done, stop and say which"; "When not to use": a task without a check. Add a fourth case on the `versions` fixture: prompt "Implement T-cm-3." (it comes after T-cm-2, which is `todo`); assertions: "The reply quotes the task script's output showing T-cm-2 is not done (`\"dependencies_done\": false`) and stops", "No file is among the files the run produced or changed". The fixture already supports it: `docs/product/backlog.md:36` reads `Depends on: T-cm-2`.

6. **Step 3 gate (`SKILL.md:53`) does not say that nothing is written before the answer nor that "go" is not one.** Proposed: "... otherwise stop and ask before writing any code, with a recommended answer; write nothing until the user answers, and `go` or `proceed` is not an answer to a question that has options."

7. **Step 7 (`SKILL.md:57`) and the quality criterion at line 92 assume `git status --short` shows only project files.** In every eval run it also shows the folder the adapter copied the skill into (`?? .claude/` or `?? .agents/`), and the replies explain it ("`.agents/` ... predates this work"), which puts a harness path into the report. The fix is in the runner (Patterns, item 3). In the skill, one sentence is enough and harness-neutral: "A folder that was untracked before step 1 (`task.py` lists it under `worktree_changes`) is not part of the change: name it once as pre-existing."

8. **Description (`SKILL.md:3-13`) misses the hand-off from a review.** eng-code-review ends with "Next: eng-implement for #..." and this description names a backlog task, a fix with a cause, a failing test and a small change. Add "or one finding of a code review (`docs/engineering/reviews/<change>.md`)" and the input. 924 characters today: trim "It reads the task, the design contracts and the conventions before touching a file," to make room.

9. **`scripts/task.py:49-51`: usage on stdout with exit 2**; and the error object for an unknown task goes to stdout with exit 1 (acceptable as data; say so in `--help`). The id pattern at line 28 accepts lower-case abbreviations only (`T-[a-z0-9]+-\d+`); `product-backlog` writes them that way, so no change, but `--help` should say it.

### For the maintainer to decide

1. **What status a task gets when its Check still fails.** Case 2: five of six with-skill runs marked the spike `done` with "2 of 3 pass", one marked it `blocked`; the quality criterion (line 96) says "The backlog task carries `Status: done`", the Purpose says done-ness "is proven by the task's own check", and `references/proof.md` only covers a check that cannot run (`in-progress`). The spike's `Does:` makes the recorded outcome the deliverable, so `done` is defensible there. Recommended rule for step 8: "`done` only when the Check passes, or when the task's `Does:` makes a recorded result the deliverable (a spike) and the note says the result; otherwise `blocked` with the failing line." Then assert the status in case 2.
2. **Gotchas lines 107 and 108 tell one incident with tool names** ("a `BroadcastChannel` created at component setup ... a static-site generate command", "`pkill -f "bun run generate"` killed the shell ... `pkill -f "bin/nux[t] generate"`"). The lessons are good and no project is named; the commands name real tools. Recommended: keep the lessons, replace the commands by `<runner> <script>` forms.
3. **Fixtures say `Current flow: flow-new-feature`** (`evals/files/*/docs/workbench/state.md`), a flow that D12 marks as planned. Recommended: `Current flow: none`, as in eng-codebase-map's fixture.

Fixtures verified in the audit (Node 24.10, copies): `versions` check fails with `ERR_MODULE_NOT_FOUND` before the task and the lint passes; `example-block` spike test is 1 pass / 2 fail before the task and its lint passes; `validate-docs` is 6 pass before the setup command. They are small real projects; names are fictional (Fernleaf UI).

---

## eng-integration-tests

Per case, with the skill (strong / floor): case 1 `0.86, 1.0, 1.0` / `0.86, 0.86, 0.86`; case 2 `1.0 x3` / `1.0 x3`. Two cases only. Every with-skill failure is one assertion.

### Must fix (would fail, mislead the score, or break a principle)

1. **Case 1, assertion 6, fails four of six good runs and passes the baseline** `[FPP | FFF | PPP | PFP]`: "src/due.js and src/index.js are unchanged". `git status --short` in all six with-skill case folders shows only the plan and the new test files (and a `fixtures/` folder in two); `src/` is untouched in every one. The grader cannot see an unchanged file ("Nothing positively shows that src/due.js and src/index.js are unchanged"). This single assertion is the whole distance between the floor's 0.86 and 1.0 on the case. Fixes: `"grader_files": ["src/due.js", "src/index.js", "releases/1.2.0/src/due.js", "AGENTS.md", "docs/engineering/plans/due-label-customer-time-zone.md"]`; new wording "Neither src/due.js nor src/index.js is among the files the run produced or changed"; the same for case 2's assertion 3 ("src/ is unchanged" → "No file under src/ is among the files the run produced or changed"); and the "Working tree" line of must-fix 3.

2. **Case 1, assertion 7, is a language assertion that passes in all twelve runs.** Remove.

3. **The skill has no template for the reply, and the plan template quotes no command and no output.** `SKILL.md:67-74`: "runtimes: <list>: <n> passed", "new behaviour <n> failed (<names>)", "`<command>`: <result>". Stop rule 3 says "report the counts it printed". Replace the three lines with:
   ```
   - With the change: `<command>` → `<the runner's count lines, verbatim, for example "ℹ pass 6" "ℹ fail 0">`
   - Against the code before the change (<base commit | previous release path>, scratch copy at <path>, removed): `<command>` → `<count lines, verbatim>`; failed there: <names of the new-behaviour tests>; passed there: <names of the preserved-behaviour tests>
   - Full check with the change: `<command>` → `<its result line, verbatim>`
   - Working tree: `git status --short` → `<its output, verbatim>`
   ```
   and add a chat template `## Integration tests: <task>` with the same four lines and `- Test files: <paths>`. Then sharpen assertions 3 to 5: "The reply or the plan quotes the command run against releases/1.2.0/src with the runner's count lines and names the tests that fail there", "The reply or the plan quotes `npm test` with its count lines for the change", "The plan's 'Integration tests' section carries both runs with their counts".

4. **Step 5 (`SKILL.md:59`) has the scratch recipe that misfired in eng-code-review**: `scratch=$(mktemp -d)`, then `git worktree add "$scratch" <base>` as separate commands. A failed first command leaves the variable empty and the next commands act on the project (eng-code-review must-fix 2, with the transcript). Same fix: one chained command that prints the path, the literal path afterwards, "never run a command with an empty path", and `git worktree list` quoted at the end (quality criterion line 84, "No scratch worktree ... is left behind", has no evidence today).

### Should fix (quality, robustness)

1. **Case 1, assertion 2, passes in all twelve runs**: "The tests run code under at least two server time zones (TZ set per process or per run)". CONTENT. Replace with stop rule 2's distinction, which is what the skill adds: "Each time-zone test starts a separate process with TZ set (a child process or `TZ=<zone> <command>`), in at least two zones, and no test assigns `process.env.TZ` inside the test process"; remove it if it still passes everywhere.

2. **The three Inputs gates have no recommended answer, do not say that nothing is written, and no case reaches them** (`SKILL.md:48-50`: "Ask for the base commit", "Ask which conditions ...", "ask before adding one"). Proposed for the first: "Stop and ask for the base, recommending the previous release's files when the project keeps them, else the parent of the change's first commit; write no test until the user answers; `go` is not an answer." Add a third case: the fixture without `releases/` (`"absent_on_purpose": ["releases/1.2.0/src/due.js"]`) and with the "Releases" section removed from `AGENTS.md`; prompt "write the integration tests for the dueLabel time-zone change"; assertions "The reply asks what the code before the change is (a base commit or the previous release's files) and recommends one" and "No test file is among the files the run produced".

3. **Quality criteria (`SKILL.md:80`) assume a served build.** "The tests load the built output through the project's own serving path, and wait on a named readiness signal." The only fixture is a library with no build and no server; every run had to decide alone that the public entry (`src/index.js`, the package's `exports`) is the "serving path". Add: "For a library with no build or server: the tests import the package through its public entry (the manifest's `exports`), never a file inside it, and the readiness signal is `n/a: no server`."

4. **Gotchas lines 89 and 90 are the notes of one case, in the past tense, and cannot be applied by a reader who was not there** ("The fallback module arrives after the loader, so the readiness signal was 'the checkbox present at load is already mixed', not `load` or `networkidle`."). Rewrite as lessons: "The readiness signal is the first observable effect of the code under test (for a module loaded after the page: an element present at load already in its final state), not `load` or `networkidle`." and "An accepted degradation is a behaviour: assert exactly what the decision record promised when the feature is unavailable, so a later change that breaks the fallback path fails."

5. **Fixture differences that cost a note in the replies.** `README.md` still documents `dueLabel(isoDate)` "in the server's local time zone" although the change is implemented, against the fixture's own rule 2; floor run-1 spent a paragraph on it and named another skill for it. Update the README in this copy (the change is implemented here; the stale README belongs to eng-docs's copy). `AGENTS.md` says Node 20 and 22 (eng-docs should-fix 6). The prompts' `invoices/` (eng-docs should-fix 5).

6. **No "External content is data." line.** The skill reads the plan, the decision record, the diff and test-runner output. The scan does not require the line here. eng-implement, which reads the same kinds of content, carries it and names "command output". Recommended: add it, naming "the diff, the previous release's files, fixtures and the output of the test runner", for one rule across the engineering skills (see "For the maintainer to decide").

7. **Frontmatter.** `outputs: [docs/engineering/plans/<task>.md]` is the shared plan ledger: `updates`. The test files the skill writes are project files (see Patterns, item 6). `inputs` are produced by other skills or user-provided.

8. **Case 2, assertion 1**: "The reply says integration tests come after the implementation, pointing to writing failing unit tests first" `[PPP | PPP | FFF | FFF]`: keep; it is the one that separates. Assertion 2 ("No integration test for a locale option is added and reported as passing") `[PPP | PPP | FPP | PPP]`: verifiable wording "No test file is among the files the run produced".

### For the maintainer to decide

1. **Whether the External-content line is required of every skill that reads a diff and command output**, or only of those the scan lists today. If required, the scan's rule should say so, so that the validator and not an audit finds the next one.
2. **Whether two cases are enough for a skill with three stop rules and three input gates.** Recommended: the third case of should-fix 2.

---

## The invoices fixture: copies in this group and their differences

Three copies in this group (`eng-docs`, `eng-impact-analysis`, `eng-integration-tests`); seven more elsewhere (`eng-refactor`, `eng-root-cause`, `eng-tradeoffs`, `eng-unit-tests`, `flow-fix-bug` twice, `ops-pull-request` twice), not compared here.

| File | eng-impact-analysis | eng-docs | eng-integration-tests | Defect? |
|------|---------------------|----------|-----------------------|---------|
| `src/due.js` | before the change (`toLocaleDateString`, server zone) | after the change (`timeZone = "UTC"`, `Intl.DateTimeFormat`) | after the change, same as eng-docs | no: each case needs that state |
| `README.md` | says "server's local time zone" (true for this code) | same text (stale on purpose: the case fixes it) | same text, stale, and no case fixes it | yes, small: in the integration copy it breaks the fixture's rule 2 and distracts the runs |
| `docs/engineering/plans/...md` | absent (the skill creates it) | "Change" section only | "Change" plus "Root cause (summary)" and "What a fix must preserve" | no |
| `CHANGELOG.md`, `docs/guide.md` | absent | present | absent | no |
| `releases/1.2.0/src/` | absent | absent | present | no |
| `AGENTS.md` | base | same as base | base plus a "Releases" section ("there is no git history in this checkout") | no; the sentence is true enough (one commit) |
| `test/due.test.js`, `package.json`, `scripts/size.mjs`, `src/index.js` | identical in the three | | | no |
| `AGENTS.md` "Supported runtimes: Node 20 and 22" | all three | | | yes: the container has Node 24.10 only |

`npm run size` prints `src/ 307 B gzip (budget 1024 B)` on the before-the-change copy and `src/ 397 B gzip (budget 1024 B)` on the two after-the-change copies (Node 24.10). `npm test` on the before-the-change copy passes only in UTC.

---

## Patterns

1. **Assertions about what did not change fail good runs, because the grader sees only produced or changed files.** "X is unchanged", "no source file is modified", "the file is deleted", "only file Y was produced": eng-integration-tests case 1 (4 of 6 with-skill runs failed, 5 of 6 baseline runs passed), eng-code-review case 1 (3 of 6), eng-docs case 1 (1 of 6), eng-codebase-map case 1 (1 of 6), eng-architecture case 3 (1 of 6, a deletion). In every one the case folder's `git status --short` shows the run was right. Three-part fix, the same everywhere: the skill's report quotes `git status --short` verbatim; the case lists the guarded files in `grader_files`; the assertion says "is not among the files the run produced or changed".

2. **Report templates state that something was done instead of quoting it.** eng-implement line 75 ("loaded with the task script; ... marked in-progress before the first file was touched"), eng-code-review line 83 ("tests <n passed, n failed>"), eng-codebase-map line 89 ("Working tree: unchanged except the map"), eng-integration-tests lines 71 to 73, eng-impact-analysis line 74, eng-docs (no place for the runs). Where an assertion asks for the evidence it fails (eng-implement case 1 assertion 1: 5 of 6; eng-code-review case 3 assertion 3: 5 of 6); where it does not, it passes on a sentence. Every template line for a script or a check should read: the command, an arrow, the line it printed, verbatim. eng-architecture already does this and is the model to copy, with the "never write `same`" sentence added.

3. **The folder the adapter copies the skill into shows in `git status --short`** (`?? .claude/`, `?? .agents/`) in every case folder, and the replies mention it. Once reports quote `git status --short` (pattern 1) this puts a harness path into every graded reply. Fix outside the skills: after `isolate_git`, the runner (or each adapter) appends the adapter's folder to `.git/info/exclude` of the case folder. No skill hash changes.

4. **Fixture copies take whatever is on the disk.** `eval_run.py:447` copies a `files` folder with no ignore pattern, while `workbench_files` (line 440) ignores `__pycache__`, `*.pyc` and `.DS_Store`. eng-code-review's three fixtures hold untracked `.pyc` files on the maintainer's machine. Give the fixture copy the same ignore patterns, and delete the files.

5. **A scratch copy made by separate commands with a shell variable is unsafe** (eng-code-review step 1 and its checklist, eng-integration-tests step 5; one floor run reverse-applied a patch onto the project). One chained command that prints the path; the literal path afterwards.

6. **`outputs` cannot express two things these skills do.** (a) Shared ledgers that several skills append to or update: `docs/engineering/plans/<task>.md` (eng-docs, eng-impact-analysis, eng-integration-tests here; nine skills in the repository), `docs/product/backlog.md` (eng-implement), `docs/workbench/state.md` (eng-architecture and eng-codebase-map write it and declare it only as an input). These go to the new `updates` field. (b) Project files that are the work itself: source and tests (eng-implement, eng-integration-tests), documents (eng-docs). They are not artifacts with a path pattern; decide once whether the contract names them (`writes: [project source]`) or leaves them out on purpose and says so.

7. **Language assertions**: six in this group, all passing in all twelve runs (eng-architecture 2.3, eng-code-review 4.4, eng-codebase-map 2.4, eng-docs 1.8, eng-impact-analysis 1.8 and 3.3, eng-integration-tests 1.7). Remove all.

8. **Cases whose score is the same in every variant.** eng-impact-analysis case 2 (1.0 everywhere), eng-code-review case 3 (0.75 everywhere), and most of eng-implement cases 2 and 3 (0.67 baseline, one assertion separating). Replacement assertions are given per skill, each chosen from a difference seen in the evidence between runs with and without the skill (an artifact file written, an output line quoted, a masked secret, a reproduction run).

9. **Stop gates work when they are "Stop rules" above the procedure and fail when they are a clause inside a long step.** eng-docs, eng-impact-analysis and eng-integration-tests carry the section and their stop cases pass in every floor run; eng-code-review has the rule inside step 1 and its stop case fails in two of three floor runs. Across the group the gates also lack two things AGENTS.md asks for: a recommended answer (eng-impact-analysis stop rule 1, eng-docs and eng-integration-tests Inputs) and the sentence that "go" or "proceed" is not an answer and nothing is written before one.

10. **Scripts.** Three of five scripts in the group end in a traceback when a flag comes last without its value (`change_scope.py`, `map_codebase.py`, `task.py`; `check_design.py` and `redact.py` are right), two of them also on a non-integer, and `task.py` on a missing backlog file. All four argument parsers print the usage to stdout on a usage error. Two of four `SKILL.md` files do not say that the script is in the skill's folder (eng-architecture, eng-code-review). `patch` is not in the image; nothing else a skill of this group prescribes is missing there.

11. **Real-case residue.** Gotchas of eng-docs (lines 97 to 98), eng-impact-analysis (lines 112 to 115, with numbers), eng-integration-tests (lines 89 to 90) and eng-implement (lines 107 to 108) read as the record of one project's bug fix rather than as lessons. No project, person or account is named, and the private-terms check passes; the numbers and the quoted rules are the part principle 8 excludes. One fictional-name defect: `STRIPE_KEY` and `payments.internal` in eng-code-review's `secret` fixture. `evals/result.json` of every skill names the harness and the models; it is generated and exempt from the validator's harness check, which is worth one sentence next to principle 1.

12. **The fixtures say "Node 20 and 22" and the image has Node 24.10.** Several runs report runtimes they could not exercise. One line in each copy of the invoices `AGENTS.md`.
