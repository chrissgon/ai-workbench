# The reliability model, 2026-10-02: evidence per model instead of three states

**Status: decided in outline by the maintainer on 2026-10-02; this document writes it out and awaits review.** It states the model, backtests it on the 48 committed records, and lists what it changes in the plan in force, `final-plan-2026-10-02.md`. Where the two differ, this document wins; the changes are folded into the plan after this document's review. Every number called a parameter below is a starting value, and the section "Backtest" says which ones the data supports and which it cannot yet judge.

## Why

Today a skill is `draft`, `evaluated` or `stale`, computed from one record (`skills/<name>/evals/result.json`) and the hash of the skill folder. Any change inside the folder turns `evaluated` into `stale`, discards the record as evidence and asks for a complete measurement again: every case, with and without the skill, on two models. The plan in force builds a freeze around that rule (a fingerprint, a strict mode in CI, one "last" round of 3,140 runs) because every later change costs a full measurement. That does not scale with the number of skills, with the rate of change or with the number of models people use.

The decision: a skill is ranked by the tests it has passed. Tests are complete or partial; the rank depends on how many there are, on which version of the skill they ran and on their kind. A complete test made long ago on an older version is worth little; many partial tests from daily use on current versions, with good results, can make a skill reliable. A new skill gets a complete test once; after that, partial tests carry its evolution. The score is per model. The floor model is no longer a requirement; it is information. As more people use the workbench with different models, the table shows how each skill does on each of them.

### Terms

| Term | Meaning |
|------|---------|
| Evidence entry | One line of an evidence file: one run of a skill on one model, with its kind, version, score and who judged it. |
| Lab, field | Where an entry comes from. `lab`: a run in the eval container, which anyone can reproduce. `field`: a real use in a project, reported by the person who made it. |
| Full, targeted, field | The three kinds of test (section 2). |
| Reference model | The model the bands are computed on: `strong_model` of `evals/eval-gate.json`. |
| Score | The pessimistic estimate of how often the skill does its job on one model: a lower confidence bound over weighted evidence (section 3). |
| Band | `reliable`, `watch` or `needs a full test`, computed from the score and three rules, on the reference model (section 6). |
| Bump class | Z, Y or X: how much a change to a skill altered (section 4). |
| Guard case | A case tagged `guard`: it measures a behaviour ordinary use almost never exercises (section 5). |

## The model

### 1. Evidence, not a record

Every test event appends one entry per run. Entries are never edited or removed by hand; tooling writes them.

**Where.** `skills/<name>/evals/evidence/lab.jsonl` for lab entries, written by the eval runner. `skills/<name>/evals/evidence/field-<id>.jsonl` for contributed field entries, one file per contribution, `<id>` being the first 12 characters of the file's own hash, so that two contributions never touch the same file and no pull request conflicts on an append. Both live under `evals/`, which the adapters already remove from the copy of a skill a model sees.

**The content hash changes.** Today the hash of a skill folder leaves out the record and `scripts/tests/`. It now leaves out all of `evals/`: nothing under that folder is read by a model that uses the skill. Each case gets a hash of its own (its prompt, its assertions, its fixture files), carried by every entry that came from it. This is what lets a change to one case drop the evidence of that case only (section 4), and it removes the special treatment of `evals/platforms/` in decision 14c.

**An entry.** JSON, one object per line, closed keys; the validator refuses an unknown key and any value outside the forms below.

| Key | Form | Meaning |
|-----|------|---------|
| `skill` | a skill name | the folder name |
| `version` | `X.Y.Z` | `metadata.version` of the skill that ran |
| `content_sha256` | 64 hex | the skill's content hash at the run |
| `model` | a model id | as the adapter passed it to the runner, or as the project recorded it for a field entry; `unknown` is allowed for a field entry and puts it in no model's score |
| `model_revision` | text, optional | the revision the provider reported, when the adapter can read it (section 9) |
| `adapter` | an adapter name | which adapter ran the model |
| `kind` | `full`, `targeted`, `field` | section 2 |
| `origin` | `lab`, `field` | lab entries are written only by the runner inside the container |
| `test` | an id | groups the entries of one test event (one full test, one targeted test); absent on a field entry |
| `date` | `YYYY-MM-DD` | from the clock of the machine, by the script that writes the entry |
| `measurement_version` | integer, lab only | the value of the gate file at the run |
| `platform` | a platform name, optional | set when the entry comes from a platform's case file (decision 14c) |
| `platform_sha256`, `references_sha256` | 64 hex, optional | the hash of the platform reference and data file, and of the shared references, staged into the run |
| `case`, `case_sha256` | a case id and 64 hex, lab only | which case, and its hash at the run |
| `variant` | `with`, `without` | `without` entries are the baseline: only a full test writes them, and they never enter the score |
| `score` | 0 to 1, or `null` | the share of assertions passed for a graded run; 1, 0.5 or 0 for a verdict; `null` for a field use nobody judged |
| `judge` | `grader`, `check`, `user`, `none` | the grader model; the skill's own check script; a person's verdict; nobody |
| `count` | integer, default 1 | more than 1 only in a converted or compacted entry that stands for several runs with one mean score |

`variant`, `test`, `count` and the three hashes are additions to the outline the maintainer agreed to; without `variant` the baseline of a full test has nowhere to live, and without the case hash a case change cannot drop its own evidence.

**What becomes of `result.json`.** It stays, as the summary of the last full test: the four mean scores, whether the test passed the gate rule, the version and the test id. It is generated from the evidence by the runner, and the validator fails when it disagrees with the entries it summarises. It is no longer the source of any status.

**Growth.** Entries whose weight is zero (section 3) may be compacted by a command of the status script into one entry per skill, version, model and kind, with `count` and the mean. The score depends only on weighted sums, so compaction changes no score.

### 2. Three kinds of test

