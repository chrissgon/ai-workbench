# Plan: due-label-customer-time-zone

- Task: "The due date must print in the customer's time zone, not the server's" (checkout team)
- Date: 2026-09-25

## Change

- Owner: eng-implement
- `src/due.js`: `dueLabel(isoDate, timeZone = "UTC")` formats the date with `Intl.DateTimeFormat` in `timeZone`; the result no longer depends on the server's zone. `npm test` passes.

## Root cause (summary)

- Evidence: confirmed. The label depended on the server's zone: `new Date(isoDate)` read the date as UTC and `toLocaleDateString` formatted it in the server's zone.

### What a fix must preserve
- `dueLabel("2026-09-25")` is `"2026-09-25"` whatever the server's TZ (UTC, Europe/Lisbon, America/Sao_Paulo).
- `dueLabel("2026-09-25", "Asia/Tokyo")` is `"2026-09-25"`.
- The public API is `src/index.js`; `daysLeft` keeps its meaning.
