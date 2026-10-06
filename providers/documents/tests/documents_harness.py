"""How a person changes documents without the provider, per implementation of integration:documents: what the
contract tests (test_documents_contract.py) use to play the person. Not a test file.

Every implementation the resolver lists needs an entry in HARNESSES, or the contract tests fail. An entry is a class
whose instance gives:
  config(tmp_path) -> dict          the documents object of a project configuration, for a fresh place
  env() -> dict                     the environment variables the implementation needs (stand-in values only)
  person_edits(id, markdown)        a person replaces a document's text where it lives
  person_comments(id, text)         a person adds a comment to a document
  expected(markdown) -> str         what a read returns for a text that was written: the text itself for an
                                    implementation that stores Markdown, notion_blocks.round_trip(text) for one that
                                    stores blocks
"""
from __future__ import annotations

from pathlib import Path


class LocalDocuments:
    """The local implementation: the documents are Markdown files in a folder a person edits by hand."""

    def config(self, tmp_path) -> dict:
        self.dir = Path(tmp_path) / "documents"
        self.dir.mkdir()
        return {"provider": "local", "dir": str(self.dir)}

    def env(self) -> dict:
        return {}

    def person_edits(self, ident: str, markdown: str) -> None:
        (self.dir / ident).write_text(markdown, encoding="utf-8")

    def person_comments(self, ident: str, text: str) -> None:
        side = self.dir / (ident + ".comments.md")
        before = side.read_text(encoding="utf-8") if side.is_file() else ""
        side.write_text(before + f"- {text}\n", encoding="utf-8")

    def expected(self, markdown: str) -> str:
        return markdown


HARNESSES = {"local": LocalDocuments}
