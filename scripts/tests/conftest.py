"""Shared test setup for scripts/tests.

Git exports GIT_DIR, GIT_INDEX_FILE and friends to hooks. A test that runs `git init` or
`git commit` in a temporary folder while they are set acts on the workbench repository instead:
it commits there, or turns it bare. Every test here uses temporary repositories only, so these
variables are removed before any test runs, whoever starts pytest.
"""
import os

REPO_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX", "GIT_COMMON_DIR",
             "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_CEILING_DIRECTORIES")

for name in REPO_VARS:
    os.environ.pop(name, None)