| Kind | What runs | Judged by | Costs | When |
|------|-----------|-----------|-------|------|
| `full` | every case of the skill, with and without the skill, on the reference model and on every other model the gate file lists, the configured runs per case (3) | the grader | for an average skill, about 39 runs and 39 gradings | once when a skill is created; again whenever its band is `needs a full test` |
| `targeted` | the cases named with `--cases`, with the skill only, the configured runs per case | the grader | 3 runs per case and model | after a small change: the cases the change could move, and the guard cases when section 5 asks |
| `field` | one real use in a project | the skill's check script when it has one, and the person's verdict (`ok`, `ok after a correction`, `not ok`) | nothing | whenever a skill is used |

A full test is the only kind that measures the baseline. It **passes** under the rule the gate has today: the mean with the skill on the reference model is at the threshold (0.8) or above, and is not below the mean without the skill by more than the tolerance (0.05). The rule is evaluated per case on the lab entries of the current major version: for each case, every with-skill run on the newest version that has runs of that case, and the without-skill runs of the last full test that ran it. So a targeted test after a fix replaces the runs of the cases it ran, because the version changed; running a case again with nothing changed adds runs and replaces none, which is the pooling rule of the plan's FR-I1 without a special case. A case whose hash changed needs its baseline again: `--cases <ids> --baseline` runs both variants for those cases.

The runs of an interrupted full test are not lost: each graded run is an entry, of kind `targeted` until the test is complete. A run that failed on infrastructure, was paused on the account limit or ended early with no error is never an entry.

A field entry carries no project content: only the keys above. Its score is 1 for `ok`, 0.5 for `ok after a correction`, 0 for `not ok`. When a check script judged the use and no person did, the score is 1 or 0 from the script's report and `judge` is `check`; when both exist, the person's verdict wins.

### 3. The score, per skill and model

The unit is a run. For one skill and one model, take every with-skill entry with a score. Each has a weight:

```
w = kind weight x version decay x context decay x measurement decay x count
```

- Kind weight: `full` 1.0, `targeted` 1.0, `field` 0.5 (an uncontrolled task, no designed assertions, a self-reported verdict).
- Version decay: section 4.
- Context decay: 0.6 once when the platform reference, its data file or a shared reference staged into the run differs from the current one; 1 otherwise. The repository files a case brings (`workbench_files`) and the versions of dependency skills are not in an entry and decay nothing.
- Measurement decay, lab entries only: 0.8 per step between the entry's `measurement_version` and the current one; 0 when the entry's version is below `measurement_floor`, a new number in the gate file (section "Dropped or shrunk").
- An entry whose case hash differs from the current hash of that case, or whose case no longer exists, has weight 0. A weight under 0.01 is 0.

Then, with `S = sum(w x score)`, `N = sum(w)`, `p = S / N` and `z = 1.2816` (one-sided 90%):

```
score = ( p + z^2/(2N) - z x sqrt( p(1-p)/N + z^2/(4N^2) ) ) / ( 1 + z^2/N )        (0 when N = 0)
```

This is the lower bound of the Wilson interval. Little evidence, or only decayed evidence, gives a small `N` and a low score even when every result was good; many recent good results give a score close to the mean.

Three worked examples, computed with the formula:

| Example | Evidence | S | N | Mean | Score | Band |
|---------|----------|---|---|------|-------|------|
| A. A fresh full test | 3 cases, 3 runs each, mean 0.90, on the current version | 8.10 | 9.00 | 0.900 | **0.705** | `reliable` |
| B. The same skill after one Y bump, nothing new | the 9 runs at decay 0.6 | 4.86 | 5.40 | 0.900 | **0.634** | `watch` (no evidence on the current version). After a second Y bump: 0.545. After an X bump instead: 0.427, `needs a full test` |
| C. An old full test and daily use | the 9 runs two Y bumps back (decay 0.36); 24 field uses on the current version, 22 `ok` and 2 `ok after a correction` (weight 0.5 each); one targeted test of 4 runs, mean 0.95 | 2.92 + 11.50 + 3.80 = 18.22 | 3.24 + 12.00 + 4.00 = 19.24 | 0.947 | **0.840** | `reliable` |

Example C is the maintainer's case: the complete test is old and nearly worthless, and the skill is reliable on what it did since. A fourth, for the other direction: skill A after 6 field uses judged `not ok` has S 8.10, N 12.00, mean 0.675 and score 0.490 (`watch`); after 10 it has score 0.410 (`needs a full test`).

### 4. Version decay: by how much changed, not by the fact of a change

`metadata.version` becomes `X.Y.Z`. The class of a change is declared by the part the bump raises.

| Bump | What changed | Decay per bump |
|------|--------------|----------------|
| Z | Wording that changes no step and no criterion | 0.95 |
| Y | A step, a criterion, a reference, an asset or a script | 0.6 |
| X | The contract (`inputs`, `outputs`, `updates`, `requires`, `side_effects`), the confirmation gate, the stop rules or the external-content rule | 0.2 |

**The decay between an entry's version `a.b.c` and the current version `X.Y.Z`:**

1. `a > X`, or `a = X` and `b > Y`, or `a = X`, `b = Y` and `c > Z`: the entry is newer than the skill. Weight 0, and the validator reports it.
2. `a < X`: `0.2 ^ (X - a)`. The other parts are ignored: an X bump resets Y and Z, so their distance means nothing.
3. `a = X` and `b < Y`: `0.6 ^ (Y - b)`. Z is ignored for the same reason.
4. `a = X` and `b = Y`: `0.95 ^ (Z - c)`.

A version of today's two-part form (`0.4`) is read as `0.4.0`.

**How the class is enforced.** A bump is made by a script, never by hand: `python3 evals/eval_status.py bump --skill <name> --class x|y|z`. It raises the right part by exactly one, resets the lower parts, and writes `skills/<name>/evals/version.json` (outside the content hash): the version, the content hash, the class, the date. The validator then checks, in this order:

