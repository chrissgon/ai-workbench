# Ideal customer profile: process automation with AI

- Owner: biz-icp-positioning
- Status: hypothesis
- Date: 2026-09-24
- Offer: process automation with AI; size band: micro and small companies with staff; founder access: no experience or contacts in any segment

## Comparison
| Rank | Option | pain | base | ability to pay | incumbents | reach | regulation | Total |
|---|---|---|---|---|---|---|---|---|
| 1 | Law firms | 4 [1] | 3 [2] | 4 [1] | 3 [3] | 3 [2] | 2 [4] | 19 |
| 2 | Real estate agencies | 3 [5] | 3 [5] | 3 [5] | 2 [5] | 3 [5] | 4 [5] | 18 |
| 3 | Physiotherapy clinics | 3 [6] | 2 [6] | 2 [6] | 2 [6] | 2 [6] | 3 [6] | 14 |
- Reading: law firms and real estate agencies are within 2 points; law firms were chosen by the user on 2026-09-24.

## Primary profile
- Segment and size: law firms with 2 to 9 staff, about 4,200 in Portugal [2]
- Job to be done: open: 1. answering routine client questions about case status [1]; 2. preparing standard documents [1]; to test in interviews
- Pain and evidence: lawyers report 6 hours a week on client status questions [1]
- Today they use: practice management software with a client portal, EUR 39 per user per month [3]
- Decider: the managing partner [1]
- Triggers: a new court filing system from 2028-01 [4]
- Where to find them: the bar association's public directory, regional chapter events [2]
- Rules that shape the offer: the bar's advertising rules forbid comparative claims and promised results [4]

## Secondary profile
- Real estate agencies with 2 to 9 staff; pain: repeated viewing requests [5]

## Who not to sell to
- Sole practitioners: outside the size band [2]

## Validation plan
- Interviews: 5 with managing partners of law firms with 2 to 9 staff, found through the bar's public directory
- Questions (past behaviour only): 1. Which tasks took the most hours last week? 2. When did a client last ask for the status of a case, and how did you answer? 3. What do you pay today for software that touches clients?
- Validated if: 3 of 5 interviews name the same task among their three most time-consuming ones
- Rejected if: fewer than 2 of 5 name any task the offer could automate
- Results: none yet

## Unknowns
- Which task the automation should take first.

## Assumptions
- none

## Sources
[1] Time use in small law firms, Legal Practice Review Example. Published 2026-02-14. Accessed 2026-09-23. https://legalreview.example/time-use-2026. Tier 2. estimate. Quote: "6 hours a week answering clients about case status; managing partners decide on software"
[2] Directory statistics 2026, Bar Association Example. Published 2026-05-01. Accessed 2026-09-23. https://bar.example/directory-2026. Tier 1. fact. Quote: "4,200 firms with 2 to 9 staff"
[3] Pricing, Practice Manager Example. Published undated. Accessed 2026-09-23. https://practicemanager.example/pricing. Tier 1. fact. Quote: "client portal included, EUR 39 per user per month"
[4] Advertising rules for lawyers, Bar Association Example. Published 2025-11-20. Accessed 2026-09-23. https://bar.example/advertising-rules. Tier 1. fact. Quote: "comparative advertising and the promise of results are forbidden; the new filing system starts on 2028-01-03"
[5] Agency survey 2026, Property Agents Example. Published 2026-04-08. Accessed 2026-09-23. https://propertyagents.example/survey-2026. Tier 2. estimate. Quote: "agents spend a third of their week on viewing requests"
[6] Clinic census 2025, Health Registry Example. Published 2025-12-01. Accessed 2026-09-23. https://healthregistry.example/clinics-2025. Tier 1. fact. Quote: "1,900 physiotherapy clinics with staff"

## Method
- Queries: "law firm time spent client status questions", "bar association directory firm size", "practice management software price per user"
- M1: rank.py with the scores of the Comparison table on standard input → totals and the gap between the top two
- Checks: check_refs.py --file docs/business/icp.md; lint_icp.py --file docs/business/icp.md --kind icp
