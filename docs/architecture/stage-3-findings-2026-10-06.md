# What the acceptance of stage 3 showed (2026-10-06)

Stage 3 of the platform plan (`platform-plan-2026-10-05.md`) put the tasks and the documents of the task runtime on the project's platform (a task board and a documents platform, each reached through a provider), added the router step and the plan a person approves, the brand flow, the file drop and the milestones a manifest makes mandatory. Its acceptance asks for the workbench's own brand: the request is routed, the tasks appear on the board, the person edits the brand strategy on the platform, and the name task runs on a copy that holds that edit. This file records what that acceptance and the live measurements before it showed.

It holds counts, kinds, endings, durations and token counts only: no content of a document, no answer, no identifier of the workspace and no path of the machine. The maintainer was away and had delegated supervision: every act the plan gives the person on the platform that was made was made through the platform's API by the executor, and is marked so.

## The live service, before the acceptance

The ten measurements of WP-3.10 (step 4) are recorded in the two providers' `README.md`, "Measured on the live service" (#169). One of them changed the design:

| Measurement | Observed | What it changed |
|---|---|---|
| N3 | A comment does not move a page's version (its last-edited time, rounded to the minute) | The contract said the version changes when the comments change, and the mirror read a page only when its version changed, so a new comment on an unchanged page was never saved. Decided by the supervisor on the maintainer's delegation: the version covers the content, and the comments are listed apart. Built in #171 (WP-3.15): a verb `comments --id` in both classes, called for every mirrored document and every board item at every pull, one call each, whatever the version; the comments on a page's blocks still come with the read |
| N4 | A comment on a block is listed under that block only | Fixed in #169: a read lists the page and every block |
| N8 | A row in the trash answers 404 for its body | Fixed in #169: a trashed row is read as archived, with no text |

Still to be measured by hand, by the maintainer, because the API cannot make the act or the measurement used the API instead: N5 (whether a resolved comment is listed), N10 (a page that exists and was not shared with the integration), and the by-hand variants of N1 (an edit in the app), N3 (a comment in the app), N4 (a comment on a paragraph in the app) and N8 (archiving a row in the app).

## Before any model call

| Check | Observed |
|---|---|
| The real base | It had no text property for the runtime's shown fields and its state property is a status with three options, which the API cannot extend. Added through the API: a text property and a select property with the nine task states as options; the configuration's `fields` points the title, the state and the shown fields at them. The base's own status property was left untouched and is never written |
| The acceptance checkout | Advanced to the central branch holding #171; clean |
| The eval image | The evidence's digest |
| The store | Migrated to version 4 by the first command of the advanced checkout |
| A configuration not accepted yet | `status` refused, exit 3, naming both hashes; `accept-config` accepted it |
| `sync --dry-run` | 1 s; would create 6 board items and 2 pages, read nothing, wrote nothing |
| `proof` (no model call) | The router, `brand-strategy` and `brand-name`: tier `floor`, proven, `reliable` on both models, both checks passing, key `lab` |
| `scripts/select_skills.py` on the system's Python 3.9 (O6) | Runs: `--pack brand` printed the five brand skills, exit 0 |

## The runs

| Run | Task | Skill | Tier | Key | Ending | Right? | Pending | Duration (ms) | Tokens |
|---|---|---|---|---|---|---|---|---|---|
| 11 | the request (route) | core-orchestrator | floor | lab | unclassified (no route line) | the route was right, its form was not a route line | question "The route was not recognised", then cancelled by `route --flow brand` | 213,769 | 215,313 |
| 12 | strategy | brand-strategy | floor | lab | question | yes: it wrote nothing and asked | question, left open | 96,138 | 94,851 |

Both runs: `ok` on the first attempt, `skill_loaded` 1, no value replaced in what they left, a use recorded, the image the evidence's. Run 11 entered the general copy (1,302 files, seven left out: three work-data files, the project's `AGENTS.md`, the runtime's configuration and two files the credential scan flagged), kept the state file it changed (a route-only run returns no file) and brought nothing back. Run 12 entered its declared artifacts (3 files, the workbench section of `AGENTS.md`) and changed nothing. Total: 2 runs, 309,907 ms of model time, 310,164 tokens.

## What the platform showed

| After | Board | Documents |
|---|---|---|
| `approve`, then the first `sync` (125 s) | 12 rows created: the request and its five tasks (strategy `ready`, the others `planned`) and the six requests and tasks of stages 1 and 2 (`done`) | 2 pages created, the two business documents of stage 1 |
| run 12, then `sync` (12 s) | 1 row written (strategy `waiting`); 0 read; 0 comments | nothing read (versions unchanged), nothing written; 0 comments |

