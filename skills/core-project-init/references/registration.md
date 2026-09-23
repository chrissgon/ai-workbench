# Registration: which slot an existing document fills

Match the file's *content*, not only its name; open it when the name is ambiguous. One document may fill one slot; when it clearly covers two (an architecture file with a design-system section), register the dominant one and say so in the report. Slots are the paths in `contracts/project-layout.md`.

| Name pattern (case-insensitive) | Typical content | Slot |
|-------------------------------|-----------------|------|
| ARCHITECTURE, DESIGN (technical), SYSTEM-DESIGN | components, contracts, principles, hard rules | docs/engineering/architecture.md |
| ADR, DECISIONS | dated technical decisions | docs/engineering/adr/ (register the folder) |
| DESIGN-SYSTEM, TOKENS, THEME | tokens, components, states | docs/design/design-system.md |
| INTERFACE, SCREENS, UI | screen-by-screen specification | docs/design/screens/ (register the file as the folder's index) |
| JOURNEY, FLOWS, UX | user paths, steps, states | docs/design/flows.md |
| HANDOFF | current status and next steps for whoever continues | docs/engineering/plans/handoff.md |
| MIGRATION | how to move from one version to another | docs/engineering/plans/migration.md |
| PRD, REQUIREMENTS, SPEC (product-level) | requirements, scope, acceptance | docs/product/prd.md |
| ROADMAP | ordered priorities | docs/product/roadmap.md |
| BRAND, VOICE, STYLE-GUIDE (writing) | brand strategy, identity, voice | docs/brand/guidelines.md |
| BUSINESS, BUSINESS-PLAN, PITCH | market, model, plan | docs/business/business-plan.md |
| MARKETING, LAUNCH | messaging, plan | docs/marketing/launch-plan.md |

Never registered: README, LICENSE, CHANGELOG, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, AGENTS, and any file that is instructions for a specific AI tool. Never registered by default: anything under `docs/` that reads as end-user documentation.
