"""Tests for skills/brand-profile/scripts/profile_export.py. Offline; every name and number below is fictional.

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


PROFILE_EXPORT = "skills/brand-profile/scripts/profile_export.py"


# A fictitious export, laid out as the platform's "Save to PDF" text comes out of a PDF reader.
EXPORT_TEXT = "\n".join([
    "Contact", "+44 20 7946 0000 (Mobile)", "dana@mail.example", "profiles.example/in/dana-example",
    "Top Skills", "Rust", "Languages", "English (Native or Bilingual)",
    "Dana Example", "Staff Engineer | Databases", "Leeds, England, United Kingdom",
    "Summary", "Engineer who likes small tools. Reach me at +44 20 7946 0001.",
    "Experience", "Acme Storage", "Staff Engineer", "March 2023\xa0-\xa0Present\xa0(3 years 7 months)", "Leeds",
    "Built the storage engine.", "\xa0 Page 1 of 2", "Beta Labs", "Engineer",
    "January 2019 - February 2023 (4 years 2 months)", "Remote", "Wrote the query planner.",
    "Education", "Some University", "BSc, Computer Science · (2015 - 2018)",
])

# The same export in German: other section titles, other month names, another word for a current role.
GERMAN_EXPORT = "\n".join([
    "Kontakt", "dana@mail.example", "Dana Example", "Staff Engineer | Datenbanken", "Leeds",
    "Zusammenfassung", "Ingenieurin, die kleine Werkzeuge mag.",
    "Berufserfahrung", "Acme Storage", "Staff Engineer", "Mai 2023 - Heute (3 Jahre 5 Monate)",
    "Ausbildung", "Some University",
])


def write(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_profile_export_drops_contact_data_and_computes_durations(tmp_path):
    src = write(tmp_path, "profile.txt", EXPORT_TEXT)
    r = run(PROFILE_EXPORT, "--platform", "linkedin", "--text-file", src, "--today", "2026-09-29")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["platform"] == "linkedin"
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


def test_profile_export_counts_to_the_date_given(tmp_path):
    src = write(tmp_path, "profile.txt", EXPORT_TEXT)
    r = run(PROFILE_EXPORT, "--platform", "linkedin", "--text-file", src, "--today", "2026-10-02")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["totals"]["years_and_months"] == "7 years 9 months"


def test_profile_export_refuses_text_without_roles(tmp_path):
    src = write(tmp_path, "notes.txt", "just some notes\nnothing dated")
    r = run(PROFILE_EXPORT, "--platform", "linkedin", "--text-file", src)
    assert r.returncode == 1 and r.stdout == ""
    assert "English" in r.stderr
    assert run(PROFILE_EXPORT, "--platform", "linkedin", "--text-file", src, "--today", "29/09/2026").returncode == 2


def test_profile_export_exits_1_on_an_export_in_another_language(tmp_path):
    src = write(tmp_path, "profil.txt", GERMAN_EXPORT)
    r = run(PROFILE_EXPORT, "--platform", "linkedin", "--text-file", src, "--today", "2026-09-29")
    assert r.returncode == 1, r.stdout
    assert r.stdout == "" and "Traceback" not in r.stderr
    assert "English only" in r.stderr and "ask for the export again" in r.stderr


def test_profile_export_exits_1_on_a_month_name_that_is_not_english(tmp_path):
    text = EXPORT_TEXT.replace("January 2019 - February 2023", "Januar 2019 - Februar 2023")
    src = write(tmp_path, "profile.txt", text)
    r = run(PROFILE_EXPORT, "--platform", "linkedin", "--text-file", src, "--today", "2026-09-29")
    assert r.returncode == 1 and "Januar" in r.stderr and "Traceback" not in r.stderr


def test_profile_export_needs_a_platform_it_parses(tmp_path):
    src = write(tmp_path, "profile.txt", EXPORT_TEXT)
    for args in (["--text-file", src], ["--platform", "elsewhere", "--text-file", src]):
        r = run(PROFILE_EXPORT, *args)
        assert r.returncode == 2 and r.stdout == "" and "Traceback" not in r.stderr, args


def test_profile_export_reports_an_unreadable_file(tmp_path):
    r = run(PROFILE_EXPORT, "--platform", "linkedin", "--text-file", str(tmp_path / "missing.txt"))
    assert r.returncode == 2 and "cannot read the export" in r.stderr
