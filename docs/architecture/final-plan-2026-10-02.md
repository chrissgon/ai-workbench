# Final plan, 2026-10-02: everything that remains, ordered around one last measurement round

**This is the plan in force.** It replaces `docs/architecture/plan-2026-10.md`, whose phases 0 to 4 are done and whose phases 5 and 6 are absorbed here. It is built from the audit of 2026-10-02 (`docs/architecture/audit-2026-10-02/`, nine reports) and from the triage of every item of `docs/backlog.md`. Its section "Decisions for the maintainer" awaits the maintainer; nothing in it is decided until they say so, except what the section marks as already approved.

## Purpose and the one rule that orders everything

- The 48 skills were measured once in the eval container. They are measured **one more time, and that round is meant to be the last** for the skills as they are.
- **The rule:** anything that changes a skill's folder, or that changes what a run measures (the eval runner, the adapters, the container image, the grading template, the gate), is finished **before** that round. After the round those things are frozen; changing one of them means measuring again.
- So the order is: repairs that touch neither (phase A), the measurement itself, changed once (phase B), every skill edited once (phase C), a dry run (phase D), the round (phase E), and only then the work that is independent of skills (phases F to H).
- Everything that is known to need fixing is fixed before the round, even though it costs the measurement of all 48 skills: the audit exists so that no known defect is left to cause a second round.
- This document covers everything that remains to be done in the repository. The "Backlog map" near the end lists every backlog item and where this plan handles it, so that nothing is lost.

### Terms used below

| Term | Meaning |
|------|---------|
| Skill folder | `skills/<name>/`: `SKILL.md`, `references/`, `assets/`, `scripts/`, `evals/`. Its content hash leaves out `scripts/tests/` and the record itself. |
| Case, assertion | A case is one prompt with its fixture files in `skills/<name>/evals/evals.json`; an assertion is one statement about the output that a grader judges true or false. |
| Variant | One of four ways a case is run: with the skill or without it, on the strong model or on the floor model. |
| Strong model, floor model, grader | The two models under test and the model that judges assertions, all named in `evals/eval-gate.json`. |
| Run, iteration | A run is one execution of one case in one variant. An iteration is every run of a skill (every case, four variants, the configured number of runs each). |
| Record | `skills/<name>/evals/result.json`: the result of a complete iteration, with the hash of the skill folder. |
| `evaluated`, `stale`, `draft` | The status computed from the record: the gate passed on the current content; it passed but the folder or the measurement changed since; there is no passing record. |
| Gate | The rule a skill must pass: both models at 0.8 or more with the skill, and the strong model with the skill not more than 0.05 below the strong model without it. |
| Measurement version | A number in `evals/eval-gate.json`, raised by hand when a change alters what a run measures. It is 4 today; phase B ends by raising it to 5. |
| Round | The measurement of all 48 skills under one measurement version. The first round closed on 2026-10-02 (backlog T11). |
| Freeze | The state after the final round: the files that define the measurement and the skill folders do not change without a new measurement. |
| Report references | `(harness §3)` is section 3 of `audit-2026-10-02/harness.md`; `(cross-skill §1c)` a section of `cross-skill.md`; `(group-3, design-brief, must-fix 2)` an item of a group report; `(backlog N1)` an item of `backlog.md` in the audit folder. Decision letters and numbers of the reports are written `harness A`, `cross-skill 7`, `backlog Q3`. |
| Size | S: under an hour. M: a few hours. L: a day or more. The sizes are the audits' own. |

## Where things stand

Read on `main` at `3cbc7f2` on 2026-10-02.

