# Independent review of the reliability model, 2026-10-02: digest

This file is a digest, not the report. The report was written in another language by a reviewer outside the sessions that wrote the model and the plan, and it is kept by the maintainer outside the repository. The digest has one entry per finding: its id, its severity, where it lies, the evidence in one or two sentences, and where it is now resolved, in [the model](../reliability-model-2026-10-02.md) as rewritten (version 2) or in [the plan](../final-plan-2026-10-02.md).

## Scope and method

- Read-only, on `main` at `03e16ee`. Reviewed: the reliability model as first written (version 1). Nothing in the repository was edited, no model was called, no container was started and no network was used. The simulation scripts stayed in a temporary folder outside the repository.
- Read in full: the model, the digest of the earlier independent review, `evals/eval_status.py`, `evals/eval_run.py`, and the parts of `scripts/validate.py` that compute the status.
- The model's backtest was redone from the 48 committed records.
- The correlation between runs and the real variance of the scores were measured on the 1,689 gradings of the first round, which are in the eval workspace, a folder outside the repository.
- Three subagents read one scope each: guard coverage and the field trigger (the skills with side effects read in full, with their cases); the change classes (the 48 skills and the 204 changes of the history); the fit with the plan, item by item. The reviewer checked in the code, in the data or in the history the findings that entered the report, and says where only part was checked.
- Before the model was rewritten, five of the review's claims were checked again against the repository, and they hold.

## Ids

The report numbers its findings B1 to B4 (blockers), I1 to I14 (important) and M1 to M9 (minor), each with the prefix M: MB1 to MB4, MI1 to MI14, MM1 to MM9. The model and the plan cite them by those ids.

## Verdict

The direction is right and the gain is real: evidence accumulated per run, a cheap targeted test, a hash per case, the floor model as information only. The backtest of version 1 is correct: every number agrees.

As written, the design did not reach three of its six goals (a rank that falls when a skill changes with no new evidence, a table that can be trusted, guards that never ride on usage) and reached a fourth, seeing real use, only in part. The common reason: the score did little of the work. The bands were decided by rules, and the rules had four holes: a guard had to exist and never to pass; the lowest change class could not be verified and accepted changes of behaviour; any change followed by a targeted test erased the bad runs of a case; and field evidence, self-reported and selected, entered the same sum as lab evidence. Each had a small fix, and a version with about half the parts delivers four of the goals. The maintainer adopted that version, with every correction, on 2026-10-02.

## Blockers

| Id | Where | Evidence | Resolved in |
|----|-------|----------|-------------|
| MB1 | version 1, sections 2, 5 and 6 | No rule looked at the result of a guard case, and the gate is the mean of all runs: in the first round `ops-branch-sync`, `eng-unit-tests` and `design-execute` passed while one guard assertion failed in every run. Three of the nine skills with side effects have no case that reaches their gate, and the one consequence the rule had was to fail CI, which would have kept `main` red from the first row of phase C | the model, section 4 (the tag on the assertion; a failed or missing guard gives `needs a full test`; guard cases on every Y change; one guard per declared effect); the plan, B14, C0.7, default 39, rows 18, 20 and 22 |
| MB2 | version 1, section 4 | 38 of the 48 skills have no stop-rule section, so the validator watched sections most skills lack; a step is one line with a median of 329 characters, so the limit of 15 lines covered most of a procedure; a merged change that altered what happens on a missing input in nine skills would have been the lowest class. The description was in that class by definition | the model, section 3 (an allow-list and a budget in characters; a description is Y; a `## Stop rules` section); the plan, B13, C0.6 |
| MB3 | version 1, section 2 and the repair loop | After any version change, the new runs of a case replaced its old ones in the gate rule while the cases that had passed kept theirs: with the movement measured between identical measurements, a skill whose true score is 0.76 passes one draw 19% of the time and 71% of the time with six | the model, section 2 (only a full test evaluates the gate; a partial test moves the score); the plan, B12, rule 4 of phase E |
| MB4 | version 1, sections 3, 6 and 8 | Only a use that was delivered and answered became a trial; ten good self-reports returned `reliable` after any change, and in the model's own example field evidence was 63% of the weight; no key tied an entry to a contributor, and one hostile file could sink a skill. The trigger did not run where the design assumed: the block of the instruction file belongs to another skill, no installer sets the workbench root, and no variable carries the model id | the model, section 7 (own columns, a demotion signal, no promotion, `record --start`, a maximum weight per file, a verdict line that cannot be a consent); the plan, B15, row 13, lane F9 |

## Important findings