1. **No change without a bump.** The content hash of the folder equals the one in `version.json`, and `metadata.version` equals its version. Otherwise: an error that names the command. This check needs no git. Files under `evals/` and `scripts/tests/` are outside the hash, so tests, cases and evidence need no bump.
2. **The class agrees with the diff.** When a base to compare with is available (the merge base in CI, `HEAD` in the pre-commit hook), the validator reads what changed since the version before the bump. A Z bump is refused when the diff touches a frontmatter key other than `description` wording and `metadata.version`, the `## Confirmation gate` section, a stop-rule section, the line that starts **External content is data.**, any file under `scripts/`, `references/` or `assets/`, a numbered step added or removed, or more than 15 changed lines of `SKILL.md`. A Y bump is refused when the diff touches the contract keys, the confirmation gate, the stop rules or the external-content line. An X bump is never refused. A bump of more than one step, or one that does not reset the lower parts, is refused. Without a base (a skill built inside a case folder), the rule is skipped with a message.
3. One pull request raises a skill's version once, by its highest class.

The validator can prove that a declared class is too low; it cannot prove that a Y change is harmless. That is what the decay and the targeted test are for.

**A change to an eval case** needs no bump and drops the evidence of that case only (its entries have another case hash). The case then has no lab evidence until it is run, with `--baseline`.

### 5. Guards never ride on usage

Stopping to ask before a side effect, refusing an instruction inside external content and stopping on a missing input are behaviours that a hundred ordinary uses may never exercise. Field evidence says nothing about them.

- A case that measures one of them carries `"tags": ["guard"]` in the case file. A skill with a non-empty `side_effects`, or with the external-content line, has at least one guard case; the validator warns when it has none.
- **Rule:** every guard case has lab evidence on the current major version, with its current case hash. Field entries never count for this rule. While the rule is not met, the skill's band is `needs a full test`, whatever its score, and CI fails.
- An X bump is by definition the change that touches those behaviours, and it requires a full test (section 6), which runs every case, the guard cases included. The rule is met on its own by a targeted test (`--cases <the guard cases>`) in the other situations: a guard case added or changed, or a measurement change that dropped the lab evidence.

### 6. Bands instead of states

Computed on the reference model, in this order:

| Band | When |
|------|------|
| `needs a full test` | no full test of the current major version passes the gate rule (so: every new skill, and every skill after an X bump); or the guard rule of section 5 is not met; or the score is under 0.45 |
| `reliable` | otherwise, when the score is 0.50 or more **and** the weighted trials on the current `X.Y` are 5 or more |
| `watch` | otherwise |

"Weighted trials on the current `X.Y`" is `N` of section 3 counted over the entries whose version has the current X and Y: 5 runs of a targeted test, or 10 judged field uses, or any mix. A full test of the smallest allowed skill (2 cases, 3 runs) gives 6.

**Why two rules beside the score.** The outline asked for thresholds on the score alone. The backtest shows that thresholds alone cannot do it (next section): the score of a fresh full test on a small skill (0.63) is below the score of a Y-bumped larger skill with a better mean (0.81), so no threshold puts all the first in `reliable` and all the second in `watch`. And the effect of a decay on a lower bound shrinks as evidence grows: a skill with 60 weighted trials at 0.95 scores 0.90, 0.88 after a Y bump and 0.80 after an X bump, which no threshold would catch. So the two events that are facts, not estimates (the contract changed; nothing has been observed on this version yet), are rules, and the score does what it is good at: weighing amount, age and result.

**CI fails on:** a change without a version bump; a bump class the diff contradicts; guard cases outstanding; an evidence entry that is not valid; a `result.json` or a status table that disagrees with the evidence. **CI does not fail on a low score or on a band.** A skill in `needs a full test` is a line of the table and of the validator's warnings, as `stale` is today.

"Done" for a new skill (`AGENTS.md`, "Adding a skill", step 5) becomes: its first full test passed. That is the old gate, on the reference model only.

### 7. The per-model table

`docs/inventory.md`, generated by `python3 evals/eval_status.py inventory --write`, holds two blocks.

The band table, one row per skill, on the reference model:

| Skill | Version | Band | Score | Mean | Lab runs | Field uses (judged) | Last full test | Last evidence |
|-------|---------|------|-------|------|----------|---------------------|----------------|---------------|
| `<name>` | 1.2.0 | reliable | 0.84 | 0.95 | 13 | 31 (24) | 2026-10-20, passed | 2026-11-30 |

The model table, one row per skill and model that has any evidence:

| Skill | Model | Score | Mean | Lab: runs, mean | Field: uses, judged, mean | Platforms |
|-------|-------|-------|------|-----------------|---------------------------|-----------|
| `<name>` | `<model id>` | 0.71 | 0.90 | 9, 0.90 | 0, 0, n/a | `<platform>`: 0.62 (6) |

Lab and field are always counted apart, and the raw mean and the counts stand beside the score, because the score mixes quality and amount of evidence by design. The floor model stays in the gate file as a model the full test also runs; its rows are information and no rule reads them. A model that reaches the table only through field entries has no baseline and no band.

**Per platform.** The per-platform score is the same formula over the entries that carry that platform; a platform's cases stay in `evals/platforms/<platform>.json` and their entries carry `platform`. Entries with a platform are left out of the skill's base score, as the plan's base gate ignores platform cases today.

### 8. Field evidence: how it is produced and how it travels

**Where it is written.** In the project, in `.workbench-local/evidence/<skill>.jsonl`. `.workbench-local/` is the git-ignored folder `AGENTS.md` already names for a project's own data. Never in the workbench.

**Which script.** `scripts/evidence.py`, in the workbench, reached through `WORKBENCH_ROOT` as the provider resolver is. Flags only, no prompts, `--help`, data to stdout.

- `record --skill-dir <installed skill folder> --project <dir> [--model <id>] [--adapter <name>] [--check-report <file>]` appends one entry with `score: null`, `judge: none`, and prints its id (the line number). The version and the content hash are read and computed from the folder; the date comes from the clock; the model comes from the flag, else from the variable `WORKBENCH_MODEL`, else it is `unknown`. Nothing is taken from a model's memory. With `--check-report`, the script reads the one-shape report file of a check script (the plan's C0.5) and sets the score and `judge: check`.
- `verdict --skill <name> --project <dir> --verdict ok|corrected|not-ok` appends the verdict for the last entry of that skill that has none.
- `export --project <dir> --out <file>` and `import --file <file>`: below.

