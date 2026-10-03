# Feature specification: invoice-list

- Owner: product-feature-spec
- Status: approved
- Date: 2026-09-25
- Feature of: docs/product/prd.md, F-1, phase P-1

## Summary

The freelancer sees every invoice with its status in one list.

## Goal and users

- Problem: freelancers lose track of invoices. Source: docs/product/prd.md, Problem and goal
- Users: freelance designers (U-1). Source: docs/product/prd.md, U-1
- Success: every invoice the freelancer created appears in the list with its current status.

## Scope

- In: the list of invoices, the status of each invoice.
- Out: payments by clients (F-3). Source: docs/product/prd.md, F-3

## Sources

- docs/product/prd.md (F-1, F-2, U-1)

## Functional requirements

- REQ-1: The list shows every invoice with its client, amount, due date and status. Source: docs/product/prd.md F-1
- REQ-2: The status of an invoice is one of draft, sent, overdue or paid, computed in one place from its due date and payments; the overdue reminders of F-2 read this same status. Source: docs/product/prd.md F-1, F-2

## Non-functional requirements

- NFR-1: The list of 500 invoices renders in under 1 second. Source: user answer 2026-09-25

## Constraints

- technical: web only. Source: docs/product/prd.md, Constraints

## Edge cases

- EDGE-1: An invoice whose due date is today → its status is sent, not overdue, until the day ends.
- Categories skipped: permissions, because each freelancer sees only their own invoices.

## Acceptance criteria

- AC-1:
  Given three invoices, one draft, one sent and one paid
  When the freelancer opens the list
  Then the list shows the three invoices with those statuses
  Covers: REQ-1, REQ-2
- AC-2:
  Given 500 invoices
  When the freelancer opens the list
  Then the list renders in under 1 second
  Covers: NFR-1

## Assumptions

- none

## Open questions

- none

## Readiness

- Ready for architecture: yes
