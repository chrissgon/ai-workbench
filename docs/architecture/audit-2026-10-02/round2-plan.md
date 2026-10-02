# Second review of the final plan: execution lens

Read-only review, 2026-10-02. All 850 lines of `docs/architecture/final-plan-2026-10-02.md` read, at `6347292` (the plan as amended, #47). "L123" is a line of the plan. Checked against the repository: `evals/eval-gate.json`, `evals/eval_status.py`, `evals/eval_run.py`, `skills/*/evals/evals.json`, `skills/*/SKILL.md` frontmatter, `scripts/tests/test_script_copies.py`, `.githooks/pre-commit`, `.github/`, `adapters/`, `docs/decisions.md`, `git log`. Findings of the first two reviews are not repeated; where a finding touches one, it says what is new.

Severity: **blocker** (rework, a broken or stuck `main`, or a second round), **should-fix**, **nit**.

## Summary table

| # | Sev | Finding | Smallest addition |
|---|-----|---------|-------------------|
| 1 | blocker | `known_draft` and the new meaning of `--strict` are used by phase E (L614, L620, L627) and built by no item; the gate loader rejects an unknown key | Build both in B10, before the freeze |
| 2 | blocker | The repair loop has no rule for a fix that lies outside the one skill (shared script source, fixture family, platform reference, dependency skill, frontmatter that regenerates the owner table) | A rule 4a in the loop, and batch order by dependency |
| 3 | blocker | The pilot's `--platform` run (L576) is refused by B7a's own rule (L461), and no record is written by a real run before batch 1 | One pilot skill at the configured runs, record written, then `--platform` |
| 4 | blocker | C0.4 and C0.3 cannot merge green in the order given: the conformance test fails on nine scripts until the rows land; `sync_copies.py --check` fails on copies not yet regenerated | An expected-failure list and a per-copy "adopted" flag that each row removes |
| 5 to 27 | should-fix | see sections 1 to 7 | |
| 28 to 37 | nit | see section 8 | |

---

## 1. Regressions of the amendment and the mechanical cross-reference check

### 1.1 Ids referenced and never defined

Every pattern was extracted by script (A\d+, B\d+[a-z]?, C0.\d+, D\d+, F\d+, R\d+, N\d+, S\d+, T\d+, PB\d+, NS\d+, Q\d+, PL-*, "default N", "decision N", "G step N", "lane FN").

| Pattern | Result |
|---------|--------|
| A1 to A10 | A6 is never defined and never referenced: a gap, explained at L426 ("first filed here, is item B6a"). Nit 28. |
| B1 to B11, B6a, B7a | all defined (L453 to L465) |
| C0.1 to C0.9 | all defined; the table lists C0.9 before C0.8 (L489, L490). Nit. |
| D1 to D4 | defined (L574 to L577); D7 to D14 are the review's decisions (L98, L764 to L771): no number overlaps |
| E\d+ | none used |
| F1 to F7 | all defined (L635 to L641) |
| defaults 15 to 90 | all defined, contiguous (L296 to L383); every "default N" cited resolves |
| decisions 1 to 14, 14a, 14b, 14c | all defined |
| G steps 1, 3, 4, 6, 7 | resolve to the "Order" column of L654 to L661 |
| N1 to N19, S1 to S19, T1 to T20, PB1 to PB16 (no PB9, said at L796), NS1 to NS3, PL-* | all have a row in the backlog map; 101 rows counted, as L796 says |
| Q1 to Q11, Q4a to Q4d | exist in `audit-2026-10-02/backlog.md` |
| "the loop's rule 3" (L802) | resolves to L611 |
| **R1 to R7** | **defined twice**: see 1.2 |
| `known_draft` | used at L614, L620, L627; defined by no item: see finding 1 |

### 1.2 Should-fix 5: R1 to R7 mean two things

L35: "Where the plan applies one, it says "(R1)" to "(R7)"." The same ids are the backlog's runtime items: L197 "the runtime items R1 to R7 get a "Done when"", L198 "department agents (R3, R4, R8, R9)", L733 to L743, and above all L636: "the per-agent parts sit behind a handler (R1) ... made generic (R2, R5, R6, R7)". By the rule of L35, the reader of L636 takes those as resolutions of the review. Smallest edit: rename the resolutions (for example RV1 to RV7) or write "backlog R1" in L197, L198 and L636. The same collision, smaller: L438 "consistency S12" beside backlog S12 (L705).

### 1.3 Should-fix 6: the state the plan describes is no longer the state of `main`

- L49: "Read on `main` at `3cbc7f2`". `git log`: `a0b60be fix(ci): the Python 3.9 job runs the tests where they now live (#45)` is merged, then #46 and #47.
- L66: "one job failing | `python39`, since #44; the repair is open as pull request #45"; L430 (A1): "Merge the repair of the `python39` CI job (pull request #45)"; L776: "N1 | ... | open as pull request #45".
- An agent executing A1 tomorrow looks for an open pull request that does not exist. Edit: A1 keeps only its second half (the wiring test); L66 and L776 read "merged as #45".

### 1.4 Should-fix 7: R6's claim against B10's list (new part: the runner itself)

- L42 (R6): "It covers every file that decides what a run measures". L8: frozen are "the eval runner, the adapters, the container image, the grading template, the gate". L817: "what the runner gives the grader (the facts block, the input files, the number of passes)".
- L464 (B10) lists: the template, `evals/container/`, `evals/executor.py`, `scripts/stage_skills.py`, the two `run-prompt.sh`, the `adapter.json` files, `measurement.json`, `shared/references/` without `platforms/`. **`evals/eval_run.py`, `evals/eval_status.py` and `scripts/redact.py` are not in it.**
- What lives only there after phase B: the facts block (B3), the early-end rule (B4; only its phrase lists move to `measurement.json`), the zero for a repeated timeout (default 16), the redaction applied before grading (B6a, through `scripts/redact.py`), which platform files are staged (B2), the unrounded gate comparison (B5, in `eval_status.py`).
- The first review asked for the executor, the staging code and `adapter.json`; the runner was left out without a sentence saying so. A change there after the round passes `validate.py`; the only thing that notices is `core-skill-creator`'s `workbench_files` hash, which stales one skill and says nothing about the other 47.
- Smallest edit: either add the three files to B10's list (cost: F4 and lane F2's scenario evals then cannot touch `eval_run.py` without a justification on record), or move the measuring functions into one fingerprinted module (`evals/measure.py`: facts block, grading call, early-end rule, scoring) and say in R6 that the rest of the runner is free.

