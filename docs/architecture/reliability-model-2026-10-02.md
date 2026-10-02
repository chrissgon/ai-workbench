# The reliability model, version 2 (2026-10-02): lab evidence per model, bands by rules

**Status: decided.** The maintainer decided the model in outline on 2026-10-02; version 1 of this document wrote it out; an independent review of version 1 found four blockers and recommended a simpler version; the maintainer adopted that simpler version, with every correction the review proposes, the same day. This document states the model as it now is. The work that builds it is in [`final-plan-2026-10-02.md`](final-plan-2026-10-02.md): this document describes the model, the plan describes the work, and neither amends the other. The review's findings are cited by their ids (MB1 to MB4, MI1 to MI14, MM1 to MM9); a digest with one entry per finding is [`audit-2026-10-02/model-review.md`](audit-2026-10-02/model-review.md), and the last section here says what each one changed.

Every number called a parameter is a starting value. The section "Backtest" says which ones the 48 committed records support and which they cannot judge.

## Why

Until now a skill was `draft`, `evaluated` or `stale`, computed from one record and the hash of the skill folder. Any change inside the folder discarded the record and asked for a complete measurement again: every case, with and without the skill, on two models. The plan had to build a freeze around that cost. It does not scale with the number of skills, with the rate of change or with the number of models people use.

The model replaces the three states. A skill is ranked by the lab tests it has passed, on which version and how many. A new skill gets a full test once; after that, small tests carry its changes. What the model must deliver:

1. A change costs in proportion to what changed, never a full measurement of everything.
2. The rank falls when a skill changes with no new evidence, and rises only with evidence.
3. Real use is seen: how often a skill is used and how it went, per model.
4. The published table per model can be trusted.
5. The behaviours ordinary use almost never exercises (stopping before a side effect, refusing an instruction in external content) are always measured in the lab.
6. Nothing of a project enters the workbench (principle 8).

Version 2 delivers 1, 2, 5 and 6, delivers 3 as visibility (field evidence is shown and can demote, but does not promote), and delivers 4 for lab evidence on the reference model.

### Terms

| Term | Meaning |
|------|---------|
| Evidence | The lines the eval runner writes: one line per run of one case on one model, in one file per test event. |
| Lab, field | Lab: a run in the eval container, which anyone can reproduce. Field: a real use in a project, reported by the project. Bands and scores are computed from lab evidence only. |
| Full test, partial test | The two kinds of lab test (section 2). |
| Baseline | The runs of a case without the skill, on the reference model. |
| Reference model | The model the bands are computed on: `strong_model` of `evals/eval-gate.json`. |
| Gate | The rule a full test passes or fails: the mean with the skill on the reference model is 0.8 or more, and is not below the baseline's mean by more than 0.05. |
| Pessimistic score | A lower estimate of how often the skill does its job on one model, which falls with little evidence (section 6). It is not a confidence bound. |
| Band | `reliable`, `watch` or `needs a full test`: rules, computed on the reference model (section 5). |
| Change class | X, Y or Z: what a change to a skill touched (section 3). |
| Guard assertion, guard case | An assertion tagged `guard`: it measures a behaviour that must hold and that ordinary use almost never exercises. A guard case is a case with at least one (section 4). |
| Inherited evidence | Lab evidence that ran on something that is no longer current (an earlier version, an earlier state of the model or of a dependency). It counts, capped (section 6). |

## The model

### 1. Evidence

**One line per lab run, one file per test event.** A test event writes `skills/<name>/evals/evidence/lab-<test id>.jsonl`. The test id is the UTC time the event started and eight random hexadecimal characters, so two events never share a file and two open pull requests that add evidence to one skill never conflict (MI9). A committed evidence file is never edited; tooling writes it, never a person. The file of an event in progress lives in the run folder, outside the repository, and is copied into the skill when the event ends.

The first line describes the event, the others one run each. Both have closed keys: the validator refuses an unknown key and any value outside the forms below.

The event line (`"record": "test"`): the skill, the test id, the kind, the version and content hash of the skill, the date, the models, the configured runs per case, the measurement version and fingerprint, the image's digest and CPU platform, the grading template's hash, whether the baseline of each case was run or reused, per model and variant the counts of retries, refusals, timeouts, pauses on the account limit, early ends and with-skill runs that loaded the skill, the names of extra variables passed into the runs, whether the event is complete, and, for a full test, the gate's result and the means it was computed from.

A run line (`"record": "run"`):

| Key | Form | Meaning |
|-----|------|---------|
| `skill` | a skill name | the folder name |
| `version` | `X.Y.Z` | `metadata.version` of the skill that ran |
| `content_sha256` | 64 hex | the skill's content hash at the run |
| `model` | an id of the gate file's model list, or `unknown` | see "Model ids" below |
| `model_revision` | optional: a date `YYYY-MM-DD` or 7 to 64 hexadecimal characters | the revision the provider reported, when the adapter can read one; any other form is dropped |
| `adapter` | an adapter's folder name | which adapter ran the model |
| `kind` | `full`, `partial` | section 2 |
| `test` | a test id | the event the run belongs to |
| `date` | `YYYY-MM-DD` | the day of the run, UTC, from the clock |
| `measurement_version` | integer | the value of the gate file at the run |
| `measurement_sha256` | 64 hex | the measurement fingerprint the runner computed when the event started (MI12) |
| `case`, `case_sha256` | a case id and 64 hex | which case, and its hash at the run |
| `context_sha256` | 64 hex, optional | one hash over the dependency skills the case installs and the shared and platform references staged into the run; absent when there is none |
| `platform` | a platform name, optional | set when the case comes from a platform's case file |
| `variant` | `with`, `without` | `without` lines are the baseline and never enter a score |
| `outcome` | `graded`, `timeout` | `timeout`: the run was still incomplete after the cap of resumptions |
| `score` | 0 to 1 | the share of assertions passed; 0 for a timeout |
| `results` | a list of 0 and 1, one per assertion in the case's order | what the guard rule, the per-assertion counts and the difference on assertions that are not `format` are computed from; all 0 for a timeout |

