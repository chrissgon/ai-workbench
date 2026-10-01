# Inventory: capabilities, flows and agents

What the workbench should contain, per area, cross-referenced with the previous repository (`ai-prompts`). This is a plan, not a promise: a skill exists only after it has been written from the template, validated, and refined against at least one real task (see `skills/core-skill-creator/references/authoring-guide.md`).

**State legend.** `reuse`: content carried over, adapted to the template. `rewrite`: same purpose, new content (the old one was organization-specific, stack-bound or duplicated). `merge`: folded into another skill. `create`: no prior content; must be written alongside a real task, never from generic knowledge. `planned`: not built until a real project demands it.

**Wave** is the build order (see the end of this document).

## Core (`core-`), horizontal

| Skill | Produces | Reads | Old repo | State | Wave |
|-------|----------|-------|----------|-------|------|
| core-orchestrator | routes a request to one capability or flow across all areas; reads project state first | docs/workbench/state.md | orchestrator agent (engineering only) | rewrite | 0 |
| core-clarify | interrogation until shared understanding; decisions recorded in state | — | grill-me | reuse | 0 |
| core-research | sourced research brief: claims with URL and access date, recency check, contradictions flagged | — | — | create | 0 |
| core-critique | adversarial review of any plan or artifact; at least two failure modes, each with a test | any artifact | solution-critic (bug fixes only) | rewrite, generalized | 0 |
| core-project-init | `docs/` layout, `docs/workbench/state.md`, autonomy mode, project `AGENTS.md` | — | agents-md-generator | rewrite | 0 |
| core-agents-md | create or update a project's `AGENTS.md` from its codebase and conventions | codebase | agents-md-generator | reuse | 0 |
| core-skill-creator | a new skill scaffolded, evaluated with strong and floor models, refined | authoring guide | — | create | 0 |
| core-security-audit | audit of the whole workbench against the security checklist; vetting of third-party skills before install | skills, agents, providers, adapters | — | 0.2, grounded in the audit of 2026-09-27; strong delta +0.125, floor 0.875 | — |

`core-research` requires `search:web`. Tooling that is not a skill but belongs to wave 0: `scripts/eval-run` (runs an eval case with and without a skill, on a strong and a floor model, and grades assertions).

## Business (`biz-`)

All six come from splitting `startup-ceo` (573 lines) and `startup-strategy-workflow` (567 lines), which duplicated each other. Content is reused; structure is rewritten.

| Skill | Produces | Reads | State | Wave |
|-------|----------|-------|-------|------|
| biz-validate-idea | docs/business/idea-validation.md | — | rewrite | 2 |
| biz-market-analysis | docs/business/market.md | idea-validation (optional), research briefs | 0.4, grounded in `startup-ceo` and a real company's run of 2026-09-28; requires `search:web`; passes at eval iteration 8 (strong claude-code Opus 0.958 with vs 0.283 without; floor DeepSeek V3.2 0.917, threshold 0.8); scripts rank.py, capacity.py, check_refs.py, lint_market.py | 2 |
| biz-icp-positioning | docs/business/icp.md, docs/business/positioning.md | market | 0.3, grounded in `startup-ceo` and a real company's segment research of 2026-09-28; requires `search:web`; passes at eval iteration 1 (strong 0.933 vs 0.700, floor 0.85); scripts rank.py, check_refs.py, lint_icp.py | 2 |
| biz-business-model | docs/business/business-model.md, docs/business/pricing.md | icp, positioning | rewrite | 2 |
| biz-gtm | docs/business/gtm.md | icp, positioning, business-model | rewrite | 2 |
| biz-business-plan | docs/business/business-plan.md | all of the above | rewrite | 2 |

## Product (`product-`)

| Skill | Produces | Reads | Old repo | State | Wave |
|-------|----------|-------|----------|-------|------|
| product-feature-spec | docs/product/specs/<feature>.md: requirements, edge cases, acceptance criteria | prd (optional) | spec-extractor | reuse | 1 |
| product-backlog | docs/product/backlog.md: epics, stories, tasks, dependencies | prd or spec | product-manager | reuse | 1 |
| product-discovery | docs/product/discovery.md: problem, hypotheses, segments | business artifacts | — | create | 2 |
| product-prd | docs/product/prd.md | discovery, positioning | prd-generator prompt, spec-extractor | rewrite | 2 |
| product-roadmap | docs/product/roadmap.md: prioritized, with method stated | prd | — | create | 2 |
| product-metrics | docs/product/metrics.md: north star, KPIs, instrumentation | prd | — | create | 2 |

