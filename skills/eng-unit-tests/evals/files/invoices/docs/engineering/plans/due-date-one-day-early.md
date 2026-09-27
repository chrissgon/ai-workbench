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
src/due.js:3 `const date = new Date(isoDate);`
The line assumes the string is read as a local date. ECMAScript reads a date-only ISO string as UTC ("When the UTC offset representation is absent, date-only forms are interpreted as a UTC time and date-time forms are interpreted as a local time", ECMA-262, Date Time String Format), and toLocaleDateString formats in local time, so a zone behind UTC shows the previous day.

### Reach
- Triggers: every date-only string in a zone behind UTC.
- Same assumption elsewhere: src/due.js:9 `daysLeft` parses the same way.

### Why it escaped
- CI runs in UTC, where test/due.test.js passes.

### What a fix must preserve
- dueLabel("2026-09-25") is "2026-09-25" in UTC, Europe/Lisbon and America/Sao_Paulo.
- dueLabel of a date-time string without an offset keeps its local date.
- daysLeft("2026-09-25", now) is 1 when now is 2026-09-24 at 12:00 local time, in each of the three zones.
