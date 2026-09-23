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
    ├── brand/                    # strategy.md, identity.md, voice.md, guidelines.md
    ├── design/                   # research.md, flows.md, wireframes/, design-system.md, handoff/
    ├── engineering/              # architecture.md (or codebase-map.md beside a registered spec), adr/NNNN-title.md, plans/<task>.md
    ├── ai/                       # opportunity.md, requirements.md, evals/, governance.md
    ├── delivery/                 # runbooks/, releases/, incidents/
    └── marketing/                # messaging.md, launch-plan.md, calendar.md, content/, campaigns/
```

## Rules

- One artifact per capability, with a fixed name. A skill's `metadata.outputs` lists exactly the paths it writes.
- A skill reads its `metadata.inputs` if they exist. If an input is missing, it says so and either asks the user for the information or offers to run the skill that produces it. It never silently invents the content of a missing input.
- Artifacts are Markdown unless the content is inherently structured (design tokens, eval datasets), in which case JSON or YAML sits next to a Markdown summary.
- Every artifact starts with a short header: purpose, owning skill, date, status (`draft` | `approved`). Status is mirrored in `docs/workbench/state.md`.
- Day-to-day engineering tasks (implementing a ticket, fixing a bug) do not create artifacts under `docs/` except a temporary plan in `docs/engineering/plans/`, removed or archived when the task ships.
- Artifact templates live in `contracts/templates/<name>.md` and are copied by the skill that owns the artifact.

## Existing projects

A project that already keeps specifications elsewhere (`ARCHITECTURE.md` at the root, a `specs/` folder) does not move them. `core-project-init` registers each one in `docs/workbench/state.md` as the slot it fills, with its real path and owner `existing`. A skill whose `inputs` list that slot reads the registered path. Only new artifacts follow the layout above. End-user documentation under `docs/` (a documentation site) is product content, never a workbench artifact.
