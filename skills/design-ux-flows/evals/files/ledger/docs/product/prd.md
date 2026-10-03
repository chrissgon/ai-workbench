# PRD: Ledger

- Owner: product-prd
- Status: draft
- Date: 2026-09-23
- Brief: docs/workbench/briefs/ledger.md

## Summary

A personal finance app for freelancers.

## Problem and goal

- Problem: freelancers lose track of invoices. Source: brief
- Goal: every invoice is paid within its term. Source: brief

## Users

- U-1: Freelance designers. Situation: bill 3 to 8 clients a month. Needs: know what is overdue. Source: brief, facts established without asking

## Scope

- In: invoices and reminders. Source: brief decision 1
- Out: accounting exports. Source: brief decision 2

## Sources

- docs/workbench/briefs/ledger.md

## Features

- F-1: Invoice list. Outcome: the freelancer can see every invoice with its status. Priority: must. Phase: P-1. Source: brief decision 1
- F-2: Overdue reminders. Outcome: the freelancer gets a reminder within 1 day of an invoice becoming overdue. Priority: must. Phase: P-1. Source: brief decision 1
- F-3: Client portal. Outcome: the client can pay online. Priority: later. Phase: P-2. Source: brief decision 4

## Success metrics

- M-1: Invoices paid on time. Target: 80% of invoices paid within their term. Baseline: none. Measured by: invoice status at term end. Source: user answer 2026-09-20
- M-2: Weekly active freelancers. Target: 1,000. Baseline: none. Measured by: analytics event app_open. Source: user answer 2026-09-20

## Constraints

- technical: web only. Source: brief decision 3

## Dependencies and risks

- R-1: Email provider outage. Trigger: provider returns errors for more than 1 hour. Impact: reminders not sent. Mitigation: queue and retry for 24 hours.

## Release phases

- P-1: Core. Includes: F-1, F-2. Exit: a freelancer can list invoices and receives reminders. Source: brief
- P-2: Payments. Includes: F-3. Exit: clients pay online. Source: brief

## Assumptions

- ASSUMPTION-1: Freelancers invoice in one currency. Safe because: the brief mentions Brazil only.

## Open questions

- OPEN-1: Which email provider? Blocks: F-2. Recommended: the one already used for transactional mail, because credentials exist.

## Readiness

- Ready for feature specs: no, because OPEN-1 blocks F-2
