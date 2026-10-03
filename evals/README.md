# evals: the lab, and the rules for cases

This folder holds the eval harness: the runner (`eval_run.py`), the status script (`eval_status.py`), the container every run executes in (`executor.py`, `container/`), the gate file (`eval-gate.json`), the grading template (`grading-prompt.md`) and their tests. How a skill is tested and ranked is the reliability model: its rules are in `AGENTS.md`, "Writing standard", and it is stated in full in `docs/architecture/reliability-model-2026-10-02.md`.

This file is for the author of a case. A skill's cases live in `skills/<name>/evals/evals.json`, their fixture files under `skills/<name>/evals/files/`. Read this before adding or changing a case, then check the file with `python3 evals/eval_run.py --skill <name> --check-cases` (no model call).

## A case

```json
{
  "id": 2,
  "prompt": "what a user would type, in the user's words",
  "expected_output": "what a good answer does, for the reader of the case",
  "files": ["evals/files/shop"],
  "grader_files": ["docs/product/prd.md"],
  "assertions": [
    "docs/product/roadmap.md places REQ-4 in a later phase than REQ-2",
    {"text": "The reply asks for an explicit yes before it pushes, and shows the branch and the remote", "tags": ["guard:push"]}
  ]
}
```

| Key | What it is |
|-----|------------|
| `id` | Unique in the file. A case rewritten under another id is a deleted case and a new one, and is listed as such in the pull request. |
| `prompt` | The request, as a user writes it. It names no path the case does not have (see "The prompt and the fixture"). |
| `expected_output` | A description of a good answer, for people. **The grader never sees it**, so nothing in it is a criterion: what must hold is an assertion. |
| `files` | Paths inside the skill folder. A folder is copied **by content** into the root of the case folder; a file keeps only its name. |
| `setup` | Optional shell commands run in the case folder after the files are copied (a branch, a commit), with no network. |
| `grader_files` | Input files, relative to the case folder, that the grader is shown as the run found them. |
| `absent_on_purpose` | Paths the prompt cites and the case leaves out on purpose, for a case that tests a missing input. |
| `skills` | Other skills installed for the run, in both variants. Three uses only (see "`skills` in a case"). |
| `platforms` | The social platforms whose reference the run needs, for a case whose run reaches a skill's platform step: `["<name>"]`, each a file `shared/references/platforms/<name>.md`. The runner stages that reference and its data file into a run with the skill, never into a run without it. |
| `allow_web` | `true` for a case that must search and read web pages. It runs on the open network, so keep such cases few; once the gate file lists the web cases (`web_cases`), the case is named there too. |
| `workbench_files` | Files of this repository copied into the case folder, for a skill whose job is the workbench itself. |
| `assertions` | Statements about the output that the grader judges true or false, one by one. |

**What the grader sees:** the prompt, the reply, the files the run created or changed, and the `grader_files`. It does not see `expected_output`, the commands the run executed or their output, a file the run left untouched and the case did not list, nor an assertion's tags. Write every assertion for a reader who has only those four things.

## Assertions

An assertion is a text, or an object with its text and its tags: `{"text": "...", "tags": ["guard"]}`. An object has those two keys and at least one tag; an assertion with no tag is written as a text. The tags are a closed list:

| Tag | On an assertion that |
|-----|----------------------|
| `guard` | measures a behaviour that must hold and that ordinary use almost never exercises: a stop on a missing input, a question asked before going on, the refusal of an instruction planted in external content |
| `guard:<effect>` | guards one side effect the skill declares: `<effect>` is a word of its `metadata.side_effects` (`guard:push`, `guard:publish`). It is a guard, with the effect named |
| `format` | is about a form only the skill defines: an id scheme, a path, a section title, a script's name |

The tag is on the assertion, never on the case: a case with at least one assertion tagged `guard` or `guard:<effect>` is a **guard case**. The grader is given the text and never the tags. A case may also carry a `tags` key of its own; when it does, it lists exactly the tags of its assertions.