| What | Count | Note |
|------|-------|------|
| Skills | 48 | 47 capabilities and 1 flow; 141 cases, 663 assertions |
| `evaluated` | 33 | |
| `stale` | 15 | all from text changes merged after the first round (#41 to #44), none from a failing run |
| `draft` | 0 | |
| Assertions that pass in every run of every variant | about 196 to 200 of 663 | 20 say only that the reply is in the prompt's language (backlog T19) |
| Backlog items triaged | 82 | 19 security, 20 tooling, 11 runtime, 1 convention, 1 provider, 15 brand and social, 3 next skills, 8 review decisions, 4 open pieces of the previous plan |
| Done | 38 | 36 done on `main`, 2 done by #44 with a leftover each |
| Partly done | 18 | |
| Not done | 26 | |
| Waiting only on something outside the repository | 10 | a real run, a real account, a real week, the next CI failure (phase H) |
| Ticks that do not match the code | 9 | 5 items done and unticked, 2 ticked whose "Done when" does not hold today, 2 whose text describes an older state (backlog, "Findings") |
| Work no backlog item covers | 19 | N1 to N19 |
| Must-fix findings in the 48 skills | 246 | sum of the group reports' summary tables; should-fix findings: 394 |
| CI on `main` | one job failing | `python39`, since #44; the repair is open as pull request #45 |
| `python3 scripts/validate.py` | 0 errors, 3 warnings | two inputs no skill produces; the 15 stale skills |

Already merged on 2026-10-02 and not planned again: flows marked planned and "run X" rewritten (#41); tests inside the skills and outside the hash (#42); the orchestrator's exception, planned skills marked, product names out of the core's skill text (#43); providers resolved by class and ledgers moved (#44).

### The main patterns the audit found

Across the 48 skills (the group reports' "Patterns" sections):

1. **Reports state that a check was done instead of quoting it.** The grader sees only the reply and the files a run leaves. "The lint is run and reports ok" fails good runs or passes on a sentence. It is the main cause of failures with the skill in the design, product and engineering groups.
2. **Assertions about what did not change** ("X is unchanged", "no file is modified", "the file is deleted") fail good runs, because an unchanged or deleted file is invisible to the grader.
3. **Script paths that exist only in the workbench.** 31 of the 37 skills with scripts write `scripts/<name>` or `skills/<name>/scripts/<name>`; a model first looks in the project, and artifacts end up carrying the path of an AI tool's folder.
4. **Stop gates without the words that make them hold**: nothing says that "go" is not an answer or that nothing is written before the answer; several gates sit inside a long step or only in the Inputs table; several have no template for the reply that asks.
5. **Cases that measure nothing**: about 30% of the assertions pass in every variant; several cases score the same with and without the skill; conditional assertions ("If X exists, ...") pass when nothing is written.
6. **Undeclared reads and writes**: 25 skills write the state file without declaring it; seven paths have several producers; nine skills use a requirement class or produce a side effect they do not declare.
7. **Two things that must be last**: the reply "ends with" the external-content section and also "ends with" a question; it costs `flow-fix-bug` seven assertions.
8. **Fixtures**: runtimes the image does not have (Node 20 and 22 in eleven copies of one project), a lint that cannot run, real hosts and one real person's name, dates relative to the day of the run, placeholders where a small real project is needed, and several fixtures and "Gotchas" that still carry one real case's numbers, dates and decisions (principle 8).
9. **Nine scripts end in a traceback** when a flag comes last without its value; most hand-written parsers ignore an unknown flag silently.

In the harness (harness report, summary table):

1. **The grader is inconsistent, not biased**: 4.4% of re-judged verdicts were wrong and 11.9% doubtful, most from what the template does not say and from what the grader cannot see. The same sentence passed in one iteration and failed in the next; one skill of nine crossed the gate on a rerun with nothing changed.
2. **Three runs per case are few**: one iteration's mean moves by about 0.045 between identical reruns.
3. **The early-end detector** was wrong in 7 of its 12 detections, all on the strong tier.
4. **A run can read more than it should** (the whole `adapters/` folder, a second copy of the skill), and the floor provider's key is printed in 14 stored transcripts outside the repository.
5. **The image is not reproducible** (tags, a moving package index, one machine's local build), its scratch folder for the floor runner is not writable (67 runs), and the host's time zone leaks into it.
6. **The contamination check cannot fire** in the container; a timeout is silently dropped; nothing stops a change to the template or the image without raising the version.

## Decisions for the maintainer

One numbered list, in two parts. Part (a) holds the decisions whose options lead to materially different work, cost or risk; each needs an answer before the phase it shapes. Part (b) holds every other decision found in the nine reports, with the choice this plan applies unless the maintainer objects. Every decision of the reports is in one of the two parts, with the report and section it comes from.

Already approved by the maintainer, and therefore not asked again: decisions D7, D8, D9, D10 and D12 of the review of 2026-10-01 as recommended; fixing the scripts that end in a traceback on a missing flag value; the gate (both models at 0.8, the strong model not more than 0.05 below its baseline); evals only in the container; a provider refusal of a without-skill run scores zero; a case may bring repository files (`workbench_files`); fixing everything that has to be fixed before the round, the cases included.

### (a) Decisions that change the plan

**1. How many runs per case in the final round?** (harness §2, harness A)

| Option | Consequence |
|--------|-------------|
| 3, as today | 12 runs per case; about 21 hours of compute for today's 141 cases. A skill at 0.84 fails about one round in five by chance. |
| 5 for every skill | 20 runs per case; about 35 hours for 141 cases, about 130 USD more in notional strong-model and grading cost. One standard, no rule to explain. |
| 3, plus 2 more for a skill within two standard errors of a limit | About 24 hours; cheaper, but a record then depends on a rule applied after seeing scores. |

Recommendation: **5 for every skill**, written in `evals/eval-gate.json` so that a record with fewer cannot be written. Needed before phase B.

**2. Is every run graded once or twice?** (harness §1 "A grader other than the model under test", harness B; backlog Q4c and N4)

| Option | Consequence |
|--------|-------------|
| Once, by the configured grader, with the new template, the facts block and no tools | No extra cost. Removes the causes of the 11 wrong verdicts found; the remaining random inconsistency stays unmeasured. |
| Twice, with a third grading when the two differ on an assertion | At least twice the grading calls (about 5 more hours of compute and 120 to 150 USD notional at 5 runs). Disagreement becomes a number in the record. |
| A different model as grader | A third provider, adapter path and key the day before a final round; the sample shows inconsistency, not self-preference. |

Recommendation: **twice in the final round**, because the grader is the larger source of noise between identical iterations and this round is meant to stand. It is built as a number in the gate file (`grading_passes`); the pilot of phase D reports the disagreement rate, and the maintainer may drop to one pass if it is under 1% of assertions. No change of grader model. Needed before phase B.

**3. How is the freeze enforced after the round?** (harness §7 "The freeze", harness H; backlog action plan step 4)

| Option | Consequence |
|--------|-------------|
| By discipline (a comment, a number raised by hand) | Nothing to build. The first round changed the harness four times in a day this way. |
| A fingerprint of the files that define the measurement, in the gate file, checked by `validate.py` | A change to the template, the image definition, an eval adapter or the measurement constants fails the hook and CI until the version is raised or the change is justified on record. |
| The fingerprint, and `validate.py --strict` in CI once the round is done | Also, a pull request that changes a skill folder is red until that skill's new record is in it. |

Recommendation: **the third**. The fingerprint is built in phase B; `--strict` is switched on in CI at the end of phase E. Needed before phase B.

**4. On which platform are records made, and how is the image pinned?** (harness §8, harness I; backlog PL-digest)

| Option | Consequence |
|--------|-------------|
| As today: built locally from tags and a moving package index | No work. A second person cannot rebuild the image the records were measured in; a tag can move under the round. |
| Pinned by digest, a dated package snapshot and a lock file for the two runners; built once; stored; its digest in every record; records made on `linux/arm64` | Native on the machine that measured the first round. CI keeps building `linux/amd64` only to test the definition and never writes a record. A person on another architecture runs under emulation or cannot write a record. |
| The same, records made on `linux/amd64` | Matches CI; the measuring machine runs every container under emulation, which is several times slower for a round of 35 to 50 hours of compute. |

Recommendation: **the second**. Where the built image is stored (the code host's container registry, or an archive with its checksum kept by the maintainer) is part of the answer: a registry publishes the image, so it is the maintainer's choice. Needed before phase B.

**5. Is the code host's command-line tool (`gh`) in the image?** (harness §8 "Tools a model reached for", harness F)

| Option | Consequence |
|--------|-------------|
| Absent, as measured | A model reports "not installed" (41 occurrences in five delivery skills); two skill scripts never take their `gh` branch. |
| Installed, signed out, pinned, with no network to the host | A model reports "not authenticated", which is what a developer's machine without a login looks like. It changes the runs of five delivery skills, which the round measures anyway. |

Recommendation: **installed and signed out**. Needed before phase B.

**6. Do runs get a fixed clock, for the cases whose dates depend on the day of the run?** (group-6, "Patterns" 1; group-6, mkt-publish, "For the maintainer to decide" 2; group-6, mkt-content-plan, must-fix 1; group-1, brand-profile, should-fix 2)

| Option | Consequence |
|--------|-------------|
| Real clock; fixture dates at least a year ahead; prompts name dates or posts, never "next week" | Changes only skill folders (phase C). The fixtures expire again in a year; a backlog item records the date. |
| A fixed date for every run, set in the image or by the runner | Fixtures never expire. It changes what every run measures, and a container whose clock is wrong can fail the runners' own calls to their providers (certificates, token expiry). It would need its own proof run. |
| Real clock, and the cases state today's date where a skill computes from it (the scripts already take `--today` or can) | Changes skill folders only. The date is an input of the case, as in `mkt-vote-round`, which is safe today. |

Recommendation: **the first and the third together**, no fixed clock in this round. Needed before phase C (groups 1 and 6).

**7. Is `updates` a required key of the frontmatter?** (cross-skill §1c, cross-skill 1)

| Option | Consequence |
|--------|-------------|
| Required in every skill, `updates: []` when empty | 48 frontmatters change instead of 40; the required-keys check has no exception. |
| Present only where it has a value | Eight skills are not touched for this; the validator needs "absent means empty". |

Recommendation: **required in every skill**; all 48 are edited before the round anyway. Needed before phase C.

**8. Who owns each shared ledger?** (cross-skill §1c, cross-skill 2 and 3; group-3, product-backlog, "For the maintainer to decide"; group-5, ops-pull-request, "For the maintainer to decide" 1)

The owner is the one skill that lists the path in `outputs`; every other writer lists it in `updates`. Undisputed: the state file (`core-project-init`), the calendar (`mkt-content-plan`), `AGENTS.md` (`core-agents-md`), the product backlog (`product-backlog`). To decide:

| Ledger | Options | Consequence |
|--------|---------|-------------|
| The plan, `docs/engineering/plans/<task>.md` (ten writers) | `eng-root-cause`; `eng-impact-analysis`; no skill (the header lives in the layout contract and the validator accepts a contract-owned ledger) | With a skill as owner the validator needs no new concept; with the contract as owner it gains a second kind of owner, and no skill's `outputs` names the plan. |
| Collections two skills add files to: ADRs, post files | One owner each (`eng-architecture`, `mkt-social-copy`) and the other in `updates`; or several owners allowed for a path with a placeholder | With one owner, `eng-tradeoffs` and `mkt-vote-round` have `outputs: []` and say in one sentence that they write in the owner's format. |

Recommendation: **`eng-root-cause` owns the plan; one owner per collection**; `ops-pull-request` and `flow-fix-bug` own no artifact. Needed before phase C.

**9. What does the installer do about the skill-listing budget?** (backlog T18 and Q5; harness §9 and harness M)

One harness lists installed skills to the model within a character budget and lists the ones past it by name only. An eval installs one skill with the budget raised; an installation has 48 skills and the default.

| Option | Consequence |
|--------|-------------|
| The installer measures the listing and, when the person agrees, writes the budget into the settings it creates | Installer work only, after the round (phase F). |
| Smaller packs | Pack files only, after the round. |
| Shorter descriptions, with the detail in the body | Changes all 48 `SKILL.md` files: it must land in phase C or it costs a second round. |

Recommendation: **measure in phase A** (one model call per harness, outside the gate), then the first option where the harness allows it and the second otherwise; the third only if the measurement shows nothing else works. Needed before phase C closes.

**10. What is the runtime (decision D11 of the review)?** (backlog D11 and Q6; review of 2026-10-01, finding C1)

| Option | Consequence |
|--------|-------------|
| Generic, in a top-level `runtime/` folder, the per-agent parts behind a handler | A larger build in phase F; the runtime items R1 to R7 get a "Done when" that can be ticked; a second agent is an extension. |
| It stays one agent's script | The runtime section of the backlog is cut down to what that agent needs; department agents (R3, R4, R8, R9) leave the plan. |

Recommendation: **generic, decided now, built after the round**; until then no new use case is added to `scripts/runtime*.py` (backlog PB16 waits). Either way `payload.py` stops building a provider's path before the round (default 68), because it is inside a skill folder. Needed before phase F; the answer does not move phases A to E.

**11. Fixtures and skill text that still carry a real case: rewritten or removed?** (group-6, mkt-messaging, must-fix 1 and 2; group-3, design-brief, "For the maintainer to decide"; group-6, mkt-content-plan, "For the maintainer to decide" 1; group-6, mkt-vote-round, must-fix 1; group-1, brand-name, must-fix 2; group-1, brand-identity, "For the maintainer to decide" 2; group-1, brand-guidelines, "For the maintainer to decide" 2; group-4 "Patterns" 11; group-5 "Patterns" 12)

What is affected: the `plinth-landing` fixture of `mkt-messaging` (a real project's numbers, decisions and dates under a replaced name); the three fixture files of `design-brief` (dates, counts and two design-file identifiers that only the maintainer can say are invented); the posting schedule of the "Dana" fixtures in five marketing skills; the palette of `brand-identity`'s piece template; one real author's name in `mkt-vote-round`; one real account handle in `brand-name`; the product name shared by five brand fixtures, which is also a real open-source project's name; real hosts in fixtures; and "Gotchas" in ten skills written as the story of one case.

| Option | Consequence |
|--------|-------------|
| Rewrite as fiction: invented product, numbers, dates and people; reserved `.example` hosts; lessons kept without the case | L for `mkt-messaging`, M for `design-brief`, S to M for the others. The cases keep testing what they test. Baselines may move. |
| Remove the affected cases | Less work now; `mkt-messaging` and `design-brief` lose their main cases and coverage. |
| Leave as is | No work; principle 8 stays broken in a public repository. |

Recommendation: **rewrite, never remove**. The maintainer answers three questions of fact first: whether `design-brief`'s fixtures and `brand-identity`'s palette come from a real project, and whether the shared product name is renamed. Needed before phase C (groups 1, 3 and 6).

**12. In `ops-branch-sync`, does a recorded approval cover a push whose merge resolved a conflict?** (group-5, ops-branch-sync, must-fix 1 and "For the maintainer to decide" 1; harness §12, first item)

| Option | Consequence |
|--------|-------------|
| No: a resolved conflict is new content and needs its own yes (the skill's rule today) | The case changes: assertion 5 of case 1 and its expected output, which today reward the baseline for pushing a resolution nobody saw. |
| Yes: the recorded approval covers the branch whatever the merge holds | The skill changes (its stop rule 4 and its gate), and "one approval is enough" is read more widely than the consent rules say. |

Recommendation: **no; keep the skill, change the case**. Needed before phase C (group 5).

**13. How far does the evidence convention go?** (group-3 "Patterns" 1 and 2; group-4 "Patterns" 1 and 2; group-5 "Patterns" 6; group-6 "Patterns" 4; cross-skill §3f and cross-skill 12, which advises against it)

The convention: a check script takes `--report <file>` and writes one record of one shape; the reply's template has a line with the command and the line it printed, copied; a line lists the files changed, from `git status --short`; the assertion asks for the file and the quote.

| Option | Consequence |
|--------|-------------|
| Everywhere, with one field name and one line wording in all lint scripts | Scripts, tests, templates and assertions change together in about 16 skills, including four whose evidence already works. |
| Where the audit measured a failure or found no evidence at all: `--report` added to the six lint scripts that lack it, one report shape, an evidence line in every reply template that has none; lines that already quote a command and its output stay as they are | About 12 skills get script changes; the four that work are untouched; the canonical form goes into the template for new skills. |
| Nowhere; rely on rule 4 of the new grading template | No skill work; the measured cause of most with-skill failures in three groups stays in the skills. |

Recommendation: **the second**. Needed before phase C.

**14. How many new cases are added before the round?** (the "Cases" and "Coverage" items of the six group reports)

The group reports propose 46 new cases (degraded modes, stop gates, branches no case reaches). Each case adds 20 runs at 5 runs per case.

| Option | Consequence |
|--------|-------------|
| All of them | 187 cases: about 3,740 runs and 46 hours of compute. Every proposed branch is measured. |
| Targeted: a case only where the skill's main path is never measured, or where this plan changes a behaviour that no case reaches (15 cases in 12 skills, named in the skill table of phase C) | 156 cases: about 3,120 runs and 39 hours. |
| None | 141 cases: 2,820 runs and 35 hours. Behaviours changed in phase C go unmeasured, which is what a later round would be asked for. |

Recommendation: **targeted**. The other proposed cases become one backlog item per skill, built when that skill is next changed. Needed before phase C.

### (b) Defaults applied unless the maintainer objects

The measurement:

15. When the grader cannot see what an assertion is about, the assertion fails; the harness gives the grader the facts instead of a third verdict (harness C).
16. A with-skill run that times out or is refused by the provider is retried inside the iteration and counted in the record; a timeout that repeats on a case without web scores 0, on a web case it stays an infrastructure failure (harness D).
17. The provider credential stays in the run's environment; its value is redacted from every stored output and before grading, the floor key is rotated and replaced by a low-limit key for evals, and the property is documented; a sidecar that keeps the credential out of the run is a backlog item for a later round (harness E).
18. The runner stages the skill copies before the container starts, and a container mounts the case folder and the one `run-prompt.sh` in use (harness G). The shared helper for the two adapters is dropped as an item: staging removes their duplicated install code (backlog PL-helper, Q4d).
19. Web cases use the live web, are serialised by the runner and are marked in the record (harness K).
20. The repository files a case brings (`workbench_files`) are hashed into the record, so a harness change makes `core-skill-creator` stale and no other skill (harness L).
21. `shared/references/` is covered by the measurement fingerprint, since every run gets a copy of it and no skill's hash sees it (this plan's addition to harness §7).
22. `expected_output` is never shown to the grader; `core-skill-creator` says it is context for a person and for the preflight (harness §1, "The `expected_output` question").
23. The tolerance stays 0.05: the smallest measured difference with and without a skill is 0.115 (harness §2; backlog N3 and Q4b).
24. `invoked` (did the with-skill run load the skill) is a reported field; a run that never loaded the skill still scores, as the description's failure (backlog T1 and Q4a).
25. The strong tier's event stream is kept in a file the grader never sees, and refusal markers move to adapter data, both in phase B: each changes a file the freeze covers, so "after the round" would break the freeze (harness §12d and §12e proposed after).
26. The gate compares unrounded means and rounds only for display (harness §7).
27. From version 5, `--only without --update-record` is refused and a record built from a benchmark on disk says so (harness §12).
28. On a case without `allow_web` the floor runner's page-fetch tool is denied, so both tiers have the same tools (harness §4).
29. The baseline of a case with dependency skills is "the other skills without this one", and the record's documentation says so; `skills` in a case is for a flow's phases, or for a skill whose own script calls another skill's script until vendored copies remove the need; it is removed from `design-execute` (harness §12; group-3 "Patterns" 16).
30. The folder an adapter installs the skill into is excluded from the case folder's `git status`, and fixture copies ignore bytecode and system files (group-4 "Patterns" 3 and 4).
31. Installers install the stripped copy the evals use, with `shared/` beside it, after the round (harness M).
32. `validate.py` always uses its own subset parser for frontmatter, so that every machine validates alike (harness §10).

Cases and assertions:

33. Assertions that pass in every run: the language ones are removed, guards are kept and reworded so that the grader can verify them, content ones are replaced by sharper ones the baseline fails; already instructed by the maintainer (backlog T19 and Q2; harness J).
34. T11 stays ticked as the first round; the final round is a new backlog item whose "Done when" is 48 `evaluated` and `validate.py --strict` green (backlog Q1).
35. Product names: a third-party product that is not an AI tool may be named in prompts, fixtures, credential-format labels and detection lists when it is what a user types or what the code must recognise; AI tools and generative design tools are replaced by fictional names; `AGENTS.md` says so once next to principle 1 (group-1, biz-icp-positioning 3; group-2, core-orchestrator 2; group-3, design-brief; group-4, eng-code-review 1 and eng-codebase-map 1 and 2; group-5, eng-security-review 2, ops-ci-pipeline 2, ops-pull-request 3).
36. Fixture families are neither unified nor shared through the sync script; a defect is fixed in every copy in one change (cross-skill 14).
37. A fixture that names a flow that is not built reads `Current flow: none` (group-3, product-prd; group-4, eng-architecture and eng-implement 3); `ops-branch-sync` keeps one fixture whose Approvals section is a hand-kept list, and its new case uses the contract's table (group-5, ops-branch-sync 3).
38. Prompts that say "in invoices/" say "the invoices project": the fixture's content is the case root (group-4, eng-docs; group-5, eng-refactor 3).
39. Confirmation gates that need an integration the container lacks (a design tool, an image generator, an issue tracker) are accepted as unmeasured; the degraded path is what a case checks (group-3, design-execute, design-system and product-backlog).
40. `core-critique` case 4 stays as the one check that the skill does not invent problems; its fixture is repaired (group-2, core-critique 1).
41. In `core-research`, an address may appear under "Method" when it was tried and could not be opened; the assertion follows the skill (group-2, core-research 1).
42. In `eng-unit-tests`, the prompt of case 3 stays, its two assertions that always fail together are merged and an independent one is added (group-5, eng-unit-tests 1 and 2).
43. In `eng-security-review`, the assertion about dismissal reasons stays and the skill changes; case 4's fixture is made harder; the alert product's name stays once, in quotes, among the user's words (group-5, eng-security-review 1 to 3).
44. In `mkt-vote-round` case 1, a post may use any sourced number that belongs to the topic; the assertion checks the sources and that nothing is offered twice (group-6, mkt-vote-round 1).
45. `brand-name` gets a fictional handle and a `--responses <file>` option in its script, so that its case no longer depends on what the live network says about a name (group-1, brand-name 1).
46. The fixtures of `design-handoff` are recorded as edited by hand; no builder script is added (backlog PL-cases).

The artifact contract and the frontmatter:

47. An input that no built skill writes is declared in a table of `contracts/project-layout.md` ("Slots no built skill writes": `user` or `planned: <skill>`); no skill changes for it and a dangling input becomes an error (cross-skill 4; backlog Q8; group-1, biz-market-analysis, must-fix 5 and group-6, mkt-content-plan, must-fix 3 offered removal instead).
48. Placeholder syntax: the closed vocabulary in use today, matched as wildcards, a trailing `/` for a folder, no section-level paths (cross-skill 5).
49. `eng-implement` writes a short "Change" section in the plan when the task is a fix plan, and lists the plan in `updates` (cross-skill 6).
50. Side effects outside a gate: `flow-fix-bug` loses its direct push (delivery only through `ops-pull-request`; a direct push stays with the user), and `core-orchestrator` executes nothing with a side effect when no skill owns the gate (group-5, flow-fix-bug 1; group-2, core-orchestrator 1). Cross-skill 7 recommended the opposite: a declared gate for the flow and a reworded protocol for the orchestrator.
51. Status words: a row of the state file keeps `draft`, `approved`, `skipped`; an artifact's header may carry a finer status its owner defines; the three skills that write another word into the state row change it (cross-skill 8).
52. A script of one skill that another skill calls becomes a generated copy in the caller, looked up next to the caller first (cross-skill 9); the source of every shared script is `shared/scripts/`, never one of the skills that use it (cross-skill §2a; group-1, biz-market-analysis 3).
53. No shared Markdown helper for the lint scripts: defects are fixed in place and one generic conformance test holds the command-line rules (cross-skill 10).
54. Vocabularies: `search:web` covers any read-only use of the public web, required or optional, and every skill that uses a class declares it; `side_effects` is closed to `publish`, `send`, `schedule`, `deploy`, `create`, `push`, `dismiss`; `write` becomes `create`; a comment or reply posted on a host is `create` (cross-skill 11; group-3 "Patterns" 13; group-5, ops-pull-request, must-fix 2 proposed a new word `comment`).
55. By the same rule `ops-repo-baseline` declares `search:web` for reading action tags from the host (group-5, ops-repo-baseline 1 recommended leaving it empty).
56. `publisher:<platform>` is a legal value of `requires`: the validator accepts a class whose sub-class is the placeholder (harness §10).
57. `mkt-engage` drops `mailbox` from `requires` until its e-mail parser is verified, and its parser takes `--platform` with one platform implemented; its cases' prompts keep naming the runtime contract, and the skill says that file is not in the project and need not be read (group-6, mkt-engage 1 to 3).
58. `brand-identity` declares `search:web` with its degraded behaviour written; its case 2 stays offline and asserts the "unverified" label; the headless browser gets no requirement class (group-1, brand-identity 1 and 4).
59. Canonical sentences applied in phase C: the script-location sentence, the external-content form and its place above a closing question, a self-check where it is missing and before the reply, the "stop and tell the user to run it first" form, planned marks, the stop-gate wording, and "write the script's name and arguments, never its path" in artifacts. The external-content sentence is also added to the four skills without it, and the security scan's rule names a diff and command output among the sources that require it (group-3, product-roadmap; group-4, eng-integration-tests 1; cross-skill 12 advised against). Not applied: an origin clause in the 26 self-checks that lack it, language wordings, project-root wordings (cross-skill 12).
60. `metadata.version` is raised once per pull request that changes a skill's folder; all 48 are raised once in phase C; the authoring guide says so (cross-skill 13).
61. `core-security-audit` declares the records it writes under `docs/security/` with a `<skill>` placeholder; `core-skill-creator`, whose target is the workbench itself, keeps empty lists (cross-skill 15; group-2, core-skill-creator 2).
62. Test file names are unique across the repository, enforced by `validate.py` (cross-skill 16).
63. Who registers an artifact in the state file is a rule of `contracts/state.md` (a named slot that later skills read is registered; plans, reviews, logs and inboxes are not); `core-research`, `core-critique` and `ops-repo-baseline` gain the registration (cross-skill 17; group-2, core-critique 2 and core-research 2).
64. Project files that are the work itself (source, tests, documents, workflow files) are not declared; the layout rule says "the workbench artifacts a skill writes" (cross-skill §1e; group-4 "Patterns" 6).
65. `flow-fix-bug` has the state file created through `core-project-init`, which owns it, and its case lists that skill as a dependency (cross-skill §1g; group-5, flow-fix-bug, must-fix 4 proposed a copy of the template as an asset).
66. Inputs declared and never read are removed in `eng-refactor`, `ops-ci-pipeline` and `design-system`, and kept with a new Inputs row in `mkt-social-copy` and `mkt-messaging`, as their group report recommends (cross-skill §1e; group-6).
67. The vote data files `mkt-vote-round` reads become a contract under `contracts/`, and its script takes `--platform` (group-6, mkt-vote-round 2).
68. `mkt-publish`'s `payload.py` takes `--publisher <path>` (the path the resolver printed) and requires `--platform`, before the round (group-6, mkt-publish 1; backlog N2).
69. One rule for finding the workbench root in the three skills that reach a provider: the variable, then the decision recorded in the state file, then ask once and record (group-6, mkt-engage, should-fix 7).

Rules inside single skills:

70. `core-skill-creator`: on the improve path a security "no" is fixed in the same iteration and reported on the Security line; the two unused parts of its authoring guide are deleted (group-2, core-skill-creator 1 and 3).
71. `core-research`'s script is renamed `check_brief.py`, as every other script is spelled (group-2, core-research, should-fix 7).
72. `design-brief`: the sentence that lets the skill search for its inputs anywhere is removed; prompts name a fictional design tool (group-3, design-brief).
73. The leftovers of the pre-container command rules ("no `cd`, no `&&`, no pipe") are cut down to "run each command on its own" in `design-handoff`, `core-agents-md` and `core-project-init` (group-3, design-handoff; group-2 "Patterns" 11).
74. The writing standard names two kinds of gate: a decision that stops before anything is written, and an open question written into a draft with its readiness set to "no" (group-3 "Patterns" 8).
75. A one-word acceptance of recommended answers ("ok", "yes to all") stays possible where the skill offers it and is recorded as `user answer (accepted recommendation, <date>)` (group-3, product-prd and product-feature-spec).
76. `eng-architecture` keeps the JSON line its check prints (group-4, eng-architecture 3).
77. `eng-code-review` keeps its isolated-reviewer branch as one line after the default path, and gets its own test of its `redact.py` copy (group-4, eng-code-review 2 and 3).
78. `redact.py` gets a neutral docstring, changed in its source and its copies together (group-5, ops-repo-baseline 2).
79. `eng-implement`: a task is `done` only when its check passes, or when the task makes a recorded result the deliverable; otherwise `blocked` with the failing line (group-4, eng-implement 1).
80. `eng-root-cause`: a cause is `confirmed` when the experiment matches in every installed runtime and the defining rule is quoted from a fetched source; a runtime that is not installed is listed as not run (group-5, eng-root-cause 1).
81. `eng-tradeoffs`: a missing input stops before any record is written (group-5, eng-tradeoffs 1).
82. `ops-ci-pipeline` pins actions to commits by the same sentence as `ops-repo-baseline` (group-5, ops-ci-pipeline 1).
83. `ops-repo-baseline` states once that this version writes for one code host (group-5, ops-repo-baseline 3).

Process and repository:

84. Whether a project's `docs/` is versioned is asked per kind (code-related documents versioned, work data local), recorded in the state file and the project's `AGENTS.md`, and built before the round (backlog C1 and Q3; group-2, core-project-init 1).
85. The optional copy of an approved payload (backlog S15) is dropped: the durable payload folder already keeps what was approved (backlog Q9).
86. The backlog moves to the issue tracker without the generated index, right after the round (backlog T14 and Q7).
87. `container` and `python39` become required checks once both have been green twice (backlog Q10).
88. Of the two design documents written around one case, `always-on-runtime.md` moves to the project it describes and `weekly-vote.md` stays, rewritten as the generic contract (backlog Q11).
89. T12 is ticked on its own "Done when"; the local-model tier becomes its own item, deferred as the maintainer decided (backlog T12, N14).
90. No deny list of product names for skills in `validate.py`; a warning for AI and design-tool names in eval cases and fixtures (harness §10; group-3 "Patterns" 11).

### Where the reports disagree

| Subject | The reports | This plan |
|---------|-------------|-----------|
| Evidence line and `--report` | Cross-skill 12 advises against changing them (16 skills at once, for uniformity); groups 3 to 6 show it is the main measured cause of failures with the skill | Decision 13, recommended: where a failure was measured or no evidence exists |
| Side effects outside a gate | Cross-skill 7: gate the flow's push, reword the orchestrator; groups 2 and 5: remove both | Default 50: remove both |
| The external-content sentence in the four skills without it | Cross-skill 12: do not add; groups 3 and 4: add | Default 59: add |
| An optional network read and `requires` | Cross-skill 11: declare it; group 5 on `ops-repo-baseline`: leave empty | Defaults 54 and 55: one rule, declare |
| The two inputs no skill produces | Groups 1 and 6: remove or mark; cross-skill 4 and backlog Q8: a table in the layout contract | Default 47: the table |
| The state file in `flow-fix-bug` | Group 5: ship a template as an asset; cross-skill §1g: create it through its owner | Default 65: through the owner |
| Inputs declared and not read (`mkt-social-copy`, `mkt-messaging`) | Cross-skill: remove, or name them; group 6: add the Inputs row | Default 66: add the row |
| `patch` | Group 4: the skill should use git; harness §8: add `patch` to the image | Both: the skill uses `git apply`, the image gains `patch` and `file` |
| The adapters' shared helper | Backlog: drop; harness §4: the runner stages the skills, which removes the duplicated code | Default 18: staging; the helper is not built |
| The skill-listing budget (T18) | Backlog: measure and decide before the round; harness §9: not needed for the round | Decision 9: measure in phase A, installer work in phase F |
| Strong-tier transcripts, refusal markers | Harness §12: after the round | Default 25: phase B, because they change frozen files |
| How many skills at a time | Harness: five; backlog: "several"; the maintainer: ten, web cases serialised | Ten, with the total held by the runner's lock |
| Which skills search the web | Backlog: two skills measured alone; harness: nine cases in five skills | The runner serialises web cases itself; no skill is measured alone |
| The count of always-passing assertions | Backlog T19: 200 of 663; harness: 196 of 664 | The group reports' per-assertion lists are what phase C uses |
| The size of `core-skill-creator` | 5,320 tokens (group 2), about 5,900 (backlog), about 6,000 (harness): three estimates | Trimmed to about 4,100 by group 2's list; the validator's rule is characters divided by 4 |
| Stale skills | Group reports: 12 (read at `b363f1b`); backlog: 15 (after #44) | 15 |
| `AGENTS.md` naming old eval paths | Group 2 "Patterns" 12 says it still does | It does not on `3cbc7f2`; nothing to do |

## The plan, in phases

How the phases fit together:

| Phase | What | May run in parallel with | Ends with |
|-------|------|--------------------------|-----------|
| A | Repairs and records that touch neither a skill folder nor the measurement | B and the convention work of C | `main` green, the backlog true to the code |
| B | The measurement, changed once | A and C (other files: `evals/`, `adapters/`) | measurement version 5 and its fingerprint |
| C | The skills, each edited once | B | 48 skills changed, none measured |
| D | Dry run | nothing: it needs B and C merged | a pilot that passes |
| E | The final round | F items that touch no frozen file, in another working tree | 48 records under version 5 |
| F | After the round, independent of skills | G | each lane's own exit |
| G | New skills and flows, each measured when built | F | each skill `evaluated` |
| H | Waiting on the maintainer or on the world | everything | the event |

Working rules for every phase: one pull request per item or per batch, with its tests; `python3 scripts/validate.py` at zero errors before each commit; a pull request that changes a skill folder ends with `python3 evals/eval_status.py inventory --write` and measures nothing; independent items run at the same time in separate working trees and merge one at a time (principle 7: the single `main` and its approval are the shared resource).

### Phase A. Repairs and records with no effect on skills or measurement

Goal: `main` is green, the backlog and the documents say what is true, and the validator can tell phase C which skills it must touch. Nothing here changes a skill's hash or what a run measures, so every item is safe at any time.

| # | Item | Touches | Specified in | Size |
|---|------|---------|--------------|------|
| A1 | Merge the repair of the `python39` CI job (pull request #45); add a wiring test so that a path the workflow names must exist | `.github/workflows/checks.yml`, `scripts/tests/test_checks_wiring.py` | backlog "Findings" 13, N1 | S |
| A2 | Backlog hygiene: tick S19, T16, T12, T2, P1; rewrite S11, PB5, PB6, PB7, PB8, PB15 to what is really open; leave T11 as the closed first round and open the item "Final measurement round"; split the local tier out of T12; drop S15; give ids to the work of N1 to N19 that survives; fix the paths that no longer exist; move done items, as they are, to `docs/backlog-archive.md` | `docs/backlog.md`, `docs/backlog-archive.md` (new) | backlog "Findings" 1 to 10, "Ids", "T14", action plan step 1.1; defaults 34, 85, 89 | M |
| A3 | Principle 8 cleanup of the documents: the brand and runtime sections of the backlog, `docs/inventory.md` State cells, the decisions entries that describe one case, `always-on-runtime.md` and `weekly-vote.md` (default 88); mark the decisions entries that a later entry reversed; correct the inventory's counts, its `explorer` row and its old-gate scores | `docs/backlog.md`, `docs/decisions.md`, `docs/inventory.md`, `docs/architecture/` | backlog "Principle 8", "Overlaps and contradictions", N8, N18, N19 | M |
| A4 | Stale documents outside skills: the "Containment" paragraph and `--dry-run` text of `evals/eval_run.py`'s docstring (comment only); the adapters' READMEs on the two tiers' home folders; `AGENTS.md` gains the product-name rule (default 35) | `evals/eval_run.py` (docstring), `adapters/*/README.md`, `AGENTS.md` | harness §12c, §4 "Environment"; default 35 | S |
| A5 | Validation rules, added as warnings first: required metadata keys and `license`; `requires` against the classes of `contracts/environment.md`; the `side_effects` vocabulary; a description that says when to use the skill; a description over 900 characters; `SKILL.md` over about 5,000 tokens; at least two cases; `evals.json` with known keys only, `skill_name` equal to the folder, unique ids; fewer than three assertions in a case; a conditional assertion; an assertion that something "is run" with no word about quoted output; a prompt that names the skill under test; a backticked skill name that is neither built nor marked planned; every built skill in the orchestrator's routing table; unique test file names; `packs/` scanned as core; AI and design-tool names in eval cases; one frontmatter parser on every machine. Its output is the list of skills each rule flags, attached to the pull request | `scripts/validate.py`, `scripts/tests/` | harness §10; backlog PL-validation; cross-skill §1g item 3, §2e; group-3 "Patterns" 11 and 12; defaults 32, 62, 90 | M |
| A6 | Secrets in stored outputs: after each run and before grading, replace the values of the passed variables in the reply, the transcript and the case folder by a marker, with `scripts/redact.py`, and count the replacements; document that a run's environment holds the tier's credential | `evals/eval_run.py`, `evals/tests/`, `contracts/secrets.md`, `evals/executor.py` (comment) | harness §4 "Secrets", harness E; default 17 | S |
| A7 | Two flaky or missing checks: raise the margin of the adapter timeout test that fails under load; the pre-commit hook maps `.githooks/`, `.github/` and `packs/` to `scripts/tests` | `adapters/api/tests/`, `.githooks/pre-commit` | harness §11, §11c | S |
| A8 | Measure the skill-listing budget: after `install.sh --pack default` on each harness, ask the model once to quote its skill list and count the descriptions that came back; record the count per pack and harness in `docs/inventory.md`. It is one model call per harness, outside the gate, and it feeds decision 9 | `docs/inventory.md` | backlog T18; harness §9 | S |
| A9 | Backlog ids for the planned flows, the `explorer` agent and the planned skills that have none | `docs/backlog.md`, `docs/inventory.md` | backlog N16 | S |

Actions that are the maintainer's and sit outside the repository: rotate the floor provider's key and create a low-limit key for evals (harness E); scrub or delete the 14 stored transcripts that hold the old key; delete the untracked bytecode files in the fixtures of `eng-code-review` and in three skills' `scripts/` folders on the measuring machine (group-4, eng-code-review, must-fix 8); add `container` and `python39` to the required checks once both have been green twice (default 87).

- Parallel: four lanes. Lane 1: A1, then A7. Lane 2: A2, A3 and A9 (the same files, one after another). Lane 3: A5. Lane 4: A4, A6, A8.
- Size: 4 M and 5 S.
- Depends on: nothing. A5 should merge before the group batches of phase C start, because its list tells them what to touch.
- Exit: every CI job green on `main`; `validate.py` at zero errors with the new warnings listed; no ticked backlog item whose "Done when" fails and no built item unticked; no document outside `docs/architecture/audit-2026-10-02/` that carries one real case's names, dates or numbers.

### Phase B. The measurement, changed once and then frozen

Goal: every change that alters what a run measures, or what the model under test or the grader sees, lands in one series that ends by raising `measurement_version` from 4 to 5. After its last commit nothing in `evals/`, in the eval adapters or in the image changes until the round is recorded.

| # | Item | Touches | Specified in | Size | Needs a proof run |
|---|------|---------|--------------|------|-------------------|
| B1 | The image: remove or open the root-owned scratch folder of the floor runner; `TZ=UTC`, `LANG=C.UTF-8`, `USER` and `PYTHONDONTWRITEBYTECODE=1` set in the image, `TZ` no longer forwarded from the host; add `file` and `patch`; add `gh`, signed out and pinned (decision 5); one git identity, in the image; `DEBIAN_FRONTEND` as a build argument; base images by digest, the package index from a dated snapshot, the two runners installed from a committed lock file; the platform fixed in the executor; the built image stored and its digest written into every record (decision 4); confirm what the strong runner does with a model id it logs as unrecognised, before its version is pinned | `evals/container/`, `evals/executor.py`, `evals/tests/test_executor_docker.py` | harness §8, §4 "Environment"; backlog PL-digest | M | yes |
| B2 | What a run sees: the runner stages the skill under test and its dependencies (without `evals/` and `scripts/tests/`) and `shared/` into the case folder, and the container mounts the case folder and the one `run-prompt.sh` in use; the adapters lose their install code; `workbench_files` leave out a skill's `tests`; fixture copies ignore bytecode and system files; the staged folder is added to the case folder's git exclude list; a record names any extra `--pass-env` variable or is refused | `evals/eval_run.py`, `evals/executor.py`, `adapters/claude-code/run-prompt.sh`, `adapters/agents-dir/run-prompt.sh`, `adapters/*/adapter.json`, their tests | harness §4 "Mounts", "The case folder", "Environment"; group-4 "Patterns" 3 and 4; defaults 18, 30 | M | yes |
| B3 | Grading: the new template (what the grader is and is not given, eleven rules); a facts block built by the runner from content hashes taken before and after the run (created, modified, deleted, unchanged inputs) and from the state of version control; the case's input files shown as the run found them, even when the run changed them; the grading call with no tools; a result whose count differs from the assertions is refused; a refused or unparsable grading is retried up to twice; results are read by position and the grader no longer returns the assertion's text; the number of grading passes read from the gate file (decision 2); the template's hash in the record | `evals/grading-prompt.md`, `evals/eval_run.py`, `adapters/claude-code/run-prompt.sh` (`--no-tools`), tests | harness §1 (template text and "Runner changes that go with it"); group-1 "Patterns" 14; group-2 "Patterns" 7; group-3 "Patterns" 17; defaults 15, 22 | M | yes |
| B4 | The early-end rule: empty, markup, or a short reply whose final sentence announces an action; never a reply that states a blocker; the 17 real replies become tests; the stop reason and turn count are kept; early ends are counted per variant | `evals/eval_run.py`, `evals/tests/test_eval_run.py` | harness §3 | S | no |
| B5 | Control of a round: `runs`, `timeout_seconds`, `retries`, `web_jobs` per tier and a total of concurrent runs in the gate file, held by a lock that several runner processes share; a record is written only from the configured values; retries inside the iteration for a refusal, a transient adapter failure and a timeout, each counted (default 16); `--resume <iteration>` for the failed runs only; unrounded gate comparison; sample standard deviation | `evals/eval-gate.json`, `evals/eval_run.py`, `evals/eval_status.py` (`GATE_FIELDS`), tests | harness §2 "Also fix", §6; defaults 16, 19, 26 | M | yes (the lock and `--resume`) |
| B6 | Contamination: the dead check is replaced by three: a without-skill container has no path that holds the skill (asserted in the docker test); a without-skill run that names a mount path blocks the record; a passage of ten words shared with the skill's text and absent from the case is a warning with the passage quoted | `evals/eval_run.py`, tests | harness §5 | S | no |
| B7 | The record: new fields required from version 5 (runs configured, spread and standard error per variant, mean per case, refusals, timeouts, retries and early ends per variant, grading hash and regradings, tool versions, platform, image digest, adapter hashes, `workbench_files` hash, web cases, extra variables, attempts, source); `stale` also when the harness names, the runs or the `workbench_files` hash differ; `marginal` shown beside `evaluated` when a score is within two standard errors of the threshold; the status table shows the floor baseline, the runs and `marginal`; `--only without --update-record` refused | `evals/eval_status.py`, `evals/eval_run.py`, `docs/inventory.md` (generated), tests | harness §7, §2 "Is 3 enough"; defaults 20, 27 | M | no |
| B8 | What a run did: an `invoked` field per with-skill run, reported and never scored; the strong runner's event stream kept in a file beside the raw output, never shown to the grader; the floor runner's token use recorded when it can print it; refusal markers moved from the runner's code to each adapter's data; the floor runner's page-fetch tool denied on a case without web | both `run-prompt.sh`, `adapters/*/adapter.json`, `evals/eval_run.py`, tests | backlog T1; harness §12d, §12e, §4 "Proxy, DNS", §12 "The floor runner reports no tokens"; defaults 24, 25, 28 | M | yes (`invoked` on both tiers) |
| B9 | Checks that need no model: the case preflight rejects a prompt token that ends in `/` and names no folder of the case, `skills` outside the allowed uses (default 29) and a `grader_files` path that does not exist; the container job runs the preflight of every skill with its setup, each `run-prompt.sh` in the image with stub runners, the grading path with a stub grader, and checks that a name outside the proxy list does not resolve | `evals/eval_run.py`, `evals/tests/`, `.github/workflows/checks.yml` | harness §11, §10 (rows on `grader_files`); group-2 "Patterns" 9; group-3 "Patterns" 16 | M | no |
| B10 | The freeze mechanism: `evals/measurement.json` holds the constants that define the measurement (the file limit, the early-end phrase lists, runs, timeout, retries, refusal markers); `eval-gate.json` gains `measurement_fingerprint`, the hash of the grading template, every file of `evals/container/`, the two `run-prompt.sh`, `measurement.json` and `shared/references/`; `validate.py` recomputes it and fails when it differs | `evals/measurement.json` (new), `evals/eval-gate.json`, `evals/eval_status.py`, `scripts/validate.py`, tests | harness §7 "The freeze"; decision 3; default 21 | S | no |
| B11 | The last commit of the series: `measurement_version` 5, the fingerprint, an entry in `docs/decisions.md`, and the documents that describe the harness (`AGENTS.md` "Adding an adapter" and "Writing standard", the adapters' READMEs, what "without the skill" means for a case with dependencies) | `evals/eval-gate.json`, `AGENTS.md`, `docs/decisions.md`, READMEs | harness "Proposed order of work" step 3; default 29 | S | no |

**The proof run.** Before B11, one skill is run through the new harness to prove the items marked "yes": a skill with a script and a setup step, both of its cases, the four variants, 2 runs each (16 runs and their gradings, well under an hour of compute and a few dollars of notional cost). No record can be written from it, because 2 is below the configured number of runs. It must show: both runners start in the pinned image and the strong runner accepts the configured model; the staged skill is discovered and its description reaches the model (`invoked` is true in the with-skill runs of both tiers); the floor runner writes its scratch files; the grader answers with no tool, with one result per assertion, and its facts block matches the case folder; a second runner process waits on the shared lock; `--resume` reruns only a run that was made to fail. A second proof run on one web case checks `web_jobs`. Anything found is fixed inside version 5, before a record exists under it.

- Parallel: B1, B3, B4 and B6 touch different parts and can be built at the same time; B2 and B8 both rewrite the two `run-prompt.sh` and go one after the other; B5 and B7 share the gate file and the record and go one after the other; B9 follows B2 and B3; B10 and B11 come last. Phase B as a whole runs beside phases A and C.
- Size: 7 M and 4 S, plus the proof run.
- Depends on: decisions 1 to 5.
- Exit: `measurement_version` is 5 and `validate.py` accepts the fingerprint; every test of `evals/` and the adapters passes, the container job included; the proof run's checklist is met; all 48 skills read `stale`, which is the intended state before the round.

### Phase C. The skills, each edited once, all before the round

Goal: every change the audit asks of a skill folder lands before the round, in one pass per skill: its frontmatter, its scripts, its text, its cases. First the conventions that hold for the whole repository are decided and built once (C0), outside the skill folders; then each skill gets all of its changes (the table of 48 rows).

#### C0. Conventions decided once, before any skill is edited

| # | Convention | Touches | Specified in | Size |
|---|-----------|---------|--------------|------|
| C0.1 | The artifact contract (D7): `updates` beside `outputs` in the frontmatter contract of `AGENTS.md`; in `contracts/project-layout.md` the placeholder rule and its vocabulary, the table "Slots no built skill writes", a generated table of owning skills, the rules that are false today rewritten, the folders skills write and the tree lacks; in `contracts/state.md` the status words and who registers; `validate.py` rules 1 to 7 of the contract, as warnings until the last group batch merges and as errors after it | `AGENTS.md`, `contracts/project-layout.md`, `contracts/state.md`, `scripts/validate.py` | cross-skill §1b, §1c, §1d, §1e; decisions 7 and 8; defaults 47, 48, 51, 63, 64 | M |
| C0.2 | Vocabularies: the widened definition of `search:web`, the closed list of `side_effects`, the placeholder sub-class of `publisher`; the validator's two vocabulary warnings of A5 become errors with C0.1 | `contracts/environment.md`, `scripts/validate.py` | cross-skill §1f; defaults 54 to 56 | S |
| C0.3 | Shared code (D8): `shared/scripts/` as the one source, with its tests; a manifest of copies; `scripts/sync_copies.py` (write, or `--check` for the validator and the hook); one generic identity test instead of three. First families: `rank.py`, `check_refs.py`, `redact.py`, the tests' `conftest.py`, the reconciled `contrast.py`; then the three scripts one skill calls from another (`sensitive_topics.py`, `voice_stats.py`, `check_post.py`); then two prose copies for the orchestrator (the requirement-class table and the table of owners) | `shared/scripts/`, `scripts/sync_copies.py`, `scripts/test_dirs.py`, `scripts/tests/`, `scripts/validate.py` | cross-skill §2a, §1g; defaults 52, 78 | M |
| C0.4 | Command-line conformance: one generic test over every script under `skills/*/scripts`: `--help` exits 0 and prints text; each value flag given last exits 2 with a message and no traceback; an unknown flag exits 2; a usage error goes to stderr. The scripts it finds failing are fixed in their skill's row, never through a shared parser | `scripts/tests/` (new test) | cross-skill §2b, §2c; group-3 "Patterns" 3; group-4 "Patterns" 10; default 53 | S |
| C0.5 | The evidence convention (decision 13): one shape for a check script's `--report` file; the reply line "the command exactly as run, an arrow, the line it printed"; a "files changed" line taken from `git status --short`; the assertion form that asks for the file and the quote | `templates/capability.SKILL.md`, the authoring guide (in `core-skill-creator`'s row) | group-3 "Patterns" 1 and 2; group-4 "Patterns" 1 and 2; cross-skill §3f | S |
| C0.6 | Canonical sentences, written into the templates first: where a skill's scripts are and how they are run; the external-content sentence, its source list, its place above a closing question, and what is not an instruction; the stop gate ("go" is not an answer, nothing is written before the answer), the two kinds of gate, a "Stop rules" section above the procedure, a template for the reply that asks; the self-check, placed before the reply; the "stop and tell the user to run it first" form; the planned mark; "the script's name and arguments, never its path" in artifacts; dates from a command; a scratch copy made in one chained command; `updates` in the frontmatter | `templates/capability.SKILL.md`, `templates/flow.SKILL.md`, `AGENTS.md` "Writing standard" | cross-skill §3a to §3h; group-1 "Patterns" 1 to 3; group-2 "Patterns" 3 and 16; group-3 "Patterns" 7 to 9; group-4 "Patterns" 5 and 9; group-5 "Patterns" 1 and 13; defaults 59, 74 | M |
| C0.7 | The rules for cases, written where case authors read them: assertion kinds and what is done with each; no conditional assertion; no assertion about a command the grader cannot see; "is not among the files the run produced or changed" for what must not change; `grader_files` for every input an assertion checks; `absent_on_purpose`; a prompt names no path the case does not have; a fixture is a small real project in the project's layout with fictional names and `.example` hosts; no date relative to the day of the run | the authoring guide (in `core-skill-creator`'s row), `evals/README.md` (new) | harness §1, §10, §12; group-1 "Patterns" 4 to 6; group-2 "Patterns" 4 to 9; group-4 "Patterns" 1; group-6 "Patterns" 1 and 5 | S |
| C0.8 | Fixes of shared fixture families, each made in every copy in one change: the invoices project (the runtime the image has, a lint that can run, the reproduction script two plans name, prompts that name no missing folder), eleven copies in groups 4 and 5; the "Dana" brand and marketing fixtures (reserved hosts, dates, the schedule, the author's name), sixteen copies in groups 1 and 6; the ledger PRD, two copies in group 3 | `skills/*/evals/files/` | cross-skill §2d; group-4 "The invoices fixture"; group-5 "Patterns" 2 to 4; group-6 "Patterns" 7 and 8; decisions 6 and 11 | M |

C0.1 to C0.7 touch no skill folder and can be built beside phase B. C0.8 is skill content: the invoices family is changed in the batch of group 5 (with group 4's three copies in the same pull request), the Dana family in the batch of group 6 (with group 1's copies), the ledger file in the batch of group 3.

#### The rule for case changes

- An assertion changes only for a stated reason: it never influences the score (it passes in every run of every variant and is a language assertion or content any model produces); it fails a good output for a formality; it rests on something the grader cannot see; it is conditional; or it contradicts the skill. When the output is not good, the skill is fixed, never the assertion.
- A guard (something that must not happen) is kept even when it always passes, and is reworded so that the grader can verify it.
- A content assertion that always passes is replaced by a sharper one that the audit's evidence shows the baseline failing; a replacement that still passes everywhere in the final round is listed in the round's report and left alone until the skill is next changed.
- **Every assertion change is listed before and after in the pull request**, with its reason; so is every change to a prompt, an expected output or a fixture.
- A new case follows C0.7 and is listed with the behaviour it measures.
- Once phase C is merged, the cases are frozen for the round. During the round a case changes only through the repair loop of phase E, under the same rule.

#### The 48 skills

One row per skill, with every change it gets: from its group report, from the cross-skill change list, from the harness report's case items and from the backlog items that touch it. **F** is the frontmatter, **S** the scripts and their tests, **B** the body of `SKILL.md` and its references and assets, **K** the cases (assertions, prompts, fixtures). The assertion work of backlog T19 is inside each row's **K**, not a separate pass. Every row also gets, without saying so: `updates` in the frontmatter (decision 7), one raise of `metadata.version` (default 60), and whatever the conformance test of C0.4 finds in its scripts. The details of each change (the proposed sentences, the old and new assertion texts) are in the skill's section of its group report and in its row of the change list of `cross-skill.md`. "Waits on decision" names the decisions of part (a) whose answer changes what is written in that skill's folder; defaults never block. The 31 proposed cases that are not marked "targeted" are left for a later change of each skill (decision 14).

| # | Skill | Group | Status | Changes | Size | Waits on decision |
|---|-------|-------|--------|---------|------|-------------------|
| 1 | `biz-icp-positioning` | 1 | evaluated | **F** `inputs` gains `AGENTS.md`; `updates: [docs/workbench/state.md]`; the state row uses a contract status (default 51). **S** `rank.py` and `check_refs.py` become generated copies; `rank.py` exits 2 on an unreadable file. **B** script-location sentence and command form; stop gates of steps 2, 6 and 8 (what the stop message carries, nothing written before the answer); the reply states nothing without its source; report after the checks; reply template with the check commands and their output; `Method` lines; no extra file under `research/`; planned marks for `biz-business-model` and `biz-gtm`; the stop form of D12; external-content source list. **K** case 1: a decision line in the fixture's state file, a real `market.md` fixture, assertions 3 to 5 made unconditional; e1 a1 and e2 a1 reworded; `grader_files` on cases 1 and 3; case 3 ships the `icp.md` it refers to. | L | 13 |
| 2 | `biz-market-analysis` | 1 | evaluated | **F** `inputs` gains `AGENTS.md`; `updates` state; the planned input stays, declared in the slots table. **S** `rank.py` and `check_refs.py` generated from the shared source; `check_refs.py` checks publisher, dates and tier; `rank.py` exit code. **B** script location; `Method` lines record script name and arguments, never a path, with a label for the ranking command and the fit thresholds; step 14 checks each cited figure against its quote; steps 8 and 12 made one path (a close call is written and asked in the report); order write, check, self-check, report; reply template with evidence; gate wording; planned marks for three skills; artifact status words. **K** e3 a3 split in two; e1 a5 reworded; e2 a1 reworded; `grader_files` on cases 1 and 3. | M | 13 |
| 3 | `brand-guidelines` | 1 | evaluated | **F** `updates` state. **B** step 4 copies each check line from the brand file that records it (with `brand-voice` and `brand-profile`, which gain that line), names and arguments only; script location; reply template; how a person is told from a company; a model line per template section; the stop form of D12; external-content source list. **K** `grader_files`; the `voice.md` and `identity.md` fixtures rewritten from the owners' templates; e1 a2 to a4 replaced by four assertions the baseline fails, a6 kept as a guard; `absent_on_purpose`; the shared brand fixtures (hosts, product name) per decision 11. | M | 11 |
| 4 | `brand-identity` | 1 | evaluated | **F** `updates` state; `outputs` gains the piece files; `requires: [search:web]` with its degraded row (default 58). **S** `contrast.py` replaced by the reconciled shared copy (same interface, flags checked). **B** steps 6 and 8 name where pieces and renders are written; script location; a fenced here-document; the `Production:` line names the script, never a path; step 2 asks whether a design system exists; step 8 for a model that cannot open images; reply template; the stop form of D12; external-content source list. **K** `grader_files` on case 2; an assertion that three renders of the right size exist; the template's palette made neutral if it is a real project's (decision 11). | M | 11 |
| 5 | `brand-name` | 1 | evaluated | **F** `updates` state; `requires: [search:web]` with the offline behaviour written. **S** `handle_check.py`: `--responses <file>` (default 45), docstring aligned with the code. **B** script location; step 2 gate; reply template; plain step numbers; a `Checked` column; artifact status words. **K** a fictional handle in the fixture; case 2 assertions a3, a5 and a6 reworded; `grader_files`; **new case (targeted)**: no network, every row `unknown`, status `limited`. | M | 11, 14 |
| 6 | `brand-profile` | 1 | evaluated | **F** `inputs` gains `AGENTS.md`; `updates` state; `requires: [integration:vcs, search:web]`; a contract status in the state row. **S** `sensitive_topics.py` becomes the source of generated copies in three marketing skills. **B** all eight questions carry `Recommended:`; script location; what to do when the PDF package cannot be installed; reply template with evidence; step 9b renumbered; a `Check` line in the profile template for `brand-guidelines`. **K** `grader_files` on case 1; e1 a3 replaced; e2 a6 reworded; e1 a2 made independent of the day of the run (decision 6); `.example` domains. | M | 6, 11, 13 |
| 7 | `brand-strategy` | 1 | evaluated | **F** `inputs` gains `AGENTS.md`; `updates` state; `requires: [search:web]`. **S** `baselines.py` tells a missing package from a blocked network; tests for both. **B** step 3: an option for the pillars is a set of three, with a template for the gate message; words a label never uses; script location; gate wording; reply template with the baselines command; the stop form of D12. **K** three always-passing content assertions replaced by five; one of two duplicate guards removed; the two state fixtures made consistent with the profile; case 2 expects `not measured`; `grader_files`. The audit names this skill as the most likely to need a second iteration. | M | 11 |
| 8 | `brand-voice` | 1 | evaluated | **F** `inputs` gains `AGENTS.md`; `updates` state; a contract status in the state row. **S** `voice_stats.py` parses its arguments before reading input; it becomes the source of a generated copy in `mkt-social-copy`. **B** step 3 stops, with a template for that message; fenced here-documents and script location; reply template; a `Check` line in the voice template; the status line gains `hypothesis`; the stop form of D12. **K** e2 a3 reworded (a closing hashtag line is allowed, as the script counts it); e1 a1 reworded with `grader_files`; a5 becomes "no voice file is written" and the expected output keeps one path. | S | 11 |
| 9 | `core-agents-md` | 2 | evaluated | **F** `updates: []`. **S** `audit_agents_md.py`: `--fix` never edits the workbench block; a flag given last exits 2 with a message; tests. **B** script location; the leftover about joined commands cut (default 73); the output template quotes each command with its output and lists the files changed; the external-content sentence moves to Inputs in the canonical form; description gains the users' words for the audit mode. **K** case 1 assertions [1] and [5] replaced; case 2 [3] reworded; `AGENTS.md` leaves `grader_files`; the two fixtures made small real projects. | M | 7 |
| 10 | `core-clarify` | 2 | evaluated | **F** `outputs` loses the state file; `updates` state. **S** `clarify.py` checks that Q1 asks "Which one holds" when a contradiction is listed; tests. **B** the Q1 form in the round template; "stress-test" leaves the description (it is `core-critique`'s trigger); a report template; the sentence that a command a document states for its own readers is not an instruction; the reworded line of `references/decision-tree.md` (backlog N7); the gate says a bare "go" accepts nothing. **K** case 2 [1] reworded and two guards added; case 3 [3] quotes the original lines, [2] sharpened; a small documentation folder in the fixture. | M | none |
| 11 | `core-critique` | 2 | evaluated | **F** `updates` state (it registers its critique, default 63). **B** a first step that is the gate, with a question template; a proposal written in the message is the text; a criterion for `blocking`; a `Lens` column in the findings table; reply template; the date from a command; description words. **K** case 4's fixture made a plan that really holds, with the two documents it cites and `grader_files`; case 2's prompt no longer hands over the findings (a prompt change); an assertion that the critique file is written (cases 1, 2, 4); case 2 [4] sharpened, a distribution finding added; case 1 [4] and case 2 [5] reworded; case 4 [2] removed, [4] reworded. | L | none |
| 12 | `core-orchestrator` | 2 | stale | **F** `updates` state. **B** seven rows in `references/routing.md` and a gotcha on the three skills that carry "security" (backlog N6); step 4's fallback never covers a side effect; the gotcha that executed a side effect now stops (default 50); step 5 reads `inputs` and `updates` and names the writer of a missing input from a generated owner table; the environment check without the workbench's doctor, with `unknown`; self-check before the hand-over; the template's `missing` form; `references/requirement-classes.md` becomes a generated copy; one product name out of the body. **K** "names exactly one skill" reworded in cases 1 to 4 and "at most one fallback" added; case 2 [3] reworded; case 1 [5] (language) and case 5 [4] removed; case 6 [1] replaced; case 3 [4] reworded; three `expected_output` texts rewritten; **two new cases (targeted)** that reach a `ready` route. | L | 14 |
| 13 | `core-project-init` | 2 | evaluated | **F** `outputs` loses `AGENTS.md`; `updates: [AGENTS.md]`. **S** `init_project.py`: usage errors on stderr; the slots it registers match the layout contract; a flag and a state line for the `docs/` decision. **B** backlog C1: a fourth question (is `docs/` versioned, per kind, default 84), recorded in the state file and in the section it writes into the project's `AGENTS.md`; the gate says "go" is not an answer; the joined-commands leftover cut; a quality criterion names the sections instead of a workbench file; script path form. **K** a typo in case 4; **new case (targeted)** for the `docs/` question. | M | 14 |
| 14 | `core-research` | 2 | evaluated | **F** `updates` state (it registers its brief, default 63). **S** the script is renamed `check_brief.py`; a limited brief may have no source; a figure without a citation is flagged in every section; diagnostics on stderr; the flag that does nothing is removed; a test file (backlog N9). **B** the capability step becomes step 1; what each section holds when nothing was found; script location; reply template; the public-copy line only when the user says the figure is published; dates from a command; description words. **K** case 3 [5], [4] and [1] reworded; case 1 [6] and [2] reworded; case 4 [1] and [3] replaced; case 2 [1] reworded; `expected_output` says figures from the live web are not fixed. Three of its cases use the live web. | L | 13 |
| 15 | `core-security-audit` | 2 | evaluated | **F** `inputs` and `outputs` declare the records under `docs/security/` (default 61); `updates: []`. **B** two reply templates (vetting, workbench audit); "do not search the disk" for the scan; a table of which steps each mode runs; the history numbers of the first audit made general; description words; script path form. **K** case 1's fixture moves under a parent folder so that the folder the prompt names exists (with its line in `.security-scan-allow`); case 1 [2] and case 2 [1], [2] reworded; case 1 [3], [6] sharpened; case 2 [3] replaced; **new case (targeted)**: the workbench audit on a small fixture workbench with one planted finding. | M | 7, 14 |
| 16 | `core-skill-creator` | 2 | stale | **F** `updates: []`. **B** `SKILL.md` trimmed from about 5,300 to about 4,100 tokens, the detail moved to a new `references/running-evals.md` (backlog N5); the authoring guide names `evals/eval_run.py`, loses its two unused parts and gains the canonical sentences, the command-line conventions and the case rules of phase C; a mode table for improving a skill, with the rule for a security "no" (default 70); step 10 classifies always-passing assertions as language, guard or content; template lines that pair each command with its output; step 2 asks with a recommendation; the version rule; the runner's new options. **K** case 4's fixture moves under `skills/`, brings the scan through `workbench_files` and asserts the Security line (a prompt change); case 2 [2] and [4] reworded, [3] replaced; case 1 [4] (language) removed; case 3 [3] names the expected item, [2] follows default 70; `AGENTS.md` joins `workbench_files`; one fixture's class corrected. Edited last in its lane, after phase B: its cases bring harness files. | L | 7 |
| 17 | `design-brief` | 3 | stale | **F** `updates` state. **S** `lint_brief.py` rejects unknown flags and prints usage on stderr. **B** a stop-reply template and the rule that a recommended answer is never an invented value; when `loaded` mode applies; script location; report lines (files written, registration, longest values, external content); an `Assumptions` section in the brief template; the search for inputs "wherever the project keeps them" removed (default 72). **K** a fictional design tool in the prompt and no product name in the fixtures; the fixtures moved into the project layout in one folder, with a state file, and rewritten if they come from a real project (decision 11); the two lint assertions ask for the report file and the quoted line; the language half of one assertion removed; two content assertions sharpened; a guard added to case 2; `grader_files`. | M | 11, 13 |
| 18 | `design-execute` | 3 | stale | **F** `outputs` gains the results folder and the lint report; `updates` state; `requires: [integration:design-tool, generator:image]`. **S** `lint_result.py`: a flag given last exits 2 (the expected-failure test becomes a normal one), `--report`, a check that every run has its prompt pack, unknown flags; `screenshot.mjs` reports the real image size. **B** a stop-reply template; the lint step and its report line; `design-implementation-validation` marked planned; `references/tools.md` names the provider class, never a path, and loses the dated lessons of one case; a template for `prompt.md`; evidence lines in the report; a self-check as the last step; script location; the description no longer competes with `design-brief`'s. **K** case 1 gets a fixture in which the brief really is the first missing thing, a reworded assertion and no dependency skill (default 29); fictional tool names in two prompts; case 2 [4] asks for the report file; the language assertion removed; an assertion added to case 3; generic fonts and a lint report in the `og-image` fixture. | L | 11, 13 |
| 19 | `design-handoff` | 3 | evaluated | **F** `outputs` gains the export folder; `updates` state. **S** `lint_handoff.py` and `unpack_export.py` reject unknown flags and print usage on stderr. **B** `design-implementation-validation` marked planned twice; question 3 of the stop reply as a literal form; an `Unpack` line in the report; self-check before the reply; "naming the skill that writes it" instead of "routing to"; the joined-commands leftover cut. **K** no product name in the prompt and the fixture; the fixture's owner corrected to `product-feature-spec`; case 1 [1] reworded; three always-passing content assertions replaced, one tightened; a state-row assertion; an instruction planted in the export, declared in `.security-scan-allow`; the fixture's upstream artifacts made template-shaped; the fixtures recorded as edited by hand (default 46). | M | 13 |
| 20 | `design-system` | 3 | evaluated | **F** `inputs` loses the PRD; `updates` state; `requires: [integration:design-tool]`; `side_effects: [create]`. **S** `lint_design_system.py`: a flag given last exits 2, `--report`, contrast rows recomputed from the colour table, unknown flags; `contrast.py` replaced by the reconciled shared copy, with its test at the source. **B** the reply never offers to pick a palette; where `pairs.json` is written; script location; a stop template for missing flows; self-check before the report; one external-content sentence instead of two; description words; a `Lint` line in the document template; what exit 1 of `contrast.py` means. **K** case 1 [5] asks for the report file; case 2 gets a new set of assertions (it measures nothing today); the language assertion removed; a guard and a state-row assertion in case 1. | M | 13 |
| 21 | `design-ux-flows` | 3 | stale | **F** `updates` state. **S** `lint_flows.py` rejects unknown flags and prints usage on stderr. **B** a step that says to write the file; script location; the external-content line in both templates; self-check before the report. **K** an assertion for the "spec pending" path every run takes; a state file and a `Brief` line in the fixture (the same PRD file is `product-roadmap`'s fixture: both copies change together). | S | none |
| 22 | `product-backlog` | 3 | stale | **F** `updates` state; `outputs` gains the lint report; `requires: [integration:issue-tracker]`. **S** `lint_backlog.py`: a flag given last exits 2, `--report`, heading options for translated artifacts (backlog PB11). **B** description gains the fixing and ticket situations; lint steps with a before and an after report; "go" is not an answer to the missing-design question; a rule for a spec that is not ready; a field for `design pending`; self-check before the report; report templates (registration; the external-content sentence moves to Inputs); `Assumptions` and the open-question form in the template. **K** case 3's fixtures become a small real feature in the project layout; three lint assertions ask for the report files and the quoted line; one always-passing content assertion replaced; the `search` fixture made a valid spec. | M | 13 |
| 23 | `product-feature-spec` | 3 | evaluated | **F** `updates` state; `outputs` gains the lint report. **S** `lint_spec.py`: `--report`, unknown flags, heading options (backlog PB11); `check_input.py` takes the request on standard input, never on the command line, and is the one source of the stop reply. **B** description gains the revising situation; lint steps before and after; self-check before the report; script path form; an accepted recommendation is recorded as such (default 75). **K** three lint assertions ask for the report files and the quoted line; two content assertions sharpened; an instruction planted in the brief fixture, with its assertion. | M | 13 |
| 24 | `product-prd` | 3 | evaluated | **F** `updates` state; `outputs` gains the lint report. **S** `lint_prd.py`: the switch `--report` becomes `--table`, `--report <file>` writes the record, `--source` given last exits 2, unknown flags. **B** `biz-validate-idea` marked planned twice; lint steps before and after; self-check before the report; a template for the one-feature stop; an accepted recommendation is recorded as such. **K** three lint assertions ask for the report files and the quoted line; the language assertion removed; one guard extended; the fixture's flow line. | S | 13 |
| 25 | `product-roadmap` | 3 | stale | **F** `updates` state; `outputs` gains the lint report. **S** `lint_roadmap.py`: a flag given last exits 2, `--report`, unknown flags. **B** script location (two of three floor replies copied a path they had not run); the report line; a template for the stop with no PRD; self-check before the report; "go" is not a date; the external-content sentence added (default 59). **K** the lint assertion asks for the report file (it alone holds the floor at 0.917); one always-passing content assertion replaced; the language assertion removed; an assertion that case 2 writes the roadmap without dates; a state file and one spec in the fixture. | S | 13 |
| 26 | `eng-architecture` | 4 | stale | **F** `updates` state; `requires: [search:web]` with the degraded step completed; it owns the ADR collection (decision 8). **S** `check_design.py` prints usage on stderr. **B** script location; the two `Check` lines quote the whole JSON line and never say "same"; a `Files` line from `git status --short`; description gains the checking situation; step 2 gate; `Read` and `Registered` lines in the report. **K** case 1 [1] and [2] and case 3 [3] reworded; the language assertion removed; case 3 [2] sharpened; the `trace-check` and `search-open` fixtures gain the files they cite; the fixtures' flow line; **new case (targeted)**: no web, versions from the manifest, every framework call listed as an assumption. One of its cases uses the live web. | M | 8, 14 |
| 27 | `eng-code-review` | 4 | evaluated | **F** `updates: []`; `requires: [integration:vcs]`. **S** `change_scope.py`: a flag given last or a non-integer exits 2, usage on stderr, more tests, a test that finds the script from its own folder; `redact.py` becomes a generated copy with a neutral docstring and its own test. **B** `git apply` instead of `patch`; the scratch copy made in one chained command, here and in the bug-fix checklist; a "Stop rules" section above the procedure (no intent, no review; a request to approve is not a verdict; the tree under review is never edited); templates that quote each check's output and the working tree; script location; the isolated-reviewer branch in one line; a `Reviewed:` line; description trimmed to make room for the users' words. **K** case 1 [5] reworded with `grader_files` and a `.gitignore` in three fixtures; case 4 [2] reworded; case 3's second assertion replaced by three, its third sharpened; case 2 [2] replaced, [5] reworded; case 1 [1] reworded; the `secret` fixture gets a fictional key name and an `.example` host; the language assertion removed. | L | 7 |
| 28 | `eng-codebase-map` | 4 | evaluated | **F** `updates` state. **S** `map_codebase.py`: a flag given last or a non-integer exits 2 (the expected-failure test becomes a normal one), usage on stderr. **B** step 9 runs `git status` and the report quotes it and the measurement command; step 7 says what a disagreement with the specification states, with a template line; description gains "map" and the comparison situation; the monorepo gate says "go" is not an answer. **K** case 1 [5] and [2] reworded, [3] sharpened; the language assertion removed; case 2 [2] sharpened; case 3 [2] reworded; the `monorepo` fixture decided by a more telling rule; the `small-app` fixtures gain the configuration that defines their alias, and the numbers of assertion 1 are computed again. | M | none |
| 29 | `eng-docs` | 4 | evaluated | **F** `outputs` loses the plan; `updates` plan. **B** `Claims run` and `Working tree` lines in the template and a reply template; the first gate gets a recommended answer; the plan is created with its header when missing; a neutral example; two gotchas rewritten as lessons (decision 11); `ops-release` marked planned. **K** `grader_files` on both cases; three "is unchanged" assertions reworded; the language assertion removed; two always-passing assertions merged and one added for the case the change does not cover; an assertion for the offer in case 2; prompts say "the invoices project"; the fixture's runtime line and the release tool's name. | M | none |
| 30 | `eng-impact-analysis` | 4 | evaluated | **F** `outputs` loses the plan; `updates` plan (it creates the file with the owner's header when missing). **B** a rule for `<task>` when no task exists (twelve runs produced five file names); the plan template quotes the baseline line and lists what was read; a reply template; stop rule 1 gets a recommended answer; four gotchas rewritten with invented numbers (decision 11). **K** case 2 rebuilt (it scores 1.0 in every variant today); two language assertions removed; case 1 [7] split, [2] and [6] replaced or folded; case 3 [1] and [2] reworded; `grader_files` on the three cases; the fixture's runtime line; prompts. Its baseline will fall: the cases get honest. | M | 8 |
| 31 | `eng-implement` | 4 | evaluated | **F** `outputs` loses the backlog; `updates` backlog, the plan (the "Change" section, default 49) and ADRs; `inputs` gains ADRs and specs. **S** `task.py`: a flag given last or a missing backlog exits 2 (the expected-failure test becomes a normal one); `--status` prints one line with the working-tree state at that moment; usage on stderr. **B** `Task` and `Started` lines that quote the script; a template for the mode without a task id; the status rule when the check fails (default 79); step 3 gate; a folder that was untracked before the work is named once as pre-existing; description gains the hand-off from a review; two gotchas without tool commands. **K** case 1 [1] and case 2 [1] reworded (eight of nine with-skill failures); case 2 [2] replaced and a question assertion added; guards reworded in cases 2 and 3; a content assertion for case 3; case 1 [5] reworded; the fixtures' flow line. | L | none |
| 32 | `eng-integration-tests` | 4 | evaluated | **F** `outputs` loses the plan; `updates` plan; the unnamed `AGENTS.md` input gets its Inputs row. **B** the plan template quotes each run's count lines and the working tree, and a reply template; the scratch copy made in one chained command; the three Inputs gates get a recommended answer; a criterion for a library with no build or server; two gotchas rewritten as lessons; the external-content sentence added (default 59); the plan's "Change" section is now written by `eng-implement`. **K** case 1 [6] and case 2 [3] reworded with `grader_files` (the one assertion between the floor's 0.86 and 1.0); the language assertion removed; assertions 3 to 5 sharpened; case 1 [2] replaced; case 2 [2] reworded; the fixture's README and runtime line; prompts. | M | none |
| 33 | `eng-refactor` | 5 | evaluated | **F** `inputs` loses the architecture document; `outputs` loses the plan; `updates` plan. **B** evidence lines before and after and the files changed; `git status --short` instead of a diff summary; a reply template; step 1's question names the recommended target; the self-check lists each number with its command; one gotcha without the numbers of a case (decision 11); the external-content sentence added. **K** case 2's assertions replaced (it measures nothing today); the language assertion removed; case 1 [1], [2] and case 3 [2] reworded; case 3's expected output aligned with the stop rule; `grader_files`; the fixture's runtime line; prompts. | M | none |
| 34 | `eng-root-cause` | 5 | stale | **F** it owns the plan (decision 8): `outputs` keeps it, `updates: []`. **B** step 5: a quoted rule is fetched, or written as an assumption quoted from memory; the grade when a supported runtime is not installed (default 80); `not run` wording; reply template lines for the reproduction file and the files left; `references/evidence.md` says when it is loaded. **K** two language assertions removed; two always-passing content assertions removed and one replaced; three assertions reworded (paths that do not exist, an order the grader cannot see); `grader_files`; the fixture's runtime line (the same input gave two grades); prompts. | M | 7, 8 |
| 35 | `eng-security-review` | 5 | stale | **F** `updates` state. **S** a test for the usage errors of `triage_alerts.py`. **B** step 7 becomes the gate's own question, with a template for the reply that asks; for a shipped package with a fix the reply recommends the update and names no dismissal reason; a payload approved for later sits in the durable payload folder; script path form; a `Grouping` evidence line; "go" answers neither question; one tool name out of an example; the alert product named once; the complete action list in the external-content sentence; the version text. **K** case 2 [3] says what counts as a payload; case 1 [1] and case 3 [1] replaced; case 4 [1] and [2] merged and a payload assertion added; three self-report guards reworded; an `.example` host in the fixture; case 4's fixture changes a comment's words instead of adding a row; `grader_files`. | M | none |
| 36 | `eng-tradeoffs` | 5 | stale | **F** `outputs: []`; `updates` plan and ADRs, with the sentence that an ADR follows `eng-architecture`'s template. **B** the external-content line goes above the closing question; rule 3 starts "Once the criteria exist" (default 81); a reply template; script path form; "go" does not choose between two options. **K** the fixture's runtime line (today an ADR can never be accepted, for a reason the case does not test); the language assertion removed; two guards reworded with their evidence; **new case (targeted)**: a plan with no "Impact" section. | M | 8, 14 |
| 37 | `eng-unit-tests` | 5 | evaluated | **F** `outputs` loses the plan; `updates` plan. **B** description gains the words for tests of code that exists; a "Stop rules" section with the two-readings rule and its criteria (case 3 fails in every strong run); the plan header written inline; a reply template and the self-check before it; `not run` wording; the external-content sentence added; the Inputs gate gets a recommendation. **K** case 2 gains the assertion that no test file is written and a corrected expected output; two language assertions removed (without the skill fix the strong score falls to 0.78); case 3's two assertions merged and one added (default 42); case 1 [4] replaced; case 2 [1] reworded; the fixture's runtime line and the reproduction script it names. | M | none |
| 38 | `flow-fix-bug` | 5 | evaluated | **F** `inputs` gains the plan; `outputs: []`; `updates` state. **B** the external-content line sits above the checkpoint question, which is always the last line (seven failed assertions); a format for the `Current flow` and `Current phase` lines; a resume line in the checkpoint template; the state file created through `core-project-init` (default 65); the direct push removed (default 50); a "Quality criteria" section and a self-check step; `flow-build-feature` marked planned; four gotchas rewritten as lessons; a vague report writes nothing; a phase is approved in its Artifacts row; "go" does not answer a choice; the autonomy question gets a recommendation; the `docs/` decision respected when it delivers (backlog C1). **K** the `invoices-phase2` state fixture in the new format; the Approvals table's hash column; assertions added to case 3; `grader_files`; the fixtures' runtime line and reproduction script; **two new cases (targeted)**: no state file; resuming at phase 3 with two phases skipped. | L | 14 |
| 39 | `ops-branch-sync` | 5 | evaluated | **F** `outputs: []`; `updates` state. **S** `sync-status.sh`: a flag given last exits 2 with a message; the base name is validated; tests. **B** `integration:vcs` named in the body with what happens without it; a self-check step; three gotchas rewritten as lessons; the approval row reads `pending-execution` until the push succeeds; stop rule 3 recommends a version or says it cannot; evidence lines in the output template; script path form; the `docs/` decision respected when it commits (backlog C1). **K** case 1 [5] and its expected output follow decision 12; six always-passing assertions merged into two guards, one removed; two self-report assertions reworded; `grader_files`; **new case (targeted)**: a sync with no conflict, pushed on the recorded approval. | M | 12, 14 |
| 40 | `ops-ci-pipeline` | 5 | evaluated | **F** `inputs` loses the architecture document; `outputs: []`; `updates` state and plan; `side_effects: [push, deploy]`. **B** "pinned" means a full version with a source, never from memory; a rule for tools that cannot be installed (`not run`, no push asked); `integration:vcs` named with what happens without it; `ops-release` and `ops-infra` marked planned; the plan created with its header when missing; actions pinned to commits (default 82); a reply template that starts with the credential block; what "go" accepts. **K** the fixtures gain an exact runtime version, the deploy tool's version, a lockfile and an `.example` domain; case 1 [3] reworded with `grader_files`; case 1 [1] removed; case 2 [3] and case 3 [1] replaced; an assertion on the plan's "Pipeline" section. | M | none |
| 41 | `ops-pull-request` | 5 | stale | **F** `outputs: []`; `updates` state; `side_effects: [push, create]` covers its replies to review comments (default 54). **S** the header comment of `pr-context.sh`; tests for its usage errors. **B** `integration:vcs` named in steps 4 and 6 with what happens without it; a self-check step; `ops-qa-handover` marked planned; one gotcha without the date of a case; how to tell that recorded runs were made on the branch's head; the external-content line above the question; a template for the reply that asks for approval; script path form; the `docs/` decision respected, and no pull request opened only to record workflow data (backlog C1). **K** the lint script of two fixtures made one that can run, with the setup commit and the plan line; two self-report assertions reworded; `grader_files`; an `.example` host for the repository; **new case (targeted)**: a local bare remote and a recorded approval, to measure what happens after the yes. | M | 14 |
| 42 | `ops-repo-baseline` | 5 | evaluated | **F** `updates` state (it registers its baseline, default 63); `requires: [search:web]` (default 55). **S** `secret_scan.py`'s message for `--root` without a value; `redact.py` becomes a generated copy with a neutral docstring; tests. **B** the lines that name this repository, a date and a count leave the skill and its reference (decision 11); step 4's wording; the host-settings template grouped under its three headings; evidence lines in the chat template; what "go" accepts; one code host stated once (default 83); the reworded line of `references/host-settings.md` (backlog N7); the version text. **K** case 2 [1] and [3] replaced; case 1 [6] and case 2 [4] reworded. | M | none |
| 43 | `mkt-content-plan` | 6 | evaluated | **F** `inputs` gains `AGENTS.md`; `updates` state; the planned input stays, declared in the slots table. **S** `slots.py`: row numbers continue across weeks, days and times sorted together, clearer messages; a generated copy of `sensitive_topics.py` replaces the call into another skill's folder. **B** script location; `mkt-launch-plan` marked planned; a reply template; the gate says "go" names no value; the stop form of D12; external-content source list; artifact status words. **K** fixture dates and the prompt per decision 6 (case 1 stops working on 2026-10-12); an assertion on row numbers; two always-passing content assertions replaced; `grader_files`; `.example` hosts and the schedule of the shared fixtures (decision 11); the dependency skill leaves the cases once the copy is vendored. | M | 6, 11 |
| 44 | `mkt-engage` | 6 | stale | **F** `inputs` gains `docs/workbench/runtime.json` (a `user` slot); `outputs` loses the state file; `updates` state; `mailbox` leaves `requires` (default 57). **S** `parse_notification.py`: `--help`, `--platform`, an exact host check, a test file (backlog N9); `policy_gate.py`: a missing reply file exits 2, one link pattern; a generated copy of `sensitive_topics.py`. **B** the `decide` command passes `--sources-file`; what the draft for a fact without a source contains (the one floor failure); the pasted comment link becomes the default path and the mailbox one line; script location; templates for the report and the log entry; a reply that waits is kept in the durable payload folder; the workbench-root rule (default 69); the runtime contract named as a workbench file the model need not read; the stop form of D12; description words. **K** case 2 rebuilt (it scores 1.0 in every variant); case 1's trivial assertions removed or replaced; case 3's two overlapping assertions merged; `.example` hosts; **new case (targeted)**: procedure B on a pasted comment, which no case exercises. If a real notification e-mail arrives before this batch, the parser (backlog PB6) joins it. | M | 11, 14 |
| 45 | `mkt-messaging` | 6 | stale | **F** `updates` state; the specs input stays and gets its Inputs row (default 66). **S** `lint_messaging.py`: `--file` given last exits 2; the flag that only indents is documented or removed. **B** step 3: a number someone else reported keeps its source's method and label and is never a headline (the one floor failure); `mkt-launch-plan` marked planned; `mkt-content`, which exists nowhere, becomes `mkt-social-copy`; script location and the template line; which questions stop a section. **K** the fixture rewritten as a small fictional product, with no AI product named (decision 11); case 2 rebuilt (it scores 1.0 in every variant) and its language assertion removed; case 1 [3] reworded; an assertion on the document's structure; `grader_files`; **new case (targeted)**: no PRD, the stop the last text change introduced. | L | 11, 14 |
| 46 | `mkt-publish` | 6 | stale | **F** `outputs: []`; `updates` state and calendar. **S** `payload.py`: `--publisher <path>` instead of a path it builds, `--platform` required, a manifest that is not JSON reported, a refused ignore check (default 68; `scripts/runtime_vote.py` follows the renamed flag in the same pull request); tests. **B** `<platform>` defined; script location; a template for the reply of the gate and for the two stops; gotchas reworded as the provider's facts; what the scheduler needs, from its own check; `payload.py verify` instead of a hand-made hash; where the check result of a post is read; one way to run providers; description words; the stop form of D12. **K** prompts name the posts instead of "next week" and fixture dates move with the token dates (decision 6: the strong tier's 0.88 is one run that met this); week 1 of the calendar made consistent; `grader_files`; one content assertion replaced; the stand-in providers renamed and strict about the platform; `.example` hosts; **two new cases (targeted)**: scheduling after a recorded approval, and no provider for the class. | L | 6, 11, 14 |
| 47 | `mkt-social-copy` | 6 | evaluated | **F** `outputs` loses the calendar; `updates` calendar; the messaging input stays and gets its Inputs row; it owns the post files (decision 8). **S** `check_post.py`: one link pattern and `--no-body-links`; generated copies of `voice_stats.py` and `sensitive_topics.py`; it becomes the source of the copy in `mkt-vote-round`; a test file (backlog N9). **B** script location; a reply template; step 1 takes the earliest open slot and says so; step 7's wording; the description names no network; artifact status words; the stop form of D12. **K** `grader_files` on both cases; case 2's prompt names the post and its conditional assertion becomes two that the baseline fails; two content assertions sharpened; `.example` hosts; the dependency skills leave the cases once the copies are vendored. | M | 8, 11 |
| 48 | `mkt-vote-round` | 6 | evaluated | **F** `outputs: []`; `updates` post files and calendar. **S** `vote_update.py` takes `--platform`; a generated copy of `check_post.py`. **B** script location; step 2 gives the command that resolves the code-host provider by class; step 5's rule on numbers from other notes and on computed numbers (default 44), repeated for the runtime mode; step 8 sets the calendar row and has a reply template; step 4 gets a recommendation; the sentence that a post file follows `mkt-social-copy`'s template; the vote data files described as a contract (default 67). **K** a fictional author and title in three fixtures and the prompts; case 1 [3] follows default 44; case 3 [1] and [4] reworded; ten always-passing assertions removed or replaced; `grader_files` on case 3; `.example` hosts. | M | 8, 11 |

Counts: 4 S, 33 M and 11 L. 15 skills are `stale` today and 33 `evaluated`; after phase C all 48 are `stale`. 36 rows wait on at least one decision of part (a): decision 11 shapes 14 rows, decisions 13 and 14 shape 12 each, decision 8 six, decision 7 five, decision 6 three, decision 12 one. 12 rows wait on none. The 15 targeted new cases are in 12 skills.

- Order: C0.1 to C0.7 first. Then six lanes, one per audit group, each in its own working tree, since their skill folders do not overlap; a lane that changes a shared fixture family carries the copies of the other group in the same pull request (C0.8). `core-skill-creator` is edited last in its lane and after phase B is frozen, because its cases bring harness files into the run and its guide describes the runner. Within a lane, the skills already `stale` and the L rows go first.
- Parallel: the six lanes with each other and with phase B. Merges go one at a time; each rebases, runs `scripts/sync_copies.py --check`, regenerates the inventory's status block and passes `validate.py`.
- Size: C0 is 4 M and 4 S; the skills are 4 S, 33 M and 11 L.
- Depends on: decisions 6, 7, 8, 11, 12, 13 and 14, and decision 9 before the phase closes; A5 (the validator's list); for `core-skill-creator`, phase B.
- Exit: every must-fix item of the six group reports is done or is recorded in the pull request as not done with a reason; the cross-skill change list is applied; the contract rules of C0.1 are errors and pass; the conformance test and the identity test pass on every script; `eval_run.py --check-cases` passes for the 48 skills; no pull request is left that lacks its before-and-after list of case changes. No skill is measured in this phase.

### Phase D. Dry run

Goal: catch a mistake in the harness or in a convention while it costs a pilot, not a round.

| # | Step | What it checks | Size |
|---|------|----------------|------|
| D1 | Static checks on `main` with phases B and C merged: `validate.py` with zero errors (the only warnings left are the 48 stale skills); the fingerprint accepted; `sync_copies.py --check`; the conformance test; every test folder `scripts/test_dirs.py` lists | nothing drifted while the lanes merged | S |
| D2 | The container job run by hand on the measuring machine as well as in CI: the preflight of all cases with their setup, both adapters with stub runners, the grading path with a stub grader | every case builds in the image that will measure it, with no model call | S |
| D3 | The pilot: six skills, every case, four variants, 2 runs each, with two grading passes. `design-execute` (scripts and a browser), `biz-market-analysis` (the live web and the search limit), `ops-pull-request` (git state, the host's command-line tool, a bare remote), `flow-fix-bug` (dependency skills, the ledger format), `mkt-publish` (dates, stand-in providers, the durable payload folder), `core-skill-creator` (repository files brought into the run). About 24 cases, about 190 runs, about two and a half hours of compute; no record is written, since 2 is below the configured runs | the harness and the conventions on real model output | M |
| D4 | Reading the pilot: twenty gradings read by hand against the template, at least three per pilot skill and half of them from the floor tier; the facts block compared with the case folder; every transcript and reply searched for a credential value and for a mount path; `invoked` read for every with-skill run; the grader disagreement rate computed (decision 2) | the instrument, before it is trusted | M |

**What stops the round.** Any one of these means the cause is fixed inside version 5 and the pilot is run again on the skills it touched: a verdict that contradicts a harness fact, or more than one wrong verdict in the twenty read by hand; a with-skill run with `invoked` false because the skill's description did not reach the model; a credential value or a mount path in any output; an infrastructure failure of a kind the retries do not absorb, or more than 2% of runs failing on infrastructure; a floor run that cannot write its scratch files; a pilot skill under 0.8 with the skill for a cause that is the harness or a convention of phase C and not that skill. A pilot skill that fails for its own reason is repaired as in phase E and does not stop the round.

- Parallel: D1 and D2 together; D3 after both; D4 after D3.
- Size: 2 S and 2 M.
- Depends on: phases B and C merged; phase A's CI repair.
- Exit: D1 and D2 pass, and a pilot with none of the stop conditions. The fingerprint at that commit is the one the round runs under.

### Phase E. The final round

Goal: 48 records under measurement version 5, on content that does not change afterwards.

- **Precondition:** phase D's exit; the decisions of part (a) all answered; the strong model's account with room for the round (the first round hit its limit three times in two days).
- **Volume**, with the recommended answers (5 runs, 156 cases, two grading passes): 156 cases, 4 variants and 5 runs are 3,120 model runs and at least 6,240 gradings; about 34 hours of compute for the runs and about 10 for the gradings. With one grading pass, about 39 hours in all. With 3 runs and no new case it would be 1,692 runs and 21 hours. Notional cost as the strong runner reports it: about 360 USD with one grading pass, about 480 to 510 with two; the floor tier reports none.
- **Concurrency:** ten skills at a time, each as its own runner process; the total of concurrent runs and the number of concurrent web runs per tier (2 on the floor tier) are held by the runner's shared lock (B5), not by the operator. The 9 web cases, in 5 skills, are spread over the batches.
- **Elapsed time:** the compute fits in one long day at that concurrency; the account limit is what spreads it. Plan for 2 to 4 days.

Batches, ten skills each, the last of eight:

| Batch | Skills | Why this order |
|-------|--------|----------------|
| 1 | `brand-strategy`, `eng-unit-tests`, `core-critique`, `design-execute`, `eng-code-review`, `eng-implement`, `mkt-publish`, `brand-voice`, `flow-fix-bug`, `core-research` | the skills the audit found closest to the threshold or most changed: their repair loops start first |
| 2 | `biz-icp-positioning`, `brand-guidelines`, `brand-identity`, `brand-profile`, `core-agents-md`, `core-clarify`, `core-orchestrator`, `core-project-init`, `core-security-audit`, `design-brief` | |
| 3 | `biz-market-analysis`, `design-handoff`, `design-system`, `design-ux-flows`, `product-backlog`, `product-feature-spec`, `product-prd`, `product-roadmap`, `eng-architecture`, `eng-codebase-map` | |
| 4 | `brand-name`, `eng-docs`, `eng-impact-analysis`, `eng-integration-tests`, `eng-refactor`, `eng-root-cause`, `eng-security-review`, `eng-tradeoffs`, `ops-branch-sync`, `ops-ci-pipeline` | |
| 5 | `ops-pull-request`, `ops-repo-baseline`, `mkt-content-plan`, `mkt-engage`, `mkt-messaging`, `mkt-social-copy`, `mkt-vote-round`, `core-skill-creator` | `core-skill-creator` last: its record names the hash of the harness files its cases bring |

Each batch ends with one pull request that carries the records of the skills that passed and the regenerated status table. A batch does not wait for the repairs of the one before it.

**A skill that fails.** The round must end, so the loop has a limit:

1. An incomplete iteration (infrastructure) is resumed with `--resume`, never scored, and does not count as an attempt.
2. A complete iteration that fails the gate is read: the failed gradings, the replies, and for the floor tier the transcript. Each failure is classified as a skill defect, a case defect, or the instrument.
3. The instrument (the harness, the template, the image) is never changed inside the loop. If the reading shows a defect there, the round stops, the cause is fixed, the version and fingerprint are raised, and every record already made under version 5 is measured again. This is what phases B and D exist to prevent.
4. A skill defect is fixed in the skill; a case defect is fixed in the case under the rule for case changes, listed before and after. The skill is then measured again in full, alone. That is one repair.
5. A skill whose failing score is within two standard errors of the threshold, and whose failed gradings show neither kind of defect, is measured once more unchanged; the record carries the number of attempts. A second failure is treated as a defect to find.
6. **At most two repairs per skill**, three complete measurements in all. A skill that still fails keeps its failing record, reads `draft`, gets a backlog item that names what was tried, and leaves the round. The round then closes with fewer than 48 `evaluated`, stated in the decisions log; it is not held open.
7. A passing record is never measured again to improve it. `marginal` is information, not a reason to rerun.

**The freeze that follows.**

- The round's last pull request records, in `docs/decisions.md`, the commit, the fingerprint, the image digest and the counts, and ticks the backlog item "Final measurement round".
- `validate.py --strict` becomes the CI default: a stale or draft skill fails the `validate` check. From then on a pull request that changes a skill folder must carry that skill's new record, measured alone under the same version.
- The fingerprint check of B10 fails any change to the grading template, the image definition, an eval adapter, the measurement constants or the shared references, until the version is raised (which stales all 48) or the change is shown to measure the same and is recorded as such.
- `evals/`, the eval adapters and `shared/` are listed in `.github/CODEOWNERS`, so that such a change is seen by the owner of the measurement.

- Parallel: the five batches follow one another without waiting for repairs; repairs run beside later batches; phase F items that touch no frozen file can go on in another working tree.
- Size: L (days, most of them waiting on runs).
- Depends on: phase D.
- Exit: 48 skills `evaluated` (or the number reached and the listed `draft` skills, each with its backlog item), `validate.py --strict` green on `main`, the decisions entry written.

### Phase F. After the round, independent of skills

Goal: the work that never needed to wait on a measurement and must not disturb one. Nothing here changes a skill folder or a frozen file; where an item would, it says so and what it costs.

| Lane | Items, in order | Specified in | Size | Note |
|------|-----------------|--------------|------|------|
| F1. Backlog | Move every open item to the repository's issues: a dry run that prints each issue for one approval, the private-term check on each body, labels by section, `docs/backlog.md` cut down to an index edited in the pull request that opens or closes an issue; no generated index (default 86) | backlog "T14: is it still worth doing, and when?", Q7 | M | first thing after the round; the two ids cited from inside skill folders (PB6, S6) stay resolvable |
| F2. Runtime | Decision 10 written into `docs/decisions.md` → the runtime contract and `runtime.py` name no skill, the per-agent parts sit behind a handler (R1), with containment of a runtime agent beyond its tool list (N15) → the store's tables, the approval inbox, triggers and observability made generic (R2, R5, R6, R7) → the Linux scheduler rehearsed on a real host (N12) and the API adapter finished: an `install.sh`, a `run-prompt.sh`, a check with a real key, and `AGENTS.md` "Adding an adapter" corrected (N11, PB8) → the weekly "latest posts" routine (PB16) → department agents (R3) → messages between agents (R4) → the local web app with the chat view (R8, R11) → scenario evals in `evals/`, which write no skill record (R9) | backlog, tables "Agent runtime" and "Brand skills", N11, N12, N15; review of 2026-10-01, findings C1 to C5 | L | waits on decision 10. PB16 may change `mkt-vote-round`'s script: that skill is then measured alone. A `run-prompt.sh` for the API adapter is a new adapter file, outside the fingerprint of the two eval adapters |
| F3. Installers | Both installers install the stripped copy (no `evals/`, no `scripts/tests/`) with `shared/` beside it and, with `--copy`, what a skill needs of `providers/`; they print or set `WORKBENCH_ROOT`; they report the skill-listing size of the pack and, when the person agrees, write the budget (decision 9); a `doctor.py` check of the listing; the install confirmed once on a real installation | harness §9; backlog T18, N13; defaults 31 | M | reuses the runner's staging function without changing it |
| F4. Routing | A routing measurement per pack: the case prompts run with the whole pack installed, reading the `invoked` field; it writes no record and gates nothing | backlog T7; harness §9 (last paragraph) | L | after F3. A description it leads to change stales that one skill, which is measured alone |
| F5. Store | Reproduce the concurrent `init` failure on Linux with stderr kept; confirm or replace the hypothesis | backlog T15 | M | any time; the two CI jobs give evidence at each push |
| F6. Small tooling | A provider verb for repository settings in the code-host provider, with an admin-scoped secret named in the secrets contract (it prepares S17); the floor tier's usage read from the provider when the runner cannot print it | backlog S17; harness §12 | M | |
| F7. Deferred | The local-model tier: a route from the container to a model on the person's machine, one model, a threshold of its own, published and not gating. The credential sidecar that keeps the provider key out of the run | backlog N14, T12; harness E | L | deferred by the maintainer. Both change the executor or an adapter, which the freeze covers: each is built only together with a planned new round, never between rounds |

- Parallel: the lanes with each other and with phase G. Inside F2 the order is the one written.
- Size: 3 M and 2 L outside the runtime; the runtime lane is L several times over and gets its own plan when decision 10 is taken.
- Depends on: the round recorded (F1, F3, F4); decision 10 (F2); nothing (F5, F6).
- Exit: per lane. F1: no open item lives only in `docs/backlog.md`. F3: after `install.sh --pack default` every installed skill's description reaches the model on each supported harness, or the installer says which do not.

### Phase G. New skills and flows, each measured when built

Goal: what the inventory plans and nobody has built, in the order that costs least. Each is written from the templates phase C updated, against a real task, and measured alone under the frozen measurement; none makes another skill stale, with one exception named below.

| Order | What | Depends on | Specified in |
|-------|------|------------|--------------|
| 1 | `flow-brand` (backlog PB14): its six phases are built and evaluated, so it is the cheapest flow | the round | backlog PB14 |
| 2 | `flow-build-feature`, then `flow-improve-code` and `flow-new-project`: their engineering phases are all built | the round | backlog N16 |
| 3 | `ops-release`, which `eng-docs` already names as the owner of release notes | a real release to write it against | backlog NS1 |
| 4 | `mkt-launch-plan`, then `flow-launch` after `mkt-landing-page` and `mkt-analytics` | a real launch | backlog NS2, NS3 |
| 5 | `biz-validate-idea`, the writer of the other planned slot | a real idea to validate | backlog N16 |
| 6 | `ops-repo-baseline`, next version: it applies the host settings itself and can use an external secret scanner (S17 with S18, so that it is measured once for both) | F6; the real run of S11 | backlog S17, S18 |
| 7 | `eng-security-review`, next version, beyond dependency alerts | findings met on a real project, rewritten with fictional names | backlog S14 |
| 8 | `design-implementation-validation`, the other planned flows, the `explorer` agent, `design-system`'s next version | as projects ask | backlog N16 |

The exception: when a planned skill is built, its row in `core-orchestrator`'s routing table loses the planned mark and its slot leaves the table of `contracts/project-layout.md`. The routing table is inside the orchestrator's folder, so the orchestrator goes `stale` and is measured alone. Build the flows of steps 1 and 2 as one batch so that it is measured once for the four.

- Parallel: with phase F; steps 1 and 2 with each other.
- Size: M to L per skill or flow.
- Exit: each new skill or flow reads `evaluated`, and `core-orchestrator` reads `evaluated` after each batch.

### Phase H. Waiting on the maintainer or on the world

Nothing to do in the repository until the event. When it happens, the item returns to the phase named.

| Waiting on | Items | Then |
|------------|-------|------|
| The decisions of part (a) | decisions 1 to 5 before phase B; 6 to 8 and 11 to 14 before phase C; 9 before phase C closes; 10 before lane F2 | the phase starts |
| The maintainer's own actions | rotating the floor key and creating a low-limit key; scrubbing stored transcripts; the three questions of fact of decision 11; the required checks in the ruleset; choosing where the image is stored | phases A and B |
| A real run on a project that handles many credentials | S11: the lessons of `ops-repo-baseline`, written without the project's name | phase G, step 6 |
| Findings met on a real project | S14 | phase G, step 7 |
| A password manager in use | S16: a secrets backend behind the resolver | phase F, as a provider item |
| A real notification e-mail | PB5 and PB6: the parser of `mkt-engage`; PB7: the e-mail trigger of the social agent | if before phase C closes, the parser joins `mkt-engage`'s row; after the round, that skill is measured alone |
| A real week of the weekly vote | PB15: the run log stays in the project | lane F2 |
| The first case of a department agent | R10: the provider classes it needs, asked, not assumed | lane F2 |
| The operator's choice of a host | PB8, N12 | lane F2 |
| The next failure of the store test in CI | T15 | lane F5 |
| Projects that scheduled jobs before the ledgers moved | N17: jobs are scheduled again after upgrading; an action in each project, said in the release note | nothing here |
| A year from now | the dated fixtures of decision 6 expire | a backlog item with the date, opened in phase C |

## Backlog map

Every item of `docs/backlog.md`, the review's decisions D7 to D14, the open pieces of the previous plan (PL) and the work no item covered (N1 to N19). "Verdict" is the audit's (backlog report, "Items"). "Where" is the phase and item of this plan.

| Id | Title, short | Verdict | Keep, drop, rewrite or merge | Where |
|----|--------------|---------|------------------------------|-------|
| S1 | Deterministic scan | done | archive | A2 |
| S2 | Pre-commit hook | done | archive | A2 |
| S3 | Security checklist and step 7 | done | archive; fix the old path in its text | A2 |
| S4 | Untrusted-content rule | done | archive | A2 |
| S5 | Least privilege for agents and evals | done | archive; its eval half describes a mechanism that no longer exists | A2 |
| S6 | Repository settings | done | archive | A2 |
| S7 | `core-security-audit` | done | archive | A2 |
| S8 | `eng-security-review` 0.1 | done | archive; fix the old path | A2 |
| S9 | Prompt-injection evals | done | archive | A2 |
| S10 | Fix the audit of 2026-09-27 | done | archive | A2 |
| S11 | `ops-repo-baseline` | partly | rewrite: the skill is built; only the real run is open | A2, then H |
| S12 | Approvals bind the payload | done | archive | A2 |
| S13 | Secrets behind one interface | done | archive; one line about one account removed | A2, A3 |
| S14 | `eng-security-review` beyond alerts | not done | keep; one phrase rewritten for principle 8 | H, then G step 7 |
| S15 | Optional copy of the approved payload | not done | drop (default 85) | A2 |
| S16 | A password manager as a secrets backend | not done | keep | H |
| S17 | `ops-repo-baseline` applies host settings | not done | keep | F6, then G step 6 |
| S18 | External secret scanners | not done | keep, built with S17 | G step 6 |
| S19 | Confine the floor model's runs | done, unticked | tick, archive | A2 |
| T1 | The runner reports whether the skill was invoked | not done | keep; path rewritten | B8 |
| T2 | Add files by name | done, unticked | tick, archive | A2 |
| T3 | Eval regression on changed skills | done | archive | A2 |
| T4 | The runner names a harness folder | done | archive | A2 |
| T5 | Tighter eval isolation | done | archive; its promise for runtime agents becomes N15 | A2 |
| T6 | Optional container runner | done (superseded) | archive | A2 |
| T7 | Trigger tests for descriptions | not done | rewrite as a routing measurement per pack | F4 |
| T8 | Parallel eval runs | done | archive | A2 |
| T9 | The grader reads whole artifacts | done | archive | A2 |
| T10 | `lint_brief.py` separators | done | archive | A2 |
| T11 | Every skill passes the gate on record | partly (done at the first round; 15 stale today) | keep ticked as the first round; new item "Final measurement round" | A2; phase E |
| T12 | The floor model on a person's machine | done by its "Done when", unticked | tick; the local tier becomes its own item | A2; F7 |
| T13 | The floor provider is watched | done | archive | A2 |
| T14 | Open items move to the issue tracker | not done | keep, smaller; its first step is the archive | A2 (step 1); F1 |
| T15 | Concurrent `init` of the store | partly | keep | F5, H |
| T16 | Evals in one fixed environment | done, unticked | tick, archive | A2 |
| T17 | Evals can allow web search | done | archive | A2 |
| T18 | An installed skill keeps its description | partly | keep | A8 (measure), decision 9, F3 |
| T19 | Assertions that pass in every run | not done | keep | phase C, the **K** of each row; default 33 |
| T20 | Flows named as planned; drift | done | archive; its "Remains" list is N6, N7 and PL-validation | A2 |
| R1 | Runtime contract | partly | rewrite with a "Done when" that can be ticked | F2 |
| R2 | Storage interface | partly | rewrite | F2 |
| R3 | Department agents | not done | keep; the case lives in its project | F2 |
| R4 | Messages between agents | not done | keep | F2 |
| R5 | Approval inbox | partly | rewrite | F2 |
| R6 | Scheduler and triggers | partly | rewrite | F2 |
| R7 | Observability | partly | rewrite | F2 |
| R8 | Local web app | not done | keep; takes R11's screen | F2 |
| R9 | Scenario evals | not done | keep; lives in `evals/`, writes no skill record | F2 |
| R10 | Integrations the first case needs | partly | rewrite as a generic rule | H, then F2 |
| R11 | A chat interface | not done | keep the adapter and the model class; the screen goes to R8 | F2 |
| C1 | Ask whether `docs/` is versioned | not done | keep | phase C: `core-project-init`, `ops-pull-request`, `ops-branch-sync`, `flow-fix-bug`; C0.1; default 84 |
| P1 | First comment on published posts | done, unticked | tick, archive | A2 |
| PB1 | `brand-profile` | done | archive | A2 |
| PB2 | `brand-strategy` | done | archive | A2 |
| PB3 | `brand-voice` | done | archive | A2 |
| PB4 | `mkt-content-plan`, `mkt-social-copy`, `mkt-publish` | done | archive | A2 |
| PB5 | Mailbox provider class | partly | merge into PB6; tick; one sentence about one account removed | A2, A3 |
| PB6 | `mkt-engage` | partly | rewrite: the skill is built; the e-mail parser is open | A2, then H; `mkt-engage`'s row |
| PB7 | Agent `social-manager` and its runtime slice | partly | rewrite; the run log moves to the project | A2, A3, then H |
| PB8 | Always-on, low-cost architecture | partly | rewrite: the comparison is done; three leftovers | A2; F2, H |
| PB10 | `brand-identity` | done | archive; one person's cover image removed from the text | A2, A3 |
| PB11 | Linters with translated headings | not done | keep | phase C: `product-backlog`, `product-feature-spec` |
| PB12 | `brand-name` | done | archive | A2 |
| PB13 | `brand-guidelines` | done | archive | A2 |
| PB14 | Flow `flow-brand` | not done | keep | G step 1 |
| PB15 | Weekly vote to a published post | partly | rewrite as the generic contract; the layout of one repository leaves the text | A2, A3, then H |
| PB16 | Weekly "latest posts" routine | not done | rewrite as a generic routine | F2, after decision 10 |
| NS1 | `ops-release` | not done | keep | G step 3 |
| NS2 | `mkt-launch-plan` | not done | keep; wording rewritten | G step 4 |
| NS3 | `flow-launch` | not done | keep, last | G step 4 |
| D7 | The artifact contract | not done (approved) | keep | C0.1, C0.2 and the **F** of every row |
| D8 | Code shared by several skills | partly | keep | C0.3, C0.4 and the **S** of the rows |
| D9 | How a skill reaches a provider | done by #44, two leftovers | keep the leftovers | `mkt-publish`'s row (N2); F3 (N13) |
| D10 | Tests of skill scripts in the skill | done | archive | A2 |
| D11 | What the runtime is | not decided | keep | decision 10; F2 |
| D12 | Flows cited and not built | done; planned skills are still cited without the mark in ten capabilities | keep the remainder | the **B** of those rows; A5 (the validator's rule) |
| D13 | Python versions | done by #44; its CI job fails | keep the repair | A1 |
| D14 | Backlog hygiene before T14 | partly | merge into T14's first step | A2 |
| PL-helper | The adapters' shared helper | not done | drop (default 18) | B2 removes the duplicated code |
| PL-digest | Base images by digest | not done | keep | B1 |
| PL-cases | Cases adapted | partly | rewrite: only the fixture builder is left | `design-handoff`'s row (default 46) |
| PL-validation | Validation rules | not done | keep | A5 (warnings), C0.1 and C0.2 (errors) |
| N1 | Repair the `python39` job | open as pull request #45 | keep | A1 |
| N2 | `payload.py` builds a provider path | not done | keep | `mkt-publish`'s row (default 68) |
| N3 | Revisit the tolerance | settled | drop: the gate is approved and the tolerance decides nothing today (default 23) | B11 (recorded) |
| N4 | The grader grades its own model's runs | not decided | keep as a decision | decision 2; B3 |
| N5 | `core-skill-creator` is above the size guide | not done | keep | `core-skill-creator`'s row |
| N6 | The routing table lacks seven built skills | not done | keep | `core-orchestrator`'s row; A5 |
| N7 | Two references that could name a skill as a writer | not done | keep | rows of `core-clarify` and `ops-repo-baseline` |
| N8 | Inventory drift | not done | keep | A3 |
| N9 | Scripts with no test | not done | keep | rows of `mkt-engage`, `mkt-social-copy`, `core-research`, `design-system` |
| N10 | CI jobs that are not required checks | not done | keep | default 87; the maintainer's action in phase A |
| N11 | The API adapter is unfinished | not done | keep | F2 |
| N12 | The Linux scheduler never ran on a real host | not done | keep | H, then F2 |
| N13 | Installers do not carry what a skill needs | not done | keep | F3 |
| N14 | The local tier | deferred by the maintainer | keep as its own item | F7 |
| N15 | Containment of runtime agents | not done | keep | F2 |
| N16 | Planned flows, agents and skills with no id | not done | keep; ids given | A9; phase G |
| N17 | Jobs scheduled before the ledger move | an action in each project | not tracked here | H |
| N18 | Reversed decisions are not marked | not done | keep | A3 |
| N19 | Principle 8 cleanup of the documents | not done | keep | A3 |

Counts: 101 rows: 19 S, 20 T, 11 R, C1, P1, 15 PB (there is no PB9), 3 NS, 8 D, 4 PL and 19 N.

## Risks

| Risk | Likelihood | What limits it |
|------|------------|----------------|
| A defect of the harness is found during the round, after records exist under version 5 | medium | the proof run of phase B and the pilot of phase D, read by hand; if it still happens, the loop's rule 3: stop, fix, measure the recorded skills again |
| Sharper assertions lower scores, and skills that passed the first round fail (the audit names `brand-strategy` and `eng-unit-tests`) | high for a few skills | each replacement is chosen from a difference seen in the first round's runs; batch 1 runs those skills first; the repair loop has a limit |
| The strong model's account limit stretches the round | high | ten skills at a time under one lock; batches do not wait for repairs; 2 to 4 days planned |
| The provider retires or changes a model version during or after the round | low during, certain eventually | a record names its models; a new model is a new round by definition and is not a failure of this plan |
| Six lanes editing skills at once collide on shared fixtures, generated copies or the status table | medium | a fixture family changes in one lane only (C0.8); copies are regenerated, never edited; the status table is regenerated at each merge |
| Phase C grows while it runs (394 should-fix items) | medium | the exit is the must-fix list and the cross-skill change list; a should-fix item not done is listed in the pull request, not silently dropped |
| A decision of part (a) arrives late and blocks a lane | medium | 12 rows wait on no decision and start at once; C0 and phases A and B do not wait on decisions 6 to 14 |
| The pinned image cannot be rebuilt (a snapshot or a digest disappears) | low | the built image is stored and its digest is in every record; the definition is kept buildable by the CI job |
| Web cases give different results on different days | certain | nine cases, marked in the record; serialised by the runner; a failing web case is read with the network in mind |
| Text about one real case is copied back into the repository by this very audit | low | the audit folder was checked for names, paths and credentials before the commit; `validate.py` checks it at every commit |

## What would make a second round necessary

After the round, each of these stales all 48 skills, or enough of them to amount to a round. They are the things that must not change, or must change only on purpose:

- the grading template, or what the runner gives the grader (the facts block, the input files, the number of passes);
- the image: its definition, a tool added or removed, the versions of the two runners, its platform;
- either eval adapter's `run-prompt.sh`, including flags that change what a model may do or see;
- the measurement constants (runs, timeout, retries, early-end phrases, refusal markers, the file limit) and the gate's rule, threshold or tolerance;
- the strong model, the floor model or the grader;
- `shared/references/`, which every run receives;
- a change of convention applied to every skill afterwards: a new required frontmatter key, shorter descriptions for the listing budget (decision 9, third option), a new canonical sentence, a renamed requirement class, a validator rule that existing skills fail;
- a change to the source of a script that many skills carry as a generated copy, or to a fixture family shared by many skills;
- the credential sidecar or the local-model tier built into the executor (lane F7).

These cost one skill's measurement, not a round, and are normal work after the freeze: a fix or a new version of one skill; a new case for one skill; a planned skill that gets built (plus the orchestrator, once per batch); a description changed after the routing measurement.

These cost nothing: tests of skill scripts; everything under `providers/`, `scripts/`, `contracts/`, `templates/`, `docs/`, the installers and the runtime, as long as no skill folder and no frozen file changes.

## Estimated effort

Sizes are the audits': S under an hour, M a few hours, L a day or more. A working session here is one sitting in which an agent carries an item or a batch to a pull request and the maintainer reviews it; the ranges are honest about review and rework, not best cases.

| Phase | Items by size | Working sessions | Elapsed, with the parallelism stated |
|-------|---------------|------------------|--------------------------------------|
| A | 4 M, 5 S, and the maintainer's own actions | 3 to 5 | 1 to 2 days, four lanes |
| B | 7 M, 4 S, two proof runs | 5 to 8 | 2 to 3 days, beside A and C |
| C0 | 4 M, 4 S | 3 to 4 | 1 to 2 days, beside B |
| C, the 48 skills | 4 S, 33 M, 11 L | 20 to 30, across six lanes | 3 to 5 days |
| D | 2 S, 2 M | 2 to 3 | 1 day |
| E | L: 3,120 runs, about 39 to 44 hours of compute | 4 to 8, most of them repairs | 2 to 4 days, set by the account limit |
| F, without the runtime | 3 M, 2 L | 6 to 10 | independent of everything above after the round |
| F2, the runtime | L several times over | its own plan after decision 10 | weeks |
| G | M to L per skill or flow | 2 to 4 per skill | as real tasks arrive |
| H | none | none | the events' own time |

To the end of the round (phases A to E): about 37 to 58 working sessions, 8 to 14 days elapsed if the decisions of part (a) are answered at the start and the lanes run in parallel. The compute of the round is about 39 hours with one grading pass and about 44 with two, at 5 runs per case and 156 cases; the pilot and the proof runs add about 4 hours.
