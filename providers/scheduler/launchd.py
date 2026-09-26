#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Scheduler provider for macOS: run one command once, at a set time, through launchd.

Sources (Apple documentation and manual pages, accessed 2026-09-26):
- launchd.plist(5): StartCalendarInterval (Month, Day, Hour, Minute in local time; a
  missed interval while the computer sleeps fires once on wake), ProgramArguments,
  WorkingDirectory, EnvironmentVariables, StandardOutPath, StandardErrorPath.
- launchctl(1): `bootstrap gui/<uid> <plist>` loads a user agent, `bootout gui/<uid>/<label>`
  unloads it and stops its processes.
- Creating Launch Daemons and Agents (Daemons and Services Programming Guide):
  https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html

What a job guarantees:
- The files named in the command file's "snapshot" are copied into the job folder at
  schedule time with their SHA-256; the command runs on the copies, so switching branches
  or editing the originals cannot change what runs. At run time the copies are hashed
  again and the command is refused if any differs.
- The command runs at most once: the job records its status before running, and removes
  its launchd agent afterwards. launchd fires a missed time on wake; a run later than the
  grace period is recorded as missed and does not run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

LABEL_PREFIX = "dev.ai-workbench.scheduler."
EARLY_TOLERANCE = timedelta(minutes=5)
DEFAULT_GRACE_MINUTES = 120
RUN_TIMEOUT_SECONDS = 600
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]{0,62}$")
RUN_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

EXIT_OK, EXIT_SERVICE, EXIT_USAGE, EXIT_NOT_CONFIGURED = 0, 1, 2, 3

HELP_EPILOG = """\
verbs:
  schedule  Run the command in --command-file once at --at. Needs --confirmed
            (or --dry-run).
  list      Print every job with its status (scheduled, running, done, failed,
            refused, missed, cancelled).
  cancel    Unload a scheduled job; needs --confirmed.
  run       Internal: what launchd calls at the set time.

command file (JSON):
  {
    "argv": ["uv", "run", "providers/publisher/linkedin.py", "publish", ...],
    "cwd": "/absolute/working/directory",
    "snapshot": ["/absolute/post.txt", "/absolute/image.png"],
    "grace_minutes": 120
  }
  argv[0] is resolved to an absolute path at schedule time. Every argv entry equal
  to a snapshot path is replaced by the job's copy of that file.

environment variables:
  SCHEDULER_HOME        job folders. Default: ~/Library/Application Support/ai-workbench/scheduler
  SCHEDULER_AGENTS_DIR  where plists go. Default: ~/Library/LaunchAgents
  SCHEDULER_LAUNCHCTL   tests only: replaces /bin/launchctl.
  SCHEDULER_NOTIFY      0 disables the macOS notification after a run.

output: JSON on stdout; diagnostics on stderr.
exit codes: 0 success, 1 provider error, 2 usage error, 3 not configured.

The computer must be on, awake and logged in at the set time (a user agent runs in the
login session). A time missed while asleep runs on wake, within the grace period.

examples:
  python3 providers/scheduler/launchd.py --check
  python3 providers/scheduler/launchd.py schedule --id launch-post \\
      --at 2026-09-29T09:00:00-03:00 --command-file job.json --dry-run
  python3 providers/scheduler/launchd.py list
  python3 providers/scheduler/launchd.py cancel --id launch-post --confirmed
"""


class ProviderError(Exception):
    def __init__(self, message: str, code: int = EXIT_SERVICE):
        super().__init__(message)
        self.code = code


def log(message: str) -> None:
    print(message, file=sys.stderr)


