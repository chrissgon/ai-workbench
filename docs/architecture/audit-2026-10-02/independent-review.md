# Independent review of the repository and of the final plan, 2026-10-02: digest

This file is a digest, not the report. The report was written in another language by a reviewer outside the sessions that wrote the audit and the plan, and it is kept by the maintainer outside the repository. The digest has one entry per finding: its id, its severity, where it lies, the evidence in one or two sentences, and the item of [the plan](../final-plan-2026-10-02.md) that now carries it.

## Scope and method

- Read-only, on `main` at `899fbe8`. Nothing in the repository was edited, no model was called through the eval harness, no container was started and no network was used.
- Read in full: `AGENTS.md`, the plan, the eval runner, the status script, the executor, the grading template, the container definition, the two `run-prompt.sh`; parts of the validator, the resolver, the publisher, the vote job and the API adapter.
- The stored runs of the first measurement round were processed by script: the 48 records and the 1,689 gradings of the recorded iterations. Those runs are in the eval workspace, a folder outside the repository; evidence paths below that start with a skill's name are inside it.
- Five subagents read one scope each: 17 skills in full (`mkt-publish`, `mkt-engage`, `mkt-vote-round`, `brand-name`, `brand-profile`, `brand-strategy`, `eng-implement`, `eng-unit-tests`, `eng-root-cause`, `flow-fix-bug`, `ops-branch-sync`, `ops-pull-request`, `core-orchestrator`, `core-skill-creator`, `core-research`, `design-execute`, `product-prd`), the platform architecture, security, and the facts the plan states. The reviewer checked in the code or in the data each of their findings that entered the report, and says where only part was checked.
- `python3 scripts/validate.py` (0 errors, 3 warnings) and `python3 evals/eval_status.py status` (33 `evaluated`, 15 `stale`, 0 `draft`) were run and agree with the plan.

## Ids

The report numbers its findings B1 to B5 (blockers), I1 to I16 (important) and M0 to M15 (minor). The plan already uses B1 to B11 for the items of its phase B, so the plan and this digest cite the findings as FR-B1 to FR-B5, FR-I1 to FR-I16 and FR-M0 to FR-M15.

## Verdict

The plan is sound in its direction and covers most of what the audit found, and it was not ready to run as written. Five points would have led to rework, to a measurement that does not measure what it says, or to measuring again continuously after the round. Each has a small fix that fits before the round, in phase B, C0 or D. The rest are findings that lower the chance of a single round, and some security findings that do not depend on the round.

When the plan was amended, the main claims were checked again against the code and the stored runs (FR-B1, FR-B2, FR-B3, FR-I4, FR-I11, FR-I12 and the resolver claim of FR-M5), and every file, line and count the plan quotes from the review was read in the code. All of them hold.

## Blockers

| Id | Where | Evidence | Carried by |
|----|-------|----------|------------|
| FR-B1 | the two `run-prompt.sh`; plan items B3 and B8 | The strong adapter stores the assistant's last message; the floor adapter stores the runner's whole output. Narration between turns is in 195 of 846 stored floor replies (23%) and in 13 of 846 strong ones (1.5%), so assertions about what the reply quotes, asks or ends with were judged on different material | default 91, B3, B8, the proof run |
| FR-B2 | decision 14c, C0.9, the rows of the platform skills | Of the 17 base prompts of the seven skills that get the literal platform step, 3 name the platform. The prompts in runtime mode copy the runtime's task text, which names none; `brand-name`'s script already uses `--platform` for something else | decision 14c, C0.9, rows 44, 46 and 48 |
| FR-B3 | the cases of `flow-fix-bug`; default 29; row 12 | The flow's three cases install the router, and all 18 stored without-skill replies start with the router's route card, 14 of them only asking to install the flow: the baseline of 0.511 is the dependency's output. The router's two new `ready` cases would have been rejected by the preflight, or would have made the two records name each other's hash | default 29, rows 12 and 38, B9, batch 5 of phase E |
| FR-B4 | default 20, B7, "The freeze that follows" | 19 of the last 30 commits touched a file that `core-skill-creator`'s cases bring; with `--strict` in CI each such pull request would fail until a new record of that skill was in it. Inferred from the plan's text: after phase B the tools read files the cases do not bring, and a flow made from the template never reaches zero errors under default 47 | default 20, default 47, A16, B7, row 16 |
| FR-B5 | phases C, D and E | The round would measure 157 rewritten cases that never ran: phase C measures nothing, the pilot runs 6 skills, and in the first round 23 of 48 skills needed more than one iteration. A case defect would show only inside the round and use one of the two repairs | D3 (the smoke pass), D4 |

## Important findings

