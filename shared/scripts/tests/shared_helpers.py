"""What the tests of shared/scripts share: where the sources are, and how one is run.

The tests of a shared script live here, at its source: a skill carries a generated copy, byte-identical, so
it carries no test of its own for that file. Every test is offline and runs on Python 3.9, the interpreter
some of these scripts are started with (providers/CONTRACT.md, "Python version").
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SOURCES = Path(__file__).resolve().parents[1]


def run(script: str, *args: str, stdin: str | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run shared/scripts/<script>. Without `stdin` the script gets an empty standard input, never a terminal."""
    return subprocess.run([sys.executable, str(SOURCES / script), *args], capture_output=True, text=True,
                          input="" if stdin is None else stdin, cwd=cwd, timeout=60)


def clean_usage_error(r: subprocess.CompletedProcess) -> bool:
    """Exit 2, a message on stderr, nothing on stdout, no traceback."""
    return r.returncode == 2 and bool(r.stderr.strip()) and not r.stdout.strip() and "Traceback" not in r.stderr
