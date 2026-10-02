# Review of `docs/architecture/final-plan-2026-10-02.md` against the code and the architecture

Read-only review, 2026-10-02, a working tree of the repository at `c8bf70f`. Nothing in the repository was changed. "Plan:N" is a line of the plan; every other reference is `file:line` in the worktree.

Commands run (read-only): `python3 providers/resolve.py --list`, `python3 evals/eval_status.py status` (33 evaluated, 15 stale, 0 draft, version 4: matches the plan), `python3 scripts/validate.py` (0 errors, 3 warnings: matches Plan:51), greps.

Severity: **blocker** = rework, a broken install, or a second measurement of many skills; **should-fix**; **nit**.

## Summary table

| # | Severity | Finding | Smallest change to the plan |
|---|----------|---------|-----------------------------|
| 1 | blocker | `shared/references/` is in the measurement fingerprint, so adding or editing a platform reference fails `validate` until the version is raised (all 48 stale): the opposite of 14c | Fingerprint covers `shared/references/` without `platforms/`; a platform reference is covered only by the hash in the record |
| 2 | blocker | A platform-tagged case in `evals.json` is inside the skill's content hash: adding a platform makes the skill `stale`, and `--platform` cannot write a record | Later platforms' cases in `evals/platforms/<platform>.json`, outside the hash, with their own record section; base gate untouched |
| 3 | blocker | "role then target" folders collide with "the sub-class is passed as `--platform`" for `publisher` and `generator` | Name two kinds of role in 14a: target is the class's identity (folder per target, one variable) or an argument (one folder per role, two variables) |
| 4 | blocker | C0.2 lists two files and size S; the provider move silently breaks test discovery, the hook, the 3.9 guard, the providers' secret lookup, a scheduled workflow and the runtime | List the files (below) in C0.2, size M, with a test that every provider test folder is discovered |
| 5 | blocker | `../../shared/...` resolves in eval and run-agent layouts only; in installs it is absent (copy) or tool-dependent (symlink); the plan says both "C0.9" and "after the round", and names `install.sh` where the file is `build.py` | Ship `shared/` in C0.9 (before the round), name `build.py`, add an installer test, say who owns `~/.agents/shared` |
| 6 | should-fix | The without-skill baseline can receive the platform reference | B2: `shared/references/platforms/` is staged only into with-skill runs |
| 7 | should-fix | The API adapter sends only `SKILL.md`: a runtime agent cannot read a platform reference | Decide in phase C how Runtime mode gets the reference (the task file carries it) |
| 8 | should-fix | Recurring jobs already scheduled, `runtime.json` keys and variables on users' machines: no migration stated | One paragraph in 14a: what keeps its name, what must be rescheduled |
| 9 | should-fix | Per-platform parsers are code inside skill folders; "a data table, never code" and "only that platform is measured" cannot both hold; callers of the scripts that gain `--platform` are not listed | State the exception or move parsers behind a provider; list `scripts/runtime.py`, `runtime_vote.py`, `vote_job.py` |
| 10 | should-fix | `validate.py --strict` turns every warning into an error; the plan allows `draft` skills and permanent warnings after the round | A flag that makes only eval-status strict, or make those warnings non-warnings |
| 11 | should-fix | The fingerprint leaves out the executor, the staging code and `adapter.json`; B8 and B10 disagree on where refusal markers live | Staging in one module that is fingerprinted and that F3 imports; markers in one place |
| 12 | should-fix | B2 staging trips the adapters' own "case folder already holds harness settings" refusal | Move that check to the runner, before staging; folder names from `adapter.json` |
| 13 | should-fix | Default 57 (mkt-engage drops the mailbox class but keeps using it) contradicts default 54 (every class used is declared) | Declare it, or remove the mailbox line from the body |
| 14 | should-fix | `AGENTS.md` says "numbers go" in three places; A4 rewords one | A4 lists lines 14, 139, 157 and the authoring guide |
| 15 | should-fix | F3 "both installers install the stripped copy": one installer has no copy mode | Say that the claude-code build copies instead of linking |
| 16 | nit | Six smaller items (A6 phase, record field name, A1 file exists, gate fields, A8 timing, C0.2 touches skills) | see section 16 |

---

## 1. Blocker: the freeze covers `shared/references/`, which 14c says can grow without measuring anything else

