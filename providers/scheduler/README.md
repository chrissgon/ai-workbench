# Scheduler providers

Implementations of the `scheduler` class. Interface: `providers/CONTRACT.md` (`schedule (--at <ISO-8601> | --every <minutes>) --command-file <f> [--approved <digest>]`, `list`, `cancel --id <id>`).

## macOS launchd (`launchd.py`)

Runs a command as a launchd user agent, once at a set time (`--at`) or every N minutes (`--every`, a recurring job). Standard library only; launchd calls it with `/usr/bin/python3`.

### What a job guarantees

- **What was approved is what runs.** `snapshot` is required, and every argument that names an existing file (bare or as `--flag=/path`, absolute or relative to `cwd`) must be in it, or the job is refused; paths the command only writes go in `outputs`. The files are copied into the job folder with their SHA-256 and the arguments are swapped for the copies. The program (`argv[0]`) and this runner are hashed too, and launchd calls a copy of the runner kept in the job folder. Editing the originals, switching branches or merging and deleting the branch changes nothing. At run time the copies, the program and the runner are hashed again; a mismatch records the job as `refused` and runs nothing. Directories (`cwd`, a folder argument) are not snapshotted: files read from them are not verified.
- **Fixed at approval.** The dry run prints an `approved` digest of everything above. The confirmed call must pass it back (`--confirmed --approved <digest>`); if anything changed since the dry run, it refuses and the gate has to show the new dry run.
- **At most once.** The job records `running` before the command starts and removes its agent afterwards; a second firing finds the status and exits.
- **Late means missed.** launchd fires a time missed during sleep on wake. Within `grace_minutes` (default 120) the command runs; after it, the job is recorded as `missed`.
- **A notification** reports every outcome (the post URL when the command prints one), and the job folder keeps `job.json` and the command's output.
- **Private files.** Job folders are 0700, `job.json`, logs and the plist 0600, the copies 0400. Scheduling an id whose job has finished moves the old folder to `.history/` in the jobs folder.
- **Bounded waits.** Every `launchctl` call times out after 30 seconds; a bootstrap that times out records the job as `failed`.

### Recurring jobs (`--every`)

`schedule --id <id> --every <minutes> --command-file <f> (--dry-run | --confirmed --approved <digest>)`, with `--every` from 5 to 1440 and never together with `--at`. The plist carries `StartInterval` (the minutes in seconds) and no `StartCalendarInterval`. Everything above about snapshots, hashes and the approved digest holds; the digest covers `every_minutes` and `timeout_minutes` instead of `at` and `grace_minutes`, and `job.json` has `"kind": "recurring"` (a one-shot job has no `kind`).

