"""Tests for the secret resolver (no real secret store: a fake object stands in for keyring).

Run: uv run --with pytest pytest providers/secrets/tests
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "resolver.py"
ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("workbench_secret_resolver_test", SCRIPT)
res = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = res
spec.loader.exec_module(res)

SENTINEL = "zz-not-a-real-value-41"


class FakeStore:
    def __init__(self, values=None, fail=False):
        self.values, self.fail, self.asked = values or {}, fail, []

    def get_password(self, service, username):
        self.asked.append((service, username))
        if self.fail:
            raise RuntimeError("locked")
        return self.values.get(username)


def test_environment_wins_then_aliases_then_store():
    store = FakeStore({"github": "from-store"})
    assert res.resolve("VCS_GITHUB_TOKEN", environ={"VCS_GITHUB_TOKEN": "a", "GITHUB_TOKEN": "b"}, store=store) \
        == ("a", "environment (VCS_GITHUB_TOKEN)")
    assert res.resolve("VCS_GITHUB_TOKEN", environ={"VCS_GITHUB_TOKEN": "  ", "GITHUB_TOKEN": "b"}, store=store) \
        == ("b", "environment (GITHUB_TOKEN)")
    assert store.asked == []
    assert res.resolve("VCS_GITHUB_TOKEN", environ={}, store=store) == ("from-store", "secret store")
    assert store.asked == [("ai-workbench", "github")]


def test_store_is_skipped_when_not_allowed_or_unavailable():
    store = FakeStore({"openrouter": "x"})
    assert res.resolve("OPENROUTER_API_KEY", allow_store=False, environ={}, store=store) is None
    assert store.asked == []
    assert res.resolve("OPENROUTER_API_KEY", environ={}, store=None) is None
    assert res.resolve("OPENROUTER_API_KEY", environ={}, store=FakeStore(fail=True)) is None


def test_unregistered_names_are_refused():
    with pytest.raises(res.NotRegistered):
        res.resolve("HOME", environ={"HOME": "/root"})


def test_report_never_carries_a_value():
    env = {name: SENTINEL for name in res.REGISTRY}
    rows = res.report(environ=env, store=None)
    assert {r["name"] for r in rows} == set(res.REGISTRY)
    assert all(r["found"] for r in rows)
    assert SENTINEL not in json.dumps(rows)


def run(*args, env=None):
    base = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp")}
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          env={**base, **(env or {})}, timeout=60)


def test_cli_check_and_list_print_no_value():
    found = run("--check", "OPENROUTER_API_KEY", env={"OPENROUTER_API_KEY": SENTINEL})
    assert found.returncode == 0 and SENTINEL not in found.stdout + found.stderr
    assert json.loads(found.stdout)["source"] == "environment (OPENROUTER_API_KEY)"
    listed = run("--list", env={name: SENTINEL for name in res.REGISTRY})
    assert listed.returncode == 0 and SENTINEL not in listed.stdout + listed.stderr
    assert run("--check", "NOT_A_SECRET").returncode == 2
    assert run("--bogus").returncode == 2


def test_every_reader_exists_and_the_contract_lists_every_secret():
    contract = (ROOT / "contracts" / "secrets.md").read_text(encoding="utf-8")
    for secret in res.REGISTRY.values():
        assert f"`{secret.name}`" in contract, f"contracts/secrets.md does not list {secret.name}"
        for reader in secret.readers:
            assert (ROOT / reader.split()[0]).exists(), reader
