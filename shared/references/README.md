# Shared references

Knowledge that more than one skill loads, written once. This file says what kinds of reference the folder holds and the rules for each; it lists no file, so that adding a reference edits nothing that exists.

Skills reference these files with a relative path from the skill folder (`../../shared/references/<file>`). Adapters that copy skills instead of linking them must copy `shared/references/` alongside.

Two kinds of reference live here:

- **A transversal concern**, a file directly in this folder (`<concern>.md`): a checklist or a method that constrains work in every area, such as security. It states at the top which skills load it and at which step. One is added when a second skill needs the same knowledge, never speculatively.
- **A platform reference**, in `platforms/`: `<platform>.md`, what one social platform is as a medium, and `<platform>.json`, the same facts as data for scripts. One is written when the platform has a real task, never from general knowledge. The rules, the keys of a data file and the definition of which platform a step works on are in `platforms/README.md`.

A change to a file here changes the context of the skills that read it: the lab evidence they made with the old file becomes inherited (the reliability model, "What a change costs"). A new file moves nothing.