On every row the base's own status property reads the platform's default for a new row, since the runtime does not write it.

## Findings

| # | Finding | Kind | What it asks of the design |
|---|---|---|---|
| 1 | The stage's real case could not be completed. The brand strategy of a company needs the positioning document (`brand-strategy`, Stop rule 2), and stage 1's case left it unwritten because the job the offer does is not decided. The strategy run stopped and asked two questions: positioning first, and which platform the brand speaks on. The facts the answers come from settle neither, so the question was left open and no second run was made. Steps 6 and 7 (the person's edit of the strategy on the platform, a comment, and the name task reading the edit) were not run | plan precondition not met (a decision of the maintainer) | The maintainer decides the job (so that the positioning can be written) and the platform, then the acceptance resumes at step 5. The router saw the same gap in its own reply |
| 2 | The router named the brand flow but wrote its route line in backticks with extra words (`flow, pending`: its routing table lists the brand flow skill as planned), which is not a route line by design; the run ended `unclassified` and the flow was named with `route --flow brand`, as step 3's table says | as designed (lab case 9 measures the strict form) | None now. If a router run writes this form again, a tolerant reading of a route line is a runtime package of its own |
| 3 | The board mirrors every task of the store, so the six requests and tasks of stages 1 and 2 appeared with the six of this request; step 4 expected six items | plan text | Step 4 expects every task of the store. Whether a board should receive only the requests made after it was configured is a decision for the maintainer |
| 4 | The base's own status property has three options and the API cannot add any, so the runtime's nine states live in a select property of their own; the person's status is not written and holds the platform's default | as designed (decided before the acceptance) | A coarse mapping of the nine states onto a board's own status property is a backlog item for the maintainer to decide |
| 5 | A run copy holds no platform reference. The brand skills read `shared/references/platforms/<platform>.md` once the platform is known; the lab gives a case those files through its `platforms` key, and the runtime stages the skill's folder only. Run 12 stopped before that step, so nothing failed; read in the run copy, not observed as a failure | runtime gap, not yet hit live | Before a brand run that names its platform: a runtime package that stages the platform references a skill cites (the folder is small and read-only). Open point O7 says to stop and ask when a run reports the reference missing |
| 6 | Run 12 reported that the market analysis named in the request was not in its copy: it is not a declared input of the strategy skill, so limit L3 left it out | as designed | None |
| 7 | A `sync` with nothing to write still makes one call per board item and per mirrored page to list their comments (#171): 12 s for 12 items and 2 pages. The first `sync`, which created 12 rows and 2 pages and read each page back, took 125 s | as designed | The cost grows with every task the store holds (finding 3). If a sync becomes slow, the board's comments can be listed only for tasks that are not final |

## Open points of part 3 that this run answered

| # | Open point | Observed |
|---|---|---|
| O1 | The behaviours of the live service | Recorded in the providers' `README.md` (#169); N3 changed the design (#171) |
| O2 | Whether the router answers the route-only text with exactly one route line | Not on the floor model in this run: the flow was named in a non-strict form (finding 2) |
| O3 | What the router does to the state file in a route-only run | Its reply says it added an open question; the runtime kept the file (class `state`) and wrote nothing to the project |
| O6 | Whether `scripts/select_skills.py` runs on Python 3.9 | Yes |
| O7 | Whether a brand run can read the platform reference its skill cites | Not reached by the run; the run copy holds none (finding 5) |
| O8 | What the voice skill does for a company with no profile | Not reached |
| O9 | Whether a run treats a handed-over file as intended | Not exercised: no file was handed over |
| O10 | Whether an edit made within the minute of the runtime's write is seen | Not exercised: no edit was made (finding 1) |
| O11 | How long a `sync` takes on the real base | 1 s dry, 125 s creating, 12 s with nothing to write (finding 7); calls not counted |

## What was not run

- Steps 6 to 8 of the acceptance: no edit and no comment on the platform, so the round trip of an edit and of a comment was not shown live (finding 1). The comment path of #171 is covered by its offline tests only.
- No lab test, no `eval_run.py`, no docker build, removal or `ensure`.

## Due at the end of this stage

Section F of part 0 of the execution plan (outside the repository) is amended to state what stage 3 built: the modules `router.py`, `plan.py`, `board.py`, `documents.py` and `drop.py`; store migration 4; the configuration keys of `task_board` (`provider`, `base`, `fields`, `states`, `dir`, `expires`) and `documents` (`provider`, `parent`, `dir`, `expires`); the operations `route`, `approve`, `reject`, `hand_over`, `sync` and `answer(..., with_comments)`; the verbs of both classes with `comments`; and the rule that a version covers the content.
