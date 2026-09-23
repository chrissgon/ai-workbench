# Artifact contract: `docs/workbench/state.md`

The state file is what lets a flow resume in a new session and lets the orchestrator know where a project stands. Every flow reads it first and updates it at every checkpoint. Capabilities update only the row of the artifact they own.

Keep it small. It is a table of contents with status, not a journal.

## Template

```markdown
# Workbench state

- Project: <name>
- Current flow: <flow-name or none>
- Current phase: <phase name or none>
- Updated: <YYYY-MM-DD>

## Artifacts

| Artifact | Owner skill | Status | Updated |
|----------|-------------|--------|---------|
| docs/business/idea-validation.md | biz-validate-idea | approved | 2026-09-22 |
| docs/business/business-model.md | biz-business-model | draft | 2026-09-22 |

## Decisions

- 2026-09-22: No brand phase; internal tool. (user)
- 2026-09-22: Pricing is usage-based; see docs/business/pricing.md. (biz-pricing, approved by user)

## Open questions

- [ ] Who owns customer support after launch? (raised by flow-new-product, phase Delivery)
```

## Rules

- `Status` is `draft`, `approved` or `skipped`. Only the user approves. A skill sets `draft`; a checkpoint sets `approved` or `skipped`.
- A flow resumes from the first phase whose artifacts are not `approved` or `skipped`.
- Decisions record what was decided, by whom, and where the reasoning lives. One line each.
- Open questions are checkboxes; a flow surfaces unchecked ones at every checkpoint.
- Never store secrets, tokens or personal data here.
