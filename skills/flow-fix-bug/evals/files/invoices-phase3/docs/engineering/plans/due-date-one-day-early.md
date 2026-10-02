# Plan: due-date-one-day-early

- Task: "Customers in Brazil see the due date one day early"
- Date: 2026-09-25

## Root cause

- Owner: eng-root-cause
- Evidence: confirmed

### Report
Seen: an invoice due 2026-09-25 prints 2026-09-24 for customers in Brazil. Expected: 2026-09-25 everywhere. Reported by: support.

### Reproduction
`scripts/repro-due.mjs` — run with `TZ=America/Sao_Paulo node scripts/repro-due.mjs` and `TZ=UTC node scripts/repro-due.mjs`.
| Case | TZ=UTC | TZ=Europe/Lisbon | TZ=America/Sao_Paulo |
|------|--------|------------------|----------------------|
| dueLabel("2026-09-25") | 2026-09-25 | 2026-09-25 | 2026-09-24 |
| dueLabel("2026-09-25T00:00") | 2026-09-25 | 2026-09-25 | 2026-09-25 |

### Cause
src/due.js:3 `return new Date(isoDate);`, inside `toDate`.
The line assumes the string is read as a local date. ECMAScript reads a date-only ISO string as UTC ("When the UTC offset representation is absent, date-only forms are interpreted as a UTC time and date-time forms are interpreted as a local time", ECMA-262, Date Time String Format), and toLocaleDateString formats in local time, so a zone behind UTC shows the previous day.

### Reach
- Triggers: every date-only string in a zone behind UTC.
- Same assumption elsewhere: none. `toDate` is the only place that parses a date; it is private to src/due.js (not exported), and its two callers, `dueLabel` and `daysLeft`, are in the same file. No other file of the project imports src/due.js except test/due.test.js and scripts/repro-due.mjs.
- Public surface: the exported names and signatures of `dueLabel` and `daysLeft` do not need to change.

### Why it escaped
- CI runs in UTC, where test/due.test.js passed.

### What a fix must preserve
- dueLabel("2026-09-25") is "2026-09-25" in UTC, Europe/Lisbon and America/Sao_Paulo.
- dueLabel of a date-time string without an offset keeps its local date.
- daysLeft("2026-09-25", now) is 1 when now is 2026-09-24 at 12:00 local time, in each of the three zones.

## Failing tests

- Owner: eng-unit-tests
- Command: `npm test`
- Files: `test/due.test.js`

| Test | Source | Expected before the change | Observed before (per runtime) |
|------|--------|----------------------------|-------------------------------|
| dueLabel keeps a date-only due date in America/Sao_Paulo | Root cause › What a fix must preserve, 1 | fails now | Node 24: actual '2026-09-24', expected '2026-09-25' |
| dueLabel keeps a date-only due date in UTC, in Europe/Lisbon | Root cause › What a fix must preserve, 1 | passes now | passes in every runtime |
| dueLabel keeps the local date of a date-time in each zone | Root cause › What a fix must preserve, 2 | passes now | passes in every runtime |
| daysLeft is 1 at noon the day before in each zone | Root cause › What a fix must preserve, 3 | passes now | passes in every runtime |

- Result before the change: 1 failed, 8 passed (the failure is exactly the `fails now` row)
- Not run: none
- Pending decisions: none