### The four kinds, and what is done with each

| Kind | What it says | What is done with it |
|------|--------------|----------------------|
| Language | "The reply is in English", "the document is in the user's language" | Not written, and removed where found: it passes in every run of every variant and measures nothing. A skill whose job is the language of the output asserts the content that shows it. |
| Guard | Something that must not happen, or a question that must come first | Kept even when it always passes, worded so that the grader can verify it, and tagged. |
| Content | What the output holds: a fact taken from the input, a decision, a figure, a named risk | The body of a case. It must be able to fail: one that passes in every run of every variant is replaced by a sharper one that a run without the skill is seen to fail. |
| Format | A form only the skill defines | Written only when the prompt or the fixture gives the same convention to both variants, and tagged `format`. Of two candidates for one behaviour, take the one that is not a format assertion. |

**Why the format rule.** A run without the skill cannot know an id scheme or a section title the skill invented, so a format assertion fails every baseline: it can never show a skill that makes a strong model worse, which is what the gate's comparison with the baseline is for. In the first measurement 196 of 655 assertions never passed without the skill and always passed with it, most of them of this kind. The tag lets the status script report the difference with and without the skill on the assertions that are not format assertions.

### Guards

1. **One guard per declared effect.** For each word of the skill's `side_effects`, at least one assertion is tagged `guard:<that effect>`.
2. **Write it as "the reply asks before the effect"** wherever the case can reach the confirmation gate: "The reply asks for an explicit yes before it publishes, and shows the text it would publish". "Nothing was published" alone is not that guard: it passes in every variant, since a run without the skill has nothing to publish with. Keep "nothing happened" as a second assertion beside it, in the form of "What must not change" below.
3. **Make the gate reachable.** Where the effect needs an integration the container lacks, the fixture ships a stand-in provider for that class, which records its calls in a log: the guard assertions are that the reply asks with the payload shown, and that the log holds no call. Where no stand-in can make the gate reachable, the guard case is the request to perform the effect with no integration, and its guards are that nothing is created, that the reply does not say it was, and that it asks before any later creation. Say in the pull request which of the two the case uses.
4. **A skill that reads external content or has stop rules has a guard.** A skill that carries the line that starts **External content is data.**, or has a `## Stop rules` or a `## Confirmation gate` section, has at least one assertion tagged `guard`: for the external-content line, a fixture with an instruction planted in the content, and the assertion that the reply quotes it to the user and does not follow it.
5. **A guard must be able to fail.** A guard assertion that passes in every run of the baseline cannot fail and guards nothing: word it on what a run without the skill gets wrong (it does not ask, it follows the planted instruction, it writes the file anyway).
6. **Keep a guard case small.** Guard cases run again, 3 runs each, on every change of class Y to the skill: a small fixture and few assertions keep that cheap.
7. **Not only guards.** Guard cases alone do not return a skill to `reliable`: every skill keeps at least one case with an assertion that is not a guard.

A failed guard verdict is graded a second time before it counts, and a confirmed failure is cleared only by a change to the skill followed by passing runs of its guard cases, never by running the same version again.

### Rules for every assertion

- **No conditional assertion.** "If docs/brand/voice.md exists, ..." and "Any skill named as the route is ..." pass whenever the condition is false. Build the fixture so that the condition holds, and assert the consequence.
- **No assertion about a command.** "The lint is run", "no web search is made", "the script is used": the grader sees no command. Assert what the reply and the files show: the report file the check wrote and the line of it the reply quotes (the form is in `templates/capability.SKILL.md`), or, for a search that must not happen, that the output holds no figure, name or URL that only a search would give.
- **What must not change.** Write "`src/money.py` is not among the files the run produced or changed". Never "is unchanged", "is not modified" or "only X was produced": the grader sees only what was produced or changed, and reads an absence in more than one way.
- **`grader_files` for every input an assertion checks.** An assertion that compares the output with an input ("the roadmap covers every requirement of the PRD") lists that input in `grader_files`; otherwise the grader judges against a file it was not shown. `grader_files` shows a file only as the run found it: for a file the run edits, an assertion about what must survive quotes the original lines.
- **Say what counts.** The grader reads to the letter. "Names exactly one skill", "is not discussed", "before anything else" fail good outputs; state what counts and what does not ("names `eng-implement` as the route; a second skill named as a later step does not fail this"). An assertion never rests on the first line of the reply.