### 1.5 Should-fix 8: B10 and B7 disagree on what the record guards

- L464: "`runs`, `timeout_seconds`, `retries` and `web_jobs` have one home, the gate file (B5), and are covered by the record, which reads `stale` when they differ (B7)".
- L460 (B7): "`stale` also when the harness names, the runs or the `workbench_files` hash differ". Only `runs`.
- `grading_passes` (L120, L455) is in neither list, yet L817 names "the number of passes" among what forces a round.
- Edit in B7: "`stale` also when `runs`, `timeout_seconds`, `retries` or `grading_passes` differ from the gate file" (`web_jobs` is pacing and should not stale).

### 1.6 Should-fix 9: "Touches" columns the amendment left incomplete

| Item | Missing | Evidence |
|------|---------|----------|
| B3 (L455) | `evals/eval-gate.json` | it adds `grading_passes`; `gate_problems` reports both "unknown field" and "missing field" (`evals/eval_status.py:115-118`), so code and file change together |
| B10 (L464) | `evals/eval_run.py` | the file limit and the phrase lists move to `measurement.json`; the runner must read them |
| C0.3 (L484) | `AGENTS.md` (Layout: `shared/scripts/`, `scripts/sync_copies.py`; "today only security.md") | L438 lists the edits of `AGENTS.md` before the round as "(C0.1, C0.6, B11)" only |
| C0.6 (L487) | `scripts/security_scan.py` | default 59 (L346): "the security scan's rule names a diff and command output among the sources that require it"; no item touches the scan, and it is one of `core-skill-creator`'s `workbench_files` |
| C0.9 (L489) | the authoring guide, or its removal from the text | "in the templates and the authoring guide" against L492 "C0.1 to C0.7 and C0.9 touch no skill folder"; row 16 (L526) lists the runner's `--platform` but not the literal step, the `--platform-file` rule or the parser exception |
| C0.1 (L482) | the generator of "a generated table of owning skills" | no script is named; `sync_copies.py` (C0.3) only copies it into the orchestrator |
| A3 (L432) | `adapters/api/README.md`, `providers/scheduler/systemd.py` | both cite `docs/architecture/always-on-runtime.md` (README line 3, `systemd.py` line 9), which A3 moves out |
| A10 (L438) | `AGENTS.md:89` | "`publisher:linkedin`" is a platform named as an example in a core file, against rule 2 of 14b and default 35, which A10 writes into the same file |

---

## 2. Is each item executable without guessing?

Only items with a gap are listed. "ok" items: A4, A7, A9, B4, B6, B6a, B9, C0.2, C0.7, D1, D2.

### Phase A

| Item | Gap | Smallest addition |
|------|-----|-------------------|
| A1 | first half already done (1.3) | keep the wiring test only |
| A2 | no acceptance of its own; also the home of two unowned records: "one backlog item per skill" for the 31 untargeted cases (L245) and the dated-fixture item (L686), which otherwise make six lanes edit `docs/backlog.md` at once | "Done when: the audit's Findings 1 to 10 no longer reproduce"; open those items here, before the lanes |
| A3 | "`always-on-runtime.md` moves to the project it describes" (L381, L432): the destination is outside the repository and cannot be named in it; an agent cannot do it | "the maintainer copies the file out and confirms; the pull request then deletes it and rewrites the two citations" |
| A5 | one pull request with 19 rules; no order relative to C0.1, C0.2, C0.3, B7a and B10, which all edit `scripts/validate.py`; its list of flagged skills is "attached to the pull request", where the six lanes will not find it | "A5 merges first of the items that edit `validate.py`"; write the list to a file under `docs/architecture/` |
| A8 | "on each harness" does not say which, nor where the install goes; an install into the person's own settings changes their machine | name the two harnesses and "into a scratch home, removed afterwards" |
| A10 | sized S, edits seven places of `AGENTS.md` and two decisions entries; fine as one pull request | add `AGENTS.md:89` (1.6) |

### Phase B

