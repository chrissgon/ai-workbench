"""Tests for skills/brand-profile/scripts/check_profile.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/brand-profile/scripts/tests
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def run(rel: str, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / rel), *args], capture_output=True, text=True,
                          cwd=cwd, input=stdin, timeout=60)


CHECK_PROFILE = "skills/brand-profile/scripts/check_profile.py"


PROFILE_OK = "\n".join([
    "# Brand profile: Dana", "", "## Who they are", "- Staff engineer since 2019 [1]", "",
    "## Never expose", "- Employer [2]", "", "## Voice", "- Samples written by them:", "  > hello network [3]", "",
    "## Sources", "[1] Export, provided 2026-09-29.", "[2] User in chat, 2026-09-29.",
    "[3] Post, 2022-11-04, https://www.linkedin.com/feed/update/urn:li:activity:6994304183386443776/",
])


def test_check_profile_passes_a_clean_profile_and_ignores_ids_in_links(tmp_path):
    doc = tmp_path / "profile.md"
    doc.write_text(PROFILE_OK, encoding="utf-8")
    r = run(CHECK_PROFILE, "--file", str(doc))
    assert r.returncode == 0, r.stdout + r.stderr


def test_check_profile_reports_contact_data_refs_and_unmarked_samples(tmp_path):
    doc = tmp_path / "profile.md"
    bad = PROFILE_OK.replace("- Employer [2]", "- nothing listed").replace("- Employer", "") \
        .replace("- Samples written by them:", "- Samples:").replace("since 2019 [1]", "since 2019 [1][4], call +44 20 7946 0000")
    bad = bad.replace("## Never expose\n- nothing listed", "## Never expose\n")
    bad = bad.replace("[3] Post, 2022-11-04,", "[3] Post, undated,")
    doc.write_text(bad, encoding="utf-8")
    r = run(CHECK_PROFILE, "--file", str(doc))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["contact_data"] == ["line 4"]
    assert out["undefined"] == ["4"] and out["unused"] == ["2"]
    assert out["never_empty"] is True and out["samples_unmarked"] is True
    assert out["no_date"] == ["3"]  # digits inside the URL's activity id are not a date
