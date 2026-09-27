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
- Every file the command reads through its arguments is in the command file's "snapshot":
  an argument that names an existing file, bare or as --flag=/path (absolute or relative to
  cwd), and is not listed there makes the job refused. The files are copied into the job
  folder with their SHA-256 and the arguments are swapped for the copies, so switching
  branches or editing the originals cannot change what runs.
- The scheduled program (argv[0]) and this runner script are hashed too; the runner itself is
  copied into the job folder and launchd calls the copy.
- The hashes are fixed at approval: the dry run prints a digest of everything that will run,
  and the confirmed call must pass it back with --approved. At run time the copies, the
  program and the runner are hashed again and the command is refused if any differs.
- The command runs at most once: the job records its status before running, and removes
  its launchd agent afterwards. launchd fires a missed time on wake; a run later than the
  grace period is recorded as missed and does not run.
- Job folders are 0700 and the files written in them 0600 (copies 0400).
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
LAUNCHCTL_TIMEOUT_SECONDS = 30
NOTIFY_TIMEOUT_SECONDS = 10
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]{0,62}$")
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RUN_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
HISTORY = ".history"

EXIT_OK, EXIT_SERVICE, EXIT_USAGE, EXIT_NOT_CONFIGURED = 0, 1, 2, 3

HELP_EPILOG = """\
verbs:
  schedule  Run the command in --command-file once at --at. Run it first with
            --dry-run: it prints the job and its "approved" digest. After the
            calling skill's gate, run it again with --confirmed --approved <digest>;
            it refuses when anything changed since the dry run.
  list      Print every job with its status (scheduled, running, done, failed,
            refused, missed, cancelled).
  cancel    Unload a scheduled job; needs --confirmed.
  run       Internal: what launchd calls at the set time.

command file (JSON):
  {
    "argv": ["uv", "run", "/abs/providers/publisher/linkedin.py", "publish", ...],
    "cwd": "/absolute/working/directory",
    "snapshot": ["/abs/providers/publisher/linkedin.py", "/abs/post.txt"],
    "outputs": ["/abs/result.json"],
    "grace_minutes": 120
  }
  "snapshot" is required. Every argv entry after argv[0] that names an existing
  file, bare or as --flag=<path>, absolute or relative to cwd, must be listed in
  it (as an absolute path) and is replaced by the job's copy of that file; a file
  argument left out makes the job refused. "outputs" (optional) lists absolute
  paths the command writes and does not read; they are exempt. argv[0] is resolved to an absolute
  path at schedule time and hashed. Directories are not snapshotted: files the
  command reads from cwd or from a directory argument are not verified.

environment variables:
  SCHEDULER_HOME        job folders. Default: ~/Library/Application Support/ai-workbench/scheduler
  SCHEDULER_AGENTS_DIR  where plists go. Default: ~/Library/LaunchAgents
  SCHEDULER_TEST        1 enables test mode; required for SCHEDULER_LAUNCHCTL.
  SCHEDULER_LAUNCHCTL   tests only (with SCHEDULER_TEST=1): replaces /bin/launchctl.
  SCHEDULER_NOTIFY      0 disables the macOS notification after a run.

output: JSON on stdout; diagnostics on stderr.
exit codes: 0 success, 1 provider error, 2 usage error, 3 not configured.

The computer must be on, awake and logged in at the set time (a user agent runs in the
login session). A time missed while asleep runs on wake, within the grace period.

examples:
  python3 providers/scheduler/launchd.py --check
  python3 providers/scheduler/launchd.py schedule --id launch-post \\
      --at 2026-09-29T09:00:00-03:00 --command-file job.json --dry-run
  python3 providers/scheduler/launchd.py schedule --id launch-post \\
      --at 2026-09-29T09:00:00-03:00 --command-file job.json --confirmed --approved <digest>
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


def test_mode() -> bool:
    return os.environ.get("SCHEDULER_TEST") == "1"


def launchctl() -> str:
    override = os.environ.get("SCHEDULER_LAUNCHCTL")
    if override:
        if not test_mode():
            raise ProviderError("SCHEDULER_LAUNCHCTL is for tests only and needs SCHEDULER_TEST=1", EXIT_USAGE)
        return override
    return "/bin/launchctl"


def run_launchctl(*args: str) -> subprocess.CompletedProcess | None:
    """Run launchctl with a timeout; None when it timed out."""
    try:
        return subprocess.run([launchctl(), *args], capture_output=True, text=True,
                              timeout=LAUNCHCTL_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        log(f"launchctl {args[0]} timed out after {LAUNCHCTL_TIMEOUT_SECONDS} s")
        return None


def domain() -> str:
    return f"gui/{os.getuid()}"


def label(job_id: str) -> str:
    return LABEL_PREFIX + job_id


def plist_path(job_id: str) -> Path:
    return agents_dir() / f"{label(job_id)}.plist"


def job_dir(job_id: str) -> Path:
    return home() / job_id


def private_dir(path: Path) -> None:
    """Create path (and missing parents) as 0700 and make sure path itself is 0700."""
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def write_private(path: Path, data: bytes) -> None:
    """Write data to path atomically, readable by the owner only."""
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def read_job(job_id: str) -> dict:
    path = job_dir(job_id) / "job.json"
    if not path.is_file():
        raise ProviderError(f"no job with id {job_id!r}", EXIT_USAGE)
    return json.loads(path.read_text(encoding="utf-8"))


def write_job(job: dict) -> None:
    data = (json.dumps(job, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    write_private(job_dir(job["id"]) / "job.json", data)


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
    if "snapshot" not in spec:
        raise ProviderError("the command file needs snapshot: the list of files the command reads "
                            "([] only when no argument names a file)", EXIT_USAGE)
    snapshot = spec["snapshot"]
    if not isinstance(snapshot, list) or not all(isinstance(s, str) for s in snapshot):
        raise ProviderError("snapshot must be a list of absolute file paths", EXIT_USAGE)
    for item in snapshot:
        if not Path(item).is_absolute() or not Path(item).is_file():
            raise ProviderError(f"snapshot entries must be existing absolute files: {item}", EXIT_USAGE)
    outputs = spec.get("outputs", [])
    if not isinstance(outputs, list) or not all(isinstance(o, str) and Path(o).is_absolute() for o in outputs):
        raise ProviderError("outputs must be a list of absolute paths", EXIT_USAGE)
    names = [Path(item).name for item in snapshot]
    if len(set(names)) != len(names):
        raise ProviderError("snapshot files must have distinct names", EXIT_USAGE)
    grace = spec.get("grace_minutes", DEFAULT_GRACE_MINUTES)
    if not isinstance(grace, int) or grace < 0:
        raise ProviderError("grace_minutes must be a non-negative integer", EXIT_USAGE)
    return {"argv": argv, "cwd": cwd, "snapshot": snapshot, "outputs": outputs, "grace_minutes": grace}


def resolve_program(program: str, cwd: str) -> str:
    if os.path.isabs(program):
        found = program
    elif os.sep in program:
        found = str(Path(cwd) / program)
    else:
        found = shutil.which(program, path=os.environ.get("PATH", "") + os.pathsep + RUN_PATH)
        if not found:
            raise ProviderError(f"argv[0] {program!r} not found on PATH", EXIT_USAGE)
    resolved = Path(found).resolve()
    if not resolved.is_file():
        raise ProviderError(f"argv[0] {program!r} is not a file", EXIT_USAGE)
    return str(resolved)


def split_argument(arg: str) -> tuple[str, str]:
    """Split '--flag=value' into ('--flag=', 'value'); any other argument into ('', arg)."""
    if arg.startswith("-") and "=" in arg:
        flag, value = arg.split("=", 1)
        return flag + "=", value
    return "", arg


def argument_file(value: str, cwd: str) -> Path | None:
    """The resolved file an argument value names, or None when it names no existing file."""
    if not value:
        return None
    path = Path(value) if os.path.isabs(value) else Path(cwd) / value
    try:
        return path.resolve() if path.is_file() else None
    except OSError:
        return None


def snapshot_argv(argv: list[str], cwd: str, copies: dict[Path, str], outputs: set[Path]) -> list[str]:
    """Swap every file argument for its copy; refuse a file argument that has no copy."""
    out = []
    for arg in argv:
        prefix, value = split_argument(arg)
        target = argument_file(value, cwd)
        if target is None or (target in outputs and target not in copies):
            out.append(arg)
            continue
        if target not in copies:
            raise ProviderError(
                f"the argument {arg!r} names the file {target}, which is not in the command file's "
                "snapshot; add it so the job runs on a verified copy", EXIT_USAGE)
        out.append(prefix + copies[target])
    return out


def approval_digest(job: dict) -> str:
    """SHA-256 over everything that decides what runs; printed by the dry run, checked on --confirmed."""
    fields = {key: job[key] for key in ("id", "at", "grace_minutes", "argv", "cwd", "outputs", "program")}
    fields["files"] = {source: entry["sha256"] for source, entry in job["files"].items()}
    fields["runner"] = job["runner"]["sha256"]
    blob = json.dumps(fields, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def plan_job(job_id: str, at: datetime, spec: dict) -> dict:
    """The job as it will run, hashed from the current files; nothing is written."""
    folder = job_dir(job_id)
    files, copies = {}, {}
    for source in spec["snapshot"]:
        copy = folder / "files" / Path(source).name
        files[source] = {"copy": str(copy), "sha256": sha256(Path(source)), "bytes": Path(source).stat().st_size}
        copies[Path(source).resolve()] = str(copy)
    program = resolve_program(spec["argv"][0], spec["cwd"])
    outputs = {Path(o).resolve() for o in spec["outputs"]}
    argv = [program] + snapshot_argv(spec["argv"][1:], spec["cwd"], copies, outputs)
    runner = Path(__file__).resolve()
    job = {
        "id": job_id,
        "label": label(job_id),
        "at": iso(at),
        "at_local": at.astimezone().isoformat(),
        "grace_minutes": spec["grace_minutes"],
        "argv": argv,
        "cwd": spec["cwd"],
        "files": files,
        "outputs": spec["outputs"],
        "program": {"path": program, "sha256": sha256(Path(program))},
        "runner": {"source": str(runner), "copy": str(folder / "runner" / runner.name), "sha256": sha256(runner)},
        "status": "scheduled",
    }
    job["approved"] = approval_digest(job)
    return job


def build_plist(job: dict) -> dict:
    local = parse_iso(job["at"]).astimezone()
    folder = job_dir(job["id"])
    return {
        "Label": label(job["id"]),
        "ProgramArguments": [python_for_launchd(), job["runner"]["copy"], "run", "--id", job["id"]],
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


def archive_finished(job_id: str, existing: dict) -> str:
    """Move a finished job's folder to <home>/.history/ so the id can be scheduled again."""
    stamp = re.sub(r"[^0-9A-Za-z]", "", existing.get("finished_at") or existing.get("created_at") or iso(now()))
    target = home() / HISTORY / f"{job_id}-{stamp}"
    n = 1
    while target.exists():
        n += 1
        target = home() / HISTORY / f"{job_id}-{stamp}-{n}"
    private_dir(target.parent)
    os.replace(job_dir(job_id), target)
    return str(target)