def now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: str) -> datetime:
    raw = value.strip()
    if raw.endswith(("Z", "z")):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def home() -> Path:
    override = os.environ.get("SCHEDULER_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / "Library" / "Application Support" / "ai-workbench" / "scheduler"


def agents_dir() -> Path:
    override = os.environ.get("SCHEDULER_AGENTS_DIR")
    return Path(override).expanduser() if override else Path.home() / "Library" / "LaunchAgents"


def launchctl() -> str:
    return os.environ.get("SCHEDULER_LAUNCHCTL", "/bin/launchctl")


def domain() -> str:
    return f"gui/{os.getuid()}"


def label(job_id: str) -> str:
    return LABEL_PREFIX + job_id


def plist_path(job_id: str) -> Path:
    return agents_dir() / f"{label(job_id)}.plist"


def job_dir(job_id: str) -> Path:
    return home() / job_id


def read_job(job_id: str) -> dict:
    path = job_dir(job_id) / "job.json"
    if not path.is_file():
        raise ProviderError(f"no job with id {job_id!r}", EXIT_USAGE)
    return json.loads(path.read_text(encoding="utf-8"))


def write_job(job: dict) -> None:
    folder = job_dir(job["id"])
    tmp = folder / "job.json.tmp"
    tmp.write_text(json.dumps(job, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, folder / "job.json")


def python_for_launchd() -> str:
    # The system interpreter survives cache cleaning and version-manager changes.
    return "/usr/bin/python3" if Path("/usr/bin/python3").exists() else sys.executable


def validate_id(job_id: str) -> str:
    if not ID_PATTERN.match(job_id or ""):
        raise ProviderError("--id must be lowercase letters, digits, dots and hyphens (at most 63)", EXIT_USAGE)
    return job_id


def load_command_file(path_arg: str) -> dict:
    path = Path(path_arg)
    if not path.is_file():
        raise ProviderError(f"--command-file not found: {path}", EXIT_USAGE)
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        raise ProviderError("--command-file is not valid JSON", EXIT_USAGE)
    argv = spec.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
        raise ProviderError("the command file needs argv: a non-empty list of strings", EXIT_USAGE)
    cwd = spec.get("cwd")
    if not cwd or not Path(cwd).is_absolute() or not Path(cwd).is_dir():
        raise ProviderError("the command file needs cwd: an existing absolute directory", EXIT_USAGE)
    snapshot = spec.get("snapshot", [])
    for item in snapshot:
        if not Path(item).is_absolute() or not Path(item).is_file():
            raise ProviderError(f"snapshot entries must be existing absolute files: {item}", EXIT_USAGE)
    names = [Path(item).name for item in snapshot]
    if len(set(names)) != len(names):
        raise ProviderError("snapshot files must have distinct names", EXIT_USAGE)
    grace = spec.get("grace_minutes", DEFAULT_GRACE_MINUTES)
    if not isinstance(grace, int) or grace < 0:
        raise ProviderError("grace_minutes must be a non-negative integer", EXIT_USAGE)
    return {"argv": argv, "cwd": cwd, "snapshot": snapshot, "grace_minutes": grace}


def resolve_program(program: str, cwd: str) -> str:
    if os.path.isabs(program):
        return program
    if os.sep in program:
        return str((Path(cwd) / program).resolve())
    found = shutil.which(program, path=os.environ.get("PATH", "") + os.pathsep + RUN_PATH)
    if not found:
        raise ProviderError(f"argv[0] {program!r} not found on PATH", EXIT_USAGE)
    return found


def build_plist(job: dict) -> dict:
    local = parse_iso(job["at"]).astimezone()
    folder = job_dir(job["id"])
    return {
        "Label": label(job["id"]),
        "ProgramArguments": [python_for_launchd(), str(Path(__file__).resolve()), "run", "--id", job["id"]],
        "StartCalendarInterval": {
            "Month": local.month, "Day": local.day, "Hour": local.hour, "Minute": local.minute,
        },
        "EnvironmentVariables": {
            "PATH": RUN_PATH,
            "SCHEDULER_HOME": str(home()),
            "SCHEDULER_AGENTS_DIR": str(agents_dir()),
        },
        "StandardOutPath": str(folder / "launchd.out.log"),
        "StandardErrorPath": str(folder / "launchd.err.log"),
    }


# --- verbs ---------------------------------------------------------------------


def cmd_schedule(args) -> int:
    job_id = validate_id(args.id)
    try:
        at = parse_iso(args.at)
    except (TypeError, ValueError):
        raise ProviderError(f"--at is not ISO-8601: {args.at}", EXIT_USAGE)
    if at <= now():
        raise ProviderError("--at is in the past", EXIT_USAGE)
    if at - now() > timedelta(days=330):
        raise ProviderError("--at is more than 330 days away; launchd calendar times repeat yearly", EXIT_USAGE)
    spec = load_command_file(args.command_file)
    if not args.dry_run and not args.confirmed:
        raise ProviderError(
            "refusing to schedule without --confirmed; the calling skill must pass its confirmation "
            "gate first (use --dry-run to preview)",
            EXIT_USAGE,
        )
    if (job_dir(job_id) / "job.json").exists():
        existing = read_job(job_id)
        if existing["status"] == "scheduled":
            raise ProviderError(f"job {job_id!r} is already scheduled; cancel it first", EXIT_USAGE)

    folder = job_dir(job_id)
    files = {}
    argv = [resolve_program(spec["argv"][0], spec["cwd"])] + spec["argv"][1:]
    for source in spec["snapshot"]:
        copy = folder / "files" / Path(source).name
        files[source] = {"copy": str(copy), "sha256": sha256(Path(source)), "bytes": Path(source).stat().st_size}
        argv = [str(copy) if a == source else a for a in argv]
    job = {
        "id": job_id,
        "label": label(job_id),
        "at": iso(at),
        "at_local": at.astimezone().isoformat(),
        "grace_minutes": spec["grace_minutes"],
        "argv": argv,
        "cwd": spec["cwd"],
        "files": files,
        "status": "scheduled",
        "created_at": iso(now()),
    }
    plist = build_plist(job)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "job": job, "plist_path": str(plist_path(job_id)), "plist": plist},
                         indent=2, ensure_ascii=False))
        return EXIT_OK

    (folder / "files").mkdir(parents=True, exist_ok=True)
    for source, entry in files.items():
        shutil.copyfile(source, entry["copy"])
        os.chmod(entry["copy"], 0o400)
        if sha256(Path(entry["copy"])) != entry["sha256"]:
            raise ProviderError(f"the copy of {source} does not match its hash")
    write_job(job)
    agents_dir().mkdir(parents=True, exist_ok=True)
    with plist_path(job_id).open("wb") as fh:
        plistlib.dump(plist, fh)
    subprocess.run([launchctl(), "bootout", f"{domain()}/{label(job_id)}"], capture_output=True)
    loaded = subprocess.run([launchctl(), "bootstrap", domain(), str(plist_path(job_id))],
                            capture_output=True, text=True)
    if loaded.returncode != 0:
        job["status"] = "failed"
        job["error"] = f"launchctl bootstrap exited {loaded.returncode}: {loaded.stderr.strip()}"
        write_job(job)
        plist_path(job_id).unlink(missing_ok=True)
        raise ProviderError(job["error"])
    print(json.dumps(job, indent=2, ensure_ascii=False))
    return EXIT_OK


