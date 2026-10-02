# Platform and service mentions in `skills/` (inventory, 2026-10-02)

Read-only inventory of the worktree `agent-a43c99dfd506a87f0`. Nothing in the repository was changed.

## Method and scope

- Searched every file under `skills/*/` with a wide list of product names (social networks, code hosts, registries, deploy hosts, trackers, design tools, OS services, databases, mail, browsers, package managers, test runners, OS names) plus host names and URL patterns, then read the surrounding lines of every hit. `evals/` and `scripts/tests/` are counted only as totals (last table of section 1).
- A "mention" is one line that names a product. Counts of CODE in long scripts are line counts and are approximate (±2).
- Two tiers are kept apart, because they call for different treatment:
  - **Tier A, platforms and services**: LinkedIn, Instagram, X, Threads, TikTok, YouTube, dev.to, GitHub (and `gh`, Dependabot, Actions, CODEOWNERS, `.github/`), GitLab, npm as a registry, RDAP services, Netlify, Vercel, Fly, Render, AWS, Slack, Stripe, Google, Jira, Linear.
  - **Tier B, local toolchain**: package managers and lockfiles (npm, bun, pnpm, yarn, uv, poetry, cargo), runners and frameworks (Playwright, Vitest, Jest, pytest, Tailwind, Nuxt...), browsers (Chrome, Chromium, WebKit), Lighthouse, OS names (macOS, Linux, Ubuntu), pypdf, Docker.
- **Never named outside evals and tests**: Figma, Gmail, Buffer, launchd, systemd, SQLite, Bitbucket, Twitter. Jira and Linear appear once, as an example. GitLab appears twice (one example, one file-name regex). The design skills are already written by kind of tool, and the marketing skills mostly say "the network" and `<platform>`.
- Platform facts that are present **without the name** (so a name search misses them) are listed in section 1 as "unnamed".
- Out of scope here but seen: `ops-repo-baseline/SKILL.md:125` and `references/host-settings.md:3,7,20` name this repository, a date and a count (the plan already removes them, decision 11).

## 1. Table per skill

30 of the 48 skills have at least one mention outside evals and tests. 18 have none: `biz-icp-positioning`, `biz-market-analysis`, `brand-guidelines`, `core-clarify`, `core-critique`, `design-brief`, `design-handoff`, `design-ux-flows`, `eng-architecture`, `eng-impact-analysis`, `eng-integration-tests`, `eng-refactor`, `eng-tradeoffs`, `mkt-content-plan`, `mkt-messaging`, `product-feature-spec`, `product-prd`, `product-roadmap`.

Counts are EX / KN / CODE / SUBJ (lines).