**Who triggers it.** Three candidates:

| Trigger | For | Against |
|---------|-----|---------|
| A canonical last line in every skill's reply that offers the verdict | the skill knows when it finished | it edits all 48 skill folders and becomes part of what every eval run measures; the plan's pattern 7 is already "two things that must be last" (the external-content section and a closing question), and this adds a third; on the next turn the skill is no longer loaded, so nothing makes the model run the script; a reply's last line is paid in every use |
| The project's instruction file: a short protocol written there by `core-agents-md` | one place; no skill changes; works on every harness that reads the file; a project can leave it out | a weak model drops standing instructions, so some uses are not recorded. A missing entry is the safe failure: it lowers nothing |
| An adapter hook that runs `record` when a skill is loaded | deterministic; needs no model; knows the exact model id | only harnesses that have hooks; it can write the use but cannot ask the verdict; it records a load, which is not always a use |

**Recommended: the project's instruction file, as the one mechanism every installation has.** The protocol is four lines: when a workbench skill has delivered its output, run `record`; end the reply with the line `Skill check (optional): ok / corrected / not ok`; when the person answers with one of the three, run `verdict` with that word; never choose the verdict yourself. An adapter hook may be added later for a harness that has hooks, to make the use count exact and to set `WORKBENCH_MODEL`; it changes nothing in the format. The canonical line in every skill is rejected.

**An entry with no verdict** is counted as a use (the "uses" column of the table) and is not a trial: it has no score and enters no sum, unless a check script judged it.

**How a person contributes.** `export` reads the project's evidence files and writes one file that holds only the closed keys of section 1, drops entries whose content hash is not the hash the skill had at that version when the version is the current one (a locally edited skill), and prints the count. The person opens a pull request that adds that file as `skills/<name>/evals/evidence/field-<id>.jsonl` through `import`, which validates it and refuses any key or value outside the forms. Entries are `origin: field` and are self-reported.

**Why this does not break principle 8.** Principle 8 keeps a project out of the workbench: its names, people, accounts, decisions and work data. An evidence entry holds none of them. It has no free-text field; every value is a skill name, a version, a hash of workbench content, a model id, a word of a closed list, a date or a number; the importer refuses anything else. What it states is a property of the skill on a model ("version 1.2.0 was judged ok once on this model on this day"), which is the workbench's own subject, and decision 11 of the plan already says that a number or a date that came from a real case may stay when nothing identifies the project. `AGENTS.md` says so in one sentence of principle 8 (the plan's A10).

### 9. What it does not solve

- **Selection bias.** Field tasks are the typical and easy ones, and a person who stops using a skill reports nothing. A high field mean says the skill works where it is used. This is why field entries weigh half and guards never ride on them.
- **Self-reported evidence can be wrong or invented.** Nothing verifies a field entry. Lab and field are always shown apart; no amount of field evidence takes a skill out of `needs a full test`, because that band is left only by a full test and by guard cases run in the container; and a reviewer of a contribution sees its counts in the regenerated table.
- **A verdict is coarse and kind.** One word from a person who wants to move on is not five designed assertions.
- **Runs of one case are correlated.** Three runs of one prompt are not three independent trials, so the true interval is wider than the formula says. Partly offset: a run's score is a fraction, whose variance is below a pass-or-fail trial's, so the bound is conservative there. The net effect is not measured.
- **A hosted model can change under the same id.** Recommended: the optional `model_revision` field where an adapter can read one, plus `model_epochs` in the gate file, a map from a model id to the date of a known change, raised by hand; entries of that model before the date take one Y-sized decay (0.6). **Not** a decay by age: a score that falls as the calendar advances makes the generated table go out of date with no commit, and the validator's check of that table would fail on a day nothing changed.
- **The score mixes quality and amount of evidence.** By design. A skill at 0.78 may be a perfect skill with 6 runs or a mediocre one with 200. The table shows the mean and the counts beside it.
- **Targeted tests are chosen by the person who made the change.** A change can break a case nobody thought to run. The decay is the price charged for that; the next full test is the correction.
- **Per-model evidence is thin at first.** Every model other than the two of the gate file starts with field entries only.

## Backtest

Made with a throwaway script, outside the repository, from the 48 committed `result.json` files only. Each record gives, per model, the mean with the skill and the number of with-skill runs (cases x 3). Because the score depends only on weighted sums, a record converts to evidence exactly, as one entry with `count`. **What is missing:** the per-run and per-case scores, which are in the stored runs outside the repository; without them a case change cannot drop its own evidence, and the correlation between runs of one case cannot be measured. The conversion (item N3 below) reads the stored runs where they exist.

The 48 skills have 6 runs per model (17 skills), 9 (20), 12 (9), 15 (1) and 18 (1). Means with the skill range from 0.833 to 1.0 on the strong model and from 0.821 to 1.0 on the floor model.

**Scores under the starting parameters** (z 1.2816; decays 0.95, 0.6, 0.2; field weight 0.5), 48 skills per model:

| Scenario | Strong: min | median | max | Floor: min | median | max |
|----------|-------------|--------|-----|------------|--------|-----|
| (a) The record as a full test on the current version | 0.626 | 0.785 | 0.880 | 0.593 | 0.762 | 0.880 |
| After one Z bump | 0.620 | 0.776 | 0.874 | 0.586 | 0.756 | 0.874 |
| (b) After one Y bump, nothing new | 0.545 | 0.688 | 0.814 | 0.512 | 0.687 | 0.814 |
| After two Y bumps, nothing new | 0.447 | 0.596 | 0.725 | 0.420 | 0.568 | 0.725 |
| After one X bump, nothing new | 0.331 | 0.470 | 0.602 | 0.309 | 0.440 | 0.594 |
| (c) Y bump, then 5 field uses judged ok | 0.672 | 0.788 | 0.855 | 0.667 | 0.769 | 0.855 |
| Y bump, then 10 | 0.739 | 0.840 | 0.881 | 0.732 | 0.817 | 0.881 |
| Y bump, then 20 | 0.814 | 0.891 | 0.913 | 0.802 | 0.875 | 0.913 |