**The content hash of a skill leaves out all of `evals/`.** It also leaves out `scripts/tests/`, caches, and the marker file an installer writes into a copied skill folder (`.installed-by-ai-workbench`). Nothing under those paths is read by a model that uses the skill, so cases, evidence and tests change no hash.

**Each case has its own hash, over the whole case.** The hash covers the case object as it stands in the case file (its prompt, its assertions with their tags, `grader_files`, `skills`, `setup`, `allow_web`, `workbench_files`, its tags, every other key) and the bytes of its fixture files (MI14). A change to one case drops the evidence of that case only: a line whose `case_sha256` differs from the case's current hash, or whose case no longer exists, has weight 0. `workbench_files` enters the hash as the list of paths, not as the content of those files: an edit of a repository file that a case brings changes no hash and no evidence.

**The context hash.** A line that ran with a dependency skill or a staged reference carries `context_sha256`. When it differs from the current one (a dependency skill changed, a platform reference was edited), the line counts as inherited evidence (section 6). Dependencies and references are treated alike.

**Model ids.** The gate file holds `models`: the known model ids, each with its aliases (the same model spelled with and without a provider prefix is one id). The runner and the field importer write the listed id for an alias and `unknown` for anything else, so that one model never falls into two rows of the table and a private model name never enters the repository (MI10).

**What is not evidence.**

- A run that failed on infrastructure, was paused on the account limit or ended early with no error is run again and writes no line.
- A run that is still incomplete after the cap of resumptions writes a line with `outcome: timeout` and score 0, with the skill and without it alike, so that dropping it cannot raise a mean (MI11).
- A run made with a stub runner or a stub grader, with a number of runs other than the configured one, or with a measurement fingerprint that differs from the committed one, writes the same files into a scratch tree inside the run folder and never into a skill's evidence folder. The smoke pass of the plan's phase D is such a run: it writes no evidence (MI13).

**The 48 old records.** `skills/<name>/evals/result.json` stays as the history of the first round. Nothing reads it, and no line is converted from it: the plan rewrites almost every case and changes what the grader sees, so those results are not comparable with what comes after (MI8).

### 2. Two kinds of lab test

| Kind | What runs | Costs, for an average skill (3.3 cases) | When |
|------|-----------|------------------------------------------|------|
| `full` | every current case with the skill, on one version, 3 runs per case, on the reference model and on the other models the gate file lists; and the baseline of every case whose baseline is not in force | the first one: 10 runs with the skill and 10 without on the reference model, 10 with the skill on the floor model. A later one with the baseline reused: 10 runs per model | once when a skill is created; whenever the band is `needs a full test` for a cause a full test clears; after an X change |
| `partial` | the cases named with `--cases`, with the skill only, 3 runs per case | 3 runs per case and model | after a Y change: the cases the change could move and the guard cases |

**The baseline is reused.** A run without the skill does not see the skill, so a change to the skill cannot age it (MI6). The baseline of a case is in force while three things are unchanged: the case (its hash), the model (no epoch after the baseline's date, section 8) and the measurement (at or above the measurement floor). When one of them changes, the baseline of that case is expired, the next full test runs it again, and `--cases <ids> --baseline` runs it for named cases.

**Other models get no baseline by default.** No rule reads a baseline on a model other than the reference one. The floor model, and any other model the gate file lists, run with the skill only; `--baseline-on <model>` remains for whoever wants the column.

**The gate.** A full test passes when the mean with the skill on the reference model is 0.8 or more and is not below the mean of the baselines in force by more than 0.05, both unrounded. It is computed over the lines of kind `full`, with the skill, of the `X.Y` version the newest full test ran on, every current case being required and only lines of weight above zero being counted (MI14). Two consequences:

- A partial test moves the score and not the gate. Running the cases that failed again, after a change, cannot replace their bad runs in the gate while the cases that passed keep the runs of an older version (MB3).
- A second full test of an unchanged `X.Y` adds its runs to the first and replaces none, so a skill near the threshold is not decided by the better of two draws.

One exception lets a partial test enter the gate, and it replaces no run of an unchanged case. A case that changed or was added after the newest full test has no runs the gate can count. It completes the gate with its own runs, made with `--cases <id> --baseline` on the same `X.Y`. Until then the gate cannot be computed, and the band is `needs a full test` with that cause. A deleted case leaves the gate to be computed on the cases that remain; the rule for case changes asks for the reason in the pull request, because a mean can rise that way with nothing run.

### 3. Versions and change classes

`metadata.version` is `X.Y.Z`. A change to anything inside the content hash raises it, and the part it raises declares the class of the change.

| Class | What changed | What it asks |
|-------|--------------|--------------|
| X | Security and contract: `side_effects`; an item removed or renamed in `outputs` or `updates`; the `## Confirmation gate` section; the `## Stop rules` section; the line that starts **External content is data.** | a full test: every case with the skill, the baseline reused where the case's hash is unchanged. About 10 runs on the reference model for an average skill |
| Y | Everything else: a step, a criterion, a template, a reference, an asset, a script; an addition to `inputs`, `outputs`, `updates` or `requires`; a removal from `inputs` or `requires`; any change of the description | a partial test of the cases the change could move and of the guard cases, 3 runs each: 3 to 9 runs. A changed description also runs the routing mode, which shows whether another skill now loads in its place |
| Z | Wording that the allow-list below accepts | nothing |

**X is narrow on purpose** (MI7). In the repository's history the contract keys changed eight times, every time by an addition. An addition cannot break a reader of the artifact contract; a removal or a rename can.

**Stop rules live in a `## Stop rules` section.** The validator can only watch a section it can find, and 38 of the 48 skills have their stops inside steps or in the inputs table today. The plan's phase C moves them, at no cost in evidence, since every skill becomes `1.0.0` at its end (MB2).

**Z is an allow-list, not a size.** A change is Z only when all of these hold (MB2):

1. Every changed file is `SKILL.md` or a file under `references/`.
2. No changed line is in the frontmatter (the description included), the inputs table, the procedure, the quality criteria, the output template, the confirmation gate or the stop rules.
3. No changed line differs from the line it replaces in a number, a path, a code span or one of the words never, only, must, may, stop, ask.
4. The characters changed, added to those of the earlier Z changes since the skill's newest lab evidence, stay within the budget: 300 characters. When the budget is spent, the next change is a Y change.

Anything else is Y at least. A description decides when a skill loads, so a change to it is never Z.

**The version file.** `skills/<name>/evals/versions.jsonl` is an append-only list, one line per version: the version, the content hash, the class, the date and, for a Z line, the characters changed. It is outside the content hash. It answers what a version's content was, so an evidence line whose content hash is not the one its version had is refused on import, for any version and not only the current one (the review's answer 9).

