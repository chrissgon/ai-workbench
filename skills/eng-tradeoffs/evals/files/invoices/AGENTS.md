# invoices

A tiny invoice helper used by a web shop in Brazil and Portugal.

- Test: `npm test` (node --test). CI runs in UTC.
- Size: `npm run size` prints the gzip size of `src/`; the budget is 1,024 B.
- Supported runtimes: Node 20 and 22; the shop's servers run in the America/Sao_Paulo and Europe/Lisbon time zones.

## Rules (never break)

1. Zero runtime dependencies: only Node's standard library and the platform's `Intl`.
2. Every exported function is documented in README.md.
3. The public API is `src/index.js`; nothing else is imported by consumers.

## Consumers

- The shop's checkout (`shop-web`, another repository) imports `dueLabel` from `invoices` and prints it on the PDF.
