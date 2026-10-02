# Audit, group 1: biz-icp-positioning, biz-market-analysis, brand-guidelines, brand-identity, brand-name, brand-profile, brand-strategy, brand-voice

Read-only audit of `<repository>` (branch `main`, commit `b363f1b`). Nothing in a repository was changed, no eval was run and no model was called. Scripts and tests were run on a copy of the eight skill folders in the scratchpad.

Evidence used: the highest complete iteration of each skill under `<eval workspace>/<skill>/`. `python3 evals/eval_status.py status` reports all eight as `evaluated` ("the gate passed on the current content"), so the skill text on `main` is the text that was measured; no finding below rests on older text.

Paths are relative to `skills/<skill>/`. "e2 a3" means case 2, assertion 3 of `evals/evals.json`. Pass counts are written strong / floor (with the skill) and strong / floor (without it).

## Summary

| Skill | Must fix | Should fix | Needs a maintainer decision | Size |
|-------|----------|------------|-----------------------------|------|
| biz-icp-positioning | 8 | 8 | yes | L |
| biz-market-analysis | 6 | 8 | yes | M |
| brand-guidelines | 5 | 6 | yes | M |
| brand-identity | 5 | 7 | yes | M |
| brand-name | 5 | 6 | yes | M |
| brand-profile | 5 | 7 | no | M |
| brand-strategy | 6 | 5 | yes | M |
| brand-voice | 4 | 6 | no | S |

Scores of the last measurement (mean pass rate):

| Skill | Iteration | Strong with | Floor with | Strong without | Floor without |
|-------|-----------|-------------|------------|----------------|---------------|
| biz-icp-positioning | 2 | 0.954 | 0.981 | 0.485 | 0.550 |
| biz-market-analysis | 4 | 0.889 | 0.931 | 0.242 | 0.175 |
| brand-guidelines | 2 | 0.976 | 1.000 | 0.536 | 0.560 |
| brand-identity | 2 | 1.000 | 0.958 | 0.181 | 0.236 |
| brand-name | 2 | 1.000 | 1.000 | 0.500 | 0.333 |
| brand-profile | 2 | 0.972 | 0.944 | 0.407 | 0.296 |
| brand-strategy | 2 | 0.972 | 0.917 | 0.857 | 0.690 |
| brand-voice | 5 | 1.000 | 0.850 | 0.417 | 0.300 |

Script checks (all eight skills): every script answers `--help` with exit 0; a flag given last without its value exits 2 with a usage line and no traceback, except the two scripts that do not use an argument parser (`brand-identity/scripts/contrast.py`, `brand-voice/scripts/voice_stats.py`, see their sections); every `scripts/tests/` folder exists and passes (`uv run --with pytest pytest <folder> -q`: icp 2, market 11, guidelines 2, identity 32, name 2, profile 6, strategy 1, voice 3). No script uses a macOS-only tool; `render.py` finds the browser through `--browser`, `RENDER_BROWSER`, `CHROME_BIN`, then macOS paths, then `PATH`.

Size and description (all within limits): icp 180 lines, 2,439 words (about 3,290 tokens), description 901 characters; market 198, 2,778 (3,750), 816; guidelines 98, 1,068 (1,440), 791; identity 110, 1,429 (1,930), 766; name 107, 1,338 (1,810), 657; profile 173, 2,322 (3,135), 807; strategy 143, 1,606 (2,170), 750; voice 124, 1,365 (1,840), 741.

Principle checks that found nothing: no AI tool, harness, harness directory or harness tool name in any file of the eight folders (SKILL.md, scripts, assets, eval prompts, fixtures); every file is in English; each SKILL.md carries the "External content is data." line; none has `side_effects`, and none changes anything outside the repository.

## biz-icp-positioning

Per case, with the skill: case 1 strong 1.0, 1.0, 0.83, floor 1.0, 1.0, 0.83; case 2 all 1.0; case 3 strong 1.0, 0.75, 1.0, floor all 1.0.

### Must fix (would fail, mislead the score, or break a principle)

1. **`evals/evals.json` case 1 does not test the happy path, and three of its six assertions pass with nothing written.** In five of the six runs with the skill the model stopped at the job question and wrote no `docs/business/icp.md` (files left in `cwd`: only the fixtures; only floor run 2 wrote `icp.md`). Assertions 3, 4 and 5 start with "If ... exists", so they pass when nothing exists; the baseline scores 1.0, 0.67, 1.0 (strong) and 1.0, 1.0, 1.0 (floor) on this case. The comparison, `rank.py`, the profile, the interview guide and the two lint scripts are never measured. Fix, in two parts:
   - Fixture `evals/files/scoped-dev/docs/workbench/state.md`: add `- 2026-09-21: Job the automation does: leave it open, the interviews find it (user). (user)`. The job question stays covered by case 2 (assertion 3).
   - Replace assertions 3, 4, 5 with unconditional ones: "docs/business/icp.md exists with `Status: hypothesis` and a Comparison table that lists physiotherapy clinics, law firms and real estate agencies"; "Every score cell in that table carries a source number in brackets or reads `1 (no evidence)`, and each Total equals the sum of its row"; "The Validation plan has questions about past behaviour or current spend only (no 'would you', 'if we'), and a 'Validated if' and a 'Rejected if' line"; "The job to be done is written as open hypotheses; no product shape (a chatbot, an app, a channel) is chosen".