def cmd_list(_args) -> int:
    jobs = []
    if home().is_dir():
        for folder in sorted(home().iterdir()):
            if (folder / "job.json").is_file():
                job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
                job["plist_present"] = plist_path(job["id"]).exists()
                jobs.append(job)
    print(json.dumps({"jobs": jobs}, indent=2, ensure_ascii=False))
    return EXIT_OK


def unload(job_id: str) -> None:
    plist_path(job_id).unlink(missing_ok=True)
    subprocess.run([launchctl(), "bootout", f"{domain()}/{label(job_id)}"], capture_output=True)


def cmd_cancel(args) -> int:
    job = read_job(validate_id(args.id))
    if not args.confirmed and not args.dry_run:
        raise ProviderError("refusing to cancel without --confirmed (use --dry-run to preview)", EXIT_USAGE)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "would_cancel": job}, indent=2, ensure_ascii=False))
        return EXIT_OK
    if job["status"] == "scheduled":
        job["status"] = "cancelled"
        job["finished_at"] = iso(now())
        write_job(job)
    unload(job["id"])
    print(json.dumps(job, indent=2, ensure_ascii=False))
    return EXIT_OK


def notify(title: str, message: str) -> None:
    if os.environ.get("SCHEDULER_NOTIFY", "1") == "0":
        return
    script = f"display notification {json.dumps(message)} with title {json.dumps(title)}"
    subprocess.run(["/usr/bin/osascript", "-e", script], capture_output=True)