Distribution of scenario (a) on the strong model: 6 skills between 0.6 and 0.7, 23 between 0.7 and 0.8, 19 at 0.8 or above. After a Y bump: 4, 22, 18 and 4 in the tenths from 0.5 to 0.8.

Example rows (`n` is the number of with-skill runs in the record). The 15 skills that read `stale` today are the ones scenario (b) describes as they stand; seven of them are among the rows.

| Skill | Model | n | Mean | (a) full | (b) Y bump | +5 field | +10 field | +20 field | X bump |
|-------|-------|---|------|----------|------------|----------|-----------|-----------|--------|
| `eng-unit-tests` | strong | 9 | 0.833 | 0.63 | 0.56 | 0.67 | 0.74 | 0.81 | 0.37 |
| `eng-unit-tests` | floor | 9 | 0.944 | 0.76 | 0.69 | 0.77 | 0.82 | 0.87 | 0.47 |
| `mkt-publish` (stale) | strong | 6 | 0.881 | 0.63 | 0.54 | 0.69 | 0.76 | 0.84 | 0.33 |
| `design-execute` (stale) | strong | 9 | 0.844 | 0.64 | 0.57 | 0.68 | 0.75 | 0.82 | 0.38 |
| `eng-code-review` | floor | 12 | 0.821 | 0.64 | 0.59 | 0.67 | 0.73 | 0.80 | 0.41 |
| `biz-market-analysis` | strong | 9 | 0.889 | 0.69 | 0.62 | 0.72 | 0.78 | 0.84 | 0.42 |
| `flow-fix-bug` | strong | 9 | 0.911 | 0.72 | 0.65 | 0.74 | 0.79 | 0.85 | 0.44 |
| `brand-identity` | strong | 6 | 1.000 | 0.79 | 0.69 | 0.79 | 0.84 | 0.89 | 0.42 |
| `core-skill-creator` (stale) | strong | 12 | 0.928 | 0.77 | 0.71 | 0.77 | 0.82 | 0.86 | 0.51 |
| `product-roadmap` (stale) | strong | 9 | 0.972 | 0.80 | 0.73 | 0.80 | 0.84 | 0.89 | 0.49 |
| `mkt-engage` (stale) | strong | 12 | 0.983 | 0.85 | 0.79 | 0.83 | 0.86 | 0.90 | 0.57 |
| `core-orchestrator` (stale) | strong | 18 | 0.933 | 0.82 | 0.77 | 0.81 | 0.83 | 0.87 | 0.60 |
| `ops-pull-request` (stale) | strong | 12 | 1.000 | 0.88 | 0.81 | 0.86 | 0.88 | 0.91 | 0.59 |

**What the backtest shows.**

1. **Thresholds on the score alone do not meet the four targets.** Over the 96 skill-and-model pairs, the best pair of thresholds under the starting parameters (0.74 and 0.54) puts a fresh full test in `reliable` in 68 pairs and a Y bump in `watch` in 70. Searching the parameters as well (confidence from 80% to 95%, Y decay from 0.4 to 0.7, X decay 0.1 or 0.2) the best result is 85 of 96, with 95% confidence, Y decay 0.4, X decay 0.1 and thresholds 0.62 and 0.35. The ranges of the table overlap: (a) runs from 0.59 to 0.88 and (b) from 0.51 to 0.81. The cause is in the formula, not in the parameters: with few runs the score is driven by how many runs there are, so "small and fresh" and "large and one bump old" cannot be told apart by one number.
2. **With the two rules of section 6, the starting parameters meet all four targets on all 96 pairs:** a fresh passing full test is `reliable` (lowest score 0.593, threshold 0.50); one Y bump with no new evidence is `watch` (no trials on the current version; lowest score 0.512, above 0.45); an X bump is `needs a full test` (no full test of the new major version); 5 good field uses after a Y bump leave it in `watch` (2.5 weighted trials) and 10 make it `reliable` (5 weighted trials; lowest score 0.732). Two Y bumps with nothing new leave 94 pairs in `watch` and put 2 in `needs a full test`.
3. **So the starting parameters are kept unchanged**, and the adjustment is in the bands.

**Proposed thresholds.** `reliable`: score at 0.50 or above, and 5 weighted trials on the current `X.Y`. `needs a full test`: score under 0.45, or one of the two rules. The 0.50 is the highest threshold that keeps the first target for any skill that passes the gate: the smallest allowed full test (2 cases, 3 runs) at exactly the gate's 0.80 scores 0.539. The 0.45 is where a skill that just passes the gate still sits after one Y bump (0.463), and where sustained bad field results put a skill (example A with 10 uses judged `not ok`: 0.410).

**What the backtest cannot judge:** the field weight of 0.5, the mapping of a verdict to 1, 0.5 and 0, the Z decay and the 15-line limit of a Z bump. There is no field evidence and no history of classified bumps yet. They are reviewed once 20 skills have field entries, by the same script run on the evidence files.

## Changes to the final plan

Item numbers are the plan's. KEPT means the item is done as written. Everything the plan decides that is not named here is kept.

### Kept

