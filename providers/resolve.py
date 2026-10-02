#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Resolve a requirement class to the provider script that satisfies it.

This is the one place that turns a class from contracts/environment.md (`scheduler`,
`publisher:linkedin`, `integration:vcs`) into a script under providers/. Skills, the agent
runtime and scripts/doctor.py all ask here; none of them names an implementation.

Usage:
  python3 providers/resolve.py --class <class> [--json] [--root <workbench root>]
  python3 providers/resolve.py --list [--root <workbench root>]
  python3 providers/resolve.py --help

  --class <class>  print the absolute path of the provider script chosen for the class
                   (with --json: class, implementation, path, source, variables)
  --list           print, as JSON, every class with its folder, its variables, the
                   implementations shipped and the one that resolves now
  --root <path>    the workbench checkout to look in, instead of WORKBENCH_ROOT

How a class maps to a folder (providers/CONTRACT.md):
  a          -> providers/a/                  scheduler -> providers/scheduler/
  a:b        -> providers/a/                  publisher:linkedin -> providers/publisher/
  integration:<service> -> providers/<service>/   integration:vcs -> providers/vcs/
An implementation is providers/<folder>/<name>.py; helpers next to it (auth.py) are not one.
A sub-class written as a placeholder (`publisher:<platform>`) means "any": only the class is used.

