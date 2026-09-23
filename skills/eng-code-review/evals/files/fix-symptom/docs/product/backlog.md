# Backlog: accounting parser (`T-ap`)

- Owner: product-backlog
- Status: approved
- Date: 2026-09-20

## Tasks

- T-ap-3: fix negative amounts written with parentheses
  Does: makes parse_amount return a negative value for "(12.50)" and keeps every other input unchanged
  Delivers: BUG-7
  Touches: src/money.py, tests/test_money.py
  Depends on: none
  Check: python3 -m unittest tests.test_money -q
  Size: S, because one function
  Milestone: M1
  Status: done (2026-09-23) unittest 3 passed, 1 skipped