**Evidence.**
- Plan:270 (default 21): "`shared/references/` is covered by the measurement fingerprint". Plan:431 (B10): the fingerprint is "the hash of the grading template, every file of `evals/container/`, the two `run-prompt.sh`, `measurement.json` and `shared/references/`; `validate.py` recomputes it and fails when it differs". Plan:588: a change to "the shared references" fails "until the version is raised (which stales all 48)". Plan:789 repeats it under "What would make a second round necessary".
- Plan:253-257 (14c): references live at `shared/references/platforms/<platform>.md`; "adding a reference makes no skill stale"; "Adding a platform runs only that platform's cases". Plan:246 (14b rule 3): "only that platform is measured".
- Both mechanisms act on the same folder. The record's per-platform reference hash (Plan:257) and the global fingerprint (Plan:431) cannot both be the authority.

**Consequence.** The first platform added after the round turns `validate` red; the only exits the plan gives are raising the version (48 stale, a second round) or "recording that it measures the same", which is the discipline option decision 3 rejected.

**Smallest change.** In default 21, B10, Plan:588 and Plan:789: the fingerprint covers `shared/references/` except `platforms/`. A platform reference is covered by `reference_sha256` in the record of each skill measured with it (finding 2). One sentence in 14c says so.

## 2. Blocker: a platform-tagged case lives inside the hashed skill folder

**Evidence.**
- `evals/eval_status.py:149-172` (`content_hash`): everything in the skill folder is hashed except `evals/result.json`, `scripts/tests/`, caches. `evals/evals.json` and `evals/files/**` are inside.
- `evals/eval_status.py:413`: `rec["content_sha256"] != content_hash(skill_dir)` → `stale`.
- `evals/eval_run.py:1385` (`full = ... not o["cases"] and not o["only"] ...`) and `:1421-1422`: a run of a subset of cases never writes a record. `evals/eval_status.py:273-287` (`build_record`): refused when any case of `evals.json` has no graded run. `:334` (`update_baseline`): refused when the record's hash is not the current one.
- `evals/eval_status.py:93-95, 230, 249-257`: a record has four scores and `gate` must equal `gate(scores, ...)`; there is no place for a second set of scores.
- Plan:428 (B7a): "`eval_run.py --platform <name>` runs only that platform's cases and merges them into the record". Plan:257: "The gate of a skill is computed on its untagged cases and on the platforms measured".
- The cases of the three marketing skills are all about the one platform (2, 4 and 3 cases in `mkt-publish`, `mkt-engage`, `mkt-vote-round`; their scripts carry that platform's URL shapes, `skills/mkt-vote-round/scripts/vote_update.py:43-70`). If "cases that test one platform are tagged" (Plan:472), those skills have no untagged case.

**Consequence.** Adding a case for a new platform to `evals.json` changes the hash: the skill is `stale`; after the round `--strict` makes that pull request red until the whole skill is measured again. For `--platform` to "merge", it would have to write the new `content_sha256` without measuring the untagged cases on the new content, which makes `evaluated` ("the gate passed on the current content", `eval_status.py:416`) false. And a platform whose cases fail would pull an `evaluated` skill to `draft` if the gate pools platforms.

**Smallest design that works.**

1. Cases of a platform added after the round live in `skills/<name>/evals/platforms/<platform>.json`, fixtures under `skills/<name>/evals/platforms/<platform>/files/`. `content_hash` skips the prefix `evals/platforms/` (one more line beside `TESTS_REL`, `eval_status.py:159`). The reason is the one already written for `scripts/tests/` (`eval_status.py:35-36`): the adapters remove `evals/` whole (`adapters/claude-code/run-prompt.sh:58`, `adapters/agents-dir/run-prompt.sh:52`), so no model reads them and they change nothing the base cases measure.
2. The cases of the first platform stay in `evals.json` for this round (they are the base; an informational `"platform"` tag is fine). The base record gains `platform_references: {"<platform>": "<sha256 of the reference>"}`; `skill_status` reads `stale` when that hash differs. So editing the first platform's reference stales the seven skills measured with it, and nothing else.
3. The record gains an optional `platforms: {"<platform>": {"reference_sha256", "cases_sha256", "cases", "runs", "date", "iteration", "scores": {four variants}, "complete", "gate"}}`. `record_problems` (`eval_status.py:179-232`) accepts and checks it. It is written by a new function modelled on `update_baseline` (`eval_status.py:319-365`): refused unless the base record is of the current content hash, measurement version and models.
4. The base status and `gate()` are unchanged and computed on `evals.json` only. A platform has its own status: `passed`, `failed`, `stale` (its reference or its case file changed), `not measured`. It is shown in the status table and is never a `validate` warning (finding 10), so adding a reference does not turn CI red for seven skills.
5. `eval_run.py --platform <p>`: `load_evals` (`eval_run.py:346`) reads the platform file; the `full` test (`:1385`) gets a second branch that writes only the platform section; `case_files` (`:379`) already confines fixtures to the skill folder. `validate.py`'s `check_eval_cases` (`scripts/validate.py:414`) runs the preflight on platform files too.
6. Where a script's "data table" lives must be said (Plan:255 does not). Beside the script it is inside the hash, and adding a row stales the skill. Either put it in `shared/references/platforms/<platform>.json` and give scripts `--platform-file <path>` (needed anyway in a scheduled job's flat snapshot, finding 9), or state in rule 3 that a skill whose script needs the platform's rules is measured in full when a platform is added.