How the implementation is chosen, first match wins:
  0. An implementation the caller names explicitly (the function's `implementation` argument;
     the runtime passes what a project's runtime.json names). Not available on the command line.
  1. The environment: <CLASS>_<SUBCLASS>_PROVIDER, then <CLASS>_PROVIDER (PUBLISHER_LINKEDIN_PROVIDER,
     then PUBLISHER_PROVIDER; a hyphen becomes "_"). integration:<service> uses only the first
     form (INTEGRATION_VCS_PROVIDER): one integration's provider never serves another.
  2. The platform default, where the class has one and that implementation is shipped:
     scheduler is launchd on macOS and systemd on Linux.
  3. The only implementation, when the class's folder ships exactly one.
Otherwise nothing resolves (exit 3): the message names the variable to set and the choices.
A name from the environment or the caller is accepted only when it is an implementation shipped
in the class's folder; it is never used as a path.

environment variables:
  WORKBENCH_ROOT            the workbench checkout a project uses (an absolute path). Default:
                            the checkout this script is in.
  <CLASS>[_<SUBCLASS>]_PROVIDER   the implementation of a class, as above.

output: the path on stdout (JSON with --json or --list); diagnostics on stderr.
exit codes: 0 resolved, 2 usage error or unknown class, 3 nothing resolves.
Standard library only. Runs on the system interpreter (Python 3.9): the scheduled runtime
imports it (providers/CONTRACT.md, "Python version").
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT_VARIABLE = "WORKBENCH_ROOT"
NAME = re.compile(r"[a-z0-9][a-z0-9-]*")
PLACEHOLDER = re.compile(r"<[^<>]*>")
NOT_IMPLEMENTATIONS = {"auth"}  # helpers that live next to providers (providers/CONTRACT.md)
# Every class of contracts/environment.md. True: the class always has a sub-class.
HEADS = {"integration": True, "search": True, "generator": True, "publisher": True,
         "mailer": False, "mailbox": False, "scheduler": False, "store": False}
LISTED = ["generator:image", "generator:video", "integration:design-tool", "integration:issue-tracker",
          "integration:vcs", "mailbox", "mailer", "publisher:<platform>", "scheduler", "search:web", "store"]
# Documented defaults per platform (sys.platform prefix -> implementation).
PLATFORM_DEFAULTS = {"scheduler": {"darwin": "launchd", "linux": "systemd"}}

EXIT_OK, EXIT_USAGE, EXIT_UNRESOLVED = 0, 2, 3


class UnknownClass(ValueError):
    """The text is not a requirement class of contracts/environment.md."""
    code = EXIT_USAGE


class Unresolved(LookupError):
    """The class is known and no implementation can be chosen for it."""
    code = EXIT_UNRESOLVED


def split_class(cls: str) -> tuple[str, str | None]:
    """("publisher", "linkedin") for publisher:linkedin; the sub-class is None when absent or a placeholder."""
    parts = str(cls).split(":")
    head = parts[0]
    if len(parts) > 2 or head not in HEADS:
        raise UnknownClass(f"unknown class {cls!r}; known: {', '.join(LISTED)}")
    sub = parts[1] if len(parts) == 2 else None
    if sub is not None and PLACEHOLDER.fullmatch(sub):
        sub = None
    if sub is not None and not NAME.fullmatch(sub):
        raise UnknownClass(f"unknown class {cls!r}: the sub-class must be lowercase letters, digits and hyphens")
    if head == "integration" and sub is None:
        raise UnknownClass(f"unknown class {cls!r}: an integration names its service, for example integration:vcs")
    return head, sub


def folder(cls: str) -> str:
    """The folder under providers/ for a class: a and a:b -> a, integration:<service> -> <service>."""
    head, sub = split_class(cls)
    return sub if head == "integration" else head


def variables(cls: str) -> list[str]:
    """The environment variables that select the implementation, most specific first."""
    head, sub = split_class(cls)

    def key(parts):
        return "_".join(parts).upper().replace("-", "_") + "_PROVIDER"

    names = [key([head, sub])] if sub else []
    if head != "integration":  # integration:<service> classes are unrelated services: no shared fallback
        names.append(key([head]))
    return names


def workbench_root(root=None, env=None) -> Path:
    """The workbench checkout: the argument, else WORKBENCH_ROOT, else the checkout this file is in."""
    env = os.environ if env is None else env
    if root:
        return Path(root).expanduser().resolve()
    if env.get(ROOT_VARIABLE):
        path = Path(env[ROOT_VARIABLE]).expanduser()
        if not path.is_absolute():
            raise Unresolved(f"{ROOT_VARIABLE} must be an absolute path, not {env[ROOT_VARIABLE]!r}")
        return path.resolve()
    return Path(__file__).resolve().parent.parent


def implementations_in(folder_name: str, root=None, env=None) -> list[str]:
    """Implementation names in providers/<folder_name>/: <name>.py files, helpers excluded."""
    if not NAME.fullmatch(str(folder_name)):
        return []
    base = workbench_root(root, env) / "providers" / folder_name
    if not base.is_dir():
        return []
    return sorted(p.stem for p in base.glob("*.py")
                  if p.is_file() and NAME.fullmatch(p.stem) and p.stem not in NOT_IMPLEMENTATIONS)


def implementations(cls: str, root=None, env=None) -> list[str]:
    """Implementation names shipped for a class."""
    return implementations_in(folder(cls), root, env)


def from_environment(cls: str, env=None) -> tuple[str | None, str | None]:
    """(variable, value) of the first selection variable that is set, or (None, None)."""
    env = os.environ if env is None else env
    for name in variables(cls):
        if env.get(name):
            return name, env[name]
    return None, None


def resolve(cls: str, root=None, env=None, platform=None, implementation=None) -> dict:
    """Choose the provider script for a class. Returns class, implementation, path, source, variables.

    source is one of: configuration (the caller's `implementation`), environment, platform-default,
    only-implementation. Raises UnknownClass (not a class) or Unresolved (nothing to choose).
    """
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    names = variables(cls)  # raises UnknownClass first
    base = workbench_root(root, env) / "providers" / folder(cls)
    shipped = implementations(cls, root, env)

    def chosen(name: str, source: str, variable=None) -> dict:
        return {"class": cls, "implementation": name, "path": str(base / f"{name}.py"), "source": source,
                "variable": variable, "variables": names}

    def checked(name: str, origin: str) -> str:
        if name not in shipped:
            raise Unresolved(f"{name!r} (from {origin}) is not a provider of {cls} "
                             f"(providers/{folder(cls)}/); shipped: {shipped}")
        return name

    if implementation is not None:
        return chosen(checked(str(implementation), "the caller's configuration"), "configuration")
    variable, value = from_environment(cls, env)
    if value:
        return chosen(checked(value, variable), "environment", variable)
    for prefix, name in PLATFORM_DEFAULTS.get(split_class(cls)[0], {}).items():
        if platform.startswith(prefix) and name in shipped:
            return chosen(name, "platform-default")
    if len(shipped) == 1:
        return chosen(shipped[0], "only-implementation")
    if not shipped:
        raise Unresolved(f"no provider is shipped for {cls} (providers/{folder(cls)}/ has none); "
                         f"a provider added there is selected with {names[0]}")
    raise Unresolved(f"{cls} has several providers and none is selected: set {names[0]} to one of {shipped}")


def provider_path(cls: str, **kw) -> Path:
    """The path of the provider script for a class (see resolve)."""
    return Path(resolve(cls, **kw)["path"])


def secret_resolver(root=None, env=None) -> Path:
    """The secret resolver every provider reads credentials through (contracts/secrets.md). Not a class."""
    return workbench_root(root, env) / "providers" / "secrets" / "resolver.py"


def listing(root=None, env=None, platform=None) -> dict:
    rows = []
    for cls in LISTED:
        row = {"class": cls, "folder": f"providers/{folder(cls)}/", "variables": variables(cls),
               "implementations": implementations(cls, root, env), "resolves": None, "source": None, "note": None}
        try:
            got = resolve(cls, root=root, env=env, platform=platform)
            row.update(resolves=got["implementation"], source=got["source"], path=got["path"])
        except Unresolved as e:
            row["note"] = str(e)
        rows.append(row)
    return {"root": str(workbench_root(root, env)), "root_variable": ROOT_VARIABLE, "classes": rows}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--class", dest="cls", metavar="<class>")
    p.add_argument("--list", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--root", metavar="<path>")
    a = p.parse_args(argv)
    if bool(a.cls) == bool(a.list):
        print("error: give exactly one of --class <class> and --list. See --help.", file=sys.stderr)
        return EXIT_USAGE
    try:
        if a.list:
            print(json.dumps(listing(root=a.root), indent=1))
            return EXIT_OK
        got = resolve(a.cls, root=a.root)
    except (UnknownClass, Unresolved) as e:
        print(f"error: {e}", file=sys.stderr)
        return e.code
    print(json.dumps(got, indent=1) if a.json else got["path"])
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
