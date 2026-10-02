"""Tests for skills/brand-profile/scripts/linkedin_export.py. Offline; every name and number below is fictional.

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


LINKEDIN_EXPORT = "skills/brand-profile/scripts/linkedin_export.py"


# A fictitious export, laid out as LinkedIn's "Save to PDF" text comes out of a PDF reader.
EXPORT_TEXT = "\n".join([
    "Contact", "+44 20 7946 0000 (Mobile)", "dana.example@example.org", "www.linkedin.com/in/dana-example",
    "Top Skills", "Rust", "Languages", "English (Native or Bilingual)",
    "Dana Example", "Staff Engineer | Databases", "Leeds, England, United Kingdom",
    "Summary", "Engineer who likes small tools. Reach me at +44 20 7946 0001.",
    "Experience", "Acme Storage", "Staff Engineer", "March 2023\xa0-\xa0Present\xa0(3 years 7 months)", "Leeds",
    "Built the storage engine.", "\xa0 Page 1 of 2", "Beta Labs", "Engineer",
    "January 2019 - February 2023 (4 years 2 months)", "Remote", "Wrote the query planner.",
    "Education", "Some University", "BSc, Computer Science · (2015 - 2018)",
])


def test_linkedin_export_drops_contact_data_and_computes_durations(tmp_path):
    src = tmp_path / "profile.txt"
    src.write_text(EXPORT_TEXT, encoding="utf-8")
    r = run(LINKEDIN_EXPORT, "--text-file", str(src), "--today", "2026-09-29")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert "7946" not in r.stdout and "@" not in r.stdout
    assert out["redacted"] == {"contact_section_dropped": True, "emails": 1, "phones": 2}
    assert out["header_lines"] == ["Dana Example", "Staff Engineer | Databases", "Leeds, England, United Kingdom"]
    assert out["languages"] == ["English (Native or Bilingual)"]
    first, second = out["experience"]
    assert (first["company"], first["title"], first["start"], first["end"], first["months"]) == \
        ("Acme Storage", "Staff Engineer", "2023-03", "present", 43)
    assert (second["company"], second["months"], second["location"]) == ("Beta Labs", 50, "Remote")
    assert out["totals"]["first_start"] == "2019-01" and out["totals"]["years_and_months"] == "7 years 8 months"
    assert "(2015 - 2018)" in out["education"][1]


def test_linkedin_export_refuses_text_without_roles(tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text("just some notes\nnothing dated", encoding="utf-8")
    assert run(LINKEDIN_EXPORT, "--text-file", str(src)).returncode == 1
    assert run(LINKEDIN_EXPORT, "--text-file", str(src), "--today", "29/09/2026").returncode == 2
