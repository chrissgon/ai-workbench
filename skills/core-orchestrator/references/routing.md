# Routing table: intent → area → skill

Match the intent column, not the example words. Skills marked (planned) are not built yet; when routed to one, say so and fall back (see SKILL.md step 4). Keep this table in sync with `docs/inventory.md` in the workbench.

## Business (`biz-`)

| Intent | Skill |
|--------|-------|
| Is this idea worth pursuing; who has the problem; is there a market | biz-validate-idea |
| Size the market, map competitors and alternatives | biz-market-analysis |
| Who exactly we sell to; how we position against alternatives | biz-icp-positioning |
| How we make money; pricing; unit economics; validate the business model | biz-business-model |
| How we reach and acquire the first customers | biz-gtm |
| The whole plan in one document; investor narrative | biz-business-plan |
| Validate or build a business end to end | flow-business-plan |

## Product (`product-`)

| Intent | Skill |
|--------|-------|
| Frame the problem, hypotheses and segments before deciding what to build | product-discovery |
| Product-level requirements document | product-prd |
| Feature-level spec with edge cases and acceptance criteria | product-feature-spec |
| What to build first and why; prioritization | product-roadmap |
| Break work into epics, stories, tasks | product-backlog |
| How we measure product success | product-metrics |

## Brand (`brand-`)

| Intent | Skill |
|--------|-------|
| Purpose, personality, positioning of the brand | brand-strategy |
| Logo direction, color, typography, imagery, brand tokens | brand-identity |
| How the brand speaks; tone; messaging pillars | brand-voice |
| The brand book that compiles it all | brand-guidelines |
| Create a brand from nothing | flow-brand |

## Design (`design-`)

| Intent | Skill |
|--------|-------|
| Plan or synthesize research with users | design-user-research |
| User flows, information architecture, wireframes | design-ux-flows |
| Tokens and components as a system | design-system |
| Screen-level design specs | design-ui |
| Spec for engineering: layout, tokens, states, breakpoints | design-handoff |
| Does the implementation match the design | design-implementation-validation |
| Produce an image or visual asset consistent with the brand | design-generate-asset |
| Accessibility audit | design-accessibility-review (planned) |
| Design a product's experience end to end | flow-design |

## Engineering (`eng-`)

| Intent | Skill |
|--------|-------|
| Understand an existing codebase's architecture | eng-codebase-map |
| Design the architecture for a feature or system; ADRs | eng-architecture |
| Choose between technical approaches | eng-tradeoffs |
| What does this change touch; dependencies; blast radius | eng-impact-analysis |
| Why does this bug happen (no fixing) | eng-root-cause |
| Write failing unit tests before code | eng-unit-tests |
| Make the tests pass; implement a fix or feature | eng-implement |
| Integration and end-to-end tests after implementation | eng-integration-tests |
| Improve code without changing behaviour | eng-refactor |
| Review a diff; security, edge cases, regressions, performance | eng-code-review |
| Update documentation for a change | eng-docs |
| Fix a bug end to end | flow-fix-bug |
| Build a feature end to end | flow-build-feature |
| Improve existing code end to end | flow-improve-code |
| Start a codebase from nothing | flow-new-project |
| Take a ticket and implement it ("check ticket N and implement it", any ticket id or issue link) | flow-implement-ticket |

## Delivery and operations (`ops-`)

| Intent | Skill |
|--------|-------|
| Open a pull request | ops-pull-request |
| Update my branch with its base; resolve conflicts | ops-branch-sync |
| Set up or change the CI pipeline | ops-ci-pipeline (planned) |
| Cut a release; release notes; versioning | ops-release (planned) |
| Notes for QA about a change | ops-qa-handover (planned) |

## Marketing and growth (`mkt-`)

| Intent | Skill |
|--------|-------|
| What we say and to whom; messaging framework | mkt-messaging |
| Plan a launch | mkt-launch-plan |
| Content calendar | mkt-content-plan |
| Write a social post (text only, nothing published) | mkt-social-copy |
| Publish or schedule a post that is already written and illustrated | mkt-publish |
| Landing page structure and copy | mkt-landing-page (planned) |
| SEO plan | mkt-seo (planned) |
| Email campaign or sequence | mkt-email (planned) |
| Measurement plan; experiments | mkt-analytics (planned) |
| Any request that ends in a post being published or scheduled and the post still has to be written or illustrated ("schedule a post about X", "post about our launch tomorrow") | flow-social-post |
| Launch end to end | flow-launch |

## AI inside the product (`ai-`)

| Intent | Skill |
|--------|-------|
| Where would AI add value here; build or buy; is it feasible and affordable | ai-opportunity-assessment |
| Requirements for an AI feature: quality bar, fallbacks, cost ceiling | ai-feature-requirements |
| How the interface should handle uncertainty and feedback | ai-ux-patterns |
| Integrate a model: prompts, retrieval, tool use | ai-llm-integration |
| Evaluate the product's AI: datasets, graders, thresholds | ai-evals |
| Privacy, prompt injection, compliance for AI features | ai-governance |

## Workbench and methods (`core-`)

| Intent | Skill |
|--------|-------|
| Set up a project for the workbench: docs layout, state, autonomy, project instructions | core-project-init |
| Create or update the project's instruction file | core-agents-md |
| Interrogate me about a plan until we agree | core-clarify |
| Research a question with sources | core-research |
| Find what's wrong with this plan or artifact | core-critique |
| Create or improve a skill of the workbench | core-skill-creator |

## Cross-area

| Intent | Skill |
|--------|-------|
| Build a digital product from scratch, business through launch | flow-new-product |
| Where are we; what's next | read state, summarize, propose the next phase (no skill) |