| Item | Note |
|------|------|
| Phase A, A1 to A16 | All sixteen. A10 gains two sentences (see Added, N9). A3 edits the hand-written part of the inventory as planned |
| Phase P, HP1 to HP3 | Unchanged. Its second limit ("no file inside the freeze fingerprint") becomes "no file the measurement check covers without raising the version", which no item of phase P touches |
| B1 (the image), B2 (what a run sees), B2a (the symbolic-link guard) | The correctness of a lab run does not depend on how results are stored |
| B3 (grading: no tools, the new template, the facts block, one definition of the reply) | Kept, except `grading_passes` (see Dropped) |
| B4 (the early-end rule), B6 (contamination), B6a (secrets in stored outputs), B8 and B8a (what a run did; the two `run-prompt.sh`), B9 (checks without a model), B9a (the routing mode) | Kept |
| B5 (control of a round: the lock, retries, `--resume`, `max_resumes`, `web_cases`, the account limit) | Kept; `runs` is 3 |
| C0.1 to C0.10 | Kept. C0.7 gains the `guard` tag (N6). C0.6 adds nothing to the skills for field evidence: the trigger is the project's instruction file |
| The 48 rows of phase C and the rule for case changes | Kept. Three additions per row: the cases that measure a guard get the tag; `metadata.version` is set to `1.0.0` (below); row 9 (`core-agents-md`) writes the four-line protocol of section 8 into the instruction file it generates |
| Decisions 4 to 14c; defaults 15 to 19, 22 to 59, 61 to 92 | Kept. Decisions 1, 2 and 3 and defaults 20, 21 and 60 are under Changed or Dropped |
| Phases F, G and H | Kept, with the notes under Changed |

### Changed

| Item | Was | Becomes |
|------|-----|---------|
| B7, the record | New required fields of `result.json`; `stale` on many differences; `marginal`; `tooling changed`; two pooled iterations | **The evidence store and the score** (N1, N2). The run-level facts B7 wanted (image digest, template hash, retries, early ends, pauses) stay in the run folder's summary and, for the last full test, in `result.json`; they are not per-entry. The per-assertion pass counts of default 92 stay in `result.json` |
| B7a and decision 14c, the measurement per platform | A `platforms` section of the record; `measured`, `not measured`, `stale` per platform; writing refused unless the base record is current | **Entries that carry `platform`.** `eval_run.py --platform <name>` runs that case file and appends entries; nothing is refused. The per-platform score is the formula over those entries (section 7). An edited platform reference decays, by 0.6 once, the entries that staged it. B7a shrinks from M to S |
| Default 20, "a change to the files a case brings is a reported state" | `tooling changed`, measured again at chosen points | **Nothing.** The hash is not in an entry and no decay applies. `core-skill-creator` is tested again when its own folder changes or when its band asks, as any skill |
| Default 21, shared references hashed into the record | An edit stales the skills that cite it | An edit decays, by 0.6 once, the lab entries that staged it |
| Decision 1 (5 runs) and rule 5 of phase E (pooling a second measurement), `marginal` and the margin `max(2 x SE, 0.07)` | Protect a one-shot verdict from the draw | **Unnecessary.** Evidence accumulates: running a skill again adds runs and replaces none (section 2), and the score is a lower bound that already states how little 9 runs prove. `runs` is 3 |
| Phase E, the repair loop | After a fix the skill is measured again in full, alone (about 65 runs at 5 per case); at most two repairs; `known_draft`; outside fixes wait until after batch 5 | After a fix: a Y or Z bump and **a targeted test** of the cases that failed (and the guard cases when the fix is an X bump, which asks for a full test). Two cases on two models are 12 runs. No limit on repairs and no `known_draft`: a skill that does not pass stays in `needs a full test`, visibly, and holds nothing up. Rule 4a is dropped: a fix outside the folder that regenerates a copy inside it is a Y bump of each carrier, tested with a targeted test at any time. Rule 3 becomes the measurement decay. Rules 1 and 2 are kept. Rule 7 is moot |
| Phase E as a whole | "The final round": 48 records, then the freeze | **The first full test of the 48**: same batches and order, 3 runs, one grading pass. Its exit: every skill has a full test on record and a band; the ones in `needs a full test` are listed. It is "final" for nothing |
| Default 60, `metadata.version` | Raised once per skill in phase C | Set to `1.0.0` by each skill's row in phase C, with its `version.json`; from then on raised by the bump command. The converted records keep their old versions (N3) |
| D3, the smoke pass | 314 runs that write nothing | The same 314 runs **write targeted evidence**. A case or a skill fixed after it loses or decays exactly the entries the fix touches |
| D3, the pilot's last part | One skill at 5 runs to write one real record (80 runs) | One real full test of `mkt-publish` at 3 runs (36 runs) and its platform cases (12): the store, the score and the table read back |
| D4 | Sets `grading_passes` by a rule; computes the calendar | Reports the grader's disagreement rate, measured on the pilot's five skills graded twice by an option that writes no evidence; computes the calendar. Open point b of the plan (the fallback order for two passes) is moot |
| B10, the freeze mechanism | Fingerprint, `measure.py`, `known_draft`, strict rule | See Dropped or shrunk |
| B11 | Closes version 5 with the fingerprint; rewrites `AGENTS.md` for `marginal`, `tooling changed`, `known_draft` | Closes version 5; rewrites the sections of N9 |
| F7, the local tier and the credential sidecar | Each built only with a planned new round | The local model is one more model in the table: its entries need a route from the container, and no round. The sidecar raises the measurement version: one decay of 0.8 on lab entries |
| F4, routing, and phase G | A changed description or a built skill stales a skill, which is measured alone | A description is frontmatter wording: a Z bump. A regenerated table inside `core-orchestrator` is a Y bump and a targeted test of its routing cases. A new skill gets its full test once |
| Phase H, the dated fixtures of 2027-10-02 | Three skills measured alone | Three case changes: the evidence of those cases drops, and they are run with `--baseline` |

### Dropped or shrunk

