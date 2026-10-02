# Round 2 review: providers, contracts, the agent runtime, doctor, packs

Read-only review of a separate working tree of the repository at `6347292` on 2026-10-02. Nothing in the repository was changed (`git status --short --ignored` is empty after the review).

## Method

- Read in full: `docs/architecture/final-plan-2026-10-02.md`, `providers/CONTRACT.md`, the five files of `contracts/`, `packs/`, the four `agents/*.md`, `providers/resolve.py`, `providers/secrets/resolver.py`, `scripts/runtime.py`, `scripts/runtime_vote.py`, `scripts/vote_job.py`, `scripts/doctor.py`, `scripts/select_skills.py`, `scripts/redact.py`.
- The provider implementations and their tests (`publisher/`, `mailbox/`, `scheduler/`, `vcs/`, `store/`) were read in full by three parallel reviewers with separate scopes; every finding of theirs that is listed here was checked again against the quoted lines.
- Tests run offline (`uv run --offline --with pytest==9.1.1`; plain `python3 -m pytest` has no pytest on this machine): publisher, mailbox and secrets 102 passed; scheduler 62 passed; vcs and store 76 passed.
- Findings marked **reproduced** were run in a scratch test outside the repository, with the fakes of `scripts/tests/test_runtime.py` and `test_runtime_vote.py` (no network, no credential store, no real scheduler).
- Paths are relative to the repository root. "Plan" is the final plan; its items are cited as A1, B2, C0.2, F2, "row 44" (the skill table of phase C), "default 57", "N15" (backlog map).

Severity: **blocker** (unsafe or wrong in a way that must be fixed before the thing is used), **should-fix**, **nit**. Size: S under an hour, M a few hours, L a day or more.

## Summary

| Area | Blockers | Should-fix | Nits |
|------|----------|------------|------|
| Agent runtime (`runtime.py`, `runtime_vote.py`, `vote_job.py`) | 0 | 9 | 7 |
| Resolution and doctor (`resolve.py`, `doctor.py`) | 0 | 3 | 3 |
| Publisher, mailbox, secrets | 0 | 8 | 8 |
| Scheduler | 0 | 8 | 6 |
| Vcs and store | 0 | 9 | 8 |
| Contracts and design-rule coupling | 0 | 5 | 6 |

No path was found that publishes twice without a person typing a contradictory command, and none that prints a credential. The ledgers, the file locks, the redirect refusal and the hash checks hold where they were read. The serious defects are losses and stuck states: a vote round that is silently never handled, a scheduled job stuck in `running`, notifications older than the newest 50 never read, a spend cap that does not count runs whose cost is unknown. The second theme is coupling: adding a second social platform today needs edits in the resolver, the doctor, the runtime, the provider contract and one skill's procedure, and most of that is not in the plan.

Finding ids: RT (runtime), RS (resolution, doctor), PB (publisher, mailbox, secrets), SC (scheduler), VS (vcs, store), CT (contracts and coupling).

---

## 1. Agent runtime

### RT1. should-fix. A vote round is silently lost when anything fails after the agent run, and "reject so the next tick retries" does nothing. Reproduced.

- `scripts/runtime_vote.py:264`: `store("cursor-set", "--name", f"vote:{rid}", "--value", f"run:{run_id}")` is written right after the run, before the bundle is built.
- `scripts/runtime_vote.py:233-234`: `if store("cursor-get", "--name", f"vote:{rid}").get("value"): return {"status": "none", "note": f"round {rid} already handled"}`.
- The cursor is written at lines 245 and 264 and nowhere cleared: `scripts/runtime.py:599-602` (`reject`) only calls `inbox-resolve`; the store has no verb that deletes a cursor.
- Yet three messages tell the person to reject: `runtime_vote.py:238-239` ("add a row, then reject this item so the next tick retries"), `:400-401`, `:413-414`.

Reproduction 1: `tick` (item created), `reject --id <n>`, `tick` again prints `{'status': 'none', 'note': 'round 2026-10-05 already handled'}` and the inbox is empty. Reproduction 2: the content folder made read-only, `tick` exits 1 with a traceback (`PermissionError`, see RT6); the next `tick` prints "already handled" with zero inbox items.

Scenario: the second read of the vote files (`build_bundle`, `:285`) hits a network error, or the calendar has no slot and the person adds the row and rejects as told. The round never produces a post, and nothing says so after the first tick.

Fix: `reject` on a `vote` item clears `vote:<round>` (the store needs `cursor-set` to an empty value or a `cursor-clear` verb), and the cursor is set to `run:<id>` only once an inbox item exists. Test: reject then tick builds a new item.

Plan: **not in plan**. Phase F, lane F2 (scripts and a store verb, no skill folder); S. It should precede PB15's "one real week".

### RT2. should-fix. The daily spend cap does not count a run whose cost is unknown. Reproduced.

- `scripts/runtime.py:325`: `total += float(r.get("cost_usd") or 0)`.
- `scripts/runtime.py:240-242`: `nz()` stores `null` "when the harness did not report it".
- `adapters/api/run_agent.py:362, 375` write `cost_usd` null when there is no price for the model; a run that times out leaves no `timing.json` at all (`runtime.py:365-369`).

Reproduction: fake adapter reporting `"cost_usd": null`, `daily_cost_cap_usd` 0.01, three comments: all three handled, `status` prints `spend_today_usd 0.0`.

`contracts/runtime.md:22` promises "a daily spend cap across runs (`daily_cost_cap_usd`), checked before each run from the store". With the API adapter and a model missing from `prices.json`, there is no cap, and nothing is printed.

Fix: a run with unknown cost counts as `max_cost_usd_per_run` (the worst case the adapter was allowed), and the tick's output says how many runs had no cost. Test with `FAKE_COST=null`.

Plan: **not in plan** (R7 "observability" in F2 is the nearest). Phase F2; S.

### RT3. should-fix. Notifications beyond the newest 50 since the cursor are never read.

- `scripts/runtime.py:453-454`: `search ... "--since", since, "--limit", "50"`.
- `providers/mailbox/gmail.py:368-374`: one request with `maxResults: limit`, no `nextPageToken`; `:615` sorts newest first; the output (`:616`) has no field that says the list was cut.
- `scripts/runtime.py:466, 471-472`: the cursor moves to the newest `received_at`.

Scenario the code itself anticipates (`runtime.py:457-458`: "An expired authorization ... the cursor stays, so the next tick that reads the mailbox picks up what this one missed"): after some days without a readable mailbox more than 50 notifications wait; the tick takes the newest 50, moves the cursor past the rest, and the older comments are never handled or shown.

Fix: the `search` verb pages until the limit and prints `"truncated": true` when more exist; the runtime moves the cursor only to the oldest message it did not get past, or loops until not truncated.