Also rename one of two things both called "platform": B7 puts the image's CPU platform in the record (Plan:427, "tool versions, platform, image digest") and B1 fixes "the platform" in the executor (Plan:421); B7a adds a `platform` case key, a record section and a `--platform` flag (Plan:428). Use `image_platform` for the first.

## 3. Blocker: `<role>:<target>` with "folders are role then target" contradicts how `publisher:<platform>` works

**Evidence.**
- `providers/resolve.py:103-106`: `folder()` returns the head for `a:b` and the service for `integration:<service>`. `:109-119`: two variables (`<CLASS>_<SUBCLASS>_PROVIDER`, then `<CLASS>_PROVIDER`) except `integration`, which has only the first, "one integration's provider never serves another".
- `providers/CONTRACT.md:12`: "the sub-class (`linkedin` in `publisher:linkedin`) is passed as `--platform`, because one implementation often serves several sub-classes". `:68`: every publisher verb takes `--platform <p>`. `:72`: `generator:video` has "the same shape as image".
- `scripts/runtime.py:186-187`: `providers.path(f"publisher:{platform}", platform if platform in providers.shipped("publisher") else None)`: the platform name doubles as an implementation name inside one folder.
- Plan:240 (14a): "The folders under `providers/` follow the same rule, role then target (`providers/integration/vcs/`, `providers/reader/email/`)". Plan:253 (14c): "one provider may serve several platforms".
- `python3 providers/resolve.py --list` today: `publisher:<platform>` → `providers/publisher/`, variables `['PUBLISHER_PROVIDER']`, implementation `linkedin`.

**The collision.** The part after the colon means two things. For `integration:vcs`, `reader:email`, `sender:email`, `scheduler:job`, `store:runtime`, `search:web` it is part of the class's identity: another target has other verbs (`providers/CONTRACT.md:66-77`), so a folder per target and no shared variable is right. That is today's `integration` exception, which becomes the rule. For `publisher:<platform>` and `generator:image|video` it is an argument to one shared implementation: a folder per target would put an aggregator in several folders, or move `linkedin.py` to `providers/publisher/linkedin/linkedin.py` and break `runtime.py:186-187`, `contracts/secrets.md:30-32` and `uv run providers/publisher/auth.py --provider linkedin`. A generic `<ROLE>_PROVIDER` fallback is also wrong for identity targets: `resolve.py:184-186` takes the first variable that is set and `:176-180` raises when that name is not shipped in the folder, so `READER_PROVIDER=gmail` would make a later `reader:rss` unresolvable instead of falling through.

**Smallest change.** Add to 14a: "Two kinds of role. *Target is the class* (`integration`, `reader`, `sender`, `scheduler`, `store`, `search`): folder `providers/<role>/<target>/`, one variable `<ROLE>_<TARGET>_PROVIDER`. *Target is an argument* (`publisher`, `generator`): folder `providers/<role>/`, the target passed as `--platform` (or the verb's own flag), variables `<ROLE>_<TARGET>_PROVIDER` then `<ROLE>_PROVIDER`. `resolve.py` keeps this per role in `HEADS`." Also say that `providers/secrets/` stays where it is and is not a class (`resolve.py:203-205`), and whether `SCHEDULER_PROVIDER` and `STORE_PROVIDER` remain accepted (finding 8).

Worth knowing before paying for the rename: after default 57 removes `mailbox` from `mkt-engage`, one skill declares a bare class (`skills/mkt-publish/SKILL.md:18`, `scheduler`); `mailer` and `store` are declared by none (grep of `requires:`). The reason given in 14a ("every skill that declares it stale") is one skill today.

## 4. Blocker: C0.2 names two files and size S; the move breaks things the plan does not list, several of them silently

Plan:450 (C0.2) touches "`contracts/environment.md`, `scripts/validate.py`", size S. Plan:240 adds `resolve.py`, its variables, `doctor.py`, `providers/CONTRACT.md`, the orchestrator's reference and two skills. Not listed anywhere:

