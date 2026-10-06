"""How a person changes a task board without the provider, per implementation of integration:issue-tracker: what the
contract tests (test_issue_tracker_contract.py) use to play the person. Not a test file.

Every implementation the resolver lists needs an entry in HARNESSES, or the contract tests fail. An entry is a class
whose instance gives:
  config(tmp_path) -> dict          the task_board object of a project configuration, for a fresh board
  env() -> dict                     the environment variables the implementation needs (stand-in values only)
  person_edits(id, title=None, text=None, state=None)    a person changes an item on the board
  person_comments(id, text)         a person adds a comment to an item
  person_creates(title, text) -> id a person writes a new item on the board
"""
from __future__ import annotations

from pathlib import Path


class LocalBoard:
    """The local implementation: the board is a folder of Markdown files a person edits by hand."""

    def config(self, tmp_path) -> dict:
        self.dir = Path(tmp_path) / "board"
        self.dir.mkdir()
        return {"provider": "local", "dir": str(self.dir)}

    def env(self) -> dict:
        return {}

    def _lines(self, ident: str) -> list:
        return (self.dir / f"{ident}.md").read_text(encoding="utf-8").split("\n")

    def _save(self, ident: str, lines: list) -> None:
        (self.dir / f"{ident}.md").write_text("\n".join(lines), encoding="utf-8")

    def person_edits(self, ident: str, title=None, text=None, state=None) -> None:
        lines = self._lines(ident)
        if title is not None:
            lines[0] = f"# {title}"
        if state is not None:
            at = next(i for i, line in enumerate(lines) if line.startswith("State: "))
            lines[at] = f"State: {state}"
        if text is not None:
            start = next(i for i, line in enumerate(lines) if line.startswith("State: ")) + 1
            end = next(i for i, line in enumerate(lines) if line == "## Comments")
            lines[start:end] = ["", text, ""]
        self._save(ident, lines)

    def person_comments(self, ident: str, text: str) -> None:
        lines = self._lines(ident)
        end = next(i for i, line in enumerate(lines) if line == "## Runtime")
        lines[end:end] = [f"- {text}", ""]
        self._save(ident, lines)

    def person_creates(self, title: str, text: str) -> str:
        ident = "p" + str(len(list(self.dir.glob("p*.md"))) + 1)
        (self.dir / f"{ident}.md").write_text(f"# {title}\n\nState: requested\n\n{text}\n", encoding="utf-8")
        return ident


HARNESSES = {"local": LocalBoard}