| Skill | Platforms named | EX | KN | CODE | SUBJ | KNOWLEDGE, CODE and SUBJECT mentions (file:line, what) |
|---|---|---|---|---|---|---|
| `brand-identity` | LinkedIn; Chrome, Chromium, macOS (B) | 1 | 2 | 27 | 0 | KN `SKILL.md:108` profile photo covers the left of a LinkedIn cover. KN `assets/post-card-template.html:8-9` 1080 x 1350 portrait image "for a LinkedIn post" (a format size inside an asset). CODE (B) `scripts/render.py:23-27,40,52-55,64,68-69` browser lookup order and headless flags in the docstring; `:92-97` macOS application paths and `PATH_BROWSERS`; `:228-244` `CHROME_BIN`; `:310-312` keychain flags; `:329` `--browser`. EX `SKILL.md:43` "(Chrome or Chromium)". |
| `brand-name` | LinkedIn, Instagram, X, Threads, TikTok, GitHub, npm, dev.to, YouTube, rdap.org, registro.br, Google (control domain) | 0 | 4 | 19 | 0 | KN `SKILL.md:48` networks that need a login are asked by name; `:96` quality criterion names the five networks; `:104` npm `scope:` search lesson; `:105` rdap.org does not answer for every TLD. CODE `scripts/handle_check.py:6,17` docstring; `:33` `BY_HAND` list; `:38,57-60` RDAP endpoints, `.br` special case; `:66` `google.<tld>` control domain; `:78-91` one URL per platform in an if-chain; `:102,119` `--platform` choices and default list. |
| `brand-profile` | LinkedIn; pypdf, uv (B) | 1 | 1 | 14 | 0 | KN `SKILL.md:41` export procedure (`More > Save to PDF`). CODE `SKILL.md:64,90` call the script by its platform name `linkedin_export.py`; `scripts/linkedin_export.py:2,5-6` docstring; `:38` page footer pattern; `:39-41` the section headings of that export; `:81` comment; `:150-185` messages carry the script name. EX `SKILL.md:7` description. |
| `brand-strategy` | npm, GitHub, LinkedIn | 1 | 1 | 20 | 0 | KN `SKILL.md:142` a member account cannot read its analytics through the API. CODE `SKILL.md:50` command with `--npm` and `--github`; `scripts/baselines.py:5-8` docstring (hosts, 60 requests per hour); `:25` npm name regex; `:44-52` npm downloads endpoint; `:55-60` GitHub repository endpoint and field names; `:65-86` the two flags and dispatch. EX `SKILL.md:42`. |
| `brand-voice` | GitHub (word in a regex) | 0 | 0 | 1 | 0 | CODE `scripts/voice_stats.py:41` the "closing line" regex lists `link|github|demo|preview`. |
| `core-agents-md` | GitHub, GitLab, Netlify, Vercel, Fly, Render, Docker; npm, bun, pnpm, yarn, uv, poetry, cargo, linters and runners (B) | 2 | 0 | 16 | 0 | CODE `scripts/audit_agents_md.py:35` manifests; `:37-40,48-53` linter and test-runner file patterns and names; `:42` CI and deploy files (`.github`, `.gitlab-ci.yml`, `netlify.toml`, `vercel.json`, `fly.toml`, `render.yaml`); `:47,95-97,134` lockfile to install command; `:111-113` `.github/workflows`; `:256,273` known command prefixes. EX `SKILL.md:103`, `assets/agents-md-template.md:13`. |
| `core-orchestrator` | LinkedIn, X, Jira, Linear, GitHub, GitLab | 4 | 0 | 0 | 0 | EX only: `SKILL.md:60`; `references/requirement-classes.md:7,8,13` (what a class covers). |
| `core-project-init` | manifests (B) | 0 | 0 | 1 | 0 | CODE `scripts/init_project.py:42` manifest file names. |
| `core-research` | npm | 1 | 0 | 0 | 0 | EX `SKILL.md:56` ("page fetch and the npm registry work"). |
| `core-security-audit` | GitHub (folder) | 0 | 0 | 2 | 0 | CODE `scripts/components.py:50-51` `.githooks` and `.github/workflows` as component kinds. |
| `core-skill-creator` | GitHub (a link), Docker, Excel, pypdf, uv | 6 | 0 | 0 | 0 | EX only: `references/authoring-guide.md:62,95,229,381,775,899`. |
| `design-execute` | npm; Playwright, Chrome, Chromium, macOS (B) | 1 | 2 | 32 | 0 | KN `references/code-prototype.md:10` browser lookup order and the rule about the `playwright` package; `SKILL.md:102` macOS variant of the hash command. CODE (B) `scripts/screenshot.mjs:13-19` header; `:47-53` pinned Playwright version, install hint, browser names, macOS paths; `:63-65` help; `:122-139` Playwright engine; `:189-193` `CHROME_BIN`; `:332-358` engine choice and messages. EX `references/tools.md:41`. |
| `design-system` | macOS (B) | 0 | 1 | 0 | 0 | KN `SKILL.md:55` macOS variant of the hash command. |
| `eng-code-review` | AWS, GitHub, Slack, Google, npm, Stripe, Netlify; lockfiles, linters (B) | 1 | 0 | 15 | 0 | CODE `scripts/redact.py:26-34,40` credential formats per vendor (already a table); `scripts/change_scope.py:51-54` lockfiles and manifests; `:59` config names; `:69-70` skip and lint-suppress markers per runner. EX `SKILL.md:58`. |
| `eng-codebase-map` | GitHub, Netlify, Vercel, Fly, Render, Docker, Stripe, Supabase, Firebase; frameworks (B) | 0 | 0 | 18 | 0 | CODE `scripts/map_codebase.py:7,23-25` extensions, skipped folders, manifests; `:26-30` `FRAMEWORK_HINTS`; `:32` integration hints (`stripe`, `supabase`, `firebase`...); `:71,101-102,173` framework entry files; `:184-186` `.github/workflows`; `:187` deploy files. |
| `eng-docs` | Tailwind (B) | 2 | 0 | 0 | 0 | EX `SKILL.md:97-98` (a lesson told with a framework's name). |
| `eng-implement` | bun, Nuxt (B) | 1 | 0 | 0 | 0 | EX `SKILL.md:108`. |
| `eng-root-cause` | WebKit, Linux, Node (B) | 2 | 0 | 0 | 0 | EX `SKILL.md:57`, `references/evidence.md:14`. |
| `eng-security-review` | Dependabot, GitHub (folder, advisory ids); npm, pnpm, yarn, bun, pip, uv, poetry, Vitest, macOS (B) | 4 | 3 | 8 | 0 | KN `SKILL.md:57` grep for install commands by package manager; `:133` macOS hash variant; `:156` a CI file only runs from the root `.github/workflows/`. CODE `scripts/triage_alerts.py:12` field names of one host's alerts (`ghsa_id`, `html_url`); `:23-25,39` `declared` and `installed` only for `package.json` and `node_modules`; `:37,116` locked versions only from npm lockfiles; `:56-58` lockfile list. EX `SKILL.md:4,10,153,155`. |
| `eng-unit-tests` | Jest, Playwright (B) | 2 | 0 | 0 | 0 | EX `SKILL.md:10,49`. |
| `flow-fix-bug` | WebKit, Chromium (B) | 2 | 0 | 0 | 0 | EX `SKILL.md:91-92` (lessons). |
| `mkt-engage` | LinkedIn; uv (B) | 0 | 2 | 12 | 0 | KN `SKILL.md:132` the API returns 403 for reading comments with a member token; the URN form a reply needs; `:136` the copied comment link and its short URN form. CODE `scripts/parse_notification.py:10,13-18,22` docstring (link shape, one level of nesting); `:35-36` URN regexes; `:37` "commented on your post" phrases; `:54` host check `endswith("linkedin.com")` (not exact); `:91,105` messages. Unnamed: `SKILL.md:60,68` use the vocabulary "post URN, comment URN" and the flags `--post-urn`, `--parent-comment`. |
| `mkt-publish` | LinkedIn; uv, macOS, Linux (B) | 0 | 4 | 4 | 0 | KN `SKILL.md:134` the member API has no scheduling; `:135` member tokens last 60 days with no refresh; `:112,133` OS variants (hash command, temporary files). CODE `scripts/payload.py:6,363` `--platform` defaults to `linkedin`; `:168,171` builds `providers/publisher/<platform>.py` and runs it with `uv`. |
| `mkt-social-copy` | LinkedIn | 1 | 0 | 0 | 0 | EX `SKILL.md:9` (description trigger). |
| `mkt-vote-round` | LinkedIn | 0 | 0 | 9 | 0 | CODE `scripts/vote_update.py:6,14` docstring; `:43` path regex of a post URL; `:59-65` `linkedin_post()` host and path check; `:69-70` refusal message; `:146` help text. Unnamed: `SKILL.md:49` "visitors vote by opening issues" (a code-host mechanism, already behind `integration:vcs`). |
| `ops-branch-sync` | `gh`; lockfiles, macOS (B) | 1 | 2 | 4 | 0 | KN `SKILL.md:79` `gh pr checks <n> --watch` as the way to follow checks; `:58` macOS hash variant. CODE `scripts/sync-status.sh:38` `gh pr list`; `:50-52` manifest and lockfile regex. EX `SKILL.md:73`. |
| `ops-ci-pipeline` | GitHub; Lighthouse, Chrome, macOS (B) | 1 | 3 | 0 | 0 | KN `SKILL.md:101` the settings path for deleting merged branches; `:119` headless Chrome follows the OS colour scheme, with the flag; `:59` macOS hash variant. EX `SKILL.md:8` ("GitHub Actions" as a trigger phrase). Unnamed: `SKILL.md:72,122` "about 60 requests an hour" on an unauthenticated public API; `:71,121` required checks can be chosen only after they ran once. |
| `ops-pull-request` | GitHub, `gh`; macOS (B) | 1 | 5 | 3 | 0 | KN `SKILL.md:52` template paths under `.github/`; `:70` `gh pr create ...` is the command of the step; `:72` `gh pr view --json mergeable,mergeStateStatus` and the settings path for deleting branches; `:122` the authenticated CLI has no hourly limit; `:59` macOS hash variant. CODE `scripts/pr-context.sh:11` comment; `:44` template paths; `:50` `gh pr list`. EX `SKILL.md:71` (twice "for example `gh ...`"). |
| `ops-repo-baseline` | GitHub (Actions, Dependabot, CODEOWNERS, rulesets, push protection), Ubuntu; credential vendors; npm, pip, cargo... (B) | 0 | 0 | 24 | 25 | SUBJ `SKILL.md:6,11` description; `:55,57-59,87` the files it writes are that host's files (`.github/workflows/checks.yml`, `.github/dependabot.yml`, `.github/CODEOWNERS`) and the pin command uses `https://github.com/<owner>/<action>`; `:125,128` lessons; `references/host-settings.md:3,12-25,37` that host's settings in order; `assets/checks.yml:2,15-16,21,24,35,38,43`, `assets/dependabot.yml:5`, `assets/CODEOWNERS:3`, `assets/SECURITY.md:5,11,13`. CODE `scripts/baseline_status.py:7-10,28-36` ecosystem names in the alert product's vocabulary; `:79,91-104,115-117` `.github` paths; `scripts/redact.py:26-34,40` credential formats. |
| `product-backlog` | macOS (B) | 0 | 1 | 0 | 0 | KN `SKILL.md:59` macOS hash variant. |

Totals outside evals and tests: **EXAMPLE 35, KNOWLEDGE 31, CODE 229, SUBJECT 25** (320 lines). Of the 229 CODE lines, about 95 are tier A (platforms) and about 134 are tier B (browser and toolchain tables); of the 31 KNOWLEDGE lines, 9 are the OS variant of one command.

### Mentions inside `evals/` and `scripts/tests/` (totals only, pattern matches)

Tier A + tier B occurrences; test counts leave out the word `pytest`.

| Skill | evals | tests | Skill | evals | tests |
|---|---|---|---|---|---|
| biz-icp-positioning | 0 | 1 | eng-docs | 3 | 0 |
| biz-market-analysis | 0 | 4 | eng-impact-analysis | 4 | 0 |
| brand-guidelines | 7 | 1 | eng-implement | 0 | 1 |
| brand-identity | 18 | 25 | eng-integration-tests | 5 | 0 |
| brand-name | 7 | 5 | eng-refactor | 6 | 0 |
| brand-profile | 10 | 15 | eng-root-cause | 1 | 0 |
| brand-strategy | 8 | 5 | eng-security-review | 29 | 2 |
| brand-voice | 14 | 1 | eng-tradeoffs | 5 | 1 |
| core-agents-md | 22 | 37 | eng-unit-tests | 9 | 0 |
| core-clarify | 11 | 2 | flow-fix-bug | 2 | 0 |
| core-critique | 0 | 0 | mkt-content-plan | 9 | 0 |
| core-orchestrator | 4 | 0 | mkt-engage | 26 | 6 |
| core-project-init | 4 | 2 | mkt-messaging | 64 | 1 |
| core-research | 4 | 0 | mkt-publish | 40 | 1 |
| core-security-audit | 1 | 2 | mkt-social-copy | 5 | 0 |
| core-skill-creator | 0 | 0 | mkt-vote-round | 21 | 25 |
| design-brief | 21 | 2 | ops-branch-sync | 8 | 1 |
| design-execute | 3 | 37 | ops-ci-pipeline | 101 | 0 |
| design-handoff | 3 | 2 | ops-pull-request | 21 | 1 |
| design-system | 2 | 1 | ops-repo-baseline | 25 | 6 |
| design-ux-flows | 0 | 1 | product-backlog | 0 | 1 |
| eng-architecture | 6 | 1 | product-feature-spec | 3 | 2 |
| eng-codebase-map | 7 | 3 | product-prd | 0 | 1 |
| eng-code-review | 5 | 7 | product-roadmap | 0 | 0 |

Sum: about 650 in evals, about 205 in tests. The heaviest eval folders are `ops-ci-pipeline`, `mkt-messaging`, `mkt-publish`, `eng-security-review`, `mkt-engage`.

## 2. What would move, per skill with KNOWLEDGE or CODE

"Reference" below means a per-platform file with one source and generated copies (the mechanism of C0.3, `scripts/sync_copies.py`). "Table" means a data file the script reads (for example `platforms.json` beside the script, or generated from the same source).

| Skill | To the per-platform reference | Script change | Size |
|---|---|---|---|
| `brand-identity` | LinkedIn: the cover's covered area (`SKILL.md:108`), the post image size and ratio (`post-card-template.html:8-9`). The body keeps "a network's interface may cover part of a cover: see the platform reference". | None for platforms. `render.py` drives one browser engine: keep, it already takes `--browser`; its name lists are tier B. | S |
| `brand-name` | One short entry per platform: how a handle is looked up (public endpoint, or "needs a login: ask the person"), plus the npm scope lesson and the RDAP lesson. `SKILL.md:48,96` become "every platform the table marks `by_hand` is named in the question". | `handle_check.py`: the if-chain (`:78-91`), `BY_HAND` (`:33`), the RDAP endpoints (`:57-60`) and the `choices` (`:102,119`) become one table: `platform -> {url template, by_hand}`. `--platform` already exists; its allowed values come from the table. | M |
| `brand-profile` | LinkedIn: the export procedure (`SKILL.md:41`) and the layout of the export (section headings, page footer). | `linkedin_export.py` becomes `profile_export.py --platform <p>`; `SIDEBAR`, `MAIN`, `PAGE`, the "Present" word and the header position (`:33-41,97-103`) move to a per-platform table. `SKILL.md:64,90` follow the new name. One platform implemented. | M |
| `brand-strategy` | LinkedIn: no analytics API for a member account (`SKILL.md:142`); the body already says it generically at `:50`. npm and GitHub: which public metrics exist, the unauthenticated limit. | `baselines.py`: `--npm` and `--github` become `--source <kind>:<name>` (or `--registry`, `--repo` with `--platform`), with a table `kind -> {url template, fields, period}`. | M |
| `brand-voice` | Nothing. | `voice_stats.py:41`: the word `github` in the closing-line regex could be a generic "host name or link label"; optional. | S |
| `core-agents-md` | Nothing (detection of what a project uses, not a rule of a platform). | `audit_agents_md.py`: the tables are already constants; they could move to a data file shared with `eng-codebase-map`, `ops-branch-sync`, `eng-code-review`, `eng-security-review` and `ops-repo-baseline` (one "toolchain" table: manifests, lockfile to install command, CI and deploy file names). Optional. | S (M if the shared table is built) |
| `core-project-init`, `core-security-audit` | Nothing. | Same shared toolchain table (manifest names; CI folder names). Optional. | S |
| `design-execute` | Nothing for platforms. `code-prototype.md:10` describes the script's lookup order (tier B). | None required. `screenshot.mjs` is an engine wrapper with `--browser`. | S (leave) |
| `design-system`, `product-backlog`, `design-execute`, `ops-ci-pipeline`, `ops-pull-request`, `ops-branch-sync`, `eng-security-review`, `mkt-publish` | Nothing. | The sentence "`sha256sum` (macOS: `shasum -a 256`)" is one canonical gate sentence; a single hashing command (`python3 -c` or a shared script, as `payload.py verify` will do for `mkt-publish`) removes the OS name from eight skills in the C0.6 pass. | S (one change, eight copies) |
| `eng-code-review` | Nothing. | `redact.py` is already a table and becomes a generated copy (C0.3). `change_scope.py:51-70` could read the shared toolchain table. Optional. | S |
| `eng-codebase-map` | Nothing. | `map_codebase.py:26-32,187`: the hint tables are constants; a data file is possible, low value. | S (leave) |
| `eng-security-review` | Code host: the alert product's name and the shape of its alerts; the rule that a CI file only runs from the root CI folder (`SKILL.md:156`). | `triage_alerts.py` reads a host-neutral shape already, but `ghsa_id` and `html_url` are one host's names (acceptable as the provider's contract), and `declared`, `installed`, `locked_versions` exist only for the npm ecosystem (`:23-39,116`): an ecosystem table (manifest, lockfile parser, install folder) would generalise it. The grep at `SKILL.md:57` would come from the same table. | M |
| `mkt-engage` | LinkedIn: comments cannot be listed with a member token; the reply id form; the copied comment link; one level of nesting. `SKILL.md:132,136` leave the body; `:60,68` say "the ids the platform reference names" instead of URN. | `parse_notification.py --platform <p>`: `SHORT`, `POST`, `OWN`, the host and the query parameter names move to a table; exact host match instead of `endswith`. | M |
| `mkt-publish` | LinkedIn: no scheduling in the member API; token lifetime 60 days, no refresh (`SKILL.md:134-135`). | `payload.py`: `--platform` required, no default (`:363`); the provider path comes from the resolver. | S |
| `mkt-vote-round` | LinkedIn: what a post URL looks like. | `vote_update.py --platform <p>`; `LINKEDIN_PATH_RE` and the host list (`:43,59-65`) move to a table `platform -> {hosts, path pattern}`; `linkedin_post()` becomes `post_url_ok(platform, url)`. | S |
| `ops-branch-sync` | Code host: how to follow checks (`SKILL.md:79`). | `sync-status.sh:38`: the `gh pr list` call becomes the `integration:vcs` provider's verb, or an `--open-pr <url>` argument filled by the caller. | S |
| `ops-ci-pipeline` | Code host: the settings path (`SKILL.md:101`), the unauthenticated API limit (`:72,122`), "required checks only after they ran once" (`:71,121`). The Lighthouse and Chrome lesson (`:119`) is a tool lesson: keep, or word it as "a headless browser". | None (no script). | S |
| `ops-pull-request` | Code host: template paths, the commands that create, watch and inspect a pull request, the settings path, the rate-limit lesson (`SKILL.md:52,70-72,122`). The body keeps "create the pull request through `integration:vcs`". | `pr-context.sh:44` template paths from a table per host; `:50` `gh pr list` through the provider or an argument. | M |
| `ops-repo-baseline` | If parametrized: everything in `references/host-settings.md` and the four assets is the reference of one host, and `baseline_status.py` uses that host's ecosystem names. That is the whole skill. | See section 4: treat as SUBJECT; no `--platform` now. | L if parametrized, S if stated once |

**Overall size**: about twelve skills need real work. Six are M (`brand-name`, `brand-profile`, `brand-strategy`, `mkt-engage`, `ops-pull-request`, `eng-security-review`), the rest S; the per-platform sources and the generator rule are one more M (two sources matter today: LinkedIn and "code host: GitHub"). Total **M to L**, roughly one extra S or M on rows that phase C already opens. Parametrizing `ops-repo-baseline` or building the shared toolchain table would add an L and an M and is not needed for the goal.

## 3. Distinct platforms and the skills that would need each reference

| Platform or service | Skills with KNOWLEDGE or CODE about it | Copies | Example-only mentions |
|---|---|---|---|
| LinkedIn | `brand-identity`, `brand-name`, `brand-profile`, `brand-strategy`, `mkt-engage`, `mkt-publish`, `mkt-vote-round` | 7 | `mkt-social-copy`, `core-orchestrator` |
| GitHub as code host (`gh`, `.github/`, Actions, Dependabot, CODEOWNERS, rulesets, API) | `ops-pull-request`, `ops-branch-sync`, `ops-ci-pipeline`, `ops-repo-baseline` (subject), `eng-security-review`, `brand-name`, `brand-strategy` | 7 | `core-orchestrator`, `core-skill-creator` (a link), `brand-voice` (a word) |
| GitHub, as a folder name in detection tables | `core-agents-md`, `eng-codebase-map`, `core-security-audit` | table, not a reference | |
| npm as a registry (handles, downloads) | `brand-name`, `brand-strategy` | 2 | `core-research`, `design-execute` |
| npm as an ecosystem (lockfile, `node_modules`) | `eng-security-review`, `ops-repo-baseline`, plus the toolchain tables of `core-agents-md`, `ops-branch-sync`, `eng-code-review` | table | several |
| Instagram, X, Threads, TikTok | `brand-name` (the by-hand list) | 1 each; better one row each in `brand-name`'s table | `core-orchestrator` (`publisher:x`) |
| YouTube, dev.to | `brand-name` | 1 each (table rows) | |
| RDAP services (rdap.org, registro.br) | `brand-name` | 1 (table rows) | |
| Deploy hosts: Netlify, Vercel, Fly, Render, Docker | `core-agents-md`, `eng-codebase-map` (file names), `redact.py` (Netlify token) | table | |
| Credential vendors: AWS, GitHub, Slack, Google, npm, Stripe, Netlify | `eng-code-review`, `ops-repo-baseline` (`redact.py`, same table) | already one shared table (C0.3) | |
| GitLab | `core-agents-md` (a file name) | none | `core-orchestrator` |
| Jira, Linear | none | none | `core-orchestrator` |
| Chrome, Chromium, Playwright, Lighthouse (B) | `brand-identity`, `design-execute`, `ops-ci-pipeline` | none proposed (engine, not platform) | `flow-fix-bug`, `eng-root-cause`, `eng-unit-tests` |
| macOS, Linux (B) | the hash sentence in eight skills; paths in `render.py`, `screenshot.mjs` | one canonical sentence | |

So a shared source would generate **two references with real fan-out** (LinkedIn: 7 skills; code host: 6 or 7), and everything else is better as rows of a table inside the one skill that uses it (`brand-name`) or as a toolchain table.

## 4. The code-host mentions (GitHub, `gh`)

Outside evals and tests they are mostly **CODE and KNOWLEDGE in the delivery skills, and SUBJECT in one**; EXAMPLE is the minority (five lines).

| Skill | What it has | Class | Recommendation |
|---|---|---|---|
| `ops-repo-baseline` | Writes that host's files and lists that host's settings | SUBJECT | **Treat as subject.** State once which host this version writes for (plan default 83) and keep the assets; a second host would be a second set of assets, not a flag. |
| `ops-pull-request` | `gh` commands in steps 4 to 6, template paths, settings path, `gh pr list` in the script | KNOWLEDGE + CODE | **Parametrize**: steps name `integration:vcs`; the commands, template paths and settings path go to the code-host reference; the script takes the open pull request from the provider or an argument. |
| `ops-branch-sync` | `gh pr checks` in step 7, `gh pr list` in the script | KNOWLEDGE + CODE | **Parametrize**, same reference and same script change as above. |
| `ops-ci-pipeline` | One settings path, one trigger phrase, two unnamed limits | KNOWLEDGE + EXAMPLE | **Parametrize** the settings path and the limits (reference); **leave** the trigger phrase in the description (users type it). |
| `eng-security-review` | The alert product named in the description; alert field names; `.github/workflows/` | EXAMPLE + CODE | **Leave** the description words (users type them; the plan already names the product once); **parametrize** only the rule at `SKILL.md:156`. |
| `brand-name`, `brand-strategy` | API endpoints in scripts, a flag named `--github` | CODE | **Parametrize** through the table (section 2). |
| `core-agents-md`, `eng-codebase-map`, `core-security-audit` | `.github/workflows` and other CI file names in detection tables | CODE | **Leave** (they detect what a project uses; a list of known file names is the data). Optionally one shared table. |
| `eng-code-review`, `ops-repo-baseline` (`redact.py`) | Token formats | CODE | **Leave**: already a data table, one source after C0.3. |
| `core-orchestrator` | Examples of what a class covers | EXAMPLE | **Leave**; the plan already removes one product name from its body. |
| `core-skill-creator` | One URL in a link list | EXAMPLE | **Leave**. |
| `brand-voice` | The word in a regex | CODE | **Leave** or generalise in passing. |

## 5. Overlap with `docs/architecture/final-plan-2026-10-02.md` (table "The 48 skills")

| Skill | Already in the plan | Not in the plan |
|---|---|---|
| `mkt-engage` (row 44) | `parse_notification.py`: `--help`, **`--platform`**, an exact host check, a test file (default 57: "`--platform` with one platform implemented"); `mailbox` leaves `requires`. | Moving `SKILL.md:132,136` to a platform reference; the URN vocabulary in steps B1 and B5; the regexes into a table. |
| `mkt-publish` (row 46) | `payload.py`: `--publisher <path>` instead of a path it builds, **`--platform` required** (default 68); "`<platform>` defined"; "gotchas reworded as the provider's facts"; `payload.py verify` instead of a hand-made hash (removes the OS variant at `:112`). | Where the reworded gotchas live (a platform reference instead of the body). |
| `mkt-vote-round` (row 48) | **`vote_update.py` takes `--platform`** (default 67); step 2 resolves the code-host provider by class. | The URL pattern as a table instead of a regex per platform in code. |
| `mkt-social-copy` (row 47) | "the description names no network". | Nothing left. |
| `brand-name` (row 5) | `handle_check.py`: `--responses <file>`, docstring aligned with the code (the docstring lists three by-hand networks, the code five). | The platform table; `SKILL.md:48,96,104,105`. |
| `brand-profile` (row 6) | `requires` gains `integration:vcs`; what to do when the PDF package cannot be installed. | Renaming `linkedin_export.py`, `--platform`, the layout table, `SKILL.md:41`. |
| `brand-strategy` (row 7) | `baselines.py` tells a missing package from a blocked network. | The `--npm` and `--github` flags and endpoints; `SKILL.md:142`. |
| `brand-identity` (row 4) | Template palette made neutral (decision 11). | `SKILL.md:108` and the size comment in the template. |
| `ops-pull-request` (row 41) | "`integration:vcs` named in steps 4 and 6 with what happens without it"; the header comment of `pr-context.sh`; one gotcha without a date. Phase B adds `gh` to the eval image (decision 5), which assumes the skills keep calling it. | Removing the `gh` commands, template paths and settings path from the body; the script's `gh pr list`. **Conflict to settle**: decision 5 measures the `gh` branch; parametrizing removes it. |
| `ops-branch-sync` (row 39) | "`integration:vcs` named in the body with what happens without it". | `sync-status.sh:38`; `SKILL.md:79`. Same conflict with decision 5. |
| `ops-ci-pipeline` (row 40) | "`integration:vcs` named with what happens without it"; pinned versions with a source. | `SKILL.md:101,119` and the unnamed limits. |
| `ops-repo-baseline` (row 42) | "one code host stated once" (default 83); the lines naming this repository, a date and a count leave (decision 11); `redact.py` a generated copy. | Nothing, if it is treated as SUBJECT. |
| `eng-security-review` (row 35) | "one tool name out of an example; the alert product named once". | The npm-only logic of `triage_alerts.py`; `SKILL.md:57,156`. |
| `eng-code-review` (row 27) | `requires: [integration:vcs]`; `redact.py` a generated copy with a neutral docstring. | Nothing needed. |
| `core-orchestrator` (row 12) | "one product name out of the body"; `requirement-classes.md` becomes a generated copy. | Nothing needed (examples stay in the class table). |
| `design-execute` (row 18) | `references/tools.md` names the provider class and loses the dated lessons of one case (this removes the `npm` mention at `:41`). | Nothing needed. |
| `eng-docs`, `eng-implement`, `flow-fix-bug` (rows 29, 31, 38) | Gotchas rewritten as lessons, "two gotchas without tool commands", "a neutral example". | Nothing needed. |
| `eng-root-cause`, `eng-unit-tests`, `core-research`, `core-skill-creator`, `core-agents-md`, `core-project-init`, `core-security-audit`, `eng-codebase-map`, `brand-voice`, `design-system`, `product-backlog` | No related change. | Only optional items (shared toolchain table; the OS variant of the hash sentence, which belongs to the canonical gate sentence of C0.6). |

Also relevant in the plan: C0.3 (`shared/scripts/` with generated copies and `scripts/sync_copies.py`) is the mechanism a per-platform reference would reuse; it lists scripts and two prose copies today, not platform references. C0.2 keeps `publisher:<platform>` as a legal class. Nothing in the plan creates `shared/references/platforms/` or a platform data table, so that convention would be a new C0 item, decided before the lanes of groups 1, 5 and 6 start.
