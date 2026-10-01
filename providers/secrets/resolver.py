#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["keyring==25.7.0"]
# ///
"""One way to find the workbench's secrets, the same on a laptop, in a cloud session and in CI.

Every script asks for a secret by name; the resolver looks in the same places, in the same order:
  1. environment variables: the name, then its aliases (a cloud environment's settings, CI secrets,
     or an export in the shell);
  2. the OS secret store (keyring): service "ai-workbench", the username listed below.
The first non-empty value wins. Values are never printed, logged or written, not even partially.
Adding a backend (a password manager) means adding one lookup function to BACKENDS; callers do
not change.

Usage:
  python3 providers/secrets/resolver.py --list [--json]
  python3 providers/secrets/resolver.py --check <NAME>

  --list    every registered secret: purpose, minimum permission, readers, whether it is found
            and where (environment or store), and how to set it; never the value
  --check   exit 0 when <NAME> is found, 3 when not, 2 when <NAME> is not registered
  --json    machine-readable output for --list
  --help    this text

Setting a secret:
  cloud session  the environment's settings, as an environment variable named like the secret
  CI             a repository secret, mapped to an environment variable of the same name in the
                 workflow (env: NAME: ${{ secrets.NAME }})
  local          uv run --with keyring==25.7.0 keyring set ai-workbench <username>
                 (typed at a hidden prompt, never on the command line), or an export in the shell

Without the keyring package (plain python3), the store is reported as unavailable and only the
environment is read. Exit codes: 0 ok, 2 usage error, 3 not found.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field

SERVICE = "ai-workbench"
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3


@dataclass(frozen=True)
class Secret:
    name: str
    purpose: str
    permission: str
    readers: tuple[str, ...]
    store_username: str | None = None
    aliases: tuple[str, ...] = field(default_factory=tuple)
    note: str = ""
    set_local: str = ""  # how to store it locally when not with `keyring set`


REGISTRY: dict[str, Secret] = {s.name: s for s in (
    Secret("VCS_GITHUB_TOKEN",
           "read (and, with a separate token, dismiss) Dependabot alerts",
           "fine-grained token, only the repositories concerned: \"Dependabot alerts: Read-only\" "
           "(\"Read and write\" only in the separate token used to dismiss)",
           ("providers/vcs/github.py", ".github/workflows/dependabot-alerts.yml"),
           store_username="github", aliases=("GITHUB_TOKEN",),
           note="GITHUB_TOKEN is read last: a harness or CI may set its own, with other permissions"),
    Secret("LINKEDIN_ACCESS_TOKEN",
           "publish posts on LinkedIn",
           "OAuth scopes openid, profile and w_member_social (providers/publisher/auth.py)",
           ("providers/publisher/linkedin.py",),
           store_username="publisher-linkedin",
           set_local="uv run providers/publisher/auth.py --provider linkedin (writes the record after the browser consent)",
           note="the store holds a JSON record written by providers/publisher/auth.py "
                "(access_token, expires_at); from the environment, LINKEDIN_TOKEN_EXPIRES_AT may give the expiry"),
    Secret("LINKEDIN_CLIENT_ID",
           "the LinkedIn app that authorizes the publisher, once",
           "an app with the \"Share on LinkedIn\" product",
           ("providers/publisher/auth.py",),
           store_username="linkedin-client-id"),
    Secret("LINKEDIN_CLIENT_SECRET",
           "the LinkedIn app's secret, used once by the authorization",
           "the app's primary client secret",
           ("providers/publisher/auth.py",),
           store_username="linkedin-client-secret"),
    Secret("GMAIL_REFRESH_TOKEN",
           "read the user's Gmail (search and read messages, never change them)",
           "OAuth scope https://www.googleapis.com/auth/gmail.readonly only (providers/mailbox/auth.py)",
           ("providers/mailbox/gmail.py",),
           store_username="mailbox-gmail",
           set_local="uv run providers/mailbox/auth.py --provider gmail (writes the record after the browser consent)",
           note="the store holds a JSON record written by providers/mailbox/auth.py (refresh_token, scope, "
                "obtained_at, account); from the environment, the bare refresh token"),
    Secret("GMAIL_CLIENT_ID",
           "the Google Cloud OAuth client (Desktop app) that authorizes and refreshes the Gmail access",
           "a Desktop app OAuth client in a project with the Gmail API and only the gmail.readonly scope",
           ("providers/mailbox/auth.py", "providers/mailbox/gmail.py"),
           store_username="gmail-client-id"),
    Secret("GMAIL_CLIENT_SECRET",
           "that Google OAuth client's secret, used by the authorization and every token refresh",
           "the Desktop app client's secret",
           ("providers/mailbox/auth.py", "providers/mailbox/gmail.py"),
           store_username="gmail-client-secret"),
    Secret("OPENROUTER_API_KEY",
           "run the floor model's eval runs through OpenRouter, and the runtime's model calls through the "
           "API adapter when its model is openrouter/<vendor>/<model>",
           "a key used only for evals and the runtime; a credit limit on it is recommended",
           ("evals/eval_run.py --pass-env", "adapters/agents-dir/run-prompt.sh",
            "adapters/api/run_agent.py"),
           store_username="openrouter"),
    Secret("DEEPSEEK_API_KEY",
           "run the floor model's eval runs through DeepSeek's own API, when the floor model id is deepseek/<model>",
           "a key used only for evals; a spending limit on it is recommended",
           ("evals/eval_run.py --floor-pass-env", "adapters/agents-dir/run-prompt.sh"),
           store_username="deepseek"),
    Secret("ANTHROPIC_API_KEY",
           "the runtime's model calls through the API adapter (adapters/api/) when its model is anthropic/<model>",
           "an API key with a spend limit",
           ("adapters/api/run_agent.py",),
           store_username="anthropic"),
)}


class NotRegistered(KeyError):
    pass


def _from_env(secret: Secret, environ) -> tuple[str, str] | None:
    for name in (secret.name, *secret.aliases):
        value = (environ.get(name) or "").strip()
        if value:
            return value, f"environment ({name})"
    return None


def _keyring():
    try:
        import keyring  # imported lazily: only needed when the store is used
    except ImportError:
        return None
    return keyring


def _from_store(secret: Secret, store) -> tuple[str, str] | None:
    if not secret.store_username or store is None:
        return None
    try:
        value = (store.get_password(SERVICE, secret.store_username) or "").strip()
    except Exception:  # a locked or missing backend is "not found here", never a crash
        return None
    return (value, "secret store") if value else None


def resolve(name: str, *, allow_store: bool = True, environ=None, store="default") -> tuple[str, str] | None:
    """Return (value, source) for a registered secret, or None. Never prints the value."""
    secret = REGISTRY.get(name)
    if secret is None:
        raise NotRegistered(name)
    environ = os.environ if environ is None else environ
    found = _from_env(secret, environ)
    if found or not allow_store:
        return found
    return _from_store(secret, _keyring() if store == "default" else store)


def how_to_set(secret: Secret) -> str:
    local = secret.set_local or (f"uv run --with keyring==25.7.0 keyring set {SERVICE} {secret.store_username}"
                                 if secret.store_username else f"export {secret.name}=...")
    return f"cloud or CI: environment variable {secret.name}; local: {local}"


def report(environ=None, store="default") -> list[dict]:
    environ = os.environ if environ is None else environ
    store = _keyring() if store == "default" else store
    rows = []
    for secret in REGISTRY.values():
        env_hit = _from_env(secret, environ)
        store_hit = None if env_hit else _from_store(secret, store)
        rows.append({
            "name": secret.name,
            "found": bool(env_hit or store_hit),
            "source": (env_hit or store_hit or (None, None))[1],
            "store": "unavailable" if store is None else "available",
            "purpose": secret.purpose,
            "permission": secret.permission,
            "readers": list(secret.readers),
            "set": how_to_set(secret),
            "note": secret.note,
        })
    return rows


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("--help", "-h"):
        print(__doc__)
        return 0 if argv else EXIT_USAGE
    if argv[0] == "--list" and len(argv) <= 2 and (len(argv) == 1 or argv[1] == "--json"):
        rows = report()
        if "--json" in argv:
            print(json.dumps(rows, indent=2))
        else:
            for r in rows:
                state = f"found ({r['source']})" if r["found"] else "missing"
                print(f"{r['name']:<24} {state:<34} {r['purpose']}")
                if not r["found"]:
                    print(f"{'':<24} set it: {r['set']}")
        return 0
    if argv[0] == "--check" and len(argv) == 2:
        try:
            found = resolve(argv[1])
        except NotRegistered:
            print(f"error: {argv[1]!r} is not a registered secret; see --list", file=sys.stderr)
            return EXIT_USAGE
        if found:
            print(json.dumps({"name": argv[1], "found": True, "source": found[1]}))
            return 0
        print(f"{argv[1]} not found: {how_to_set(REGISTRY[argv[1]])}", file=sys.stderr)
        return EXIT_NOT_FOUND
    print("error: unknown arguments; see --help", file=sys.stderr)
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