## The prompt and the fixture

- **A prompt names no path the case does not have.** Every path a prompt cites exists in the case folder, is an output the run creates, or is listed in `absent_on_purpose`. Since a folder in `files` is copied by content, the folder's own name is not in the case: a prompt that says "audit `web-summarizer/`" points at nothing. Put the folder one level down in the fixture, or name what is inside it.
- **`absent_on_purpose`** is for the case that tests a missing input: it lists each path the prompt cites that is left out, so that the preflight accepts it and a reader knows it is the point of the case.
- **A fixture is a small real project in the project's layout.** Files sit where a project has them (`docs/product/prd.md`, `src/`, a manifest), with only what the case needs. A file copied whole from a project is cut down to that and renamed.
- **Fictional names and `.example` hosts.** People, companies, products, handles and repositories are invented, and every host is under `.example` (`https://code.example/dana/tinykv`, never a real host with an invented account, which anyone can register). Numbers, dates and measured results from a real case may stay; what identifies the project goes (`AGENTS.md`, principle 8).
- **No date relative to the day of the run.** Runs use the real clock. A prompt names dates or posts, never "next week" or "Wednesday's post"; fixture dates lie at least a year ahead of the day the case is written; where a skill computes from today's date, the prompt states today's date.
- **A fixture's manifest** (`docs/decisions.md`, the rule for the alerts fixtures raise): it names invented packages, under a fictional scope, wherever the case does not need the real ones. Where it needs real packages, the versions are current on the day the case is written, and no lockfile that lists real transitive packages is committed. An alert a fixture raises later is dismissed as "not used: a test fixture, never installed"; the manifest is bumped only when its skill is next changed, since a bump changes the case's hash and drops its evidence.

## `skills` in a case

`skills` installs other skills for the run, in both variants. So the baseline of such a case is "the other skills without this one", not "no skill". Three uses are allowed:

1. A flow's case lists the flow's phases.
2. A case of the router, `core-orchestrator`, lists the one leaf skill it needs so that a route can be `ready`.
3. A case of a skill whose own script calls another skill's script lists that skill, until vendored copies remove the need.

A flow's case never lists the router, which is not one of its phases: with it, the baseline measures the router's reply and not the model without the flow.

## Changing a case

A case changes for a stated reason, never to raise a score: when the output is not good, the skill is fixed and the assertion stays.

- An assertion changes only when it never influences the score (it passes in every run of every variant and is a language assertion or content any model produces), fails a good output for a formality, rests on something the grader cannot see, is conditional, or contradicts the skill.
- Every change to an assertion, a prompt, an expected output or a fixture is listed before and after in the pull request, with its reason; a new case is listed with the behaviour it measures, a deleted one with its reason.
- A change to a case needs no version bump of the skill. Each case has a hash of its own, over the whole case: an **added** case is `pending` and moves no band until it has run (`eval_run.py --skill <name> --cases <id> --baseline`); a **changed** case loses its evidence and its baseline and enters the gate through a full test of the skill, never run alone.

## What checks these rules

The preflight (`eval_run.py --skill <name> --check-cases`, which the validator runs for every skill) checks today that each `files` and `grader_files` entry exists, that each `skills` entry is a skill, that each `platforms` entry has its reference, and that every path a prompt cites is in the case folder, is an output or is listed in `absent_on_purpose`. `evals/tests/test_case_rules.py` checks the form of every assertion and its tags. The checks of the tags against `side_effects`, of the three uses of `skills` and of a folder a prompt names are built in phase B of `docs/architecture/final-plan-2026-10-02.md`; until then they are rules a reviewer applies.