| Item | Gap | Smallest addition |
|------|-----|-------------------|
| B1 | "the built image stored" needs the answer L140 leaves open ("a registry ..., or an archive ... it is the maintainer's choice") and L676 still lists as pending; eleven sub-changes in one row | record the answer; split "pinning and storing" from "what is in the image" if review size matters |
| B2 | ten sub-changes, sized M; "the files of the platforms its case file names" (L454): no key of a case is defined for that, and A5 adds "`evals.json` with known keys only" (L434) | define the key (`platforms: [<name>]` on a case) in B2 and in the known-keys list of A5; split the hygiene parts (bytecode, git exclude, `--pass-env`, `tests` in `workbench_files`) into B2b |
| B3 | see 1.6; the order relative to B2 (same `run-prompt.sh`) and B5 (same `GATE_FIELDS`) is not given (3.2) | "B3 after B2; B5 after B3" |
| B5 | "a total of concurrent runs in the gate file" (L457): no number anywhere; L592 gives only "2 on the floor tier" for web | state the total and the strong tier's `web_jobs` |
| B7 | see 1.5 | |
| B7a | "refused unless the base record is current" (L461): refused to run, or refused to write? It decides whether D3 can run it (finding 3) | "the run is allowed; writing the entry is refused" |
| B8 | "read from the provider when it cannot" (L462): no acceptance | add to the proof run's checklist: "`total_tokens` is not null in the floor tier's `timing.json`" |
| B10 | `known_draft` missing (finding 1); see 1.6 | |
| B11 | the documents of the freeze itself (`--strict`, `known_draft`, `marginal`, the `platforms` section, `measurement.json`) are not in its list of `AGENTS.md` sections ("Adding an adapter" and "Writing standard" only, L465) | add "Validation" and "Eval status" |
| Proof run (L467) | "a skill with a script and a setup step, both of its cases": not named; the agent picks | name it (a skill with two cases, a script and a setup step, not in the pilot) |

### Phase C0

| Item | Gap | Smallest addition |
|------|-----|-------------------|
| C0.1 | the generator of the owner table (1.6); the table "Slots no built skill writes" needs a third row, `docs/workbench/runtime.json` (row 44, L554: "a `user` slot"); "as warnings until the last group batch merges and as errors after it": no item makes the switch | name the script; add the slot; add an item "C-last: warnings become errors" (finding 13) |
| C0.3 | finding 4; which pull request changes a shared script's behaviour (finding 12) | |
| C0.4 | finding 4 | |
| C0.5 | "one shape for a check script's `--report` file": where it is written is the template only; nothing tests that twelve scripts in four lanes write the same shape | add the shape to C0.4's generic test |
| C0.6 | see 1.6 (the scan) | |
| C0.8 | finding 11 | |
| C0.9 | two unrelated deliverables (the reference and its data file; three installers) in one M | split into C0.9a and C0.9b; only C0.9a blocks the lanes of groups 1 and 6 |

### The 48 rows

- **Should-fix 10: "batch" is not defined for phase C.** L422: "one pull request per item or per batch"; L492 "the batch of group 5"; L482 "until the last group batch merges"; L562 "Within a lane, the skills already `stale` and the L rows go first". If a batch is a group, one pull request carries ten skills, each with its before-and-after list of case changes (L499); if it is a row, "the last group batch" means nothing. Addition: "one pull request per row; a family change of C0.8 is its own pull request, first in its lane".
- The rows themselves delegate their detail to the group reports (L507); with those, each is executable. Row 12 and row 16 have an order constraint (3.3).

### Phase D

| Item | Gap | Smallest addition |
|------|-----|-------------------|
| D1 | L574 "the fingerprint accepted, and this value is the one the round runs under" against L584 "The fingerprint at that commit is the one the round runs under" (after a pilot that may have fixed the harness) | drop the clause in D1 |
| D1 | decision 9 cycle (finding 14) | |
| D3 | finding 3 | |
| D4 | "the grader disagreement rate computed" (L577): no record exists at 2 runs; nothing says the benchmark on disk carries the count | B3: "the iteration summary carries passes and disagreements" |
| "What stops the round" (L579) | "the pilot is run again on the skills it touched": a harness fix touches all six | "on all six when the fix is in a frozen file" |

### Phase E

- Finding 1, 2, 15, 16, 17 below.
- **Should-fix 15: nothing in phase E runs the platform cases.** L505: the `mkt-publish` case moves "so that the path exists for the pilot and for the round (the case count does not change)". The batches (L599 to L603), the loop and the exit (L627) never mention `eval_run.py --platform`; the volume counts the case; the exit accepts `not measured` (L620). Addition to L605: "after a skill's base record is written, its platform cases are run with `--platform`; the round's report lists each platform's state".
- **Should-fix 16: the loop's count.** L613 adds one unchanged re-measurement; L614 says "At most two repairs per skill, three complete measurements in all". With rule 5 a skill can reach four. Say whether the unchanged re-measurement counts.
- **Should-fix 17: default 60 against a record's pull request.** L347: "`metadata.version` is raised once per pull request that changes a skill's folder". `evals/result.json` is inside the folder: read literally, the batch pull request raises the version, which changes `SKILL.md` and stales the record it carries. Also the C0.8 pull request of another lane raises a skill's version a second time, against "all 48 are raised once in phase C". Edit: "that changes a file inside the skill's content hash; once per skill in phase C whatever the number of pull requests".