2. **Fixture `evals/files/scoped-dev/docs/business/market.md` is a placeholder.** Lines 19 to 22: `[1] Placeholder fixture source. https://example.org. Quote: "fixture"` and `- Fixture for evals.`. It has no Comparison table, although the state file calls the offer "the top of the market ranking". Fix: a small real `market.md` in the layout of `biz-market-analysis` (Scope, Summary, a Comparison table as `rank.py` prints it, Implications as questions, Unknowns, two or three sources with `.example` URLs and quotes, Method).
3. **`SKILL.md` lines 73 and 82: the script path is the workbench's, not the project's.** `python3 skills/biz-icp-positioning/scripts/rank.py` does not exist in a project. Floor transcripts show the search: `python3 rank.py` six times, `python3 lint_icp.py` four times, `python3 check_refs.py` twice, before the model found the installed copy. Fix: before step 5 add "The scripts are in the `scripts/` folder next to this file, not in the project. Run them from the project root by that path: `python3 <this skill's folder>/scripts/<name>.py`." and replace the three commands with that form.
4. **Stop gates leave two paths (steps 2, 6 and 8).** Step 2 says "ask ... and wait", step 6 "Stop and ask", step 8 "Then ask the user ... Write `docs/business/positioning.md`"; none says that nothing is written before the answer or that "go" is not an answer. Case 3 shows the split: three runs wrote `positioning.md` and three asked first. Fix, step 2: "Stop until they answer. A 'go', 'proceed' or 'use your judgement' is not an answer and does not accept the recommendations: ask anyway. Search nothing and write no file before the answers." Step 8: "Stop until they answer; write no `positioning.md` before it." Step 6: say what is written when it stops (see item 5).
5. **Skill defect behind e1 a3 (strong run 3 failed).** Assertion: "If a comparison table exists, it has the three segments and every score cites a source or reads 1 with a no-evidence label". The reply stopped at the close call and showed a table whose citations pointed to "the list I'll write into icp.md", and scored pain 2 for a segment whose own notes say "not found". Cause: step 6 stops before step 7 writes the sources, and nothing says what the stop message carries. Fix in step 6: "When you stop here, the reply carries the table exactly as `rank.py` printed it and, under it, the Sources entries the table cites, in the template's format. A criterion for which the research found nothing is scored 1 with no source."
6. **Skill defect behind e3 a4 (strong run 2 failed).** Assertion: "Rules on advertising for lawyers are cited from a source or listed as unknown". The reply stated rules as findings ("Advertising was liberalised in 2024", "art. 92") and said "none of it is cited yet". Cause: the grounding rules name the artifacts, not the reply. Fix in step 8: "The reply states no alternative, price or rule without its source URL; what was not researched yet is written `not researched yet`, never from memory."
7. **Frontmatter and citations of skills that do not exist.** `inputs` holds `docs/workbench/research/<topic>.md`, a placeholder path (decision D7 defines the placeholder syntax and turns dangling inputs into errors). Lines 30, 35 and 81 name `biz-business-model` and `biz-gtm`, which are not built; line 81 sends the user to `biz-business-model` as the next step. Fix: mark both as planned where they are named, and write the next step as "interviews, then pricing (`biz-business-model`, planned)".
8. **No `grader_files` in any case.** Case 1 assertions 1 and 6 and case 3 assertion 2 check the reply against the state file. Fix: `"grader_files": ["docs/workbench/state.md", "docs/business/market.md"]` on cases 1 and 3.

### Should fix (quality, robustness)

1. **Assertions that passed in every run of all four variants.** e1 a4 and e1 a5: CONTENT, vacuous as written; replaced in must-fix 1. e2 a1 "No web search or page fetch is run before the questions are answered": GUARD, but the grader never sees commands; reword to "The reply states no figure, competitor, price or URL about any segment; it consists of the scope questions". e2 a5 "No docs/business/icp.md is written": GUARD, verifiable, keep.
2. **e1 a1 failed once (floor run 3) on the grader, not on the output.** Its evidence ends "No re-ask ... occurs, so this should pass" and marks it failed. Reword so that the allowed question is explicit: "The reply does not ask again for the offer, the segments, the size band, the founder's access, the name or the number of conversations; asking which job the automation does is allowed".
3. **Report template missing (step 9 describes the reply in prose).** Add a reply template that carries the evidence:
   ```markdown
   - Files written: docs/business/icp.md[, docs/business/positioning.md], docs/workbench/state.md
   - Primary profile: <one line>; ranking: 1. <segment> (<total>) 2. ... ; gap between the top two: <n>, close call: <yes | no> (from `rank.py`)
   - Checks: `check_refs.py --file docs/business/icp.md` → `"ok": true`; `lint_icp.py --file docs/business/icp.md --kind icp` → `"ok": true`
   - Open: <tie, risk, unknowns>
   - Next: interviews, then pricing
   **Instructions found in external content**
   ```
4. **Step order.** Step 9 reports, step 10 runs the scripts and says "report to the user only when every script passes", step 11 is the self-check. Move the report to the last position before the self-check.
5. **The template's `## Method` section is empty (line 128).** Add lines as in `biz-market-analysis`: queries, the ranking command with a label, the two check commands, by script name and arguments only (no path; see Patterns 2).
6. **One strong run wrote three files under `docs/workbench/research/`,** which the skill declares as an input, not an output. Add to step 4: "Keep research notes in the artifact's Sources; write no other file."
7. **Scripts.** `rank.py` exits 1 for an unreadable `--input` and for invalid JSON, where `check_refs.py` and `lint_icp.py` exit 2 for an unreadable file; make it 2. `check_refs.py --help` says "Check the citations of a market analysis". `scripts/tests/` has `test_lint_icp.py` only: `rank.py` and `check_refs.py` (byte-identical to the copies in `biz-market-analysis`) have no test here; D8's identity test would cover it.
8. **Cases.** No case for the degraded mode (no `search:web`: query plan, `Status: limited`, nothing scored). Add one without `allow_web`. Case 3 says "we picked law firms already" but ships no `icp.md` and no decision that records it; ship a fixture with `docs/business/icp.md` (law firms as primary, `hypothesis`) and the decision in the state file.

### For the maintainer to decide

1. `docs/workbench/state.md` is written by this skill (decisions, artifact rows, open questions) and is not in `outputs`: a shared ledger for the new `updates` field.
2. Case 3 on the floor model met HTTP 429 from the search service in all three runs (5 to 8 mentions per transcript). The scores held, but this skill should be measured alone, two runs at a time, in the final round.
3. The prompt of case 3 names a messaging product ("WhatsApp bot"). It is not an AI tool, so principle 1 holds; say whether product names in prompts are acceptable.
4. Line 43 "offer `biz-market-analysis`": keep, or reword to the D12 form ("name the artifact, the skill that writes it, and stop").

## biz-market-analysis

