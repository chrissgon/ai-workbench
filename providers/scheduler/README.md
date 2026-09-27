# Scheduler providers

Implementations of the `scheduler` class. Interface: `providers/CONTRACT.md` (`schedule --at <ISO-8601> --command-file <f> [--approved <digest>]`, `list`, `cancel --id <id>`).

## macOS launchd (`launchd.py`)

Runs one command once, at a set time, as a launchd user agent. Standard library only; launchd calls it with `/usr/bin/python3`.

### What a job guarantees

- **What was approved is what runs.** `snapshot` is required, and every argument that names an existing file (bare or as `--flag=/path`, absolute or relative to `cwd`) must be in it, or the job is refused; paths the command only writes go in `outputs`. The files are copied into the job folder with their SHA-256 and the arguments are swapped for the copies. The program (`argv[0]`) and this runner are hashed too, and launchd calls a copy of the runner kept in the job folder. Editing the originals, switching branches or merging and deleting the branch changes nothing. At run time the copies, the program and the runner are hashed again; a mismatch records the job as `refused` and runs nothing. Directories (`cwd`, a folder argument) are not snapshotted: files read from them are not verified.
- **Fixed at approval.** The dry run prints an `approved` digest of everything above. The confirmed call must pass it back (`--confirmed --approved <digest>`); if anything changed since the dry run, it refuses and the gate has to show the new dry run.
- **At most once.** The job records `running` before the command starts and removes its agent afterwards; a second firing finds the status and exits.
- **Late means missed.** launchd fires a time missed during sleep on wake. Within `grace_minutes` (default 120) the command runs; after it, the job is recorded as `missed`.
- **A notification** reports every outcome (the post URL when the command prints one), and the job folder keeps `job.json` and the command's output.
- **Private files.** Job folders are 0700, `job.json`, logs and the plist 0600, the copies 0400. Scheduling an id whose job has finished moves the old folder to `.history/` in the jobs folder.
- **Bounded waits.** Every `launchctl` call times out after 30 seconds; a bootstrap that times out records the job as `failed`.

### Usage

```sh
python3 providers/scheduler/launchd.py --check
python3 providers/scheduler/launchd.py schedule --id <id> --at 2026-09-29T09:00:00-03:00 \
    --command-file job.json --dry-run      # prints the job and its "approved" digest
python3 providers/scheduler/launchd.py schedule --id <id> --at 2026-09-29T09:00:00-03:00 \
    --command-file job.json --confirmed --approved <digest>   # after the calling skill's gate
python3 providers/scheduler/launchd.py list
python3 providers/scheduler/launchd.py cancel --id <id> --confirmed
```

Command file:

```json
{
  "argv": ["uv", "run", "/abs/providers/publisher/linkedin.py", "publish", "--platform", "linkedin",
           "--text-file", "/abs/post.txt", "--media", "/abs/image.png",
           "--idempotency-key", "launch-post", "--confirmed"],
  "cwd": "/abs/ai-workbench",
  "snapshot": ["/abs/providers/publisher/linkedin.py", "/abs/post.txt", "/abs/image.png"],
  "grace_minutes": 120
}
```

Jobs live in `~/Library/Application Support/ai-workbench/scheduler/<id>/`, agents in `~/Library/LaunchAgents/dev.ai-workbench.scheduler.<id>.plist`.

### Requirements at run time

The Mac must be on and the user logged in (a locked screen is fine); a user agent runs in the login session, which is also what lets the publisher read its token from the login keychain. To wake a sleeping Mac, the user can run `sudo pmset schedule wake "MM/DD/YYYY HH:MM:SS"` a few minutes before.

### Rehearse before the real job

Schedule a job two minutes ahead whose command has no side effect (for the LinkedIn publisher, `linkedin.py --check`). The first real use did this and proved, from launchd rather than a terminal, that `uv` resolved, the keychain answered and the agent removed itself.

### Tests

`uv run --with pytest==9.1.1 pytest providers/scheduler/tests`: offline, with a fake `launchctl` (`SCHEDULER_LAUNCHCTL`, honoured only with `SCHEDULER_TEST=1`) and temporary job and agent folders.