### Phase F

- **Should-fix 18.** The table has no "Touches" column; exits exist for F1 and F3 only (L646). F3 is sized M and holds: the default from link to copy in two installers, a `--link` option, the provider files, `WORKBENCH_ROOT`, the listing size, a `doctor.py` check and a real install. F4 must add a mode to `evals/eval_run.py`, which is one of `core-skill-creator`'s `workbench_files` (`skills/core-skill-creator/evals/evals.json:21`), and its note names only "A description it leads to change". Additions: a "Touches" column; exits for F4 to F6; F3 split in two; in F4's note "changes `eval_run.py`: `core-skill-creator` is measured alone".

---

## 3. Dependency graph

### 3.1 Order implied by the plan

```
A1 ─ A7                       A5 ──────────────┐ (its list; first editor of validate.py)
A2 ─ A3 ─ A9                                   │
A4, A10, A8                                    ▼
decisions 1-5 ─ B1 ┐                    C0.1 ─ C0.2 (errors "with C0.1")
                   ├ B2 ─ B3 ─ B6a      C0.3 (sources) ─ C0.4
                   │   └ B8             C0.5, C0.6, C0.7, C0.9a
                   ├ B4, B6             │
                   └ B5 ─ B7 ─ B7a      ▼
        proof runs ─ B9 ─ B10 ─ B11     six lanes (C0.8 first in lanes 5, 6, 3)
                              │         │
                              └──► row 16 (core-skill-creator), row 12 last
                                        ▼
                              "C-last": warnings to errors
                                        ▼
                              D1, D2 ─ D3 ─ D4 ─ E batches ─ freeze ─ F, G
```

### 3.2 Parallel lanes that edit the same file (should-fix 19)

L414: phase B runs beside A and C on "other files: `evals/`, `adapters/`". L442 gives four lanes for phase A. L469 gives the lanes of B. By the "Touches" columns:

| File | Editors said to be parallel | Lines |
|------|-----------------------------|-------|
| `docs/inventory.md` | A8 (lane 4) with A3 and A9 (lane 2); B7 changes the generated table's columns while every lane regenerates it | L436, L432, L437, L442, L460 |
| `docs/decisions.md` | A10 (lane 4) with A3 (lane 2); B11 | L438, L432, L465 |
| `scripts/validate.py` | A5, B7a, B10, C0.1, C0.2, C0.3, and the unowned switch to errors | L434, L461, L464, L482 to L484 |
| `AGENTS.md` | A10, C0.1, C0.6, B11 (C0.6 and B11 both in "Writing standard") | L438, L482, L487, L465 |
| `templates/capability.SKILL.md` | C0.5, C0.6, C0.9 | L486, L487, L489 |
| `evals/eval_run.py` | A4 (docstring) with B2, B3, B4, B5, B6, B6a, B7, B7a, B8, B9 | L433, L454 to L463 |
| `adapters/claude-code/run-prompt.sh` | B3 (`--no-tools`) is put in the parallel set "B1, B3, B4 and B6" while B2 rewrites the same file | L455, L454, L469 |
| `evals/eval_status.py` (`GATE_FIELDS`) and `evals/eval-gate.json` | B3 in the parallel set, B5 in the serial one; both add keys to the same dict and file | L455, L457, L469 |
| `evals/executor.py` | B1 and B2 (no order given), B6a | L453, L454, L459 |
| `contracts/secrets.md` | B6a with C0.2 | L459, L483 |
| `.github/workflows/checks.yml` | A1 with B9 | L430, L463 |
| `adapters/*/README.md` | A4 with B11 | L433, L465 |
| `.githooks/pre-commit` | A7 with C0.3 | L435, L484 |
| adapters' tests, `scripts/tests/test_installers.py` | B2 with C0.9 | L454, L489 |

Addition: in L442 move A8 and A10's decisions entries into lane 2, or say "A8 and A10 merge after A3"; in L469 "B3 after B2, B5 after B3, A4 before B2"; in L492 "C0.5, C0.6, C0.9 in that order on the template; A5, C0.1, C0.2, C0.3 in that order on the validator".

### 3.3 Needed earlier than scheduled, and cycles

