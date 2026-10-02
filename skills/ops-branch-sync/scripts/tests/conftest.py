"""Shared test setup: the tests here run git in temporary repositories only.

Git exports GIT_DIR, GIT_INDEX_FILE and friends to hooks. With them set, a `git init` or `git commit`
in a temporary folder acts on the workbench repository instead. Every GIT_* variable is removed before
any test module is imported, whoever starts pytest.
"""
import os

for name in [n for n in os.environ if n.startswith("GIT_")]:
    os.environ.pop(name, None)
