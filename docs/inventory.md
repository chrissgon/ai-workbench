# Inventory: capabilities, flows and agents

What the workbench should contain, per area, cross-referenced with the previous repository (`ai-prompts`). This is a plan, not a promise: a skill exists only after it has been written from the template, validated, and refined against at least one real task (see `docs/skill-authoring-guide.md`).

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

`core-research` requires `search:web`. Tooling that is not a skill but belongs to wave 0: `scripts/eval-run` (runs an eval case with and without a skill, on a strong and a floor model, and grades assertions).

## Business (`biz-`)

All six come from splitting `startup-ceo` (573 lines) and `startup-strategy-workflow` (567 lines), which duplicated each other. Content is reused; structure is rewritten.

| Skill | Produces | Reads | State | Wave |
|-------|----------|-------|-------|------|
| biz-validate-idea | docs/business/idea-validation.md | — | rewrite | 2 |
| biz-market-analysis | docs/business/market.md | idea-validation | rewrite; requires `search:web` | 2 |
| biz-icp-positioning | docs/business/icp.md, docs/business/positioning.md | market | rewrite | 2 |
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
| brand-strategy | docs/brand/strategy.md | positioning, icp | rewrite | 3 |
| brand-identity | docs/brand/identity.md plus brand tokens | strategy | rewrite; `generator:image` optional for moodboards | 3 |
| brand-voice | docs/brand/voice.md | strategy | rewrite | 3 |
| brand-guidelines | docs/brand/guidelines.md | identity, voice | rewrite | 3 |

## Design (`design-`)

| Skill | Produces | Reads | Old repo | State | Wave |
|-------|----------|-------|----------|-------|------|
| design-ux-flows | docs/design/flows.md: user flows, information architecture, wireframe notes | prd, research | — | create | 3 |
| design-system | docs/design/design-system.md: tokens, components, states | brand identity | — | create | 3 |
| design-ui | docs/design/screens/<screen>.md | flows, design-system | — | create; `integration:design-tool` optional | 3 |
| design-handoff | docs/design/handoff/<screen>.md | screens, design-system | — | create | 3 |
| design-implementation-validation | validation report, design vs. code | handoff or design tool, code | design-implementation-validator (319 lines, evals, utilities) | reuse, restructure to standard folders; requires `integration:design-tool` | 3 |
| design-generate-asset | image files plus the brief used | brand identity | — | create; requires `generator:image` | 4 |
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
| eng-data-model | schema and migration plan | architecture | — | planned | — |

## Delivery and operations (`ops-`)

| Skill | Produces | Reads | Old repo | State | Wave |
|-------|----------|-------|----------|-------|------|
| ops-pull-request | a pull request | branch, spec or plan | pr-creator, create-github-pull-request prompt | rewrite, organization specifics removed; requires `integration:vcs`; side effect `create` | 1 |
| ops-branch-sync | branch updated with its base, conflicts resolved | — | backmerge-master prompt, deploy-to-staging | rewrite, generic; side effect `push` | 1 |
| ops-ci-pipeline | pipeline configuration | repository | — | create | 4 |
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
| flow-fix-bug | engineering | impact-analysis → root-cause → critique → unit-tests → implement → code-review → pull-request | debug-workflow (767 lines) | rewrite | 1 |
| flow-build-feature | engineering | feature-spec → architecture → unit-tests → implement → integration-tests → code-review → docs → pull-request | feature-workflow (811 lines) | rewrite | 1 |
| flow-improve-code | engineering | codebase-map or impact-analysis → tradeoffs → refactor → code-review → pull-request | improvement-workflow (601 lines) | rewrite | 1 |
| flow-new-project | engineering | clarify → prd or feature-spec → backlog → architecture → implement per task → pull-request | greenfield-workflow (482 lines) | rewrite | 1 |
| flow-implement-ticket | engineering | read ticket → clarify → route to fix-bug, build-feature or improve-code → update ticket | — | create; requires `integration:issue-tracker` | 1 |
| flow-business-plan | business | validate-idea → ai-opportunity-assessment → market-analysis → icp-positioning → business-model → gtm → business-plan | startup-strategy-workflow | rewrite | 2 |
| flow-brand | brand | strategy → identity → voice → guidelines | brand-workflow | rewrite | 3 |
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
| Capabilities | 62 | 6 | 68 |
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
| 4 | marketing first slice (5), design-generate-asset, ops-ci-pipeline, ops-release, flow-social-post, flow-launch, first providers (publisher, image) | actuators and the scheduled-post scenario; needs a real launch |
| 5 | flow-new-product, remaining marketing (4), remaining AI (5), ops-qa-handover, design-accessibility-review, assistant candidates | the capstone flow ties every area; the rest fills in behind real demand |

Planned items are never scheduled; they are built when a project needs them.

## First real project: Telar

Telar (AI-generated linguistic content; a sample exists, v1 is about to start) is the vehicle for every wave after 0. Two consequences:

- **AI moves forward.** Telar is an AI product, so `ai-feature-requirements`, `ai-llm-integration`, `ai-evals` and `ai-governance` are needed in the same wave as Telar's engineering, not in wave 5. `ai-opportunity-assessment` still runs first and must still be able to say which parts of Telar do not need AI.
- **Business and product come before engineering for Telar.** v1 should be built on a validated PRD, so `flow-business-plan` and the product skills are needed as soon as core exists, while engineering skills are refined on the sample's real code tasks.

Skills in waves 2 to 5 are written alongside the corresponding Telar phase and refined against it before they count as done.

## Progress

Wave 0:
- [x] core-orchestrator
- [x] core-project-init
- [x] core-clarify
- [x] core-research
- [x] core-critique
- [ ] core-agents-md
- [ ] core-skill-creator
- [x] researcher agent
- [ ] eval runner
