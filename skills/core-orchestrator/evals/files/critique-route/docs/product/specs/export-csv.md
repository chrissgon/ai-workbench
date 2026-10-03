# Feature specification: export-csv

- Owner: product-feature-spec
- Status: draft
- Date: 2027-10-12
- Feature of: Pennyfold PRD, F-4 "Take your expenses out"

## Goal

A member downloads one month of expenses as a CSV file that opens in a spreadsheet with every amount,
category and note intact, so that they can hand it to their accountant without copying rows by hand.

## Scope

- In: one month at a time, from the month page, as a CSV file.
- Out: several months in one file; any format other than CSV; scheduled exports.

## Functional requirements

- REQ-1: The month page shows an "Export CSV" control to the member who owns the expenses.
- REQ-2: The file is named `pennyfold-<YYYY-MM>.csv` and has one header row and one row per expense.
- REQ-3: The columns are `date`, `amount`, `currency`, `category`, `note`, in that order.
- REQ-4: The file is UTF-8, comma separated, with fields quoted when they contain a comma or a quote.
- REQ-5: The export is built in the browser from the expenses the month page already loaded.

## Acceptance criteria

- AC-1: A month with 3 expenses gives a file with 4 rows.
- AC-2: A note that contains a comma opens in one cell.