- **Should-fix 14: decision 9 is a cycle.** L191: "Needed before phase C closes"; L189: shorter descriptions "must land in phase C or it costs a second round"; L574 (D1): the measurement is "taken again, since phase C lengthened descriptions, before decision 9 is closed", and L583: D "Depends on: phases B and C merged". The measurement that can reopen all 48 `SKILL.md` files runs after the phase it must precede. Edit: the second measurement is the last step of phase C's exit; D1 only checks it was done.
- **Finding 4 (blocker).** L562: "Order: C0.1 to C0.7 and C0.9 first. Then six lanes". L485 (C0.4): "The scripts it finds failing are fixed in their skill's row". L83: "Nine scripts end in a traceback". The test of C0.4 is red on `tests`, a required check, from the day it is written until the last of those rows merges; today three such tests exist only because they are `xfail(strict=True)` (`skills/design-execute/scripts/tests/test_lint_result.py:130`, `eng-codebase-map` line 99, `eng-implement` line 104). C0.3 has the same shape: `sync_copies.py --check` is wired into the validator and the hook (L484), and the copies it lists differ from their new sources (the "reconciled `contrast.py`", the two prose copies of the orchestrator) until rows 4, 20 and 12 regenerate them, or C0.3 edits skill folders, against L492. Addition: "C0.4 ships with a list of scripts expected to fail, one line removed by each row; the manifest of C0.3 marks a copy `adopted` when its row regenerates it, and `--check` reads adopted copies only; both lists are empty at phase C's exit".
- **Should-fix 11: C0.8 makes two lanes edit one skill folder.** L562: the lanes run "each in its own working tree, since their skill folders do not overlap"; L492: "the invoices family is changed in the batch of group 5 (with group 4's three copies in the same pull request), the Dana family in the batch of group 6 (with group 1's copies)". Rows 29, 30 and 32 (group 4) each list "the fixture's runtime line" as their own change (L539, L540, L542); row 3 (group 1) lists "the shared brand fixtures get reserved hosts" (L513). The same change is assigned twice and the folders do overlap. Addition: "the family pull request is the first of lanes 5 and 6; lanes 4 and 1 start the affected skills after it merges and their rows do not repeat it".
- **Should-fix 12: a change of behaviour in a shared script crosses lanes.** After C0.3 the source is in `shared/scripts/`. Row 8 (group 1): "`voice_stats.py` parses its arguments before reading input" with a copy in `mkt-social-copy` (group 6). Default 78 and rows 27 (group 4) and 42 (group 5): `redact.py`'s docstring "changed in its source and its copies together", and `scripts/tests/test_script_copies.py:29` already fails when the two copies differ from `scripts/redact.py`. Whichever lane changes the source breaks the other lane's copy. Addition to C0.3: "every behaviour change the rows name for a shared script (`voice_stats.py`, `redact.py`, `rank.py`, `check_refs.py`, `check_post.py`, `contrast.py`) is made in the source by C0.3; a row only adopts the copy".
- **Should-fix 13: steps with no owner.** (a) the switch of the validator's rules from warnings to errors "after the last group batch" (L266, L482, L483), which phase C's exit requires (L566); (b) `known_draft` (finding 1); (c) the security scan's rule (1.6); (d) the backlog items of L245 and L686. Each needs an item id.
- **Row 12 and the owner table.** L522: the orchestrator "names the writer of a missing input from a generated owner table", a generated copy inside its folder. The table is final only when the frontmatter of the other 47 rows is merged, so every lane regenerates a file in lane 2's skill. Addition: "row 12 merges last in phase C, with row 16".

---

## 4. The freeze

### 4.1 Files inside the fingerprint, and who edits them

| File (L464, L621) | Edited by | After the freeze? |
|-------------------|-----------|-------------------|
| `evals/grading-prompt.md` | B3 | no |
| `evals/container/*` | B1 | F7 (named, L641, L825) |
| `evals/executor.py` | B1, B2, B6a | F7 (named) |
| `scripts/stage_skills.py` | B2 (new) | F3 "imports ... without changing it" (L637). It is written for evals and must also serve an installer that carries "what a skill needs of `providers/`": a constraint, not a design. Write F3's needs into B2's interface now |
| both `run-prompt.sh` | B2, B3, B8 | none planned |
| eval adapters' `adapter.json` | B2, B8 | none planned |
| `evals/measurement.json` | B10 (new) | none |
| `shared/references/` except `platforms/` (today `security.md`) | L464 allows "items of C0" to edit it and update the fingerprint; no item of C0 lists it | none |

No item scheduled after the freeze edits a fingerprinted file without the plan saying so. What the fingerprint does not see is finding 7 (1.4).

### 4.2 Blocker 1: `known_draft` and `--strict`

- L614: a failing skill "is entered by name with that item in the gate file's `known_draft` list". L620: "`validate.py --strict` becomes the CI default: ... a draft skill that is not in `known_draft`, fails". L627 is the exit.
- No item of phases A to D builds either. `grep known_draft`: three hits, all in phase E.
- `evals/eval_status.py:84-86` (`GATE_FIELDS`) has no such key and line 115 returns `unknown field` for any key outside it; the plan itself notes this for `grading_passes` (L455). Writing the list into `evals/eval-gate.json` in the middle of the round, as loop rule 6 says, makes every `eval_status.py` and `validate.py` call fail.
- Building it then means editing `evals/eval_status.py` and `scripts/validate.py`. Both are `workbench_files` of `core-skill-creator` today (`skills/core-skill-creator/evals/evals.json:21`: `scripts/validate.py`, `scripts/security_scan.py`, `scripts/redact.py`, `templates`, `evals/eval_run.py`, `evals/eval_status.py`, `docs/area-map.md`, `adapters/agents-dir/run-prompt.sh`), and default 20 hashes them into its record. So the edit that makes the exit possible stales `core-skill-creator`, and the exit ("every other skill reads `evaluated`") fails by the plan's own last step. The same holds for any sentence about the freeze added to `AGENTS.md` after batch 5 (L438: "After the round any edit of `AGENTS.md` makes `core-skill-creator` stale").
- Smallest addition: B10 gains "`known_draft` (a list, empty) in the gate file and `GATE_FIELDS`; `validate.py --strict` accepts a `draft` skill listed there and a platform's state, with tests"; B11 gains the `AGENTS.md` text of the freeze. The round's last pull request then changes only `.github/workflows/checks.yml` and `.github/CODEOWNERS`.

