# Plan: due-label-customer-time-zone

- Task: "The due date must print in the customer's time zone, not the server's" (checkout team)
- Date: 2026-09-25

## Change

- Owner: eng-implement
- `src/due.js`: `dueLabel(isoDate, timeZone = "UTC")` formats the date with `Intl.DateTimeFormat` in `timeZone`; the result no longer depends on the server's zone. `npm test` passes.
