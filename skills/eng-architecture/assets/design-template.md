# Design: {feature}

- Owner: eng-architecture
- Status: draft
- Date: {YYYY-MM-DD}
- Specification: docs/product/specs/{feature}.md
- Frameworks and versions relied on: {name version (docs URL, accessed date)}

## Summary

{five to eight lines: what is built, from what parts, how a change flows from a file edit to the published site or the running system}

## Sources

- {specification, codebase map, decisions, framework documentation pages with URLs and access dates, files read}

## Decisions

| # | Decision | Chosen | Class | ADR or source |
|---|----------|--------|-------|---------------|
| 1 | ... | ... | decided \| engineering \| user | ADR-NNNN \| brief decision n \| user answer date |

## Components

| Component | Responsibility | Location | Inputs | Outputs | Satisfies |
|-----------|----------------|----------|--------|---------|-----------|
| ... | one sentence | folder or file | ... | ... | REQ-n, NFR-n |

## Data or content model

{schemas, folders, files, with validation rules and the EDGE they come from; show the framework's own form and cite the API}

## Contracts

### Routes
| Route | Params | Resolves to | Serves |
|-------|--------|-------------|--------|

### Files and generated artifacts
| Path | Produced by | Shape (example) | Consumed by | Serves |
|------|-------------|-----------------|-------------|--------|

### Component interfaces
| Component | Props / inputs | Slots / events | Serves |
|-----------|----------------|----------------|--------|

## Flows

### Build
1. {component} — {what happens}
### {Runtime flow}
1. ...
### Failure paths
| EDGE | Where it is caught | What happens | Message names |
|------|--------------------|--------------|---------------|

## Removals

| Removed | Replaced by | Must keep working | Checked by |
|---------|-------------|-------------------|------------|

## Verification plan

| AC | Check | Type | Command or location |
|----|-------|------|---------------------|

## Traceability

| Id | Where in this design |
|----|----------------------|

## Assumptions to verify before implementation

- {API or behaviour not cited, and how to verify it}

## Open questions

- {only items the user must answer, with the component they block and a recommendation}
