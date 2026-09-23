# Edge-case categories

Walk every category. Write `EDGE-n: <scenario> → <expected behaviour>` for those that apply; name the ones skipped and why.

| Category | Ask |
|----------|-----|
| Data | empty, missing required field, wrong format, very large, special characters and other scripts, duplicates |
| Timing | concurrent actions, slow dependency, timeout, out-of-order events, retry and duplicate submission |
| State | thing does not exist, already exists, no permission, expired session, invalid transition, partially applied change |
| Volume | zero items, one item, thousands of items, pagination boundaries, rate limits |
| Integration | dependency down, unexpected response, contract change, partial failure, stale cache |
| Content | very long text, missing translation, broken link or image, unsupported markup |
| Version and time | older version selected, page absent in that version, deprecated feature, clock and timezone |
| Device and environment | small screen, keyboard only, screen reader, no JavaScript, feature unsupported by the browser (for example no WebGPU), offline |

Good: `EDGE-3: reader switches to v0 on a page that exists only in v1 → lands on the v0 index with the notice "This page does not exist in 0.23"`.
Poor: `EDGE-3: handle missing pages gracefully`.