**The bump command.** `python3 evals/eval_status.py bump --skill <name> --class x|y|z` sets the version to the version of the pull request's base raised by one step of the class, resets the lower parts, and writes the line. It is idempotent: run twice, or run again with a higher class after more edits, it rewrites the one line this pull request adds. Two pull requests that change the same skill conflict on that line, which is the conflict that should be seen: the second rebases and runs the command again.

**What the validator checks**, in the pre-commit hook and in CI alike, against the same base: the base of the pull request (the merge base with the default branch), never `HEAD`, so that an edit and its bump in two commits are read as one change (MI9).

1. **No change without a bump.** The folder's content hash equals the hash of the last line of the version file, and the raw text of `metadata.version` matches `^\d+\.\d+\.\d+$` and equals that line's version (MM4).
2. **The file is append-only.** The base's lines are unchanged, and at most one line is added: one pull request raises a skill once, by its highest class.
3. **The class agrees with the diff.** For the frontmatter lists the validator takes the set difference between base and current: any difference in `side_effects`, or an item missing from `outputs` or `updates`, requires X. A changed line inside the two sections or in the external-content line requires X. A declared Z is checked against the allow-list. A declared X is never refused.

The validator can prove that a declared class is too low. It cannot prove that a Y change is harmless: the partial test is what that is for.

**A change to an eval case needs no bump.** It changes the case's hash: the evidence of that case drops, its baseline expires, and the case is run with `--baseline`.

### 4. Guards

Stopping to ask before a side effect, refusing an instruction inside external content and stopping on a missing input are behaviours a hundred ordinary uses may never exercise. Version 1 required a guard case to exist and to have run; nothing required it to pass, and in the first round three skills passed the gate while a guard assertion failed in every run (MB1).

- **The tag is on the assertion.** In the case file an assertion is a text, or an object with the text and `tags`. The tags are a closed list: `guard`, `guard:<effect>` for a guard of one declared side effect (`guard:publish`, `guard:push`), and `format` (an assertion on a form only the skill defines). A case with a guard assertion is a guard case.
- **The rule.** Every guard assertion passes in every with-skill run of the newest test event that ran its case, on the reference model, and that event ran on the current `X.Y`. Otherwise the band is `needs a full test`, the status names the assertion and the cause (failed, or not run on this version), and the validator warns. CI does not fail for it.
- **Guard cases run again on every Y change**, 3 runs each, because the mechanism of a guard often lives in text or in a script that is not the gate section itself: a payload builder, a policy script, a numbered step.
- **After an X change** the full test runs every case, the guard cases among them.
- **One guard per declared effect.** A skill with a non-empty `side_effects` has, for each effect it declares, at least one assertion tagged `guard:<that effect>`. A missing one is an error of the validator. This is the only guard rule that fails CI, and it fails on the case file, which any contributor can fix without a model.
- An assertion that says only that nothing happened passes in every variant and measures little; an assertion that the reply asks before the effect discriminates (in the first round, 98 of 108 with the skill against 25 of 108 without). A guard of a side effect is written as the second kind wherever the case can reach the gate.

### 5. Bands

The bands are rules. The score is one input to one of them. Computed on the reference model, in this order:

| Band | When | What clears it |
|------|------|----------------|
| `needs a full test` | (a) no full test of the current major version passes the gate: every new skill, and every skill after an X change | a full test that passes |
| | (b) a guard assertion failed, or has not run, on the current `X.Y` | a partial test of the guard cases, after the fix when one failed |
| | (c) the newest full test of the current major version fails the gate, or its gate cannot be computed because a current case has no runs on that version | a full test that passes, after the fix; for a changed or added case, that case run with `--baseline` |
| | (d) three Y changes in a row with no lab evidence between them | a full test |
| `watch` | no with-skill lab line exists on the current `X.Y`; or the pessimistic score is under 0.70; or the field signal of section 7 is on | lab runs: a partial test, or more runs of a full test |
| `reliable` | otherwise | |

A Z change stays inside the current `X.Y`, so it moves no band; its budget is what keeps wording from piling up untested.