| Id | Where | Evidence | Carried by |
|----|-------|----------|------------|
| FR-I1 | phase E rules 5 and 7; decision 1; B7 | Rule 5 measured again only a skill that failed by little and let the new record replace the old one, which is the option decision 1 rejected. A skill whose true score is 0.78 passes one measurement 28% of the time and 49% with a second chance; and the standard error inside an iteration is two to three times smaller than the movement between iterations | decision 1, B7, rules 5 and 7 of phase E |
| FR-I2 | the gate's third criterion; the rule for case changes; C0.7 | Of 655 assertions with all four variants, 196 pass everywhere and another 196 never pass without the skill and always pass with it, most of them on a form only the skill defines. The criterion that should catch an over-specified skill cannot fire on them | default 92, C0.7, B7, the rule for case changes |
| FR-I3 | the risk table; the batches of phase E | Without the always-passing assertions five skills fall under 0.8 on a tier and five more are between 0.80 and 0.87; the plan named two, and two of the ten were in the last batch | batches 1 and 2 of phase E, the risk table |
| FR-I4 | B10, default 21, B6a | Only two skills cite `shared/references/`, yet the whole folder was in the fingerprint, and so was `scripts/redact.py`, whose pattern matching would also mask a planted fake secret before grading. Two files that would have been frozen are already wrong: one line of the security checklist and the README's enumeration | default 21, B2, B6a, B7, B10, C0.6, C0.9 |
| FR-I5 | HP3 (CT2), HP2 (PUB1), C0.9 against row 44 | Three things the platform skills quote would change after the round: the limits that are constants of the runtime today, the reading of the exit codes of `--check` (the skill says 3, the provider exits 1), and the field names the gate script reads | C0.2, C0.9, rows 44 and 46, the limits of phase P, HP3 |
| FR-I6 | D3 against B2 | The pilot's routing pass used an option of the adapters that B2 removes; the mode that would serve was planned for after the round | B9a, D3, lane F4 |
| FR-I7 | row 48 | `check_post.py` looks up two other skills' scripts and prints `ok: false` without them; the row vendored only the first, kept three dependency skills in one case, and proposed a command with an option the provider does not have | row 48 |
| FR-I8 | rows 14, 31, 34, 37, 38, 39 and 41 | Six rows treated a symptom or created a case that cannot pass: a question the code already answers (`eng-unit-tests`), opposite rules for a later push frozen into two fixtures (`ops-branch-sync`, `ops-pull-request`), a grade that needs a web the cases never have (`eng-root-cause`), two new cases of the flow that end in questions or on a phase that is not installed, a mode with no procedure and no case (`eng-implement`), and a script rule that would flag 33 of 104 items in the stored briefs (`core-research`) | rows 14, 31, 34, 37, 38, defaults 42 and 80; rows 39 and 41 as open point c |
| FR-I9 | decision 14b rule 3; decision 14c; A10 | Walking the path of a post that is only an image shows that the post file, the payload builder, the provider's verb, the vote job and the gate's key all assume a text post; `mkt-social-copy` carries platform rules and was not among the seven skills | decision 14b rule 3, decision 14c, A10, rows 44, 46 and 47 |
| FR-I10 | the secrets contract; the runner; default 17; lane F7 | On a web case the model reads live pages, runs any command and has the long-lived token of the maintainer's account in its environment; the grader holds the same token and has tools today | B3, B5, B9; open point a |
| FR-I11 | the runner's snapshot and file listing | These functions run on the host after a run and follow a symbolic link a run leaves: the target's content, up to the file limit, goes into the grading prompt and to the provider | B2a |
| FR-I12 | the vote job; the publisher; HP1 | When only the first comment fails, the provider prints the post's address and exits with a service code, and the job reports that nothing was published; the pending entry is deleted on every 4xx answer; a scheduled job may use another ledger. In the API adapter, the text of an external comment chooses which project files are sent to the model | HP1, HP2 |
| FR-I13 | phase E; decision 2; D4 | Measured from the first round's `timing.json` files: 155 million tokens in 843 strong runs and 54 million in 1,689 gradings; the final round is near 490 million, 2.3 times as much, and the plan had no agreed fallback | phase E's arithmetic, the proof run, D4; open point b |
| FR-I14 | default 16; B5; phase E rule 1 | A repeated timeout scored 0 with the skill and was left undefined without it, and a persistent refusal was resumed with no limit | default 16, B5, rule 1 of phase E |
| FR-I15 | A5 part 2; A11 | The widened harness pattern would fail on a case file's `workbench_files`, on two contracts and on two files that only A11 cleans, with no order between the two items | A5, A11, the lanes of phase A |
| FR-I16 | "Shared files and their order"; phase B's "Depends on"; A11; C0.3 | The order of the validator's editors made two items of phase B wait for phase C; seven files with several editors were missing from the table; the pass-through variables had two homes; one CI job lists test paths by hand; a correction was attributed to the wrong script | the table of shared files, phase B's "Depends on", A11, C0.3 |

