# Proving a task done

## What counts as proof

| Check kind | Proof |
|------------|-------|
| a test file or test command | the command exits 0 and the named tests appear as passed in the output |
| a build command | exit 0 and the artifact named by the task exists (`ls` it) |
| an observable in the running app | a script or a test drives the app and asserts the observable; a screenshot alone is not proof |
| a repository invariant (a file is gone, a string never appears) | a `grep`/`find` with the expected empty result, quoted |
| a measurement (size, time) | the number, the command that produced it, and the threshold from the task |

## When the check cannot run here

- The tool is missing (no browser, no runner): install it if the project's `AGENTS.md` lists it; otherwise report the exact command for the user to run and mark the task `in-progress`, not `done`.
- The check needs credentials or network the environment lacks: same rule; never fake the result.

## Long or hanging checks

Run builds and generators under a timeout (for example a Python `subprocess.run(..., timeout=180)`); if the work finished (the artifact exists, the success line was printed) but the process did not exit, report a hang with the last output line and look for open handles in application code before blaming the tool.

## Flaky checks

- Run it three times. Three passes: done. Any failure: it is not flaky, it is failing; find the cause or report it.
- Never add retries, sleeps or `skip` to make a check pass.

## Before and after

Record the failing output before implementing and the passing output after. Both go in the report; the pair is the evidence that the change caused the pass.