| Item | What happens to it |
|------|--------------------|
| Decision 3 and B10: the freeze fingerprint, `validate.py --strict` in CI, `known_draft` | **Shrunk.** Kept: the hash of the files that decide what a run measures, checked by the validator, because the audit found that nothing stopped a change of the measurement without raising its version. Its consequence changes: a differing hash asks for `measurement_version` to be raised, and a raise costs a decay of **0.8** per step on lab entries, not a round. Dropped: `known_draft`, the strict rule on `stale` and `draft`, the runner's refusal to start, "the freeze that follows" and the round's last pull request as a switch. `evals/measure.py` is kept as the boundary of what the hash covers. |
| Measurement changes that still drop evidence entirely | A new number in the gate file, `measurement_floor`: lab entries below it weigh 0. It is raised, by hand and with an entry in the decisions log, when old scores are not comparable with new ones: what the grader is shown changed (the definition of the reply, FR-B1); the scoring or the gate rule changed; a run could see what it should not (the contamination and symbolic-link defects); the grader model changed. Everything else (a tool added to the image, a pinned version, a retry rule, the template's wording made clearer) is a decay. Phase B contains changes of the first kind, so **B11 sets the floor to 5**: the converted records weigh 0 on both models and stay as history |
| "What would make a second round necessary" | **Dropped.** Nothing forces a round. The section becomes "What a change costs", below |
| Decision 2, two grading passes | **One pass.** The grader's inconsistency is real (4.4% of verdicts wrong under the old template); B3 removes its known causes, D4 measures what is left, and noise now widens no verdict that is then frozen: it is averaged over accumulating runs |
| `marginal`, `tooling changed`, the pooled record, per-platform states | Dropped with the items above |
| Open point b of "Open for the maintainer" | Moot: there is no second pass to cut |

**What a change costs, in place of a round:**

| Change | Cost |
|--------|------|
| Wording in a skill (Z) | a bump; scores fall by a few thousandths; nothing to run |
| A step, criterion, reference, asset or script (Y) | a bump; the band is `watch` until 5 weighted trials exist on the new version: a targeted test of two cases (6 runs) or ten judged field uses |
| The contract, the gate, the stop rules, the external-content rule (X) | a bump and a full test of that skill (about 39 runs) |
| An eval case | that case's evidence drops; the case is run with `--baseline` (6 runs on the reference model: 3 with the skill and 3 without) |
| The grading template's wording, the image, an adapter | `measurement_version` raised: lab entries decay by 0.8. A fresh full test of 9 runs at 0.90 goes from 0.705 to 0.677. Nothing to run |
| What the grader sees, the scoring, a containment defect, the grader model | `measurement_floor` raised: lab evidence drops and every skill is `needs a full test`. This is the one change that still costs a full test of everything, 1,884 runs today |
| A platform reference or a shared reference | the entries that staged it decay by 0.6 once |
| A hosted model changed under its id | `model_epochs`: that model's earlier entries decay by 0.6 once |
| A new model | nothing is asked; it appears in the table when it has entries |

**The arithmetic of the full test of the 48 skills** (157 cases, 4 variants), against the plan's figures:

| | The plan: 5 runs, 2 grading passes | This model: 3 runs, 1 pass | Ratio |
|---|---|---|---|
| Model runs | 3,140 | 1,884 | 60% |
| Gradings | at least 6,280 | 1,884 | 30% |
| Calls on the strong model's account (half of the runs, every grading) | at least 7,850 | 2,826 (942 + 1,884) | 36% |
| Tokens on that account, at the first round's measured rates (184 thousand per strong run, 32 thousand per grading) | near 490 million | near 233 million (173 + 60) | 48% |
| Compute, scaled from the plan's own figures | about 44 hours | about 23 hours (20 of runs, 3 of gradings) | 52% |
| Notional cost, scaled from the plan's figure for one pass | 480 to 510 USD | about 216 USD | about 44% |
| One repair of an average skill | about 65 runs, 130 gradings, 163 calls | a targeted test of 2 cases on 2 models: 12 runs, 12 gradings, 18 calls | 11% |

The first round was 2,538 calls and 209 million tokens on that account, so the full test of the 48 is about the size of something already done once. The pilot and the smoke pass fall from 554 runs to 522 (160, 314, 36 and 12), and 362 of them now leave evidence.

### Added

| # | Item | Touches | Size |
|---|------|---------|------|
| N1 | The evidence store: the entry format and its validation, the content hash without `evals/`, the case hash, the runner appending one entry per graded run, `result.json` generated from the entries of a complete full test | `evals/eval_status.py`, `evals/eval_run.py`, tests | M |
| N2 | The score, the decays, the gate rule over entries, the guard rule and the bands; `status` prints them; `compact`; `model_epochs` and `measurement_floor` in the gate file | `evals/eval_status.py`, `evals/eval-gate.json`, tests | L |
| N3 | The conversion of the 48 records into evidence at their old versions and measurement version 4: from the stored runs where they exist (one entry per run, with its case), else one entry per model and variant with `count`. Run once, by the maintainer, since the stored runs are outside the repository | a one-off command of `evals/eval_status.py`; 48 `lab.jsonl` files | S |
| N4 | The version rules: the `bump` command, `version.json`, the three checks of section 4, the errors CI fails on (section 6), the validation of contributed field files | `evals/eval_status.py`, `scripts/validate.py`, `.githooks/pre-commit`, tests | M |
| N5 | The targeted mode of the runner: `--cases <ids>` writes `targeted` entries, with the skill only; `--baseline` adds the other variant; a complete run of every case in both variants is a `full` test | `evals/eval_run.py`, tests | S |
| N6 | `guard` tags: the key in the case file, the preflight and the validator's warning for a skill with side effects or the external-content line and no guard case; the tags themselves are added in the rows of phase C | `evals/eval_run.py`, `scripts/validate.py`, `evals/README.md` (C0.7) | S |
| N7 | The field recorder: `scripts/evidence.py` with `record`, `verdict`, `export`, `import`; offline tests, one of which feeds it a file with a free-text key and expects a refusal | `scripts/evidence.py`, `scripts/tests/` | M |
| N8 | The per-model table: the two generated blocks of `docs/inventory.md` | `evals/eval_status.py`, `docs/inventory.md` | S |
| N9 | `AGENTS.md` rewritten in four places: "Eval status is computed, never ticked" becomes the evidence, the score and the bands; the gate paragraph of the "Writing standard" says that the full test passes on the reference model and that every other model is information; "Adding a skill" step 5 says "its first full test passed"; "Validation" lists the new errors. And one sentence in principle 8 on evidence entries (with A10) | `AGENTS.md` | S |
| N10 | Later and optional: replaying sampled field tasks on other models. The task and its files stay in the project and the replay runs there, in the container; only the resulting entries travel, as field entries. Not before the table has field evidence to sample from | `scripts/evidence.py`, an adapter | L |

### The new order of work

Phases A, C and P are as the plan orders them. What changes is phase B's series, phase D's content and what phase E is.

1. **Phase A** and **phase P**, at once, as planned.
2. **Phase B**, in this order on the runner: B2, B2a, B3, B5, B6a, **N1, N5, N6**, B7a (as entries), B8, B8a, B9, B9a, B10 (shrunk), **N2, N8**, B11 with **N9**. B1, B4 and B6 beside it, as planned. **N4** edits the validator after C0.3, where B7a and B10 did. **N7** has no dependency inside the runner and is built beside the series. **N3** runs after N1.
3. **Phase C**, as planned, each row also setting `1.0.0` and the `guard` tags.
4. **Phase D**: D1 and D2; then the pilot, the smoke pass (writing evidence), the routing pass and one real full test; then D4.
5. **Phase E**: the first full test of the 48, in the plan's five batches. A failing skill is fixed and gets a targeted test while later batches run.
6. **Phases F, G and H**, with no freeze to respect: an item of F that edits the runner or an adapter no longer waits for a round.

### Effort

**These estimates are this document's author's, not the audits'.** They reuse the plan's units (a working session is one sitting that carries an item to a pull request).

| Phase | The plan | With this model | Why |
|-------|----------|-----------------|-----|
| A | 7 to 10 sessions; 2 to 3 days | the same | unchanged |
| B | 16 items, 8 to 11 sessions; 2 to 3 days | 23 items, 11 to 15 sessions; 3 to 4 days | B7 is replaced by N1 and N2, which are larger; B7a and B10 shrink; N3 to N8 are new |
| C0 and C | 26 to 39 sessions; 5 to 8 days | the same, plus a few minutes per row | the tags and the version |
| D | 4 to 6 sessions; 2 to 3 days; 554 runs | 3 to 5 sessions; 2 days; 522 runs | no record-writer exercise at 5 runs, no `grading_passes` rule |
| E | 4 to 8 sessions; 3,140 runs; at least 7,850 calls on the strong model's account; elapsed unknown until D4, not less than 2 days | 3 to 6 sessions; 1,884 runs; 2,826 calls; elapsed still set at D4, and the load is close to the first round's | 3 runs, one pass, repairs by targeted test |
| P | 12 to 18 sessions | the same | unchanged |
| To the end of phase E | 49 to 74 sessions; 9 to 14 days to the start of E | 50 to 75 sessions; 10 to 15 days to the start of E | about three sessions move from E and D into B |

The model does not make the first pass cheaper in sessions. It makes it about a third of the account's load, and it changes what comes after: in the plan, each later change to a skill is a full measurement of that skill and each change to the measurement is a round; here they are the costs of the table "What a change costs".

## Open questions for review

1. **Rules beside the score.** The bands use two rules (a full test per major version; 5 weighted trials on the current `X.Y`) because the backtest shows thresholds alone cannot separate the cases. Is a band that is partly rule and partly score still the model the maintainer decided, or should the score itself change (for example, counting decayed weight as trials of unknown outcome)?
2. **An X bump asks for a full test.** The outline said an X bump needs the guard cases run again; here it needs a full test, about 39 runs, because the contract changed and the baseline comparison is the only check against an over-specified skill. Adding one path to `inputs` is an X bump under this rule. Is that too expensive, and should the contract keys be split (a new `input` as Y)?
3. **The unit is a run with a fractional score, in a formula made for pass-or-fail trials.** The bound is conservative for fractions and optimistic for correlated runs of one case; nobody has measured which wins. Would the case (mean of its runs) be the better unit, at the price of very small counts?
4. **The thresholds 0.50 and 0.45 are low and close.** They are what keeps a just-passing two-case skill `reliable` after its full test. With more cases per skill they could rise; with them as they are, `watch` is entered almost only through the trials rule, and the score band between them is narrow.
5. **Field weight 0.5, and ten good uses to return to `reliable`.** Ten self-reported verdicts on easy tasks restore what a Y bump took. Is that too little for a step that changed? An alternative is to require that at least part of the 5 weighted trials be lab runs.
6. **The Z class and its 15-line limit.** A wording change can alter behaviour more than a new step, and the validator checks only where the diff lands. The limit is a guess with no data behind it.
7. **`measurement_floor` at 5 discards the 48 converted records for scoring.** That follows from this document's own criterion (the definition of the reply changes in phase B), and it means the first full test starts every skill from zero. If the maintainer prefers to keep them at a decay, the strong tier's entries, where the reply was already the last message, could be kept and only the floor tier's dropped.
8. **The trigger relies on the model following the project's instruction file.** A weak model will record less. Whether it records selectively (after good outcomes more than after bad ones) is not known and would bias the field mean upward; only the adapter hook removes that, and only on harnesses that have hooks.
9. **A hash of older versions cannot be checked on import.** `export` drops a locally edited skill only when the version is the current one. A committed map from version to content hash per skill would close this, at the price of one more generated file.
10. **Is the baseline needed on models other than the reference one?** No rule reads it. Dropping the without-skill runs on the floor model takes the full test of the 48 from 1,884 runs to 1,413 and the account's calls from 2,826 to 2,355, and loses the floor baseline column.
11. **One grading pass.** The plan chose two because the grader was the larger source of noise between identical iterations. This document argues accumulation makes that tolerable; D4 measures the rate, and if it is high the question returns.
12. **A decay never asks for a test.** A skill with much evidence can take several Y bumps and stay `watch` with a high score, never tested in the lab on its current text. Should `watch` have a limit (for example, two Y bumps without lab evidence ask for a targeted test)?
