# Design brief: {SCREEN-n name}, for an external design tool

- Owner: design-ui
- Status: draft
- Date: {YYYY-MM-DD}
- Screen: docs/design/screens/{screen}.md ({SCREEN-n})
- Tool: {tool for the first round}; the brief is written for any AI design tool
- Self-contained: the tool reads nothing but this document{ and the design file, when it can}

## Summary

{two sentences: what to explore, at which widths and modes, and what is fixed versus open}

## Sources

- {messaging, design system, flows, screen document, specs, user review that triggered the exploration}

## Product

{what the product is in two paragraphs a stranger can act on, with one real code sample}

## Audience and voice

- {who reads the page, one line per audience}
- Voice: {rules}
- Words to use: {list}
- Words to avoid: {list}

## Creative direction

{what the previous version got wrong, in one paragraph}

{what to take from the references, as attitudes, never as layouts or copy}

- Direction A, "{name}": {the idea in two sentences}
- Direction B, "{name}": {…}
- Direction C, "{name}": {…}

{identity hooks to keep; what is allowed and what is not}

## Visual language

{colour table with light and dark values; type table with sizes; space, radii, borders, elevation, focus, motion, breakpoints; every value written out, because the tool cannot read the design system}

## Components

{real markup of the components the demos use; the site-only elements described with their fixed contents}

## Page structure

- SECTION-1 {name}. Headline: {verbatim}. Body: {verbatim}. Demo: {what happens}. Call to action: {label}.
- {…}

## Constraints

- {values only from Visual language; demos real; copy verbatim; contrast; targets; focus; narrow first viewport; motion and reduced motion; no-JavaScript state; fixed shell; buildability and budget}

## Deliverables

- Round 1: {what the tool returns first, at which width and mode}
- Round 2: {the full set after a direction is chosen}

## Evaluation criteria

- CRIT-1: {criterion a reviewer can check on a screen}
- {at least five}

## How to run

1. {where to start the tool and what to attach}
2. {what to paste}
3. {how the results come back for critique}
4. {what happens after the choice}

## Prompt

```text
{the short prompt to paste, under 25 lines, ending with "The brief follows."}
```

## Open questions

- OPEN-1: {question}. Blocks: {…}. Recommended: {answer and why}

## Readiness

- Ready for round 1 in the external tool: {yes | no, because …}
