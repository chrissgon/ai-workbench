# Brand voice: Dana Example

- Owner: brand-voice
- Status: confirmed (2026-09-25)
- Date: 2026-09-25
- Reads: docs/brand/profile.md (confirmed), docs/brand/strategy.md (approved)
- Applies to: posts and replies, English

## In one sentence
A tired sysadmin with dry humour who writes short and never cringes [1]

## Declared direction
- "dry humour, like a tired sysadmin, never cringe" [1]
- "keep the dry jokes, lose the ALL CAPS shouting and the rocket emojis" [1]

## What stays from the samples
| Trait | Evidence (quote, sample) | Rule |
|-------|--------------------------|------|
| Dry punchline | "it is always a timezone." (S1) | End the first paragraph on a short dry line |
| Saves the reader time | "so you don't have to" (S1, S2) | Say what the reader skips by reading |
| Lowercase, plain words | "anyway, wrote down what I learned" (S1) | Lowercase is fine; no jargon to impress |

## What changes
| Old habit | Evidence (count from voice_stats.py) | New rule | Source of the change |
|-----------|--------------------------------------|----------|----------------------|
| Rocket emojis | S2: 3 emojis; S3: 1 emoji | No emojis | [1] |
| Eight hashtags | S2: 8 hashtags | At most 2 hashtags | [1] |
| ALL CAPS opening | S2: "NEW BLOG POST!!!" | No capitals for emphasis, no exclamation marks | [1] |

## Checkable limits
```voice-rules
{"max_emojis": 0, "max_hashtags": 2, "max_exclamations": 0, "end_with_question": true, "no_emoji_line_start": true, "banned": ["NEW BLOG POST", "Excited to announce"]}
```
- Check: voice_stats.py check --rules docs/brand/voice.md < draft (script of brand-voice)

## Register
- Fits: "trust nobody, set UTC." Does not fit: "blazing-fast" [2]

## Post structure
1. The dry observation.
2. What was learned, in one line.
3. A question to the reader.

## Replies to comments
- One or two sentences; thank once; no emojis; never mention an employer, family, salary or location [2].

## Calibration: before and after
### English (S1)
Before: 0 emojis, 2 hashtags, no closing question
After:
> spent three days chasing a bug that turned out to be a timezone. it is always a timezone.
> wrote down what I learned so you don't have to: vacuum your tables, trust nobody, set UTC.
> what was your last timezone bug?
>
> #postgres #debugging

### English (S2)
Before: 3 emojis, 8 hashtags, 3 exclamation marks, ALL CAPS opening, no closing question
After:
> I benchmarked 5 key-value stores so you don't have to.
> spoiler: the fastest one is the one you already run. read it, then go to bed.
> which one are you already running?
>
> #databases #benchmarks

### Reply to a comment
Comment: "nice write-up, which store won on writes?"
After:
> thanks for reading. the one you already run, as usual. which one is it?

## Assumptions
- none

## Sources
[1] Decisions in docs/workbench/state.md, 2026-09-20 to 2026-09-24.
[2] docs/brand/profile.md, 2026-09-21.
