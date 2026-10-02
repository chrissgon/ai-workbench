"""Tests for skills/design-system/scripts/lint_design_system.py. Offline; every name and number below is fictional.

Run: uv run --with pytest pytest skills/design-system/scripts/tests
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


# ---------- design-system/lint_design_system.py: the library prefix ----------

LINT_DS = "skills/design-system/scripts/lint_design_system.py"


def test_lint_design_system_infers_the_library_prefix(tmp_path):
    doc = tmp_path / "ds.md"
    doc.write_text("# Design system\nUses --ui-ink and --ui-bg.\n", encoding="utf-8")
    css = tmp_path / "lib.css"
    css.write_text(":root { --ui-ink: #111; --ui-bg: #fff; --ui-line: #ddd; --x-y: 1px }\n", encoding="utf-8")
    out = json.loads(run(LINT_DS, "--file", str(doc), "--library", str(css)).stdout)
    assert out["library_prefix"] == "ui"
    assert any("['--ui-line']" in e for e in out["errors"])
    listed = tmp_path / "lib.md"
    listed.write_text("| Token | Value |\n| `--ds-bg` | #fff |\n| `--ds-ink` | #111 |\n", encoding="utf-8")
    out = json.loads(run(LINT_DS, "--file", str(doc), "--library", str(listed)).stdout)
    assert out["library_prefix"] == "ds"
    out = json.loads(run(LINT_DS, "--file", str(doc), "--library", str(css), "--prefix", "x").stdout)
    assert out["library_prefix"] == "x" and any("['--x-y']" in e for e in out["errors"])
    assert run(LINT_DS, "--file", str(doc), "--library", str(css), "--prefix", "../a").returncode == 2


def lint(rel: str, path: Path, text: str, *args: str) -> tuple[int, dict]:
    """Write `text` to `path`, lint it, and return the exit code and the parsed JSON result."""
    path.write_text(text, encoding="utf-8")
    r = run(rel, "--file", str(path), *args)
    return r.returncode, json.loads(r.stdout)


# ---------- design-system/lint_design_system.py: flows, library values, empty Components ----------

DS_FLOWS = "# Flows\n\n## Screens\n\n- SCREEN-1: Home. Regions: hero.\n- SCREEN-2: Post. Regions: body.\n"
DS_LIBRARY = "| Token | Light | Dark |\n|---|---|---|\n| `--ui-bg` | #FFFFFF | #000000 |\n| `--ui-gap` | 16px |\n"


def design_system(bg: str = "#FFFFFF", gap: str = "16px",
                  component: str = "| Button | library | size: sm, md | default, hover | SCREEN-1, SCREEN-2 | lib.md |") -> str:
    return f"""# Design system: Plinth

## Summary

One library governs the values.

## Sources

- lib.md

## Ownership

- Colour: the library.

## Colour

| Token | Light | Dark | Role | Source |
|-------|-------|------|------|--------|
| `--ui-bg` | {bg} | #000000 | page background | lib.md |

## Contrast

| Text token | On background | Light ratio | Dark ratio | AA |
|------------|---------------|-------------|------------|----|

## Type

- Typeface: Example Sans, fallback sans-serif. Source: lib.md
- Reading width: 68ch. Source: lib.md

## Space, radii, borders, elevation

| Token | Value | Role | Source |
|-------|-------|------|--------|
| `--ui-gap` | {gap} | gap between blocks | lib.md |

## Layout

## Components

| Component | Owner | Variants | States | Screens | Source |
|-----------|-------|----------|--------|---------|--------|
{component}

## Design tool

- File: none available

## Assumptions

## Open questions

## Readiness

- Ready for design-brief: yes
"""


def lint_ds(tmp_path: Path, text: str, *flags: str) -> tuple[int, dict]:
    (tmp_path / "flows.md").write_text(DS_FLOWS, encoding="utf-8")
    (tmp_path / "lib.md").write_text(DS_LIBRARY, encoding="utf-8")
    args = []
    for flag in flags:
        args += [flag, str(tmp_path / ("flows.md" if flag == "--flows" else "lib.md"))]
    return lint(LINT_DS, tmp_path / "ds.md", text, *args)


def test_lint_design_system_accepts_a_document_that_mirrors_flows_and_library(tmp_path):
    code, out = lint_ds(tmp_path, design_system(), "--flows", "--library")
    assert (code, out["errors"]) == (0, []) and out["library_prefix"] == "ui"


def test_lint_design_system_needs_a_screen_on_every_component_row(tmp_path):
    row = "| Button | library | size: sm, md | default, hover | every page | lib.md |"
    code, out = lint_ds(tmp_path, design_system(component=row), "--flows")
    assert code == 1 and out["errors"] == ["component row Button cites no SCREEN-n in its Screens cell"]
    assert lint_ds(tmp_path, design_system(component=row))[1]["errors"] == [], "the check runs only with --flows"


def test_lint_design_system_refuses_a_screen_the_flows_do_not_have(tmp_path):
    row = "| Button | library | size: sm, md | default, hover | SCREEN-1, SCREEN-9 | lib.md |"
    code, out = lint_ds(tmp_path, design_system(component=row), "--flows")
    assert code == 1 and out["errors"] == ["screens cited that the flows file does not have: ['SCREEN-9']"]
    (tmp_path / "empty.md").write_text("# Flows\n", encoding="utf-8")
    r = run(LINT_DS, "--file", str(tmp_path / "ds.md"), "--flows", str(tmp_path / "empty.md"))
    assert json.loads(r.stdout)["errors"] == ["--flows: the flows file names no SCREEN-n"]


def test_lint_design_system_refuses_a_changed_library_value(tmp_path):
    code, out = lint_ds(tmp_path, design_system(bg="#FAFAFA"), "--library")
    assert code == 1
    assert out["errors"] == ["library value changed or absent: no line naming --ui-bg carries #FFFFFF and #000000"]
    code, out = lint_ds(tmp_path, design_system(gap="1rem"), "--library")
    assert out["errors"] == ["library value changed or absent: no line naming --ui-gap carries 16px"]
    assert lint_ds(tmp_path, design_system(bg="#ffffff"), "--library")[0] == 0, "letter case of a hex value is not a change"


def test_lint_design_system_refuses_an_empty_components_table(tmp_path):
    code, out = lint_ds(tmp_path, design_system(component=""))
    assert code == 1 and out["errors"] == ["Components table has no rows"] and out["counts"]["components"] == 0
