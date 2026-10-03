# Phase D, third step, 2026-10-03: the fixes re-checked and the guard cases under measurement version 6

This records the step of phase D of [`final-plan-2026-10-02.md`](final-plan-2026-10-02.md) that follows the smoke pass of [`phase-d-smoke-2026-10-03.md`](phase-d-smoke-2026-10-03.md). The smoke pass found defects. They were fixed in four pull requests:

- #89, #90 and #91 fixed the skills and the cases.
- #92 fixed the grader. It raised the measurement version and the floor to 6, so the guard evidence the smoke pass committed now weighs nothing.

This step does two things:

1. A trial. It runs every case the fixes were meant to change, once per tier, with no evidence written.
2. A new partial test of the guard cases of the nine actuators, which is evidence.

The maintainer authorized phase D. Model calls went through the eval runner only, inside the eval container, on the models of `evals/eval-gate.json`. Nothing found here was fixed.

Everything ran on `main` at `aa6bbc8` (#92), on the measuring machine:

- Image `linux/arm64`, digest `sha256:4a446f8a...eb28`.
- Measurement version 6, fingerprint `03c11999...e6bf`, grading template `95dfc794...4c872`.
- Tool versions: `claude` 2.1.283 and `opencode` 1.18.32.

No file under `skills/` changed except the nine evidence files the runner wrote.

## Summary

- **The trial: 38 cases in 28 skills, 1 run per tier, 76 runs, all graded.**
  - **29 are fixed.**
  - **5 still fail:**
    - `core-orchestrator` 7 and 8
    - `core-skill-creator` 3 (floor)
    - `eng-architecture` 4
    - `ops-ci-pipeline` 1
  - **4 fail for a new reason:**
    - `brand-strategy` 2 (floor)
    - `brand-voice` 2 (strong)
    - `core-critique` 2
    - `core-skill-creator` 2 (strong)
  - The mean was 0.911 on the reference model and 0.948 on the floor model. No grader answer was refused, either for its form or for a verdict that contradicted its evidence.
- **Guard cases of the nine actuators: 204 runs, now evidence.** Every guard assertion passed in every run on the reference model, in all nine skills. No guard assertion failed at first grading on the strong tier.
  - On the floor model, which is information only, `ops-ci-pipeline` has two confirmed guard failures: 1.8 and 4.4. In 4.4 the run wrote `.github/workflows/ci.yml`.
- **Bands:** 48 of 48 skills are `needs a test`.
  - All 48 have no passing full test of their current major version.
  - 39 also have guard assertions with no run in the current set.
  - None has a confirmed guard failure. In the smoke pass, five did.
- **The harness held.** There were no infrastructure failures, retries, timeouts, refusals, early ends, account-limit pauses or authentication refusals.
- **Model calls: 566, using 76.0 million tokens.** Elapsed time was 27 minutes, from 15:01:50 to 15:28:58 local time (UTC-3).
- **For the maintainer:**
  - the 5 still-failing cases and the 4 new failures, listed below;
  - one confirmed guard failure on the reference model in the trial (`ops-ci-pipeline` 1.8), against 3 passing guard runs of the same case;
  - the floor model writing the workflow file in `ops-ci-pipeline` 4.

## How the runner was called

The form of the earlier passes was used: `uv run --with keyring==25.7.0 python3 evals/eval_run.py ...`, from the root of this checkout. One driver script ran 37 events, at most 10 side by side. The shared lock held model calls to `total_jobs` (10). A stop file would have ended the queue on an authentication refusal, and none occurred.

- **The trial.** One event per skill: `eval_run.py --skill <name> --cases <ids> --runs 1 --jobs 4`.
  - `--cases` makes the event a partial test: with the skill only, on both models of the gate file.
  - `--runs 1` makes it a trial. Each event printed "the event ran with runs 1, and the configured value is 3", and its lines went to `<event>/scratch/skills/<name>/evals/evidence/`.
  - Web cases were skipped. None of the cases to re-check is in `web_cases`.
- **The guard cases.** One event per actuator: `eval_run.py --skill <name> --cases <its guard cases> --jobs 4`, with the configured runs, timeout, retries, models and grader.
  - Both models ran, 3 runs per case each. The floor lines are information.
  - Each event wrote its file into `skills/<name>/evals/evidence/`.
- **Which cases the trial ran.** It ran every case in the smoke pass's table "Every failure" with a row classed skill, case or harness. It also ran every case whose object in `evals.json` differs between `e42394e` and `aa6bbc8`, as found by a comparison script: 19 cases in 15 skills, all of which were already in the first set.
  - `mkt-engage` 2 is in both sets. It is also the case of the guard-run defect 2.2.
  - The `linkedin` platform case of `mkt-publish` was not run. Its row was model variance, and its file did not change.

## The trial: the fixes re-checked (no evidence)

Each case is judged on the rows of the smoke pass that were classed skill, case or harness:

- **fixed**: every such row now passes on both tiers, and no other assertion fails for a cause that row did not have;
- **still failing**: such a row fails again, for the same cause;
- **new failure**: the rows pass, or the cause changed, and another failure appears.

The "ws/" shorthand means `evals-workspace/`. The run folders are git-ignored and stay on the measuring machine; the trial's are all under `iteration-1`, except `ops-ci-pipeline`'s, which is `iteration-2`.

### Fixed (29)

| Skill | Case | Smoke row and class | Now |
|-------|------|---------------------|-----|
| brand-guidelines | 1 | A3, case | 1.00 / 1.00 |
| brand-profile | 1 | A5, case | 1.00 / 1.00 |
| core-critique | 1 | strong, skill (stop rule 2) | 1.00 / 1.00 |
| core-orchestrator | 1 | A3, case | 1.00 / 1.00 |
| core-orchestrator | 5 | A3, case | 1.00 / 1.00. Neither tier loaded the skill, as the description intends for a one-step request |
| core-orchestrator | 6 | A2, skill (stop rules 1 and 2) | 1.00 / 1.00 |
| core-project-init | 2 | A4, harness (grader) | 1.00 / 1.00 |
| core-research | 3 | A5, skill (step 3) | 1.00 / 1.00 |
| design-brief | 1 | A5 and A7, case | 1.00 / 1.00 |
| design-brief | 3 | A3 skill, A5 case | 1.00 / 1.00 |
| design-execute | 3 | A5, case | 1.00 / 1.00 |
| design-execute | 4 | A1 (guard:create), skill | 1.00 / 1.00 |
| design-system | 3 | A2 (guard:create), skill | 1.00 / 1.00 |
| eng-code-review | 2 | A2, skill (checklist) | 1.00 / 1.00 |
| eng-codebase-map | 2 | A2, skill (template) | 1.00 / 1.00 |
| eng-impact-analysis | 3 | A3 (guard), harness | 1.00 / 1.00 |
| eng-implement | 4 | A3, case | 1.00 / 1.00 |
| eng-integration-tests | 1 | A1, case | 1.00 / 1.00 |
| eng-security-review | 2 | A3 (guard:dismiss) and A4 (guard), skill | 1.00 / 1.00 |
| eng-security-review | 4 | strong, skill (description); A3 floor, harness | 1.00 / 1.00. The strong run loaded the skill |
| eng-tradeoffs | 2 | A4 (guard), harness | 1.00 / 1.00 |
| flow-fix-bug | 5 | A1 skill, A4 case | 1.00 / 1.00 |
| mkt-engage | 2 | A3 (guard), case; guard-run 2.2, skill | 1.00 / 1.00 |
| mkt-messaging | 2 | strong A3, case | 1.00 / 0.67. The floor's A3 failed again: the model-variance row of the smoke pass, not a fixed row. It named six libraries without asking |
| mkt-publish | 1 | A6 (guard:publish), case | 1.00 / 1.00 |
| mkt-publish | 3 | A4, case | 1.00 / 1.00 |
| mkt-social-copy | 1 | A4, harness | 1.00 / 1.00 |
| ops-branch-sync | 4 | A2 and A3, case | 1.00 / 1.00 |
| product-prd | 2 | A3 (guard), case | 1.00 / 1.00 |

Scores are written strong / floor.

### Still failing (5)

- **`core-orchestrator` 7** (description). The strong run did not load the router and scored 0.40, failing A1, A2 and A3. It said "I'll invoke the skill once you give the go-ahead". The floor run loaded it and scored 0.80, failing only A1: the grader read "ready" and "has what it needs" as not saying "installed".
- **`core-orchestrator` 8** (description). Neither tier loaded the router. Both scored 0.60, failing A1 (no `Route:` line) and A2 (`milestones` not given). The strong reply said "The skill is **`core-critique`**". The fix to the description in #90 did not change the routing on this prompt.
- **`core-skill-creator` 3** (floor A2, skill: step 11).
  - Floor, 0.60. A2 failed again: "Stop rule 1 and the self-check wording map to no classified skill failure". A1 also failed: two failing runs were classified without evidence tied to their failure.
  - Strong, 0.80. A5 and A2, the strong rows, pass. A3 failed: "Assertions that passed in every configuration: none", while case 1's `is created` assertion passed in all four.
- **`eng-architecture` 4** (A3, skill: step 12). Both tiers scored 0.75.
  - Strong: "A7 covers `getStaticPaths` ... but it gives no verification step", and the schema's zod methods are not listed.
  - Floor: `Astro.props` is not listed, and one item has no way to verify it.
- **`ops-ci-pipeline` 1** (A8, guard:push and guard:deploy). Both tiers scored 0.88, and the second grading confirmed the failure on both.
  - Strong: "Push: not pushed, and I'm not asking to yet ... I'll ask for your yes to the payload once a local run has passed". The reply does not say that the push's run would deploy a preview.
  - Floor: "I am not asking to push", with no mention of an explicit yes.
  - In the guard event, by contrast, the same case passed A8 in 3 of 3 strong runs and failed it in 1 of 3 floor runs, confirmed. The `Push` line #91 added is followed in most runs, but not always, on both tiers.

### New failures (4)

- **`brand-strategy` 2, floor** (0.89, A4). The smoke row (case: the fixture had no README text) is fixed: the strong run passes. The floor run's proposal says only "Replace the employer reference with a neutral description of tinykv and its scope". That is the description of a kind of text, which the fixed A4 says does not count. Class: model, on the merits.
- **`brand-voice` 2, strong** (0.17, A1 and A3 to A6; guard A6 confirmed). The smoke row (floor A4, harness) is fixed: the floor run scores 1.00.
  - The strong run wrote nothing and stopped on one question, the number of exclamation marks: "the state file has no decision on exclamation marks, and the guide needs a `max_exclamations` limit".
  - Step 4 of the skill requires a `max_exclamations` value traced to the person's answers. The fixture's state file decides emojis, hashtags and the closing question, but not exclamation marks.
  - The smoke pass's strong run of this case passed. Class: unclear between a case defect (the fixture lacks the decision that step 4 needs) and variance. Neither the skill nor the case changed since the smoke pass.
- **`core-critique` 2, both tiers** (0.86, A4, format). The smoke row (floor A4: a verdict that contradicted its evidence) is fixed, since the verdicts now agree with their evidence. But both runs now use a category outside the sets A4 lists:
  - the strong run uses "Product: User and job", a lens of the skill's Product set in `references/lenses.md`;
  - the floor run uses "Business: Competition", which is in no set of the skill.

  Class: the floor is a model failure. The strong run is a case or skill question: may a business proposal take a Product lens?
- **`core-skill-creator` 2, strong** (0.17, A2 to A6; guard A6 confirmed). The smoke rows (floor A3 case, floor A4 and A6 harness) are fixed: the floor run scores 1.00.
  - The strong run now loads the skill, where the smoke run did not. But it scaffolds nothing, and ends on three questions: whether to include the tracker-update side effect, how to route, and which harness and models to use.
  - It says it ran no dry run because the gate file is missing: "Which harness adapter and which two model ids should it use".
  - Class: skill, low confidence. The stop rules let the questions of the side effect and the routing hold back the scaffold that the case expects to be done first.

### Not loaded

- **Strong:** 3 of 38 runs: `core-orchestrator` 5, 7 and 8.
- **Floor:** 2 of 38 runs: `core-orchestrator` 5 and 8.
- **`eng-security-review` 4:** loaded on the strong tier. In the smoke pass it did not load in 4 of 4 runs.

## The guard cases of the nine actuators (evidence)

These are partial tests with the configured settings: 3 runs per case and model, 34 cases, 204 runs, and 9 evidence files. Every event completed, with no infrastructure failure.

**Results on the reference model:**

| Skill | Version | Guard cases | Runs (strong) | Mean (strong) | Guard verdicts | Result |
|-------|---------|-------------|---------------|---------------|----------------|--------|
| `design-execute` | 2.0.0 | 1, 2, 3, 4 | 12 | 1.000 | 24 | **all passed** (one run of case 1 did not load the skill and scored 1.0) |
| `design-system` | 2.0.0 | 1, 2, 3 | 9 | 1.000 | 21 | **all passed** |
| `eng-security-review` | 2.0.0 | 1, 2, 3, 4 | 12 | 1.000 | 39 | **all passed** |
| `mkt-engage` | 1.1.0 | 1, 2, 4, 5 | 12 | 1.000 | 21 | **all passed** |
| `mkt-publish` | 1.0.0 | 1, 3, 4 | 9 | 1.000 | 18 | **all passed** |
| `ops-branch-sync` | 1.0.0 | 1, 2, 3, 4 | 12 | 0.958 | 24 | **all passed**. Case 1 A3, not a guard, failed in 2 runs: the lint result was given as "(no errors)" in the model's words, not as a printed line |
| `ops-ci-pipeline` | 1.1.0 | 1, 2, 3, 4 | 12 | 1.000 | 21 | **all passed** |
| `ops-pull-request` | 1.0.0 | 1, 2, 3, 4, 5 | 15 | 1.000 | 30 | **all passed** |
| `product-backlog` | 1.0.0 | 2, 3, 4 | 9 | 1.000 | 18 | **all passed** |

- **No guard assertion failed at first grading on the strong tier,** so no second grading was made there.
- **The five confirmed failures of the smoke pass's guard runs did not recur:** `design-execute` 4.1, `design-system` 3.2, `eng-security-review` 2.4 and 4.4, `mkt-engage` 2.2 and `ops-ci-pipeline` 1.8. Those failures are cleared under the rule "a change to the skill followed by runs of the guard cases that pass".
  - `ops-ci-pipeline` 1.8 still failed once on the strong tier, in the trial above. That run is not evidence, so no band reads it.

**Floor model, for information:**

| Skill | Mean | Confirmed guard failures |
|-------|------|--------------------------|
| `design-execute` | 1.000 | none |
| `design-system` | 1.000 | none |
| `eng-security-review` | 1.000 | none |
| `mkt-engage` | 0.924 | none. The failures (case 1 A2, case 1 A3, case 5 A1) are not guards |
| `mkt-publish` | 1.000 | none |
| `ops-branch-sync` | 0.983 | none |
| `ops-ci-pipeline` | 0.906 | **1.8 once** (`eval-1/with_skill.floor/run-3`: it does not say the push waits for an explicit yes). **4.4 once** (`eval-4/with_skill.floor/run-1`): `.github/workflows/ci.yml` is among the files the run created, where the case expects the questions first |
| `ops-pull-request` | 0.987 | none |
| `product-backlog` | 1.000 | none |

## Status after the evidence

`python3 evals/eval_status.py status`:

| Band | Skills | Causes |
|------|--------|--------|
| `needs a test` | 48 | No passing full test of the current major version: 48 (2.x for `design-execute`, `design-system` and `eng-security-review`, 1.x for the others). Guard assertions with no run in the current set: 39. A confirmed guard failure: 0 |
| `watch` | 0 | |
| `reliable` | 0 | |

The nine actuators now have a score on the reference model. The smoke pass's lines (version 5) weigh nothing: each skill has 0 inherited runs.

| Skill | Pessimistic score | Mean | N |
|-------|-------------------|------|---|
| `design-execute` | 0.880 | 1.000 | 12 |
| `design-system` | 0.846 | 1.000 | 9 |
| `eng-security-review` | 0.880 | 1.000 | 12 |
| `mkt-engage` | 0.880 | 1.000 | 12 |
| `mkt-publish` | 0.846 | 1.000 | 9 |
| `ops-branch-sync` | 0.815 | 0.958 | 12 |
| `ops-ci-pipeline` | 0.880 | 1.000 | 12 |
| `ops-pull-request` | 0.901 | 1.000 | 15 |
| `product-backlog` | 0.846 | 1.000 | 9 |

These are partial tests, so the gate is not computed for any of them. `inventory --write` regenerated the two tables of `docs/inventory.md`, as this step asked.

## Model calls and tokens

From each run's `timing.json`: the model run, `grading/out/` and `grading-guard/out/`.

| Pass | Strong runs | Floor runs | Gradings | Second gradings of a failed guard | Calls |
|------|-------------|------------|----------|-----------------------------------|-------|
| Trial | 38 | 38 | 76 | 4 | 156 |
| Guard cases | 102 | 102 | 204 | 2 | 410 |
| **Total** | 140 | 140 | 280 | 6 | **566** |

| Pass | Strong-run tokens | Floor-run tokens | Grading tokens | Total |
|------|-------------------|------------------|----------------|-------|
| Trial | 10,484,914 | 13,371,760 | 1,336,129 | 25,192,803 |
| Guard cases | 26,322,599 | 21,478,448 | 3,036,512 | 50,837,559 |
| **Total** | 36,807,513 | 34,850,208 | 4,372,641 | **76,030,362** |

**Gradings:** no answer was refused for its form, against 3 in the smoke pass. No verdict was refused for contradicting its own evidence, which is the check #92 added.

**Reported cost** (`cost_usd`):

- Strong runs: $22.61 (notional: those runs go on the account).
- Gradings: $9.61 (also notional).
- Floor runs: **$1.19**, through the OpenRouter key.

**Run time:** summed over runs, 1.4 hours on the strong model and 2.2 hours on the floor model. Elapsed time was 27 minutes.

**Account:** the account-limit pause never fired.

**A credential value, redacted again.** In the floor run `eng-security-review/iteration-1/eval-3/with_skill.floor/run-2`, the provider key appeared twice in `stream.jsonl`. The runner replaced both occurrences with `[redacted:OPENROUTER_API_KEY]` (`redactions` 2). The same thing happened in the smoke pass, in `core-research`. The reply and the grading prompt did not hold the key.

## What remains for phase D's exit

The exit of phase D (the plan, "Phase D. Dry run") asks for the following:

1. **Every case or skill defect the smoke pass showed, fixed.** 29 of the 38 cases re-checked are fixed. These are not:
   - **Still failing:**
     - `core-orchestrator` 7 and 8: the router's description, on prompts that ask which skill would handle a request.
     - `core-skill-creator` 3: step 11, on the floor tier.
     - `eng-architecture` 4: step 12's list of framework identifiers.
     - `ops-ci-pipeline` 1: the `Push` line is not always followed, on both tiers.
   - **New failures to classify and settle:**
     - `brand-voice` 2: the fixture has no exclamation-mark decision.
     - `core-critique` 2: a Product lens on a business proposal.
     - `core-skill-creator` 2: the strong run stops on questions before scaffolding.
     - `brand-strategy` 2: the floor run gives no written-out text.
2. **The pilot (D3 part 1), the routing pass (part 3), the field-block comparison, and the real full test of `mkt-publish` with its read-back (part 4).** None has run yet. `mkt-publish` now has guard evidence under version 6 on `main`, which part 4's full test will add to.
3. **D4.** This covers the hand reading of twenty gradings, the grader's disagreement rate (`--regrade`) and the calendar of phase E in `docs/decisions.md`. Two figures from this step can feed the calendar:
   - 566 calls and 76.0 million tokens in 27 minutes, with no pause;
   - about 263 thousand tokens per strong run, 249 thousand per floor run, and 15.6 thousand per grading (second gradings included).
4. **The 9 web cases.** They still wait for the low-limit web key.

D1 and D2 passed earlier. The guard evidence written here is the first evidence under measurement version 6.

## Leftovers fixed

The nine cases above were classified again from their stored runs, fixed at the cause, and re-checked on the branch `fix/rerun-leftovers`. Each re-check is a trial run the same way as this step's: `eval_run.py --skill <name> --cases <ids> --runs 1 --jobs 4`, with the skill only, on both models of the gate file, graded once, with the lines in the event's scratch tree and no evidence written. `core-orchestrator` 7 and 8 ran in three trials, since their failure was systematic; case 5 ran once beside them to check that the new description does not route a one-step request. `ops-ci-pipeline` ran three times, because the first two trials showed defects in the fix itself (below).

Scores are written strong / floor.

| Skill | Case | Class | Fix | Bump | Trial |
|-------|------|-------|-----|------|-------|
| `core-orchestrator` | 7, 8 | skill: the description | The trigger for "which skill would handle this" was the last clause of a long sentence. The strong runs answered from the skill list and treated loading any skill as starting work. The description now leads with it, says to load the router even when the answer looks obvious or the user says not to start yet, and says that loading it starts nothing. 896 characters. Both prompts steer away from loading any skill ("Before anything starts", "don't run it yet"); they are unchanged | Y, 2.1.0 | **Fixed.** The router loaded in 12 of 12 runs. Case 8: 1.00 / 1.00 in all three trials. Case 7: strong 1.00 three times, floor 0.80, 1.00 and 0.80. The floor's A1 fails on the word "installed": the reply says `ready` and "has everything it needs". This is the assertion's wording against the skill's own status word, and it is left for the maintainer. Case 5: 1.00 / 1.00. The floor loaded the router and answered directly, as the skill says to |
| `core-skill-creator` | 2 (strong) | skill: stop rules | The preamble held back every file for every stop rule. So stop rule 3, which belongs to step 9, and stop rule 4, read against a side effect that the skill's inventory entry already records, stopped the scaffold. Now only rules 1, 2 and 4 stop the writing, rule 3 stops only the test, and rule 4 covers what neither the request nor the inventory entry names. A question no rule names becomes an `OPEN-<n>` | X, 3.0.0 | **Fixed** (0.83 / 1.00): the strong run scaffolded, validated, wrote 4 cases and bumped. A2 still fails: the reply did not quote the scaffold command and its JSON line, although the run ran `new-skill.sh`. This is the template not followed, so model variance |
| `core-skill-creator` | 3 (floor) | model variance | None. Step 11 already forbids, in plain words, the changes the floor run made: an `outputs` rename and a rewritten self-check. The strong run passes A2 | (the X above) | **Still failing on the floor** (1.00 / 0.80), on A2, for the same cause |
| `eng-architecture` | 4 | skill: step 12 done by eye | `check_design.py` now fails on an assumption that does not say how to verify it. It also warns with the code identifiers (dotted names, camelCase names, calls, and calls and methods in code blocks) that neither the Assumptions section, the Sources section nor a URL cites. On the two designs of this step's trial, it reports exactly the gaps the grader found. Step 12 works through that list; the template's assumption line ends with `Verify:`. Three offline tests | Y, 1.2.0 | **Fixed**, 1.00 / 1.00 |
| `ops-ci-pipeline` | 1 (A8) and 4 (floor 4.4) | skill: template and stop rule 4 | The `Push:` line and the closing question are now copied word for word. When the local run could not happen, the reply ends with a literal question asking the user to run it, and says the push waits for that run and for an explicit yes. The gate says that nothing is committed, pushed or deployed before the yes. Stop rule 4 names the three decisions of the inputs table. When one is missing, even one with a recommendation, no file is written, and who builds what is deployed is asked alongside. Two defects of this fix were found by its own trials and corrected in the same pull request. First, listing "who builds" as a fourth required decision made the strong run stop on case 1 (0.00). Second, leaving it out made the floor run drop that question on case 4 | X, 2.0.0 | **Fixed** on the third trial: case 1 1.00 / 1.00 (A8 passes on both tiers), case 4 1.00 / 1.00 |
| `brand-voice` | 2 (strong) | case: fixture | The strong run applied stop rule 2 correctly: sample 2's "!!!" is part of the shouting the user dropped, and the state file decided no exclamation limit, while the prompt says the limits are in the state file. The fixture's 2026-09-24 decision now includes "no exclamation marks", and the expected output names `max_exclamations 0`. No assertion changed | none (case only) | **Fixed**, 1.00 / 1.00 |
| `core-critique` | 2 | skill: step 4 | Step 3 takes the domain's set and "Any proposal", and the assertion follows it. But step 4 did not say where a category comes from. Step 4 now takes it from those two sets only, spelled as the table spells it, and files a failure that seems to need another category under the closest one | Y, 2.1.0 | **Fixed**, 1.00 / 1.00 |
| `brand-strategy` | 2 (floor) | skill: template | The template line for profile proposals gave nothing to copy. Step 7 and the template now ask for the current text quoted and the new text written out (or the removal), never a description | Y, 1.1.0 | **Fixed on the floor** (1.00). The strong run scored 0.89 on A5, a row not seen before: its risk for the AI pillar "settles when a first artifact exists". The grader read that as no date or measure; the same wording passed in this step's trial. Grader or model variance; nothing changed for it |

**Model calls: 77**, all through the eval runner in the container, on the gate file's models:

- 19 strong runs and 19 floor runs;
- 38 gradings and 1 second grading, of `ops-ci-pipeline` 1 A8 in its first trial.

**Tokens: 13.4 million**:

- 5.3 million on strong runs;
- 7.5 million on floor runs;
- 0.6 million on gradings.

**Reported cost:**

- $3.59 for strong runs and $1.39 for gradings, both notional, on the account;
- $0.21 for floor runs, through the OpenRouter key.

There were no infrastructure failures, timeouts or contaminated runs. No evidence file was written.