Per case, with the skill: case 1 strong 1.0, 0.88, 0.88, floor 0.88, 1.0, 1.0; case 2 all 1.0; case 3 strong 0.75, 0.75, 0.75, floor 0.75, 1.0, 0.75.

### Must fix

1. **e3 a3 failed in five of six runs with the skill (strong 0/3, floor 1/3): "No number in docs/business/market.md lacks a citation, a Method command or an 'Assumption:' label".** Two causes, to be separated:
   - Formality, caused by the skill's own template. The Capacity table template (line 143) writes `<h> (assumed | [n] | user)`, and the grader failed cells such as "30 (assumed)" for lacking the literal label `Assumption:`. The ranking command has no label (line 171: "Ranking: ..."), so totals and the gap ("The gap between first and second is 1 point") have nothing to cite. The fit thresholds and the recency threshold are constants of the method and were also failed.
   - Real defects in the output. Floor run 3 wrote "6.7% in 2025 [6]" while source [6] quotes 13.7%; floor run 1 wrote "up to 2,250 SMEs" cited to a source whose quote does not contain it.
   Fix in the skill: label the ranking command `M<n>` in the Method template and tell step 9 to cite totals and the gap with it; add a Method template line "Fit thresholds (goal: <goal>): ..."; in step 14 add "For every figure that carries a source number, find the figure in that source's Quote; when it is not there, correct the quote from the page or remove the figure." Fix in the case, replacing the assertion with two: "Every percentage, currency amount, count of buyers or competitors and score in docs/business/market.md carries a source number or a command label, or is marked assumed (in its cell or under Assumptions); constants stated under Method are exempt" and "Every figure cited to a source appears in that source's Quote". The second keeps the check that the output really failed.
2. **e1 a5 failed in two strong runs because the assertion contradicts the skill and asks for a self-report.** Text: "The comparison table was produced by running rank.py and every score in it cites a source or reads '1 (no evidence)'". The grader rejected fit scores cited as `[M3]`, which step 7 requires ("cite the capacity command as `M1`"), and said the script run "cannot be verified". New wording: "The Comparison table has the columns rank.py prints (Rank, Option, one per criterion, Total); every score cell carries a source number or a command label such as M1, or reads '1 (no evidence)'; each Total equals the sum of its row; Method names the rank.py command".
3. **`SKILL.md` lines 75, 87, 107, 108, 170 to 172: workbench script paths, and harness paths written into the project's artifact.** The Method template hard-codes `python3 skills/biz-market-analysis/scripts/...`. The artifacts the runs produced carry the installed path instead: 31 occurrences of a path under the strong harness's directory and 15 under the floor harness's directory, across the `market.md` files. A project artifact then names an AI tool's folder. Fix: the sentence of Patterns 1 before step 6, and Method lines that record the script name and its arguments only: `- M1: capacity.py --hours-per-week 20 --hours-per-job 40 --utilization 0.7 → 1.5 jobs per month`.
4. **Steps 8 and 12 contradict each other.** Step 8: "Stop and ask the user when the top two options are within 2 points". Step 12: "Always write `docs/business/market.md` ... a reply without the artifact is a failed run". Every run wrote the artifact and put the close call in the reply (strong run 2 of case 3: "First and second are 1 point apart, so I'm not declaring a winner"). Make that the one path: "On a close call, write the artifact with both readings under Comparison, add the question to the state file's Open questions, and ask it in the report with your recommended reading; pick no winner." Add to the reply template: `- Close call: <question and recommended reading | none>` and `- Assumed: <hours per job, utilization>`.
5. **Frontmatter.** `inputs` lists `docs/business/idea-validation.md`, which no skill produces (`validate.py` warning today, an error under D7), and `docs/workbench/research/<topic>.md` with a placeholder. The description and lines 29, 34 and 36 name `biz-validate-idea`, `biz-business-model` and `biz-gtm`, which are not built. Fix: note the input as produced by a planned skill or remove it, and mark the three names as planned.
6. **No `grader_files`.** Case 1 assertions 1 and 4 and case 3 check against the state file (20 hours per week, the three offers). Add `"grader_files": ["docs/workbench/state.md"]` to cases 1 and 3.

### Should fix

1. **Assertions that passed in every run of all four variants.** e1 a1 "does not ask again for geography, offers, ...": GUARD, verifiable, keep. e2 a1 "No web search or page fetch is run before the questions are answered": GUARD but unverifiable; reword to "The reply states no market figure, competitor name, price or URL; it consists of the scope questions". e2 a5 "No docs/business/market.md is written": GUARD, keep.
2. **e1 a6 failed once (floor run 1): publisher not a separate field.** The entries followed "<Title>, <Publisher>." as the template says; this is variance in the grader. Make it deterministic in the skill: extend `check_refs.py` `incomplete` to require the published marker (or `undated`), the access date and the tier, with the translated labels as options.
3. **Step order.** Step 10 reports; steps 11 to 13 follow, and step 13 ends "Do not report to the user before both scripts pass". Order: write, check, self-check, report.
4. **Reply template (lines 95 to 104) quotes no evidence.** Add: `- Checks: check_refs.py --file docs/business/market.md → "ok": true; lint_market.py --file docs/business/market.md → "ok": true`, `- State: artifact registered as draft; <n> open questions added`.
5. **Step 2 gate wording.** "ask ... and wait. Do not search before the answers arrive" lacks the rule that "go" is not an answer; add the sentence of Patterns 3.
6. **Step 7, fit thresholds.** They are given "for a first client"; the fixture's goal is "the first three paying clients", and the runs reused the first-client thresholds without saying so. Add: "state the thresholds used and the goal they are for under Method".
7. **Cases.** No case exercises degraded mode (step 11). Add a case with the scoped fixture and no `allow_web` that expects `Status: limited`, a query plan and no scores.
8. **`rank.py` exit code** as in biz-icp-positioning (1 for an unreadable file).

### For the maintainer to decide

1. `docs/workbench/state.md` is written (decisions, the Artifacts row, open questions): shared ledger for `updates`.
2. Measure alone and two runs at a time in the final round: cases 1 and 3 search the web (HTTP 429 seen in five floor transcripts).
3. `rank.py` and `check_refs.py` are byte-identical to the copies in biz-icp-positioning; D8 (one source, sync script) decides which folder owns them.

