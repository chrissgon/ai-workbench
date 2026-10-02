# Audit of 2026-10-02

Nine read-only audits of the whole repository, made on 2026-10-02 before one final measurement round of the 48 skills. The plan built from them is [../final-plan-2026-10-02.md](../final-plan-2026-10-02.md); this folder is its evidence.

## What was audited

| File | Scope | Commit read |
|------|-------|-------------|
| [group-1.md](group-1.md) | `biz-icp-positioning`, `biz-market-analysis` and the six `brand-` skills | `b363f1b` |
| [group-2.md](group-2.md) | the eight `core-` skills | `b363f1b` |
| [group-3.md](group-3.md) | the five `design-` and the four `product-` skills | `b363f1b` |
| [group-4.md](group-4.md) | `eng-architecture`, `eng-code-review`, `eng-codebase-map`, `eng-docs`, `eng-impact-analysis`, `eng-implement`, `eng-integration-tests` | `b363f1b` |
| [group-5.md](group-5.md) | `eng-refactor`, `eng-root-cause`, `eng-security-review`, `eng-tradeoffs`, `eng-unit-tests`, `flow-fix-bug` and the four `ops-` skills | `b363f1b` |
| [group-6.md](group-6.md) | the six `mkt-` skills | `b363f1b`, and for two skills the branch that became `3cbc7f2` |
| [harness.md](harness.md) | the eval harness: grading, noise, early ends, what a run sees, the record, the container, installers, `validate.py`, CI | `b363f1b` |
| [cross-skill.md](cross-skill.md) | what crosses skills: the artifact contract (decision D7), shared code (D8), command-line conventions of the 55 skill scripts, canonical sentences, a change list per skill | `3cbc7f2` |
| [backlog.md](backlog.md) | every item of `docs/backlog.md`: done or not, still worth doing, where it belongs; work no item covers (N1 to N19) | `3cbc7f2` |

## Reviews of the plan

The plan built from the audits was itself reviewed in two rounds on 2026-10-02, read-only. The plan's section "Reviews" says where each round's findings went.

First round:

| File | Scope |
|------|-------|
| [plan-review-consistency.md](plan-review-consistency.md) | the plan against itself: counts, order, defaults and decisions that contradict each other (2 blockers, 19 should-fix, 9 nits) |
| [plan-review-architecture.md](plan-review-architecture.md) | the plan against the code and the architecture, with 38 of its items checked in the files they name (5 blockers, 10 should-fix, 6 nits) |

Second round, made on the plan as amended after the first (`6347292`):

| File | Scope |
|------|-------|
| [round2-plan.md](round2-plan.md) | the plan read by its executor: whether each item can be carried out without guessing, the order between items, the freeze, the round's arithmetic (4 blockers, 19 should-fix, 10 nits) |
| [round2-providers-runtime.md](round2-providers-runtime.md) | the providers, the contracts, the agent runtime, the doctor and the packs, read in the code and run offline (no blocker, 42 should-fix, 38 nits); the source of the plan's phase P |
| [round2-adapters-ci.md](round2-adapters-ci.md) | the adapters and installers, the validator, the security scan, CI and the public face, with installs made in a scratch clone (no blocker, 24 should-fix, 27 nits) |

All five are the reports as written, with these changes: the name of the working tree two of them were made in is replaced by a description; in the second round, one quoted probe value that the repository's secret scan rejects and three quoted phrases in another language are replaced by descriptions. They cite the plan by the line numbers it had when they were written ("L123" in `round2-plan.md`): search for the quoted text. Three ids differ between the second round's reports and the plan, which renamed them to avoid a clash with backlog ids: the reports' "R1 to R7" for the first round's resolutions are the plan's PR1 to PR7, the providers report's findings PB1 to PB16 are the plan's PUB1 to PUB16, and the plan's phase P items are HP1 to HP3.

## How it was made

- Nine audits ran in parallel, each with its own scope and none changing a file: no eval was run, no model was called by the harness, no provider touched a real service. Scripts and tests were run on copies outside the repository.
- The six group audits read each skill's folder in full and the last complete eval iteration of the skill (the gradings of the four variants, selected replies and transcripts). Each skill has three lists: "Must fix" (it would fail, mislead the score or break a principle), "Should fix" (quality and robustness) and "For the maintainer to decide".
- The harness audit read the harness files in full, processed every benchmark and grading of the first round by script, and re-judged 47 gradings (252 verdicts) by hand.
- Pull request #44 (providers resolved by class) merged while the audits ran. The cross-skill and backlog audits were computed again on that commit; the others say where it matters.

## How to read the files

- The files are the reports as written, with three kinds of change made for this repository: paths of the machine the audit ran on are replaced by `<repository>` (this repository), `<eval workspace>` (the folder, outside the repository, that holds the runs of the first measurement round) and `<scratch>` (the audit's temporary folder, not kept); one real person's name, two identifiers of a design file and one account handle were replaced by a description in place; one quoted command and one quoted place name were reworded so that the repository's own checks accept the file.
- Evidence paths that start with `<eval workspace>` point at data that is not in the repository. An implementer who needs a run's output asks the maintainer for it; nothing in the plan depends on those files being present.
- `file:line` references are to `main` at the commit named in the table. Line numbers move as files change: search for the quoted text.
- Notation differs per report and each report defines its own at the top (pass patterns per variant, case and assertion numbers; group 6 counts assertions from zero).
- Where two reports disagree, the plan says which one it follows and why (its section "Where the reports disagree").
- The reports are a snapshot. They are not updated as the work lands; the plan's tables are.