- **Re-verified at every firing.** The copies, the program and the runner are hashed again each time. A mismatch records the firing as `refused`, marks the job `refused` and unloads it: a recurring job that stopped matching its approval does not fire again. Schedule it again, through the dry run and the gate, to resume. The program is the resolved `argv[0]`: when it is an interpreter from a package manager, upgrading the interpreter refuses the job the same way.
- **No overlap.** A firing takes `run.lock` in the job folder (an `flock` plus the holder's PID). A firing that finds it held records `skipped-overlap` and exits. The kernel drops the lock when its holder dies, so a lock left by a runner that died is stale: the next firing takes it over and records `stale_lock_pid`.
- **Bounded firings.** `timeout_minutes` in the command file (default 30, 1 to 240) bounds each firing. The command runs in its own process group; past the limit the group gets SIGTERM, then SIGKILL 5 seconds later, and the firing is recorded as `failed` with a reason starting `timeout`. If launchd stops the runner (a `cancel` during a firing), the runner kills the group the same way and records `failed`.
- **A log of firings.** Each firing appends one JSON line to `runs.jsonl` in the job folder: `started_at`, `ended_at`, `status` (`done`, `failed`, `refused`, `skipped-overlap`), `exit_code`, `reason` when there is one, and `stdout_tail` and `stderr_tail`, the last 4 kB of each. The file is 0600; past 4 MB it moves to `runs.1.jsonl` (replacing the older one). `list` shows each recurring job's `every_minutes` and `last_run` (its last firing without the tails).
- **Notifications on trouble only.** A `refused` firing notifies, and so does a `failed` one whose previous firing did not fail; a job that keeps failing notifies once until it recovers.
- **`cancel --id <id> --confirmed`** unloads it and records `cancelled`, as for a one-shot job.

What launchd does with the interval, from `launchd.plist(5)` (man page dated 30 July 2019, read with `man 5 launchd.plist` on macOS 27.0.1 on 2026-09-29):

- `StartInterval` "causes the job to be started every N seconds". `RunAtLoad` defaults to false, so the first firing comes one interval after `bootstrap`, and after a login, one interval after the agent loads from `~/Library/LaunchAgents`.
- **Sleep:** an interval firing due while the system is asleep "will be missed due to shortcomings in kqueue(3)". The coalescing into one firing on wake that the man page describes belongs to `StartCalendarInterval`, not to `StartInterval`. The provider adds no catch-up: the next firing is the next interval launchd delivers.
- **Overlap:** a firing due while the job still runs is missed by launchd itself; the lock covers any other way the runner is started twice.

A command file for the agent runtime's tick:

```json
{
  "argv": ["python3", "/abs/ai-workbench/scripts/runtime.py", "tick",
           "--project", "/abs/project", "--agent", "social-manager"],
  "cwd": "/abs/project",
  "snapshot": ["/abs/ai-workbench/scripts/runtime.py"],
  "timeout_minutes": 30
}
```

The job runs the copy of `runtime.py` kept in its folder, so whatever that script finds next to itself (sibling modules, the workbench root) has to be in the snapshot too or passed as an argument; a folder argument such as `--project` is not snapshotted or verified.

### Usage

```sh
python3 providers/scheduler/launchd.py --check
python3 providers/scheduler/launchd.py schedule --id <id> --at 2026-09-29T09:00:00-03:00 \
    --command-file job.json --dry-run      # prints the job and its "approved" digest
python3 providers/scheduler/launchd.py schedule --id <id> --at 2026-09-29T09:00:00-03:00 \
    --command-file job.json --confirmed --approved <digest>   # after the calling skill's gate
python3 providers/scheduler/launchd.py schedule --id <id> --every 15 --command-file tick.json --dry-run
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
  "snapshot": ["/abs/providers/publisher/linkedin.py", "/abs/providers/secrets/resolver.py",
               "/abs/post.txt", "/abs/image.png"],
  "grace_minutes": 120
}
```

A provider reads its credential through `providers/secrets/resolver.py`; the job runs a copy of the provider from its own folder, so the resolver goes into the snapshot too, and the copy finds it next to itself. A job scheduled without it fails at run time with a message that names the snapshot. Jobs scheduled before 2026-09-28 hold a copy of the provider from before the resolver and run as they are.

Jobs live in `~/Library/Application Support/ai-workbench/scheduler/<id>/`, agents in `~/Library/LaunchAgents/dev.ai-workbench.scheduler.<id>.plist`.

### Requirements at run time

The Mac must be on and the user logged in (a locked screen is fine); a user agent runs in the login session, which is also what lets the publisher read its token from the login keychain. To wake a sleeping Mac, the user can run `sudo pmset schedule wake "MM/DD/YYYY HH:MM:SS"` a few minutes before.

### Rehearse before the real job

Schedule a job two minutes ahead whose command has no side effect (for the LinkedIn publisher, `linkedin.py --check`). The first real use did this and proved, from launchd rather than a terminal, that `uv` resolved, the keychain answered and the agent removed itself.

### Tests

`uv run --with pytest==9.1.1 pytest providers/scheduler/tests`: offline, with a fake `launchctl` (`SCHEDULER_LAUNCHCTL`, honoured only with `SCHEDULER_TEST=1`) and temporary job and agent folders. `test_launchd_recurring.py` covers `--every`; its timeout test shortens the minute in-process instead of adding an environment override.
