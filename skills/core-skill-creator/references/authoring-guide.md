> Authoring reference carried over from the previous repository, now owned by `core-skill-creator`. Load the section you need when the procedure in `SKILL.md` points at it. Repository-wide rules live in the workbench `AGENTS.md`; where the two disagree, `AGENTS.md` wins.

# Agent Skills Guide

This document enforces rules and best practices for creating and maintaining skills in this repository, based on the [Agent Skills specification](https://agentskills.io/).

## Table of Contents

- [Folder Structure](#folder-structure)
- [SKILL.md Format](#skillmd-format)
- [Best Practices](#best-practices)
- [Using Scripts](#using-scripts)
- [Evaluation Framework](#evaluation-framework)
- [Description Optimization](#description-optimization)
- [Quality Checklist](#quality-checklist)

---

## Folder Structure

### Required Structure

Every skill MUST follow this directory structure:

```
skill-name/
├── SKILL.md          # Required: metadata + instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: detailed documentation
├── assets/           # Optional: templates, resources
└── evals/            # Optional: evaluation test cases
    ├── evals.json
    └── files/
```

### Progressive Disclosure Principle

Skills are loaded in stages:

1. **Metadata (~100 tokens)**: `name` and `description` fields loaded at startup
2. **Instructions (< 5000 tokens)**: Full `SKILL.md` body loaded when skill activates
3. **Resources (as needed)**: Files in `scripts/`, `references/`, `assets/` loaded only when required

**Golden Rule**: Keep `SKILL.md` under **500 lines** and **5,000 tokens**. Move detailed content to separate files.

---

## SKILL.md Format

### Frontmatter Requirements

Every `SKILL.md` MUST start with YAML frontmatter:

```yaml
---
name: skill-name                    # Required: 1-64 chars, lowercase, hyphens only
description: >                       # Required: 1-1024 chars, what + when to use
  Clear description of what the skill does and when to use it.
  Include specific keywords for agent discovery.
license: Apache-2.0                 # Optional: license identifier
compatibility: >                     # Optional: environment requirements (≤500 chars)
  Designed for terminal agents. Requires git, docker, jq.
metadata:                           # Optional: custom key-value pairs
  author: example-org
  version: "1.0"
allowed-tools: Bash(git status:*) Bash(git diff:*) Read    # Optional: pre-approved tools (experimental); name read-only subcommands, never a whole tool
---
```

### Name Field Rules

- **Length**: 1-64 characters
- **Characters**: Only lowercase `a-z`, `0-9`, and hyphens `-`
- **Restrictions**:
  - Must NOT start or end with hyphen
  - Must NOT contain consecutive hyphens (`--`)
  - MUST match parent directory name

✅ Valid: `pdf-processing`, `data-analysis`, `code-review`  
❌ Invalid: `PDF-Processing`, `-pdf`, `pdf--processing`

### Description Field Rules

- **Length**: 1-1024 characters
- **Style**: Use imperative phrasing ("Use this when...")
- **Content**: Describe BOTH what it does AND when to use it
- **Keywords**: Include specific terms agents search for
- **Scope**: Be "pushy" - mention edge cases where it applies

✅ Good:
```yaml
description: >
  Analyze CSV and tabular data files — compute summary statistics,
  add derived columns, generate charts, and clean messy data. Use this
  skill when the user has a CSV, TSV, or Excel file and wants to
  explore, transform, or visualize the data, even if they don't
  explicitly mention "CSV" or "analysis."
```

❌ Poor:
```yaml
description: Helps with PDFs.
```

### Body Content Guidelines

The Markdown body should contain:

1. **Clear objectives** - What the skill accomplishes
2. **Step-by-step instructions** - Ordered workflows
3. **Examples** - Concrete input/output samples
4. **Edge cases** - Gotchas and non-obvious issues
5. **File references** - Links to scripts, references, templates

Use relative paths from skill root:
```markdown
See [detailed API reference](references/api-docs.md) for complete details.

Run the extraction script:
```bash
bash scripts/extract.sh input.pdf
```
```

---

## Best Practices

### 1. Start from Real Expertise

**DO NOT** ask an LLM to generate skills from generic knowledge.

**DO** ground skills in domain-specific context:

- ✅ Extract from hands-on tasks (conversation traces with corrections)
- ✅ Synthesize from project artifacts (runbooks, incident reports, PRs)
- ✅ Use real API specs, schemas, configuration files
- ✅ Include actual failure cases and resolutions
- ✅ Reference version control history and patches

### 2. Refine with Real Execution

The first draft ALWAYS needs refinement:

1. Run the skill against real tasks
2. Review agent execution traces (not just outputs)
3. Feed results back into improvement
4. Identify wasted steps, unclear instructions, false positives
5. Iterate until quality plateaus

**Look for in traces:**
- Agent tries multiple approaches → instructions too vague
- Agent follows irrelevant instructions → too many options
- Agent reinvents same logic → bundle as script

### 3. Spending Context Wisely

#### Add What the Agent Lacks

Focus on what the agent wouldn't know without your skill:

- ✅ Project-specific conventions
- ✅ Domain-specific procedures  
- ✅ Non-obvious edge cases
- ✅ Particular tools or APIs to use
- ✅ Environment-specific gotchas

❌ DON'T explain common knowledge (what PDFs are, how HTTP works)

#### Structure Large Skills

When a skill legitimately needs extensive content:

1. Keep core instructions in `SKILL.md`
2. Move details to `references/`
3. Tell agents WHEN to load each file:

```markdown
## Error Handling

For API errors, read [references/api-errors.md](references/api-errors.md) 
when receiving non-200 status codes.
```

### 4. Calibrating Control

Match instruction specificity to task fragility:

**Flexible tasks** (multiple valid approaches):
```markdown
## Code Review Process

1. Check database queries for SQL injection (use parameterized queries)
2. Verify authentication on all endpoints
3. Look for race conditions in concurrent code
4. Confirm errors don't leak internal details
```

**Fragile tasks** (exact sequence required):
```markdown
## Database Migration

Run exactly this sequence:

```bash
python scripts/migrate.py --verify --backup
```

Do NOT modify the command or add flags.
```

### 5. Provide Defaults, Not Menus

Pick a default and mention alternatives briefly:

✅ Good:
```markdown
Use pdfplumber for text extraction:

```python
import pdfplumber
```

For scanned PDFs requiring OCR, use pdf2image with pytesseract instead.
```

❌ Poor:
```markdown
You can use pypdf, pdfplumber, PyMuPDF, or pdf2image...
```

### 6. Favor Procedures Over Declarations

Teach HOW to approach problems, not WHAT to produce:

✅ Reusable method:
```markdown
1. Read schema from `references/schema.yaml` to find tables
2. Join tables using `_id` foreign key convention
3. Apply filters as WHERE clauses
4. Aggregate numeric columns and format as markdown table
```

❌ Specific answer:
```markdown
Join `orders` to `customers` on `customer_id`, filter `region = 'EMEA'`, sum `amount`.
```

---

## Patterns for Effective Instructions

### Gotchas Sections

The highest-value content - environment-specific facts that defy assumptions:

```markdown
## Gotchas

- The `users` table uses soft deletes. Queries MUST include 
  `WHERE deleted_at IS NULL` or results include deactivated accounts.
- User ID is `user_id` in database, `uid` in auth service, 
  and `accountId` in billing API. All three are the same value.
- The `/health` endpoint returns 200 even if database is down. 
  Use `/ready` for full service health checks.
```

**When to update**: Add corrections after every mistake you have to fix.

### Templates for Output Format

Provide concrete structures instead of prose descriptions:

```markdown
## Report Structure

Use this template, adapting sections as needed:

```markdown
# [Analysis Title]

## Executive Summary
[One-paragraph overview of key findings]

## Key Findings
- Finding 1 with supporting data
- Finding 2 with supporting data

## Recommendations
1. Specific actionable recommendation
2. Specific actionable recommendation
```
```

**Short templates**: Inline in `SKILL.md`  
**Long templates**: Store in `assets/` and reference with trigger condition

### Checklists for Multi-Step Workflows

Help agents track progress and avoid skipping steps:

```markdown
## Form Processing Workflow

Progress:
- [ ] Step 1: Analyze form (run `scripts/analyze_form.py`)
- [ ] Step 2: Create field mapping (edit `fields.json`)
- [ ] Step 3: Validate mapping (run `scripts/validate_fields.py`)
- [ ] Step 4: Fill form (run `scripts/fill_form.py`)
- [ ] Step 5: Verify output (run `scripts/verify_output.py`)
```

### Validation Loops

Instruct agents to validate before proceeding:

```markdown
## Editing Workflow

1. Make your edits
2. Run validation: `python scripts/validate.py output/`
3. If validation fails:
   - Review the error message
   - Fix the issues
   - Run validation again
4. Only proceed when validation passes
```

### Plan-Validate-Execute Pattern

For batch or destructive operations:

```markdown
## PDF Form Filling

1. Extract fields: `python scripts/analyze_form.py input.pdf` → `form_fields.json`
2. Create `field_values.json` mapping field names to values
3. Validate: `python scripts/validate_fields.py form_fields.json field_values.json`
   - Checks field names exist, types compatible, required fields present
4. If validation fails, revise `field_values.json` and re-validate
5. Fill form: `python scripts/fill_form.py input.pdf field_values.json output.pdf`
```

**Key**: Step 3 must check the plan against source of truth with actionable errors.

---

## Using Scripts

### When to Bundle Scripts

Bundle scripts when you see agents repeatedly:
- Building the same charts
- Parsing the same format
- Validating the same structure
- Running the same complex command

### Script Location

All scripts go in `scripts/` directory with relative paths from skill root.

### Self-Contained Scripts

Use inline dependency declarations (PEP 723 for Python):

```python
# /// script
# dependencies = [
#   "beautifulsoup4==4.12.3",
#   "requests==2.32.3"
# ]
# requires-python = ">=3.11"
# ///

from bs4 import BeautifulSoup
import requests

# ... script logic
```

Run with: `uv run scripts/extract.py`

### Designing Scripts for Agents

#### ❌ NEVER Use Interactive Prompts

Scripts MUST accept all input via:
- Command-line flags
- Environment variables
- stdin

```bash
# ❌ Bad: hangs waiting for input
$ python scripts/deploy.py
Target environment: _

# ✅ Good: clear error with guidance
$ python scripts/deploy.py
Error: --env is required. Options: development, staging, production.
Usage: python scripts/deploy.py --env staging --tag v1.2.3
```

#### ✅ ALWAYS Document with `--help`

```
Usage: scripts/process.py [OPTIONS] INPUT_FILE

Process input data and produce a summary report.

Options:
  --format FORMAT    Output format: json, csv, table (default: json)
  --output FILE      Write to FILE instead of stdout
  --verbose          Print progress to stderr

Examples:
  scripts/process.py data.csv
  scripts/process.py --format csv --output report.csv data.csv
```

#### ✅ ALWAYS Write Helpful Error Messages

```python
# ❌ Bad
print("Error: invalid input")

# ✅ Good
print(f"Error: --format must be one of: json, csv, table.")
print(f"       Received: '{args.format}'")
```

#### ✅ ALWAYS Use Structured Output

- Prefer JSON, CSV, TSV over free-form text
- Send data to stdout, diagnostics to stderr
- Make output parseable by `jq`, `cut`, `awk`

```bash
# ❌ Bad - hard to parse
NAME          STATUS    CREATED
my-service    running   2025-01-15

# ✅ Good - unambiguous
{"name": "my-service", "status": "running", "created": "2025-01-15"}
```

#### Additional Script Guidelines

- **Idempotency**: "Create if not exists" vs "create and fail on duplicate"
- **Input constraints**: Reject ambiguous input with clear errors
- **Dry-run support**: `--dry-run` flag for destructive operations
- **Exit codes**: Use distinct codes for different failure types
- **Safe defaults**: Require `--confirm` or `--force` for destructive ops
- **Output size**: Default to summaries, support `--offset` for pagination

### Referencing Scripts in SKILL.md

List available scripts:

```markdown
## Available Scripts

- **`scripts/validate.sh`** - Validates configuration files
- **`scripts/process.py`** - Processes input data
- **`scripts/analyze.py`** - Analyzes results
```

Then instruct usage:

```markdown
## Workflow

1. Validate inputs:
   ```bash
   bash scripts/validate.sh "$INPUT_FILE"
   ```

2. Process results:
   ```bash
   python scripts/process.py --input results.json --output summary.json
   ```
```

---

## Evaluation Framework

### Test Case Structure

Create `evals/evals.json` with realistic test cases:

```json
{
  "skill_name": "csv-analyzer",
  "evals": [
    {
      "id": 1,
      "prompt": "I have a CSV of monthly sales data in data/sales_2025.csv. Can you find the top 3 months by revenue and make a bar chart?",
      "expected_output": "A bar chart image showing the top 3 months by revenue, with labeled axes and values.",
      "files": ["evals/files/sales_2025.csv"],
      "assertions": [
        "The output includes a bar chart image file",
        "The chart shows exactly 3 months",
        "Both axes are labeled",
        "The chart title or caption mentions revenue"
      ]
    }
  ]
}
```

### Test Case Design Principles

**Start small**: Begin with 2-3 test cases, expand later

**Vary prompts**:
- Different phrasings (formal, casual, with typos)
- Different explicitness ("analyze CSV" vs "make a chart from this file")
- Different detail levels (terse vs context-heavy)
- Different complexity (single-step vs multi-step)

**Cover edge cases**:
- Malformed input
- Unusual requests
- Ambiguous instructions

**Use realistic context**:
- File paths: `~/Downloads/report_final_v2.xlsx`
- Personal context: "my manager asked me to..."
- Specific details: column names, company names, values
- Casual language, abbreviations, typos

### Workspace Structure for Evals

```
skill-name/
└── evals/
    ├── evals.json
    └── files/
        ├── sales_2025.csv
        └── customers.csv

skill-name-workspace/
└── iteration-1/
    ├── eval-top-months-chart/
    │   ├── with_skill/
    │   │   ├── outputs/
    │   │   ├── timing.json
    │   │   └── grading.json
    │   └── without_skill/
    │       ├── outputs/
    │       ├── timing.json
    │       └── grading.json
    └── benchmark.json
```

### Running Evals

For each test case:

1. **Run with skill**: Provide skill path, prompt, input files, output dir
2. **Run without skill** (baseline): Same prompt, no skill, different output dir
3. **Capture timing**: Save `total_tokens` and `duration_ms` to `timing.json`
4. **Grade assertions**: Evaluate each assertion, save to `grading.json`

### Writing Assertions

Good assertions (specific, verifiable):
- ✅ "The output file is valid JSON"
- ✅ "The bar chart has labeled axes"
- ✅ "The report includes at least 3 recommendations"

Weak assertions (vague, brittle):
- ❌ "The output is good"
- ❌ "Output uses exactly 'Total Revenue: $X'"

### Grading Outputs

Example `grading.json`:

```json
{
  "assertion_results": [
    {
      "text": "The output includes a bar chart image file",
      "passed": true,
      "evidence": "Found chart.png (45KB) in outputs directory"
    },
    {
      "text": "Both axes are labeled",
      "passed": false,
      "evidence": "Y-axis labeled 'Revenue ($)' but X-axis has no label"
    }
  ],
  "summary": {
    "passed": 3,
    "failed": 1,
    "total": 4,
    "pass_rate": 0.75
  }
}
```

**Grading principles**:
- Require concrete evidence for PASS
- Don't give benefit of the doubt
- Review assertions themselves (too easy, too hard, unverifiable?)

### Aggregating Results

Create `benchmark.json`:

```json
{
  "run_summary": {
    "with_skill": {
      "pass_rate": { "mean": 0.83, "stddev": 0.06 },
      "time_seconds": { "mean": 45.0, "stddev": 12.0 },
      "tokens": { "mean": 3800, "stddev": 400 }
    },
    "without_skill": {
      "pass_rate": { "mean": 0.33, "stddev": 0.10 },
      "time_seconds": { "mean": 32.0, "stddev": 8.0 },
      "tokens": { "mean": 2100, "stddev": 300 }
    },
    "delta": {
      "pass_rate": 0.50,
      "time_seconds": 13.0,
      "tokens": 1700
    }
  }
}
```

**Interpret delta**: What the skill costs (time, tokens) vs what it buys (pass rate)

### Analyzing Patterns

After aggregating results:

1. **Remove assertions that always pass** in both configs (inflate scores without showing value)
2. **Investigate assertions that always fail** (broken, too hard, wrong check)
3. **Study with_skill passes, without_skill fails** (where skill adds value)
4. **Tighten instructions for high stddev** (inconsistent = ambiguous)
5. **Check time/token outliers** (read execution transcripts to find bottleneck)

### Human Review

Record specific feedback in `feedback.json`:

```json
{
  "eval-top-months-chart": "Chart missing axis labels and months in alphabetical order instead of chronological.",
  "eval-clean-missing-emails": ""
}
```

Empty feedback = output looked fine. Focus improvements on cases with specific complaints.

### Iteration Loop

1. Give eval signals + current `SKILL.md` to LLM, ask for improvements
2. Review and apply changes
3. Rerun all tests in new `iteration-<N+1>/` directory
4. Grade and aggregate new results
5. Human review
6. Repeat until satisfied or no meaningful improvement

**Stop when**: Results satisfy you, feedback consistently empty, or improvement plateaus.

**LLM improvement guidelines**:
- Generalize from feedback (fixes should address underlying issues broadly)
- Keep skill lean (fewer, better instructions often outperform exhaustive rules)
- Explain the why (reasoning-based > rigid directives)
- Bundle repeated work (scripts for repeated patterns)

### In This Workbench: Checked Cases, a Record, a Computed Status

The loop above is run by `scripts/eval_run.py` of this skill, and its result is kept on record. `eval_run.py --skill <name>` is the whole command: the strong and floor model, their adapters, the floor model's key variable and the threshold default to the eval gate configuration, `evals/eval-gate.json`, and a flag overrides one for a run. The floor model is an inexpensive hosted open-weight model; a model on a person's own machine is measured and published as a goal and does not gate.

1. **Check the cases before running them**: `eval_run.py --skill <name> --check-cases` calls no model. It fails when a `files` entry does not exist, when the prompt cites a path that is not in the case folder (unless the path is an output named in `expected_output`, an assertion or the skill's `metadata.outputs`, or is listed in the case's `absent_on_purpose`), when a `grader_files` entry is not in the case folder, or when a `skills` dependency does not exist. Every real run does the same check first.
2. **Runs happen outside the repository**: each model run and each grading works in a fresh temporary folder whose parents hold no repository, instruction file or skills folder, with no path into the repository in its environment; the folder is moved to `evals-workspace/<skill>/iteration-N/.../cwd` when the run ends, also after a timeout or a stop. A without-skill run whose output still shows the repository's path is listed under `contaminated` in `benchmark.json` and blocks the record unless `--allow-contaminated`. `eval_run.py --skill <name> --only without --update-record` measures the baseline again, alone, and replaces the two without-skill scores of a record that is still current.
3. **Infrastructure failures are not scores**: a run whose adapter fails, times out, returns nothing, or whose grading is unreadable goes to `infra_failures` in `benchmark.json`, never into a mean, and the iteration gets `"complete": false` (exit code 1). Rerun it; do not change the skill for it.
   - **Early ends**: a model sometimes ends its turn before doing the work, with exit 0 and no error. The runner calls a run an early end only when it wrote no file and its response is not a reply to the user: empty, a tool call or control block printed as text at the start of a line, or a last line that announces a next action ("Let me update the file:") in a response with no question mark. Such a run is rerun in a fresh folder (`--retries`, default 2), the early attempts are kept in `early-end-<j>/` and counted per model in `early_ends`; one that early-ends on every attempt is an infrastructure failure with reason `early_end`. A reply that asks a question and writes nothing is a stop-and-ask, and a run that wrote a file and then stopped is graded as it is: neither is retried.
   - **The warning**: `early_end_warning` is set when a model has at least 3 early ends and either a rate above `--early-end-rate` (default 0.15) or all of them on one case. Read the transcripts, then decide: one case points at the skill or the case, a spread points at the provider or the model. Never tune a skill to fix a provider's early ends.
4. **The record**: a complete run of every case, with and without the skill, on both models, writes `skills/<name>/evals/result.json`: scores, gate, date, iteration, early ends per model, and a sha256 of the skill folder taken when the run started. It is committed and never edited by hand. `python3 evals/eval_status.py record --skill <name> --benchmark <path>` builds it from an older `benchmark.json`.
5. **The status** (`python3 evals/eval_status.py status`): `draft` (no record, a failed gate or an incomplete run), `evaluated` (gate passed on the configured floor model, folder unchanged), `stale` (gate passed, but on another floor model than the configured one, or the folder changed since). Only `evaluated` is done. When the configured floor model changes, every record goes stale and every skill is rerun on the new one; a full run on any other floor model writes no record unless `--record-anyway`. A changed threshold is applied to the recorded scores.
6. **The inventory**: `python3 evals/eval_status.py inventory --write` regenerates the status table in `docs/inventory.md`; `scripts/validate.py` fails while it is out of date.

---

## Description Optimization

### How Triggering Works

Agents use **progressive disclosure**:
1. Load only `name` + `description` of all skills at startup
2. Match description against user's task
3. Read full `SKILL.md` when description matches

**Critical**: Description carries entire burden of triggering.

**Nuance**: Agents consult skills for tasks requiring specialized knowledge, not simple one-step requests.

### Writing Effective Descriptions

**Use imperative phrasing**: "Use this skill when..." not "This skill does..."

**Focus on user intent**: What user wants to achieve, not internal mechanics

**Be pushy**: List contexts explicitly, including indirect mentions

**Stay concise**: Few sentences to short paragraph (max 1024 chars)

### Testing Trigger Accuracy

Create `eval_queries.json` with should/should-not-trigger queries:

```json
[
  {
    "query": "I've got a spreadsheet in ~/data/q4_results.xlsx with revenue in col C and expenses in col D — can you add a profit margin column?",
    "should_trigger": true
  },
  {
    "query": "what's the quickest way to convert this json file to yaml",
    "should_trigger": false
  }
]
```

**Aim for**: ~20 queries (8-10 should-trigger, 8-10 should-not-trigger)

**Should-trigger queries**: Vary phrasing, explicitness, detail, complexity

**Should-not-trigger queries**: Near-misses (share keywords but need different skill)

### Running Trigger Evals

1. Run each query 3+ times (nondeterministic behavior)
2. Compute trigger rate (fraction where skill invoked)
3. Pass threshold: >0.5 for should-trigger, <0.5 for should-not-trigger

### Train/Validation Split

Avoid overfitting:
- **Train set** (~60%): Use to identify failures and guide improvements
- **Validation set** (~40%): Use only to check if improvements generalize
- Keep split fixed across iterations

### Optimization Loop

1. Evaluate current description on train + validation sets
2. Identify failures in **train set only**
3. Revise description:
   - Should-trigger failing? → Broaden scope
   - Should-not-trigger failing? → Add specificity, clarify boundaries
   - Avoid adding specific keywords → Find general category
   - Try structurally different approach if stuck
   - Keep under 1024 characters
4. Repeat until train set passes or no improvement
5. Select best iteration by **validation pass rate**

**Stop after**: ~5 iterations (if not improving, issue is with queries)

### Before and After Example

```yaml
# ❌ Before
description: Process CSV files.

# ✅ After
description: >
  Analyze CSV and tabular data files — compute summary statistics,
  add derived columns, generate charts, and clean messy data. Use this
  skill when the user has a CSV, TSV, or Excel file and wants to
  explore, transform, or visualize the data, even if they don't
  explicitly mention "CSV" or "analysis."
```

---

## Quality Checklist

Before considering a skill complete, verify:

### Structure
- [ ] Skill directory name matches `name` in frontmatter
- [ ] `SKILL.md` has valid YAML frontmatter
- [ ] `SKILL.md` body is under 500 lines / 5000 tokens
- [ ] Detailed content moved to `references/`
- [ ] Scripts bundled in `scripts/` with relative paths
- [ ] Templates/resources in `assets/`

### Frontmatter
- [ ] `name`: 1-64 chars, lowercase, hyphens only, matches directory
- [ ] `description`: 1-1024 chars, imperative, what + when to use
- [ ] `license`: Present if not using default
- [ ] `compatibility`: Only if specific requirements exist
- [ ] `metadata`: Includes author, version if applicable

### Content Quality
- [ ] Grounded in real expertise (not generic LLM knowledge)
- [ ] Refined through real execution (at least one iteration)
- [ ] Adds what agent lacks (project-specific, domain-specific)
- [ ] Omits common knowledge (HTTP, PDFs, etc.)
- [ ] Specificity matches fragility (flexible vs rigid)
- [ ] Provides defaults, not menus
- [ ] Teaches procedures, not specific answers

### Patterns
- [ ] Gotchas section for non-obvious issues
- [ ] Templates for structured outputs
- [ ] Checklists for multi-step workflows
- [ ] Validation loops where appropriate
- [ ] Plan-validate-execute for destructive ops

### Scripts
- [ ] No interactive prompts (all via flags/env/stdin)
- [ ] `--help` documentation present
- [ ] Helpful error messages with guidance
- [ ] Structured output (JSON/CSV/TSV)
- [ ] Inline dependencies declared (PEP 723)
- [ ] Idempotent where possible
- [ ] Dry-run support for destructive ops

### Evaluation
- [ ] `evals/evals.json` exists with 2+ test cases
- [ ] Prompts are realistic (varied, detailed, casual)
- [ ] Assertions are specific and verifiable
- [ ] At least one with_skill vs without_skill comparison
- [ ] Grading results documented
- [ ] Human feedback captured

### Description
- [ ] Under 1024 characters
- [ ] Uses imperative phrasing
- [ ] Focuses on user intent
- [ ] Includes trigger keywords
- [ ] Tested with trigger evals (if applicable)
- [ ] Train/validation split maintained
- [ ] Pass rate >0.8 on validation set

### Documentation
- [ ] File references use relative paths
- [ ] References explain WHEN to load ("when API returns 404")
- [ ] No deeply nested reference chains
- [ ] Examples include realistic file paths, context
- [ ] One level deep references from `SKILL.md`

---

## Migration Plan

To update existing skills to match these standards:

### Phase 1: Structure Audit
1. Verify directory names match frontmatter `name`
2. Check `SKILL.md` token count (aim < 5000)
3. Identify content to extract to `references/`
4. Ensure scripts are in `scripts/` with relative paths

### Phase 2: Content Refinement
1. Add/improve frontmatter (especially `description`)
2. Add Gotchas sections from past corrections
3. Add templates for outputs
4. Add checklists for workflows
5. Extract detailed docs to references

### Phase 3: Script Hardening
1. Remove interactive prompts
2. Add `--help` documentation
3. Improve error messages
4. Convert to structured output
5. Add inline dependencies

### Phase 4: Evaluation Setup
1. Create `evals/` directory
2. Write 2-3 initial test cases
3. Run first with/without comparison
4. Document grading criteria
5. Set up iteration workspace

### Phase 5: Description Optimization
1. Create trigger eval queries
2. Split train/validation
3. Run optimization loop
4. Validate final description
5. Update frontmatter

---

## References

- [Agent Skills Specification](https://agentskills.io/specification)
- [Best Practices](https://agentskills.io/skill-creation/best-practices)
- [Using Scripts](https://agentskills.io/skill-creation/using-scripts)
- [Optimizing Descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)
- [Evaluating Skills](https://agentskills.io/skill-creation/evaluating-skills)
- [skills-ref Validator](https://github.com/agentskills/agentskills/tree/main/skills-ref)

---

## Appendix: Quick Reference

### File Size Limits
- **SKILL.md**: < 500 lines, < 5000 tokens
- **Description**: 1-1024 characters
- **Name**: 1-64 characters
- **Compatibility**: 1-500 characters

### Directory Naming
- Lowercase `a-z`, numbers `0-9`, hyphens `-`
- No leading/trailing hyphens
- No consecutive hyphens `--`

### Script Best Practices
- Accept input via: flags, env vars, stdin
- Output: data to stdout, diagnostics to stderr
- Format: JSON, CSV, TSV (not free-form text)
- Help: Always implement `--help`
- Errors: Specific with guidance

### Evaluation Metrics
- **Pass rate**: % assertions passed
- **Trigger rate**: % queries that triggered skill
- **Token cost**: Mean tokens used
- **Time cost**: Mean duration

### Progressive Disclosure
1. Metadata: `name` + `description` (~100 tokens)
2. Instructions: Full `SKILL.md` (< 5000 tokens)
3. Resources: `scripts/`, `references/`, `assets/` (as needed)
