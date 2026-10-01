# Proof of concept: evals in a container (2026-10-01)

Phase 3 of `docs/architecture/plan-2026-10.md`. Question: can every eval run execute in one fixed container, both tiers with the same rights, with the network open only to the model provider? Answer: **yes**. What was built for the proof is the executor itself (`evals/executor.py`), not a throwaway.

## What was tried and what happened

| Question | Result |
|----------|--------|
| The strong runner authenticates without a login or a keychain (D5) | Yes: a long-lived token in the secret store, passed as an environment variable by name. The value is never on a command line. |
| The floor runner works in the container | Yes, with its provider key passed the same way. |
| Both tiers have the same rights | Yes. Each run is one container that sees the run folder (read-write), the adapters, the shared references and the skill (read-only). No home folder, no other checkout. Inside it every command is allowed; the strong adapter has a `container` mode for this, and the web tools still need `allow_web`. |
| A model finds the workbench by searching the disk | No: `find / -name AGENTS.md` returned nothing on both tiers; the contamination guard found nothing in 12 without-skill runs. |
| Egress only to the model provider (D6) | Yes: runs sit on an internal network whose only way out is a proxy with a list of hosts (`evals/container/proxy/allow.txt`). From a run, the two provider hosts answered; another host through the proxy, the same host without the proxy and a bare address were all refused. The floor runner also asks for two hosts it does not need (a model catalogue and a package registry); refused, with no effect on the run. |
| Setup commands and the fixture commit | Run in a container with no network and no secret. |
| A browser | The image's browser took a screenshot from a model's command. |
| Stopping | A stopped evaluation with four containers running left no container, no runner and no client process behind. |
| Start-up cost | Not measurable against a model run: a full run of one skill took the same time as on the host. |

## Scores, one skill, full run (2 cases, 3 runs, both tiers, with and without the skill)

| | Strong with | Strong without | Floor with | Floor without |
|---|---|---|---|---|
| Host, command rules (the record) | 0.81 | 0.44 | 0.93 | 0.43 |
| Host, sandbox (strong with only, not recorded) | 0.94 | | | |
| Container | 0.94 | 0.26 | 0.92 | 0.32 |

With the skill the scores are the ones the host gave once the strong tier stopped being denied commands. Without the skill both tiers score lower in the container: on the host the floor baseline of this skill was contaminated (it found the workbench by searching the disk) and both tiers could read a machine full of other material.

## The tolerance (D4)

Spread between the three runs of a case, with the skill: the strong tier's standard deviation over the six runs is 0.08, the floor tier's 0.13. The gate compares two means of six runs, so their difference moves by about 0.05 from noise alone. **Proposed: `strong_tolerance` 0.05**, to be approved by the maintainer; it stays 0 until then. It rests on one skill; revisit it when the 48 are measured.

## What changed in the repository

- `evals/executor.py`: builds and names the images, the internal network and the proxy after a hash of `evals/container/`; wraps a command in `docker run`; removes containers by name.
- `evals/container/`: the image (pinned language runtime, git, the package tools, a browser, the two runners) and the proxy.
- `evals/eval_run.py`: every model run, grading, setup command and fixture commit goes through the executor; a benchmark and a record name the environment (definition hash, image id).
- `evals/eval-gate.json`: `strong_pass_env`, and `measurement_version` 3 (the environment changed what a run measures).
- The strong adapter's `container` mode; the secret registered in the resolver and the secrets contract.

## Left for phase 4

- Host-only code in the adapters is now unused by evals (the strong adapter's sandbox settings, the floor adapter's throwaway home and keychain): remove it, and move the adapters' shared parts to one helper.
- The case preflight (`--check-cases`, which `validate.py` runs) still executes a case's setup commands on the host: it is a static check and writes no score, but it should not need the host either.
- On Linux a run keeps the caller's numeric user (`--user`); written, not yet run there. CI does not build the image.
- A case with `allow_web` gets the open network: written, not yet run.
- Cases tied to one operating system need a stand-in; dependencies a case installs must come from the image.
- The image is pinned by tags; pin the base by digest when it settles.
