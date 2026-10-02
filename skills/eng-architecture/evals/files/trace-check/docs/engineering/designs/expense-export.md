# Design: expense-export

- Owner: eng-architecture
- Status: draft
- Date: 2026-04-16
- Specification: docs/product/specs/expense-export.md
- Frameworks and versions relied on: none beyond the existing server (see Sources)

## Summary

The Expenses page gets an "Export month" button. It requests a new export route with the selected
month; the route reads that month's expenses from the existing expense store and answers with a
file download. Nothing is stored: the file is built on each request.

## Sources

- docs/product/specs/expense-export.md
- src/pages/expenses.tsx, src/server/routes/index.ts, src/server/store/expenses.ts (files read, 2026-04-16)

## Decisions

| # | Decision | Chosen | Class | ADR or source |
|---|----------|--------|-------|---------------|
| 1 | File format of the export | CSV | engineering | ADR-0001 |
| 2 | Where the file is built | On the server, on each request; nothing stored | decided | spec Summary ("downloads", no scheduled exports in Scope) |

## Components

| Component | Responsibility | Location | Inputs | Outputs | Satisfies |
|-----------|----------------|----------|--------|---------|-----------|
| ExportButton | Requests the export of the month selected on the page | src/pages/expenses.tsx | selected month | a request to the export route | REQ-1 |
| ExportRoute | Reads the month's expenses and answers with the file as a download | src/server/routes/export.ts | month (YYYY-MM) | a CSV response | REQ-1, REQ-3, NFR-1, EDGE-1 |

## Data or content model

No new entity. The route reads the existing `expenses` table (date, payee, category, amount_cents)
through `src/server/store/expenses.ts`, filtered by month.

## Contracts

### Routes
| Route | Params | Resolves to | Serves |
|-------|--------|-------------|--------|
| GET /expenses/export | month=YYYY-MM | 200, `text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="expenses-YYYY-MM.csv"` | REQ-1, REQ-3 |

### Component interfaces
| Component | Props / inputs | Slots / events | Serves |
|-----------|----------------|----------------|--------|
| ExportButton | month: string (YYYY-MM) | click → navigates to the export route | REQ-1 |

## Flows

### Export
1. ExportButton — sends the selected month to the export route.
2. ExportRoute — reads the month's expenses in one query and streams the response (NFR-1).

### Failure paths
| EDGE | Where it is caught | What happens | Message names |
|------|--------------------|--------------|---------------|
| EDGE-1 | ExportRoute | The query returns no row; the response carries the header row only | none (not an error) |

## Verification plan

| AC | Check | Type | Command or location |
|----|-------|------|---------------------|
| AC-1 | Export a seeded month of 5,000 expenses; assert the file name, the content type and a response under 3 seconds | integration | test/export.route.test.ts |
| AC-3 | Export a month with no expenses; assert the body is the header row only | integration | test/export.route.test.ts |

## Traceability

| Id | Where in this design |
|----|----------------------|
| REQ-1 | Components (ExportButton, ExportRoute), Contracts |
| REQ-3 | Components (ExportRoute), Contracts, Decisions 1 |
| NFR-1 | Components (ExportRoute), Flows |
| EDGE-1 | Failure paths |
| AC-1 | Verification plan |
| AC-3 | Verification plan |

## Assumptions to verify before implementation

- none

## Open questions

- none