def finish(job: dict, status: str, **fields) -> int:
    job.update(fields)
    job["status"] = status
    job["finished_at"] = iso(now())
    write_job(job)
    summary = fields.get("post_url") or fields.get("reason") or f"exit {fields.get('exit_code')}"
    notify(f"ai-workbench: {job['id']} {status}", summary)
    log(f"job {job['id']}: {status} ({summary})")
    # Unloading stops this process's launchd job, so it is the last thing done.
    unload(job["id"])
    return EXIT_OK if status == "done" else EXIT_SERVICE


def cmd_run(args) -> int:
    job = read_job(validate_id(args.id))
    if job["status"] != "scheduled":
        log(f"job {job['id']} is {job['status']}; nothing to run")
        unload(job["id"])
        return EXIT_OK
    at = parse_iso(job["at"])
    current = now()
    if current < at - EARLY_TOLERANCE:
        log(f"job {job['id']} fired at {iso(current)}, before its time {job['at']}; waiting")
        return EXIT_OK
    if current > at + timedelta(minutes=job["grace_minutes"]):
        return finish(job, "missed", reason=f"fired at {iso(current)}, after the {job['grace_minutes']}-minute grace")
    for source, entry in job["files"].items():
        copy = Path(entry["copy"])
        if not copy.is_file() or sha256(copy) != entry["sha256"]:
            return finish(job, "refused", reason=f"the copy of {Path(source).name} changed after scheduling")

    job["status"] = "running"
    job["started_at"] = iso(current)
    write_job(job)
    folder = job_dir(job["id"])
    try:
        done = subprocess.run(job["argv"], cwd=job["cwd"], capture_output=True, text=True,
                              timeout=RUN_TIMEOUT_SECONDS, env={**os.environ, "PATH": RUN_PATH})
    except (OSError, subprocess.TimeoutExpired) as exc:
        return finish(job, "failed", reason=f"{type(exc).__name__}: {exc}")
    (folder / "run.stdout.log").write_text(done.stdout, encoding="utf-8")
    (folder / "run.stderr.log").write_text(done.stderr, encoding="utf-8")
    fields = {"exit_code": done.returncode}
    try:
        output = json.loads(done.stdout)
        if isinstance(output, dict) and output.get("post_url"):
            fields["post_url"] = output["post_url"]
    except ValueError:
        pass
    return finish(job, "done" if done.returncode == 0 else "failed", **fields)


def cmd_check() -> int:
    if sys.platform != "darwin" and "SCHEDULER_LAUNCHCTL" not in os.environ:
        raise ProviderError("launchd exists only on macOS")
    if not Path(launchctl()).exists():
        raise ProviderError(f"launchctl not found at {launchctl()}")
    print(json.dumps({
        "ready": True,
        "jobs_dir": str(home()),
        "agents_dir": str(agents_dir()),
        "launchd_python": python_for_launchd(),
        "timezone": datetime.now().astimezone().tzname(),
    }, indent=2))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="launchd.py",
        description="Scheduler provider for macOS: runs one command once at a set time through launchd.",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("verb", nargs="?", choices=["schedule", "list", "cancel", "run"])
    parser.add_argument("--check", action="store_true", help="verify launchd is usable; no side effects")
    parser.add_argument("--id", help="job id: lowercase letters, digits, dots and hyphens")
    parser.add_argument("--at", help="ISO-8601 time with offset, e.g. 2026-09-29T09:00:00-03:00")
    parser.add_argument("--command-file", help="JSON file with argv, cwd, snapshot and grace_minutes")
    parser.add_argument("--dry-run", action="store_true", help="print the job and the plist; do nothing")
    parser.add_argument("--confirmed", action="store_true", help="required to schedule or cancel")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.check:
            return cmd_check()
        if args.verb == "schedule":
            if not args.id or not args.at or not args.command_file:
                raise ProviderError("schedule needs --id, --at and --command-file", EXIT_USAGE)
            return cmd_schedule(args)
        if args.verb == "list":
            return cmd_list(args)
        if args.verb in ("cancel", "run"):
            if not args.id:
                raise ProviderError(f"{args.verb} needs --id", EXIT_USAGE)
            return cmd_cancel(args) if args.verb == "cancel" else cmd_run(args)
        raise ProviderError("give a verb (schedule, list, cancel) or --check; see --help", EXIT_USAGE)
    except ProviderError as exc:
        log(f"error: {exc}")
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
