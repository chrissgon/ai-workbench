# Plan: T-ap-3 negative amounts in parentheses

- Owner: eng-root-cause
- Status: approved
- Date: 2026-09-22

## Bug

`parse_amount("(12.50)")` returns `12.5`; statements with refunds total too high (BUG-7).

## Root cause

`src/money.py`, `parse_amount`: the parentheses are stripped (`strip("()")`) before the sign test
(`startswith("(")`), so the test never sees them and the sign is never applied. The cause is in
`parse_amount` itself; every caller receives a wrong value.

## Failing test

`tests/test_money.py::ParseAmountTests::test_parentheses_negative` (written before the fix; fails
with `12.5 != -12.5`).

## Reproduction

`python3 -c "import sys; sys.path.insert(0, 'src'); from money import parse_amount; print(parse_amount('(12.50)'))"` prints `12.5`.
