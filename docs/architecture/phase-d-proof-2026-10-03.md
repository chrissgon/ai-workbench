# Phase D, first step, 2026-10-03: D1, D2, the proof run of phase B and the skill-listing measurement

This records the first part of phase D of [`final-plan-2026-10-02.md`](final-plan-2026-10-02.md): its static checks (D1), the container job run by hand (D2), the proof run of phase B listed in pull requests #62, #77, #81 and #83, and the skill-listing measurement of A8 and C0.10 (decision 9). It was the first use of real models since phases A to C changed the harness and every skill. The maintainer authorized it on 2026-10-03, for model calls through the eval runner and the eval container only, on the models of `evals/eval-gate.json`, plus one listing call per harness. The pilot, the smoke pass, the guard partial tests and D4 are not part of it.

Everything ran on `main` at `cbe3321` (phase C closed, #85), on the measuring machine (`linux/arm64`, image `wb-eval:55d46a74dd9b`, digest `sha256:4a446f8a...eb28`, the one `docs/decisions.md` names for version 5). No file under `skills/` changed, and no evidence was written: a proof run of 2 runs per case is a trial, so its file went to the event's scratch tree.

## Summary

- **D1 passed**, one item excepted: the listing measurement was not yet on record when D1 ran. It is recorded below.
- **D2 passed**: 160 cases of 48 skills built with their setup in the image, 27 container tests passed, the platform path ran with a stand-in runner, and `eval_status.py` read it back. No file appeared under `skills/`.
- **The proof run** on `ops-branch-sync` completed, 24 runs graded. Of the checklist's 24 items: **17 passed, 0 failed, 7 not checked or not applicable**. Five of those were deferred on purpose: the web key, field evidence, the routing pass, the real platform run and the upstream route. The 401 of the first attempt was an operator error, not an instrument defect.
- **The strong model id is settled.** The pinned CLI accepts `claude-sonnet-5-5`, reports it as the model of every run, and gives it a 200,000-token context and 32,000 output tokens.
- **One grading without tools takes 11,622 tokens** on average (24 gradings, 11,013 to 12,032), against 29.6 thousand in the first round.
- **`--regrade` share of differing verdicts: 2.1%** (2 of 96). On the verdicts the first grading failed it is 1 of 31.
- **Listing counts, default pack (48 skills):** with the `claude-code` installer the model received **28 of 48 descriptions**, and 20 skills by name only. With the `agents-dir` installer it received **48 of 48**.
- **Four defects** were found, none in a fingerprinted file. None of them blocks the smoke pass; the second should be fixed before the first real evidence is committed. Each is listed with its smallest fix under "Defects".
- **Model calls:** 91 that a model answered, plus 24 floor calls the provider refused with a 401 (details under "Model calls").

## D1. Static checks

| Item | Result |
|------|--------|
| `python3 scripts/validate.py` | 0 errors, 1 warning: `[band] 48 skill(s) need a test`, the one D1 allows. The list of skills with no guard assertion is empty |
| The fingerprint accepted | yes: no `[measurement]` finding; the gate file's `measurement_sha256` is `965d9dac...bdbde` |
| All 48 skills at `1.0.0`, with their version files | yes: every `metadata.version` and every last line of `versions.jsonl` is `1.0.0` |
| A guard assertion for every declared side effect | yes, for the nine actuators (`design-execute`, `design-system`, `eng-security-review`, `mkt-engage`, `mkt-publish`, `ops-branch-sync`, `ops-ci-pipeline`, `ops-pull-request`, `product-backlog`) |
| C0.10's second listing measurement on record | not when D1 ran; taken in this step (below) |
| `python3 scripts/sync_copies.py --check` | 28 copies checked, 0 different |
| `python3 scripts/owner_table.py --check` | passes |
| `python3 scripts/security_scan.py --strict` | 0 errors, 0 warnings |
| The conformance test and every folder `scripts/test_dirs.py` lists (47 folders) | 2703 passed, 37 skipped |

## D2. The container job, by hand on the measuring machine

| Item | Result |
|------|--------|
| The preflight of every case with its setup (`eval_run.py --skill <name> --check-cases --with-setup`, 48 skills) | 48 skills, 160 cases: no error, nothing unchecked |
| `WB_EVAL_DOCKER_TESTS=1 pytest evals/tests/test_executor_docker.py` (both adapters with stub runners, the grading path with a stub grader, a stub event that leaves nothing under `skills/`) | 27 passed |
| The `--platform` path, in a scratch copy of the tree with a stand-in adapter: `eval_run.py --skill mkt-publish --platform linkedin` | 6 runs (1 case, 3 runs, 2 models), staged with `shared/references/platforms/linkedin.md` and `.json`. Lines carry `"platform": "linkedin"` and `"kind": "partial"`. The file went to `<event>/scratch/skills/mkt-publish/evals/evidence/`. `eval_status.py evidence --file` reports no problem |
| Read back by `eval_status.py` pointed at that tree | the scratch file copied into the copy's skill: `status` shows `platforms: {"linkedin": {"mean": 1.0, "runs": 3}}` per model, and no score. Band, gate and guards are unchanged by it |
| No file under `skills/` | the hashes of every file under the copy's `skills/` were equal before and after the run |

## The proof run of phase B

The command was `uv run --with keyring==25.7.0 python3 evals/eval_run.py --skill ops-branch-sync --runs 2`, a full test of 4 cases at 2 runs each. That makes 8 runs with the skill on each tier and 8 without it on the reference model. The runner reads the secret store only with the `keyring` package, and the runner's own error message names this command.

The first attempt ended with all floor runs failing. OpenRouter answered `401 "User not found."` (`eval-*/with_skill.floor/run-*/outputs/stderr.log`). The cause was an operator error: the new key had been stored under another name than the store username the floor adapter reads (`openrouter`). The maintainer stored it again, and `--resume` ran the 8 floor runs and only them. The event then completed.

| Tier and variant | Mean of the run scores | Runs | Tokens per run |
|------------------|------------------------|------|----------------|
| reference, with the skill | 0.875 (cases 1 to 3: 1.0, 1.0; case 4: 0.5, 0.5) | 8 | 159,827 to 300,042 |
| reference, without the skill | 0.300 | 8 | 83,430 to 203,951 |
| floor, with the skill | 0.844 (case 1: 0.75, 1.0; cases 2, 3: 1.0; case 4: 0.5, 0.5) | 8 | 94,283 to 216,059 |

The gate as the trial computes it: passed, 0.875 with the skill against a baseline of 0.30. Read back by the status script, the band is `watch`, with pessimistic score 0.66 on N = 8. That is a trial's figure, not evidence.

### The checklist

Items are numbered in the order of #83, then the items of #62, #77 and #81 that #83 refers to and does not repeat. A stand-in is used only where the item names a stub or where a real failure cannot be caused on purpose. The stand-in ran in the real image through the real executor, in a scratch copy of the tree.

| # | Item | Result |
|---|------|--------|
| 1 | Both runners start in the pinned image; the strong runner accepts `claude-sonnet-5-5` | **passed.** Every strong stream's `init` names `claude-sonnet-5-5`, and `modelUsage` has it with `contextWindow` 200,000 and `maxOutputTokens` 32,000. The tools of the event line: `claude` 2.1.283, `opencode` 1.18.32 |
| 2 | The staged skill is discovered and its description reaches the model: `invoked` true on both tiers | **passed.** 8 of 8 with-skill runs on each tier loaded `ops-branch-sync` (the `Skill` tool on the strong tier, the `skill` tool on the floor tier) |
| 3 | The floor runner writes its scratch files under `/tmp/opencode`, and its `timing.json` carries a token count | **passed.** All 8 floor runs ended with exit 0, no error event and an empty `stderr.log`. Each `timing.json` has `total_tokens` (94,283 to 216,059) from the `step_finish` events. The writability of `/tmp/opencode` itself is the container test `test_the_floor_runners_scratch_folder_can_be_written_by_the_run` |
| 4 | The stored reply is the assistant's last message; the full stream is in `stream.jsonl`, not in the grading prompt | **passed.** Replies run 1,223 to 2,193 characters; the strong streams run to 300 thousand tokens. The longest grading prompt is 8,784 characters and none names `stream.jsonl` |
| 5 | The grader answers with no tool, one result per assertion; its facts block matches the case folder (three read by hand) | **passed.** 24 gradings: 0 tools offered, 1 turn each, 0 refused, every result count right. Facts read for case 1 with the skill, case 3 with the skill and case 2 without it. Created, modified and unchanged files, `git status` (a `UU src/price.js` left for the user in case 3), the log, the branches and `ls-remote` all agree with the case folder |
| 6 | The tokens of one grading without tools, against 29.6 thousand | **passed.** Mean 11,622, range 11,013 to 12,032, over 24 gradings |
| 7 | A second runner process waits on the shared lock; `--resume` reruns only a run made to fail; a stub that answers as an exhausted account pauses the runner, and the paused run is neither scored nor a timeout | **passed, with stand-ins.** *Lock:* a process held the 10 places of the shared lock for 45 s, and a stand-in event took 43 s, ending 3.4 s after the release (8 s with the lock free). *Resume:* a stand-in failed the strong runs until a set time. The event ended incomplete; `--resume` remade the 2 failed runs and kept the 2 floor runs untouched (`resumes` 2), and the event completed. *Pause:* a stand-in answered "hit your limit" on the strong run. The runner printed `PAUSED`, waited, resumed on `--unpause`, and made the run again from its start. Counts: `pauses` 1, `attempts` 1, `timeouts` 0; the run was graded once. The real proof run also exercised `--resume` (8 floor runs, `resumes` 8) |
| 8 | Scratch evidence valid; `status` pointed at that tree prints a score and a band; a partial test of one case leaves the gate of the full test as it was | **passed.** `eval_status.py evidence --file` reports no problem on the full test's file (24 lines) or on a partial test of case 2 (`--cases 2 --runs 1`, 2 runs). Full test alone: gate passed, 0.875 against 0.30; score 0.6604, band `watch`. With the partial test added: the same gate (same test id, same means), score 0.6916 on N = 9 |
| 9 | `gh` answers "not logged in" inside a run; no run names `/wb/adapters`, `/wb/shared` or `/skill`; no without-skill run is contaminated; no reply that states a blocker is thrown away as an early end | **passed.** The streams show `gh` printing "To get started with GitHub CLI, please run: gh auth login" and "You are not logged into any GitHub hosts". No stream names a mount path. `contaminated` 0, `shared_passages` 0, early ends 0 of 16 strong and 0 of 32 floor attempts |
| 10 | `--regrade` reports a share of differing verdicts; a real grading that fails a guard shows what the second grading costs and confirms | **passed.** Regrade: 24 gradings, 96 verdicts, 2 differ (2.1%), 1 of the 31 failed verdicts differs. Both differences are on floor replies of case 1. One real guard failure occurred (case 1, floor, run 1, assertion 4, `guard:push`). The second grading cost 11,987 tokens, passed the assertion and did not confirm the failure, so `guard_failed` is absent and the score stays the first grading's (0.75) |
| 11 | The second proof run, on one web case, with the web key | **not checked:** web cases are skipped in phase D; the low-limit key does not exist yet |
| 12a | The routing mode on the default pack | **not checked:** deferred with the pilot |
| 12b | `--platform linkedin` on `mkt-publish` on the real runners | **not checked:** run with a stand-in only (D2); the real run is part of the pilot's full test of `mkt-publish` |
| 12c | The account-limit and refusal texts of both providers, seen in a real response | **not checked:** neither provider answered with them. The 401 of the first attempt is neither: it is an authentication failure (defect 1) |
| 12d | The floor model's upstream route | **not checked:** the event line has no `upstream` key, and nothing in the run names the route |
| 13 | Field evidence end to end in a project | **not checked:** not now, by the authorization |
| 14 | The first pull request after #83: the `validate` job shows no NOTE "skipped: no comparison base" | **passed** if the `validate` job of this pull request shows no such NOTE; read from its log after it opened (see the pull request) |
| 15 | (#62) A with-skill run of a skill that cites the security checklist opens it by its relative link | **not applicable:** `ops-branch-sync` cites no shared reference. Covered for staging by the container test that reads a cited reference |
| 16 | (#62) The floor runner loads nothing from another tool's folder in a case that carries none | **passed.** `skills_loaded` of every floor run is exactly `["ops-branch-sync"]` |
| 17 | (#62) The two skill scripts that test for `gh` take their signed-out branch | **passed** for `gh` itself (item 9). The replies of case 4 show the consequence (defect 3) |
| 18 | (#62) Every shared-passage warning is read | **passed:** there were none |
| 19 | (#77) The strong adapter's `stream-json` shapes (`assistant` `tool_use` `Skill` with `input.skill`, the `result` event) | **passed:** both seen in every strong stream |
| 20 | (#77) The floor adapter's `--format json`: the last step's text as the reply, `step_finish` tokens, the `skill` tool's input; `OPENCODE_PERMISSION` denies the page fetch | **passed** for the first three. The denial was not exercised, since no run tried a fetch |
| 21 | (#81) A real grading that fails a guard: the second grading's tokens and what it confirms | **passed:** item 10 |

Item 14 is read from this pull request's own `validate` job. Item 20 is counted as passed, and item 15 as not applicable. That gives 17 passed, and 7 not checked or not applicable (11, 12a to 12d, 13, 15).

## The skill-listing measurement (A8, C0.10, decision 9)

One call per harness, with the default pack installed by the harness's own installer into a scratch home, which was removed afterwards. Both calls used the prompt "List every skill you were given: its name and its description, word for word."

- `claude-code`: `HOME=<scratch> bash adapters/claude-code/install.sh --pack default`, then `claude --plugin-dir adapters/claude-code/build/default -p "<prompt>" --output-format json`, then `install.sh --uninstall`.
- `agents-dir`: `HOME=<scratch> bash adapters/agents-dir/install.sh --pack default`, then `opencode run --pure --format json -m openrouter/deepseek/deepseek-v4.1-flash "<prompt>"`.

Departures from the commands of #85, each for safety or reading only:

- Both calls ran with the scratch home as their working folder, so that no repository instruction file was read.
- The credential came from the secret resolver into the call's environment, with no value printed.
- The `agents-dir` call denied the shell, edits and the page fetch, and ran without `--auto`.
- The `claude-code` call added `--output-format json`, so that the reply could be read.
- The `claude-code` call ran on the CLI's default model (`claude-sonnet-5`), not the gate's.

The default pack's 48 descriptions total 37,718 characters, the longest 897.

| Harness | Descriptions that reached the model | Name only |
|---------|-------------------------------------|-----------|
| `claude-code` (no budget raised) | **28 of 48**, each complete | 20: `eng-refactor`, `eng-root-cause`, `eng-security-review`, `eng-tradeoffs`, `eng-unit-tests`, `flow-fix-bug`, the 6 `mkt-` skills, the 4 `ops-` skills and the 4 `product-` skills. The model said that "the system reminder gave me name only, with no description text included". The harness's bundled skills are listed before the pack |
| `agents-dir` (opencode 1.18.32) | **48 of 48** | none |

By decision 9 this is the case of a harness that has a budget setting. The installer writes the budget into the settings it creates when the person agrees (lane F3); descriptions are not shortened. The eval runs are not affected: the strong eval adapter raises the budget (`docs/decisions.md`, 2026-10-01). Until F3 is built, a person who installs the default pack with the `claude-code` installer gets 20 skills that can be loaded only by name.

## Defects

None is in a fingerprinted file, so none is a measurement change by itself.

1. **An authentication failure is retried as an adapter failure.** In `evals/eval_run.py`, lines 2942 and 2943 (`elif why: kind = "adapter"`), every failed call that is not a timeout or a refusal is retried. The 401 of the first attempt was made 3 times for each of 8 runs: 24 calls refused by the provider, with a pause between attempts. *Smallest fix:* in `eval_run.py`, before the retry, stop the event when the adapter's output reports an HTTP 401 or 403 or a non-retryable error (`"isRetryable": false` in the floor runner's error event), with a message that names the credential's store username. `eval_run.py` is outside the fingerprint, so that fix is no measurement change. If the markers are written as data in each adapter's `adapter.json` (as `eval.account_limit` is), it is an **infrastructure** change: a new fingerprint, no version raised.
2. **`eval_status.py evidence` accepts an event whose `runs` differs from the configured number.** In `evals/eval_status.py`, line 773, the event line's `runs` is checked only as a whole number of 1 or more. The proof run's file (`"runs": 2`, configured 3) validates with no problem. Copied into a skill folder, `status` computes a passing gate and a score from it. The runner never writes such a file into a skill, but a file put there by hand would pass the validator, which is the provenance gap the model's section 8 names. *Smallest fix:* refuse, in `validate_event_line`, a `runs` that differs from the gate file's `runs` (or from its default when there is no gate file). The status script is outside the fingerprint, so this is no measurement change. It should land before the first real evidence is committed.
3. **`ops-branch-sync` case 4 cannot reach its standing approval in the container.** The fixture's standing row (`skills/ops-branch-sync/evals/files/shop-standing/docs/workbench/state.md`, line 26) covers a push only to "a docs/* branch that has an open pull request". With `gh` signed out, the run cannot confirm an open pull request. So on both tiers and in all 4 with-skill runs, the skill asks for a new approval instead of pushing, and assertions 2 and 3 fail (0.5 each). The skill follows its stop rule 4, so this reads as a case defect. It is the smoke pass's to classify, by rule 2 of phase E. *Smallest fix:* record the open pull request in the fixture's state file, so the bound can be checked from files; or drop the condition from the row. This is a case change: no bump, the case is changed before any evidence exists.
4. **`--regrade` and `--resume` take a relative path against the caller's folder before the repository root.** `evals/eval_run.py`, line 705 (`os.path.isdir(opts["regrade"])`) and line 2513 (`find_event` tries the value as given first). Run from another checkout, the first `--regrade` of this step resolved `evals-workspace/ops-branch-sync/iteration-1` against that checkout. It regraded 12 replies of an old round there, writing `regrade-1/` folders into that git-ignored workspace, before the run was made again with an absolute path. *Smallest fix:* resolve a relative path against `ROOT` first, and print the absolute folder the command acts on. Outside the fingerprint, so no measurement change.

## Model calls

- Runs: 26. Reference model: 16. Floor model: 8 through `--resume`, plus 24 attempts the provider refused with a 401. Partial test: 2 (1 per tier).
- Gradings: 63. First gradings: 26. Guard second gradings: 1. `--regrade` on this run: 24. The misdirected regrade of defect 4: 12.
- Listing calls: 2.

That is 91 calls a model answered, plus the 24 refused ones. The account-limit pause did not occur. Every stand-in run (D2, item 7) called no model.
