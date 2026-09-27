"""Shared test setup for scripts/tests.

Git exports GIT_DIR, GIT_INDEX_FILE and friends to hooks. A test that runs `git init` or
`git commit` in a temporary folder while they are set acts on the workbench repository instead:
it commits there, or turns it bare (from a worktree, `git init <tmp>` with GIT_DIR set rewrote the
shared config with core.bare = true). Every test here uses temporary repositories only, so every
GIT_* variable is removed before any test module is imported, whoever starts pytest.
"""
import os

for name in [n for n in os.environ if n.startswith("GIT_")]:
    os.environ.pop(name, None)