def copy_verified(source: str, copy: Path, expected: str, mode: int) -> None:
    shutil.copyfile(source, copy)
    os.chmod(copy, mode)
    if sha256(copy) != expected:
        raise ProviderError(f"{source} changed after the dry run: its copy does not match the approved hash")


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
    if not args.dry_run and not DIGEST_PATTERN.match(args.approved or ""):
        raise ProviderError("--confirmed needs --approved <digest>: the digest the dry run printed", EXIT_USAGE)
    existing = None
    if (job_dir(job_id) / "job.json").exists():
        existing = read_job(job_id)
        if existing["status"] in ("scheduled", "running"):
            raise ProviderError(f"job {job_id!r} is {existing['status']}; cancel it or wait for it first", EXIT_USAGE)

    job = plan_job(job_id, at, spec)
    plist = build_plist(job)
    if args.dry_run:
        out = {"dry_run": True, "approved": job["approved"], "job": job,
               "plist_path": str(plist_path(job_id)), "plist": plist}
        if existing:
            out["replaces_finished_job"] = {"status": existing["status"], "moved_to": str(home() / HISTORY)}
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return EXIT_OK
    if args.approved != job["approved"]:
        raise ProviderError(
            "the job changed since the dry run (a file, the program, the runner or the command file): "
            "run --dry-run again and show the new payload before confirming", EXIT_USAGE)
    launchctl()  # refuse an untrusted launchctl override before writing anything

    private_dir(home())
    if existing:
        job["replaced"] = archive_finished(job_id, existing)
    folder = job_dir(job_id)
    if folder.exists() and not (folder / "job.json").exists():
        shutil.rmtree(folder)  # left by an interrupted schedule; it never held a job record
    private_dir(folder / "files")
    private_dir(folder / "runner")
    try:
        for source, entry in job["files"].items():
            copy_verified(source, Path(entry["copy"]), entry["sha256"], 0o400)
        copy_verified(job["runner"]["source"], Path(job["runner"]["copy"]), job["runner"]["sha256"], 0o500)
        if sha256(Path(job["program"]["path"])) != job["program"]["sha256"]:
            raise ProviderError(f"{job['program']['path']} changed after the dry run")
    except ProviderError:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    for name in ("launchd.out.log", "launchd.err.log"):
        write_private(folder / name, b"")
    job["created_at"] = iso(now())
    write_job(job)
    if not agents_dir().exists():
        private_dir(agents_dir())
    write_private(plist_path(job_id), plistlib.dumps(plist))
    run_launchctl("bootout", f"{domain()}/{label(job_id)}")
    loaded = run_launchctl("bootstrap", domain(), str(plist_path(job_id)))
    if loaded is None or loaded.returncode != 0:
        job["status"] = "failed"
        job["error"] = ("launchctl bootstrap timed out" if loaded is None
                        else f"launchctl bootstrap exited {loaded.returncode}: {loaded.stderr.strip()}")
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
    run_launchctl("bootout", f"{domain()}/{label(job_id)}")


