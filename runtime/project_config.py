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
the same file). "area_agents" is read by runtime/plan.py (the packs in scope).

It also reads "task_board" and "documents" (stage 3), each an object or absent (None):

  "task_board": {"provider": "local", "dir": "/abs/path/board"}
  "task_board": {"provider": "<another implementation>", "expires": "YYYY-MM-DD", ...}

"provider" is an implementation shipped in the class's folder of the workbench the file names
(integration:issue-tracker for the board, integration:documents for the documents, by providers/resolve.py); for
"local", "dir" is an absolute folder that is neither inside the project's docs/ (the path rule would call an item a
document) nor inside the workbench checkout; any other provider has "expires", a date YYYY-MM-DD, after which the
runtime writes nothing to it. Every other key is the implementation's, passed on untouched. These objects are the
bounds of what the runtime writes to a platform: they are inside the file whose hash the person accepts.

It also reads "protected_paths" (a list of path globs; absent means none): stage 2 asks it one question only,
whether a glob matches AGENTS.md (runtime/workcopy.py, limit L5).

It also reads "dependencies" (stage 4; absent means none): the project's dependency sets, each installed by code
from a recipe of the closed table of runtime/deps.py, checked there (deps.declared()):

  "dependencies": [{"recipe": "python-requirements", "file": ".workbench-local/requirements-dev.txt"}]

The hash is the sha256 of the file's bytes. Every operation compares it with the hash the person accepted last
(kept in the store's cursor ACCEPTED, written only by ops.accept_config) and refuses to act on a file that
changed. Nothing in this module reads the store.

Usage (a library):
  python3 runtime/project_config.py --help
  python3 runtime/project_config.py --project <dir>     print the configuration and its hash, as JSON

Standard library only. Runs on Python 3.9.
"""
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deps  # noqa: E402  (the same folder: the recipes and the check of the key "dependencies")

REL = "docs/workbench/runtime.json"
REQUIRED = ("workbench", "data_dir", "store_db")
ACCEPTED = "config:accepted-sha256"  # the store's cursor that holds the hash the person accepted last
PLATFORM_KEYS = {"task_board": "integration:issue-tracker", "documents": "integration:documents"}


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
    protected = raw.get("protected_paths", [])
    if not isinstance(protected, list) or not all(isinstance(p, str) and p.strip() for p in protected):
        raise ConfigError("runtime.json protected_paths must be a list of path globs")
    out["protected_paths"] = list(protected)
    try:
        out["dependencies"] = deps.declared(raw)
    except deps.DepsError as e:
        raise ConfigError(e.reason) from None
    for key, cls in PLATFORM_KEYS.items():
        out[key] = _platform(raw.get(key), key, cls, project, out["workbench"])
    return out


def _implementations(workbench: str, cls: str) -> list:
    """The implementations shipped for a class in the workbench checkout, by its providers/resolve.py."""
    path = os.path.join(workbench, "providers", "resolve.py")
    name = "workbench_config_resolve"
    module = sys.modules.get(name)
    if module is None or getattr(module, "__file__", None) != path:
        if not os.path.isfile(path):
            raise ConfigError(f"the workbench {workbench} has no providers/resolve.py")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module.implementations(cls, root=workbench)


def _platform(value, key: str, cls: str, project: str, workbench: str):
    """A task_board or documents object, checked (see the module's text); None when absent."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ConfigError(f"runtime.json {key} must be an object")
    shipped = _implementations(workbench, cls)
    provider = value.get("provider")
    if provider not in shipped:
        raise ConfigError(f"runtime.json {key}.provider must be one of {', '.join(shipped) or 'none: no provider is shipped'}")
    if provider == "local":
        folder = value.get("dir")
        if not isinstance(folder, str) or not os.path.isabs(folder):
            raise ConfigError(f"runtime.json {key}.dir must be an absolute path")
        folder = os.path.realpath(folder)
        for inside, what in ((os.path.join(project, "docs"), "the project's docs/ folder"),
                             (workbench, "the workbench checkout")):
            if folder == inside or folder.startswith(inside + os.sep):
                raise ConfigError(f"runtime.json {key}.dir is inside {what}")
    else:
        try:
            datetime.date.fromisoformat(str(value.get("expires")))
        except ValueError:
            raise ConfigError(f"runtime.json {key}.expires must be a date YYYY-MM-DD") from None
        if not isinstance(value.get("expires"), str) or len(value["expires"]) != 10:
            raise ConfigError(f"runtime.json {key}.expires must be a date YYYY-MM-DD")
    return dict(value)


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