| What breaks | Evidence | How it fails |
|-------------|----------|--------------|
| CI test discovery | `scripts/test_dirs.py:17` pattern `providers/*/tests`; `scripts/tests/test_checks_wiring.py:39` asserts only `scripts/tests` and `evals/tests` are found | **Silent**: with `providers/<role>/<target>/tests` the glob finds nothing and the `tests` job stops running nine provider test files, green |
| The 3.9 guard | `scripts/tests/test_runtime_python39.py:72-74` globs `providers/scheduler/*.py` and `providers/store/*.py` | **Silent**: empty globs make the "every scheduler provider is listed" test pass on nothing |
| The 3.9 job and list | `.github/workflows/checks.yml:69`; `test_runtime_python39.py:24-25` | Loud (path not found), but these are the paths A1 has just repaired |
| Pre-commit hook | `.githooks/pre-commit:29` maps `providers/*/*` to `providers/<2nd segment>/tests`; `:40-41` fails when that folder is missing | Every commit that touches a moved provider is refused ("providers/integration has no tests"); the hook must change in the same commit |
| Providers' secret lookup | `providers/vcs/github.py:273`, `providers/publisher/linkedin.py:252`, `providers/publisher/auth.py:240`, `providers/mailbox/gmail.py:199`: `here.parents[1] / "secrets" / "resolver.py"` | One level deeper, `parents[1]` is `providers/<role>/`: every credential read fails |
| The resolver | `providers/resolve.py:63, 137` (`NAME.fullmatch(folder_name)` rejects a `/`), `:67-72` (`HEADS`, `LISTED`, `PLATFORM_DEFAULTS` keyed by head) | in scope of "the resolver follows", listed here for size |
| The doctor | `scripts/doctor.py:156-157`: `r.split("/")[1]` compared with `provider_folder(c)` | the secrets report stops naming classes |
| Secret registry | `providers/secrets/resolver.py:65-102` (reader paths, `set_local` commands); `contracts/secrets.md:29-35`; the resolver's tests compare the two (`contracts/secrets.md:11`) | stale paths in what `--list` tells a user to run |
| The runtime | `scripts/runtime.py:185` (`"mailbox"`), `:188` (`"store"`), `scripts/runtime_vote.py:87` (`"scheduler"`): bare class names passed to the resolver | `UnknownClass` → `Fail("runtime.json: ...")` at every tick once "the validator rejects a class without a role" reaches the resolver |
| A scheduled workflow | `.github/workflows/dependabot-alerts.yml:34, 39`: `uv run providers/vcs/github.py` | **Silent** until its next scheduled run; it feeds `eng-security-review` |
| Documents in the core | `contracts/runtime.md:9, 11`; `shared/references/security.md:27, 32, 40`; `skills/design-execute/references/tools.md:59`; `AGENTS.md` "Layout" and the `requires` paragraph; each `providers/*/README.md` | text only; `security.md` is inside the fingerprint, so it must change before B11 |
| Skill folders | `skills/mkt-publish/SKILL.md:18, 53`, `skills/mkt-engage/SKILL.md:19, 60`, `skills/core-orchestrator/references/requirement-classes.md` | Plan:459 says "C0.1 to C0.7 touch no skill folder"; C0.2 does |

**Smallest change.** C0.2's "Touches" lists these files, its size becomes M, and it adds one test: every `tests` folder under `providers/` is in `test_dirs.py`'s output (and the same assertion replaces the two hard-coded names at `test_checks_wiring.py:39`). A1's wiring test ("a path the workflow names must exist", Plan:398) covers every file under `.github/workflows/`, not only `checks.yml`.

## 5. Blocker: `../../shared/references/platforms/<platform>.md` does not resolve in an installation today, and the plan gives two dates for fixing it

**Each layout, as the code builds it.**

| Layout | Where a skill is | `shared/` beside it? | `../../shared/...` |
|--------|------------------|----------------------|--------------------|
| claude-code install | `~/.claude/skills/ai-workbench` → `adapters/claude-code/build/<pack>/` (`install.sh:43`); `build/<pack>/skills/<name>` is a symlink into `skills/` (`build.py:87-89`) | no: `build.py` creates only `.claude-plugin/`, `skills/`, `agents/` (`build.py:83-85`) | lexically `build/<pack>/shared`: absent. Through the symlink's real path: `<checkout>/shared`: present. Works only when the tool does not normalise the path first |
| agents-dir, symlink | `~/.agents/skills/<name>` → `<checkout>/skills/<name>` (`install.sh:60`) | no | same: absent lexically, present physically |
| agents-dir `--copy` or `--project --copy` | a copy (`install.sh:60`, `cp -R`) | no | absent either way |
| eval run, both adapters | `<case>/.claude/skills/<name>`, `<case>/.agents/skills/<name>`, copies | yes, a copy: `adapters/claude-code/run-prompt.sh:65-69`, `adapters/agents-dir/run-prompt.sh:59-63` | resolves |
| runtime, claude-code | `<out>/cwd/.claude/skills/<name>` | yes: `adapters/claude-code/run-agent.sh:50-51` | resolves |
| runtime, api | not installed: `SKILL.md` is quoted in the prompt | no, and no tools (`adapters/api/run_agent.py:16-17, 184-185`) | cannot be read (finding 7) |
| eval run after B2 | staged by the runner | Plan:422 stages `shared/` "into the case folder" | resolves only if it is staged as a sibling of the harness's `skills` folder; say so, and see findings 6 and 12 |

