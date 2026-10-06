# Documents provider (`integration:documents`)

The documents of the task runtime (`runtime/`), mirrored where the project keeps them: on the machine or on a platform. The runtime calls a provider of this class with the project configuration's `documents` object (`docs/workbench/runtime.json`); the verbs and what each prints are in `providers/CONTRACT.md`, "Verbs per class". A write replaces the whole document; it never merges.

| File | What it is |
|------|------------|
| `local.py` | The documents as Markdown files in a folder of the machine, outside the project (`dir`); comments are the `- ` lines of a side file `<path>.comments.md`. Standard library only, Python 3.9 |
| `notion_blocks.py` | A pure helper, not an implementation: Markdown to the blocks of a page and back (`round_trip`), the platform's side of the trip for an implementation that stores blocks |

The class is found by its folder; its row in `contracts/environment.md` (and `LISTED` of `providers/resolve.py`) comes with the router's first change of its routing table.

## Which documents a person may edit on a platform

A skill's runtime manifest (`skills/<name>/evals/runtime-manifest.json`) marks each document it writes `editable` or `read_only`. A type is `editable` only when it survives the trip: `tests/test_document_types.py` runs, for each `editable` entry, the skill's own checker on its fixture before and after `notion_blocks.round_trip` (or, with no checker, checks that no word is lost). A fixture is a case of `tests/fixtures/round-trip.json` or of `tests/fixtures/types/<skill>.json`, a document a lab run of the skill wrote on its own fictional fixture. A type that fails is set to `read_only` in its manifest; the converter is not changed to make it pass.

## Tests

`uv run --with pytest==9.1.1 pytest -q providers/documents/tests`: the contract on every implementation (`documents_harness.py` plays the person for each), what is particular to `local.py`, the trip of each editable type, and the converter.