## Minor findings

| Id | Where | Evidence | Carried by |
|----|-------|----------|------------|
| FR-M0 | A7 | The API adapter's timeout test failed 4 of 6 local runs and is in a required check | A7, first of phase A |
| FR-M1 | B7, B10 | The record did not carry the fingerprint, so a measuring checkout with an altered file could write a record unnoticed | B10, B7 |
| FR-M2 | D3, D4 | If D4 sets `grading_passes` to 1, the pilot's record, made with 2, reads `stale` | decision 2, D3, D4 |
| FR-M3 | B7 | The floor model's upstream provider is reported and not pinned; not verified, for lack of network | B8 |
| FR-M4 | phase E | The round's gradings and replies sit on one disk, outside the repository | phase E (the archive of each batch) |
| FR-M5 | several | Facts stated wrongly, with small effect: the count of skills that declare no publisher; the resolver has no class-to-folder map; nine of eleven fixture copies carry the runtime line; two shell scripts have a hyphen; the proof run's count of cases; "after C0" includes C0.10 | decisions 14a and 14c, C0.2, default 71, "Where things stand", the proof run, A15 |
| FR-M6 | C0.4, C0.5 | `--report` has three shapes in four scripts and is a switch in a fifth | C0.5, rows 17, 19, 21 and 26 (row 24 already changes the fifth) |
| FR-M7 | row 6 | The export parser of `brand-profile` reads English only, and the skill has no stop rule for its exit | row 6 |
| FR-M8 | row 46 | The payload hash depends on the spelling of `--platform` | row 46 |
| FR-M9 | row 18 | The dependency skill is in all three cases of `design-execute`, and no fixture has a state file | default 29, row 18 |
| FR-M10 | row 7 | No case of `brand-strategy` measures a successful read of its baselines script | row 7 |
| FR-M11 | the executor | The container is started without dropped capabilities, without the no-new-privileges option and without a process limit | B1 |
| FR-M12 | B6a | The proxy filters by host name only, and the allowed hosts serve many accounts; the audit's sentence that a run cannot reach a third party is wrong | B6a |
| FR-M13 | A12 | Five more skills carry the external-content sentence inside a numbered item, which the "start of a line" rule would flag | A12 |
| FR-M14 | A5, C0.10, decision 9 | Nine descriptions are over the 900-character warning that must reach zero | the paragraph above the 48 rows, C0.10 |
| FR-M15 | row 16 | By the validator's rule `core-skill-creator`'s `SKILL.md` has 6,016 tokens, and the planned cut ends near 4,800 | row 16 |

## Triggers of a second round

The report closes with a table of what can change after the round and whether the plan protects against it. Its rows are the plan's section "What would make a second round necessary", each with the protection the plan now has.

## What the review checked and found correct

- The counts of "Where things stand" (48 skills, 141 cases, the three statuses, the validator's result, 196 always-passing assertions, 9 web cases in 5 skills) and the volumes of phase E as the plan stated them then.
- What the audit says about the runner: a record could be written with one run per case, the count of the grader's results is not checked, the comparison of the gate uses rounded means, the contamination check cannot fire in the container.
- Grading is blind to the variant, and `expected_output` does not reach the grader. The skills help on the assertions that are not of the format kind as well: the strong model's difference is positive in 47 of 48 skills.
- The nine `workbench_files` of `core-skill-creator` are today exactly what the tools need.
- Security: no shell invocation through a string, setup commands run with no network and no secret, the proxy's internal network is real, the container's user is not root, tokens live only in the OS secret store, CI has read-only permissions and pinned actions.
- The script-location sentence, "the `scripts/` folder next to this file", is the one form that is right in every layout without naming a tool.

## What the review could not verify

- Anything that needs the network, a container or a model: the state of CI, whether the pinned runner has an option that switches tools off, how the floor runner separates messages in its structured output, the floor provider's route.
- The second part of FR-B4 is an inference from the plan's text about code that does not exist yet.
- The subagents' experiments on scratch copies were not repeated; the code and the texts they cite were read.
- How many floor verdicts depend on the narration: its presence was measured, not its effect on each verdict.
- Whether the working sessions of phases P and F use the same account as the strong model.

## Changes made for this repository

Locations on the reviewer's machine are replaced by descriptions ("the eval workspace"). The report's three closing lists are summarised in the two sections above; its first list, the five largest risks, is in the plan's risk table.
