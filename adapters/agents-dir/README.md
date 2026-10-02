# agents-dir adapter

Installs the selected pack of skills into `~/.agents/skills/`, the directory that Codex, Cursor, Cline, OpenCode, OpenClaw and most tools following the Agent Skills standard scan. Nothing is generated; each skill folder is symlinked (or copied with `--copy`).

```bash
bash adapters/agents-dir/install.sh                # pack "default", user-level
bash adapters/agents-dir/install.sh --pack all     # optional areas too
bash adapters/agents-dir/install.sh --project .    # project-level: ./.agents/skills
```

## Limitations

- Agents (`agents/`) are not installed by this adapter: agent formats differ per tool. Add a dedicated adapter when a tool's subagent format is needed.
- The shared references are installed beside the skills, in `<skills folder>/../shared/references` (a link, or a copy with `--copy`), so a skill's `../../shared/references/<file>` resolves by the installed path. The `shared` folder holds the installer's marker file; a `shared` folder the installer did not make is left alone and reported, and the run exits 1.
- One pack is installed at a time: installing a pack removes what an earlier pack installed and this one does not select (a dangling link to a renamed skill included), and `--uninstall` removes everything the installer made, whatever pack installed it.

## Evals

`eval_run.py` creates the case folder (`--cwd`) in a temporary folder outside the repository and moves it into `evals-workspace/` afterwards, so a model that walks up from it finds no workbench; the adapter only needs to locate itself by its own path, which it does. `run-prompt.sh` implements the eval contract with OpenCode (`opencode run`) by default, or any CLI through `RUN_PROMPT_CMD` (`{prompt_file}`, `{model}`, `{cwd}` placeholders, filled with shell-quoted values). Token counts are not reported. The skill under test and a case's dependencies (`--extra-skill-dir`) are copied into the case folder, never linked, so a run that approves every tool cannot edit the workbench; a case folder that already holds `.agents/`, `.opencode/` or `opencode.json` is refused. It runs only inside the eval container that `evals/eval_run.py` starts (the image sets `WB_EVAL_CONTAINER=1`; the script refuses to start without it), since the default runner approves every tool: the container is the boundary. The runner's provider key is named in `evals/eval-gate.json` (`floor_pass_env`) or with `eval_run.py --floor-pass-env`. No connectors or MCP servers load while the throwaway home is used (the default). Isolation caveat observed on the first run: the default runner also loads skills from the user-level skill directories of other tools, so a without-skill run is clean only if the workbench is not installed globally anywhere; check the transcript for the skill name.

## Floor model through OpenRouter

The floor model of the eval gate is `openrouter/deepseek/deepseek-v4.1-flash` since 2026-10-01 (it was `openrouter/deepseek/deepseek-v3.2`), set in `evals/eval-gate.json` with this adapter and the key variable `OPENROUTER_API_KEY`, so `eval_run.py --skill <name>` needs no model flag. The floor runs recorded before 2026-09-28 used `claude-haiku-4-5-20251001` (35 runs, through the claude-code adapter) and `openrouter/deepseek/deepseek-v3.2` (6 runs, through this adapter), read from `evals-workspace/*/iteration-*/benchmark.json` on the maintainer's machine. OpenCode had no stored credentials (`opencode auth list`: 0), so the OpenRouter key came from the shell environment. Since the containment of 2026-09-27, `eval_run.py` passes only an allowlisted environment and this adapter uses a throwaway home, so the key must be named explicitly:

```bash
# OPENROUTER_API_KEY from the environment settings, or stored once in the OS secret store:
#   uv run --with keyring==25.7.0 keyring set ai-workbench openrouter
# --pass-env reads it from there when it is not exported (contracts/secrets.md).
python3 evals/eval_run.py --skill <name>
# the same, spelled out (what evals/eval-gate.json supplies):
python3 evals/eval_run.py --skill <name> --harness claude-code --model <strong-id> \
  --floor-harness agents-dir --floor-model openrouter/deepseek/deepseek-v4.1-flash --floor-pass-env OPENROUTER_API_KEY
```

`--floor-pass-env` gives the key to the floor model's runs only; the strong model's runs and the grader never see it. The strong model and the grader run through the claude-code adapter on the user's own account (decided 2026-09-28).

Requires `opencode` on `PATH`.

Learned in a cloud session on 2026-09-28 (`opencode-ai@1.18.32`):
- Behind an outbound proxy, also name it: `--pass-env HTTPS_PROXY --pass-env NO_PROXY`, since the allowlisted environment drops it.
- Decided by the user on 2026-09-28: the OpenRouter key is for the floor model only. Claude models (the strong model and the grader) run through the claude-code adapter with the maintainer's own login (`--harness claude-code --model <claude-id> --floor-harness agents-dir --floor-model openrouter/deepseek/deepseek-v4.1-flash`); in a cloud session the CLI is already signed in, and `claude -p` works with only `PATH` and `HOME` from the allowlisted environment.
- The runner's web search (`--allow-web`) goes through a search service that limits concurrent use: with many runs searching at once it answers 429 and the model waits until the run times out (seen 2026-10-01 on a skill whose cases research the web). Measure such a skill alone, with `--jobs 2`.
- Three `eval_run.py` in parallel made `opencode run` fail within seconds with `UnknownError`, and those runs and their gradings were lost. The cause, found later, was a provider key that did not reach the runner, not the parallelism: runs share nothing, and several skills are evaluated at the same time within the provider's rate limits (`eval_run.py --help`, `--jobs`).

## Stopping a run

`run-prompt.sh` starts the runner in a session of its own, so the runner and everything it starts (model sessions, browsers, servers) form one process group. The group is ended, with TERM and then KILL after two seconds, when the runner returns and when the script itself gets TERM, INT or HUP (it then exits with 143). `eval_run.py` does the same one level up for every adapter call and setup command, on a timeout, on a signal and on any way out, so stopping an evaluation leaves no model session working. Before this, killing `eval_run.py` or passing a timeout left the sessions alive for many minutes. A process that moves itself into yet another session escapes this.

## Floor model on your own machine (Ollama)

Not wired to the eval container yet: evals now run in a container whose network reaches only the hosted providers, so a model served on the person's machine is not reachable from a run until the executor gains a route to it (backlog T12). What follows describes the adapter's side, which is unchanged.

A model id `ollama/<name>` runs a model served by Ollama on this machine (`http://127.0.0.1:11434`, or `RUN_PROMPT_OLLAMA_URL`). The adapter writes the provider entry into the run's throwaway home; nothing is added to the case folder and no key is needed.

Ollama's default context is too small for the runner's own prompt plus a skill, and the OpenAI-compatible endpoint the runner uses cannot set it per request. Create a variant with a larger context once, and use that name:

```bash
ollama pull <model>:<tag>
printf 'FROM <model>:<tag>\nPARAMETER num_ctx 32768\n' > Modelfile
ollama create <model>-32k -f Modelfile
```

Then run the floor tier one run at a time (a local model serves one request at a time; more jobs only queue and hit the timeout):

```bash
python3 evals/eval_run.py --skill <name> --harness <strong adapter> --model <strong-id> \
    --floor-model ollama/<model>-32k --floor-harness agents-dir --jobs 1 --timeout 1800
```

A local model is a measured goal, not the gate: a full run on it writes no record (the configured floor model is the hosted one) unless `--record-anyway`, and such a record reads `stale`.

Memory: the model's file size plus the context must fit in the machine's memory with room to spare; a variant that swaps is slower than the timeout allows.
