# Internal-consistency review of `docs/architecture/final-plan-2026-10-02.md`

Read-only review, 2026-10-02. All 815 lines read. Line numbers are those of the plan. Checked against `evals/eval_status.py`, `skills/*/SKILL.md` frontmatter, `contracts/environment.md`, `providers/`, `docs/backlog.md` and `audit-2026-10-02/platform-inventory.md` and `harness.md` where a reference had to be verified.

Severity: **blocker** = would cause rework or a second round; **should-fix**; **nit**.

What was verified and is consistent (not findings): the 48 rows sum to 4 S, 33 M, 11 L; 15 stale; the "Waits on decision" counts of line 527 (14, 12, 12, 6, 5, 3, 1; 36 + 12); 15 targeted cases in 12 skills; 141 + 15 = 156, 141 + 46 = 187, 46 - 15 = 31; 3,120 / 2,820 / 3,740 / 1,692 runs; 39 and 44 hours; the 5 batches hold each of the 48 skills once; backlog map 101 rows and 82 triaged; defaults 51, 59 (four skills), 63, 66, 73 match their rows; harness letters A to M and backlog Q1 to Q11 exist.

---

## Blockers

### B1. The freeze fingerprint covers `shared/references/`, and decision 14c puts platform references there and says adding one stales nothing

- Line 270 (default 21): "`shared/references/` is covered by the measurement fingerprint, since every run gets a copy of it and no skill's hash sees it".
- Line 431 (B10): the fingerprint is "the hash of the grading template, every file of `evals/container/`, the two `run-prompt.sh`, `measurement.json` and `shared/references/`; `validate.py` recomputes it and fails when it differs".
- Line 588: the check "fails any change to ... the shared references, until the version is raised (which stales all 48)".
- Line 789, under "What would make a second round necessary": "`shared/references/`, which every run receives".
- Against line 257 (14c): "`shared/` is outside a skill's folder, so adding a reference makes no skill stale ... Adding a platform runs only that platform's cases", and line 246 (14b rule 3): "only that platform is measured".

As written, adding or editing `shared/references/platforms/<p>.md` after the round fails `validate.py` and CI until the version is raised (all 48 stale). The two mechanisms (global fingerprint, per-platform reference hash in the record) both claim the same folder.