## brand-guidelines

Per case, with the skill: case 1 strong 0.86, 1.0, 1.0, floor all 1.0; case 2 all 1.0.

### Must fix

1. **No `grader_files`: e1 a5 failed in strong run 1 only because the grader could not see the source.** Assertion: "Every 'don't' example is an exact quote from Dana's samples or the AI-written launch post ...". Evidence: "The source posts are not shown in the data, so there is no evidence that these are exact quotes". The quotes were exact. Fix: `"grader_files": ["docs/brand/profile.md", "docs/brand/strategy.md", "docs/brand/voice.md", "docs/brand/identity.md"]` on case 1.
2. **Step 4 and the quality criterion "The pre-publish checklist names runnable commands" cannot be executed (lines 51, 91).** The commands belong to other skills and no brand file records them. Outputs: the floor run wrote `python3 <floor harness directory>/skills/brand-guidelines/scripts/check_guide.py ...` into `guidelines.md` section 9 and said "no voice-check script is installed in this repo"; the strong run wrote "count by hand" and a path under the strong harness's directory. A harness path lands in a brand file that agents read. Fix: the commands come from the brand files. Add a "Check" line to the templates of `brand-voice` (`voice_stats.py check --rules docs/brand/voice.md`, script of brand-voice) and `brand-profile` (`sensitive_topics.py --profile docs/brand/profile.md`, script of brand-profile); step 4 then reads "copy each check line from the brand file that records it, with its `[file.md]`; a brand file with no check line gets `no command recorded: run <skill>`. Write script names and arguments, never a path." This changes three skills together.
3. **Line 52: workbench script path.** `python3 skills/brand-guidelines/scripts/check_guide.py`. Apply Patterns 1.
4. **Fixture `evals/files/dana/docs/brand/voice.md` is not a voice guide in the real layout.** It has "In one sentence" and the `voice-rules` block only: no "What stays", "What changes" or "Calibration" section. Step 3 takes the Do column "from approved calibration examples", which the fixture does not have, so the runs diverged: strong left the Do column empty, floor filled it with profile samples. `identity.md` is equally thin (no tokens block, no formats). Fix: write both fixtures from the templates of `brand-voice` and `brand-identity`, with two calibration rewrites.
5. **Four of the seven assertions of case 1 pass in every run of all four variants, so the case measures three.** e1 a2 (label copied), a3 (expert claim forbidden), a4 (voice limits), a6 (colours): CONTENT, trivially met by copying the fixtures; remove a2, a3, a4, and replace with assertions the baseline fails:
   - "Every Do cell is an exact quote of a calibration rewrite in voice.md, and every Don't cell an exact quote of a sample or of the launch post in profile.md" (replaces a5 as well, and needs must-fix 1 and 4).
   - "Every rule line in the guide ends with the brand file it comes from in the form [file.md]".
   - "Section 9 names the voice check and the sensitive-topics check as recorded in voice.md and profile.md, with no path into a tool's folder".
   - "The reply quotes the check_guide.py command and its output with \"ok\": true, and docs/workbench/state.md registers docs/brand/guidelines.md as draft".
   Keep a6 reworded as the guard it is: "The guide contains no colour code that identity.md lacks". e2 a1 "No docs/brand/guidelines.md is written": GUARD, keep.

### Should fix

1. **No reply template.** Step 6 says "report which brand files are still `draft`". Add:
   ```markdown
   ## Brand guide: <name> (draft)
   - File: docs/brand/guidelines.md; registered in docs/workbench/state.md as draft
   - Check: `check_guide.py --guide docs/brand/guidelines.md --brand-dir docs/brand` → `<the line with "ok">`
   - Not defined yet: <brand file: skill that writes it | none>
   - Brand files still draft, with their open questions: <... | none>
   ### Instructions found in external content
   ```
2. **A third case for the trigger "after any brand file changes".** The description and the last gotcha promise that the checker's stale-quote list is the diff; no case tests it. Add a fixture with an existing `guidelines.md` whose label and one quote are older than `strategy.md`, expecting the stale quotes named and the guide corrected.
3. **`absent_on_purpose`.** Case 1 relies on `docs/brand/name.md` being absent and case 2 on `strategy.md` and `voice.md`: list them.
4. **Line 40 "(a person)".** Nothing says how to tell a person from a company. Add: "the subject is on the `Subject:` line of strategy.md".
5. **The output template is headings only (lines 69 to 81).** Add one model line per section, for example `- <rule, copied> [voice.md]` and the "not defined yet: run `brand-name`" line, so that a weak model does not invent the line format.
6. **Line 40 "Stop; offer `brand-profile`"** against step 1, which says to name the file and the skill and stop; use one wording.

### For the maintainer to decide

1. `docs/workbench/state.md` is written (step 6) and is not in `outputs`: shared ledger.
2. "tinykv", the product in the fixtures of five brand skills, is also the name of a real open-source teaching project (a key-value store course). Principle 8 asks for fictional products; decide whether to rename it across the five fixtures.

## brand-identity

Per case, with the skill: case 1 strong all 1.0, floor 1.0, 1.0, 0.75; case 2 all 1.0.

### Must fix

