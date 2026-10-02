# Brief: ledger

- Owner: core-clarify
- Status: approved
- Date: 2026-09-19

## Goal
Freelancers see what they are owed and get every invoice paid within its term.

## Scope
- In: invoices and reminders
- Out: accounting exports

## Constraints
- technical: web only (decision 3)

## Decisions
| # | Decision | Chosen | Why | By |
|---|----------|--------|-----|----|
| 1 | What the first release covers | invoices and reminders | the problem is unpaid invoices | user |
| 2 | Accounting exports | out | freelancers already use an accountant | user |
| 3 | Platforms | web only | one platform to start | user |
| 4 | Client payments | a client portal, after the first release | the reminder comes first | user |

## Facts established without asking
- The users are freelance designers who bill 3 to 8 clients a month (source: the user's request)
- A reminder must arrive within 1 day of an invoice becoming overdue (source: the user's request)

## Open questions
- [ ] Which email provider sends the reminders? (blocks: the reminders; recommended: the one already used for transactional mail, not adopted)

## Contradictions surfaced
- none
