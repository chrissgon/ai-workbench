# Brand profile: Dana Example

- Owner: brand-profile
- Status: confirmed
- Date: 2026-09-21
- Language of artifacts: English; language of posts: English [2]

## Who they are
- Public name: Dana Example [1]
- Experience: 7 years 8 months since 2019-01 [1]

## Citable proof
| Proof | What it shows | Type | Source | May cite |
|-------|---------------|------|--------|----------|
| tinykv: a 900-line key-value store | small, boring tools | public product | [1] | yes [2] |
| p99 query latency cut by 64% | databases | self-reported | [1] | yes, without the employer [2] |

## Never expose
- Employer names [2]
- Family [2]
- Salary [2]
- Exact location [2]

### Sensitive-topics lock
```sensitive-topics
{"action": "never_reply_escalate_to_user", "topics": {"employer": {"keywords": ["employer", "your company", "where do you work"], "exclude": []}, "family": {"keywords": ["family", "kids", "wife", "husband"], "exclude": []}, "salary": {"keywords": ["salary", "how much do you earn"], "exclude": []}, "location": {"keywords": ["where do you live", "which city"], "exclude": []}}}
```
- Check: sensitive_topics.py --profile docs/brand/profile.md < text (script of brand-profile)

## Voice
- Declared reference: "dry humour, like a tired sysadmin, never cringe" [2]
- Samples written by Dana (confirmed by the user [2]):
  1. LinkedIn, 2021-03-02 [3]:
     > spent three days chasing a bug that turned out to be a timezone. it is always a timezone.
     > anyway, wrote down what I learned so you don't have to: vacuum your tables, trust nobody, set UTC.
     >
     > #postgres #debugging
  2. LinkedIn, 2022-08-15 [3]:
     > NEW BLOG POST!!! 🚀🚀 I benchmarked 5 key-value stores so you don't have to 🚀
     > spoiler: the fastest one is the one you already run. read it, then go to bed.
     >
     > #databases #benchmarks #rust #performance #opensource #devlife #coding #tech
  3. LinkedIn, 2024-01-09 [3]:
     > my new year's resolution is fewer dependencies. I have already failed, npm installed 212 packages before breakfast 🚀
     > so I wrote tinykv: 900 lines, zero deps, does one thing.
     > what's the smallest tool you actually rely on?
     >
     > #rust #opensource #tinykv
- Not voice samples: the tinykv launch post of 2026-09-10, written by the AI [2]:
  > 🚀 Excited to announce tinykv! A blazing-fast, lightweight key-value store in under 1,000 lines of Rust.

## Open questions
- none

## Sources
[1] LinkedIn export and code host, 2026-09-20.
[2] Decisions in docs/workbench/state.md, 2026-09-20 and 2026-09-23.
[3] Posts provided by the user, 2026-09-20.