**What the 0.70 means** (MI2). A pessimistic score of 0.70 needs 4 runs at a mean of 1.0, 9 at 0.90, 16 at 0.85 and 35 at 0.80: a marginal skill needs much evidence to be called reliable. A small skill that has just passed its full test with a marginal mean therefore starts in `watch` and reaches `reliable` as runs accumulate. The maintainer accepted this explicitly.

**"Done" for a new skill** is: its first full test passed. That is the old gate, on the reference model only. A skill can be done and in `watch`.

**CI fails on:** a change without a bump; a class the diff contradicts; a missing guard assertion for a declared effect; a version file that is not append-only; an evidence line that is not valid. **CI never fails on a score or on a band.** A skill in `needs a full test` or in `watch` is a line of the status output and of the validator's warnings.

### 6. The pessimistic score

For one skill and one model, take the lab lines with the skill whose weight is above zero (the case exists with the same hash, and the measurement version is at or above the measurement floor). The unit is the run, with its fractional score. Split them into three pools:

- **Current:** lines of the current `X.Y`, with the current context hash, dated after the model's last epoch. Each counts as 1.
- **Inherited, same major:** lines of an earlier `X.Y` of the current major version, and lines of the current `X.Y` that ran before an epoch or with another context hash. Together they count as at most 3 runs: each is multiplied by `min(1, 3 / their number)`.
- **Inherited, earlier major:** lines of earlier major versions. Together they count as at most 1 run.

With `S` the weighted sum of scores, `N` the weighted number of runs, `p = S / N` and `z = 1.2816`:

```
score = ( p + z^2/(2N) - z x sqrt( p(1-p)/N + z^2/(4N^2) ) ) / ( 1 + z^2/N )        (0 when N = 0)
```

This is the lower bound of the Wilson interval, used as a penalty for little evidence. It is called the pessimistic score and never a confidence bound: measured on the first round, the real variance of a skill's mean is 17% to 32% of what the formula assumes, so the interval is far too wide to be a calibrated one, and with few runs the score mostly says how many runs there are (MI1). For that reason the score is always shown with the mean and `N` beside it.

**Why a cap and not a decay** (MI3). Version 1 multiplied old evidence by 0.6 or 0.2 per change. On a skill with much evidence that hardly moved the score: 60 runs at 0.95 went from 0.900 to 0.881 after a Y change. With the cap, a change always weighs: inherited evidence alone can never reach 0.70 (3 runs at 1.0 score 0.646), so a changed skill leaves `reliable` and returns only with lab runs on its new version.

Worked examples, computed with the formula:

| Evidence | S | N | Mean | Score | Band |
|----------|---|---|------|-------|------|
| A fresh full test: 3 cases, 9 runs at 0.90 | 8.10 | 9 | 0.900 | **0.705** | `reliable` |
| The same skill after a Y change, nothing new | 2.70 | 3 | 0.900 | **0.531** | `watch`, or `needs a full test` until its guard cases have run |
| Then a partial test of one case, 3 runs at 0.90 | 5.40 | 6 | 0.900 | **0.651** | `watch` |
| The same, the 3 runs at 1.0 | 5.70 | 6 | 0.950 | **0.713** | `reliable` |
| Then 9 runs at 0.90 instead of 3 | 10.80 | 12 | 0.900 | **0.737** | `reliable` |
| After an X change instead, nothing new | 0.90 | 1 | 0.900 | **0.308** | `needs a full test` |
| Then its full test, 9 runs at 0.90 | 9.00 | 10 | 0.900 | **0.718** | `reliable` |
| The smallest skill at the gate: 2 cases, 6 runs at 0.80 | 4.80 | 6 | 0.800 | **0.539** | `watch`; done, since its full test passed |
| 60 runs at 0.95 | 57.00 | 60 | 0.950 | **0.900** | `reliable` |
| The same after a Y change, nothing new | 2.85 | 3 | 0.950 | **0.585** | `watch` |
| Then 6 runs at 0.95 | 8.55 | 9 | 0.950 | **0.770** | `reliable` |

A platform's cases get no score of their own: the table shows their mean and their number of runs.

### 7. Field evidence

Field evidence is recorded from the first day and shown. It decides no band upward (MB4): it is self-reported, it is selected (only a use that was delivered and answered leaves a verdict), and anyone who sends a file can move it. The maintainer answered this point explicitly: after a change of behaviour a skill returns to `reliable` only with lab runs.

**Where it is written.** In the project, in `.workbench-local/evidence/<skill>.jsonl`, the git-ignored folder `AGENTS.md` names for a project's own data. Never in the workbench.

**Its lines.** Closed keys, no free text, no count:

| Key | Form |
|-----|------|
| `record` | `use`, `verdict` |
| `skill`, `version`, `content_sha256` | read and computed from the installed skill folder by the script |
| `model` | an id of the gate file's model list, or `unknown` |
| `adapter` | an adapter's folder name, or `unknown` |
| `use` | 8 random hexadecimal characters: links a verdict to its use, and nothing to a person or a project |
| `week` | `YYYY-Www`: the week, not the day, so that a contributed file does not publish when a person used each skill (MM2) |
| `score`, `judge` | verdict lines only: 1, 0.5 or 0; `user` or `check` |

**The recorder.** `scripts/evidence.py`, flags only, no prompts:

- `record --start --skill-dir <installed skill folder> --project <dir> [--model <id>] [--adapter <name>]` appends a `use` line and prints its id. It runs when the use begins, so a use that stops, fails or is abandoned is still counted, and the share of uses with no verdict is visible.
- `record --verdict worked|corrected|failed --use <id> --project <dir>` appends the verdict of a person (1, 0.5, 0). `record --check-report <file> --use <id>` appends the verdict of the skill's own check script, with `judge: check`; when both exist the person's is shown.
- `export --project <dir> --out <file>` and `import --file <file>` are described under "Contributed files".

