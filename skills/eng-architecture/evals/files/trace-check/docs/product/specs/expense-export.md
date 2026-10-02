# Feature specification: expense-export

- Owner: product-feature-spec
- Status: approved
- Date: 2026-04-14
- Feature of: Fennel Books, phase P-1, F-4 "Monthly export"
- Ready for architecture: yes

## Summary

A member downloads one month of expenses as a file and hands it to their accountant, who loads it
into the accounting import tool.

## Scope

- In: a download of the month selected on the Expenses page.
- Out: exports of more than one month; scheduled exports; any file format other than CSV.

## Sources

- docs/product/prd.md, F-4
- User answers, 2026-04-12 (columns, order, file format, size)

## Functional requirements

- REQ-1: The Expenses page has an "Export month" button that downloads a file with the expenses of the month selected on the page. Source: PRD F-4
- REQ-2: The file has one row per expense, in the columns date (YYYY-MM-DD), payee, category and amount (two decimals, a dot as the decimal separator), sorted by date, oldest first. Source: user, 2026-04-12
- REQ-3: The file is CSV: UTF-8, comma-separated, with a header row. The accountants' import tool accepts no other format, so the format is fixed by this requirement and is not a design choice; no alternative format is in scope. Source: user, 2026-04-12

## Non-functional requirements

- NFR-1: A month of 5,000 expenses downloads in under 3 seconds on the production server. Source: user, 2026-04-12

## Edge cases

- EDGE-1: The selected month has no expenses → the file is still downloaded, with the header row only.

## Acceptance criteria

- AC-1:
  Given a member on the Expenses page with March 2026 selected and 5,000 expenses in that month
  When they press "Export month"
  Then a file named expenses-2026-03.csv downloads in under 3 seconds
  Covers: REQ-1, REQ-3, NFR-1
- AC-2:
  Given three expenses in March 2026, entered out of order, one of them with the amount 12.5
  When the member exports March 2026
  Then the file has a header row and three rows sorted by date, oldest first, and that amount reads 12.50
  Covers: REQ-2
- AC-3:
  Given a month with no expenses
  When the member exports it
  Then the file has the header row and no other row
  Covers: EDGE-1

## Open questions

- none
