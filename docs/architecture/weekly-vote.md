# Weekly vote to published post (backlog PB15)

- Status: design, 2026-09-30; decisions by the user on 2026-09-30 (listed below)
- First real case: the profile repository `chrissgon/chrissgon` (public, default branch `master`, no ruleset), built in the personal-brand project

## What exists (read on 2026-09-30, read only)

- `data/pick.json`: the open round (`round`, `closes`, `pillar`, `options` A/B/C, `picks` as hashed account ids) and `history` (closed rounds, newest first: `round`, `pillar`, `options`, `counts`, `winner`, `post_url`).
- `data/pick-queue.json`: the next rounds, each `{pillar, options}`.
- `data/posts.json`: posts shown on the profile, each `{date, lang, title, url, image}`, images under `assets/posts/`.
- `.github/workflows/weekly.yml`: every Monday at 12:00 UTC (09:00 in Sao Paulo) runs `scripts/readme.py weekly --apply`: closes the round that ended (winner = most picks, a tie goes to the earlier letter, no picks = no winner), opens the next queued round, rebuilds the README, and commits as github-actions.
- The README shows the last winner with "I wrote it" and the link when `post_url` is set, "I'm writing it now." otherwise.

## Decisions (user, 2026-09-30)

1. A round with no winner: the agent proposes one of the three with its reasons, inside the weekly approval.
2. No answer before the slot: the slot is skipped and the topic waits; nothing is published without the yes.
3. The weekly approval is asked on Monday, right after the round closes.
4. The agents commit directly to the profile repository's default branch, only the vote data files, only after the weekly yes.
5. Only the vote post carries an image: HTML in the brand identity rendered to PNG, contrast checked.
6. Topics already in the content calendar, in the queue or in the history are never proposed again (found on 2026-09-30: the open round's three options were all already in the calendar).

## The weekly run

```text
Mon 09:00  profile workflow closes round R (winner W, post_url empty), opens the next queued round
Mon 09:15+ runtime tick: vote step
           1. read pick.json, pick-queue.json, posts.json from the profile repo (vcs read-file, read only)
           2. vote_state.py: is there a closed round with post_url empty that was not handled? which slot of the
              content calendar carries its pillar in the coming week? which pillar comes next in the queue's rotation?
              which topics are already used (calendar, queue, history)?
           3. agent run (read only): a vote-proposal block: the post on W (or the proposed topic when there is no
              winner, with reasons) in the slot's language, first comment, sources; the 3 topics of the round after
              the queued ones, for the next pillar, each with its material and source
           4. code: content file from the proposal, check_post.py, the post image (HTML piece rendered to PNG,
              contrast.py), payload.py build (post, first comment, image), the profile-repo change set for the
              queue (new round appended), one payload file with everything and its sha256; inbox item + notification
Mon        the person approves once (runtime.py approve --id N --confirmed --sha256 H)
           5. code: schedules the publish job at the slot time (launchd, digest), and commits the queue change to the
              profile repo (vcs commit-files, confirmed under the same approval)
slot time  6. the job publishes the post and its first comment, then records it: post_url into history[R], the post into
              posts.json with its image, committed to the profile repo (the same approval covers it; the files
              written are computed by vote_update.py from the published URL, nothing else)
```

## Pieces

| Piece | Where | Notes |
|-------|-------|-------|
| Reading and committing files in a repository | `providers/vcs/github.py`: `read-file` (REST contents API, read only) and `commit-files` (a private clone, the given files, a signed commit with the user's git configuration, a push to the named branch; idempotency key; `--dry-run` prints the diff) | the requirement class is `integration:vcs`; the skill never names the host |
| Vote state and updates | skill `mkt-vote-round`: `scripts/vote_state.py` (what is pending, the slot, the next pillar, used topics), `scripts/vote_update.py` (the new JSON files, computed, never written by a model) | capability; runtime mode returns the `vote-proposal` block |
| The post image | `brand-identity/scripts/render.py`: an HTML piece rendered to PNG at an exact size with a headless browser; `contrast.py` for the colours | degrade: no browser, no image, the post goes text-only and the approval says so |
| The weekly step | `scripts/runtime.py`: a `vote` section in `runtime.json` (`repo`, `branch`, `slot_pillars`), run once per closed round (cursor `vote:<round>`) | the model proposes; code builds, checks, queues and commits |
| Publish and record | a runner the scheduled job calls: publish, then `vote_update.py` with the post URL, then `commit-files` | its files are in the job's snapshot like any job |

## Safety

- Visitors write the pick issues; picks are counts. The agent never reads issue text; the vote data holds letters and hashed ids only.
- The approval's hash covers the post text, first comment, image, time, and the profile-repo change set. A change to any of them is a new approval.
- `commit-files` refuses paths outside a list the runtime passes (`data/pick-queue.json`, `data/pick.json`, `data/posts.json`, `assets/posts/<slug>.png|webp`).
- A push that is rejected (the workflow committed meanwhile) is retried once after a fresh clone; a second rejection goes to the inbox.

## Open for the user

- The round open now (closes 2026-10-05, pillar "AI built in public") offers three topics that are all already in the calendar (09/10, 07/10, 14/10). Recommendation: when it closes, record the winner's `post_url` as the calendar post of that topic, and use the next week's AI slot for new material.