def cmd_cancel(args) -> int:
    job = read_job(validate_id(args.id))
    if not args.confirmed and not args.dry_run:
        raise ProviderError("refusing to cancel without --confirmed (use --dry-run to preview)", EXIT_USAGE)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "would_cancel": job}, indent=2, ensure_ascii=False))
        return EXIT_OK
    launchctl()
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
    try:
        subprocess.run(["/usr/bin/osascript", "-e", script], capture_output=True, timeout=NOTIFY_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        pass


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


def changed_since_approval(job: dict) -> str | None:
    """Name what no longer matches its approved hash, or None when everything matches."""
    for source, entry in job["files"].items():
        copy = Path(entry["copy"])
        if not copy.is_file() or sha256(copy) != entry["sha256"]:
            return f"the copy of {Path(source).name} changed after scheduling"
    program = Path(job["program"]["path"])
    if not program.is_file() or sha256(program) != job["program"]["sha256"]:
        return f"the program {program} changed after scheduling"
    if sha256(Path(__file__).resolve()) != job["runner"]["sha256"]:
        return "the runner script changed after scheduling"
    return None


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
    if "program" not in job or "runner" not in job:
        return finish(job, "refused", reason="the job was scheduled without program and runner hashes; schedule it again")
    reason = changed_since_approval(job)
    if reason:
        return finish(job, "refused", reason=reason)

    job["status"] = "running"
    job["started_at"] = iso(current)
    write_job(job)
    folder = job_dir(job["id"])
    try:
        done = subprocess.run(job["argv"], cwd=job["cwd"], capture_output=True, text=True,
                              timeout=RUN_TIMEOUT_SECONDS, env={**os.environ, "PATH": RUN_PATH})
    except (OSError, subprocess.TimeoutExpired) as exc:
        return finish(job, "failed", reason=f"{type(exc).__name__}: {exc}")
    write_private(folder / "run.stdout.log", done.stdout.encode("utf-8"))
    write_private(folder / "run.stderr.log", done.stderr.encode("utf-8"))
    fields = {"exit_code": done.returncode}
    try:
        output = json.loads(done.stdout)
        if isinstance(output, dict) and output.get("post_url"):
            fields["post_url"] = output["post_url"]
    except ValueError:
        pass
    return finish(job, "done" if done.returncode == 0 else "failed", **fields)


def cmd_check() -> int:
    if sys.platform != "darwin" and not test_mode():
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
    parser.add_argument("--dry-run", action="store_true", help="print the job, its approved digest and the plist; do nothing")
    parser.add_argument("--confirmed", action="store_true", help="required to schedule or cancel")
    parser.add_argument("--approved", help="with schedule --confirmed: the digest the dry run printed")
    return parser


def main(argv: list[str] | None = None) -> int:
    os.umask(0o077)  # every file and folder this provider creates is private to the user
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