Today two skills use the link (`skills/core-security-audit/SKILL.md:51`, `skills/core-skill-creator/SKILL.md:53`), both about the workbench itself, where the checkout is at hand. After phase C seven user-facing skills stop with "the platform is not supported" when the file is not found (Plan:254).

**The plan's two dates.** Plan:456 (C0.9) lists "the installers copy `shared/`" and touches `adapters/*/install.sh`, before the round. Plan:280 (default 31) and Plan:604 (F3) say installers ship `shared/` "after the round". If the second reading is followed, every installation is broken for those seven skills between phase C and F3. `scripts/tests/test_installers.py` asserts nothing about `shared/`.

**Smallest change.** Default 31 and F3 keep only the stripped copy and the budget; shipping `shared/` is C0.9, before the round (installers are not frozen files). C0.9 names `adapters/claude-code/build.py` (a `shared` link or copy in `build/<pack>/`), `adapters/agents-dir/install.sh` (also for `--project` and `--copy`), and a test in `test_installers.py` that `<skills dir>/../shared/references/security.md` exists after each kind of install. For agents-dir, `~/.agents/shared` is a generic name in a folder other tools share: the installer's rule "replaces or removes only what it made" (`install.sh:38-48`) must cover it (marker file or link target, refusal when it is someone else's, removal on `--uninstall`).

## 6. Should-fix: the baseline must not receive the platform reference

- Today `shared/` is copied whenever a skills folder exists in the case (`adapters/claude-code/run-prompt.sh:66`, `[[ -d "$CWD/.claude/skills" ...`): never in a plain without-skill run, but always in a without-skill run of a case with dependency skills.
- Plan:422 (B2) stages "the skill under test and its dependencies ... and `shared/`" with no condition; B6's new check (Plan:426) is about paths "that hold the skill", not `shared/`.
- After 14c the reference holds what the skill's body held (text limits, URL shapes). A baseline that can read it scores higher, which narrows the difference the gate measures.

Change: B2 says `shared/references/platforms/` is staged only in with-skill runs (and for a tagged case, only that platform's file, which also makes the per-platform hash exact); B6 asserts it in the docker test.

## 7. Should-fix: the API adapter cannot give a runtime agent a platform reference

- `adapters/api/run_agent.py:16-17, 184-185`: the prompt carries each `SKILL.md` whole and says "Their scripts, references and assets are not available in this run". No tools.
- `agents/social-manager.md:10`: `skills: [mkt-engage, mkt-vote-round]`, two of the seven skills of Plan:256.
- With the literal step of Plan:254 the agent must stop: "there is no such file".

Change: the rows of `mkt-engage` and `mkt-vote-round` say that in Runtime mode the task file carries the platform's reference (the runtime adds it, as it adds the trigger's data, `contracts/runtime.md:20`), and the literal step applies to interactive use. Decided in phase C, because rewording Runtime mode after the round stales both skills.

## 8. Should-fix: what happens to machines that already run the workbench

14a says only "a project that uses the workbench renames its provider variables when it updates" (Plan:240). The code shows more:

- **Recurring jobs.** A scheduled job runs copies: the runner (`providers/scheduler/launchd.py:402, 421`) and every snapshotted file (`:383-386`). The tick's copy of `runtime.py` loads `resolve.py` from its snapshot or from the live checkout (`scripts/runtime.py:116-117`). After the upgrade the old copy asks for `store`, `mailbox`, `scheduler`: an old `resolve.py` copy looks in `providers/store/` (gone), a new one rejects the bare name. Either way every tick fails (closed: nothing is published) until the job is cancelled and scheduled again. One-time publish jobs already scheduled keep working: all their files are copies, with `resolver.py` beside the provider (`scripts/runtime_vote.py:360`, `providers/publisher/linkedin.py:252`).
- **`runtime.json`.** Its keys `mailbox`, `store`, `scheduler`, `publisher` (`scripts/runtime.py:155-161`) are configuration keys in a project's file, named like the bare classes. The plan does not say whether they are renamed.
- **Variables.** `SCHEDULER_PROVIDER`, `STORE_PROVIDER`, `MAILBOX_PROVIDER` are documented (`providers/CONTRACT.md:22`, `contracts/environment.md:36`).
- **Names that must not follow the rename**: the scheduler's data folder and launchd label (`launchd.py:64, 183`), ledger files (`providers/publisher/linkedin.py:315-321`, `providers/vcs/github.py:312-318`), keyring usernames `publisher-linkedin` and `mailbox-gmail` (`contracts/secrets.md:30, 33`), `STORE_SQLITE_PATH`, `SCHEDULER_HOME`. A mechanical rename of any of these orphans jobs, ledgers or stored tokens.