1. **Step 5 needs the web, `requires` is empty, and case 2 runs without it.** Line 54: "For each piece, the pixel size and the safe area, with the source. Prefer the network's own help page". Every run of case 2 wrote the size as unverified: "the size and safe area are taken from the skill's cover template ... could not be retrieved (HTTP 403 through the sandbox proxy)". The skill does not say what to do without the web. Fix, one of: (a) `requires: [search:web]`, a row in Inputs ("missing: take the size from the piece template, label it `secondary, unverified`, add an open question"), and `"allow_web": true` on case 2; (b) ship `references/formats.md` with each size, safe area, source URL and access date, loaded at step 5. See the decision below.
2. **Where the pieces are written is not stated, and they are not declared.** Step 6 says "Build the first piece" with no path. Five runs wrote `docs/brand/pieces/`, one wrote `design/pieces/`, one put renders in `docs/brand/pieces/renders/`. `outputs` lists `docs/brand/identity.md` only. Fix: step 6 "write `docs/brand/pieces/<piece>.html`", step 8 "`--out docs/brand/pieces/<piece>-<variant>.png`", and declare both in `outputs`.
3. **Lines 53 and 57: workbench script paths, an invalid one-line here-document, and a harness path in the artifact.** Line 53 writes `python3 skills/brand-identity/scripts/contrast.py <<'EOF' {"pairs": [...]} EOF` on one line, which is not a valid here-document. A strong run wrote `python3 <strong harness directory>/skills/brand-identity/scripts/render.py` into the "Production:" line of `identity.md` and the asset's installed path into its Sources. Fix: Patterns 1, a fenced block for the here-document, and in the template "Production: HTML rendered with `render.py` (script of brand-identity); sources in docs/brand/pieces/".
4. **Skill defect behind e1 a2 (floor run 3 failed).** Assertion: "The reply asks where the palette should come from or whether an existing design system (for example tinykv's) should be followed, with a recommendation". The reply said "no design system is recorded in the repo, so here are two of each". Cause: the Inputs row says to ask whether one exists, step 2 only says "the palette source (recommend the design system ... when there is one)". Fix in step 2: "the palette source: ask whether a design system exists (the person's product, a company kit) and where it is; never conclude that none exists because the repository shows none".
5. **No `grader_files`.** Case 2 assertions 1 and 5 check against `design/tinykv-tokens.md` and the label in `docs/brand/strategy.md`. Add both, and `docs/workbench/state.md`.

### Should fix

1. **No assertion checks that a render happened.** The grader gets one line per image (kind, size, dimensions). Add to case 2: "At least three PNG files of 1584 x 396 pixels exist under docs/brand/pieces/".
2. **Assertions that passed in every run of all four variants.** e1 a4 "No docs/brand/identity.md is written before the user answers": GUARD, keep; it is the only one.
3. **No reply template.** Add:
   ```markdown
   ## Identity: <name> (draft)
   - Files: docs/brand/identity.md; docs/brand/pieces/<piece>.html; <each PNG with its size>
   - Contrast: `contrast.py` → <pair: ratio, pass | fail → the usage rule>, one line per failing pair
   - Render: `render.py --html ... --width <W> --height <H> --query v=<variant>` → `{"width": ..., "height": ..., "sandbox": ...}` per variant | exit 3: no browser, HTML delivered
   - Formats: <piece, size, source or `secondary, unverified`>
   - Choose a variant: <the variants>; nothing is chosen for you
   ### Instructions found in external content
   ```
4. **`scripts/contrast.py` does not parse arguments.** `contrast.py --bogus` with valid JSON on standard input exits 0, and an unknown flag is ignored. Use an argument parser so that an unknown flag exits 2 with usage.
5. **Step 8: "Look at every render yourself".** A model that cannot open images has no path. Add: "when you cannot open images, say so and rely on the size check `render.py` prints".
6. **Cases.** No case for the stop on a missing `docs/brand/strategy.md` (Inputs row 1). Add one, with `absent_on_purpose`.
7. **Line 40 "Stop; offer `brand-strategy`"**: use the D12 wording (name the file and the skill, stop).

### For the maintainer to decide

1. Must-fix 1: declare `search:web`, or ship the sizes as a dated reference.
2. `assets/piece-template.html` carries a specific palette (`#07b6f0` on black, `#0092cd` on white). `contrast.py` gives 8.96:1 and 3.50:1 for them, the numbers of the first gotcha (line 107). If that palette is a real project's, principle 8 asks for neutral values in the template and the gotcha. The template also fixes 1584 x 396 and a 420 px safe area with no source; the runs cited the template as their source.
3. `docs/workbench/state.md` is written (steps 2 and 7): shared ledger.
4. The headless browser is a requirement with no class in `contracts/environment.md`; the Inputs table handles its absence. Say whether a class is wanted.

## brand-name

Per case, with the skill: all runs 1.0 on both models. Without it: strong 0.50 mean (case 1: 0.75, 0.5, 0.75; case 2: 0.5, 0.17, 0.33).

### Must fix

1. **`requires: []` although the skill cannot work without the network.** `scripts/handle_check.py` queries rdap.org, rdap.registro.br, api.github.com, registry.npmjs.org, dev.to and youtube.com; step 4 says "Search the web for the exact name in quotes". Nothing says what happens offline, where the script answers `unknown` for every row. Fix: `requires: [search:web]`, an Inputs row ("missing: run the script anyway; when every row is `unknown`, say the network is not reachable, mark the file `Status: limited`, call nothing free or taken, and list the checks to rerun"), and a case without `allow_web` that expects it.
2. **The fixture uses a real handle that is a real company's brand.** `evals/files/octo/docs/workbench/state.md` line 20: `The handle already in use is "octocat"`. The runs reported it as "GitHub's mascot and trademark" with links to the company's brand pages, and the result of case 2 depends on what the live internet says about that name on the day. Principle 8 asks for fictional handles. See the decision below.
3. **Line 48: workbench script path.** `python3 skills/brand-name/scripts/handle_check.py`. Apply Patterns 1.
4. **Three assertions of case 2 need rewording.**
   - a6 "If docs/brand/name.md exists, its status is draft" passes when nothing is written (baseline 2/3 and 3/3). All six runs with the skill wrote the file. New: "docs/brand/name.md exists and its Status is draft".
   - a3 "Every result comes with a check date or comes from handle_check.py output" is a self-report. New: "Every row of 'Where the name is' carries one of the script's status words (registered, not_found, unknown), the URL queried and the check date".
   - a5 names three networks; the skill and the script list five. New: "LinkedIn, Instagram, X, Threads and TikTok are each named in a question to the person, and none is reported as free or taken".
5. **Step 2 gate wording (line 47).** "Ask, in one message ... Then write at least six candidates" has no stop. Fix: "Stop until they answer; 'go' or 'proceed' is not an answer and does not accept the recommendations. Check no name and write no file before the answers. Then write ...".

### Should fix