| Id | Where | Evidence | Resolved in |
|----|-------|----------|-------------|
| MI1 | version 1, sections 3 and 9 | Measured on the first round: the real variance of a mean is 17% of the binomial one with the cases fixed and 32% with the cases as a sample, so the interval is far too wide, and with few runs the score orders skills by their number of cases | the model, section 6 (the pessimistic score, never a confidence bound; shown with the mean and the number of runs) |
| MI2 | version 1, section 6 | After a passing full test the score was always at 0.539 or more, so the thresholds of 0.50 and 0.45 almost never decided, and a skill with 6 runs at 0.80 read `reliable` at 0.54 | the model, section 5 (bands stated as rules; `reliable` at 0.70; six skills start in `watch`) |
| MI3 | version 1, sections 3 and 6 | With 60 trials at 0.95 the score went from 0.900 to 0.881 after a change of a step: a decay only shrank the count | the model, section 6 (inherited evidence capped at 3 runs within a major version and at 1 across) |
| MI4 | version 1, "Dropped or shrunk" | The bands are computed on the reference model and the grader has the same id: a change of either was a full test of everything, while the text said that nothing forces one | the model, section 9 and the cost table; the plan, "What a change costs now", B3 (`--regrade`) |
| MI5 | version 1, section 3 | A factor of 0.8 per measurement step punished 43 skills for a tool that changes the runs of five, and treated a change of the grading rules as a small one | the model, section 8 (three kinds of change, no factor); the plan, B10 |
| MI6 | version 1, sections 2 and 4 | A run without the skill does not see the skill: the baseline ages with the model, the measurement and the case, and the full test after a contract change redid a baseline that had not changed | the model, section 2 (the baseline reused; about 10 runs after an X change); the plan, B12 |
| MI7 | version 1, section 4 | In 204 changes of the history the contract keys changed eight times, every time by an addition | the model, section 3 (X for `side_effects`, removals and renames, the gate, the stop rules, the external-content rule; additions are Y) |
| MI8 | version 1, item N3 | Phase C rewrites almost every case and phase B changes what the grader sees, so the converted records would weigh nothing; and one draw of 3 runs passes a skill at 0.78 a third of the time | the model, section 1 (no conversion); the plan, phase B's goal, decision 1 |
| MI9 | version 1, sections 1, 6 and 7 | Every pull request that added evidence regenerated the same block and appended to the same file, so two open ones always conflicted; the hook and CI compared against different bases | the model, sections 1, 3 and 10 (one file per test event; a snapshot table; one base; an idempotent bump); the plan, B7, B13, B16 |
| MI10 | version 1, sections 1 and 8 | The gate file and an adapter's README spell the same model two ways, so its evidence would fall into two rows; a tuned model's name identifies its company | the model, section 1 (a list of known models with aliases; `unknown`); the plan, B7 |
| MI11 | version 1, "Kept"; plan items B5, B6, B8, B9, D2, defaults 16 and 34, A2, A5 | Items kept as written whose object had gone: a timeout after the cap scored 0 in the plan and was never an entry in the model; stub runs would have written lab entries; the validator's rule of known keys rejected `tags`, and its pattern of tool names caught the adapter field of an evidence file | the model, section 1; the plan, A5, B5, B7, B9, D2, defaults 16 and 34 |
| MI12 | version 1, sections 1 and 9 | Nothing told a line written by the runner from one typed into a pull request, and the extension of the code owners file went away with the freeze | the model, section 8 (the fingerprint in every line; the runner's refusal; the maintainer runs the tests on the reference model); the plan, B7, B10, B11 |
| MI13 | version 1, "The new order of work" | Each row of phase C needed the bump command, which needed the hash, which came after five items of phase B; the first version check would have failed on all 48 skills the day it merged; the smoke pass wrote 314 entries before the instrument was checked | the plan, phase B's order, B13 (the migration), C0.10 (the sweep to `1.0.0`), D3 (the smoke pass writes no evidence) |
| MI14 | version 1, sections 1, 2 and 3 | A changed dependency skill decayed nothing; the gate rule did not exclude entries of weight zero and left an added or a deleted case undefined; the case hash left out `grader_files` (43 of 141 cases), `skills`, `setup`, `allow_web` and `workbench_files` | the model, sections 1 and 2 (`context_sha256`; the gate over lines of weight above zero with every current case required; the hash over the whole case); the plan, B7, B12 |

## Minor findings

| Id | Where | Evidence | Resolved in |
|----|-------|----------|-------------|
| MM1 | version 1, section 1 | Compaction merged entries and lost the case, after which the gate could not be computed again | the model: no compaction |
| MM2 | version 1, section 1 | A date with its day, in a contributed file, publishes when a person used each skill | the model, section 7 (the week); the plan, B15 |
| MM3 | version 1, section 4 | One line of a shared script moves every skill that carries it to `watch` | accepted: the model's cost table; the plan, "What a change costs now" |
| MM4 | `scripts/validate.py` | The validator never reads `metadata.version`, and the 48 versions are two-part texts today | the model, section 3; the plan, B13 |
| MM5 | version 1, section 7 | A model with only field evidence was shown with a score, with no guard and no baseline on it | the model, section 7 (counts and mean, no score) |
| MM6 | version 1, section 8 | The effect of the field protocol on a skill's behaviour was never measured: the container has no such block | the model, section 7; the plan, D3 (one smoke case carries the block) |
| MM7 | version 1, cost table | For the 17 skills of two cases, one measurement step gave fewer than 5 weighted trials | moot: no factor per step (the plan, B10) |
| MM8 | version 1, item N9 | The places that name the old states were undercounted: at least eight in `AGENTS.md`, seven passages of `core-skill-creator`, its guide, the templates, the scaffold | the plan, A17 (eleven places) and row 16 |
| MM9 | version 1, the tables of changes | One decision was listed as kept and as changed; the floor model's rows were read by no rule, yet a full test needed its runs | the plan is one document; the model, section 2 (the floor model runs with the skill only) |

## The findings of the earlier review

The report states what the model as first written did to the findings of the independent review of the plan (the FR ids). In short: the blockers FR-B1 to FR-B5 stayed resolved; FR-I1 (a second draw replacing the first), FR-I14 (an undefined timeout) and FR-M1 (a record with no provenance) were reopened, by MB3, MI11 and MI12; FR-I2 was weakened, since per-assertion counts were tied to the last full test; FR-I15 and FR-I16 were reopened in a small way (the evidence files against the validator's pattern; the table of shared files without the new items). Version 2 and the plan close each: the plan's section "Reviews" has the current table.

## The twelve questions

Version 1 ended with twelve open questions. The review answered each, and the model's last section gives the answers in one line each: rules beside the score, said to be rules; a narrower X class and a reused baseline; the run as the unit; `reliable` at 0.70; lab runs to leave `watch`; an allow-list for the lowest class; no conversion of the old records; a use recorded at its start by a hook or by the runtime; an append-only version file; no baseline on other models by default; one grading pass; a change always asks for lab evidence.

## The simpler version the review recommends

Seven parts: evidence as one line per lab run, one file per test event; two kinds of lab test, with the baseline reused; two change classes and an allow-list; bands by rules, said to be rules; the Wilson lower bound over lab evidence with a cap on inherited evidence; field evidence in its own columns, demoting and never promoting; one measurement floor and three kinds of measurement change. Dropped: the context decay, the factor per measurement step, model epochs as a decay, compaction and counts, a formula per platform, the limit of 15 lines, the thresholds 0.45 and 0.50, the conversion of the old records. What is lost: daily use alone no longer returns a skill to `reliable`; each change of a step asks for 3 to 9 lab runs. This is the version the maintainer adopted.

## What the review checked and found correct

- The backtest of version 1, redone from the 48 records: the distribution of runs, the eight scenario rows on both models, the example rows and the worked examples agree to the third decimal.
- The arithmetic: 157 cases, 1,884 runs, 1,413 without the floor model's baseline.
- That thresholds on the score alone cannot separate a fresh full test from a changed skill.
- Taking `evals/` out of the content hash and giving each case its own hash is consistent with what the adapters already do.
- A baseline reused after a change to the skill is statistically right.
- The assertions that say "asks before" discriminate: 98 of 108 with the skill, 25 of 108 without.
- The counts in the skills: 9 with side effects, 9 with a confirmation section, 10 with a stop-rule section, 4 without the external-content sentence.

## What the review could not verify

- Anything that needs a model, a container or the network: whether any environment reports the model id reliably; how other tools load a project's instruction file.
- The recorder script, the bump command and the validator's new rules did not exist: the text was judged.
- The field weight, the mapping of a verdict to a number and the decay of the lowest class: there is no field evidence and no history of classified changes.
- The subagents' counts were checked in part: two of the fifteen history examples, two of the guard assertions, three of the 48 rows of phase C.

## Changes made for this repository

Locations on the reviewer's machine are replaced by descriptions ("the eval workspace"). The report's table on the earlier findings and its closing lists are summarised in the sections above.
