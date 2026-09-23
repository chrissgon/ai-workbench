# Backlog: accounting parser (`T-ap`)

- Owner: product-backlog
- Status: approved
- Date: 2026-09-20

## Tasks

- T-ap-5: send account totals to the payment provider
  Does: posts each account's total to the payment provider's totals endpoint with the account id and the amount in cents
  Delivers: REQ-4
  Touches: src/client.py, tests/test_client.py
  Depends on: none
  Check: python3 -m unittest tests.test_client -q
  Size: S, because one module
  Milestone: M2
  Status: done (2026-09-23) unittest 2 passed