Two spec levels on purpose: `product-prd` is product-level, `product-feature-spec` is feature-level and is what engineering flows consume.

## Brand (`brand-`)

All four come from splitting `brand-designer` (392 lines) and `brand-workflow` (1901 lines), which duplicated each other.

| Skill | Produces | Reads | State | Wave |
|-------|----------|-------|-------|------|
| brand-profile | docs/brand/profile.md: a person's trajectory, proof, goals, audiences, limits, writing samples | — | create (backlog PB1) | 3 |
| brand-name | docs/brand/name.md: name or handle research (candidates, availability of handles, domains and package scopes, conflicts, pronunciation in each language), or an audit of a name already in use | profile, strategy | create; first case an existing handle, audit mode (backlog PB12) | 3 |
| brand-strategy | docs/brand/strategy.md, for a person or a company | profile (person) or positioning, icp (company) | rewrite | 3 |
| brand-identity | docs/brand/identity.md plus brand tokens | strategy | rewrite; `generator:image` optional for moodboards; grounded in a LinkedIn cover for a real personal brand (backlog PB10) | 3 |
| brand-voice | docs/brand/voice.md, for posts and replies | strategy, real writing samples | rewrite | 3 |
| brand-guidelines | docs/brand/guidelines.md: the brand guide, for a person or a company; for a person, one guide an agent and a human both follow (who, positioning, name, visual, voice, claims, never-expose and the sensitive-topics lock, do and don't, examples) | profile, name, strategy, identity, voice | rewrite; first case a real personal brand guide (backlog PB13) | 3 |

## Design (`design-`)

| Skill | Produces | Reads | Old repo | State | Wave |
|-------|----------|-------|----------|-------|------|
| design-ux-flows | docs/design/flows.md: user flows, information architecture, wireframe notes | prd, research | — | create | 3 |
| design-system | docs/design/design-system.md: tokens, components, states | brand identity | — | create | 3 |
| design-brief | docs/design/briefs/<artifact>.md: brief and prompt for an AI design tool, any visual artifact (screen, mockup, logo, presentation, animation, image) | design-system, flows, messaging | design-ui (screen specs and the first brief) | create; replaces design-ui | 3 |
| design-execute | docs/design/results/<artifact>.md: runs per direction, outputs, critique, decision | briefs | — | create; automatic with `integration:design-tool`, `generator:image` or a browser, assisted otherwise; side effect `create`; replaces design-generate-asset | 3 |
| design-handoff | docs/design/handoff/<screen>.md: implementation spec from an approved design or export | results, briefs, design-system, flows, specs | — | create | 3 |
| design-implementation-validation | validation report, design vs. code | handoff or design tool, code | design-implementation-validator (319 lines, evals, utilities) | reuse, restructure to standard folders; requires `integration:design-tool` | 3 |
| design-user-research | docs/design/research.md: plan, guide, synthesis | discovery | — | create | 3 |
| design-accessibility-review | docs/design/a11y-audit.md | screens or code | — | create | 5 |

## Engineering (`eng-`)

The most mature area in the old repository. Stack-agnostic procedures; stacks arrive as `references/stacks/<stack>.md` from real projects.

| Skill | Produces | Reads | Old repo | State | Wave |
|-------|----------|-------|----------|-------|------|
| eng-codebase-map | docs/engineering/architecture.md for an existing system | codebase | high-level-mapping prompt | rewrite | 1 |
| eng-architecture | architecture and ADRs for a feature or system | feature spec | system-designer | reuse | 1 |
| eng-tradeoffs | ADR comparing options | options | tradeoff-analyzer | reuse | 1 |
| eng-impact-analysis | impact section of docs/engineering/plans/<task>.md | codebase | component-mapper | reuse | 1 |
| eng-root-cause | root-cause section of the plan; never proposes fixes | bug report | root-cause-analyzer, debug-issue | merge | 1 |
| eng-unit-tests | failing unit tests before implementation | spec, plan | test-generator | reuse | 1 |
| eng-implement | code that makes tests pass; feature and patch paths | tests, plan | minimal-impl-generator, patch-implementer | merge | 1 |
| eng-integration-tests | integration and end-to-end tests after implementation | implementation | integration-test-generator | reuse | 1 |
| eng-refactor | improved code with tests green | implementation | refactor-optimizer | reuse | 1 |
| eng-code-review | review report; perspectives (quality, edge cases, regression, performance, security) and a bug-fix checklist | diff | code-reviewer, multi-agent-analyzer, post-fix-reviewer | merge | 1 |
| eng-docs | documentation updates for the change | changes | documentation-writer skill | reuse | 1 |
| eng-security-review | security review of a project: 0.1 triages dependency alerts (grouped by manifest and package, update or dismiss with the host's reason, dismissals behind a confirmation gate); later secrets, authentication and authorization, input handling, configuration (backlog S14) | alerts from `integration:vcs`, codebase | — | draft 0.1, grounded in the 30 Dependabot alerts of ai-workbench on 2026-09-28; strong delta +0.21, floor 0.95 | — |
| eng-data-model | schema and migration plan | architecture | — | planned | — |

## Delivery and operations (`ops-`)

| Skill | Produces | Reads | Old repo | State | Wave |
|-------|----------|-------|----------|-------|------|
| ops-pull-request | a pull request | branch, spec or plan | pr-creator, create-github-pull-request prompt | rewrite, organization specifics removed; requires `integration:vcs`; side effect `create` | 1 |
| ops-branch-sync | branch updated with its base, conflicts resolved | — | backmerge-master prompt, deploy-to-staging | rewrite, generic; side effect `push` | 1 |
| ops-repo-baseline | a repository's security baseline: CI with pinned actions, CODEOWNERS, Dependabot, SECURITY.md, pre-commit hook, and the host settings (ruleset with signed commits, linear history and required checks; squash only; secret scanning with push protection; private reporting) applied after one approval or as a checklist | repository | — | draft 0.1, grounded in the ai-workbench setup of 2026-09-27; writes the in-repository files and the host checklist, changes no host setting (S17 for that); strong delta +0.51, floor 0.796 | — |
| ops-ci-pipeline | pipeline configuration, settings checklist, Pipeline section of the plan | repository | — | create; requires `integration:vcs`; side effect `push` | 4 |
| ops-release | release notes and version | changes | — | create; side effect `publish` | 4 |
| ops-qa-handover | docs/delivery/qa/<ticket>.md | diff, spec | qa-notes-handover prompt | rewrite | 5 |
| ops-infra | infrastructure as code | architecture | — | planned | — |
| ops-observability | dashboards and alerts plan | architecture | — | planned | — |
| ops-incident | runbook and postmortem | incident | — | planned | — |

## Marketing and growth (`mkt-`)

No prior content. Every skill here is `create` and must be written alongside a real launch.

| Skill | Produces | Reads | State | Wave |
|-------|----------|-------|-------|------|
| mkt-messaging | docs/marketing/messaging.md | positioning, brand voice | create | 4 |
| mkt-launch-plan | docs/marketing/launch-plan.md | messaging, gtm | create | 4 |
| mkt-content-plan | docs/marketing/calendar.md | launch-plan | create | 4 |
| mkt-social-copy | docs/marketing/content/<post>.md | messaging, voice | create | 4 |
| mkt-publish | a scheduled or published post, recorded in calendar and state | content, asset | create; requires `publisher:<platform>`; side effect `publish` | 4 |
| mkt-engage | replies to comments on the person's own posts inside an engagement policy | voice, strategy, notification e-mails | create; requires `publisher:<platform>` and a mailbox class; side effect `publish` (backlog PB6) | 4 |
| mkt-vote-round | the weekly vote's post and the next round's topics, for one approval | vote files, calendar, voice, strategy | create; requires `integration:vcs` (backlog PB15) | 4 |
| mkt-landing-page | docs/marketing/landing.md: structure and copy | messaging | create | 5 |
| mkt-seo | docs/marketing/seo.md | landing, content | create | 5 |
| mkt-email | docs/marketing/campaigns/<name>.md | messaging | create; requires `mailer` for the send step; side effect `send` | 5 |
| mkt-analytics | docs/marketing/analytics.md: measurement plan, experiments | launch-plan | create | 5 |

## AI and machine learning (`ai-`), horizontal

| Skill | Produces | Reads | State | Wave |
|-------|----------|-------|-------|------|
| ai-opportunity-assessment | docs/ai/opportunity.md; must be able to conclude "no AI here" | idea or discovery | create | 2 |
| ai-feature-requirements | docs/ai/requirements.md: quality metrics, fallbacks, cost ceiling | prd, opportunity | create | 5 |
| ai-ux-patterns | docs/ai/ux.md: uncertainty, feedback, human-in-the-loop | flows | create | 5 |
| ai-llm-integration | code plus docs/ai/integration.md: prompts, retrieval, tool use | requirements | create | 5 |
| ai-evals | docs/ai/evals/: datasets, graders, thresholds for the product's AI | requirements | create | 5 |
| ai-governance | docs/ai/governance.md: privacy, prompt injection, compliance | requirements | create | 5 |
| ai-observability-cost | monitoring and cost plan | integration | planned | — |
| ai-ml-model | classical model and its training data plan | data | planned | — |

## Assistant (`asst-`), optional

Nothing until the actuators, the pre-approved gate and a runtime exist. Candidates, each only for a recurring task with a real procedure: asst-inbox-triage, asst-daily-brief, asst-follow-ups.

## Flows (`flow-`)

| Flow | Area | Phases | Old repo | State | Wave |
|------|------|--------|----------|-------|------|
| flow-fix-bug | engineering | root-cause → unit-tests → impact-analysis (optional) → tradeoffs (optional) → implement → integration-tests (optional) → docs (optional) → code-review → pull-request | debug-workflow (767 lines) | rewrite | 1 |
| flow-build-feature | engineering | feature-spec → architecture → unit-tests → implement → integration-tests → code-review → docs → pull-request | feature-workflow (811 lines) | rewrite | 1 |
| flow-improve-code | engineering | codebase-map or impact-analysis → tradeoffs → refactor → code-review → pull-request | improvement-workflow (601 lines) | rewrite | 1 |
| flow-new-project | engineering | clarify → prd or feature-spec → backlog → architecture → implement per task → pull-request | greenfield-workflow (482 lines) | rewrite | 1 |
| flow-implement-ticket | engineering | read ticket → clarify → route to fix-bug, build-feature or improve-code → update ticket | — | create; requires `integration:issue-tracker` | 1 |
| flow-business-plan | business | validate-idea → ai-opportunity-assessment → market-analysis → icp-positioning → business-model → gtm → business-plan | startup-strategy-workflow | rewrite | 2 |
| flow-brand | brand | profile (person) → name → strategy → identity → voice → guidelines | brand-workflow | rewrite; phases requested by the user on 2026-09-29 | 3 |
| flow-design | design | user-research → ux-flows → design-system → ui → handoff | — | create | 3 |
| flow-social-post | marketing | social-copy → generate-asset → confirmation gate → publish → calendar | — | create | 4 |
| flow-launch | marketing | messaging → launch-plan → content-plan → landing-page → analytics | — | create | 4 |
| flow-new-product | cross-area | business-plan → discovery, prd, roadmap → brand (optional) → design → new-project → ci-pipeline, release → launch | — | create | 5 |

Flows may invoke flows one level deep (`flow-new-product` invokes `flow-business-plan`, `flow-new-project`, `flow-launch`). Never deeper.

## Agents

| Agent | Purpose | Skills | Old repo | State | Wave |
|-------|---------|--------|----------|-------|------|
| researcher | sourced research in isolation, returns a brief | core-research | — | create | 0 |
| explorer | read-only codebase exploration, returns a map or impact list | eng-codebase-map, eng-impact-analysis | — | create | 1 |
| implementer | writes code and tests for one task in isolation, stack from the project's `AGENTS.md` | eng-implement, eng-unit-tests | backend-engineer (NestJS), frontend-engineer (React) | rewrite, stack-agnostic | 1 |
| reviewer | one review perspective per instance; several run in parallel when the harness allows | eng-code-review, core-critique | code-reviewer, multi-agent-analyzer | rewrite | 1 |

## Dropped from the old repository

| Item | Why |
|------|-----|
| btw | a harness behaviour (side question), not a skill |
| ikigai-coach, life-purpose-workflow | out of scope |
| documentation-writer agent | duplicate of the skill with different content |
| deploy-to-staging | organization-specific; the generic part became ops-branch-sync |
| site-rewrite-planner | organization-specific; its templates (component inventory, API mapping, migration plan) inspire a future eng migration skill |
| orchestrator agent | replaced by core-orchestrator |
| backend-engineer, frontend-engineer agents | replaced by the stack-agnostic implementer |

## Counts

| Kind | Build | Planned | Total |
|------|-------|---------|-------|
| Capabilities | 62 | 8 | 70 |
| Flows | 11 | 0 | 11 |
| Agents | 4 | 0 | 4 |

Sixty-two skills is the reason packs exist. It is also why each wave must ship refined skills, not drafts of everything.

## Build order

| Wave | Content | Why this order |
|------|---------|----------------|
| 0 | core (7 skills), researcher agent, eval tooling | every flow depends on orchestrator, clarify, critique, state; the eval runner is needed to refine anything |
| 1 | engineering (11), product-feature-spec, product-backlog, ops-pull-request, ops-branch-sync, 5 engineering flows, explorer, implementer, reviewer | the most mature old content, and the area used daily, so the refinement loop runs on real tasks from day one |
| 2 | business (6), product (4 remaining), ai-opportunity-assessment, flow-business-plan | top of the lifecycle chain; content exists in startup-ceo; needed before anything downstream in flow-new-product |
| 3 | brand (4), design (7), flow-brand, flow-design | content exists for brand; design needs a real product to be written against |
| 4 | marketing first slice (5), ops-ci-pipeline, ops-release, flow-social-post, flow-launch, first providers (publisher, image) | actuators and the scheduled-post scenario; needs a real launch |
| 5 | flow-new-product, remaining marketing (4), remaining AI (5), ops-qa-handover, design-accessibility-review, assistant candidates | the capstone flow ties every area; the rest fills in behind real demand |

Planned items are never scheduled; they are built when a project needs them.

## Real projects

Skills in waves 2 to 5 are written alongside the phase of a real project that needs them and refined against it before they count as done. When that project is an AI product, the AI skills it needs (`ai-feature-requirements`, `ai-llm-integration`, `ai-evals`, `ai-governance`) move forward to the wave of its engineering, not wave 5; `ai-opportunity-assessment` still runs first and must still be able to say which parts do not need AI.

## Evaluation status

A skill counts as done only when its eval result is recorded here or in its Progress line (backlog T11): strong with and without the skill, floor with the skill, iteration. These skills are built but have no recorded pass (2026-09-30):

- core-agents-md
- core-clarify
- core-critique
- core-orchestrator
- core-project-init
- core-research
- core-skill-creator
- design-execute
- design-handoff
- design-ux-flows
- eng-architecture
- eng-code-review
- eng-codebase-map
- eng-docs
- eng-impact-analysis
- eng-implement
- eng-integration-tests
- eng-refactor
- eng-root-cause
- eng-tradeoffs
- eng-unit-tests
- ops-branch-sync
- ops-ci-pipeline
- ops-pull-request
- product-backlog
- product-feature-spec
- product-prd
- product-roadmap

Recorded on 2026-10-01 (strong Opus 5.5, also the grader; floor DeepSeek V3.2; 3 runs per case):

- design-brief: strong 0.96 with vs 0.36 without; floor 0.92 at iteration 4. The lint result is written to a `.lint.json` file and quoted, template fields get their longest value from `longest_value.py`, and the cases gained the page and messaging fixtures they cited.
- design-system: strong 0.97 vs 0.37; floor 1.00 at iteration 3 (5 of 6 floor runs; one failed on a provider error). Fixtures rebuilt as a project tree with screens and components; the lint checks screens against the flows and library values verbatim; an unanswered typeface question is written as an open question.
- mkt-messaging: strong 1.00 vs 0.62; floor 0.81 at iteration 4. Fixtures at the paths the prompt names; the lint needs a method and a date on every proof, checks number words against the proofs and refuses a section with no demo.
- product-prd: strong 1.00 vs 0.48; floor 0.69 at iteration 6: not passing (the floor model is unstable on fixing an existing PRD).
- product-feature-spec: strong 1.00 vs 0.25; floor 0.74 at iteration 5: not passing (the floor model is unstable on the no-input case and on revising a spec).

## Progress

Wave 0:
- [x] core-orchestrator
- [x] core-project-init
- [x] core-clarify
- [x] core-research
- [x] core-critique
- [x] core-agents-md
- [x] core-skill-creator
- [x] researcher agent
- [x] eval runner (`skills/core-skill-creator/scripts/eval_run.py`; first runs on real tasks of the engineering skills; each case now runs in its own git repository, after a floor run's `git commit` reached the workbench, and may declare `setup` commands (a branch with commits) and `skills` it depends on (a flow's phases, linked in both variants); it does not yet report whether the model invoked the skill, which had to be read from the session transcripts)

Wave 1:
- [x] eng-codebase-map
- [x] eng-impact-analysis
- [x] eng-root-cause
- [x] eng-architecture
- [x] eng-tradeoffs
- [x] eng-unit-tests
- [x] eng-implement
- [x] eng-integration-tests
- [x] eng-refactor
- [x] eng-code-review
- [x] eng-docs
- [x] product-feature-spec
- [x] product-backlog
- [x] ops-pull-request (from two real pull requests and the generic part of pr-creator; bundles `scripts/pr-context.sh`; the floor model once changed code while preparing a pull request, to watch in real use)
- [x] ops-branch-sync
- [x] flow-fix-bug (from a real header-menu bug in a component library: nine phases, the fix in the library and the records in its documentation site; floor 0.8 at the threshold, the floor model sometimes starts eng-root-cause directly instead of the flow)
- [ ] flow-build-feature, flow-improve-code, flow-new-project, flow-implement-ticket
- [ ] agents explorer, implementer, reviewer

Built ahead of their wave, with a documentation-site rebuild as the real project:
- [x] product-prd, product-roadmap (wave 2)
- [x] design-ux-flows, design-system (wave 3)
- [x] design-brief, design-execute (wave 3; replace design-ui and design-generate-asset: design skills produce the inputs, a specialized AI design tool or a code prototype produces the design)
- [x] mkt-messaging (wave 4)
- [x] ops-ci-pipeline (wave 4; from a real documentation-site pipeline: one build tested and deployed from GitHub Actions to Netlify, previews per pull request, protected main; the floor model still misses the revoke-the-pasted-token rule and exact version pins now and then)
- [x] design-handoff (wave 3; unpacks single-file HTML exports, maps invented tokens, reads motion from scripts)
- [ ] design-system v0.3: any input (code, images, documents, a live site) or a short interview; onboarding prompt for the design tool

Built against a real personal brand (2026-09-29). Evals: strong claude-code Opus 5.5 (also the grader), floor DeepSeek V3.2 through agents-dir, 3 runs per case, floor runs in parallel with `eval_run.py --jobs`:
- [x] brand-profile 0.4 (strong 1.0 with vs 0.58 without; floor 0.917. Floor went 0.48 → 0.51 while the gate said "ask only what is missing": the floor model kept asking to confirm recorded decisions and stopped without writing. What worked was writing the profile first and turning every question into an open question inside it, with a default recommendation per item. Scripts: `linkedin_export.py` (drops contact data, computes durations), `check_profile.py`, `sensitive_topics.py`.)
- [x] brand-strategy 0.2 (strong 1.0 vs 0.80; floor 0.897 at 0.1; 0.2 fixes the two floor misses, re-offering recorded choices and writing 0 for a product that was not found, not rerun. Script: `baselines.py`.)
- [x] brand-voice 0.2 (strong 0.97 vs 0.58; floor 0.783 at 0.1, 0.878 at 0.2 after banning ranges as recommendations, "reconsider" labels and added words in rewrites. Script: `voice_stats.py`, counts and a `voice-rules` check.)
- [x] brand-identity 0.1 (strong 1.0 vs 0.50; floor 0.95 over five runs plus 1.0 on the rerun of the one run that hit the 900 s timeout while fetching font licences. Script: `contrast.py`; asset: `piece-template.html`.)
- [x] brand-name 0.3 (strong 1.0 vs 0.61 at 0.3; floor 0.72 at 0.2, 0.944 at 0.3 after default recommendations, an explicit "this skill never buys" and naming each login-only network. Script: `handle_check.py`.)
- [x] brand-guidelines 0.2 (strong 1.0 vs 0.68 at 0.2; floor about 0.5 at 0.1, when it wrote a placeholder guide with strategy and voice missing and put paraphrased rules among the examples; 0.845 at 0.2 after the gate and two checks in `check_guide.py`: every do-and-don't cell a quote, and every missing brand file named with its skill.)
- [ ] flow-brand (backlog PB14)

The content engine and the 24-hour agent (2026-09-29; backlog PB4 to PB7). Same eval setup as the brand skills; fixtures use the fictional persona Dana Example:
- [x] mkt-content-plan 0.1 (strong 1.0 vs 0.90; floor 0.844 at iteration 1, 0.944 at iteration 3 after `slots.py --after-calendar` took over continuing the language rotation, which the floor model got wrong by hand. Script: `slots.py`.)
- [x] mkt-social-copy 0.1 (strong 1.0 vs 0.71; floor 0.889, then 0.875 at iteration 4. Still failing: asked to "say how much money it saved", the floor model writes a vague figure ("six figures", "tens of thousands") in about one run in three, despite the rule against any form of an unmeasured number. Script: `check_post.py`, which runs `voice_stats.py` and `sensitive_topics.py` on the exact post and first comment.)
- [x] mkt-publish 0.1 (strong 1.0 vs 0.625; floor 0.889, then 0.875 at iteration 4. Still failing: when the token check stops the run before the payload exists, the floor model calls an older approval with a different hash "matching"; `payload.py approval` decides it once the payload is built. Script: `payload.py` (build, verify, approval).)
- [x] mkt-engage 0.1 (runtime mode and the policy procedure; iteration 1: strong 0.917 without the skill; iteration 2: strong 0.967, floor 0.911; iteration 3 after "no motive the post does not state": strong 1.0 on the praise case, floor 0.87 there. Still failing on the floor model: it adds a cause or a motive to a thank-you ("that's why I built it this way") in two runs of three, and once reused a self-reported 64% latency cut as a product benchmark. A comparison on real comments the same night (Sonnet 5.5 16/16, DeepSeek V3.2 10/16, one invented technical claim) made Sonnet the runtime model and added the source check to the gate. Scripts: `policy_gate.py`, `parse_notification.py` (comment links; the e-mail layout is still unverified).)
- [x] mkt-vote-round 0.1 (2026-09-30; runtime mode and the interactive procedure. Iteration 1: strong 0.83 (0.57 without), floor 0.74. Iteration 2, after "facts from the material behind this topic", "a used topic the person asks for is named and left out", "one block, no draft before it", two assertions aligned with their expected output and `grader_files` in eval_run.py: strong 0.96 (0.67 without), floor 0.89 over the two runtime cases; the interactive case timed out at 900 s on the floor model in all three runs, and with 1800 s (iteration 3) scored 0.67: asked to put an already used topic (tinykv 0.5 TTL) in the next round, the floor model rewords it and keeps it in all three runs, and once calls the draft approved. The runtime mode, the one the weekly step uses, passes; the interactive mode does not yet pass on the floor model. Still failing on the floor model: numbers from another note put into the winner's post, and a second, duplicated proposal block. Scripts: `vote_state.py`, `vote_update.py`.)

Built against a real one-person company (2026-09-28/29):
- [x] biz-market-analysis (wave 2; 8 eval iterations. What moved the floor model from 0.475 to 0.917 was scripts, not wording: `check_refs.py` for citations, `lint_market.py` for prices under Implications, price cells, citation form and uncited figures, `rank.py` refusing free-text sources. Wording alone left the same mistakes in place from iteration 2 to 6. Remaining misses: summaries labelled as quotes, uncited figures in the Comparison reading.)
- [x] biz-icp-positioning (wave 2; passes at eval iteration 1: strong claude-code Opus 0.933 with vs 0.700 without, floor DeepSeek V3.2 0.85; built with `lint_icp.py`, `check_refs.py` and `rank.py` from the start, after what biz-market-analysis taught. 0.3 adds a `Recommended:` line under every scope question and sourced alternatives, the two iteration-1 misses, not rerun. The positioning step has not met a real case yet: the real company's waits for customer interviews.)
