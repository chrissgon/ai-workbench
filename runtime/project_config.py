#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The project's configuration of the runtime: <project>/docs/workbench/runtime.json, and its hash.

The file is written by the person who sets the project up and holds no secret (contracts/runtime.md). The
task runtime reads three keys the first runtime already defined, with the same meaning:

  "workbench"   the absolute path of the workbench checkout the runtime runs from (a reviewed revision)
  "data_dir"    an absolute folder outside every repository, for run folders and the run lock
  "store_db"    the absolute path of the store database (class store:runtime)

and ignores every key it does not know (the first runtime's "agent", "harness", "mailbox"... stay valid in
the same file). Keys reserved for later stages of the platform plan, read by nothing yet: "area_agents",
"protected_paths", "documents", "task_board".

The hash is the sha256 of the file's bytes. From stage 2 every operation compares it with the hash the person
accepted last (kept in the store) and refuses to act on a file that changed; stage 1 computes it and shows it.

Usage (a library):
  python3 runtime/project_config.py --help
  python3 runtime/project_config.py --project <dir>     print the configuration and its hash, as JSON

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

REL = "docs/workbench/runtime.json"
REQUIRED = ("workbench", "data_dir", "store_db")
RESERVED = ("area_agents", "protected_paths", "documents", "task_board")


class ConfigError(Exception):
    """The project is not configured for the runtime; the message says what is missing."""


def path(project: str) -> str:
    return os.path.join(project, *REL.split("/"))


def load(project: str) -> dict:
    """{"project", "path", "sha256", "workbench", "data_dir", "store_db", "raw"} of a project folder. The
    project folder must exist; each of the three paths must be absolute, and data_dir and store_db must lie
    outside the project and outside the workbench checkout (work data never sits in a repository)."""
    project = os.path.realpath(project)
    if not os.path.isdir(project):
        raise ConfigError(f"{project} is not a folder")
    file = path(project)
    try:
        with open(file, "rb") as f:
            data = f.read()
        raw = json.loads(data.decode("utf-8"))
    except OSError:
        raise ConfigError(f"{file} not found: the project is not configured for the runtime (see runtime/README.md)") from None
    except ValueError as e:
        raise ConfigError(f"{file} is not valid JSON: {e}") from None
    if not isinstance(raw, dict):
        raise ConfigError(f"{file} must hold a JSON object")
    out = {"project": project, "path": file, "sha256": hashlib.sha256(data).hexdigest(), "raw": raw}
    for key in REQUIRED:
        value = raw.get(key)
        if not isinstance(value, str) or not value or not os.path.isabs(value):
            raise ConfigError(f"runtime.json needs {key}: an absolute path")
        out[key] = os.path.realpath(value)
    for key in ("data_dir", "store_db"):
        for inside, what in ((project, "the project"), (out["workbench"], "the workbench checkout")):
            if out[key] == inside or out[key].startswith(inside + os.sep):
                raise ConfigError(f"runtime.json {key} is inside {what}: work data lives outside every repository")
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] != "--project":
        print(__doc__.strip(), file=sys.stdout if argv in (["--help"], ["-h"]) else sys.stderr)
        return 0 if argv in (["--help"], ["-h"]) else 2
    try:
        cfg = load(argv[1])
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 3
    print(json.dumps({key: cfg[key] for key in ("project", "path", "sha256", *REQUIRED)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
