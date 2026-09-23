# Success metrics for a PRD

Loaded at step 6 of `product-prd`. The purpose is to stop invented numbers, not to teach analytics.

## What a metric needs

| Field | Rule |
|-------|------|
| Metric | one observable quantity, named so two people would count it the same way (visitors who open a second page, not "engagement") |
| Target | a number with a unit; `by when` only when a source gives the date |
| Baseline | today's value from an instrument or a document, or `none` when the product or the instrument does not exist yet |
| Measured by | the instrument that will produce the number (analytics event, build report, registry statistics, survey, support inbox); if none exists, say which one must be added and by which feature |
| Source | who set the target: the brief, a decision, a research citation or the user |

## Where numbers may come from

- The user, asked with a recommended target and the reason for it.
- A research brief that measured something (adoption counts, sizes, timings) with a citation.
- The current product's instruments (analytics, build output, registry downloads) for baselines.
- Never another product's benchmark, a "typical" industry figure, or the round number that sounds right.

## Picking metrics for a goal

1. Restate the goal as something a user does or stops doing.
2. Write the lagging metric that proves it (the outcome) and one leading metric that moves earlier (the behaviour that precedes the outcome).
3. Check each against the table; a metric that fails a row is `OPEN-n` with a recommended target, not a metric.
4. Prefer at least one metric per user group named in the PRD; a group without a metric is a group nobody will check on.

## Common substitutes to reject

- Output counts as outcomes ("32 pages migrated"): that is a phase exit criterion, not a success metric.
- Vanity totals without a comparison ("10,000 visits"): pair every total with a baseline or a rate.
- Satisfaction without an instrument ("users are happy"): name the survey or the channel and the question.
