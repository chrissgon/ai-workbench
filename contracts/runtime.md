# Runtime contract: agent runs started by triggers

The runtime starts agents without a person at the keyboard: a scheduler fires, the runtime finds new work, runs an agent on it through an adapter, and executes the agent's proposal only when a deterministic gate allows it. It names no AI tool; adapters do. Decided on 2026-09-28 (`docs/decisions.md`, "An agent runtime as a new, tool-free layer"); first built for one agent, `social-manager` (backlog PB7), on the user's Mac.

## Pieces

| Piece | Where | What it does |
|-------|-------|--------------|
| Trigger | `scheduler` class, a recurring job | runs `scripts/runtime.py tick` every N minutes |
| Runtime | `scripts/runtime.py` | finds new work, records it, runs the agent, applies the gate, executes, logs |
| Store | `store` class (`providers/store/`) | events, cursors, runs, inbox, actions; many writers at once |
| Agent run | `adapters/<harness>/run-agent.sh` | runs one agent on one task, read-only, and returns its answer |
| Gate | the skill's own script (`mkt-engage/scripts/policy_gate.py`) | decides whether a proposal is inside the person's approval |
| Actuator | a provider (`publisher:<platform>`) | executes, with an idempotency key |
| Configuration | `docs/workbench/runtime.json` in the project | paths, providers, model, budgets; no secret |

## An agent run

- **Input:** the agent definition (`agents/<name>.md`), a task file the runtime writes (what to do, and the trigger's data marked as external content), the skills the agent lists, read access to the project folder.
- **Tools:** read only. The model reads files and answers; it cannot write files, run commands or call a network service. Everything it proposes comes back as a fenced JSON block in its answer, whose shape the task names.
- **Budget:** a spend limit per run (`max_cost_usd`) and a time limit (`timeout_seconds`); a daily spend cap across runs (`daily_cost_cap_usd`), checked before each run from the store.
- **Output:** `<out>/response.md`, `<out>/timing.json` (`total_tokens`, `duration_ms`, `cost_usd`, `exit_code`), `<out>/raw.json` and `<out>/stderr.log`. The runtime keeps `<out>` under the run's folder and records the run in the store.

Adapter entry point:

```text
run-agent.sh --agent-file <agents/name.md> --task-file <f> --project <dir> --model <id> --out <dir>
             [--skill-dir <dir>]... [--max-cost-usd <amount>] [--timeout-seconds <n>]
```

It copies the skills (never links them) into a fresh working folder for the run, gives the model read access to `--project`, allows only reading tools, loads no connectors and no user-level settings, and writes the files above. It exits 0 when the model answered, 1 otherwise.

## Why the model never acts

The trigger's data is written by strangers (comments, e-mails). A model that could run the publisher could be talked into publishing. So the model proposes; code decides and executes:

1. The model returns a proposal (a category, a language, a reply text).
2. The runtime writes the proposal's text to a file and runs the gate script with the approved policy; the gate is code, bound by hash to what the person approved.
3. Only a gate result of `auto` makes the runtime call the actuator, with the file the gate checked and an idempotency key. Anything else goes to the inbox with the gate's reasons.

## Records

- Every trigger item is an event (deduplicated by source and external id), claimed atomically, and ends `done`, `failed` or `to_inbox`.
- Every run: agent, event, start and end, status, exit code, cost, tokens, output folder.
- Every outward action: kind, idempotency key, target, payload hash, provider result.
- Every item for the person: the inbox, with the payload and its hash; the person approves or rejects it, and an approved item runs only if its hash still matches.

## Safety rules

- The runtime never publishes without a gate result of `auto` under an active approval, or an inbox item the person approved with a matching hash.
- A proposal block that is missing, malformed or has fields outside the task's shape sends the event to the inbox; the runtime never repairs a proposal.
- The daily cost cap stops new runs; pending events wait for the next day or for the person.
- Configuration holds paths and limits only; credentials come through `providers/secrets/resolver.py`.
- One tick at a time per project (a lock); the scheduler also refuses overlapping firings.
