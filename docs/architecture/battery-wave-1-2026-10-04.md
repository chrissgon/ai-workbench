# Battery, wave 1: the reading (2026-10-04)

The first wave of the first full test of the 48 skills: the five skills of the pilot, run as real evidence under measurement version 8 (fingerprint `b628afd5ab52f0e416a52719c885c647d81639c05fd8daf9d72539f5299cf01d`, image `sha256:4a446f8ae551e20ccca1728602c6fa8ce510b73db4b1fdb17cf87ad21351eb28`), from commit `9a6e1d2`, with `eval_run.py --skill <name> --baseline-on floor`, five runners side by side. Started 12:32 UTC, ended 13:37 UTC. This file records the reading that decides whether wave 2 starts. Every item was read by the executor of the plan; no item was left out.

## Read back

| Skill | Gate | Mean with the skill | Baseline | Lines | Skill loaded (strong, floor) |
|---|---|---|---|---|---|
| `design-execute` | passed | 0.986 | 0.392 | 32 | 11/12, 12/12 |
| `biz-market-analysis` | passed | 0.964 | 0.217 | 24 | 9/9, 9/9 |
| `ops-pull-request` | passed | 1.000 | 0.520 | 40 | 15/15, 15/15 |
| `flow-fix-bug` | passed | 0.933 | 0.680 | 40 | 13/15, 15/15 |
| `core-skill-creator` | passed | 0.896 | 0.269 | 32 | 12/12, 12/12 |

`python3 evals/eval_status.py status` after the wave:

| Skill | Band | Cause | Pessimistic score | Mean | Runs |
|---|---|---|---|---|---|
| `design-execute` | `reliable` | | 0.882 | 0.989 | 15 |
| `biz-market-analysis` | `reliable` | | 0.790 | 0.964 | 9 |
| `ops-pull-request` | `reliable` | | 0.916 | 1.000 | 18 |
| `flow-fix-bug` | `needs a test` | guard assertion 4.6 failed in the current set | 0.801 | 0.933 | 15 |
| `core-skill-creator` | `reliable` | | 0.733 | 0.896 | 12 |

Every event is complete, with 0 failures, timeouts, refusals, contaminated baselines, shared passages, infrastructure failures, early ends and redactions. No attempt was set aside for the account's limit. No counted stream holds a near-limit or grace text or a rejected rate-limit status.

## Twenty gradings read by hand

Four per skill (two of each model), ten of the floor model, eleven passes and nine failures. For each, the assertion, the verdict and whether the quoted evidence supports it, checked against the reply, the run's files and its facts block. **No verdict was found wrong.**

| # | Skill, case, model, run, assertion | Verdict | Evidence checked | Right |
|---|---|---|---|---|
| 1 | `design-execute` 2, strong, 3, A6 | fail | `docs/workbench/state.md` exists in the run folder and is unchanged; the reply says no state file exists | yes |
| 2 | `design-execute` 1, strong, 1, A1 | pass | facts: nothing created or changed | yes |
| 3 | `design-execute` 3, floor, 1, A2 | pass | three prompt packs created, one per direction | yes |
| 4 | `design-execute` 4, floor, 2, A1 | pass | the reply ends "Proceed? (yes/no)" and shows the three prompts, 1200x630 and 3 images | yes |
| 5 | `biz-market-analysis` 3, floor, 1, A3 | fail | line 90 of `market.md` holds "€35–€65" with no source (line 33 cites it); the assertion says every amount | yes |
| 6 | `biz-market-analysis` 3, floor, 2, A4 | fail | "€8,80/mês … [13]", and the quote of [13] has no 8,80 | yes |
| 7 | `biz-market-analysis` 1, strong, 3, A3 | fail | "starting from $1250" carries no unit | yes |
| 8 | `biz-market-analysis` 2, strong, 1, A1 | pass | scope questions only | yes |
| 9 | `ops-pull-request` 2, floor, 1, A3 | fail | the test results are paraphrased ("1 test, 1 pass, 0 fail"), not the printed lines | yes |
| 10 | `ops-pull-request` 4, floor, 1, A4 | pass | the reply ends "Proceed? (yes/no)" | yes |
| 11 | `ops-pull-request` 1, strong, 1, A2 | pass | the body states the cause (a date-only string read as UTC) | yes |
| 12 | `ops-pull-request` 5, strong, 2, A3 | pass | "Pull request: not created (no code-hosting integration)", with a title and a body | yes |
| 13 | `flow-fix-bug` 4, strong, 2, A2 | fail | `state.md` reads "Current flow: none" | yes |
| 14 | `flow-fix-bug` 4, strong, 3, A6 | fail | the last line asks to start the flow, not to approve a root cause | yes |
| 15 | `flow-fix-bug` 4, floor, 1, A2 | pass | `state.md` reads "Current flow: flow-fix-bug …" and "Current phase: 1 Root cause" | yes |
| 16 | `flow-fix-bug` 1, floor, 1, A1 | pass | the same lines in `state.md` | yes |
| 17 | `core-skill-creator` 2, strong, 1, A2 | fail | the scaffold command is quoted without the JSON line it printed | yes |
| 18 | `core-skill-creator` 3, floor, 1, A2 | fail | a "(planned)" change to SKILL.md maps to no classified failure | yes |
| 19 | `core-skill-creator` 1, strong, 1, A1 | pass | facts: nothing created or changed | yes |
| 20 | `core-skill-creator` 4, floor, 1, A3 | pass | item 1 is "no" for a stated reason | yes |