### 4.3 Skill folders changed after the start of phase E

| Item | Named by the plan? |
|------|--------------------|
| The repair loop (L612) | yes, for the skill repaired; **not** for what the repair drags along: blocker 2 |
| F2, PB16 (`mkt-vote-round`'s script) | yes (L636) |
| F4, a description | yes (L638) |
| G, the orchestrator's routing table | yes (L663) |
| H, the e-mail parser of `mkt-engage` | yes (L680) |
| H, dated fixtures expire in a year | yes (L686), but not which skills (rows 6, 43, 46) |
| A new requirement class (lane F2, R10: "the provider classes it needs", L682) | **no**: it regenerates `core-orchestrator`'s `references/requirement-classes.md` (L522). L827 lists `outputs` and `updates`, not a new class. Add it. |
| Files outside skill folders that stale `core-skill-creator`: `scripts/validate.py` (any new rule), `templates/` (phase G), `docs/area-map.md` (phase G, new flows), `evals/eval_run.py` (F4, lane F2's scenario evals) | only in general (L827, L831). L831 says "everything under ... `scripts/`, ... `templates/`, `docs/`" costs nothing "as long as ... no file a case brings"; four of those folders hold such files. With `--strict` on, each such pull request must carry an 80-run record. **Should-fix 20:** list the nine paths once and plan them as batches. |

### 4.4 Blocker 2: the loop does not say what a repair may touch

L612: "A skill defect is fixed in the skill; a case defect is fixed in the case ... The skill is then measured again in full, alone." Phase C makes these no longer local:

1. **A generated copy.** A defect in `rank.py`, `check_refs.py`, `contrast.py`, `redact.py`, `sensitive_topics.py` (five skills), `voice_stats.py` or `check_post.py` is fixed in `shared/scripts/` (L339: "the source of every shared script is `shared/scripts/`"); `sync_copies.py --check` then forces the copy into every carrier, which stales records already made.
2. **A fixture family.** Default 36 (L320): "a defect is fixed in every copy in one change". The invoices project is in eleven skills, the Dana fixtures in sixteen copies. L824 names this as a cause of a round, but the loop has no rule for it.
3. **The platform reference or its data file.** L288: when it is edited, "the skills whose base cases read it read `stale`": up to seven.
4. **`shared/references/security.md`**: inside the fingerprint, so all 48.
5. **Frontmatter.** A repair that changes `outputs` or `updates` regenerates the owner table inside `core-orchestrator` (L827), measured in batch 2.
6. **A dependency skill.** `flow-fix-bug` is in batch 1 (L599); its cases install `core-orchestrator`, `eng-root-cause`, `eng-unit-tests` (`skills/flow-fix-bug/evals/evals.json`) and, after default 65, `core-project-init`. `eng-unit-tests` is in the same batch and is one of the two skills the plan expects to fail (L803); the orchestrator and `core-project-init` are in batch 2, `eng-root-cause` in batch 4. The record does not name a dependency's hash (`FIELDS`, `evals/eval_status.py:93`; B7's list at L460 adds none), so the flow's final record is measured on content that the same round then changes, and nothing reads `stale`. `design-execute` (batch 1) loses its dependency by default 29, so the flow is the one case.

Smallest addition, as loop rule 4a: "A repair changes only files inside that skill's hash. A defect whose fix is in a shared source, a fixture family, a platform reference, a shared reference or a dependency is recorded, the skill is measured with a copy-local fix only if `--check` allows it, and otherwise the fix waits for the end of the round, where the affected skills are named and measured once." And in the batches: move `flow-fix-bug` and `core-orchestrator` to batch 5, after their dependencies and after the frontmatter of every other skill is settled; B7 adds the dependency hashes to the record or the plan says they are left out on purpose.

---

## 5. The round's arithmetic and feasibility

### 5.1 Recomputed from the plan's own numbers

| Claim | Check |
|-------|-------|
| L591: 156 cases × 4 × 5 = 3,120 runs | correct; 141 today (counted in `skills/*/evals/evals.json`) + 15 targeted |
| L591: "at least 6,240 gradings" | correct for two passes; a third grading on each disagreement is on top |
| L106, L107, L242, L591: 21 h for 1,692 runs, 35 h for 2,820, 39 h for 3,120 | consistent: about 45 s per run with one grading |
| L591: 34 h runs + 10 h gradings = 44 h; 39 h with one pass | consistent (about 39 s a run, about 5.8 s a grading) |
| L576: "About 24 cases, about 190 runs, about two and a half hours" | 3 + 3 + 5 + 5 + 4 + 4 = 24 after phase C; 24 × 4 × 2 = 192; 192 × 51 s = 2.7 h with two passes. Correct. |
| L595: "ten skills each, the last of eight" | 10, 10, 10, 10, 8 = 48, each skill once (checked by script) |
| L560: 4 S, 33 M, 11 L; 36 rows wait, 12 do not; 15 cases in 12 skills | all correct |
| L839 to L841: 3 M 6 S; 8 M 5 S; 6 M 3 S | correct |
| L850: 39 to 60 sessions | correct sum |
| L842: phase C "3 to 5 days" | lane 2 holds four L rows (11, 12, 14, 16) and four M; by L29 ("L: a day or more") that lane alone is five days or more, and row 16 waits for phase B. The range's lower half is not reachable. Nit. |

### 5.2 Should-fix 21: the account-limit pacing has no basis in the plan's numbers

- L590: "the first round hit its limit three times in two days". `docs/decisions.md:122`: "Every evaluation until this date used Claude Opus 5.5 as the strong model and as the grader; it used up the account's usage limit three times in two days, and 42 skills are still to be evaluated. The strong model of the gate is now Claude Sonnet 5.5". The three hits were on another model, with 42 skills still to evaluate, not on the round. The plan holds no measured figure for the configured strong model.
- The grader is the strong model on the same credential: `evals/eval-gate.json` has `"grader": "claude-sonnet-5-5"`, `"strong_model": "claude-sonnet-5-5"`, `"strong_pass_env": ["CLAUDE_CODE_OAUTH_TOKEN"]`. Calls against that account in the first round: 846 strong runs + 1,692 gradings = 2,538. In the final round: 1,560 + at least 6,240 = at least 7,800, about 3.1 times. By the plan's hours: about 17 + 10 = 27 h against about 9 + 3 = 12 h, about 2.3 times.
- Not counted in the 3,120 (L844): the pilot (192 runs, at least 384 gradings, and its reruns), the proof runs, each repair (a full measurement: about 65 runs and 130 gradings per skill, up to three per skill, L614), rule 5's re-measurements, the platform runs. Ten skills repaired once and four twice add about 1,170 runs, 37%.
- The plan gives no quota and no window, so "Plan for 2 to 4 days" (L593) cannot be derived; decision 2 (L117) prices double grading in hours and dollars and not in the resource that sets the elapsed time.
- What the runner does at a limit is not said. `evals/eval_run.py` knows one provider message (`PROVIDER_REFUSALS`, line 640). B5 (L457) adds retries for "a refusal, a transient adapter failure and a timeout"; default 16 (L297): "a timeout that repeats on a case without web scores 0". If the limit shows as a stall, ten processes retry into it and with-skill runs score 0 in a record; if it shows as an error, ten iterations end incomplete and wait for a person.
- Smallest addition: a row in B5, "the adapter's data names the message of an exhausted account; the runner then pauses every process under the lock until a time given by the operator and never scores or retries that run", proven in the proof run with a stub; and in D4 "the pilot's share of the account's window is measured, and the round's days are computed from it before batch 1".

### 5.3 Blocker 3: what the pilot does not exercise

| Mechanism | Proof run (L467) | Pilot (L576) | Untested at batch 1 |
|-----------|------------------|--------------|---------------------|
| Staging, `invoked`, both runners in the pinned image | yes | yes | |
| Facts block, grading with no tools | yes | yes, read by hand | |
| Double grading and the third grading | no (not said) | yes | where the disagreement count is read from (D4) |
| Shared lock | two processes | six skills | ten processes |
| `--resume` | yes | no | at scale |
| `web_jobs` | one web case | `biz-market-analysis` | |
| `--platform` | no | **refused**: L461 "refused unless the base record is current"; in D3 "no record is written, since 2 is below the configured runs" and every skill is `stale` | the whole path with real output |
| The `platforms` section written | D2, from stub runs | no | with real runs |
| **The record's new required fields** (L460: spread, standard error, mean per case, counts, grading hash, tool versions, `image_platform`, image digest, adapter hashes, `workbench_files` hash, attempts) | no: "No record can be written from it" | no | **first written by ten skills of batch 1** |
| `marginal`, the status table's new columns from real records | no | no | yes |
| "a record with fewer [runs] cannot be written" | the refusal only | the refusal only | the accepting side |
| `known_draft`, `--strict` in CI | no | no | yes (finding 1) |
| Behaviour at the account limit | no | no | yes (5.2) |
| Timeouts scored 0, retries counted in a record | no | no | yes |

L576 says the `--platform` run "is the one exercise of that path before the round", and B7a forbids it. And the artefact the round exists to produce, the record, is never produced by a real run before ten skills depend on it; a defect there is "the instrument" of loop rule 3 (L611): "every record already made under version 5 is measured again".

Smallest addition to D3: "one pilot skill with few cases is run at the configured runs and its record is written and read back by `eval_status.py` and by `validate.py --strict`; `mkt-publish` is that skill or a second one, so that `--platform` runs after a current base record and writes its entry. A record made this way is kept if phase D ends with no change to a frozen file." About 80 more runs.

---

## 6. What could still trigger a second round, unguarded

1. **A repair that reaches outside its skill** (blocker 2): shared script, fixture family, platform reference, dependency, owner table.
2. **`known_draft` built at the end** (blocker 1): stales `core-skill-creator` at the exit.
3. **A record-writer or `--platform` defect found in batch 1** (blocker 3).
4. **The runner is outside the fingerprint** (should-fix 7): the facts block or the early-end rule can change after the round with a green `validate.py`. Not a second round that anyone sees, which is worse: the records stop being comparable silently.
5. **Should-fix 22: routing is measured only after the freeze.** Seventeen of the 48 rows change a description ("description gains ...", "description words", L519 to L557; `core-clarify` gives up a trigger word to `core-critique`, L520). A with-skill run installs one skill (L183), so no run before the round shows whether 48 descriptions still route apart. F4 measures it "after F3", after the round, and "A description it leads to change stales that one skill" (L638). If the changes of phase C made several descriptions collide, that is several skills, found when it costs a measurement each. Addition to D3: the pilot's prompts are run once more on the strong tier with the default pack staged as extra skills, reading `invoked`; no score, a list of prompts that loaded another skill.
6. **The floor model's route.** The image, the runners and the model names are pinned; the gate names the floor model by a router's model id (`openrouter/deepseek/deepseek-v4.1-flash`). Nothing in the plan pins or records which upstream serves it. A change of route between batch 1 and batch 5 changes the floor tier inside one round, and the record cannot show it. Addition to B7's fields: the provider the response names, when the adapter can read it; a difference inside a round is reported.
7. **`grading_passes`, `timeout_seconds`, `retries`** changed after the round stale nothing by B7's text (should-fix 8).
8. **A limit hit scored as a timeout** (5.2): false failing records in batch after batch, each then "repaired".
9. **The version bump read literally** (should-fix 17) stales records in the pull request that adds them.
10. **Decision 9, third option, discovered at D1** (should-fix 14): 48 `SKILL.md` edited after the cases were "frozen for the round" (L501). Before the round, so not a second one, but it reopens phase C's exit and the pilot.
11. **The harness changes in B1 to B10 while the version stays 4.** `AGENTS.md`: "Changing the container's definition changes what a run measures: raise the measurement version in the same commit." For two or three days `main` holds a new image and runner under version 4 with 33 skills reading `evaluated`. The plan forbids measuring in phase C (L422) but does not say the rule is suspended, and nothing stops a record being written. Nit 29: say so in phase B's goal, or have B1 raise the version to 5 and B11 only close it.

---

## 7. Stale confirmation marks and questions already answered

The maintainer has confirmed every decision, R1 to R7 and the additions. To reword as decided:

| Line | Text | Reword |
|------|------|--------|
| L3 | "Its section "Decisions for the maintainer" awaits the maintainer; nothing in it is decided until they say so" | "Every decision was confirmed by the maintainer on 2026-10-02" |
| L33 | "the remaining nit (a status line saying which decisions are answered) is the maintainer's to write" | now writable: add the status line |
| L35 | "each is **proposed after the review of the plan, awaiting the maintainer's confirmation**" | "each was confirmed" |
| L212, L258, L272, L281, L283, L438, L464, L489, L614 | "(...; proposed after the review of the plan, awaiting the maintainer's confirmation)" | delete the clause, nine places |
| L94 to L96 | title "Decisions for the maintainer"; "each needs an answer before the phase it shapes"; "the choice this plan applies unless the maintainer objects" | "Decisions, as taken" |
| L110, L120, L130, L140, L149, L159, L168, L179, L191, L200, L221, L233, L245 | "Recommendation: ... Needed before phase X." | "Decided: ..." |
| L172 | "To decide:" | "Decided:" |
| L292 | "### (b) Defaults applied unless the maintainer objects" | "(b) Defaults applied" |
| L471, L565 | "Depends on: decisions 1 to 5 ..."; "decisions 6, 7, 8, 11, 12, 13 and 14" | delete; keep "decision 9's measurement" |
| L507, L509 to L558, L560 | the column "Waits on decision" and "36 rows wait on at least one decision" | rename "Shaped by decision"; nothing waits |
| L590 | "the decisions of part (a) all answered" | delete |
| L636, L644, L645 | "waits on decision 10"; "gets its own plan when decision 10 is taken"; "decision 10 (F2)" | decision 10 is taken: "generic, built after the round" |
| L675 | the whole row "The decisions of part (a)" | delete |
| L676 | "confirming the seven resolutions of the plan's review (R1 to R7)" | delete that clause |
| L760, L768, L779 | "after decision 10"; "D11 | What the runtime is | not decided"; "N4 | ... | not decided | keep as a decision" | "decided: generic"; "decided: two passes" |
| L808 | the risk "A decision of part (a) arrives late and blocks a lane" | delete the row |
| L850 | "if the decisions of part (a) are answered at the start" | delete the condition |

Still open, and correctly so: where the built image is stored (L140, L676: two options and no recommendation; B1 cannot finish without it); one or two grading passes after the pilot (L120, decided at D4); the option of decision 9, after its measurement (L191); the maintainer's own actions of L440.

---

## 8. Nits

28. A6 is a gap in phase A's numbering (L426 explains it); C0.9 sits before C0.8 in the table.
29. Phase B leaves the version at 4 while the harness changes (section 6, item 11).
30. L603: "`core-skill-creator` last" inside a batch whose eight skills run at once; say "started after the other seven are recorded" or drop it.
31. L574 against L584 on which fingerprint value is the round's.
32. L579: "run again on the skills it touched".
33. L842: phase C's "3 to 5 days" against four L rows in lane 2.
34. L438: "consistency S12" beside backlog S12.
35. L827 omits "a new requirement class" among what stales `core-orchestrator`.
36. L686: the dated-fixture backlog item does not name its skills (`brand-profile`, `mkt-content-plan`, `mkt-publish`).
37. L614: the failing record "keeps its failing record": say that the batch's pull request carries it, since L605 says it carries "the records of the skills that passed".