Change: one paragraph in 14a and a row in phase H beside N17: recurring jobs are scheduled again after upgrading; `runtime.json` keys do not change (the runtime maps them to the new class names); the old variables are either still read with a note on stderr or named in the release note; the listed data names never change.

## 9. Should-fix: per-platform code in skills, and callers that are not listed

- Plan:255: "Scripts take `--platform` and read a platform's rules from a data table, never from code". Plan:246: adding a platform "never edits a skill's procedure, and only that platform is measured".
- A URL shape can be data (`skills/mkt-vote-round/scripts/vote_update.py:43-65`). A parser cannot: `skills/mkt-engage/scripts/parse_notification.py:13-22, 54, 91` reads one platform's comment links, and `skills/brand-profile/scripts/linkedin_export.py` (named in the procedure, `skills/brand-profile/SKILL.md:64, 90`) parses one platform's export. Plan:521 itself says the parser "takes `--platform` with one platform implemented". A second platform adds code in a hashed folder: the skill is measured in full.
- Callers: `scripts/runtime.py:333, 468, 557` run `parse_notification.py` with no arguments; `scripts/runtime_vote.py:288` and `scripts/vote_job.py:107` run `vote_update.py`. Only `payload.py`'s caller is listed (Plan:523). If a table file is added, the vote job's snapshot (`scripts/runtime_vote.py:360-361`) must carry it, and the scheduler requires distinct file names in one flat folder (`providers/scheduler/launchd.py:295-297`), so the script cannot find it by a relative path.

Change: rule 3 gains the exception ("a skill that parses a platform's own format carries that parser; adding the platform there is a change to that skill"), or the two parsers move behind a provider verb before the round. Rows 44 and 48 list `scripts/runtime.py`, `scripts/runtime_vote.py` and `scripts/vote_job.py` in the same pull request; row 6 says what happens to the script's name.

## 10. Should-fix: `--strict` is all warnings, and the plan keeps warnings and drafts

- `scripts/validate.py:521`: `failed = bool(report.errors) or (strict and bool(report.warnings))`.
- Plan:587: after the round "`validate.py --strict` becomes the CI default". Plan:581 (rule 6): a skill that still fails "reads `draft` ... The round then closes with fewer than 48". Plan:594 (exit) asks for both "the listed `draft` skills" and "`validate.py --strict` green": not possible together.
- Plan:351 (default 90) keeps "a warning for AI and design-tool names in eval cases and fixtures"; A5 (Plan:402) adds a dozen rules "as warnings first" and only some become errors (C0.1, C0.2); `validate.py:257` warns on a gate section without side effects. A per-platform `not measured` (Plan:257) would be one more.
- `validate` is a required check with no bypass: a single warning on `main` blocks every pull request.

Change: decision 3 and Plan:587 say "CI runs `validate.py --strict-evals`: `stale` and `draft` are errors, except skills listed with their backlog item in `evals/eval-gate.json`"; other warnings stay warnings, and `not measured` is information.

## 11. Should-fix: what the fingerprint does not cover

- Plan:431 covers the template, `evals/container/`, the two `run-prompt.sh`, `measurement.json`, `shared/references/`.
- Not covered, and changed by phase B to define the measurement: `evals/executor.py` (mounts `:113-120`, forwarded variables `:42-43`, networks `:157-164`; B1 adds the fixed platform, Plan:421); the staging code B2 moves into `evals/eval_run.py` (what a run sees, Plan:422); `adapters/*/adapter.json`, where B8 puts the refusal markers (Plan:429) while B10 puts them in `measurement.json` (Plan:431): the two items disagree.
- Plan:604 (F3): the installers reuse "the runner's staging function without changing it". After B2 that function is in `evals/eval_run.py`, which nothing checks; and an installer would import the eval runner, a dependency from `adapters/` to `evals/` that does not exist today (`adapters/agents-dir/install.sh:30` calls only `scripts/select_skills.py`).