## The facts block

Five runs, one per skill: the files the facts block lists as created, changed and deleted match a `git --no-optional-locks status` of a copy of each run's working folder. A rename shows as a file created and a file deleted.

## The grader's disagreement

`eval_run.py --regrade <event folder>`, one event at a time, nothing else running:

| Skill | Gradings | Failed | Verdicts | Differ | Share | Failed verdicts | Of them differ |
|---|---|---|---|---|---|---|---|
| `design-execute` | 32 | 0 | 136 | 1 | 0.7% | 23 | 1 |
| `biz-market-analysis` | 24 | 0 | 144 | 6 | 4.2% | 36 | 2 |
| `ops-pull-request` | 40 | 0 | 168 | 3 | 1.8% | 25 | 1 |
| `flow-fix-bug` | 40 | 0 | 216 | 0 | 0.0% | 25 | 0 |
| `core-skill-creator` | 32 | 0 | 168 | 2 | 1.2% | 43 | 1 |
| All | 168 | 0 | 832 | 12 | 1.4% | 152 | 5 |

No event reaches the stop threshold of 4.4%. `biz-market-analysis` is the closest, as expected of a skill whose assertions check figures against quotes.

## Credentials and paths

The runner's `redactions` count is 0 in every event. The mount path `/wb/run-prompt.sh` is in no stored file outside the event streams.

## Skill loaded

Three runs with the skill did not record it as loaded:

- `design-execute` case 1, strong, run 3: the reply follows the skill's output template and scores 1.0. The model read the skill's file instead of loading it, which the detector does not count.
- `flow-fix-bug` case 4, strong, runs 2 and 3: the model loaded only `core-project-init`, which the case stages as a dependency, set the project up and asked whether to start the flow. It scored 0.5.

Both descriptions reached the model (five skills staged, no listing cut), so this is not the stop condition. It is a weakness of `flow-fix-bug`'s description for a request on a project not yet set up, recorded for a repair.

## The routing pass

Run before the wave, with the default pack installed, for the five skills of the wave and then for the other 43 (one prompt per case, strong model, no score). No description collision was found. Every flagged prompt was read:

- the orchestrator loaded together with the right skill, or routed to it and stopped as a router;
- a stop case was answered with a question;
- the skill was read from its file rather than loaded.

## The field block

Case 4 of `ops-pull-request` (its reply ends with a request for approval) was run once more on each model in a scratch copy, with lines 10 and 11 of `skills/core-project-init/assets/agents-md-section.md` in its fixture's instruction file. Both replies scored 1.0 on every assertion, as in the wave, and both end with "Proceed? (yes/no)" with no skill-check line. The floor model ran the use recorder twice, as line 10 asks. The block changes nothing the assertions measure.

## The calendar

Wave 1 (168 runs and their gradings) used 15 points of the 5-hour window and 2 points of the week. Wave 2 is about 6.6 times larger: about 13 more weekly points, from 37% to about 50%, and about two 5-hour windows with the runner pausing at the limit.

## Observations for repairs

- `flow-fix-bug` is `needs a test`: the guard assertion 6 of case 4 (the last line asks to approve the root cause before the next phase) has a confirmed failure in the two strong runs that loaded only `core-project-init` (see "Skill loaded"). Classified as a skill defect: on a request for a project that is not set up yet, the model starts with the setup skill instead of the flow, which runs the setup as its first step. It is repaired beside wave 2, as section 12.6 of the plan asks: a change to the skill with its bump, a partial test of the failed cases, then one full test of the fixed version with the baseline reused.
- `core-skill-creator` case 2, assertion 2: the scaffold's JSON line is not quoted in all three strong runs. A pattern, no longer variance; the gate passed and the skill is `reliable`.

## Decision

No stop condition holds: no verdict contradicts the facts block, no reading found a wrong grading, no run missed the skill because its description did not reach the model, no credential or mount path is stored, and no event reaches 4.4% of disagreement. No file inside the measurement fingerprint needs a change. The evidence of wave 1 is merged, and wave 2 starts.