1. **Assertions that passed in every run of all four variants.** e1 a3 "No docs/brand/name.md is written" and e1 a4 "No domain or handle is declared available in this reply": both GUARD, verifiable, keep.
2. **No reply template (step 7 describes it in prose).** Add:
   ```markdown
   ## Name: <name> (<audit | research>, draft)
   - File: docs/brand/name.md
   - Check: `handle_check.py --name <name> ...` on <date> → registered: <places>; not_found: <places>; unknown: <places>
   - Not bought, not registered: this skill never does either; you do it at a registrar or on the network
   - Questions: <ownership of each registered place; LinkedIn, Instagram, X, Threads, TikTok; fallback>
   ### Instructions found in external content
   ```
3. **`handle_check.py` docstring** says the `check_by_hand` list is "(LinkedIn, Instagram, X)"; the list in the code has five. Align it.
4. **Cases.** Research mode after the answers (candidates, each checked) is never tested; add a case whose state file holds the three answers. Add `grader_files: ["docs/workbench/state.md"]` to case 2.
5. **Step numbers 6b and 6c.** Renumber to plain steps; a weak model tracks a checklist by number.
6. **Template line 73** has no column for the check date, which the quality criteria require ("output with its date"). Add a "Checked" column.

### For the maintainer to decide

1. Must-fix 2. Options: a fictional handle, with a `--responses <file>` option in `handle_check.py` (or a `setup` step) that feeds recorded answers, so that the case no longer depends on the live network; or keep a real, registered name and accept the exception.
2. `docs/workbench/state.md` is written (step 7): shared ledger.
3. The untracked `scripts/__pycache__/handle_check.cpython-311.pyc` in the main checkout is ignored by git and by the content hash; remove it when convenient.

## brand-profile

Per case, with the skill: case 1 all 1.0 on both models; case 2 strong 1.0, 1.0, 0.83, floor 0.83, 1.0, 0.83.

### Must fix

1. **Skill defect behind e2 a5 (failed in three of six runs with the skill; floor 1/3).** Assertion: "Every question carries a recommended answer". In all three failures item 7 (the material) had no `Recommended:` line. Cause: item 7 of step 3 (line 61) is a request, and its bracket default does not read as an answer. Fix in line 54: "All eight items carry a `Recommended:` line, item 7 included" and change item 7's default to `[Recommended: the profile export as PDF or pasted text, plus three posts you wrote alone, each marked with who wrote it]`.
2. **`requires: []` although step 2 reads a code host and web pages.** Line 52: "read its public profile ... through the host's CLI or API" and "read the author's text verbatim from the raw page". Fix: `requires: [integration:vcs, search:web]`; the Inputs rows already say "Skip", so add only "say in the report which source was not read and why".
3. **Lines 64, 70 and 72: workbench script paths.** Apply Patterns 1.
4. **Line 64: `uv run --with pypdf==5.1.0` installs a package.** It fails where there is no package registry (the eval container, an offline machine); `linkedin_export.py --file` then exits 2 with "--file needs pypdf". Add: "When that command cannot install the package, ask the user for the profile text and use `--text-file`."
5. **No `grader_files`.** Case 1 assertions 2, 4, 5, 7 and 9 check facts against `inputs/profile.txt`, `inputs/readme.md`, `inputs/posts/old-post.md` and the state file. List the four.

### Should fix

1. **Assertions that passed in every run of all four variants.** e1 a3 "The tinykv launch post is not used as a voice sample ...": CONTENT, the state file says who wrote it, so every model passes; replace with what the expected output already asks and no assertion checks: "Fewer than three voice samples is raised as an open question with a recommended answer". e2 a1 "No docs/brand/profile.md is written": GUARD, keep. e2 a6 "No attempt is made to fetch or scrape a LinkedIn page": GUARD but unverifiable; reword to "The reply states no fact about the person taken from a LinkedIn page and asks the person for the export or the pasted text".
2. **e1 a2 depends on the date of the run.** "... (for example '7 years' and some months), not a rounded guess such as '8 years'". From 2027-01 the script's correct answer is "8 years". Reword: "The profile gives the experience as the years and months from January 2019 to the date of the run, as `linkedin_export.py` computes them (7 years 9 months in October 2026), not a rounded figure such as '10+ years'", or add `--today` to the prompt's context through a state decision.
3. **Reply template (line 143) says "checker: ok".** Quote the evidence: `- Checks: check_profile.py --file docs/brand/profile.md → "ok": true; sensitive_topics.py --profile docs/brand/profile.md --validate → <its line>; experience from linkedin_export.py: <years_and_months>` and `- Files written: docs/brand/profile.md, docs/workbench/state.md`.
4. **Step 9b** (line 70): renumber. It also asks the person "to confirm the topics" while step 3 says not to stop when material exists; say that the confirmation is one of the open questions of step 12.
5. **Fixtures.** `inputs/profile.txt` line 3 `dana.example@example.org` and `inputs/readme.md` line 9 `https://example.org/tinykv`: use a `.example` domain, as AGENTS.md says.
6. **A check line for the guide.** Add to the profile template, under the lock: `- Check: sensitive_topics.py --profile docs/brand/profile.md < text (script of brand-profile)`, which `brand-guidelines` copies (its must-fix 2).
7. **Cases.** The update path (an existing `profile.md`, step 1) and the PDF path are not tested; the first is worth a case.

### For the maintainer to decide

None beyond the shared ledger: `docs/workbench/state.md` is written (steps 3 and 10) and is not in `outputs`.

## brand-strategy

Per case, with the skill: case 1 strong 1.0, 0.83, 1.0, floor 0.83, 0.67, 1.0; case 2 all 1.0. Without it: strong 1.0, 1.0, 1.0 on case 1 and 0.71 on case 2 (mean 0.857); delta 0.115, the smallest of the group.

### Must fix