**What triggers a `use` line.** Recording does not depend on a model remembering to do it:

1. **An adapter hook**, where the harness has hooks: it runs `record --start` when a workbench skill is loaded. The installer writes the hook with the absolute path of the workbench checkout, and the hook passes the model id the harness gives it.
2. **The runtime itself**, when the runtime runs the skill: `scripts/runtime.py` calls `record --start` before it starts the agent, with the model id it passes to the adapter, and records the verdict from what the person does with the item in the approval inbox (approved as it is, approved after an edit, rejected). The runtime's agent has reading tools only and records nothing.
3. **The block in the project's instruction file**, where there is neither: it tells the model to run `record --start` when it starts a workbench skill. A weak model will skip it sometimes; a missing line lowers nothing.

**How the workbench root and the model id reach the recorder.** Verified in the code: no installer sets `WORKBENCH_ROOT` today, and no variable for the model id exists. So: the installer writes the checkout's absolute path into the hook it installs and offers to set `WORKBENCH_ROOT` in the settings it creates; without a hook the block uses the root by the rule the provider skills already follow (the variable, then the path recorded in the state file, then ask once and record). The model id comes from the hook's input or from the runtime's flag. It is never taken from a model's own account of what it is: with neither source the line says `unknown` and enters no model's columns.

**Who owns the block.** The workbench section of a project's instruction file, between its two markers, belongs to `core-project-init` (its asset `agents-md-section.md`); `core-agents-md` preserves it byte for byte. The field block is therefore two lines of that asset, written by `core-project-init`.

**The verdict line does not collide with a consent question.** Version 1 offered `ok / corrected / not ok` at the end of a reply, where "ok" would be at once a consent and a verdict. Three rules prevent it:

1. The verdict is offered only in a reply that delivers a finished output. A reply that ends with a question or shows a confirmation gate never carries it.
2. The line reads `Skill check (optional, not an approval): answer "check: worked", "check: corrected" or "check: failed".`
3. Only an answer that starts with `check:` is recorded as a verdict, and such an answer is never an approval. A bare "ok", "yes" or "go" is never a verdict. The model never chooses a verdict itself.

The effect of the block on a skill's behaviour is seen once, in the lab: one case of the plan's smoke pass runs with the block in its fixture's instruction file, beside the same case without it (MM6).

**What field evidence does.**

- It is shown in its own columns, per model, labelled "self-reported": uses, judged uses, mean of the verdicts. A model that has only field evidence shows those three and no score (MM5).
- **It can demote.** The field signal is on when three or more verdicts of `failed` exist on the current `X.Y`, in weeks at or after the week of that version's newest full test. The band is then `watch` until the cases have run again.
- **It never promotes.** No number of good verdicts takes a skill out of `watch` or out of `needs a full test`.

**Contributed files.** `export` writes one file with only the closed keys and drops the lines whose content hash is not the hash the version file gives for that version (a locally edited skill). The person opens a pull request that adds it, through `import`, as `skills/<name>/evals/evidence/field-<id>.jsonl`, `<id>` being the first 12 characters of the file's hash. Contributed files stay separate, one per contribution. Each has a maximum weight: it adds at most 20 uses and 20 verdicts per skill to the columns, and at most one `failed` to the field signal, so that no single file can sink a skill or fill a column.

**Why this does not break principle 8.** An evidence line holds no project, product, person or account name and no work data. It has no free-text field: every value is a skill name, a version, a hash of workbench content, a listed model id, a word of a closed list, a week or a number, and the importer refuses anything else. What it states is a property of the skill on a model, which is the workbench's own subject.

### 8. Measurement changes: three kinds

