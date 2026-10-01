# Design system: {product}

- Owner: design-system
- Status: draft
- Date: {YYYY-MM-DD}
- Flows: docs/design/flows.md

## Summary

{two sentences: what governs the values, how many tokens and components}

## Sources

- {library token file, brand artifact, decision id, user answer date}

## Ownership

- {group}: {library name and file | this document}. {rule}

## Colour

| Token | Light | Dark | Role | Source |
|-------|-------|------|------|--------|
| `{--prefix-name, the library's own property name}` | {#RRGGBB} | {#RRGGBB or same} | {role} | {library file and section, brand artifact, or user answer date} |

## Contrast

Ratios come from `scripts/contrast.py`, never from memory.

| Text token | On background | Light ratio | Dark ratio | AA |
|------------|---------------|-------------|------------|----|
| `{text token}` | `{background token}` | {n.nn}:1 | {n.nn}:1 | {pass or fail} (needs {4.5 or 3}:1); used on {SCREEN-n region} |

## Type

- Typeface: {family}, fallback {stack}. Source: {brand artifact | user answer date} | Unknown, ask the user (OPEN-n). Recommended: {answer and why}
- Reading width: {value}. Source: {…}

| Role | Size | Line height | Weight | Source |
|------|------|-------------|--------|--------|
| {display, h1, h2, h3, body, small, code} | {px or rem} | {ratio} | {number} | {library base and stated ratio | brand artifact | user answer date} |

## Space, radii, borders, elevation

| Token | Value | Role | Source |
|-------|-------|------|--------|

## Layout

| Token | Value | Role | Source |
|-------|-------|------|--------|

## Components

| Component | Owner | Variants | States | Screens | Source |
|-----------|-------|----------|--------|---------|--------|
| {name} | {library or site} | {axes and values} | {default, hover, focus-visible, …} | {SCREEN-n, SCREEN-m: the ids from the flows} | {library file and section | flows SCREEN-n region} |

## Design tool

- File: {name and key | none available}
- Collections: {…}
- Styles: {…}
- Components: {…}
- Validation: {what was checked, screenshots taken}

## Assumptions

- ASSUMPTION-1: {statement}. Safe because: {reason}

## Open questions

- OPEN-1: {question}. Blocks: {…}. Recommended: {answer and why}

## Readiness

- Ready for design-brief: {yes | no, because …}
