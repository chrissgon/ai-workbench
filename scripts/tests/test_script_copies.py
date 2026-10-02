"""Tests about scripts that exist in more than one place: the shared redaction (scripts/redact.py) and the
copies of one script kept in several skills, which must stay identical.

Run: uv run --with pytest pytest scripts/tests

The tests of a skill's own scripts live in the skill, at skills/<name>/scripts/tests/. These stay here because
they are about the repository, not about one skill. Secret-like strings are assembled from pieces so that this
file does not trip the scanner.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AWS = "AKIA" + "Q7ZT2MLP4RX9KW1V"
VALUE = "q8Zt2mLp" + "4Rx9Kw1v"


def test_redact_copies_are_identical():
    shared = (ROOT / "scripts/redact.py").read_bytes()
    assert (ROOT / "skills/eng-code-review/scripts/redact.py").read_bytes() == shared, \
        "copy scripts/redact.py to skills/eng-code-review/scripts/redact.py"
    assert (ROOT / "skills/ops-repo-baseline/scripts/redact.py").read_bytes() == shared, \
        "copy scripts/redact.py to skills/ops-repo-baseline/scripts/redact.py"


def test_scan_uses_the_shared_redaction():
    scan = load("scripts/security_scan.py", "security_scan_shared")
    shared = load("scripts/redact.py", "redact_shared")
    assert scan.redact("k " + AWS) == shared.redact("k " + AWS) == "k <redacted AWS access key>"


def test_mask_secret_line_keeps_no_part_of_the_value():
    shared = load("scripts/redact.py", "redact_mask")
    for line in (f'password = "{VALUE}"', f"auth: '{VALUE}'", f"token={VALUE}{VALUE}", f"key {AWS} end",
                 f'url = "https://bot:{VALUE}@example.org/x"'):
        out = shared.mask_secret_line(line)
        assert VALUE[:6] not in out and AWS[4:] not in out, out
        assert "<redacted" in out


# ---------- copies of one script in two skills ----------

RANK = "skills/biz-market-analysis/scripts/rank.py"


def test_rank_copies_are_identical():
    a = (ROOT / RANK).read_bytes()
    assert (ROOT / "skills/biz-icp-positioning/scripts/rank.py").read_bytes() == a, \
        "copy skills/biz-market-analysis/scripts/rank.py to skills/biz-icp-positioning/scripts/rank.py"


CHECK_REFS = "skills/biz-market-analysis/scripts/check_refs.py"


def test_check_refs_copies_are_identical():
    assert (ROOT / "skills/biz-icp-positioning/scripts/check_refs.py").read_bytes() == (ROOT / CHECK_REFS).read_bytes()