Change: B2 puts staging in its own module (for example `scripts/stage_skills.py`), B10 adds it, `evals/executor.py` and the adapters' eval data to the fingerprint, and B8/B10 name one home for the refusal markers. Also note that C0.2 and C0.9 edit `shared/references/` in parallel with phase B: the check is armed in B11 but the value is final only at D1 (Plan:551 implies it; say it in B10).

## 12. Should-fix: staging by the runner meets the adapters' own refusal

- `adapters/claude-code/run-prompt.sh:49-50` and `adapters/agents-dir/run-prompt.sh:42-43` refuse a case folder that already holds the harness's settings folder; `AGENTS.md` "Adding an adapter" makes it part of the contract.
- With B2 the runner creates that folder before the adapter starts, so the check either fires on every run or is deleted and a fixture that carries harness settings goes unnoticed.
- The runner must also know each harness's skills folder; backlog T4 removed harness folder names from the runner once.

Change: B2 says the runner performs the refusal before staging, with the folder names read from `adapters/<harness>/adapter.json`, and B11 rewrites that sentence of `AGENTS.md`.

## 13. Should-fix: defaults 54 and 57 disagree on `mkt-engage`

Plan:309 (default 54): "every skill that uses a class declares it" (optional uses included, as for `search:web`). Plan:312 (default 57) and Plan:521: `mkt-engage` drops the mailbox class from `requires` while "the mailbox [becomes] one line" of the body, which still resolves the class (`skills/mkt-engage/SKILL.md:60`). A5's rule and audit pattern 6 would flag it. Change: keep `reader:email` declared with its degraded behaviour (the pasted link), or remove the line until the parser is verified.

## 14. Should-fix: decision 11 changes three sentences of `AGENTS.md`, A4 names one

`AGENTS.md:14` (principle 8: "no decisions, dates or numbers of a real case ... invented numbers"), `:139` (step 7: "the real project's names, people and numbers go") and `:157` ("Never commit a real project's names, people, decisions or data"). Plan:401 (A4) rewords principle 8 only. The same wording is taught to authors through `core-skill-creator` (its row, Plan:493, does not mention it). Left as is, the next audit flags the fixtures decision 11 keeps. Change: A4 lists the three lines; row 16 adds the sentence to the authoring guide.

`AGENTS.md` also needs, from 14a to 14c, edits no item lists: the Layout lines for `providers/<class>/<impl>.py` and for `shared/references` ("today only security.md, each other one added when a second skill needs it"), the "Transversal concerns" paragraph (platform references are not a transversal concern), and the `requires` paragraph's examples. C0.9 touches `AGENTS.md` only for "the four design rules".

## 15. Should-fix: F3 assumes a copy mode one installer does not have

Plan:604: "Both installers install the stripped copy (no `evals/`, no `scripts/tests/`)". `adapters/claude-code/install.sh:4` has no `--copy`; `build.py:87-89` links whole skill folders, which cannot be stripped. `adapters/agents-dir/install.sh:60` links by default and its `--copy` copies everything. F3 therefore changes the default of both from link to copy (edits to a skill are no longer live in an installation) and `adapter.json`'s strategy text. Say it in F3, with a `--link` option for the maintainer.

## 16. Nits

- **A6 is filed in phase A but changes what the grader is given** (Plan:403: values replaced "in the reply, the transcript and the case folder ... before grading"; phase A "touch[es] neither a skill folder nor the measurement", Plan:394). Move it to phase B, or state why version 4 is not raised.
- **Record and flag names**: finding 2, last paragraph.
- **A1** says "add a wiring test ... `scripts/tests/test_checks_wiring.py`" (Plan:398); the file exists. It is extended.
- **B3** reads `grading_passes` from the gate file (Plan:423) but does not touch `eval_status.py`: an unknown key makes `gate_problems` non-empty (`evals/eval_status.py:115`) and `load_gate` returns `{}` (`:136`), so every default disappears. Add `GATE_FIELDS` to B3's files (B5 and B10 already list it).
- **A8** measures the listing in phase A (Plan:405); phase C then lengthens many descriptions ("description gains ..." in a dozen rows). Measure again at D1, before decision 9 is closed.
- **C0.3** adds `shared/scripts/` with tests and updates `scripts/test_dirs.py`; the hook's mapping (`.githooks/pre-commit:28-36`) has no `shared/*` line, and A7 adds only `.githooks/`, `.github/`, `packs/`.

## Spot-check of plan items against the code (38 items)

