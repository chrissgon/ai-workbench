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