Plan: **not in plan**. F2 with PB6/PB7 (the e-mail trigger); S.

### RT4. should-fix. The vote job is scheduled with a bare `python3` and calls `uv` by name on a fixed PATH.

- `scripts/runtime_vote.py:354`: `argv = ["python3", str(p["job"]), ...]`. The scheduler resolves `argv[0]` with the approver's shell `PATH` (`providers/scheduler/launchd.py:317`) and hashes that file; `providers/CONTRACT.md:50` says jobs use `/usr/bin/python3` "because that path and its hash survive package upgrades", and `runtime.py:21` says the same for the tick. With a package-manager interpreter first on PATH, an interpreter upgrade between the approval and the slot makes the job `refused`: the approved post is not published.
- `scripts/vote_job.py:83, 100, 125` run `["uv", "run", ...]`; the scheduler runs the job with `PATH = RUN_PATH` only (`launchd.py:72, 820`: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`). `runtime.json` has a `path` key for exactly this problem (`runtime.py:19-21, 176-179`), but `write_job` (`runtime_vote.py:350-371`) does not carry it and `vote_job.py` has no option for it. With `uv` installed under the home folder, the job exits with `publish failed (127); nothing was recorded` at the slot.

Fix: `write_job` writes `/usr/bin/python3` and passes the configured folders (`--path`), which `vote_job.py` puts first on PATH; a test asserts both.

Plan: **not in plan**. F2 (N12 rehearses the Linux scheduler, not this); S.

### RT5. should-fix. The tick's approval covers three files; everything else it executes is read from a live, unverified checkout named by a project file.

- The documented tick job snapshots `runtime.py`, `runtime_vote.py` and `resolve.py` (`providers/scheduler/README.md:47-53`).
- At each firing the tick executes, unverified: the gate and the parser (`runtime.py:191-192`), `run-agent.sh` (`:189`), every provider including the publisher (`:184-188`), and it prepends folders to `PATH` (`:179`), all taken from `docs/workbench/runtime.json` in the project (`:148`), whose `workbench` key decides where that code is loaded from (`:180`).
- `contracts/runtime.md:39` says "the gate is code, bound by hash to what the person approved". Only the policy file is bound by hash; the gate script is not.
- `providers/CONTRACT.md:89` ("A verb whose effect happens later fixes what was approved") is honoured in letter (those files are not arguments) and not in effect.

Scenario: a pull to the workbench checkout, or an edit of `runtime.json` by anything that can write to the project, changes what the unattended job runs with the publishing credential, with no new approval and no refused firing.

Fix, smallest: the contract says plainly what the approval of a recurring tick does and does not cover; the tick records the hash of `runtime.json` and of the gate script at scheduling time and refuses when they differ. Larger: the job snapshots the gate, the parser and the providers.

Plan: **partly planned** (N15, "containment of a runtime agent beyond its tool list", is about the model's tools, not about the code the tick runs). Phase F2, with R1; M.

### RT6. should-fix. Any error that is not `Fail` ends the tick with a traceback and leaves claimed events and half-written state.

- `scripts/runtime.py:612`: only `Fail` is caught in `main`; `:486`: only `Fail` is caught per event.
- Uncaught paths read in the code: `:358` `re.findall(...)[0]` (an agent file with no `skills:` line, `IndexError`); `:422` `comment['text'][:80]` when the parser returns no text (`TypeError`); `:464` `m["id"]` (`KeyError`); `runtime_vote.py:303` `content.write_text` (`OSError`, reproduced in RT1); `:297` `json.loads(out)` on a script that printed no JSON.
- Consequence: the events the tick claimed (`:478-482`, all at once) stay `claimed` until the store reclaims them 60 minutes later (`providers/store/sqlite.py:53`), the run row stays `running`, and for the vote step the round is lost (RT1).

Fix: catch `Exception` per event and around the vote step, record `failed` with the exception's type, finish the event; keep the traceback on stderr.

Plan: **not in plan**. F2; S.

### RT7. should-fix. A reply drafted by a model that can read files is published without a check for credential formats.

- `scripts/runtime.py:404-408` sends `reply.txt` when the gate says `auto`; neither `runtime.py`, `runtime_vote.py` nor `skills/mkt-engage/scripts/policy_gate.py` calls `scripts/redact.py` or any secret pattern (grep for `redact`, `token_label`: no hit).
- The model's reading tools are not limited to the project by the runtime itself (the adapter decides; backlog N15).

Scenario: a comment talks the model into quoting a line of a file it can read; the gate checks links, sensitive topics and length, and the text goes out in public. `redact.token_label()` exists for this.

Fix: the gate (or the runtime, before the publisher call and before `approve` sends) refuses a reply or a post in which `token_label` finds a known format, and sends it to the inbox with the value masked.

Plan: **partly planned** (N15 limits what the model reads; nothing checks what goes out). In the runtime: F2, S. In `policy_gate.py` (it then also protects the interactive path): it changes a skill folder, so `mkt-engage`'s row 44, before the round.

### RT8. should-fix. The runtime's tests use a skill's eval fixture.

- `scripts/tests/test_runtime_vote.py:18`: `FIX = REPO / "skills" / "mkt-vote-round" / "evals" / "files" / "round-winner"`, copied at `:134-137`; assertions depend on its content (`:185-186`: the slot `2026-10-14T09:00:00-03:00`, the key `2026-10-14-vote-durability-is-a-budget`).
- Phase C rewrites that fixture (row 48: "a fictional author and title in three fixtures", C0.8, decision 6 on dates). The runtime tests then fail for a reason outside `scripts/`; after the round, a change the runtime tests need in that fixture stales `mkt-vote-round`.

Fix: the runtime's tests get their own copy under `scripts/tests/fixtures/`.

Plan: **not in plan**. Phase A (it touches no skill folder), before the lane of group 6 starts; S.

### RT9. should-fix. `tick --dry-run` writes to the store.

- `scripts/runtime.py:461-465` add events before the `if a.dry_run` at `:467`; `Store.__init__` (`:234`) creates the database. Reproduced: after `tick --dry-run` the store holds one `pending` event.
- `runtime.py:45`: "--dry-run reads the mailbox and parses, and runs nothing else". The next real tick runs the agent on those events.

Fix: move the dry-run return before `event-add`, or say what it writes. Plan: **not in plan**. F2; S.

### Runtime nits

- **RT10.** `providers/scheduler/README.md:47-48` documents the tick as `runtime.py tick --project ... --agent social-manager`; `runtime.py` has no `--agent` (`:569-579`). Reproduced: exit 2, "unrecognized arguments". A job scheduled from the README fails at every firing.
- **RT11.** `runtime.py:589`: the lock file is created with the process umask, not 0600; `:588` makes the folder 0700 only when it creates it.
- **RT12.** The approval hash of a reply item is the hash of the reply text only (`runtime.py:423`, `:534`); the target (`post_urn`, parent comment) and the key come from the store's payload, which is not hashed. `contracts/environment.md:57` lists the target among what an `action` approval covers. For a vote item the stored bundle is never re-hashed against `payload_sha256` (`runtime_vote.py:405`), so `slot.when` is covered only by the database. `providers/store/sqlite.py:606-619` stores `--payload-sha256` without checking it against the payload.
- **RT13.** `runtime.py:464`: an empty external id (`m["id"] or ... or ""`) makes every such message one event.
- **RT14.** `runtime.py:298-305`: the commenter's name goes into a Markdown heading of `docs/marketing/engagement-inbox.md` unquoted and with its line breaks; only the comment text is flattened and labelled as external content. `mkt-engage` reads that file.
- **RT15.** `runtime_vote.py:235`: the round id read from the repository's vote file becomes a folder name with no check here; today `skills/mkt-vote-round/scripts/vote_state.py:53, 142` validates it. The runtime depends on a skill script for a path it deletes with `shutil.rmtree` (`:281-282`).
- **RT16.** None of `runtime.py`, `runtime_vote.py`, `vote_job.py` has the PEP 723 header that `providers/CONTRACT.md:58` asks of "a script in that set" (`requires-python = ">=3.9"`, `dependencies = []`); the guard test only reads a header when one exists.

### Runtime test gaps (confirmed by grep of the two test files)

No test for: reject of a vote item and the retry (RT1); a failure after the agent run in the vote step; unknown cost and the cap (RT2); more than `--limit` messages (RT3); the tick lock (`another tick is running` appears in no test); `tick --dry-run` (RT9); an exception that is not `Fail` (RT6); a publisher that succeeds while the store write after it fails (`runtime.py:409-415`: the reply is out, the event ends `failed`, no action row, no log entry); approving the same item twice; `vote_approve` when scheduling succeeds and the store write fails (`runtime_vote.py:420-423`: the item stays open and the second approve meets "job is scheduled"); `vote_job.py` when the publisher is not found.

---

## 2. Resolution and doctor

### RS1. should-fix. The resolver does not know which platforms an implementation serves; a second publisher breaks the first.

- `providers/resolve.py:190-195`: one implementation in the folder resolves for any sub-class; two resolve for none ("has several providers and none is selected").
- Checked: `resolve("publisher:instagram")` returns `linkedin` (`only-implementation`); `providers/publisher/linkedin.py:573-575` then refuses any platform but `linkedin`, with exit 2, at the moment of use.
- `scripts/runtime.py:186-187` works around it with a rule the resolver does not have: `platform if platform in providers.shipped("publisher") else None` (the platform name doubles as the implementation name). Skills and the doctor do not get that rule, so they and the runtime resolve differently, against `providers/CONTRACT.md:18` ("Skills, the agent runtime and `scripts/doctor.py` all go through it").

What adding a provider file for a second platform forces today: every project sets `PUBLISHER_<PLATFORM>_PROVIDER` for both platforms, or `mkt-publish` and `mkt-engage` stop resolving `publisher:<first platform>`. That contradicts the adopted rule "adding a platform needs a reference file and at most a provider".

Fix: each implementation declares the sub-classes it serves (a constant read without importing, or a small `providers/<class>/<impl>.json`), and the resolver chooses among the implementations that serve the asked sub-class; the runtime's rule at `:186-187` goes away.

Plan: **not in plan** (decision 14a describes the two forms of a class; C0.2 edits the class list and the map, not the choice). C0.2 already rewrites this file and its tests: add it there; M. It touches no skill folder.

### RS2. should-fix. The doctor reports `publisher:<any platform>` as satisfied.

- `scripts/doctor.py:95-98`: `runner + ["--check"]`, with no `--platform`; `:116-127` resolves the class as RS1 describes. For a skill that requires `publisher:<other>`, the doctor runs the only publisher's `--check` and prints `provider`.
- `providers/CONTRACT.md:35` defines `--check` with no platform argument, so a provider cannot answer "do you serve this one".

Fix: `--check --platform <p>` in the contract for classes whose part after the colon is a parameter; the doctor passes it. Plan: **not in plan**. With RS1, C0.2; S.

### RS3. should-fix. The doctor ends in a traceback when a skill declares a class the resolver does not know.

- `scripts/doctor.py:157`: `provider_folder(c)` raises `UnknownClass`, caught nowhere (`check_class` catches it at `:122`, `secrets_report` does not). Checked: `secrets_report({'reader:email': {}})` raises `UnknownClass`.
- This is the state of the repository between the rename of a class in a skill's `requires` (phase C rows 44 and 46) and C0.2, if they merge in that order, and for any typo.

Fix: catch it and report the class as unknown; C0.2 merges before the skill rows. Plan: **partly planned** (C0.2 lists `scripts/doctor.py`; the order and the crash are not stated). C0.2; S.

### Resolution and doctor nits

- **RS4.** The resolver accepts classes the contract does not have: `scheduler:foo`, `mailbox:x` and a bare `publisher` all resolve (checked). `HEADS`' boolean ("True: the class always has a sub-class", `resolve.py:66-68`) is read only for `integration` (`:98`). `contracts/environment.md:35` promises exit 2 "on an unknown class". With the aliases of decision 14a this should become an exact list.
- **RS5.** `scripts/doctor.py:77-92, 106-113`: `env_provider`, `known_providers` and `check_provider` are called by nothing but `scripts/tests/test_doctor.py`. `:96` falls back to `python3 <script>` when `uv` is missing, against `providers/CONTRACT.md:62` ("never with the caller's interpreter").
- **RS6.** `contracts/environment.md:73` says the doctor lists the classes "the installed skills require"; `doctor.py:39, 44-61` reads the workbench's own `skills/`. The sentence "Flows run it before a phase" cannot hold for an installed skill (the plan's row 12 already removes the doctor from `core-orchestrator`).

Test gaps: no test of the doctor on an unknown class; none on a class with a parameter; `scripts/select_skills.py` is exercised only through `scripts/tests/test_installers.py:23, 36` (the default pack and an unknown pack): `area:` patterns, `!` exclusions, `--areas` and `--skills` have no test, and a pattern or a `--skills` name that matches nothing is silent (`select_skills.py:83-88`).

---

## 3. Publisher, mailbox, secrets

Contract conformance of `publisher/linkedin.py`, read item by item, holds for: `--help`; `--dry-run` before any credential or network use (`:737-738`, `:963-964`); refusal without `--confirmed` (`:727-732`, `:952-957`, `:989-990`); required idempotency key; the ledger written `pending` under a file lock before the request and `published` after (`:394-433`, `:658`, `:719`, `:844`, `:904`); a pending key blocks until `resolve` (`:666`, `:849-850`); the ledger in the data folder with 0600 and 0700 and the copy from the old cache location (`:312-368`); a timeout on every request (`:488-499`); redirects refused (`:475-485`); overrides only for a loopback base (`:233-244`); pinned PEP 723 header; credentials through the resolver (`:247-269`). `mailbox/gmail.py`: read only (one scope, only GET), `read-eml` without network or credential, redirects refused, loopback-only overrides, ids shape-checked. No `eval`, `exec` or subprocess in these files.

### Should-fix

- **PB1.** `--check` exits 1, not 3, when the token is missing or expired: `providers/publisher/linkedin.py:1106-1107` (`raise ProviderError(str(exc), EXIT_SERVICE)  # the contract: --check exits 1 when not ready`), pinned by `providers/publisher/tests/test_linkedin.py:577`; `providers/publisher/auth.py:121, 145`. `providers/CONTRACT.md:35` says 3. A rejected token does exit 3 (`:509-515`). The doctor shows both as `missing`, so a caller cannot tell "authorize" from "service down". **Not in plan**; phase A; S.
- **PB2.** `resolve` ignores `--dry-run`: `linkedin.py:989` checks only `--confirmed`, and `:1010` deletes the pending entry. `resolve --idempotency-key k --not-published --dry-run --confirmed` removes the block and the next run publishes again, while `providers/CONTRACT.md:36` says a dry run does nothing. This is the one path found that can lead to a second publication, and it needs the person to type both flags. **Not in plan**; phase A; S.
- **PB3.** Both OAuth callback servers are single-threaded with no handler timeout (`providers/publisher/auth.py:189, 198`; `providers/mailbox/auth.py:208, 226`): a local connection that sends nothing blocks the real callback, and `shutdown()` then waits forever. Read, not executed. **Not in plan**; phase A; S.
- **PB4.** The LinkedIn token exchange uses the default opener, which follows redirects: `providers/publisher/auth.py:218` (`urllib.request.urlopen(request, timeout=60)`), with the client secret in the body (`:206-212`); `providers/CONTRACT.md:41`. urllib does not resend the body on a redirect, but it accepts the redirect target's answer as the token. The mailbox's `auth.py` uses the refusing opener (`:232`). **Not in plan**; phase A; S.
- **PB5.** Both `auth.py --check` read the OS secret store directly (`providers/publisher/auth.py:115`, `providers/mailbox/auth.py:300`), against `contracts/secrets.md:7`; a token given through the environment is reported as not stored. **Not in plan**; phase A; S.
- **PB6.** A malformed `PUBLISHER_LINKEDIN_COMMENT_RETRY_DELAYS` is found only after the post is public: `linkedin.py:789` runs inside the first-comment step, after `publish_post` at `:742`; the test at `test_linkedin.py:926-931` pins it. Validate before the request. **Not in plan**; phase A; S.
- **PB7.** A core file names an AI tool and adapter paths: `providers/secrets/resolver.py:111-116` (`CLAUDE_CODE_OAUTH_TOKEN`, `"adapters/claude-code/run-prompt.sh"`, `store_username="claude-code-oauth"`), adapter paths also at `:108-109, 120, 125`; `contracts/secrets.md:23, 36, 37` (the variable, and "Claude models"). Principle 1 and "Never put a harness name, path or tool name in a core file"; principle 2 ("the core never reads adapters"). `scripts/validate.py:77-81` matches only the spelling with a space, so the check passes. Fix: an adapter registers its own secrets (a `secrets` list in `adapter.json` that the resolver merges when asked from outside the core), and the validator's pattern gains the hyphen and underscore spellings. **Not in plan** (A5 adds a warning for AI names in eval cases only). `evals/eval_run.py` reads this registry to fill `--pass-env`, so it belongs with phase B's runner work (B6a edits `contracts/secrets.md`), before the freeze; M.
- **PB8.** `contracts/secrets.md:11` says "the resolver's tests fail when the two disagree"; `providers/secrets/tests/test_resolver.py:86-90` only checks that each registry name occurs in the file and that reader paths exist. Drift already there: the row of `CLAUDE_CODE_OAUTH_TOKEN` (`secrets.md:36`) has three cells instead of five; the readers of `OPENROUTER_API_KEY` differ (`secrets.md:37` against `resolver.py:108`); the "Agent runtime (future ... not built yet)" row (`secrets.md:21`) describes a runtime that exists and reads through the resolver. **Not in plan**; phase A; S.

### Nits

- **PB9.** A dry run can write: reading the ledger migrates it (`linkedin.py:340-372`, asserted by `test_linkedin.py:1049-1052`), against "do nothing".
- **PB10.** A reused key with other content returns the old post with `replayed: true` (`linkedin.py:663-665`); the ledger keeps no payload hash, so a caller that ignores `replayed` reports new text as sent. `scripts/runtime.py:409-415` does not read `replayed`.
- **PB11.** `--check` wins silently over a verb (`linkedin.py:1170-1171`, `gmail.py:665`); irrelevant flags are accepted on every verb (flat parser, `linkedin.py:1139-1161`).
- **PB12.** `resolve --post-urn` accepts any `urn:li:` prefix (`:983`) while `comment` uses a strict pattern (`:919`).
- **PB13.** `ledger_save` has no fsync and leaves its temporary file if the dump raises (`:387-391`); an existing ledger folder with wider permissions is not tightened (`:398`).
- **PB14.** `providers/mailbox/gmail.py:422`: text hidden by CSS is returned as message text (the fixture's `display:none` block reaches `text`); the output carries no field that marks content as external, the statement exists only in `--help` and the README.
- **PB15.** `publish --comments-endpoint` and `--legacy-v2` (`linkedin.py:1151, 1154`) are not in `providers/CONTRACT.md:68`; `--legacy-v2` is honoured by `comment` (`:950`) and ignored by `publish` (`:725`). The contract writes `--media <path>...`; the code refuses more than one (`:593-594`).
- **PB16.** Principle 6: `providers/publisher/tests/test_linkedin.py:982` writes a Portuguese word (an informal "thanks") as test text. History of one case, without names (allowed by the narrowed decision 11, against `AGENTS.md` as written today): `linkedin.py:806-809` ("decided by the user on 2026-09-30 after a real test with the member token"), `providers/publisher/README.md:66`, `providers/mailbox/README.md:5`.

Principle 8: no real person, account, handle or project name in these three folders, tests and the `.eml` fixture included (it uses `example.com`, "Zoë Example", "Alex Sample").

Test gaps: `publisher/auth.py` has no test of the callback, the state check or the exchange (the mailbox has them); no test of `resolve --dry-run`; a post answered 5xx or 2xx without an id staying `pending` is tested only for comments; no test of the upload-host check (`linkedin.py:537-545`), of the lock-wait timeout, of a corrupt ledger, of `--media` validation, of a loopback check against `http://127.0.0.1@host`.

---

## 4. Scheduler

Conformance holds for: `--help`; `--dry-run` with no write (`launchd.py:490-496`); refusal without `--confirmed` (`:474-479`, `:563-564`); the digest checked after re-planning and the copies re-hashed (`:497-500`, `:446-450`); a timeout on every subprocess; 0600 and 0700; test binaries only with `SCHEDULER_TEST=1` (`:195-201`); the 3.9 header and syntax; `--every` 5 to 1440; re-verification at every firing with refusal and unload (`:768-789`); the run log. No shell anywhere; unit-file and notification text escaped.

### Should-fix

- **SC1.** A one-shot command that prints bytes that are not UTF-8 leaves the job `running` for ever. `launchd.py:819-822` (`subprocess.run(..., text=True, ...)`, `except (OSError, subprocess.TimeoutExpired)`); the same at `systemd.py:949-952`. Reproduced by the scheduler reviewer with a fake `launchctl`: `UnicodeDecodeError`, `job.json` stays `"status": "running"`, no notification, no log. The post may be out. **Not in plan**; phase A; S.
- **SC2.** A job in `running` can be neither cancelled nor scheduled again: `launchd.py:569-573` changes only a `scheduled` job; `:485-486` refuses the id. Reproduced: `cancel --confirmed` exits 0 and the status stays `running`. After SC1, a kill or a power loss, the id is blocked until `job.json` is edited by hand. The contract gives publishers a `resolve` verb for an unknown outcome; the scheduler has none. **Not in plan**; phase A; S to M.
- **SC3.** On macOS a recurring command can outlive its runner and overlap the next firing: the command runs in its own session (`launchd.py:713-714`, `start_new_session=True`), launchd kills only the job's own process group, and the next firing takes the free lock and records `stale_lock_pid` (`:670`, `:765-766`). `providers/scheduler/README.md:31` says "No overlap". For the tick, `runtime.py`'s own lock (`:587-594`) still excludes a second tick, so the effect is a skipped tick, not two; for another recurring job there is no such second lock. Read, not reproduced. **Not in plan**; F2 (N12); M.
- **SC4.** File arguments in other spellings run unverified: only a bare path and `--flag=path` are recognised (`launchd.py:326-331`); `-f/abs/file`, `key=/abs/file` and `a,b` lists pass through with an empty snapshot (reproduced by the reviewer). `providers/CONTRACT.md:89`: "A file argument that is not snapshotted makes the job refused". **Not in plan**; phase A; S (refuse what is not understood, or state the two forms in the contract).
- **SC5.** The one-shot path has a fixed 600 s limit that no document states (`launchd.py:67, 819-820`), kills only the direct child (`uv`, not the provider) and keeps no output on timeout; `timeout_minutes` is silently dropped for `--at` (`:305-308`). `scripts/vote_job.py:39, 89, 131` allows itself 600 s for the publish alone, then three reads and a commit of 600 s: the job can be recorded `failed` with nothing kept while the post is out. **Not in plan**; phase A; S.
- **SC6.** An early one-shot firing is never tried again on launchd: `launchd.py:803-805` returns and the plist holds local wall time (`:415-418`). A change of the system time zone between scheduling and the slot fires the job early; it then shows `scheduled` until it is `missed` a year later. systemd uses UTC. **Not in plan**; F2 (N12); S.
- **SC7.** The two scheduler files hold 27 functions that are textually identical today (`load_command_file`, `snapshot_argv`, `changed_since_approval`, `acquire_lock`, `kill_group`, `copy_verified`, `parse_iso`, `main` and others) and only the digest has a parity test (`providers/scheduler/tests/test_systemd.py:166-181`). A fix to the snapshot or the lock in one file can miss the other. **Not in plan** (C0.3 builds the generated-copies mechanism for skill scripts; these two could join its manifest, or get an identity test). Phase A; S.
- **SC8.** The scheduler knows a publisher's output field: `launchd.py:593, 828-829` and `systemd.py:727, 958-959` read `post_url` from the command's stdout for the notification. See CT3 (the output shape of a verb is stated in no contract). **Not in plan**; phase A; S.

### Nits

- **SC9.** `launchd.py --check` never exits 3 and does not probe the user's launchd domain (`:835-847`); `systemd.py` does (`:970-995`). `run_launchctl` does not catch `OSError` (`:206-211`).
- **SC10.** `--id` accepts a trailing newline: `ID_PATTERN` ends in `$` and is used with `.match` (`launchd.py:70`, `systemd.py:87`).
- **SC11.** One-shot "at most once" is a read then a write with no lock (`launchd.py:797, 814-816`); `cancel` writes with no lock (`:562-572`).
- **SC12.** `grace_minutes: true` is accepted and has no upper bound (`launchd.py:306`); a naive `--at` is taken as local time though the help says "with offset".
- **SC13.** `providers/scheduler/README.md:3` gives the interface as `schedule ... [--approved <digest>]`, `cancel --id <id>`: `--id`, `--dry-run` and `--confirmed` are missing and `--approved` reads as optional. The `run` verb, `cancel --dry-run` and the command file's keys (`argv`, `cwd`, `snapshot`, `outputs`, `grace_minutes`, `timeout_minutes`) are in no contract row (`providers/CONTRACT.md:76`).
- **SC14.** Unbounded growth: one-shot output is buffered whole and written unbounded; `launchd.err.log`, `notifications.jsonl` and `.history/` are never pruned. All are 0600; `stdout_tail` holds whatever the command printed.

Principle 8: no real name in code, tests or README.

Test gaps: id validation of any kind; the one-shot timeout and non-UTF-8 output; cancel of a `running` job; the SIGTERM path; `launchd --check`; log rotation; unsupported argument spellings; two concurrent `run` calls; drift between the duplicated functions; `systemd.py` on a real systemd (the README says so; plan N12).

---

## 5. Contracts and the design rules: what a second social platform forces today

Each place is classified: **data** (belongs in `shared/references/platforms/<platform>.md` or `.json`), **verb** (a provider verb, flag or declaration is missing), **handler** (per-agent code the plan's F2 moves behind a handler), **acceptable**.

| # | Place | What is hardcoded | Class | Plan |
|---|-------|-------------------|-------|------|
| 1 | `providers/resolve.py:190-195` | one implementation serves every sub-class; two serve none | verb (a declaration of served platforms) | not in plan (RS1) |
| 2 | `scripts/doctor.py:95-98` | `--check` without the platform | verb | not in plan (RS2) |
| 3 | `scripts/runtime.py:186-187` | platform name equals implementation name | verb (goes with 1) | not in plan |
| 4 | `providers/CONTRACT.md:68` | the publisher verbs speak one platform's identifiers: `--post-urn`, `--comment-urn`, `--parent-comment <comment urn>`; `--first-comment-file`; media optional | verb (neutral names) | not in plan (CT1) |
| 5 | `scripts/runtime.py:342-353, 402, 405-407, 538-540` | `comment_urn`, `post_urn`, `parent_comment_urn` as the runtime's own field names and publisher flags | verb, then handler | partly (F2) |
| 6 | `scripts/runtime.py:537` | an idempotency key derived by cutting a comment URN at its last comma | data or handler | not in plan |
| 7 | `scripts/runtime.py:288` | reply limit 1500 characters | data | not in plan (CT2) |
| 8 | `scripts/runtime_vote.py:40, 148` | post limit 3000, first comment 1250 | data | not in plan (CT2) |
| 9 | `scripts/runtime_vote.py:315-316` | image 1080 by 1350 | data | not in plan (CT2) |
| 10 | `scripts/runtime_vote.py:116`, `scripts/runtime.py:272` | `<PT\|EN>` in the task text | handler (the project's languages) | partly (F2) |
| 11 | `scripts/vote_job.py:65` | `--platform` defaults to `linkedin`; docstring `:6, 8` names the provider files | acceptable once the default is removed | not in plan; S |
| 12 | `scripts/vote_job.py:90`; `providers/scheduler/launchd.py:593, 828` | the publisher must print `post_url` | verb (output shape in the contract) | not in plan (CT3) |
| 13 | `providers/mailbox/gmail.py:68` | `HEADER_PREFIX_ALLOWED = "x-linkedin-"` in the generic mailbox provider | data (`--header-prefix`, from the platform's data file) | not in plan; S |
| 14 | `scripts/runtime.py:88-91, 191-192, 255-274, 387-391` | `mkt-engage`'s scripts, block name, categories, task text, file paths | handler | planned (F2, backlog R1) |
| 15 | `scripts/runtime_vote.py:39, 79-91, 190-192`; `scripts/vote_job.py:38, 99` | four skills' scripts and one repository layout (`data/pick.json`, `data/pick-queue.json`, `data/posts.json`, `assets/posts/`) | handler and a contract | partly planned (default 67 creates `contracts/vote-data.md`; F2) |
| 16 | `scripts/runtime.py:16, 155-163` | one `publisher` key: one platform per project runtime | handler (configuration shape) | not in plan |
| 17 | `agents/social-manager.md:17, 35` | "one social network"; "comment URN" as the source label | data (the word) | not in plan; S |
| 18 | `scripts/runtime.py:333, 468, 557` | calls `parse_notification.py` with no platform | verb | planned (row 44, decision 14c) |
| 19 | `contracts/environment.md:15`, `contracts/state.md:38`, `providers/CONTRACT.md:12, 22`, `providers/resolve.py:9, 25, 33` | a platform's name as the example of the class | acceptable as examples; C0.2 already removes the one in the class row | partly planned (C0.2) |
| 20 | `providers/secrets/resolver.py:68-85`, `providers/publisher/linkedin.py` | the implementation's own credentials and API | acceptable (an implementation) | n/a |

### CT1. should-fix, to decide before the round. The publisher class's contract is written in one platform's vocabulary, and a skill's procedure repeats it.

- `providers/CONTRACT.md:68`: `comment ... (--on-key <post key> | --post-urn <urn>) [--parent-comment <comment urn>]`, `resolve ... (--post-urn <urn> | --comment-urn <urn> | --not-published)`.
- `skills/mkt-engage/SKILL.md:68` writes the command with `--post-urn <post_urn> --parent-comment <comment_urn>`; `policy_gate.py` and the skill's cases use the same field names.
- Decision 14b, rule 2: "A skill's procedure names no social platform." A URN is that platform's identifier. A second platform has post ids or links, and the class contract would need either new flags per platform or a rename.

A rename after the round stales `mkt-engage`. So the choice (neutral names such as `--post <id>` and `--reply-to <id>`, with the old flags kept as aliases in the first implementation, or the URN words accepted as the class's vocabulary) belongs **before the round**: C0.2 for the contract's verbs table, row 44 for the skill. **Not in plan.** M.

### CT2. should-fix. Limits of a platform live as constants in the runtime.

`scripts/runtime_vote.py:40` (`MAX_POST = 3000`), `:148` (1250), `:315-316` (1080, 1350), `scripts/runtime.py:288` (1500). Decision 14c puts "length limits" in `shared/references/platforms/<platform>.json`, read "through a path given by flag". The plan's rows 44, 46 and 48 make the runtime pass `--platform` and `--platform-file` to the skills' scripts; nothing says the runtime's own copies of the limits go. **Partly planned.** They are in `scripts/`, so no skill is staled: same pull requests as rows 46 and 48, or F2; S.

### CT3. should-fix. What a provider prints is stated in no contract, and three callers depend on it.

`providers/CONTRACT.md:37` says "Data to stdout as JSON" and nothing about its keys. Depended on: `post_url` (`scripts/vote_job.py:90`, the two schedulers), `approved` of the scheduler's dry run (`scripts/runtime_vote.py:421`), `content` of `read-file` (`runtime_vote.py:194`, `vote_job.py:102`), `replayed`, `commit`, `unchanged`, the store's `id`, `run_id`, `claim_token`, `created`. A second publisher has to be read against the first implementation to know what to print. Fix: a "prints" column in the verbs table. **Not in plan**; phase A or C0.2 (same file); S.

### CT4. should-fix. Two homes for approvals, and the contract names one.

`contracts/environment.md:53, 66-67` and `contracts/state.md:54`: approvals are recorded in `docs/workbench/state.md` under "Approvals", with `Payload hash` and a status that moves to `executed`. The runtime records its approvals in the store (`inbox-resolve`, `action-add`; `scripts/runtime.py:544-546`, `scripts/runtime_vote.py:423, 446`) and writes nothing to the state file; `contracts/runtime.md:45-50` says so for itself and `environment.md` does not mention the inbox. A skill that "checks this table before asking" does not see what the person approved in the inbox, and the reverse. **Partly planned** (R5, "approval inbox made generic", F2). Add one paragraph to `environment.md` now (phase A, S): which approvals live where, and that the store's inbox is the record for runtime items.

### CT5. should-fix. `contracts/runtime.md` promises more than the code does in three places.

- `:39` "the gate is code, bound by hash to what the person approved" (RT5).
- `:22` the daily cap "checked before each run" (RT2).
- `:20, 32` "read access to the project folder" for the agent: the runtime passes `--project`; how far the model can read is the adapter's doing (N15).
**Partly planned** (F2 rewrites this contract for R1; N15). Until then the three sentences should say what holds; phase A; S.

### Contract nits

- **CT6.** `providers/CONTRACT.md:66-77` lists verbs for classes with no implementation (`mailer`, `generator:image`, `generator:video`, `search:web`, `integration:issue-tracker`) although `:79` says "Add a verb when a skill needs it, together with the skill".
- **CT7.** `contracts/project-layout.md` has no entry for `docs/workbench/runtime.json` or for `.workbench-local/payloads/` (`contracts/environment.md:57` names the second). The plan's row 44 adds the first as a `user` slot (planned); the second is not planned.
- **CT8.** `contracts/environment.md:57`, the paragraph "The approval binds a hash of the payload", is one sentence block of about 300 words holding seven rules; against the writing standard ("checklists ... for anything with more than three steps"), and it is what a floor model must follow. Not planned; phase A; S.
- **CT9.** `agents/social-manager.md` repeats the category names and the block shape that `scripts/runtime.py:89-91` and `mkt-engage` also hold: three copies, one edited by hand. Planned in spirit (F2 handler).
- **CT10.** `packs/README.md:22` and `AGENTS.md` say adapters take `--areas`; `packs/` itself holds no test and is not scanned as core today (planned: A5).
- **CT11.** `scripts/redact.py:6-8` names one skill's script in its docstring (planned: default 78). Its formats do not include a Google OAuth client secret or refresh token; B6a redacts by value, so this only matters for the security scan.

---

## 6. Principle 8 in the reviewed folders

No name of a real person, project, account or handle was found in `providers/`, `contracts/`, `agents/`, `packs/`, the three runtime scripts, `doctor.py`, `select_skills.py`, `redact.py` or their tests (greps for the maintainer's names and projects, for e-mail addresses outside reserved domains, for profile links and repository owners). What remains, all nits:

- `providers/vcs/README.md:28-31, 45, 57` and `providers/vcs/github.py:213-221` use `octo-org/web` and `octo/octo` as example repositories; both are existing accounts on the code host (the host's own documentation examples). A reserved-looking fictional owner would be cleaner.
- One repository's layout, without a name: `data/pick.json`, `data/pick-queue.json`, `data/posts.json`, `assets/posts/` in `scripts/runtime_vote.py:39, 190`, `scripts/vote_job.py:38, 99`, `providers/vcs/README.md:45`, `providers/vcs/github.py:220`, and the words "the profile repository" (`scripts/vote_job.py:2`, `scripts/runtime_vote.py:106`). Under the narrowed decision 11 this is not an identifier; it is covered as coupling (row 15 of the table above; plan A3 for the backlog text and default 67 for the contract).
- History of one case with dates and no names: `contracts/secrets.md:23, 43`, `contracts/runtime.md:3`, `providers/CONTRACT.md:40`, `providers/scheduler/README.md:85, 95`, `providers/publisher/linkedin.py:806-809`. Allowed by the narrowed decision 11; against `AGENTS.md` as it reads until A10.
- `scripts/tests/test_runtime.py:232`: a test reply with one case's figure ("I still measure 3.7 kB"); a number, allowed.

---

## 7. Where the uncovered findings belong in the plan

| Phase | Findings | Why there |
|-------|----------|-----------|
| Before the round, C0.2 | RS1, RS2, RS3, CT1 (contract side), CT3 | C0.2 already rewrites `resolve.py`, `doctor.py` and the verbs table of `CONTRACT.md`; CT1 decides flag names a skill's procedure repeats |
| Before the round, row 44 (`mkt-engage`) | CT1 (skill side), RT7 if the check goes into `policy_gate.py` | they change a skill folder |
| Before the freeze, phase B | PB7 | `evals/eval_run.py` reads the secrets registry; B6a already edits `contracts/secrets.md` |
| Phase A | RT8, PB1 to PB6, PB8, SC1, SC2, SC4, SC5, SC7, SC8, VS1 to VS8, CT4, CT5, the nits | no skill folder, no frozen file |
| Phase F, lane F5 | VS9 | new evidence for backlog T15 |
| Phase F, lane F2 | RT1 to RT6, RT9, SC3, SC6, CT2, table rows 6, 11, 13, 16, 17 | the runtime, after decision 10; RT1, RT2 and RT4 should not wait for the generic rewrite, since they are defects of what runs today |

Sizes: all S except RS1 (M), RT5 (M), PB7 (M), CT1 (M), SC2 (S to M), SC3 (M), VS1 (M), VS4 (M, with PB1 and SC9).

Nothing found here changes what an eval run measures, so none of it moves `measurement_version`. The only items that touch a skill folder are CT1 and, by choice, RT7.

---

## 8. Vcs and store

Conformance of `providers/vcs/github.py` holds for: `--help`; the dry run of `dismiss-alert` (no token, no request, `:681-689`); refusal without `--confirmed` (`:670-675`, `:750-751`, `:1215-1218`); a required key; the ledger claimed under a lock before the request or the clone and marked done after (`:387-416`, `:693`, `:729`, `:1227`, `:1259`); the data folder, the modes and the copy from the old location (`:309-361`); a timeout on every request and every git call (`:489`, `:944`); redirects refused (`:465-475`); overrides only for loopback or with `VCS_TEST=1` (`:254-265`, `:897-915`); the pinned header; the token only through the resolver. No token ever reaches git: the remote is `git@github.com:<repo>.git` (`:117`), nothing is put in a URL, in argv or in `.git/config`. `--repo`, `--branch`, `--path` and `--ref` are validated; traversal, absolute paths and `.git` parts are refused (`:789-807`); symlinks in the clone are not written through (`:1005-1013`); a rejected push is retried once only for `[rejected]` (`:1068-1069`), so the retry cannot commit twice.

Conformance of `providers/store/sqlite.py` holds for: the 3.9 header and syntax; `--db` with `$STORE_SQLITE_PATH` and exit 3 without either (`:328-331`, `:741-748`); `--check`; every statement with `?` parameters; 0600 and 0700. `event-next` claims in one `BEGIN IMMEDIATE` transaction (`:520-533`); `event-done` checks the token (`:544-556`); events and actions are unique by key (`:88`, `:126`); inbox transitions go forward only (`:60`, `:641`); timestamps are fixed-width UTC, so the text comparison of `action-count --since` is right.

### Should-fix

- **VS1.** A push whose connection dies after the remote took the commit releases the idempotency key. `providers/vcs/github.py:961-962` (`SSH_FAILURES`, matched as substrings: "Connection timed out", "Operation timed out", ...), `:965-973` (`ssh_failure` returns `NotPushed`, documented as "nothing was sent"), `:1071` (applied to the stderr of a push that already started), `:1247-1249` (`except NotPushed: ledger_update(key, None)`). Reproduced by the vcs reviewer with a git wrapper that pushes and then prints such a line: the remote moved and the ledger was empty. `providers/CONTRACT.md:39` asks that an unknown outcome stay pending. The damage is bounded (a rerun usually finds the files unchanged), unless the branch changed them meanwhile, in which case old content is committed again. Fix: once the push has started, an SSH failure is "outcome unknown". **Not in plan**; phase A; M with its test.
- **VS2.** What is committed and pushed is never compared with the approved hashes. `:1032` runs `git commit` with the user's hooks (no `core.hooksPath` override and no `--no-verify` in the file); `:1043-1045` checks only path names. Reproduced: a global `pre-commit` hook changed the file's content and the provider printed the original sha256 with `"pushed": true`; a `.gitattributes` line-ending rule gave a committed blob with another hash than the one printed. For the weekly vote the person approves a bundle whose hashes include the queue file (`scripts/runtime_vote.py:407`); what lands in the repository can differ. Fix: hash the blobs of `HEAD` before the push and refuse a difference; say in the contract that the user's hooks run, or disable them. **Not in plan**; phase A; S.
- **VS3.** `git_env()` hands the caller's whole environment to git (`:919`). Reproduced with `GIT_DIR` set, as it is when a provider is started from a git hook: `commit-files --confirmed` made a signed commit in that other repository. The same line gives `VCS_GITHUB_TOKEN` to git, ssh and every hook. Fix: drop the `GIT_*` variables and the registered secrets from the environment given to git. **Not in plan**; phase A; S.
- **VS4.** `--check` never exits 3: `:1272-1273` (`raise ProviderError(str(exc), EXIT_SERVICE)  # the contract: --check exits 1 when not ready`), `:1277-1278`; pinned by `providers/vcs/tests/test_github.py:580-588`. The same drift as PB1; the two identical comments show the code was written against another reading of `providers/CONTRACT.md:35`. Decide the contract once, then fix the two providers, `launchd.py --check` (SC9) and their tests. **Not in plan**; phase A; M for the three together.
- **VS5.** `--branch` accepts a tag name and the push then creates a branch of that name: `:989` (`clone --branch <b>`, which also takes tags), `:1056-1057` (`HEAD:refs/heads/<b>`). Reproduced: `--branch v1` with a tag `v1` printed `"pushed": true` and the remote had a new `refs/heads/v1`. **Not in plan**; phase A; S.
- **VS6.** SIGTERM skips the cleanup and git outlives the provider: git runs in its own session (`:940`), the clone folder is removed in a `finally` (`:994-995`) and there is no signal handler. Reproduced: exit 143, the clone folder left behind, and the push landed three seconds after the provider died; the ledger stays pending (the safe side) without the attempted commit's hash. This is what the scheduler does to a one-shot job at its limit (SC5). **Not in plan**; phase A; S.
- **VS7.** The dry-run rule contradicts itself for `commit-files`: `providers/CONTRACT.md:36` ("no credential is read and no network call is made") against `:74` (its dry run "clones read-only"), which the code follows (`github.py:1160-1165`) with the user's SSH key. Also missing from the row: `resolve` needs `--confirmed` (`github.py:750`); `--ref` takes a tag or a sha. And `contracts/secrets.md:29` lists only the Dependabot permission for `VCS_GITHUB_TOKEN`, while `read-file` needs "Contents: Read-only" (`github.py:181`). **Not in plan**; C0.2 (the same table) or phase A; S.
- **VS8.** `inbox-add` and `action-add` store `--payload-sha256` without comparing it with anything (`providers/store/sqlite.py:610, 657`; reproduced with a wrong hash), while `providers/store/README.md:19` calls it the payload's SHA-256 and `scripts/runtime.py:423` passes the hash of another file (the reply) when there is one. Say in the contract what the field is (the hash of what the person approves, which may not be the stored payload), or check it. See RT12. **Partly planned** (R5 in F2 makes the inbox generic); phase A for the sentence; S.
- **VS9.** Concurrent `init` fails when the folder does not exist yet: `sqlite.py:450-451` (`if not path.parent.exists(): path.parent.mkdir(mode=0o700, parents=True)`, no `exist_ok`). Reproduced by the reviewer: 43 of 240 concurrent inits exited 1 with "File exists". It is not shown to be the CI failure of backlog T15 (that test uses an existing folder, and 480 concurrent inits in an existing folder gave no error on macOS); the candidates left for T15 are `enable_wal`, which retries only messages with "locked" (`:369`), and `BEGIN IMMEDIATE` with no retry (`:351`). **Partly planned** (F5, T15): a second, confirmed cause to fix there; S.

### Nits

- **VS10.** `--reclaim-after-minutes 0` is accepted (`sqlite.py:515`) and takes every live claim; there is no cap on `attempts`, so an event whose run always crashes is reclaimed for ever (`:521-524`). `inbox-add` has no dedupe, so an event escalated twice makes two items.
- **VS11.** Out-of-range integers end in a traceback (`OverflowError`, `sqlite.py:829-837`); `--since` forms such as `-0300` or a fractional `Z` time are refused on Python 3.9 and accepted on 3.11 (`:230`), and the runtime runs on 3.9.
- **VS12.** `actions` (limit 1000) and `inbox-list` (100) cut their output silently (`:625`, `:678-679`); `scripts/runtime.py:514-518` (`open_item`) looks for an item in that list, so an open item past the hundredth can be neither approved nor rejected.
- **VS13.** In `--allow`, `*` matches dotfiles (`github.py:826`), so `--allow '*'` admits `.gitattributes`.
- **VS14.** Any `!` line of the push report other than `[rejected]` releases the key (`:1066-1070`); git also prints `!` for a remote that did not report, which is an unknown outcome. Not reproduced.
- **VS15.** `main` catches only `ProviderError` (`github.py:1349-1351`): a bad `VCS_GIT_TIMEOUT` or a ledger that is not an object ends in a traceback. Replaying a dismissed key needs a token (`:691` before `:693`). `read-file` has no size cap of its own (`:490`).
- **VS16.** Caller knowledge in documents and tests only: `providers/vcs/README.md:9, 45, 57-61` and `github.py:220-224` (the weekly vote, `data/pick.json`), `providers/vcs/tests/test_github_files.py:209, 286, 374`; `providers/store/README.md:5, 41, 47` and `sqlite.py:182-183` (`social-manager`); `providers/store/tests/test_sqlite.py:64, 405-439` (one platform's URN format). Neither provider's logic knows a caller, a kind or a platform.
- **VS17.** `--limit` of `inbox-list` and `actions`, the `status` field of `event-add` and the `repo` field of `read-file` are missing from `providers/CONTRACT.md:74, 77` (see CT3).

Test gaps: an inherited `GIT_DIR`; a user hook that alters the commit; a tag as `--branch`; the token absent from git's environment; SIGTERM during clone or push; an SSH failure text after the push started; the redirect refusal on PATCH; concurrent `init` with a missing folder; concurrent `action-add` with one key and concurrent `inbox-resolve` on one item; `--payload-sha256` against the payload either way.