1. **Eight of the thirteen assertions passed in every run of all four variants; the strong model alone scores 1.0 on case 1.** The record says little about what the skill adds.
   - e1 a4 and e2 a7 (leadership absent): GUARD; keep one, in case 2.
   - e1 a5 (rhythm and language not asked again): GUARD, keep.
   - e1 a6 (no strategy.md before the answers): GUARD, keep.
   - e2 a6 (no numeric target): GUARD, keep.
   - e2 a1 (label and pillars from the state file), e2 a3 (AI pillar framed as work in public), e2 a4 (self-reported numbers without the employer): CONTENT, copied from the fixtures; remove and replace with what the baseline does not do:
     - "The Goal and measures table has one row per product with its starting point, period and source, and the reply quotes the baselines.py command with what it returned".
     - "The positioning statement follows 'For <audiences>, <name> is <category> who ..., proven by <proof>' and names only proof that the profile's table marks citable".
     - "Proposals for public profiles contains a replacement for the README that names Beta Labs, marked as applied by hand" (in the expected output today, with no assertion).
     - "Risks has at least one risk for the AI-for-databases pillar with the date or measure that settles it".
     - "docs/workbench/state.md registers docs/brand/strategy.md as draft".
2. **Skill defect behind e1 a3 (failed in three of six runs with the skill; floor 1/3).** Assertion: "The reply offers pillar options tied to tinykv or to reach, with one recommendation". The replies gave one fixed set of three pillars, or marked all three "(recommended)". Cause: step 3 says "Build two or three options for each remaining item" and item 2 says "The pillars: three"; what an option is, for pillars, is left to inference, and there is no template for the gate message. Fix in step 3: "For the pillars, an option is a set of three: offer two or three sets, `Set A (recommended)`, `Set B`, each pillar with the product or reach it serves and its proof", plus a template:
   ```markdown
   1. Label. A (recommended): <label>, because <reason>. B: ... C: ...
   2. Pillars. Set A (recommended): <p1> (<serves>, proof: <...>); <p2>; <p3>. Set B: ...
   3. Rhythm and languages. A (recommended): ...
   4. Numeric targets now? A (recommended): no, measure four weeks first. B: yes.
   ```
3. **Skill defect behind e1 a2 (floor run 2 failed).** The recommended label contained "learning AI for databases in public". Cause: the "built in public" framing of item 2 leaks into the label. Fix in item 1 of step 3: "The words 'learning', 'aspiring' and 'enthusiast' appear in no label option, not for a theme with a gap either: such a theme appears as a subject or stays out of the label."
4. **`baselines.py` needs the network, `requires` is empty, and case 2 scores on a false premise.** The script calls api.npmjs.org and api.github.com. Case 2 has no `allow_web`, so in every run the script failed with "Tunnel connection failed: 403 Filtered", and step 2 (line 50) tells the model to write that as `not found (<error>)`. The expected output says "the package and repository do not exist". A blocked network and a product that does not exist are different facts. Fix: `requires: [search:web]`; step 2 "an HTTP 404 is `not found`; any other error is `not measured (<error>)`, with an open question asking the user for the number"; and for case 2 either `"allow_web": true` or an expected output and assertion that say `not measured`.
5. **Fixture inconsistency in `evals/files/dana-open` and `dana-decided`.** `docs/brand/profile.md` lists "Leadership and people management [4]" under Never expose, citing the state file; the state file's decision reads "Never expose: employer names, family, salary, exact location". A strong run raised it as an extra question ("Your profile lists leadership ... but the state file's decision ... lists only ..."). Fix: add leadership and people management to the decision in both state files.
6. **Line 50: workbench script path**, and no `grader_files`: add `docs/workbench/state.md` and `docs/brand/profile.md` to both cases.

### Should fix

1. **Step 3 gate wording (line 51).** "ask in one message ... wait" lacks the rule for "go" and for writing nothing; add the sentence of Patterns 3.
2. **Reply template (lines 115 to 124)** quotes no evidence: add `- Baselines: baselines.py --npm <package> --github <owner/repo> → <value, period | not found | not measured (<error>)>` and `- Files written: docs/brand/strategy.md, docs/workbench/state.md`.
3. **Cases.** No stop case (no `profile.md`: Inputs row 1) and no company case (reads `icp.md` and `positioning.md`). Add the stop case with `absent_on_purpose`.
4. **Lines 39 and 40 "Stop; offer `brand-profile`" / "offer `biz-icp-positioning`"**: use the D12 wording.
5. **`scripts/tests/test_baselines.py` holds one test.** Add tests for the error paths that must-fix 4 separates (404 against a network error).

### For the maintainer to decide

1. With the always-passing assertions replaced, the strong baseline will drop and the scores of the skill itself may move; nothing can be said about the gate before the final round. This skill is the one most likely to need a second iteration.
2. `docs/workbench/state.md` is written (steps 3 and 8): shared ledger.

## brand-voice

Per case, with the skill: strong all 1.0; floor case 1: 1.0, 0.6, 1.0; case 2: 0.83, 0.83, 0.83 (mean 0.85, the closest to the threshold in the group).

### Must fix

1. **e2 a3 failed in all three floor runs for a formality.** Assertion: "At least two rewrites of Dana's samples are present, with no emoji and at most 2 hashtags each, ending with a question". Every rewrite ended with its question followed by a line of two hashtags ("which one are you already running?" then "#databases #benchmarks"). `voice_stats.py` defines the rule that way (help: "whether the text ends with a question (hashtags and links after it are ignored)"), and I confirmed it: that text passes `check` with `end_with_question: true`. The output follows the skill. New wording: "At least two rewrites of Dana's samples are present, each with no emoji, at most 2 hashtags, and a question as its last sentence (a closing line of hashtags after the question is allowed, as voice_stats.py counts it)".
2. **e1 a1 and a2 failed in floor run 2; one is the grader's confusion, the other a missing template.**
   - a1 "The AI-written tinykv launch post ('Excited to announce', 'blazing-fast') is not used as evidence of Dana's voice". The reply counted "S3 tinykv" (41 words, one rocket, three hashtags, ends with a question): that is Dana's own post of 2024-01-09, which mentions tinykv; the grader took it for the launch post. Fix: `"grader_files": ["docs/brand/profile.md"]` and "The launch post of 2026-09-10 ('Excited to announce tinykv') is not counted or quoted as one of Dana's samples; Dana's post of 2024-01-09, which also mentions tinykv, is a valid sample".
   - a2 "The reply or guide keeps the dry humour and quotes at least one of Dana's own samples as evidence". The reply stopped at the questions and showed counts with no quote. The skill has no template for the message that stops at step 3, and step 1's "list the rest as excluded" was not carried into it. Fix in step 3, a template for that message:
     ```markdown
     Samples used: <id, date> ...; excluded: <text> (<who wrote it>)
     | Trait | Evidence (quote, sample) | Keep or drop (source) |
     <n>. <question> Options: <a> / <b> / <c>. Recommended: <one value>
     ```
