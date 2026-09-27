"""Shared test setup for scripts/tests.

Git exports GIT_DIR, GIT_INDEX_FILE and similar variables to hooks. A test that runs `git init` or
`git commit` in a temporary folder while they are set works on the real repository instead: from a
worktree, `git init <tmp>` with GIT_DIR set rewrote the shared config with core.bare = true. Every
test therefore runs without them.
"""
import os

import pytest


@pytest.fixture(autouse=True)
def _no_git_repository_env(monkeypatch):
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