| Plan item | Claim | Code | Verdict |
|-----------|-------|------|---------|
| Plan:37 | 48 skills, 141 cases, 663 assertions | counted from `skills/*/evals/evals.json` | true |
| Plan:38-40 | 33 evaluated, 15 stale, 0 draft | `eval_status.py status` | true |
| Plan:50 | `python39` job fails since #44 | five paths of `checks.yml:65-68` do not exist under `scripts/tests/` | true |
| Plan:51 | validate: 0 errors, 3 warnings | run | true |
| A1 | new wiring test file | `scripts/tests/test_checks_wiring.py` exists | works differently (nit) |
| A4 | stale "Containment" text | `evals/eval_run.py:67-77` ("This is not a sandbox ... HOME included") | true |
| A5 | one frontmatter parser | `scripts/validate.py:167-172` tries `import yaml` first | true |
| A5 | `packs/` not scanned as core | `validate.py:54` | true |
| A6 | uses `scripts/redact.py` | exists | true; phase wrong (nit) |
| A7 | hook lacks `.githooks/`, `.github/`, `packs/` | `.githooks/pre-commit:28-36` | true |
| B1 | `TZ` forwarded from the host | `evals/executor.py:42-43` | true |
| B1 | image built locally by tag | `executor.py:87-89` | true |
| B2 | whole `adapters/` mounted | `executor.py:115` | true |
| B2 | adapters hold duplicated install code | both `run-prompt.sh`, `install_skill` | true |
| B2 | `workbench_files` keep a skill's tests | `eval_run.py:440-441` ignores only `evals` | true |
| B2 | staging and the adapters' refusal | `run-prompt.sh:49-50`, `:42-43` | not addressed (finding 12) |
| B3 | grading through the strong adapter | `eval_run.py:1323` `grade(runner, ...)` | true |
| B3 | `grading_passes` in the gate file | `eval_status.py:84-86, 115` reject unknown keys | missing file in "Touches" (nit) |
| B5 | population standard deviation today | `eval_run.py:1347` `pstdev` | true |
| B5 | rounded gate comparison today | `eval_run.py:1347, 1356` | true |
| B5 | `GATE_FIELDS` | `eval_status.py:84` | exists |
| B5 | `--resume` | absent from `eval_run.py` usage `:5-12` | new, as stated |
| B6 | contamination check is dead in the container | `eval_run.py:150-154`: searches the repository's host path | plausible |
| B7 | `--only without --update-record` exists | `eval_run.py:123-127` | true |
| B7 | status table lacks the floor baseline | `eval_status.py:434-439` | true |
| B7a | `--platform` merges into the record | `eval_run.py:1385, 1421`; `eval_status.py:285, 334, 413` | does not fit (finding 2) |
| B8 | refusal markers in the runner's code | `eval_run.py:643` `provider_refusal` | true; home disputed with B10 (finding 11) |
| B10 | `validate.py` can load eval status code | `validate.py:407` | true |
| C0.2 | touches two files, size S | section 4 | wrong (blocker) |
| C0.3 | three identity tests today | `scripts/tests/test_script_copies.py:29, 57, 66` | true |
| C0.9 | installers are `install.sh` | claude-code builds in `build.py:83-89` | wrong file (finding 5) |
| default 56 | resolver accepts a placeholder sub-class | `resolve.py:94-95` | true |
| default 68 | `payload.py` builds a provider path, `--platform` defaults | inventory row; `payload.py:6, 363` | true |
| row 14 | script renamed to `check_brief.py` | today `check-brief.py` | true |
| row 24 | `--report` is a switch in `lint_prd.py` | `lint_prd.py:4-6, 268` | true |
| rows 1-48 | 49 script and reference files named | all exist | true |
| E | `--strict` = stale and draft fail | `validate.py:521`: all warnings | works differently (finding 10) |
| E | ten runner processes under one lock | `eval_run.py:33`: `--jobs` at most 8, per process | new, as stated |
| F3 | both installers can copy | `adapters/claude-code/install.sh:4` | wrong (finding 15) |
| F2 | API adapter has no `install.sh`, no `run-prompt.sh` | `ls adapters/api` | true |

## Principles of `AGENTS.md`: what the plan resolves and what it does not

- Principle 1 (no harness in the core): kept. B2's runner needs harness folder names; `evals/` is outside the core, and reading them from `adapter.json` keeps it clean (finding 12).
- Principle 4 (artifacts over invocation): kept. Defaults 52 and 65 remove the two places where a capability reached into another skill's folder.
- "Self-contained" capability: `AGENTS.md` already allows `../../shared/references/`; 14c fits the rule. It does not fit the installations (finding 5) or the API adapter (finding 7).
- Principle 8: A4 covers one of three sentences (finding 14).
- "Providers are core": kept; platform references name third-party services, which the core may do.
- Principle 7: the plan's lanes fit. The provider move (finding 4) and the `shared/references/` edits before B11 (finding 11) are the two places where parallel lanes meet one resource; both need an order.