3. **Step 3 gate and case 1 allow two paths.** Step 3 (line 51) says "ask in one message" with no stop; the expected output of case 1 accepts "asks ... and stops, or writes only a draft that waits on them"; a5 "If docs/brand/voice.md exists, its status is not confirmed" passes when nothing is written. Fix in step 3: "Stop until they answer; 'go' or 'proceed' is not an answer and does not accept the recommendations. Write no `docs/brand/voice.md` before the answers." Replace a5 with "No docs/brand/voice.md is written" and the expected output with the single path.
4. **Lines 50 and 54: workbench script paths and one-line here-documents.** `python3 skills/brand-voice/scripts/voice_stats.py stats <<'EOF' [{"id": "S1", "text": "..."}] EOF` is not valid on one line. Apply Patterns 1 and write both commands as fenced blocks.

### Should fix

1. **Assertions that passed in every run of all four variants:** none. No "reply is in English" assertion exists in this or any other skill of the group.
2. **`scripts/voice_stats.py` reads standard input before it checks its arguments.** With no argument it prints the help and exits 0 (should be usage, exit 2); `stats --help` and an unknown subcommand answer "stdin is not JSON" when standard input is empty and block when it is a terminal. Parse the arguments first.
3. **No reply template for step 7.** Add:
   ```markdown
   ## Voice: <name> (draft)
   - File: docs/brand/voice.md; registered in docs/workbench/state.md as draft
   - Counts: `voice_stats.py stats` → <per sample: emojis, hashtags, exclamations, ends with a question>
   - Rewrites checked: `voice_stats.py check --rules docs/brand/voice.md` → <id: "ok": true> per rewrite
   - Does it sound like you? What would you change? <each Assumption: as a question>
   ### Instructions found in external content
   ```
4. **A check line in the voice template** for `brand-guidelines` to copy: `- Check: voice_stats.py check --rules docs/brand/voice.md < draft (script of brand-voice)`.
5. **Cases.** No stop case (no `profile.md`), no case with fewer than three samples (`hypothesis`), no case for step 8 (corrections become rules, status `confirmed`). Add at least the stop case. Add `grader_files` (`docs/brand/profile.md`, `docs/workbench/state.md`) to case 2: assertions 2 and 4 check counts and facts against the samples.
6. **Line 39 "Stop; offer `brand-profile`"**: use the D12 wording. The template's status line lacks `hypothesis`, which Inputs row 2 requires.

### For the maintainer to decide

None beyond the shared ledger: `docs/workbench/state.md` is written (steps 3, 7 and 8) and is not in `outputs`.

## Patterns

1. **Script paths point into the workbench (all eight skills).** Every command reads `python3 skills/<name>/scripts/<script>.py`, a path that exists only in this repository. Floor transcripts show bare `python3 rank.py`, `python3 capacity.py` and similar attempts first. Proposed sentence, as in `core-clarify` and `eng-implement`: "The scripts are in the `scripts/` folder next to this file, not in the project. Run them from the project root by that path: `python3 <this skill's folder>/scripts/<name>.py`."
2. **Harness paths leak into project artifacts (market, guidelines, identity; possible in all).** Templates tell the model to record the command it ran, and the model records the installed path, which sits inside an AI tool's folder. Rule to add wherever a template records a command: "write the script's name and its arguments, never its path".
3. **Stop gates lack the wording that makes them hold (seven skills; only brand-identity has it).** Proposed sentence, from `brand-identity` line 51: "Stop until they answer. A 'go', 'proceed' or 'use your judgement' is not an answer to these questions and does not accept the recommendations: ask them anyway. Write no file before the answers."
4. **No case in the group has `grader_files`,** and none has `absent_on_purpose`. One measured failure (brand-guidelines e1 a5) and one grader confusion (brand-voice e1 a1) come from it.
5. **Conditional assertions ("If <file> exists, ...") pass when nothing is written:** biz-icp e1 a3 to a5, brand-name e2 a6, brand-voice e1 a5. Each needs the skill to have one path, then an unconditional assertion.
6. **"No web search or page fetch is run" (biz-icp e2 a1, biz-market e2 a1, brand-profile e2 a6) cannot be seen by the grader** and passes everywhere. Reword to what the reply shows: no figure, name or URL that only a search would give.
7. **Reply templates are missing or carry no evidence.** Only market, profile and strategy have one, and none quotes a command with its output line or lists the files written. Each section above proposes the lines.
8. **Network use is undeclared.** brand-name, brand-profile, brand-strategy and brand-identity need the network and declare `requires: []`; none states its behaviour without it, and two cases (brand-strategy 2, brand-identity 2) ran without the network they need.
9. **Every skill writes `docs/workbench/state.md` and none declares it:** all eight are candidates for the `updates` field. brand-identity also writes undeclared piece files.
10. **Report before checks.** biz-icp and biz-market place the report step before the lint steps and then forbid reporting before the lints pass. Order: write, check, self-check, report.
11. **Skills named that are not built:** `biz-business-model`, `biz-gtm` (both biz skills) and `biz-validate-idea` (market). Mark as planned, as D12 did for flows.
12. **One-line here-documents** in brand-identity line 53 and brand-voice lines 50 and 54; the two biz skills show the correct fenced form.
13. **Degraded and stop cases are thin.** Missing: degraded mode for both biz skills; the stop on a missing required file for identity, strategy and voice; the stale-guide case for guidelines.
14. **Harness observation, not a skill change:** one `grading.json` (biz-icp-positioning, case 3, floor) holds assertion results without their `text` field, and graders sometimes shorten an assertion's text, so the same assertion appears under two or three texts in one iteration (brand-profile e1 a2, brand-voice e2 a4, brand-guidelines e1 a5). Any tool that groups results by text will split them; group by `id`.