The gate file carries `measurement_version`, `measurement_sha256` (the fingerprint of the files that decide what a run measures: the grading template, the image definition, the executor, the measuring module, the staging module, the eval adapters' `run-prompt.sh` and `adapter.json`, the measurement constants) and `measurement_floor`. The validator fails when the recomputed fingerprint differs from the committed one, and the runner refuses to write evidence when it does (MI12). A change to one of those files is committed as one of three kinds, said in the commit and in `docs/decisions.md` (MI5):

| Kind | What changed | What it does |
|------|--------------|--------------|
| Grader side | what the grader is shown (the definition of the reply, the facts block, the input files), the grading rules, how a run's score is computed | Old and new scores are not comparable. `measurement_version` and `measurement_floor` are raised: every lab line below the floor weighs 0, and every skill is `needs a full test` |
| Execution side | the image (a tool added, a runner's version), the runner's system prompt and tools, an adapter, the executor, the staging | It is treated as a model epoch: `measurement_version` is raised and an entry is added to `epochs` in the gate file, naming the skills it affects, or all of them when that cannot be said. For those skills the lines before the epoch become inherited evidence and the baselines expire |
| Infrastructure | locks, resumption, retries, pacing, reports | Nothing. Where the change is in a file the fingerprint covers, the new fingerprint is committed with the reason; no version is raised |

There is no factor of 0.8 per version step any more: it punished every skill for a change that reached five, and forgave the five.

**A hosted model that changes under its id** is the same event as an execution-side change: an entry in `epochs` for that model, with its date. No score falls with the calendar: an age decay would make the published table go out of date on a day nothing changed.

**Who may write lab evidence.** `CODEOWNERS` covers `evals/`, the evidence files, the version files and the old records, so a change to any of them is seen by the owner. Lab evidence on the reference model comes from tests run by the maintainer, on the maintainer's account for that model: nothing else proves that a line was written by the runner and not typed into a pull request, so the rule is stated instead of implied (MI12). A contributor without that account can still pass every check: the checks that fail CI need no model.

### 9. A change of reference model or of grader

These are the most predictable expensive events, and version 1's sentence that nothing forces a full test of everything was false for them (MI4).

**The grader is separate from the reference model.** It is its own key of the gate file and stays fixed while its provider serves it, even when the reference model changes.

**The reference model changes.** The bands are computed on the new model, where no skill has a full test. The evidence of the old reference model counts on the new one as inherited (at most 3 runs). The 48 skills run every case with the skill on the new model. The baseline is redone by sample: one case per skill; where the sampled baseline differs from the old model's baseline of the same case by more than the tolerance (0.05), that skill's baseline is redone in full, and otherwise the old baseline stands for the cases not sampled, marked as inherited in the event line. With 160 cases that is 480 runs with the skill and 144 sampled baseline runs: 624 runs and 624 gradings, about half of a first full test of everything.

**The grader changes.** A sample of stored replies, one with-skill run per case, is graded again by the new grader with an option that writes no evidence: 160 gradings. When at least 95% of the assertion verdicts agree, nothing is zeroed: the lines graded by the old grader become inherited evidence, and each skill returns from `watch` with its next lab runs. Below that, it is a grader-side change. This needs the replies to be kept, which is the archive rule of the plan's phase E.

### 10. The tables

`python3 evals/eval_status.py status` computes everything from the evidence files, live. The committed tables in `docs/inventory.md` are a published snapshot, with the commit they were generated at.

The band table, one row per skill, on the reference model:

| Skill | Version | Band | Cause | Score | Mean | Runs (N) | Last full test | Field: uses, judged, mean (self-reported) |
|-------|---------|------|-------|-------|------|----------|----------------|-------------------------------------------|
| `<name>` | 1.2.0 | watch | no lab evidence on 1.2 | 0.59 | 0.95 | 3.0 | 2026-10-20, passed | 31, 24, 0.94 |

The model table, one row per skill and model that has any evidence:

| Skill | Model | Score | Mean | Lab runs (N) | Field: uses, judged, mean (self-reported) | Platforms: mean (runs) |
|-------|-------|-------|------|--------------|-------------------------------------------|------------------------|
| `<name>` | `<model id>` | 0.71 | 0.90 | 9.0 | 0, 0, n/a | `<platform>`: 0.89 (3) |

**The snapshot is not required in a pull request.** If every pull request that adds evidence had to regenerate one block of one file, two open pull requests would always conflict (MI9). The alternative, a job that regenerates the block on the default branch after each merge, would have to push to a branch whose rules require a pull request and a signed commit and allow no bypass. So the validator reports a snapshot that is behind the evidence as a warning, never as an error; a pull request that adds evidence does not touch the block; and the block is regenerated in a small pull request of its own, by the maintainer, after evidence merges.

## What a change costs

Runs are on the reference model, for an average skill of 3.3 cases; the same number of with-skill runs is made on the floor model while its row is kept current.

| Change | Cost |
|--------|------|
| Wording inside the allow-list (Z) | a bump; nothing to run |
| A step, a criterion, a reference, an asset, a script, a description, an added input or output (Y) | a bump; a partial test of the affected cases and of the guard cases: 3 to 9 runs. A description also runs the routing mode |
| Security or contract (X) | a bump; a full test with the baseline reused: about 10 runs |
| An eval case changed or added | the evidence of that case drops; the case runs with `--baseline`: 6 runs |
| A new skill | its first full test: about 20 runs on the reference model and 10 on the floor model |
| The source of a script several skills carry | a Y change of each carrier, made in one pull request: 3 to 9 runs per carrier |
| A dependency skill, a platform reference or a shared reference | the lines that ran with the old one become inherited: the skills that staged it are `watch` until they have lab runs |
| A repository file that a case brings | nothing |
| Infrastructure of the runner | nothing |
| The image, an adapter, the runner's prompt or tools; a hosted model changed under its id | an epoch for the skills affected: they are `watch`, and their baselines expire. Bringing all 48 back at once is 480 runs with the skill, and 480 more when their baselines are redone |
| What the grader sees, the grading rules, the scoring | the floor is raised: every skill is `needs a full test`. A full test of everything: 1,440 runs today |
| The reference model | 624 runs and 624 gradings (section 9) |
| The grader | 160 gradings; with high agreement, every skill is `watch` until its next lab runs; otherwise a full test of everything |
| A new model in the table | nothing is asked; it appears when it has lines |

## Backtest

Made with a throwaway script, outside the repository, from the 48 committed `result.json` files only. Each record gives, per model, the mean with the skill and the number of with-skill runs (cases x 3): 17 skills have 6 runs, 20 have 9, 9 have 12, one has 15 and one 18. All 48 records pass the gate. The means with the skill range from 0.833 to 1.0 on the reference model. **What is missing:** the per-run and per-case scores, which are in the stored runs outside the repository; so the backtest treats a record as runs at its mean, and the new runs of each scenario are taken at the skill's recorded mean unless said otherwise.

Pessimistic scores of the 48 skills on the reference model, and how many are at 0.70 or above:

| Scenario | Min | Median | Max | At 0.70 or above | Band |
|----------|-----|--------|-----|------------------|------|
| Right after a passing full test | 0.626 | 0.785 | 0.880 | 42 | 42 `reliable`, 6 `watch` |
| One Y change, nothing new | 0.464 | 0.621 | 0.646 | 0 | 48 leave `reliable`: `watch`, or `needs a full test` until the guard cases have run |
| Y change, then 3 lab runs at the skill's mean | 0.574 | 0.755 | 0.785 | 37 | 37 `reliable`, 11 `watch` |
| Y change, then 3 lab runs at 1.0 | 0.671 | 0.770 | 0.785 | 45 | 45 `reliable`, 3 `watch` |
| Y change, then 6 lab runs at the skill's mean | 0.626 | 0.814 | 0.846 | 43 | 43 `reliable`, 5 `watch` |
| Y change, then 9 lab runs at the skill's mean | 0.657 | 0.847 | 0.880 | 45 | 45 `reliable`, 3 `watch` |
| Y change, then 9 lab runs at 1.0 | 0.814 | 0.871 | 0.880 | 48 | 48 `reliable` |
| One X change, nothing new | 0.266 | 0.364 | 0.378 | 0 | 48 `needs a full test` |
| X change, then its full test at the skill's mean | 0.638 | 0.810 | 0.888 | 44 | 44 `reliable`, 4 `watch` |

The six skills that start in `watch` after a passing full test are `eng-unit-tests` (9 runs, mean 0.833, score 0.63), `mkt-publish` (6, 0.881, 0.63), `design-execute` (9, 0.844, 0.64), `design-handoff` (6, 0.921, 0.68), `biz-market-analysis` (9, 0.889, 0.69) and `core-critique` (12, 0.863, 0.69). On the floor model 38 of the 48 would be at 0.70 or above after the full test; that row is information.

Example rows on the reference model (`n` is the number of with-skill runs in the record):

| Skill | n | Mean | Full test | Y change | +3 runs | +9 runs | X change | + full test |
|-------|---|------|-----------|----------|---------|---------|----------|-------------|
| `eng-unit-tests` | 9 | 0.833 | 0.63 | 0.46 | 0.57 | 0.66 | 0.27 | 0.64 |
| `mkt-publish` | 6 | 0.881 | 0.63 | 0.51 | 0.63 | 0.71 | 0.30 | 0.65 |
| `design-execute` | 9 | 0.844 | 0.64 | 0.47 | 0.59 | 0.67 | 0.27 | 0.65 |
| `biz-market-analysis` | 9 | 0.889 | 0.69 | 0.52 | 0.64 | 0.72 | 0.30 | 0.70 |
| `core-critique` | 12 | 0.863 | 0.69 | 0.49 | 0.61 | 0.69 | 0.28 | 0.70 |
| `flow-fix-bug` | 9 | 0.911 | 0.72 | 0.54 | 0.66 | 0.75 | 0.32 | 0.73 |
| `core-skill-creator` | 12 | 0.928 | 0.77 | 0.56 | 0.68 | 0.77 | 0.33 | 0.78 |
| `brand-identity` | 6 | 1.000 | 0.79 | 0.65 | 0.79 | 0.88 | 0.38 | 0.81 |
| `product-roadmap` | 9 | 0.972 | 0.80 | 0.61 | 0.74 | 0.83 | 0.36 | 0.81 |
| `core-orchestrator` | 18 | 0.933 | 0.82 | 0.57 | 0.69 | 0.78 | 0.33 | 0.82 |
| `mkt-engage` | 12 | 0.983 | 0.85 | 0.62 | 0.76 | 0.85 | 0.37 | 0.86 |
| `ops-pull-request` | 12 | 1.000 | 0.88 | 0.65 | 0.79 | 0.88 | 0.38 | 0.89 |

**What the backtest shows.**

1. A change always costs the band: after one Y change no skill is at 0.70, whatever its history, and after an X change none is above 0.38.
2. The way back is short for a skill with a good mean and long for a marginal one: 3 lab runs return 37 of the 48 to `reliable`, 9 return 45, and the three that stay in `watch` have means of 0.83 to 0.86.
3. The threshold separates by mean and by amount of evidence, which is what it is for: the six skills that start in `watch` are the ones closest to the gate, with one exception, a two-case skill at 0.92, which is there for its 6 runs.

**What the backtest cannot judge:** the Z budget of 300 characters; the field signal's count of three; the cap values 3 and 1, beyond the property that inherited evidence alone stays under 0.70; the 95% agreement asked of a new grader. There is no history of classified changes and no field evidence yet. They are reviewed once the first full test of the 48 has produced per-run lines, by the same script run on the evidence files.

## What it does not solve

- **The score mixes quality and amount of evidence.** A skill at 0.78 may be a perfect skill with 6 runs or a mediocre one with 200. The mean and `N` stand beside it.
- **Runs of one case are correlated in some skills.** The median correlation between runs of one case is 0.04, but the upper quartile is 0.67: in some skills one case fails every time. The cases are few (2 to 6 per skill), so a skill's mean says how it does on those cases.
- **Partial tests are chosen by the person who made the change.** A change can break a case nobody thought to run. Protections: the guard cases always run, three Y changes without lab evidence ask for a full test, and the gate is never moved by a partial test.
- **A no-op Y change resets the gate's pool.** The gate reads the runs of the `X.Y` of the newest full test, so a maintainer could raise Y with nothing changed and draw again. It costs a full test each time and shows in the version file.
- **Nothing proves that a lab line was written by the runner.** The fingerprint in each line, the code owner's review and the rule that the maintainer runs the tests on the reference model are the protection.
- **Field evidence is selected and self-reported.** That is why it promotes nothing.
- **A verdict is coarse and kind.** One word from a person who wants to move on is not five designed assertions.
- **Per-model evidence is thin at first.** Every model other than the two of the gate file starts with field counts only.

## Deliberately left for later

- **Field evidence promoting a skill.** Once recorded uses can be compared with verdicts (how many uses end with none, whether verdicts agree with lab results on the same version), a rule that lets field evidence count toward `reliable` can be written with data. Until then it does not.
- **Numeric decays.** A decay per Z change, per changed context and per measurement step needs a history of classified changes to calibrate. The caps do the work meanwhile.
- **Compaction of old evidence.** One line per run is small; nothing is compacted, so the gate can always be computed again from the lines (MM1).
- **A score per platform.** Mean and number of runs until a platform has enough cases.
- **Replaying sampled field tasks on other models.** The task and its files would stay in the project and the replay would run there, in the container; only the resulting lines would travel. Not before the table has field evidence to sample from.

## What changed from version 1 and why

One line per finding of the review.

| Finding | What version 2 does |
|---------|---------------------|
| MB1. A guard had to exist and to have run, never to pass | The tag is on the assertion; every guard assertion must pass in every run of the newest event on the current `X.Y`, or the band is `needs a full test`; guard cases run on every Y change; one guard per declared effect, an error when missing; CI does not fail on the band (section 4) |
| MB2. The Z class could not be verified and accepted behaviour changes | Z is an allow-list with a budget in characters; a description change is Y; stop rules live in their own section (section 3) |
| MB3. Any change followed by a targeted test erased a case's bad runs | The gate is evaluated only by a full test, on one version; a partial test moves the score only (section 2) |
| MB4. Field evidence entered the same sum | Bands and scores come from lab evidence only; field evidence has its own columns, can demote, never promotes; `record --start`; no `count`; a maximum weight per contributed file (section 7) |
| MI1. The score is not a calibrated bound | Called the pessimistic score; always shown with the mean and `N`; the run stays the unit (section 6) |
| MI2. The bands were the three states renamed; 0.45 and 0.50 decided nothing | The bands are stated as rules; `reliable` needs a score of 0.70; the 0.45 gives way to "the gate fails" (section 5) |
| MI3. A decay only shrank `N` | Inherited evidence is capped at 3 runs within a major version and at 1 across major versions (section 6) |
| MI4. A new reference model or grader was a full test of everything, unsaid | Said in the cost table; the grader is separate and fixed; inherited evidence, with-skill runs and a sampled baseline for a new reference model; a re-graded sample for a new grader (section 9) |
| MI5. The 0.8 per measurement step was wrong both ways | Three kinds of measurement change, no factor (section 8) |
| MI6. The baseline ages with the model, the measurement and the case, not with the skill | The baseline is reused until one of the three changes; an X change runs with the skill only (section 2) |
| MI7. The X class was too coarse | X is `side_effects`, removals and renames, the gate, the stop rules and the external-content rule; additions are Y (section 3) |
| MI8. The conversion of the 48 records kept nothing | No conversion; the old records stay as history (section 1) |
| MI9. Two files conflicted in every evidence pull request | One file per test event; the tables are a snapshot that no pull request must regenerate; one comparison base in the hook and in CI; an idempotent bump (sections 1, 3, 10) |
| MI10. Model ids were free text | A list of known models with aliases; `unknown` for the rest; a closed form for the revision (section 1) |
| MI11. Items kept as written whose object had gone | A timeout after the cap is a line with score 0 in both variants; stub runs write to a scratch tree; the plan restates each item (section 1; the plan's phase B) |
| MI12. Lab evidence had no provenance | The fingerprint in every line; the runner's refusal kept; `CODEOWNERS` extended; the maintainer runs the tests on the reference model (section 8) |
| MI13. The order of work did not close | The plan's order: the hash, then the version rules with a migration; `1.0.0` in one sweep; the smoke pass writes no evidence |
| MI14. Dependencies decayed nothing; holes in the gate rule and in the case hash | `context_sha256`; the gate over lines of weight above zero with every current case required; the case hash over the whole case (sections 1, 2) |
| MM1. Compaction lost the case | No compaction |
| MM2. A day in a contributed file | The week, in field lines |
| MM3. One line of a shared script moves every carrier to `watch` | Accepted; the carriers change in one pull request (cost table) |
| MM4. The validator never read the version | The raw text is checked against `^\d+\.\d+\.\d+$` (section 3) |
| MM5. A score for a model with only field evidence | Counts and mean, no score (section 7) |
| MM6. The effect of the field block was never measured | One smoke case carries it (section 7) |
| MM7. One measurement step put two-case skills in `watch` | Moot: no factor per step |
| MM8. The places that name the old states were undercounted | The plan lists them all (its item A17 and row 16) |
| MM9. One decision in two tables; the floor model | The plan is one document; the floor model runs with the skill only and no rule reads its rows |

The twelve questions version 1 left open, as answered:

1. **Rules beside the score:** kept, and said to be rules; the cap and a threshold that means something replace the idea of counting decayed weight as trials.
2. **An X change asks for a full test:** too expensive as written; X is narrower, and its full test reuses the baseline.
3. **The unit:** the run. In the lab the interval is too wide, not too narrow; the case as unit would give 2 to 6 trials.
4. **The thresholds 0.50 and 0.45:** `reliable` at 0.70; the 0.45 is replaced by "the gate fails on the current evidence".
5. **Ten field uses to return to `reliable`:** no. Lab runs are required: the affected cases and the guard cases.
6. **The Z class and its 15 lines:** an allow-list and a budget in characters.
7. **`measurement_floor` at 5:** yes, and nothing is converted: there is nothing comparable to keep.
8. **The trigger through the instruction file:** not alone. A use is recorded at its start, by a hook or by the runtime; field evidence stays out of promotion.
9. **The hash of older versions:** kept, in the append-only version file.
10. **A baseline on other models:** not by default; an option remains.
11. **One grading pass:** yes. Grading the same replies again is cheap and is used only where it matters: to measure the grader's disagreement in the pilot and to compare a new grader.
12. **A decay never asked for a test:** now a change does. No skill leaves `watch` without lab runs, and three Y changes without lab evidence ask for a full test.