Smallest edit: in default 21, B10, line 588 and line 789 write "`shared/references/` except `platforms/`"; add to 14c "a platform reference is outside the fingerprint; its hash is in the per-platform section of the record (B7a)". Add "a platform reference added or changed" to the list of line 794 (costs that platform's cases only).

### B2. A platform-tagged case lives inside the skill folder, whose hash includes `evals/`: adding a platform does stale the skill

- Line 17: the skill folder includes `evals/`; "Its content hash leaves out `scripts/tests/` and the record itself". Confirmed in `evals/eval_status.py:32-33` (only `evals/result.json`, `scripts/tests/`, bytecode are left out; `evals/evals.json` and `evals/files/` are hashed).
- Line 257: "A case may carry `"platform": "<name>"` ... Adding a platform runs only that platform's cases." Line 428 (B7a): "`eval_run.py --platform <name>` runs only that platform's cases and merges them into the record".
- Line 246: adding a platform "never edits a skill's procedure, and only that platform is measured".
- Line 794 already says "a new case for one skill" costs that skill's full measurement, and line 587 makes `--strict` require "that skill's new record, measured alone" for any change to a skill folder.

A new tagged case in `skills/<name>/evals/evals.json` changes the hash, the skill reads `stale`, and CI (strict) demands a full iteration of up to seven skills per platform added: the opposite of 14c. The partial merge of B7a also contradicts the definition of a record as "the result of a complete iteration" (line 22) and B5 "a record is written only from the configured values".

Same problem for the script data: line 255 says scripts "read a platform's rules from a data table" without saying where the table is, and line 472 points to `platform-inventory.md` sections 1 and 2, whose section 2 defines it as "`platforms.json` beside the script" and the reference as "one source and generated copies". Beside the script = inside the hash = a new platform edits seven skill folders.

Smallest edit: in 14c and B7a state that (a) platform-tagged cases and their fixtures live outside the content hash (for example `skills/<name>/evals/platforms/<platform>/`, left out of the hash like `scripts/tests/`, with the per-platform section of the record carrying their own hash), (b) the data table a script reads is part of `shared/references/platforms/<platform>` (the script takes its path), never a file in the skill, (c) the per-platform section of a record is the one named exception to "a record is a complete iteration". In line 472 add "sections 1 and 2 are read for the line numbers only; where section 2 says generated copies or a table beside the script, decision 14c holds".

---

## Should-fix

### S1. C0.2 now edits skill folders and most of `providers/`, but is still sized S, lists two files, and sits under "touch no skill folder"

- Line 450 (C0.2): Touches "`contracts/environment.md`, `scripts/validate.py`", size S.
- Line 240 (14a): the rename covers the folders under `providers/`, `providers/resolve.py`, its variables, `scripts/doctor.py`, `providers/CONTRACT.md`, "the orchestrator's `requirement-classes.md` and the two skills that declare a bare class ... in one change ... Done in C0.2, before any skill is edited".
- Line 459: "C0.1 to C0.7 touch no skill folder and can be built beside phase B."

In the repository the rename reaches `skills/mkt-engage` (`requires: [mailbox, ...]`), `skills/mkt-publish` (`requires: [..., scheduler]`), `skills/core-orchestrator/references/requirement-classes.md`, `skills/core-security-audit`, `scripts/runtime_vote.py`, `contracts/runtime.md`, `contracts/secrets.md` and about ten test files. It also breaks "each skill edited once" for three or four skills.

Smallest edit: C0.2 Touches gains `providers/`, `scripts/doctor.py`, `scripts/runtime*.py`, `contracts/runtime.md`, `contracts/secrets.md`, `AGENTS.md` (Layout line `providers/<class>/<impl>.py`) and "the frontmatter and class mentions of four skills"; size M; line 459 reads "C0.1 to C0.7 touch no skill folder, except the class rename of C0.2".

### S2. Default 52 says a skill is never the source of a shared script; rows 6, 8 and 47 make a skill the source

- Line 307: "the source of every shared script is `shared/scripts/`, never one of the skills that use it".
- Line 483 (row 6): "`sensitive_topics.py` becomes the source of generated copies in three marketing skills". Line 485 (row 8): "`voice_stats.py` ... becomes the source of a generated copy in `mkt-social-copy`". Line 524 (row 47): "`check_post.py` ... becomes the source of the copy in `mkt-vote-round`".
- Line 451 (C0.3) lists the three among the families of `shared/scripts/`.

Smallest edit: in the three rows write "becomes a generated copy of the source in `shared/scripts/`, as do the copies in ...".

### S3. B2 stages the whole of `shared/` into every run, but only `shared/references/` is fingerprinted and `shared/scripts/` will hold script sources and their tests

- Line 422 (B2): the runner stages "the skill under test and its dependencies ... and `shared/` into the case folder".
- Line 451 (C0.3): "`shared/scripts/` as the one source, with its tests".
- Line 431 (B10): the fingerprint covers `shared/references/` only.

Every run would see a second copy of scripts it also has as generated copies (the audit's own finding "a second copy of the skill", line 74), plus tests no model should read, and a later change to `shared/scripts/` would change what every run sees with no check noticing.

Smallest edit: B2 and default 31 say "`shared/references/`" instead of "`shared/`"; F3 and C0.9 likewise.

### S4. Two generated prose copies in the orchestrator vs 14b rule 3 and the "one skill's measurement" list

- Line 451 (C0.3): "two prose copies for the orchestrator (the requirement-class table and the table of owners)"; line 489 (row 12).
- Line 246: adding a platform "never edits a skill's procedure, and only that platform is measured". Line 794: only "a planned skill that gets built (plus the orchestrator, once per batch)".

The class table today lists platforms by name (`requirement-classes.md:13`: "`publisher:linkedin`, `publisher:x`, `publisher:blog`"; `contracts/environment.md:15`). If the copy keeps examples, a new platform regenerates the copy and stales `core-orchestrator`. The owner table is regenerated whenever any skill's `outputs` or `updates` changes, which also stales the orchestrator.

Smallest edit: C0.2 writes the `publisher:<platform>` row with no platform examples; line 794 gains "a change to any skill's `outputs` or `updates` also stales `core-orchestrator`".

### S5. Rows and items that the narrowed decision 11 makes false and that the caveat of line 196 does not cover

The caveat covers only the phrases "rewritten as fiction", "invented numbers" and "without the numbers of a case (decision 11)". Not covered:

- Line 481 (row 4): "the template's palette made neutral if it is a real project's (decision 11)" against line 196: "the palette of `brand-identity` ... stay as they are", with the maintainer's answer that it most likely is real. Edit: delete the clause from row 4.
- Line 519 (row 42): "the lines that name this repository, a date and a count leave the skill". Edit: "the lines that name this repository leave; the date and the count stay".
- Line 518 (row 41): "one gotcha without the date of a case"; line 492 (row 15): "the history numbers of the first audit made general"; line 495 (row 18): "loses the dated lessons of one case". Edit: add these three phrases to the caveat sentence of line 196, or delete them.
- Line 457 (C0.8): "the 'Dana' ... fixtures (reserved hosts, dates, the schedule, the author's name)" and line 520 (row 43): "the schedule of the shared fixtures (decision 11)". The schedule is numbers and dates. Edit: drop "the schedule" from both; keep "dates" in C0.8 only as "(decision 6)".
- Line 480 (row 3): "the shared brand fixtures (hosts, product name) per decision 11" against line 196 "the shared product name is already a replacement" while line 188 says it "is also a real open-source project's name". The plan never says whether it is replaced. Edit: one sentence in line 196, item (1): the shared product name is or is not replaced.
- Line 413 (phase A exit): "no document outside `docs/architecture/audit-2026-10-02/` that carries one real case's names, dates or numbers". Edit: "names, people, accounts or other identifiers".
- Line 643 (phase H): "the three questions of fact of decision 11" still waits on the maintainer; line 196 records the answers. Edit: delete from the row.
- Rows 29, 30, 33 and 42 cite decision 11 in "Changes" and have "none" or "8" under "Waits on decision"; line 527's "decision 11 shapes 14 rows" is therefore 18 by the table's own text. Nit, moot now that it is decided.

### S6. Phase E exit and default 34 require `validate.py --strict` green, while the repair loop lets the round close with `draft` skills

- Line 581: a skill that still fails "keeps its failing record, reads `draft` ... The round then closes with fewer than 48 `evaluated`".
- Line 587: "`validate.py --strict` becomes the CI default: a stale or draft skill fails the `validate` check."
- Line 594 (exit): "48 skills `evaluated` (or the number reached and the listed `draft` skills ...), `validate.py --strict` green on `main`". Line 286 (default 34): "Done when" is 48 `evaluated` and strict green.

With one `draft` skill strict cannot be green, so the exit cannot be met and CI on `main` stays red.

Smallest edit: line 581 adds "it is listed in the gate file's `known_draft` list (or leaves `packs/default.txt` and the strict check), which `--strict` accepts"; default 34 reads "48 `evaluated`, or the listed exceptions".

### S7. `--strict` at the end of phase E also turns every A5 warning into an error; phase C's exit does not require them cleared

- Line 402 (A5): about eighteen rules "added as warnings first"; only the contract rules (C0.1) and the two vocabulary rules (C0.2) are said to become errors. Line 351 (default 90): "a warning for AI and design-tool names in eval cases".
- Line 541 (D1) assumes "the only warnings left are the 48 stale skills"; line 533 (phase C exit) does not say so.
- 14c adds a per-platform `not measured` and `stale` state (line 257) and the plan never says whether `--strict` fails on it.

Smallest edit: phase C exit gains "no warning of A5 is left, or the rule is named as one `--strict` ignores"; 14c says "a platform that is `not measured` is not a strict failure; a platform `stale` is".

### S8. Refusal markers, `runs`, `timeout`, `retries`: two homes each, and `adapter.json` is outside the fingerprint that claims to cover "an eval adapter"

- Line 425 (B5): "`runs`, `timeout_seconds`, `retries`, `web_jobs` per tier ... in the gate file". Line 94 (decision 1): "written in `evals/eval-gate.json`".
- Line 431 (B10): "`evals/measurement.json` holds the constants ... (the file limit, the early-end phrase lists, runs, timeout, retries, refusal markers)".
- Line 429 (B8) and line 274 (default 25): "refusal markers moved from the runner's code to each adapter's data" (`adapters/*/adapter.json`).
- Line 588: the fingerprint "fails any change to ... an eval adapter"; B10 hashes only "the two `run-prompt.sh`".

Smallest edit: B10 reads "`measurement.json` holds the file limit and the early-end phrase lists; runs, timeout and retries are in the gate file (B5) and are covered by the record (B7); the fingerprint also hashes the two `adapter.json`, which hold the refusal markers".

### S9. C0.9 and B7a are placed in no order, and C0.9 changes a fingerprinted folder after the point where phase B freezes it

- Line 456: C0.9 sits between C0.7 and C0.8. Line 459: "C0.1 to C0.7 touch no skill folder and can be built beside phase B." Line 529: "Order: C0.1 to C0.7 first. Then six lanes". C0.9 is in neither sentence, yet the lanes of groups 1 and 6 need the first reference and the templates' literal step before they edit the seven skills.
- Line 436 (phase B parallel list) names B1 to B11 and omits B7a, which shares `eval_run.py`, `eval_status.py` and the record with B5 and B7. Line 438: phase B "Depends on: decisions 1 to 5" (B7a depends on 14c).
- Line 417: "After its last commit nothing in `evals/` ... changes until the round is recorded"; line 432: B11 writes the fingerprint. C0.9 adds files under `shared/references/` and C0.7 adds `evals/README.md` (line 455), both possibly after B11. `validate.py` then fails on the fingerprint (if B1 above is not applied) in the middle of phase C.
- Line 437: "Size: 7 M and 4 S"; with B7a the table has 8 M and 4 S (line 805 says 8 M). Line 531: "C0 is 4 M and 4 S"; with C0.9 the table has 5 M and 4 S (line 806 says 5 M), 6 M and 3 S after S1.

Smallest edit: renumber C0.9 before C0.8 in the table; lines 459 and 529 read "C0.1 to C0.7 and C0.9"; line 436 adds "B7a after B7"; line 432 (B11) adds "B11 merges after C0.7 and C0.9; D1 recomputes the fingerprint once more"; fix the counts of lines 437 and 531.

### S10. Installing `shared/` is planned twice, before and after the round

- Line 258 (14c) and line 456 (C0.9): "the installers copy `shared/`", Touches `adapters/*/install.sh`, before the round.
- Line 280 (default 31): "Installers install the stripped copy the evals use, with `shared/` beside it, after the round". Line 604 (F3): the same.
- Line 258 also says "(today only the eval adapters copy it)", while B2 (line 422) removes that code from the adapters.

Smallest edit: default 31 and F3 read "the stripped copy; `shared/references/` is already installed by C0.9"; line 258 drops the parenthesis or says "until B2".

### S11. Default 57 and row 44 still describe the parser and the class the old way

- Line 312: "`mkt-engage` drops `mailbox` from `requires` ... its parser takes `--platform` with one platform implemented". Line 521 (row 44): "`mailbox` leaves `requires`"; "`parse_notification.py`: `--help`, `--platform`, an exact host check".
- Line 255 (14c): "Scripts take `--platform` and read a platform's rules from a data table, never from code." Line 235 to 236: `mailbox` is `reader:email` after C0.2.

Smallest edit: "drops `reader:email`"; "its parser takes `--platform` and reads the hosts and patterns from the platform's table; one platform has a table".

### S12. Default 35 and 14b rule 2 give `AGENTS.md` two overlapping rules about names, added by two different items

- Line 287 (default 35): a third-party product that is not an AI tool "may be named in prompts, fixtures, credential-format labels and detection lists". Line 401 (A4) writes it "next to principle 1".
- Line 245 (rule 2): "A skill's procedure names no social platform"; line 255: platform rules never in code. Line 456 (C0.9) writes it into `AGENTS.md`.
- A host check or URL pattern of a social platform is a "detection list" under 35 and forbidden in code under 14c.

Smallest edit: default 35 gains "except a social platform's rules, which live in its platform reference (decision 14c)"; A4 leaves the product-name rule to C0.9 so that `AGENTS.md` gets both in one edit.

### S13. `brand-name` is one of the seven skills of 14c and is also exempted from it

- Line 256: scope is seven skills including `brand-name`; "`brand-name`'s list of networks to check stays a table inside that skill."
- Line 472: in all seven "the platform knowledge leaves the body and the scripts for the platform reference".
- Line 246: adding a platform "never edits a skill's procedure".

A new platform edits `brand-name`'s table (inside its hash). Smallest edit: line 246 adds "(`brand-name`'s table of networks is the one exception: a row added there stales that skill)"; line 472 says what leaves `brand-name` and what stays.

### S14. `core-skill-creator` is staled by files that line 796 says cost nothing

- Line 269 (default 20): `workbench_files` are hashed into the record. Line 493 (row 16): "`AGENTS.md` joins `workbench_files`", the scan is brought the same way.
- Line 796: "These cost nothing: ... everything under `providers/`, `scripts/`, `contracts/`, `templates/`, `docs/`".
- Line 603 (F2): "`AGENTS.md` 'Adding an adapter' corrected (N11, PB8)" after the round, with no note; phase G and F1 will also edit `AGENTS.md`.

Smallest edit: line 796 adds "except a file a case brings through `workbench_files` (`AGENTS.md`, the security scan, the harness files): a change there stales `core-skill-creator` alone"; F2's note says so.

### S15. F6 changes the measurement after the freeze without saying so

- Line 607 (F6): "the floor tier's usage read from the provider when the runner cannot print it".
- Line 598: "Nothing here changes a skill folder or a frozen file; where an item would, it says so". Line 274 (default 25) moved two comparable items into phase B "because they change frozen files"; B8 (line 429) already holds the other half ("token use recorded when it can print it").

Smallest edit: move the second half of F6 into B8, or add to F6's note "done in `eval_run.py` only, which the fingerprint does not cover".

### S16. Web cases are "serialised" in three places and run two at a time in a fourth

- Line 268 (default 19): "serialised by the runner"; line 369; line 777.
- Line 559: "the number of concurrent web runs per tier (2 on the floor tier)"; B5 `web_jobs` per tier.

Smallest edit: default 19 and line 369 read "limited by the runner (`web_jobs` per tier)".

### S17. B7a's record path is exercised by no proof run and no pilot

- Line 428: B7a "Needs a proof run: no". Line 434 and line 543: neither the proof run nor the pilot can write a record ("2 is below the configured number of runs").
- The per-platform section of the record and the gate "computed on its untagged cases and on the platforms measured" (line 257) are first executed in the round, where line 578 says an instrument defect stops the round and re-measures everything.

Smallest edit: D2 adds "the record of one tagged skill is built from stub runs and read back by `eval_status.py`".

### S18. Effort and size counts that do not match the tables

- Line 411 and line 804: phase A "4 M and 5 S". The table has 3 M (A2, A3, A5) and 6 S.
- Line 611 and line 810: phase F without the runtime "3 M and 2 L". The table has 4 M (F1, F3, F5, F6) and 2 L (F4, F7).
- Lines 437 and 531: see S9.
- Line 815: "about 40 to 62 working sessions"; the column sums to 39 to 60 for A to E.

### S19. Default 67's contract file has no item that creates it

- Line 322: "The vote data files `mkt-vote-round` reads become a contract under `contracts/`". Only row 48 mentions it, as body text ("described as a contract"); no C0 item touches a new file under `contracts/`.

Smallest edit: add the file to C0.1's Touches, or word default 67 as "described in the skill".

---

## Nits

- **N1.** Line 3: "awaits the maintainer; nothing in it is decided". Lines 80, 260 ("unless the maintainer objects"), 532, 557, 642 and 775 still treat decisions as open. One status line under line 78 ("all of part (a) as recommended and all of part (b) approved on 2026-10-02") resolves all of them; decision 2's "may drop to one pass" (line 104) should say the drop is decided at D4, before D's exit fixes the fingerprint (line 551).
- **N2.** Line 775: "C0 and phases A and B do not wait on decisions 6 to 14" against C0.1 "decisions 7 and 8", C0.5 "decision 13", C0.8 "decisions 6 and 11".
- **N3.** Line 311 (default 56) and line 450: "sub-class", "the placeholder sub-class of `publisher`". After 14a the word is "target". Also `providers/secrets/` is not a class and has no role; say whether the folder rule applies to it.
- **N4.** Backlog map T20 (line 699): "done, archive" with no word that 14a reverses its entry "requirement classes are not renamed" (`docs/backlog.md:195`; `contracts/environment.md:21` says the same). A2 moves done items "as they are". Add "its entry on class names is marked reversed (decision 14a)" to T20's row and `contracts/environment.md` line 21 to C0.2. No item records 14a to 14c in `docs/decisions.md`.
- **N5.** Line 196: sizes fall "`mkt-messaging` from L to M for this part, `design-brief` from M to S"; rows 45 and 17 still read L and M, and line 472 adds an S or M to seven rows without changing them. The counts of line 527 are therefore of the rows before the amendments; say so.
- **N6.** Line 646: S16 goes to "phase F, as a provider item"; phase F has no such lane.
- **N7.** Line 314 (default 59) leaves the origin clause out of 26 self-checks while line 790 lists "a new canonical sentence" among what costs a second round and line 10 says everything known is fixed before the round. Either state it is accepted for good, or apply it.
- **N8.** Line 320 (default 65): `flow-fix-bug`'s case "lists that skill as a dependency"; row 38's **K** (line 515) does not carry it.
- **N9.** Line 451 (C0.3) makes `redact.py` a family of `shared/scripts/`; A6 (line 403) and `AGENTS.md` name `scripts/redact.py` as the shared file. Say which is the source.
