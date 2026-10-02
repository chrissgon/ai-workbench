# ADR-0001: Export file format

- Status: proposed
- Date: 2026-04-16
- Serves: REQ-3

## Context

The export is loaded by the accountants' import tool. REQ-3 of docs/product/specs/expense-export.md
fixes the file format: CSV, UTF-8, comma-separated, with a header row. The import tool accepts no
other format, so no alternative was considered.

## Options

### Option A: CSV
- Consequences: the import tool reads the file as it is; no library is needed to write it.

## Decision

Option A, CSV, as REQ-3 requires.

## Consequences

- The export route answers with `text/csv`.
