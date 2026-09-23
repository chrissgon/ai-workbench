# money-cli

Command-line tool that totals accounting statements.

## Commands

- Test: `python3 -m unittest discover -s tests -t . -q`
- Lint: none configured
- Type-check: none configured

## Conventions

- Parsing lives in `src/money.py`; `src/report.py` formats and totals and never parses strings itself.
- Every bug fix adds a regression test in `tests/` that fails without the fix.
- Credentials come from environment variables (`PAYMENTS_API_KEY`); never in source, tests or fixtures.
- Do not print from library code; the CLI entry point is the only place that writes to stdout.
