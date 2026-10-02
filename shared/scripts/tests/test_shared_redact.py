"""Tests for shared/scripts/redact.py: the credential formats, and that no part of a secret survives.
Offline. Secret-like strings are assembled from pieces so that this file does not trip the scanner.

Run: uv run --with pytest pytest shared/scripts/tests
"""
from __future__ import annotations

import importlib.util

from shared_helpers import SOURCES, clean_usage_error, run

spec = importlib.util.spec_from_file_location("redact_under_test", SOURCES / "redact.py")
redact = importlib.util.module_from_spec(spec)
spec.loader.exec_module(redact)

AWS = "AKIA" + "Q7ZT2MLP4RX9KW1V"
VALUE = "q8Zt2mLp" + "4Rx9Kw1v"
PASSWORD = "Sup3r" + "S3cr3tPw"
BEARER = "9f8e7d6c5b4a" + "39281706f5e4d3c2b1a0"


def test_known_formats_are_replaced_by_their_label():
    assert redact.redact("k " + AWS) == "k <redacted AWS access key>"
    assert redact.token_label("k " + AWS) == "AWS access key" and redact.token_label("nothing here") is None


def test_a_credential_inside_a_connection_address_is_found_and_redacted():
    for line in (f"conn = 'postgres://admin:{PASSWORD}@db.internal:5432/app'",
                 f"REDIS_URL=redis://:{PASSWORD}@10.0.0.5:6379/0",
                 f"git clone https://deploy:{PASSWORD}@git.example/team/app.git"):
        assert redact.secret_values(line) == [("credential in a connection address", PASSWORD)], line
        out = redact.redact(line)
        assert PASSWORD not in out and PASSWORD[:4] not in out and ":<redacted>@" in out, out


def test_a_bearer_token_is_found_and_redacted():
    for line in ("headers = {'Authorization': 'Bearer " + BEARER + "'}", f"curl -H 'authorization: bearer {BEARER}'"):
        assert redact.secret_values(line) == [("bearer token", BEARER)], line
        out = redact.redact(line)
        assert BEARER[:6] not in out and "<redacted>" in out, out


def test_what_is_not_a_secret_by_its_place_is_left_alone():
    for line in ("see https://example.org/a:b@c", "Bearer <token>", "Bearer $TOKEN", "git@git.example:owner/repo.git",
                 "ssh://git@host:22/path", "http://host:8080/a@b", "the bearer of this letter is welcome here",
                 "mailto:dana@tinykv.example"):
        assert redact.secret_values(line) == [] and redact.redact(line) == line, line
    # A short word after user: is still reported; whether it is a placeholder is the caller's decision.
    assert redact.secret_values("https://user:pass@host/x") == [("credential in a connection address", "pass")]


def test_mask_secret_line_keeps_no_part_of_the_value():
    for line in (f'password = "{VALUE}"', f"auth: '{VALUE}'", f"token={VALUE}{VALUE}", f"key {AWS} end",
                 f'url = "https://bot:{VALUE}@example.org/x"', f"Authorization: Bearer {VALUE}{VALUE}"):
        out = redact.mask_secret_line(line)
        assert VALUE[:6] not in out and AWS[4:] not in out, out
        assert "<redacted" in out


def test_the_docstring_names_no_path_of_one_repository():
    """The file is copied into skills, and from one of them into a user's project."""
    doc = redact.__doc__
    assert "skills/" not in doc and "scripts/" not in doc and "security_scan" not in doc


def test_the_command_line():
    r = run("redact.py", stdin=f"k {AWS}\nplain\n")
    assert r.returncode == 0 and r.stdout == "k <redacted AWS access key>\nplain\n"
    r = run("redact.py", "--secret-line", stdin=f'x = "{VALUE}"\n')
    assert r.returncode == 0 and VALUE[:6] not in r.stdout and "<redacted>" in r.stdout
    assert run("redact.py", "--help").returncode == 0
    assert clean_usage_error(run("redact.py", "--nope"))
