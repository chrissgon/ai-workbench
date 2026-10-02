# Artifact contract: layout of a target project

Skills never keep state inside this repository. Everything they produce for a project lives in that project, under `docs/`, so that later phases, other skills and other people can find it.

```
<target-project>/
├── AGENTS.md                     # project conventions; created and maintained by core-agents-md
└── docs/
    ├── workbench/
    │   ├── state.md              # phase, artifact status, decisions, open questions (schema: state.md)
    │   ├── briefs/<topic>.md     # shared-understanding briefs written by core-clarify
    │   ├── critiques/<topic>.md  # adversarial reviews written by core-critique
    │   └── research/<topic>.md   # sourced research briefs written by core-research
    ├── business/                 # idea-validation.md, market.md, icp.md, positioning.md, business-model.md, pricing.md, gtm.md, business-plan.md
    ├── product/                  # discovery.md, prd.md, specs/<feature>.md, roadmap.md, backlog.md, metrics.md
    ├── brand/                    # profile.md, name.md, strategy.md, identity.md, voice.md, guidelines.md
    ├── design/                   # research.md, flows.md (with flows.lint.json), wireframes/, design-system.md, briefs/<artifact>.md (with <artifact>.lint.json), results/<artifact>.md, handoff/<screen>.md (with <screen>.lint.json)
    ├── engineering/              # architecture.md (or codebase-map.md beside a registered spec), designs/<feature>.md, adr/NNNN-title.md, designs/<feature>.check.json, plans/<task>.md, reviews/<change>.md, security-reviews/<date>.md
    ├── ai/                       # opportunity.md, requirements.md, evals/, governance.md
    ├── delivery/                 # repo-baseline.md, runbooks/, releases/, incidents/
    └── marketing/                # messaging.md, launch-plan.md, calendar.md, content/<post>.md, campaigns/, engagement-policy.md, engagement-inbox.md, engagement-log.jsonl
```

The tree names every slot, built or planned. The paths below are written by skills that exist today and were missing from the tree until 2026-10-02; each is listed with the skill that owns it.

| Area | Path | Owning skill |
|------|------|--------------|
| brand | `docs/brand/profile.md` | brand-profile |
| brand | `docs/brand/name.md` | brand-name |
| design | `docs/design/flows.lint.json` | design-ux-flows |
| design | `docs/design/briefs/<artifact>.md`, `docs/design/briefs/<artifact>.lint.json` | design-brief |
| design | `docs/design/results/<artifact>.md` | design-execute |
| design | `docs/design/handoff/<screen>.md`, `docs/design/handoff/<screen>.lint.json` | design-handoff |
| engineering | `docs/engineering/designs/<feature>.check.json` | eng-architecture |
| engineering | `docs/engineering/security-reviews/<date>.md` | eng-security-review |
| delivery | `docs/delivery/repo-baseline.md` | ops-repo-baseline |
| marketing | `docs/marketing/content/<post>.md` | mkt-social-copy, mkt-vote-round |
| marketing | `docs/marketing/engagement-policy.md`, `docs/marketing/engagement-inbox.md`, `docs/marketing/engagement-log.jsonl` | mkt-engage |

## Rules

- One artifact per capability, with a fixed name. A skill's `metadata.outputs` lists exactly the paths it writes.
- A skill reads its `metadata.inputs` if they exist. If an input is missing, it says so and either asks the user for the information or names the skill that produces it, for the user to run. It never silently invents the content of a missing input.
- Artifacts are Markdown unless the content is inherently structured (design tokens, eval datasets), in which case JSON or YAML sits next to a Markdown summary.
- Every artifact starts with a short header: purpose, owning skill, date, status (`draft` | `approved`). Status is mirrored in `docs/workbench/state.md`.
- Day-to-day engineering tasks (implementing a ticket, fixing a bug) do not create artifacts under `docs/` except a temporary plan in `docs/engineering/plans/` and a review in `docs/engineering/reviews/`, both removed or archived when the task ships.
- An artifact's template lives with the skill that owns the artifact: in the skill's `assets/` folder, or inline in its `SKILL.md` when it is short. `contracts/templates/` holds only a README.

## Existing projects

A project that already keeps specifications elsewhere (`ARCHITECTURE.md` at the root, a `specs/` folder) does not move them. `core-project-init` registers each one in `docs/workbench/state.md` as the slot it fills, with its real path and owner `existing`. A skill whose `inputs` list that slot reads the registered path. Only new artifacts follow the layout above. End-user documentation under `docs/` (a documentation site) is product content, never a workbench artifact.
