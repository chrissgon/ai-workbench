"""Tests for installer and build hygiene: packs are validated, installers delete only what they made.

Run: uv run --with pytest pytest scripts/tests

Every run targets a temporary folder (--project, HOME and the skills directory variable point there).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = ROOT / "adapters/agents-dir/install.sh"
BUILD = ROOT / "adapters/claude-code/build.py"
BASH = shutil.which("bash")


def default_pack() -> list[str]:
    r = subprocess.run([sys.executable, str(ROOT / "scripts/select_skills.py"), "--pack", "default", "--lines"],
                       capture_output=True, text=True, check=True)
    return r.stdout.split()


def install(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(tmp_path / "home")}
    return subprocess.run([BASH, str(AGENTS_DIR), "--project", str(tmp_path / "proj"), *args], env=env,
                          capture_output=True, text=True, timeout=120)


def test_pack_names_are_validated(tmp_path):
    for pack in ("../../x", "/etc/passwd", "Default", "nope"):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/select_skills.py"), "--pack", pack],
                           capture_output=True, text=True)
        assert r.returncode == 2 and "not found" in r.stderr, pack
        b = subprocess.run([sys.executable, str(BUILD), "--pack", pack, "--dry-run"], capture_output=True, text=True)
        assert b.returncode == 2, pack
        assert install(tmp_path, "--pack", pack).returncode == 2, pack
    assert not (tmp_path / "proj").exists()


def test_symlink_install_skips_and_keeps_a_folder_it_did_not_make(tmp_path):
    names = default_pack()
    skills = tmp_path / "proj" / ".agents" / "skills"
    mine = skills / names[0]
    mine.mkdir(parents=True)
    (mine / "notes.md").write_text("mine\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (skills / names[1]).symlink_to(elsewhere)

    r = install(tmp_path)
    assert r.returncode == 1 and "Skipped" in r.stderr
    out = json.loads(r.stdout)
    assert set(out["skipped"]) == set(names[:2])
    assert out["installed"] == len(names) - 2
    assert (skills / names[2]).is_symlink()

    r = install(tmp_path, "--uninstall")
    assert r.returncode == 1
    assert (mine / "notes.md").read_text(encoding="utf-8") == "mine\n"
    assert (skills / names[1]).is_symlink() and os.readlink(skills / names[1]) == str(elsewhere)
    assert not (skills / names[2]).exists()


def test_copy_install_replaces_and_removes_only_its_copies(tmp_path):
    names = default_pack()
    skills = tmp_path / "proj" / ".agents" / "skills"
    assert install(tmp_path, "--copy").returncode == 0
    assert (skills / names[0] / "SKILL.md").is_file()
    assert install(tmp_path, "--copy").returncode == 0, "a second run replaces its own copies"
    r = install(tmp_path, "--uninstall")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["removed"] == len(names)
    assert list(skills.iterdir()) == []


def test_plugin_uninstall_keeps_a_link_it_did_not_make(tmp_path):
    plugin_installer = BUILD.parent / "install.sh"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (skills_dir / "ai-workbench").symlink_to(elsewhere)
    env = {**os.environ, "HOME": str(tmp_path / "home"), "CLAUDE_SKILLS_DIR": str(skills_dir)}
    r = subprocess.run([BASH, str(plugin_installer), "--uninstall"], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 1 and "not created by this installer" in r.stderr
    assert os.readlink(skills_dir / "ai-workbench") == str(elsewhere)
