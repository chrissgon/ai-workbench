# Plan: due-label-customer-time-zone

- Task: "The due date must print in the customer's time zone, not the server's" (checkout team)
- Date: 2026-09-25

## Root cause

- Owner: eng-root-cause
- Evidence: confirmed
- Cause: src/due.js:3 `new Date(isoDate)` reads a date-only string as UTC and `toLocaleDateString` formats it in the server's zone; the server's zone decides the printed day.

### What a fix must preserve
- dueLabel("2026-09-25") prints "2026-09-25" for a customer in America/Sao_Paulo, Europe/Lisbon and Asia/Tokyo, whatever the server's TZ.
- The signature stays compatible: dueLabel(isoDate) without a zone keeps working.
- daysLeft keeps its meaning (whole days, rounded up).

## Impact

- Owner: eng-impact-analysis
- Baseline measured: `npm run size` on 2026-09-25: src/ 307 B gzip (budget 1,024 B)
- Rules: AGENTS.md rule 1 "Zero runtime dependencies: only Node's standard library and the platform's `Intl`" (a package breaks it: user decision); rule 2 every export documented in README.md; rule 3 public API through src/index.js.
- Tests that encode today's behaviour: test/due.test.js "the label is the due date" (passes only where the server runs in UTC or ahead of it).
- Dependants: shop-web imports dueLabel and prints it on the PDF.
